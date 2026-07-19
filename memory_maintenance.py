#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""صيانة ذاكرة هادي الشهرية (بند 4.2 — مرحلة ج): يلخّص ذاكرته بنفسه، بمراجعة بشرية.

الفكرة من التقرير: «مهمة شهرية يلخص فيها هادي ذاكرته بنفسه: يؤرشف المنتهي،
يدمج المكرر، ويرفع اقتراح للمراجعة — دي حلقة self-improvement بضوابط».

الضوابط المطبَّقة هنا (مهمة):
  - الافتراضي **dry-run**: بيطبع اقتراح بس، مايكتبش أي حاجة.
  - **مفيش حذف نهائي أبدًا**: --apply بينقل السطور لـ knowledge/memory_archive.md
    (مع سبب وتاريخ) ويشيلها من memory.md — والاتنين في git، فالتراجع commit واحد.
  - --apply محتاج --yes صراحة، وبيرفض يشتغل لو في تعديلات غير محفوظة على memory.md.
  - كل الكتابات جوه قفل الكتابة المشترك (بند 3.3).

الكشف:
  expired    ملاحظة episodic عدّى تاريخ صلاحيتها  → أرشفة (مش بتتحقن أصلًا بعد تاريخها)
  duplicate  ملاحظتين متشابهين ≥ عتبة التشابه في نفس القسم → الأقدم للأرشيف
  superseded تشابه موضوع عالي + الأحدث بيناقض/بيحدّث الأقدم → اقتراح مراجعة بشرية (مش أوتوماتيك)

الاستخدام:
    memory_maintenance.py review                     # اقتراح على الشاشة (dry-run)
    memory_maintenance.py review --write-report      # + تقرير في knowledge/
    memory_maintenance.py apply --yes                # ينفّذ الأرشفة (expired + duplicate بس)
