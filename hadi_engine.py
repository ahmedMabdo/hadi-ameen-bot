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
"""
import asyncio
import json
import os
import re
import subprocess
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
    data = _load_sessions()
    data[conv_key] = {"session_id": session_id, "ts": time.time()}
    _save_sessions(data)


def reset_session(conv_key: str) -> None:
    data = _load_sessions()
    if conv_key in data:
        data.pop(conv_key, None)
        _save_sessions(data)


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


# --- مسار الـ SDK ----------------------------------------------------------
def _sdk_options(resume_id):
    return ClaudeAgentOptions(
        model=MODEL,
        cwd=str(BASE_DIR),
        cli_path=CLAUDE_BIN if Path(CLAUDE_BIN).exists() else None,
        # نفس سلوك `claude -p` بالظبط: برومبت النظام القياسي + إعدادات وذاكرة المشروع
        system_prompt={"type": "preset", "preset": "claude_code"},
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


async def _run_sdk_once(prompt: str, conv_key: str, timeout: int) -> str:
    resume_id = _get_resume(conv_key)
    parts: list = []
    final: dict = {"result": None, "session_id": None, "cost": None, "duration": None}

    async def _consume():
        async for msg in query(prompt=prompt, options=_sdk_options(resume_id)):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
            elif isinstance(msg, ResultMessage):
                final["session_id"] = msg.session_id
                final["cost"] = msg.total_cost_usd
                final["duration"] = msg.duration_ms
                final["result"] = msg.result
                if msg.is_error:
                    raise EngineError(str(msg.result or msg.subtype or "SDK error")[:1500])

    try:
        await asyncio.wait_for(_consume(), timeout=timeout)
    except asyncio.TimeoutError:
        raise EngineTimeout(f"engine timeout بعد {timeout}s")

    if final["session_id"]:
        _remember_session(conv_key, final["session_id"])
    if final["cost"] is not None or final["duration"] is not None:
        print(f"HADI ENGINE: sdk done key={conv_key or '-'} "
              f"cost=${final['cost'] or 0:.4f} dur={(final['duration'] or 0)/1000:.0f}s "
              f"resume={'yes' if resume_id else 'new'}")

    text = (final["result"] or "".join(parts) or "").strip()
    if not text:
        raise EngineError("SDK رجّع رد فاضي")
    return text


_RESUME_ERR_RX = re.compile(r"(no conversation|session).{0,40}(found|not found|expired)", re.IGNORECASE)


async def _run_sdk(prompt: str, conv_key: str, timeout: int) -> str:
    try:
        return await _run_sdk_once(prompt, conv_key, timeout)
    except EngineTimeout:
        raise
    except EngineError as error:
        msg = str(error)
        # جلسة قديمة/مفقودة → صفّرها وحاول مرة واحدة بجلسة جديدة
        if conv_key and _RESUME_ERR_RX.search(msg):
            print(f"HADI ENGINE: resume فشل — جلسة جديدة لـ {conv_key}")
            reset_session(conv_key)
            return await _run_sdk_once(prompt, conv_key, timeout)
        if _is_transient(msg):
            print(f"HADI ENGINE: transient، محاولة تانية — {msg[-200:]}")
            await asyncio.sleep(5)
            return await _run_sdk_once(prompt, conv_key, timeout)
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
async def run_agent(prompt: str, conv_key: str = "", timeout: int = 480) -> str:
    """ينفّذ برومبت هادي ويرجّع نص الرد.

    conv_key: مفتاح المحادثة ("ch:<channel_id>" أو "dm:<user_id>") — بيفعّل
    استمرارية الجلسة في مسار الـ SDK. سيبه فاضي للمهام الخلفية (جلسة نظيفة).
    بيرمي EngineTimeout عند تعدي المهلة وEngineError لأي فشل تاني.
    """
    async with _sem:
        if sdk_active():
            try:
                return await _run_sdk(prompt, conv_key, timeout)
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
