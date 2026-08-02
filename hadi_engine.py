#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""محرك هادي — Claude Agent SDK مع جلسات لكل محادثة، وحراس أمان، وfallback للـ CLI.

الفكرة:
  discord_bot.py (وأي مهمة خلفية) بينادوا run_agent() هنا بدل ما يشغّلوا
  subprocess `claude -p` بنفسهم. المحرك بيقرر المسار:

  - HADI_ENGINE=sdk (الافتراضي): Claude Agent SDK — نفس محرك Claude Code كمكتبة:
      * جلسة مستمرة لكل محادثة (conv_key) عبر resume — استمرارية حقيقية + prompt caching.
      * PreToolUse hooks: منع حتمي (مش نصي) لقراءة .env والأوامر الخطرة.
      * نفس صلاحيات المشروع (setting_sources=["project"] بيحمّل CLAUDE.md
        و .claude/settings.local.json زي الـ CLI بالظبط).
  - HADI_ENGINE=cli: المسار القديم بالظبط (subprocess claude -p) — زرار رجوع فوري
    من .env من غير أي تعديل كود.
  - لو الـ SDK مش متاح وقت التشغيل (مكتبة ناقصة/CLI مش لاقيه) بيقع لوحده على cli
    ويطبع السبب — البوت عمره ما يقف بسبب الترحيل.

