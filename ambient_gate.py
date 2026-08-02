#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة الحضور الذكي (Ambient Presence Gate) — القرار الثلاثي للرسايل غير الموجهة لهادي.

المشكلة اللي بتحلها (نقطة 1 + F16 من الأوديت):
  - قبلها: كل رسالة ambient كانت بتشغّل subprocess موديل جديد بقرار ثنائي
    (REPLY/SILENT) من غير سياق — تكلفة لكل رسالة، ومفيش مسار "رياكشن من غير رد".
  - دلوقتي: pipeline من 3 طبقات:
      1) Pre-filter محلي حتمي (صفر تكلفة) بيستبعد الرسايل اللي مستحيل تستاهل تفاعل.
      2) قرار Haiku واحد بثلاث مخرجات: SILENT / REACT: <emoji> / REPLY —
         بياخد آخر رسايل القناة كسياق + قواعد الذكاء الاجتماعي.
      3) REPLY بس هو اللي بيوصل للموديل الكامل (المسار الحالي زي ما هو).

ضوابط التكرار (قرار آسر — "مش ديما"):
  - حد أقصى HADI_AMBIENT_REPLY_PER_HOUR ردود ambient لكل قناة في الساعة (افتراضي 4).
  - ملاحظة (نقطة 4): السقف ده بيتطبّق على الردود الـ ambient الباردة بس. ردود
    **استمرار المحادثة** (هادي اتكلم للتو) و**بلاغات المشاكل** بتتخطّاه عمدًا —
    البوت بيوجّهها للمحرك مباشرة من غير ما تعدّي هنا.
  - كولداون HADI_AMBIENT_REACT_COOLDOWN_S ثانية بين رياكشنين لنفس الشخص في نفس
    القناة (افتراضي 600 = 10 دقايق).
  - الافتراضي الدائم هو الصمت — البوابة بتتعامل fail-closed: أي خطأ/غموض = SILENT.

كل قرار بيتسجل JSONL في logs/ambient_gate.jsonl (بند 5.3 — غذاء الـ error analysis):
  ts / channel / author / stage (prefilter|gate) / decision / reason / latency_ms.

إيقاف/تشغيل من .env:
  HADI_AMBIENT=on (افتراضي) | reply_only (سلوك ما قبل الترقية) | off (تجاهل تام).