"""
import argparse
import datetime as dt
import difflib
import re
import subprocess
import sys
from pathlib import Path

import state_lock  # بند 3.3

BASE = Path(__file__).resolve().parent
MEM = BASE / "knowledge" / "memory.md"
ARCHIVE = BASE / "knowledge" / "memory_archive.md"

SIM_THRESHOLD = 0.78   # تشابه نصي فوقه = مكرر
SUPERSEDE_MIN = 0.55   # تشابه موضوع فوقه (وتحت عتبة التكرار) = يستاهل مراجعة

try:
    from memory_store import normalize, parse_line, SECTION_HEADERS, SECTION_LABELS
except Exception as error:  # pragma: no cover
    sys.exit(f"memory_maintenance محتاج memory_store.py جنبه: {error}")


def load_notes():
    """كل ملاحظة مع رقم سطرها في memory.md."""
    if not MEM.exists():
        sys.exit(f"مفيش ملف ذاكرة: {MEM}")
    notes, section = [], "general"
    for lineno, raw in enumerate(MEM.read_text(encoding="utf-8").splitlines()):
        stripped = raw.strip()
        if stripped in SECTION_HEADERS:
            section = SECTION_HEADERS[stripped]
            continue
        note = parse_line(raw, section)
        if note:
            note["lineno"] = lineno
            notes.append(note)
    return notes


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def analyse(notes, today=None):
    today = today or dt.date.today()
    expired, duplicates, superseded = [], [], []

    for note in notes:
        if note["expires"]:
            try:
                if dt.date.fromisoformat(note["expires"]) < today:
                    expired.append(note)
            except ValueError:
                pass

    expired_ids = {id(n) for n in expired}
    remaining = [n for n in notes if id(n) not in expired_ids]

    for i, a in enumerate(remaining):
        for b in remaining[i + 1:]:
            if a["section"] != b["section"]:
                continue
            ratio = similarity(a["body"], b["body"])
            if ratio >= SIM_THRESHOLD:
                older, newer = sorted((a, b), key=lambda n: n["noted_at"])
                duplicates.append({"drop": older, "keep": newer, "ratio": ratio})
            elif ratio >= SUPERSEDE_MIN:
                older, newer = sorted((a, b), key=lambda n: n["noted_at"])
                superseded.append({"older": older, "newer": newer, "ratio": ratio})

    seen = set()
    unique_dups = []
    for d in duplicates:
        key = d["drop"]["raw"]
        if key not in seen:
            seen.add(key)
            unique_dups.append(d)
    return {"expired": expired, "duplicates": unique_dups, "superseded": superseded}


def build_report(notes, findings) -> str:
    today = dt.date.today().isoformat()
    lines = [
        f"# اقتراح صيانة ذاكرة هادي — {today}",
        "",
        f"> مولَّد آليًا بـ `memory_maintenance.py` (بند 4.2 مرحلة ج). **اقتراح للمراجعة البشرية** —",
        "> مفيش حاجة اتنفذت. للتنفيذ: `python3 memory_maintenance.py apply --yes`",
        "> (بينقل المنتهي والمكرر للأرشيف — مفيش حذف نهائي، وكله في git).",
        "",
        f"**الوضع:** {len(notes)} ملاحظة | منتهية: {len(findings['expired'])} | "
        f"مكررة: {len(findings['duplicates'])} | محتاجة مراجعة: {len(findings['superseded'])}",
        "",
    ]

    lines += ["## 1) منتهية الصلاحية — تتأرشف", ""]
    if findings["expired"]:
        for n in findings["expired"]:
            lines.append(f"- انتهت `{n['expires']}` — {n['body'][:160]}")
    else:
        lines.append("- مفيش.")

    lines += ["", "## 2) مكررة — الأقدم يتأرشف والأحدث يفضل", ""]
    if findings["duplicates"]:
        for d in findings["duplicates"]:
            lines.append(f"- تشابه {d['ratio']:.0%}:")
            lines.append(f"  - **يفضل** [{d['keep']['noted_at']}] {d['keep']['body'][:120]}")
            lines.append(f"  - **يتأرشف** [{d['drop']['noted_at']}] {d['drop']['body'][:120]}")
    else:
        lines.append("- مفيش.")

    lines += ["", "## 3) محتاجة قرار بشري (تحديث محتمل — مش بيتنفذ آليًا)", ""]
    if findings["superseded"]:
        for s in findings["superseded"][:15]:
            lines.append(f"- تشابه موضوع {s['ratio']:.0%} — يتراجع يدوي:")
            lines.append(f"  - الأقدم [{s['older']['noted_at']}] {s['older']['body'][:110]}")
            lines.append(f"  - الأحدث [{s['newer']['noted_at']}] {s['newer']['body'][:110]}")
    else:
        lines.append("- مفيش.")

    lines += [
        "",
        "## ملاحظات للمراجع",
        "",
        "- الملاحظات اللي المفروض تنتهي بتاريخ معروف وسّمها: "
        "`memory.py add --expires YYYY-MM-DD ...` — بتسقط من البرومبت لوحدها بعد تاريخها.",
        "- قواعد السلوك المتعلمة وسّمها `--type procedural` — بتتحقن دايمًا.",
        "",
    ]
    return "\n".join(lines)


def _git(*args, check=True):
    return subprocess.run(["git", "-C", str(BASE), *args],
                          capture_output=True, text=True, check=check, timeout=60)


def apply_changes(findings) -> int:
    """أرشفة المنتهي والمكرر — مفيش حذف: السطور بتتنقل لـ memory_archive.md."""
    to_archive = [(n, "منتهية الصلاحية") for n in findings["expired"]]
    to_archive += [(d["drop"], f"مكررة (تشابه {d['ratio']:.0%}) — الأحدث اتساب")
                   for d in findings["duplicates"]]
    if not to_archive:
        print("مفيش حاجة تتأرشف — الذاكرة نضيفة.")
        return 0

    dirty = _git("status", "--porcelain", "--", str(MEM)).stdout.strip()
    if dirty:
        sys.exit("ERROR: في تعديلات غير محفوظة على memory.md — اعمل commit الأول عشان التراجع يفضل ممكن.")

    with state_lock.write_lock():
        text = MEM.read_text(encoding="utf-8")
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        archived = []
        for note, reason in to_archive:
            line = note["raw"]
            if line + "\n" in text:
                text = text.replace(line + "\n", "", 1)
                archived.append(f"- [{stamp} — أرشفة آلية: {reason}] {line[2:]}")
        if not archived:
            print("مفيش سطر اتطابق (الملف اتغير؟) — مفيش أي تعديل.")
            return 0
        MEM.write_text(text, encoding="utf-8")

        header = "" if ARCHIVE.exists() else (
            "# أرشيف ذاكرة هادي\n\n"
            "> سطور اتشالت من memory.md بصيانة `memory_maintenance.py` — محفوظة هنا للرجوع،\n"
            "> ومش بتتحقن في البرومبت. التراجع: انقل السطر تاني لـ memory.md.\n\n"
        )
        with ARCHIVE.open("a", encoding="utf-8") as f:
            if header:
                f.write(header)
            f.write(f"\n## دورة {stamp}\n\n" + "\n".join(archived) + "\n")

        try:
            import memory_store
            memory_store.rebuild()
        except Exception as error:
            print(f"WARN: إعادة بناء الفهرس فشلت ({type(error).__name__}) — شغّل memory_store.py rebuild")

        try:
            _git("add", str(MEM), str(ARCHIVE))
            _git("commit", "-m", f"memory: monthly maintenance — archived {len(archived)} note(s)")
            _git("push", check=False)
            print("PERSISTED (committed + pushed)")
        except Exception as error:
            print(f"WARN: git فشل ({type(error).__name__}) — التعديل محفوظ محليًا")

    print(f"ARCHIVED: {len(archived)} ملاحظة → {ARCHIVE.name}")
    return len(archived)


def main():
    parser = argparse.ArgumentParser(description="صيانة ذاكرة هادي الشهرية (بند 4.2 مرحلة ج)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("review", help="اقتراح للمراجعة — مايكتبش حاجة")
    r.add_argument("--write-report", action="store_true", help="يحفظ التقرير في knowledge/")
    a = sub.add_parser("apply", help="ينفّذ الأرشفة (منتهي + مكرر بس)")
    a.add_argument("--yes", action="store_true", required=False)
    args = parser.parse_args()

    notes = load_notes()
    findings = analyse(notes)
    report = build_report(notes, findings)

    if args.cmd == "review":
        print(report)
        if args.write_report:
            out = BASE / "knowledge" / f"memory_review_{dt.date.today():%Y_%m}.md"
            out.write_text(report, encoding="utf-8")
            print(f"\nREPORT: {out}")
    else:
        if not args.yes:
            sys.exit("ERROR: apply محتاج --yes صراحة. شوف الاقتراح الأول: memory_maintenance.py review")
        print(report)
        print("\n--- تنفيذ ---")
        apply_changes(findings)


if __name__ == "__main__":
    main()
