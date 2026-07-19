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

BASE_DIR = Path(__file__).resolve().parent

try:  # تحميل .env لو المحرك اتستورد لوحده (البوت بيحمّله قبلنا أصلًا — مفيش ضرر من التكرار)
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

ENGINE_MODE = os.getenv("HADI_ENGINE", "sdk").strip().lower() or "sdk"
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5").strip() or "claude-sonnet-5"
CLAUDE_BIN = os.getenv("CLAUDE_BIN", "/home/ubuntu/.local/bin/claude").strip()
MAX_CONCURRENCY = max(1, int(os.getenv("HADI_MAX_CONCURRENCY", "2") or "2"))
SESSION_TTL_HOURS = float(os.getenv("HADI_SESSION_TTL_HOURS", "6") or "6")
MAX_TURNS = int(os.getenv("HADI_MAX_TURNS", "50") or "50")
SESSIONS_FILE = BASE_DIR / "sessions.json"
LOGS_DIR = BASE_DIR / "logs"
USAGE_LOG = LOGS_DIR / "usage.jsonl"


class EngineError(RuntimeError):
    """خطأ تشغيل من المحرك (SDK أو CLI)."""


class EngineTimeout(EngineError):
    """الطلب عدّى المهلة."""


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
    if not conv_key or not session_id:
        return
    with _sessions_mutex:
        data = _load_sessions()
        data[conv_key] = {"session_id": session_id, "ts": time.time()}
        _save_sessions(data)


def reset_session(conv_key: str) -> None:
    with _sessions_mutex:
        data = _load_sessions()
        if conv_key in data:
            data.pop(conv_key, None)
            _save_sessions(data)


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


# --- حراس الأدوات (منع حتمي، مش تعليمات نصية) ------------------------------
# .env هو ملف الأسرار — ممنوع قراءته أو نقله بأي أمر. (.env.example عادي.)
_ENV_FILE_RX = re.compile(r"\.env(?!\.example)\b")
_SECRET_NAMES = r"(AZURE_DEVOPS_PAT|DISCORD_BOT_TOKEN|POSTHOG_API_KEY|ANTHROPIC_API_KEY)"

_DANGEROUS_BASH = [
    (re.compile(r"\brm\s+(-[a-zA-Z]*[rR][a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*[rR])\s+(/|~|\$HOME)"),
     "حذف جذري خارج مجلد المشروع"),
    (re.compile(r"\bgit\s+push\b.*(--force|-f\b)"), "git push بالقوة"),
    (re.compile(r"\bgit\s+reset\s+--hard"), "git reset --hard"),
    (re.compile(r"\b(shutdown|reboot|poweroff|halt|mkfs\w*|dd\s+if=)"), "أوامر نظام خطرة"),
    (re.compile(r"(?<![.\w-])(printenv|env)\s*(\||>|$)"), "تفريغ متغيرات البيئة"),
    (re.compile(r"\becho\b[^\n]*\$\{?" + _SECRET_NAMES), "طباعة قيمة توكن"),
    (re.compile(r"\b(cat|less|more|head|tail|grep|awk|sed|cut|sort|xxd|od|base64|strings|cp|mv|scp|rsync|curl|wget|tar|zip)\b[^\n|;&]*" + _ENV_FILE_RX.pattern),
     "قراءة/نقل ملف .env"),
    (re.compile(r"\bsource\s+[^\n;|&]*" + _ENV_FILE_RX.pattern), "تحميل .env في شل ظاهر"),
]


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
    for rx, why in _DANGEROUS_BASH:
        if rx.search(cmd):
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


async def _run_sdk_once(prompt: str, conv_key: str, timeout: int, on_progress=None) -> str:
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

    text = (final["result"] or "".join(parts) or "").strip()
    if not text:
        raise EngineError("SDK رجّع رد فاضي")
    return text


_RESUME_ERR_RX = re.compile(r"(no conversation|session).{0,40}(found|not found|expired)", re.IGNORECASE)


async def _run_sdk(prompt: str, conv_key: str, timeout: int, on_progress=None) -> str:
    try:
        return await _run_sdk_once(prompt, conv_key, timeout, on_progress)
    except EngineTimeout:
        raise
    except EngineError as error:
        msg = str(error)
        # جلسة قديمة/مفقودة → صفّرها وحاول مرة واحدة بجلسة جديدة
        if conv_key and _RESUME_ERR_RX.search(msg):
            print(f"HADI ENGINE: resume فشل — جلسة جديدة لـ {conv_key}")
            reset_session(conv_key)
            return await _run_sdk_once(prompt, conv_key, timeout, on_progress)
        if _is_transient(msg):
            print(f"HADI ENGINE: transient، محاولة تانية — {msg[-200:]}")
            await asyncio.sleep(5)
            return await _run_sdk_once(prompt, conv_key, timeout, on_progress)
        raise


# --- مسار الـ CLI (القديم كما هو — زرار الرجوع) -----------------------------
def _is_transient(message: str) -> bool:
    m = (message or "").lower()
    return any(s in m for s in (
        "server error", "overloaded", "api error", "internal server",
        "connection", "econnreset", "socket hang up", "rate limit",
    ))


def _run_cli_once(prompt: str, timeout: int) -> str:
    result = subprocess.run(
        [CLAUDE_BIN, "-p", prompt, "--model", MODEL],
        cwd=BASE_DIR,
        env=os.environ.copy(),
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
        time.sleep(5)
        try:
            return _run_cli_once(prompt, min(timeout, 300))
        except subprocess.TimeoutExpired:
            raise EngineTimeout(f"engine timeout بعد {timeout}s")


# --- الواجهة العامة ---------------------------------------------------------
async def run_agent(prompt: str, conv_key: str = "", timeout: int = 480, on_progress=None) -> str:
    """ينفّذ برومبت هادي ويرجّع نص الرد.

    conv_key: مفتاح المحادثة ("ch:<channel_id>" أو "dm:<user_id>") — بيفعّل
    استمرارية الجلسة في مسار الـ SDK. سيبه فاضي للمهام الخلفية (جلسة نظيفة).
    بيرمي EngineTimeout عند تعدي المهلة وEngineError لأي فشل تاني.
    """
    if _sem.locked():  # بند 3.4: قول للمستخدم إنه مستني دوره — مش «هنج»
        _emit(on_progress, "في الطابور العام — مستني تشغيلة تانية تخلص")
    async with _sem:
        if sdk_active():
            try:
                return await _run_sdk(prompt, conv_key, timeout, on_progress)
            except (EngineTimeout, EngineError):
                raise
            except CLINotFoundError as error:  # مفاجأة وقت تشغيل → جرّب مسار الـ CLI القديم
                print(f"HADI ENGINE: SDK مش لاقي الـ CLI ({error}) — تحويل لمسار cli")
                return await asyncio.to_thread(_run_cli_sync, prompt, timeout)
            except Exception as error:  # أي خطأ SDK غير متوقع → متبلعوش
                raise EngineError(f"{type(error).__name__}: {error}") from error
        return await asyncio.to_thread(_run_cli_sync, prompt, timeout)


async def run_oneshot(prompt: str, timeout: int = 300) -> str:
    """مهمة خلفية بجلسة نظيفة (من غير resume) — زي الـ pending flush."""
    return await run_agent(prompt, conv_key="", timeout=timeout)