"""
import json
import os
import re
import time
from collections import deque
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "logs" / "ambient_gate.jsonl"

MODE = (os.getenv("HADI_AMBIENT", "on").strip().lower() or "on")
REPLY_PER_HOUR = max(0, int(os.getenv("HADI_AMBIENT_REPLY_PER_HOUR", "4") or "4"))
REACT_COOLDOWN_S = max(0, int(os.getenv("HADI_AMBIENT_REACT_COOLDOWN_S", "600") or "600"))
HISTORY_N = max(3, int(os.getenv("HADI_AMBIENT_HISTORY", "8") or "8"))
GATE_TIMEOUT_S = max(10, int(os.getenv("HADI_AMBIENT_GATE_TIMEOUT", "25") or "25"))

# الإيموجيز المسموحة للرياكشن الـ ambient — subset من ALLOWED_REACTIONS بتاعة البوت.
# (🫡/👋/🤔 مستبعدين: دول منطقيين للرسايل الموجهة لهادي، مش للتفاعل الاجتماعي الصامت.)
AMBIENT_EMOJIS = {
    "\U0001F64F",  # 🙏
    "\U0001F389",  # 🎉
    "✅",      # ✅
    "\U0001F604",  # 😄
    "⚡",      # ⚡
    "\U0001F4AA",  # 💪
    "\U0001F525",  # 🔥
    "❤️",  # ❤️
    "\U0001F622",  # 😢
    "\U0001F44D",  # 👍
}

# كلمات دالة بتخلي رسالة قصيرة تعدي للبوابة رغم قصرها (مشاكل/إنجازات/شكر/عاجل)
_SIGNAL_RX = re.compile(
    r"مشكل|عطل|واقع|وقع|باج|بايظ|مش شغال|مش راضي|فشل|خطأ|هنج|"
    r"خلص|اتحل|اتقفل|تسلم|شكر|مبروك|تهانينا|عاجل|ضروري|مستعجل|"
    r"bug|error|crash|fail|down|fixed|done|deploy|releas|congrat|thank|urgent|asap",
    re.IGNORECASE,
)

# منشنات/إيموجي مخصص/لينكات — بتتشال قبل قياس "هل في نص حقيقي"
_NOISE_RX = re.compile(r"<a?:\w+:\d+>|<@!?\d+>|<@&\d+>|<#\d+>|https?://\S+")
_LETTERS_RX = re.compile(r"[^\W\d_]+", re.UNICODE)

_REACT_LINE_RX = re.compile(r"^\s*REACT\s*:?\s*(\S{1,8})", re.IGNORECASE)


class _Limiter:
    """عدادات in-memory (عمر العملية) — كافية لأن الهدف منع الإزعاج مش محاسبة دقيقة."""

    def __init__(self):
        self._replies: dict = {}          # channel_id -> deque[timestamps]
        self._last_react: dict = {}       # (channel_id, author_id) -> timestamp

    def can_reply(self, channel_id) -> bool:
        if REPLY_PER_HOUR <= 0:
            return False
        dq = self._replies.get(channel_id)
        if not dq:
            return True
        now = time.time()
        while dq and now - dq[0] > 3600:
            dq.popleft()
        return len(dq) < REPLY_PER_HOUR

    def note_reply(self, channel_id) -> None:
        self._replies.setdefault(channel_id, deque()).append(time.time())

    def can_react(self, channel_id, author_id) -> bool:
        last = self._last_react.get((channel_id, author_id), 0.0)
        return (time.time() - last) >= REACT_COOLDOWN_S

    def note_react(self, channel_id, author_id) -> None:
        self._last_react[(channel_id, author_id)] = time.time()


_limiter = _Limiter()


def note_reply(channel_id) -> None:
    """بيتنادى من البوت بعد ما رد ambient يتبعت فعلًا — عشان العداد يبقى على الحقيقة."""
    _limiter.note_reply(channel_id)


def enabled() -> bool:
    return MODE != "off"


def legacy_reply_only() -> bool:
    return MODE == "reply_only"


def prefilter(content: str) -> tuple:
    """(verdict, reason) — verdict: 'consider' أو 'skip'. حتمي وصفري التكلفة."""
    t = (content or "").strip()
    if not t:
        return "skip", "empty"
    residue = _NOISE_RX.sub("", t)
    letters = "".join(_LETTERS_RX.findall(residue))
    if not letters:
        return "skip", "no-text"
    if len(letters) < 6 and not _SIGNAL_RX.search(t):
        return "skip", "too-short"
    return "consider", ""


def _build_prompt(content, author_name, channel_name, history_text, can_reply):
    reply_rule = (
        "- REPLY only if Hadi adds real, specific, professional value right now: "
        "a direct question Hadi can answer with data/tools, a clear bug/issue/blocker worth "
        "logging or analyzing, or misinformation Hadi can correct with facts."
        if can_reply
        else "- REPLY is NOT available right now (hourly budget used) — choose only SILENT or REACT."
    )
    # ترتيب cache-friendly: التعليمات الثابتة الأول، والسياق المتغير في الآخر.
    return f"""You are the ambient-presence gate for "Hadi Amin" (هادي أمين), a real, respected team member on the Hadaf/8Orders team Discord. The current message is NOT addressed to Hadi. Decide Hadi's social move.

Output EXACTLY one line and nothing else:
SILENT
REACT: <one emoji>
REPLY

