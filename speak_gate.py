#!/usr/bin/env python3
"""
speak_gate.py - cheap "should Hadi speak?" gate (module B2).

Runs a lightweight decision over EVERY message in authorized channels: reply or
stay silent (NO_REPLY). Escalates to the main model only on real triggers, so
Hadi can watch everything 24/7 without spamming the channel or burning tokens.

Two layers:
  1) local heuristic pre-gate (free)  -> obvious yes / no
  2) optional Haiku check (cheap)     -> only for the "maybe" cases

Wire from discord_bot.on_message AFTER the existing hard gate (guild/channel
allowlist, name/mention/reply) and BEFORE building the full prompt:

    from speak_gate import decide
    d = decide(text,
               context={"mentioned": mentioned, "named": named,
                        "reply_to_hadi": replying_to_hadi},
               ask_fn=ask_haiku)          # ask_haiku(prompt)->str using your Haiku model
    if not d["reply"]:
        return                            # stay silent (no message sent)
"""
import os
import re
import json

TRIGGERS = [
    r"\bbug\b", r"\berror\b", r"مشكل", r"عطل", r"مش شغال", r"مش بيشتغل",
    r"blocked", r"متبلوك", r"deadline", r"معاد", r"urgent", r"مستعجل",
    r"\?", r"؟", r"help", r"محتاج", r"عايز", r"ليه", r"ازاي", r"إزاي",
    r"crash", r"down", r"واقع", r"refund", r"استرجاع", r"complaint", r"شكوى",
]
_TRIG_RE = re.compile("|".join(TRIGGERS), re.I)

_PROMPT = (
    "إنت فلتر بتقرر هادي (زميل في الشات) يرد ولا يسكت.\n"
    "رد بكلمة REPLY لو الرسالة فيها: مشكلة/باج، سؤال محتاج رد، قرار محتاج تيكت، "
    "بلوكر، أو طلب صريح ليه.\n"
    "رد بكلمة SILENT لو ونسة، كلام موجّه لناس تانيين، أو مفيش قيمة من رده.\n"
    "الرسالة:\n{msg}\n\nكلمة واحدة بس: REPLY أو SILENT."
)


def _heuristic(text, ctx):
    if ctx.get("mentioned") or ctx.get("named") or ctx.get("reply_to_hadi"):
        return True, "addressed to Hadi"
    t = (text or "").strip()
    if len(t) < 3:
        return False, "too short / noise"
    if _TRIG_RE.search(t):
        return None, "possible trigger -> escalate"
    return False, "no trigger"


def decide(text, context=None, ask_fn=None):
    ctx = context or {}
    hard, why = _heuristic(text, ctx)
    if hard is True:
        return {"reply": True, "reason": why, "via": "heuristic"}
    if hard is False:
        return {"reply": False, "reason": why, "via": "heuristic"}
    if ask_fn is None:
        return {"reply": True, "reason": "no ask_fn; safe default on trigger", "via": "heuristic"}
    try:
        ans = (ask_fn(_PROMPT.format(msg=(text or "")[:1500])) or "").strip().upper()
        return {"reply": ans.startswith("REPLY"), "reason": f"haiku:{ans[:12]}", "via": "haiku"}
    except Exception as e:  # noqa
        return {"reply": True, "reason": f"haiku error -> default reply: {e}", "via": "error"}


if __name__ == "__main__":
    import sys
    txt = " ".join(sys.argv[1:]) or "الوضع هادي النهاردة"
    print(json.dumps(decide(txt, {}), ensure_ascii=False))
