#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حالة العملية (Process State) — المصدر الحي لنموذج شغل التيم (نقطة 3).

ليه موجود:
  التيم غيّر البروسيس: وقف الشغل على **بورد الاسبرنت**، وبقى الشغل الأساسي على
  **بورد السابورت** بمفهوم **كانبان**، والتفاصيل بتتطوّر حبة حبة. قبل كده هادي كان
  بيقرا iterations من ADO ويعتبرها «سبرنت جديد» ويكرّر السؤال في الـ DM — لأن
  مفيش مصدر دائم بيقوله «احنا مبقناش شغالين بالسبرنت». الملف ده هو المصدر الدائم.

بيستخدمه مين:
  - discord_bot.py: بيحقن `human_summary()` في سياق كل محادثة (هادي يبقى فاهم الوضع).
  - discord_bot.py / sprint_intake.py: بيوقفوا تنبيهات السبرنت طالما sprint_watch=false.
  - هادي أو آسر من المحادثة: `python3 process_state.py set ...` يثبّت أي تغيير عبر الجلسات.

القيم متخزّنة في process_state.json جنب الكود (قابلة للـ override بـ HADI_PROCESS_STATE).
"""
import argparse
import datetime
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = Path(os.environ.get("HADI_PROCESS_STATE", str(BASE_DIR / "process_state.json")))

# الوضع الافتراضي = الواقع الحالي (أغسطس 2026): كانبان على السابورت، الاسبرنت متوقف.
_DEFAULT = {
    "mode": "kanban",
    "sprint_watch": False,
    "boards": {
        "sprint": {"status": "paused",
                   "note": "وقفنا الشغل على بورد الاسبرنت مؤقتًا"},
        "support": {"status": "active", "flow": "kanban",
                    "note": "البورد الرئيسي دلوقتي — تدفق كانبان مستمر، والبروسيس بتتطوّر حبة حبة"},
        "cr": {"status": "active",
               "note": "بورد الـ Change Requests شغّال عادي"},
    },
    "updated": "2026-08-02",
    "updated_by": "آسر",
    "history": [],
}


def load() -> dict:
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("mode"):
            return data
    except (OSError, ValueError):
        pass
    return dict(_DEFAULT)


def save(data: dict) -> None:
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def mode() -> str:
    # override بيئي اختياري: HADI_PROCESS_MODE بيكسب على الملف
    return (os.environ.get("HADI_PROCESS_MODE") or load().get("mode") or "kanban").strip()


def sprint_watch_enabled() -> bool:
    """هل تنبيهات السبرنت شغّالة؟ الافتراضي لأ (كانبان). override بـ HADI_SPRINT_WATCH."""
    env = os.environ.get("HADI_SPRINT_WATCH")
    if env is not None:
        return env.strip().lower() in {"1", "on", "true", "yes"}
    return bool(load().get("sprint_watch", False))


def human_summary() -> str:
    """بلوك عربي مختصر بيتحقن في سياق هادي — عشان يفهم الوضع ويمشي بانسجام معاه."""
    d = load()
    b = d.get("boards", {})

    def _line(key, label):
        info = b.get(key) or {}
        st = info.get("status", "?")
        note = info.get("note", "")
        return f"  - بورد {label}: {st}" + (f" — {note}" if note else "")

    lines = [
        f"الوضع الحالي للعملية (المصدر: process_state.json — محدّث {d.get('updated','?')} "
        f"بواسطة {d.get('updated_by','?')}):",
        f"- النموذج: {d.get('mode','kanban')} (مش سبرنت).",
        _line("sprint", "الاسبرنت"),
        _line("support", "السابورت"),
        _line("cr", "الـ CR"),
    ]
    if not sprint_watch_enabled():
        lines.append(
            "- مفيش سيكونات سبرنت نشطة (Buz HL / Demos / Release Day / Planning) — "
            "متسألش عنها ومتفكّرش بمواعيدها ومتنبّهش بيها في الـ DM إلا لو آسر رجّع السبرنت صراحةً.")
    lines.append(
        "- البروسيس بتتطوّر تدريجيًا؛ لو آسر قال تغيير في الطريقة، ثبّته بـ "
        "`python3 process_state.py set ...` عشان تفضل فاكره عبر الجلسات.")
    return "\n".join(lines)


def _cli_set(args) -> None:
    d = load()
    changed = []
    if args.mode:
        d["mode"] = args.mode
        changed.append(f"mode={args.mode}")
    if args.sprint_watch is not None:
        d["sprint_watch"] = args.sprint_watch.strip().lower() in {"1", "on", "true", "yes"}
        changed.append(f"sprint_watch={d['sprint_watch']}")
    for spec in args.board or []:
        if "=" not in spec:
            continue
        name, status = spec.split("=", 1)
        name, status = name.strip(), status.strip()
        d.setdefault("boards", {}).setdefault(name, {})
        d["boards"][name]["status"] = status
        changed.append(f"board:{name}={status}")
    if args.note:
        # ملاحظة عامة على البورد المحدد أو على الحالة كلها
        if args.board and "=" in args.board[0]:
            nm = args.board[0].split("=", 1)[0].strip()
            d["boards"][nm]["note"] = args.note
        else:
            d["note"] = args.note
        changed.append("note")
    d["updated"] = datetime.date.today().isoformat()
    d["updated_by"] = args.by or d.get("updated_by", "هادي")
    d.setdefault("history", []).append({
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "by": d["updated_by"], "changed": changed, "note": args.note or "",
    })
    save(d)
    print("OK — اتحدّث:", ", ".join(changed) or "(مفيش تغيير)")
    print(human_summary())


def main() -> None:
    ap = argparse.ArgumentParser(description="حالة العملية (كانبان/سبرنت + البوردات)")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("show", help="اعرض الوضع الحالي")
    s = sub.add_parser("set", help="حدّث الوضع (يثبت عبر الجلسات)")
    s.add_argument("--mode", help="kanban / scrum / hybrid")
    s.add_argument("--sprint-watch", dest="sprint_watch",
                   help="on/off — تشغيل/إيقاف تنبيهات السبرنت في الـ DM")
    s.add_argument("--board", action="append",
                   help="name=status (مثال: support=active أو sprint=paused)")
    s.add_argument("--note", help="ملاحظة توضيحية")
    s.add_argument("--by", help="مين عمل التغيير")
    args = ap.parse_args()

    if args.cmd == "set":
        _cli_set(args)
    else:
        print(human_summary())


if __name__ == "__main__":
    main()