Rules:
- Default is SILENT. Hadi is a calm senior colleague, not an eager bot. Most messages deserve silence.
{reply_rule}
- REACT only when a light social acknowledgment genuinely fits: big effort/achievement -> 💪 or 🔥, good news/congrats -> 🎉, thanks to the team -> 🙏, task finished/bug fixed -> ✅, genuinely funny -> 😄, sad news -> 😢, urgent call that needs eyes -> ⚡, warm/appreciative moment -> ❤️ or 👍.
- Allowed reaction emojis (nothing else): 🙏 🎉 ✅ 😄 ⚡ 💪 🔥 ❤️ 😢 👍
- React sparingly: not on routine status updates, not on every joke, and if the history shows Hadi already reacted or replied in this same thread of talk, prefer SILENT.
- Never combine REACT and REPLY. Never explain your choice.

Recent channel messages (oldest to newest, Hadi's own marked "هادي (أنت)"):
{history_text or "(no history)"}

Current message from {author_name} in #{channel_name}:
{content[:1500]}"""


def _parse(raw: str) -> tuple:
    """(action, emoji|None) — أي حاجة مش مفهومة = silent (fail-closed)."""
    first = (raw or "").strip().splitlines()[0].strip() if (raw or "").strip() else ""
    up = first.upper()
    if up.startswith("REPLY"):
        return "reply", None
    m = _REACT_LINE_RX.match(first)
    if m:
        emoji = m.group(1).strip()
        if emoji in AMBIENT_EMOJIS:
            return "react", emoji
        return "silent", None
    return "silent", None


def _log(row: dict) -> None:
    try:
        LOG_FILE.parent.mkdir(exist_ok=True)
        row.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass  # فشل اللوج عمره ما يوقف القرار


async def decide(hadi_engine, content, author_name, author_id, channel_id, channel_name,
                 history_text) -> tuple:
    """القرار الكامل لرسالة ambient. بيرجع (action, emoji|None).

    action: 'silent' | 'react' | 'reply'. الرياكشن بيتحسب على الكولداون هنا؛
    الرد بيتحسب على العداد بعد الإرسال الفعلي (note_reply من البوت)."""
    t0 = time.time()
    base = {"channel": str(channel_id), "channel_name": channel_name, "author": author_name}

    verdict, reason = prefilter(content)
    if verdict == "skip":
        _log({**base, "stage": "prefilter", "decision": "silent", "reason": reason,
              "latency_ms": 0})
        return "silent", None

    can_reply = _limiter.can_reply(channel_id)
    can_react = _limiter.can_react(channel_id, author_id)
    if not can_reply and not can_react:
        _log({**base, "stage": "budget", "decision": "silent", "reason": "limits-exhausted",
              "latency_ms": 0})
        return "silent", None

    if legacy_reply_only():
        prompt = (
            "You are the gate for Hadi, a senior product/ops assistant in a team Discord. "
            "Answer ONE word. REPLY only if Hadi can add clear specific professional value "
            "right now. SILENT otherwise. Message: " + (content or "")[:1500]
        )
        raw = await hadi_engine.ask_haiku(prompt, timeout=GATE_TIMEOUT_S, cwd="/tmp")
        action = "reply" if "REPLY" in (raw or "").upper() and can_reply else "silent"
        _log({**base, "stage": "gate", "decision": action, "reason": "legacy",
              "latency_ms": int((time.time() - t0) * 1000)})
        return action, None

    prompt = _build_prompt(content, author_name, channel_name, history_text, can_reply)
    raw = await hadi_engine.ask_haiku(prompt, timeout=GATE_TIMEOUT_S, cwd="/tmp")
    action, emoji = _parse(raw)

    reason = ""
    if action == "reply" and not can_reply:
        action, reason = "silent", "reply-budget"
    if action == "react":
        if not can_react:
            action, emoji, reason = "silent", None, "react-cooldown"
        else:
            _limiter.note_react(channel_id, author_id)

    _log({**base, "stage": "gate", "decision": action, "emoji": emoji or "",
          "reason": reason, "raw": (raw or "")[:60],
          "latency_ms": int((time.time() - t0) * 1000)})
    return action, emoji
