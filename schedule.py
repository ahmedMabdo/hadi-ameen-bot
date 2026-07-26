#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداة الجدولة/التذكير لهادي. بتسجّل فعل مستقبلي في reminders.json؛ الحلقة
الخلفية جوّه discord_bot.py بتفحص كل نص دقيقة وتنفّذه في ميعاده تلقائيًا.

الأنواع:
  reminder  -> DM لآسر (تذكيرات آسر الشخصية فقط)
  post      -> رسالة تتنشر في قناة (po|mars|issues|support|<channel_id>)
               مع --mention لعمل منشن لعضو معين وقت الإرسال (اسم أو user id)

قاعدة التوجيه: تذكير لشخص غير آسر أو "في قناة كذا" = post على القناة المعنية
مع --mention باسم الشخص — مش DM لصاحب الطلب.

أوامر:
  schedule.py add --at "2026-07-11 10:00" --type reminder --text "..." --requester "الاسم"
  schedule.py add --at "2026-07-11 09:00" --type post --target mars --text "..." --requester "الاسم"
  schedule.py list
  schedule.py cancel --id <id>

المواعيد بتوقيت القاهرة، وبتتخزن UTC epoch. لازم تأكيد صاحب الطلب قبل الجدولة
(القاعدة دي مسؤولية هادي، مش الأداة).
"""
import argparse
import datetime as dt
import json
import os
import sys
import uuid
from pathlib import Path
from zoneinfo import ZoneInfo

import state_lock  # بند 3.3 — تسلسل الكتابات المشتركة مع باقي أدوات الحالة

BASE = Path(__file__).resolve().parent
STORE = BASE / "reminders.json"
TZ = ZoneInfo("Africa/Cairo")

CHANNEL_ALIASES = {
    "po": os.environ.get("PO_CHANNEL_ID", "1358833733699899704"),
    "mars": os.environ.get("MARS_CHANNEL_ID", "1136668686044909761"),
    "issues": os.environ.get("ISSUES_CHANNEL_ID", "1179369466279235584"),
    "support": os.environ.get("ISSUES_CHANNEL_ID", "1179369466279235584"),
}


def _load():
    """بيقرا المخزن. الملف التالف بياخد نسخة **وبيتبلّغ** بدل ما يرجّع [] في صمت.

    2026-07-26: القراءة كانت `except Exception: return []` — يعني ملف تالف
    (من كتابة اتقطعت) = «مفيش تذكيرات» بصمت تام، وكل المجدول يضيع من غير ما
    حد يعرف. والكتابة كانت مباشرة مش ذرية، فالفساد كان ممكن أصلًا — بينما
    discord_bot._save_reminders و4 موديولات تانية كانوا بيعملوا tmp+replace صح.
    """
    if not STORE.exists():
        return []
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception as error:
        stamp = dt.datetime.now(TZ).strftime("%Y%m%d-%H%M%S")
        bad = STORE.with_suffix(f".json.corrupt-{stamp}")
        try:
            STORE.replace(bad)
            print(f"SCHEDULE ERROR: {STORE.name} تالف ({type(error).__name__}) — "
                  f"اتنقل لـ {bad.name}. المجدول اللي كان فيه محتاج مراجعة.",
                  file=sys.stderr)
        except OSError:
            print(f"SCHEDULE ERROR: {STORE.name} تالف ومقدرتش آخد نسخة",
                  file=sys.stderr)
        return []


def _save(items):
    """كتابة ذرية: tmp ثم replace — نفس نمط باقي الموديولات."""
    tmp = STORE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STORE)


def _parse_when(s):
    s = s.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            d = dt.datetime.strptime(s, fmt).replace(tzinfo=TZ)
            return d.astimezone(dt.timezone.utc).timestamp(), d
        except ValueError:
            continue
    sys.exit(f"ERROR: صيغة --at غلط '{s}'. استخدم 'YYYY-MM-DD HH:MM' بتوقيت القاهرة.")


def _resolve_target(args):
    if args.type == "reminder":
        return {"kind": "dm"}                       # DM لآسر (ALLOWED_USER_IDS)
    raw = (args.target or "po").strip().lower()
    cid = CHANNEL_ALIASES.get(raw, args.target.strip() if args.target else "")
    if not cid:
        sys.exit("ERROR: نوع post محتاج --target (po|mars|issues|channel_id).")
    return {"kind": "channel", "id": str(cid), "mention": (args.mention or "").strip()}


def cmd_add(args):
    at_epoch, at_dt = _parse_when(args.at)
    if at_epoch <= dt.datetime.now(dt.timezone.utc).timestamp():
        sys.exit("ERROR: الميعاد في الماضي — حدد وقت مستقبلي.")
    item = {
        "id": uuid.uuid4().hex[:8],
        "type": args.type,
        "at_epoch": at_epoch,
        "at_human": at_dt.strftime("%Y-%m-%d %H:%M") + " القاهرة",
        "target": _resolve_target(args),
        "text": args.text.strip(),
        "requester": (args.requester or "غير معروف").strip(),
        "created": dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M"),
        "fired": False,
        "attempts": 0,
    }
    items = _load()
    items.append(item)
    _save(items)
    tgt = "DM لآسر" if item["target"]["kind"] == "dm" else f"قناة {item['target']['id']}"
    if item["target"].get("mention"):
        tgt += f" + منشن {item['target']['mention']}"
    print(f"SCHEDULED #{item['id']} [{args.type}] → {tgt} @ {item['at_human']}")


def cmd_list(args):
    items = [i for i in _load() if not i.get("fired")]
    if not items:
        print("مفيش تذكيرات مجدولة.")
        return
    for i in sorted(items, key=lambda x: x["at_epoch"]):
        tgt = "DM" if i["target"]["kind"] == "dm" else f"#{i['target']['id']}"
        print(f"#{i['id']} [{i['type']}→{tgt}] @ {i['at_human']}: {i['text']}")


def cmd_cancel(args):
    items = _load()
    n = len(items)
    items = [i for i in items if i["id"] != args.id]
    _save(items)
    print(f"CANCELLED #{args.id}" if len(items) < n else f"مفيش تذكير بالـ id ده: {args.id}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="اجدول تذكير/رسالة")
    a.add_argument("--at", required=True, help="'YYYY-MM-DD HH:MM' بتوقيت القاهرة")
    a.add_argument("--type", required=True, choices=["reminder", "post"])
    a.add_argument("--target", help="للـ post: po|mars|issues|support|channel_id")
    a.add_argument("--mention", default="", help="للـ post: منشن عضو في القناة (اسم أو user id)")
    a.add_argument("--text", required=True)
    a.add_argument("--requester", default="")
    a.set_defaults(func=cmd_add)

    l = sub.add_parser("list", help="التذكيرات المجدولة")
    l.set_defaults(func=cmd_list)

    c = sub.add_parser("cancel", help="ألغِ تذكير بالـ id")
    c.add_argument("--id", required=True)
    c.set_defaults(func=cmd_cancel)

    args = p.parse_args()
    if args.cmd in ("add", "cancel"):
        # بند 3.3: كتابات reminders.json بتتسلسل في طابور الكتابة المشترك (flock)
        # مع reminder_loop جوه البوت وmemory.py — بدل أمل «مفيش تصادم».
        with state_lock.write_lock():
            args.func(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
