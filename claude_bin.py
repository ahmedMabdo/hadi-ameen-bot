#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تحديد مسار Claude Code CLI بشكل متين عبر البيئات (سيرفر / Docker / Dokploy).

المشكلة (حادثة 2026-08):
  `daily_digests.py` و `hadi_engine.py` كانوا بيستخدموا مسار ثابت
  `/home/ubuntu/.local/bin/claude` (سيرفر أوبونتو القديم). في كونتينر Dokploy
  المسار ده مش موجود، فالنداء المباشر للـ CLI في الملخصات اليومية بيرمي
  `FileNotFoundError` وبيفشل الملخص. المحرك الرئيسي كان بينجو لأنه بيمرّر
  `cli_path=None` للـ SDK اللي بيلاقي الـ CLI لوحده (وجواه نسخة مرفقة).

الحل:
  `resolve()` بيمشي بنفس منطق الـ claude-agent-sdk بالظبط:
    env(CLAUDE_BIN) → PATH → الـ CLI المرفق مع الـ SDK (_bundled/claude) →
    أماكن تثبيت شائعة → آخر حل: الاسم المجرد "claude" (اعتماد على PATH وقت التشغيل).
"""
import os
import shutil
from pathlib import Path

_cached: str | None = None


def resolve() -> str:
    """يرجّع مسار قابل للتنفيذ للـ claude CLI. بيتحسب مرة واحدة ويتكاش."""
    global _cached
    if _cached:
        return _cached

    # 1) override صريح من البيئة — بس لو المسار موجود فعلاً على القرص
    env = os.getenv("CLAUDE_BIN", "").strip()
    if env and Path(env).exists():
        _cached = env
        return _cached

    # 2) على الـ PATH
    found = shutil.which("claude")
    if found:
        _cached = found
        return _cached

    # 3) النسخة المرفقة مع claude-agent-sdk — دي اللي بتشتغل جوه الكونتينر
    try:
        import claude_agent_sdk as _sdk
        bundled = Path(_sdk.__file__).resolve().parent / "_bundled" / "claude"
        if bundled.exists():
            _cached = str(bundled)
            return _cached
    except Exception:
        pass

    # 4) أماكن تثبيت شائعة (زي ما الـ SDK بيدوّر)
    for p in (
        Path.home() / ".local/bin/claude",
        Path("/usr/local/bin/claude"),
        Path.home() / ".npm-global/bin/claude",
        Path.home() / "node_modules/.bin/claude",
        Path.home() / ".claude/local/claude",
    ):
        if p.exists():
            _cached = str(p)
            return _cached

    # 5) آخر حل — الاسم المجرد، يعتمد على PATH وقت التشغيل
    _cached = "claude"
    return _cached


if __name__ == "__main__":
    print(resolve())
