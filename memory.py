#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداة الذاكرة الدائمة لهادي. بتضيف ملاحظات مؤرَّخة ومنسوبة لصاحبها في
knowledge/memory.md، وبتعمل commit + push (best-effort) عشان الذاكرة تبقى
دائمة وليها audit trail. البوت بيحمّل knowledge/memory.md مع كل محادثة،
فأي حاجة اتحفظت تبقى متاحة في كل القنوات.

أوامر:
  memory.py show
  memory.py add --section <decisions|sprint|notes|general> --text "..." --author "الاسم"
  memory.py search --query "..."

أي عضو في التيم يقدر يحفظ. كل سطر بيتسجّل: [التاريخ — مين] المعلومة.
"""
import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import state_lock  # بند 3.3 — تسلسل الكتابات المشتركة مع باقي أدوات الحالة

BASE = Path(__file__).resolve().parent
MEM = BASE / "knowledge" / "memory.md"
TZ = ZoneInfo("Africa/Cairo")

SECTIONS = {
    "decisions": "## قرارات",
    "sprint": "## سبرنت",
    "notes": "## ملاحظات",
    "general": "## عام",
}


def _now():
    return dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M")


def _ensure():
    if not MEM.exists():
        MEM.parent.mkdir(parents=True, exist_ok=True)
        body = ("# ذاكرة هادي الدائمة\n\n"
                "> ملف بيتحدّث آليًا عبر memory.py. كل سطر: [التاريخ — مين] المعلومة.\n"
                "> بيتحمّل مع كل محادثة، فهادي عارف اللي هنا في أي قناة.\n\n")
        for h in ("decisions", "sprint", "notes", "general"):
            body += SECTIONS[h] + "\n\n"
        MEM.write_text(body, encoding="utf-8")


def cmd_show(args):
    _ensure()
    print(MEM.read_text(encoding="utf-8"))


def cmd_add(args):
    _ensure()
    header = SECTIONS.get(args.section, SECTIONS["general"])
    author = (args.author or "غير معروف").strip()
    line = f"- [{_now()} — {author}] {args.text.strip()}\n"
    text = MEM.read_text(encoding="utf-8")

    if header in text:
        idx = text.index(header)
        nl = text.index("\n", idx) + 1          # بعد سطر العنوان
        while nl < len(text) and text[nl] == "\n":  # تخطّي السطر الفاضي
            nl += 1
        tail = text[nl:]
        sep = "\n" if tail.startswith("#") else ""  # سطر فاصل قبل العنوان اللي بعده
        text = text[:nl] + line + sep + tail
    else:
        text += f"\n{header}\n\n{line}"

    MEM.write_text(text, encoding="utf-8")
    print(f"SAVED [{args.section}]: {args.text.strip()}")
    _git_persist(f"memory: {args.section} note by {author}")


def cmd_search(args):
    _ensure()
    q = args.query.strip()
    hits = [l for l in MEM.read_text(encoding="utf-8").splitlines()
            if q.lower() in l.lower() and l.strip().startswith("-")]
    print("\n".join(hits) if hits else "مفيش نتيجة في الذاكرة.")


def _git_persist(msg):
    try:
        for cmd in (["add", str(MEM)], ["commit", "-m", msg]):
            subprocess.run(["git", "-C", str(BASE), *cmd],
                           check=True, capture_output=True, timeout=30)
        subprocess.run(["git", "-C", str(BASE), "push"],
                       check=True, capture_output=True, timeout=60)
        print("PERSISTED (committed + pushed)")
    except Exception as e:
        print(f"WARN: saved locally but git persist failed: {type(e).__name__} "
              "(الذاكرة محفوظة على القرص، هتتزامن مع أول push ناجح)")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="اطبع الذاكرة كلها")
    s.set_defaults(func=cmd_show)

    a = sub.add_parser("add", help="احفظ ملاحظة جديدة")
    a.add_argument("--section", default="general", choices=list(SECTIONS))
    a.add_argument("--text", required=True)
    a.add_argument("--author", default="")
    a.set_defaults(func=cmd_add)

    q = sub.add_parser("search", help="دوّر في الذاكرة")
    q.add_argument("--query", required=True)
    q.set_defaults(func=cmd_search)

    args = p.parse_args()
    if args.cmd == "add":
        # بند 3.3: الكتابة (memory.md + git commit/push) بتتسلسل في طابور كتابة
        # واحد (flock) مشترك مع schedule.py وreminder_loop — منع سباقات الملف
        # وتصادم git index.lock بين محادثتين متوازيتين.
        with state_lock.write_lock():
            args.func(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
