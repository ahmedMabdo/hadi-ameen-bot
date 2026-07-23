#!/usr/bin/env python3
"""
sprints_sync.py - auto-generate knowledge/sprints.md from the ADO snapshot (C9).

Replaces the hand-maintained sprints.md. Run after each snapshot refresh (or on a
timer). Ceremony times (planning/refinement/review/retro) are NOT in ADO; they are
kept in sprint_ceremonies.json (filled by sprint_intake.py / C10 from Asser's DM)
and merged in here. Everything else comes from the live snapshot.

Usage: python sprints_sync.py write [--path knowledge/sprints.md]
"""
import os
import sys
import json
import argparse
import datetime

import ado_snapshot as snap

CEREMONIES_PATH = os.environ.get(
    "ADO_CEREMONIES_JSON",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprint_ceremonies.json"),
)


def _tops(con, tag=None):
    rows = snap._rows(con, "is_top=1")
    if tag:
        rows = [r for r in rows if any(t.lower() == tag.lower() for t in snap._tags_list(r["tags"]))]
    return rows


def _fmt(rows):
    if not rows:
        return "- (لا يوجد)\n"
    return "".join(f"- #{r['id']} — {r['title']} _({r['state']})_\n" for r in rows)


def build(con):
    m = snap._meta(con)
    fr = snap.freshness(con)
    name = m.get("sprint_name", "?")
    start = (m.get("sprint_start") or "")[:10]
    finish = (m.get("sprint_finish") or "")[:10]

    cer = {}
    if os.path.exists(CEREMONIES_PATH):
        try:
            cer = json.load(open(CEREMONIES_PATH, encoding="utf-8")).get(name, {})
        except Exception:
            cer = {}

    off = []
    for c in con.execute("SELECT * FROM capacity"):
        for d in json.loads(c["days_off"] or "[]"):
            off.append(f"- {c['member']}: {(d.get('start') or '')[:10]} → {(d.get('end') or '')[:10]}")

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
    out = []
    out.append(f"# ذاكرة السبرنت — {name}\n")
    out.append("> ⚙️ الملف ده بيتولّد أوتوماتيك من ADO بواسطة `sprints_sync.py`. **ما تعدّلوش بالإيد.**")
    out.append(f"> آخر تحديث: {now} — نضارة: {fr['emoji']} {fr['label']}\n")
    out.append(f"## المواعيد\n- بداية: {start}\n- نهاية: {finish}\n")
    out.append("## الإيفنتات (من DM آسر)")
    if cer:
        out.append("\n".join(f"- {k}: {v}" for k, v in cer.items()) + "\n")
    else:
        out.append("- (لسه) — هادي هيسأل آسر عليها في DM أول السبرنت.\n")
    out.append("## إجازات مجدولة (من Capacity)\n" + ("\n".join(off) if off else "- (لا يوجد)") + "\n")
    out.append("## ستوريز master\n" + _fmt(_tops(con, "master")))
    out.append("## ستوريز Feature Management (FM)\n" + _fmt(_tops(con, "FM")))
    out.append("## شغل غير مخطّط (up)\n" + _fmt(_tops(con, "up")))
    return "\n".join(out) + "\n"


def main():
    p = argparse.ArgumentParser(description="Generate knowledge/sprints.md from the ADO snapshot.")
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--path", default=os.environ.get(
        "ADO_SPRINTS_MD",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge", "sprints.md")))
    a = p.parse_args()

    con = snap._db()
    snap._init(con)
    try:
        content = build(con)
    finally:
        con.close()

    os.makedirs(os.path.dirname(a.path), exist_ok=True)
    with open(a.path, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", a.path, f"({len(content)} chars)")


if __name__ == "__main__":
    main()