حالة الجلسات بتتخزن في sessions.json (حالة تشغيل — في .gitignore، مش بتترفع).
سجل الاستخدام (كاش/تكلفة/زمن لكل تفاعل) بيتكتب JSONL في logs/usage.jsonl —
تحليله: python3 usage_report.py (بند 3.1 — القياس قبل أي ادعاء توفير).
"""
import asyncio
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

import state_lock  # قفل الكتابة المشترك بين العمليات (sessions.json)

BASE_DIR = Path(__file__).resolve().parent

try:  # تحميل .env لو المحرك اتستورد لوحده (البوت بيحمّله قبلنا أصلًا — مفيش ضرر من التكرار)
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

ENGINE_MODE = os.getenv("HADI_ENGINE", "sdk").strip().lower() or "sdk"
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5").strip() or "claude-sonnet-5"
import claude_bin  # حل مسار claude CLI عبر البيئات (سيرفر/Docker) — حادثة 2026-08
CLAUDE_BIN = claude_bin.resolve()
import contextvars

# هوية طالب الطلب. ContextVar مش os.environ: الأخير عام على العملية كلها،
# ومع MAX_CONCURRENCY > 1 ده معناه تسريب هوية بين طلبين متوازيين.
_actor = contextvars.ContextVar("hadi_actor", default="")


def _actor_env() -> dict:
    """بيئة العملية الفرعية + هوية الطالب لطبقة صلاحيات PostHog."""
    return {**os.environ, "HADI_PH_ACTOR": _actor.get() or ""}


MAX_CONCURRENCY = max(1, int(os.getenv("HADI_MAX_CONCURRENCY", "2") or "2"))
SESSION_TTL_HOURS = float(os.getenv("HADI_SESSION_TTL_HOURS", "6") or "6")
# 2026-07-26: الرقم مقاس مش مخمّن — logs/usage.jsonl على 117 تفاعل:
# p50=2 p90=8 p95=12 p99=17 max=17. الـ 50 القديمة كانت 3x أعلى حالة حصلت،
# يعني مساحة هروب واسعة لو الموديل دخل حلقة. 22 = p99 + هامش 5.
MAX_TURNS = int(os.getenv("HADI_MAX_TURNS", "22") or "22")
# المهام الخلفية (pending flush) والتقارير محتاجة مساحة أوسع من الرد التفاعلي.
HEAVY_MAX_TURNS = int(os.getenv("HADI_HEAVY_MAX_TURNS", "50") or "50")
SESSIONS_FILE = Path(os.environ.get("HADI_SESSIONS_FILE", str(BASE_DIR / "sessions.json")))
LOGS_DIR = BASE_DIR / "logs"
USAGE_LOG = LOGS_DIR / "usage.jsonl"


class EngineError(RuntimeError):
    """خطأ تشغيل من المحرك (SDK أو CLI)."""


class EngineTimeout(EngineError):
    """الطلب عدّى المهلة."""


class EngineUnavailable(EngineError):
    """المحرك مش متاح لسبب تشغيلي مش برمجي — رصيد خلص أو مش مسجّل دخول.

    حادثة 2026-07-23: هادي كان واقع من 9ص لـ 1م اليوم اللي بعده على
    «You've hit your weekly limit»، وبعدين على «Not logged in · Please run
    /login» — والمستخدم كان بيشوف «حصل خطأ: EngineError» ومحدش اتبلّغ.
    الفئة دي محتاجة: تنبيه للمسؤول + رسالة مفهومة للمستخدم، ومفيش retry
    (إعادة المحاولة على حد أسبوعي مالهاش فايدة).
    """


# الأنماط الحرفية من لوج الإنتاج (journalctl 2026-07-23)
_UNAVAILABLE_RX = re.compile(
    r"hit your (weekly|session|usage) limit"
    r"|not logged in"
    r"|please run /login"
    r"|credit balance is too low"
    r"|insufficient.{0,20}quota",
    re.IGNORECASE,
)


def is_unavailable(message: str) -> bool:
    return bool(_UNAVAILABLE_RX.search(message or ""))


# --- توفر الـ SDK ---------------------------------------------------------
_SDK_IMPORT_ERROR = None
try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        CLINotFoundError,
        HookMatcher,
        ResultMessage,
        TextBlock,
        ToolUseBlock,
        query,
    )
except Exception as _e:  # مكتبة مش متسطبة → fallback cli
    _SDK_IMPORT_ERROR = _e

_sdk_disabled_reason = None
if ENGINE_MODE == "cli":
    _sdk_disabled_reason = "HADI_ENGINE=cli (اختيار يدوي)"
elif _SDK_IMPORT_ERROR is not None:
    _sdk_disabled_reason = f"claude-agent-sdk مش متاح: {type(_SDK_IMPORT_ERROR).__name__}"


def sdk_active() -> bool:
    return _sdk_disabled_reason is None


def describe() -> str:
    if sdk_active():
        return (f"sdk (model={MODEL}, max_concurrency={MAX_CONCURRENCY}, "
                f"session_ttl={SESSION_TTL_HOURS}h, max_turns={MAX_TURNS})")
    return f"cli (model={MODEL}) — السبب: {_sdk_disabled_reason}"


# --- حقن الـ Reflection المضمون (نقطة 6 — F9) ------------------------------
# قبل كده HADI_REFLECTION_INSTRUCTIONS.md كان ملف على الرف — بيتطبق بس لو الموديل
# «قرر» يفتحه. دلوقتي محتواه بيتحقن في الـ system prompt نفسه (append على البريسيت)
# فتطبيقه مضمون في كل رد. النص ثابت ← الـ prefix بيفضل byte-identical والكاش بيصمد.
def _load_reflection() -> str:
    try:
        txt = (BASE_DIR / "HADI_REFLECTION_INSTRUCTIONS.md").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if not txt:
        return ""
    return "\n\n# مراجعة ذاتية إلزامية قبل أي إرسال (Reflection — بتتطبق دايمًا)\n\n" + txt


_REFLECTION_APPEND = _load_reflection()
if not _REFLECTION_APPEND:
    print("HADI ENGINE WARN: HADI_REFLECTION_INSTRUCTIONS.md مش موجود — الـ reflection مش هيتحقن")


# --- حد التوازي الإجمالي ---------------------------------------------------
_sem = asyncio.Semaphore(MAX_CONCURRENCY)


# --- مخزن الجلسات (conv_key → session_id) ---------------------------------
# بند 3.3: المحادثات المتوازية بتسجّل جلساتها في sessions.json — الـ mutex ده
# بيسلسل القراءة-التعديل-الكتابة جوه عملية البوت (الكاتب الوحيد للملف)،
# فمفيش تسجيلة جلسة بتضيع بين رسالتين متزامنتين.
_sessions_mutex = threading.Lock()


def _load_sessions() -> dict:
    try:
        return json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_sessions(data: dict) -> None:
    tmp = SESSIONS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SESSIONS_FILE)


def _get_resume(conv_key: str):
    """session_id للمحادثة دي لو لسه جوه الـ TTL، وإلا None (جلسة جديدة)."""
    if not conv_key:
        return None
    entry = _load_sessions().get(conv_key)
    if not entry:
        return None
    if time.time() - float(entry.get("ts", 0)) > SESSION_TTL_HOURS * 3600:
        return None
    return entry.get("session_id") or None


def _remember_session(conv_key: str, session_id: str) -> None:
    """يسجّل جلسة المحادثة.

    2026-07-26: القفل بقى flock مشترك بين العمليات مش threading.Lock بس.
    السبب: threading.Lock بيحمي جوه العملية الواحدة فقط. لما اشتغلت عمليتين
    discord_bot مع بعض (حادثة 2026-07-23) كل واحدة كتبت session_id مختلف فوق
    التانية في نفس الملف، فالجلسات اتلخبطت والردود بقت متناقضة. sessions.json
    كان الملف المشترك الوحيد اللي مش تحت الـ flock — بينما memory.md و
    reminders.json كانوا محميين. الفجوة دي اتقفلت.
    """
    if not conv_key or not session_id:
        return
    with _sessions_mutex:
        try:
            with state_lock.write_lock("hadi-sessions", timeout=10):
                data = _load_sessions()
                data[conv_key] = {"session_id": session_id, "ts": time.time()}
                _save_sessions(data)
        except TimeoutError:
            # فقدان تسجيل جلسة = جلسة جديدة في الرسالة الجاية. مش سبب لفشل الرد.
            print("HADI ENGINE WARN: قفل sessions.json مشغول — الجلسة مااتسجلتش")


def session_cursor(conv_key: str):
    """id آخر رسالة عالجها هادي في المحادثة دي، أو None لو الجلسة جديدة.

    ب-1 (2026-07-26): البوت كان بيبعت سياق القناة في **أول رسالة بالجلسة بس**،
    بحجّة إن «الجلسة المستأنفة شايلة المحادثة كلها». الحجّة غلط: الجلسة شايلة
    **الأدوار اللي هادي عالجها** بس. الرسايل اللي التيم كتبها وبوابة الحضور
    سكتت عليها (وده الافتراضي) مش موجودة في الجلسة إطلاقًا — فطلب زي «إيه رأيك
    في اللي فوق؟» كان بيوصل من غير أي سياق بينه وبين آخر رد.
    و MIGRATION_SDK.md كان بيوصف السلوك القديم (سياق مع كل رسالة) وبيشرح السبب.

    الحل: مؤشر — نبعت الرسايل **من بعد** آخر واحدة عالجها بس.
    """
    if not conv_key:
        return None
    entry = _load_sessions().get(conv_key)
    if not entry:
        return None
    if time.time() - float(entry.get("ts", 0)) > SESSION_TTL_HOURS * 3600:
        return None
    return entry.get("last_msg_id") or None


def mark_processed(conv_key: str, msg_id) -> None:
    """بيعلّم إن الرسالة دي بقت جوّه الجلسة — بيتنادى بعد أي دور مكتمل.

    مابيتناداش عند الخطأ/المهلة: الرسالة ساعتها ممكن ماتكونش دخلت الجلسة،
    فالأفضل تفضل في الـ delta بدل ما السياق يضيع.
    """
    if not conv_key or not msg_id:
        return
    with _sessions_mutex:
        try:
            with state_lock.write_lock("hadi-sessions", timeout=10):
                data = _load_sessions()
                entry = data.get(conv_key)
                if entry:
                    entry["last_msg_id"] = str(msg_id)
                    _save_sessions(data)
        except TimeoutError:
            pass


def has_session(conv_key: str) -> bool:
    """هل المحادثة دي ليها جلسة حية (جوه الـ TTL)؟

    البوت بيستخدمها عشان يبعت سياق القناة **مرة واحدة** في أول رسالة بالجلسة.
    مع resume، الجلسة شايلة الترانسكريبت كله أصلًا — فإعادة إرسال آخر 80 رسالة
    مع كل دور كانت تكرار خالص (وسبب مباشر لـ context rot).
    """
    return _get_resume(conv_key) is not None


def reset_session(conv_key: str) -> None:
    with _sessions_mutex:
        try:
            with state_lock.write_lock("hadi-sessions", timeout=10):
                data = _load_sessions()
                if conv_key in data:
                    data.pop(conv_key, None)
                    _save_sessions(data)
        except TimeoutError:
            print("HADI ENGINE WARN: قفل sessions.json مشغول — الجلسة مااتصفرتش")


def touch_session(conv_key: str) -> None:
    """يجدّد الـ TTL بناءً على أي نشاط في القناة (مش رد هادي بس).
    السبب: هادي ممكن يكون صاحي ومراقب المحادثة من غير ما يرد،
    وما يلزمش الجلسة تنتهي طالما في حركة في القناة.
    بيحدّث ts بس — الـ session_id والـ last_msg_id مش بيتلمسوا.
    """
    if not conv_key:
        return
    with _sessions_mutex:
        try:
            with state_lock.write_lock("hadi-sessions", timeout=5):
                data = _load_sessions()
                entry = data.get(conv_key)
                if entry and "session_id" in entry:
                    entry["ts"] = time.time()
                    _save_sessions(data)
        except TimeoutError:
            pass  # فقدان تجديد TTL مش كارثة


# --- سجل الاستخدام (بند 3.1/F5) ----------------------------------------
def _log_usage(conv_key: str, resumed, final: dict) -> None:
    """سطر JSONL لكل تفاعل: توكنز الكاش والتكلفة والزمن — الأساس الرقمي لأي قرار.

    فشل الكتابة عمره ما يوقف الرد (best-effort)."""
    u = final.get("usage") or {}
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "conv_key": conv_key or "-",
        "model": MODEL,
        "resumed": bool(resumed),
        "input_tokens": int(u.get("input_tokens") or 0),
        "cache_read": int(u.get("cache_read_input_tokens") or 0),
        "cache_write": int(u.get("cache_creation_input_tokens") or 0),
        "output_tokens": int(u.get("output_tokens") or 0),
        "cost_usd": final.get("cost"),
        "duration_ms": final.get("duration"),
        "num_turns": final.get("num_turns"),
        "session_id": final.get("session_id"),
    }
    try:
        LOGS_DIR.mkdir(exist_ok=True)
        with USAGE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as error:
        print(f"HADI ENGINE: usage log فشل ({error}) — مش بيوقف الرد")


# --- حراس الأدوات ----------------------------------------------------------
# F4 (تصحيح تسمية): الحارس ده denylist نصي = **طبقة دفاع إضافية** مش «منع حتمي».
# الجدار الحقيقي هو allow-list الأوامر في .claude/settings.local.json — هو اللي
# بيحدد إيه اللي ينفع يتنفذ أصلًا. الـ denylist بيمسك المحاولات الواضحة بدري
# ويوفر سبب رفض مفهوم في اللوج، بس عمره ما يكون خط الدفاع الوحيد.
# .env هو ملف الأسرار — ممنوع قراءته أو نقله بأي أمر. (.env.example عادي.)
# الأنماط اتنقلت لـ guards.py (2026-07-26) عشان تتستورد في اختبار من غير الـ SDK.
# الجدار الحقيقي يفضل allow-list الأوامر في .claude/settings.local.json — ده
# denylist = دفاع في العمق، بيمسك المحاولات الواضحة بدري وبيوفّر سبب رفض مفهوم.
from guards import _DANGEROUS_BASH, _ENV_FILE_RX, bash_reason  # noqa: E402


def _deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"حارس هادي: {reason}",
        }
    }


async def _bash_guard(input_data, tool_use_id, context):
    cmd = str((input_data.get("tool_input") or {}).get("command", "") or "")
    why = bash_reason(cmd)
    if why:
        print(f"HADI GUARD: Bash مرفوض ({why}): {cmd[:120]}")
        return _deny(why)
    return {}


async def _file_guard(input_data, tool_use_id, context):
    """يمنع قراءة ملف الأسرار بأدوات الملفات (Read/Grep/Glob)."""
    ti = input_data.get("tool_input") or {}
    target = " ".join(str(v) for v in ti.values() if isinstance(v, (str, Path)))
    if _ENV_FILE_RX.search(target):
        print(f"HADI GUARD: وصول لملف .env مرفوض: {target[:120]}")
        return _deny("قراءة ملف .env (الأسرار)")
    return {}


# --- وصف نشاط الأدوات لرسالة الحالة (بند 3.4) -------------------------------
_TOOL_SCRIPT_LABELS = (
    ("ado_cli.py", "بكلم Azure DevOps"),
    ("memory.py", "بحفظ في الذاكرة"),
    ("schedule.py", "بظبط التذكير"),
    ("po_channel_cr.py", "بشتغل على قناة الـ PO"),
    ("cr_media.py", "بجهّز الميديا للتذكرة"),
    ("usage_report.py", "بطلع تقرير الاستخدام"),
    ("git ", "بحدّث الريبو"),
)


def _tool_label(name: str, tool_input) -> str:
    """وصف مصري مختصر لنشاط الأداة — بيظهر في رسالة الحالة الحية (بند 3.4)."""
    if name == "Bash":
        cmd = str((tool_input or {}).get("command", "") or "")
        for needle, label in _TOOL_SCRIPT_LABELS:
            if needle in cmd:
                return label
        return "بشغّل أوامر على السيرفر"
    if name in ("Read", "Glob", "Grep"):
        return "بقرا ملفات المشروع"
    if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return "بكتب/بعدّل ملفات"
    if name in ("WebSearch", "WebFetch"):
        return "ببحث على النت"
    if name == "TodoWrite":
        return "بنظّم خطوات الشغل"
    if name == "Task":
        return "بشغّل مهمة فرعية"
    return f"بستخدم أداة {name}"


def _emit(on_progress, label: str) -> None:
    """تبليغ رسالة الحالة بالنشاط الحالي — فشل التبليغ عمره ما يوقف التشغيل."""
    if on_progress is None:
        return
    try:
        on_progress(label)
    except Exception as error:
        print(f"HADI ENGINE: on_progress فشل ({type(error).__name__}: {error})")


# --- مسار الـ SDK ----------------------------------------------------------
def _sdk_options(resume_id):
    return ClaudeAgentOptions(
        model=MODEL,
        env=_actor_env(),
        cwd=str(BASE_DIR),
        cli_path=CLAUDE_BIN if Path(CLAUDE_BIN).exists() else None,
        # نفس سلوك `claude -p` بالظبط: برومبت النظام القياسي + إعدادات وذاكرة المشروع.
        # exclude_dynamic_sections (بند 3.1): بيشيل الأقسام المتغيرة (cwd / git status /
        # auto-memory) من الـ system prompt ويحقنها في أول user message بدالها —
        # فالـ prefix الثابت بيفضل byte-identical بين الجلسات والكاش بيصمد حتى بعد
        # commits الذاكرة (memory.py بيعمل commit مع كل حفظ ← git status بيتغير ←
        # من غير الخيار ده كل حفظة كانت بتكسر الكاش بالكامل للجلسات الجديدة).
        # نسخ CLI قديمة بتتجاهله في صمت — بيبان فورًا في اللوج (cache_write عالي باستمرار).
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "exclude_dynamic_sections": True,
            # نقطة 6 (F9): الـ reflection جزء من الـ system prompt — مضمون، مش اختياري
            **({"append": _REFLECTION_APPEND} if _REFLECTION_APPEND else {}),
        },
        setting_sources=["project", "local"],
        permission_mode="default",
        resume=resume_id,
        max_turns=MAX_TURNS,
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[_bash_guard]),
                HookMatcher(matcher="Read", hooks=[_file_guard]),
                HookMatcher(matcher="Grep", hooks=[_file_guard]),
                HookMatcher(matcher="Glob", hooks=[_file_guard]),
            ]
        },
    )


async def _run_sdk_once(prompt: str, conv_key: str, timeout: int, on_progress=None, stats=None) -> str:
    resume_id = _get_resume(conv_key)
    parts: list = []
    final: dict = {"result": None, "session_id": None, "cost": None, "duration": None,
                   "usage": None, "num_turns": None}

    async def _consume():
        async for msg in query(prompt=prompt, options=_sdk_options(resume_id)):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
                        _emit(on_progress, "بكتب الرد")
                    elif isinstance(block, ToolUseBlock):
                        _emit(on_progress, _tool_label(block.name, block.input))
            elif isinstance(msg, ResultMessage):
                final["session_id"] = msg.session_id
                final["cost"] = msg.total_cost_usd
                final["duration"] = msg.duration_ms
                final["result"] = msg.result
                final["usage"] = msg.usage or {}
                final["num_turns"] = msg.num_turns
                if msg.is_error:
                    raise EngineError(str(msg.result or msg.subtype or "SDK error")[:1500])

    try:
        await asyncio.wait_for(_consume(), timeout=timeout)
    except asyncio.TimeoutError:
        raise EngineTimeout(f"engine timeout بعد {timeout}s")

    if final["session_id"]:
        _remember_session(conv_key, final["session_id"])
    u = final.get("usage") or {}
    cache_read = int(u.get("cache_read_input_tokens") or 0)
    cache_write = int(u.get("cache_creation_input_tokens") or 0)
    raw_input = int(u.get("input_tokens") or 0)
    denom = cache_read + cache_write + raw_input
    hit_pct = (100.0 * cache_read / denom) if denom else 0.0
    if final["cost"] is not None or final["duration"] is not None:
        print(f"HADI ENGINE: sdk done key={conv_key or '-'} "
              f"cost=${final['cost'] or 0:.4f} dur={(final['duration'] or 0)/1000:.0f}s "
              f"resume={'yes' if resume_id else 'new'} "
              f"cache_read={cache_read} cache_write={cache_write} "
              f"input={raw_input} hit={hit_pct:.0f}%")
    _log_usage(conv_key, resume_id, final)
    if stats is not None:  # بند 5.3: نفس الأرقام بتتسجل في مخزن التقييم
        stats.update({
            "cost": final.get("cost"), "usage": u, "num_turns": final.get("num_turns"),
            "duration_ms": final.get("duration"), "resumed": bool(resume_id),
        })

    text = (final["result"] or "".join(parts) or "").strip()
    if not text:
        raise EngineError("SDK رجّع رد فاضي")
    return text


_RESUME_ERR_RX = re.compile(r"(no conversation|session).{0,40}(found|not found|expired)", re.IGNORECASE)


async def _run_sdk(prompt: str, conv_key: str, timeout: int, on_progress=None, stats=None) -> str:
    try:
        return await _run_sdk_once(prompt, conv_key, timeout, on_progress, stats)
    except EngineTimeout:
        raise
    except EngineError as error:
        msg = str(error)
        if is_unavailable(msg):  # رصيد/تسجيل دخول — مفيش فايدة من retry
            raise EngineUnavailable(msg) from error
        # جلسة قديمة/مفقودة → صفّرها وحاول مرة واحدة بجلسة جديدة
        if conv_key and _RESUME_ERR_RX.search(msg):
            print(f"HADI ENGINE: resume فشل — جلسة جديدة لـ {conv_key}")
            reset_session(conv_key)
            return await _run_sdk_once(prompt, conv_key, timeout, on_progress, stats)
        if _is_transient(msg):
            print(f"HADI ENGINE: transient، محاولة تانية — {msg[-200:]}")
            await asyncio.sleep(_backoff(1))
            return await _run_sdk_once(prompt, conv_key, timeout, on_progress, stats)
        raise


# --- مسار الـ CLI (القديم كما هو — زرار الرجوع) -----------------------------
def _backoff(attempt: int, cap: float = 30.0) -> float:
    """انتظار متزايد بـ jitter — بدل رقم ثابت (Google SRE).

    الـ jitter مهم: من غيره كل الطلبات الفاشلة بتعيد المحاولة في نفس اللحظة
    بالظبط وبتضرب الخدمة اللي لسه بتقوم (thundering herd).
    """
    import random
    return min(2.0 ** attempt, cap) * (0.5 + random.random())


def _is_transient(message: str) -> bool:
    m = (message or "").lower()
    return any(s in m for s in (
        "server error", "overloaded", "api error", "internal server",
        "connection", "econnreset", "socket hang up", "rate limit",
    ))


def _run_cli_once(prompt: str, timeout: int) -> str:
    cmd = [CLAUDE_BIN, "-p", prompt, "--model", MODEL]
    if _REFLECTION_APPEND:  # نقطة 6: نفس ضمان الـ reflection على مسار الـ CLI
        cmd += ["--append-system-prompt", _REFLECTION_APPEND]
    result = subprocess.run(
        cmd,
        cwd=BASE_DIR,
        env=_actor_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        error = (result.stderr or result.stdout).strip()
        raise EngineError(error[-1500:] or "Claude لم يُرجع نتيجة")
    return result.stdout.strip()


def _run_cli_sync(prompt: str, timeout: int) -> str:
    try:
        return _run_cli_once(prompt, timeout)
    except subprocess.TimeoutExpired:
        raise EngineTimeout(f"engine timeout بعد {timeout}s")
    except EngineError as error:
        if not _is_transient(str(error)):
            raise
        print(f"HADI ENGINE: cli transient، محاولة تانية — {str(error)[-200:]}")
        time.sleep(_backoff(1))
        try:
            return _run_cli_once(prompt, min(timeout, 300))
        except subprocess.TimeoutExpired:
            raise EngineTimeout(f"engine timeout بعد {timeout}s")


# --- الواجهة العامة ---------------------------------------------------------
async def run_agent(prompt: str, conv_key: str = "", timeout: int = 900, on_progress=None,
                    stats: dict | None = None, actor_id: str = "") -> str:
    """ينفّذ برومبت هادي ويرجّع نص الرد.

    conv_key: مفتاح المحادثة ("ch:<channel_id>" أو "dm:<user_id>") — بيفعّل
    استمرارية الجلسة في مسار الـ SDK. سيبه فاضي للمهام الخلفية (جلسة نظيفة).
    بيرمي EngineTimeout عند تعدي المهلة وEngineError لأي فشل تاني.
    """
    _actor.set(actor_id or "")
    if _sem.locked():  # بند 3.4: قول للمستخدم إنه مستني دوره — مش «هنج»
        _emit(on_progress, "في الطابور العام — مستني تشغيلة تانية تخلص")
    async with _sem:
        if sdk_active():
            try:
                return await _run_sdk(prompt, conv_key, timeout, on_progress, stats)
            except (EngineTimeout, EngineError):
                raise
            except CLINotFoundError as error:  # مفاجأة وقت تشغيل → جرّب مسار الـ CLI القديم
                print(f"HADI ENGINE: SDK مش لاقي الـ CLI ({error}) — تحويل لمسار cli")
                return await asyncio.to_thread(_run_cli_sync, prompt, timeout)
            except Exception as error:  # أي خطأ SDK غير متوقع → متبلعوش
                raise EngineError(f"{type(error).__name__}: {error}") from error
        return await asyncio.to_thread(_run_cli_sync, prompt, timeout)


async def run_oneshot(prompt: str, timeout: int = 300) -> str:
    """مهمة خلفية بجلسة نظيفة (من غير resume) — زي الـ pending flush.

    بتاخد HEAVY_MAX_TURNS مش MAX_TURNS: تنفيذ طابور تذاكر معلقة محتاج أدوار
    أكتر من رد محادثة عادي."""
    global MAX_TURNS
    saved, MAX_TURNS = MAX_TURNS, HEAVY_MAX_TURNS
    try:
        return await run_agent(prompt, conv_key="", timeout=timeout)
    finally:
        MAX_TURNS = saved


async def run_clean_json(prompt: str, image_paths=None, timeout: int = 220, model: str = None) -> str:
    """نداء نظيف للموديل بدون برسونا المشروع (setting_sources=[]، cwd=/tmp) لإخراج JSON،
    مع قدرة قراءة الصور المرفقة بأداة Read (vision). بيستخدمه channel_triage للاستخراج
    والمراجعة عشان يطلّع JSON نضيف من غير تلوث بـ CLAUDE.md/شخصية هادي.

    لو الـ SDK مش نشط أو حصل أي فشل/timeout → بيقع على ask_haiku نصّي بحت (cwd=/tmp)."""
    paths = [p for p in (image_paths or []) if p]
    full = prompt
    if paths:
        full = prompt + ("\n\nالصور المرفقة للتحليل (افتح كل ملف بأداة Read وحلل محتواه، "
                         "ورقم الرسالة في اسم الملف):\n" + "\n".join(paths))
    if not sdk_active():
        return await ask_haiku(full, timeout=timeout, model=(model or "sonnet"),
                               cwd="/tmp", allow_tools=["Read"])
    options = ClaudeAgentOptions(
        model=(model or MODEL),
        env=_actor_env(),
        cwd="/tmp",
        cli_path=CLAUDE_BIN if Path(CLAUDE_BIN).exists() else None,
        system_prompt={"type": "preset", "preset": "claude_code"},
        setting_sources=[],  # مفيش CLAUDE.md ولا إعدادات مشروع — إخراج نضيف
        permission_mode="default",
        max_turns=int(os.getenv("HADI_TRIAGE_MAX_TURNS", "10") or "10"),
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[_bash_guard]),
                HookMatcher(matcher="Read", hooks=[_file_guard]),
                HookMatcher(matcher="Grep", hooks=[_file_guard]),
                HookMatcher(matcher="Glob", hooks=[_file_guard]),
            ]
        },
    )
    parts: list = []

    async def _consume():
        async for msg in query(prompt=full, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
            elif isinstance(msg, ResultMessage):
                if msg.is_error:
                    raise EngineError(str(msg.result or msg.subtype or "SDK error")[:500])

    try:
        async with _sem:
            await asyncio.wait_for(_consume(), timeout=timeout)
    except Exception as error:  # timeout أو أي فشل SDK → fallback نصّي آمن
        print(f"HADI ENGINE: run_clean_json fallback ({type(error).__name__}: {str(error)[:150]})")
        return await ask_haiku(full, timeout=min(timeout, 150),
                               model=(model or "sonnet"), cwd="/tmp",
                               allow_tools=["Read"])
    return "".join(parts).strip()


async def ask_haiku(prompt: str, timeout: int = 30, model: str = None, cwd: str = None,
                    allow_tools=False) -> str:
    """نداء موديل نصّي بحت: نص داخل، نص خارج.

    2026-07-26 — تقييد الأدوات: AGENT_ROLES.md بيوصف بوابة الحضور بـ «مفيش أدوات
    خالص»، والكود كان بينده الـ CLI بالافتراضيات (كل الأدوات متاحة نظريًا) وفي
    برومبته **نص رسالة مستخدم خام**. بقى مفروض في الأمر نفسه:
        allow_tools=False        → --allowedTools "" + --permission-mode plan
        allow_tools=["Read"]     → للـ vision fallback بتاع run_clean_json بس

    لو نسخة الـ CLI مابتعرفش الفلاجز دي (رجوع لإصدار أقدم)، بنعيد المحاولة من
    غيرها مرة واحدة — عشان تقييد الأمان مايسكّتش البوابة بالكامل في صمت.
    """
    import asyncio
    base = [CLAUDE_BIN, "-p", prompt, "--model",
            (model or os.getenv("HAIKU_MODEL", "haiku"))]
    tools = "" if not allow_tools else ",".join(allow_tools)
    hardened = base + ["--allowedTools", tools, "--permission-mode", "plan"]

    async def _run(cmd):
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=cwd, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode, (out or b"").decode("utf-8", "replace").strip(), \
            (err or b"").decode("utf-8", "replace")[:300]

    try:
        code, out, err = await _run(hardened)
        if out:
            return out
        if code != 0:
            print(f"ASK_HAIKU: المحاولة المقيّدة فشلت (rc={code}: {err}) — "
                  "إعادة من غير الفلاجز")
            _, out, _ = await _run(base)
            return out
        return ""
    except Exception:
        return ""
