#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""قفل الكتابة المشترك (بند 3.3) — تسلسل كتابات الحالة المشتركة بين المحادثات المتوازية.

بعد فك القفل العالمي (الترحيل للـ Agent SDK)، محادثتين ممكن يكتبوا في نفس اللحظة على:
  - knowledge/memory.md + git commit/push  (memory.py — subprocess من جوه الجلسة)
  - reminders.json                         (schedule.py + reminder_loop جوه البوت)

قفل flock واحد (طابور كتابة واحد زي ما تقرير التحسينات محدد) بيمسك الحالتين:
  - بيشتغل بين العمليات المنفصلة (subprocesses) — اللي asyncio.Lock مش بيشوفها.
  - بيتفك أوتوماتيك لو العملية ماتت (مفيش قفل معلّق بعد أي crash).

الاستخدام:
    import state_lock
    with state_lock.write_lock():
        ...اقرأ-عدّل-اكتب...

المهلة: HADI_WRITE_LOCK_TIMEOUT ثانية (افتراضي 60) — بعدها TimeoutError صريح
بدل انتظار أبدي.
"""
import os
import time
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:  # منصة من غير flock — تعطيل آمن (مش حالة Ubuntu بتاعتنا)
    fcntl = None

BASE = Path(__file__).resolve().parent
LOCK_DIR = BASE / ".locks"
DEFAULT_TIMEOUT = float(os.environ.get("HADI_WRITE_LOCK_TIMEOUT", "60") or "60")


@contextmanager
def write_lock(name: str = "hadi-state", timeout: float | None = None):
    """قفل كتابة exclusive مشترك بين العمليات — blocking مع مهلة وpolling خفيف."""
    if fcntl is None:
        yield
        return
    wait = DEFAULT_TIMEOUT if timeout is None else timeout
    LOCK_DIR.mkdir(exist_ok=True)
    fd = os.open(LOCK_DIR / f"{name}.lock", os.O_CREAT | os.O_RDWR, 0o644)
    deadline = time.monotonic() + wait
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"write_lock({name!r}): القفل مشغول أكتر من {wait:g} ثانية — "
                        "في عملية كتابة تانية واقفة أو بطيئة")
                time.sleep(0.2)
        try:  # تشخيص: مين ماسك القفل (best-effort)
            os.ftruncate(fd, 0)
            os.write(fd, f"{os.getpid()} {time.strftime('%Y-%m-%d %H:%M:%S')}\n".encode())
        except OSError:
            pass
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
