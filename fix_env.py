#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_env.py — بيصلّح أسطر .env اللي `source` بتقع فيها، من غير ما يغيّر أي قيمة.

المشكلة: `source .env` بينفّذ كل سطر كأمر شِل. سطر زي

    ISSUES_CHANNEL_ID=1179369466279235584 8orders-issues

الشِل بتقراه «حط ISSUES_CHANNEL_ID مؤقتًا وشغّل الأمر 8orders-issues» — فبتطلّع
«8orders-issues: command not found» مع كل source.

الإصلاح: العلامات. القيمة بتتحط بين ' ' فالشِل بتاخدها كلها كقيمة واحدة.

الضمان المهم: **مفيش قيمة بتتغير**. الكود بيقرا القيمة دلوقتي بالمسافة اللي
جوّاها، وبعد التصليح بيقراها بنفس الشكل بالظبط (env_loader بيشيل العلامات).
يعني البوت مش هيلاحظ فرق — بس الشِل هتبطل زن.

بس ده بيصلّح الشكل مش المعنى: لو القيمة نفسها غلط (رقم قناة ملزوق بيه كلام)،
السكربت بيقولك عليها ومابيخمّنش الصح.

    python3 fix_env.py            # معاينة بس — مابيكتبش حاجة
    python3 fix_env.py --write    # بياخد نسخة احتياطية وبيصلّح
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import datetime as dt
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import env_loader  # noqa: E402

# قيمة محتاجة علامات لو فيها حاجة الشِل بتفسّرها
_NEEDS_QUOTING = re.compile(r"[\s#&|;<>()$`\\!*?\[\]{}~]")
# قيمة شكلها غلط في المعنى مش في الشكل: رقم طويل وبعده كلام
_SUSPECT_ID = re.compile(r"^\d{5,}\s+\S")


def _quote(value):
    """بيحط القيمة بين علامات بحيث الشِل تقراها زي ما بايثون بيقراها دلوقتي."""
    if "'" not in value:
        return f"'{value}'"
    # فيها ' فبنستخدم " ونهرب اللي الشِل بتفسّره جوه العلامات المزدوجة
    escaped = re.sub(r'([$`"\\])', r"\\\1", value)
    return f'"{escaped}"'


def analyse(path):
    """(الأسطر_الجديدة, التغييرات, المشبوه) — من غير ما يكتب حاجة."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    out, changes, suspect = [], [], []

    for i, raw in enumerate(lines, 1):
        s = raw.strip()

        # فاضي أو تعليق — سيبه
        if not s or s.startswith("#"):
            out.append(raw)
            continue

        parsed = env_loader.parse_line(raw)

        # مش تعيين أصلًا: فتافيت أو تعليق ضايع منه #. بنعلّق عليه —
        # الشِل مش بتعمل منه متغير أصلًا، فالتعليق مابيضيّعش أي إعداد.
        if parsed is None:
            out.append(f"# [اتعلّق آليًا — مكانش تعيين صالح] {s}")
            changes.append((i, s, "اتعلّق (مش تعيين صالح)"))
            continue

        key, value = parsed
        after_eq = s.split("=", 1)[1].strip()
        already_quoted = (len(after_eq) >= 2 and after_eq[0] == after_eq[-1]
                          and after_eq[0] in ("'", '"'))

        if already_quoted or not _NEEDS_QUOTING.search(value):
            out.append(raw)
        else:
            fixed = f"{key}={_quote(value)}"
            out.append(fixed)
            changes.append((i, s, fixed))

        if _SUSPECT_ID.match(value):
            suspect.append((i, key, value))

    return out, changes, suspect


def verify(path):
    """بيتأكد إن `source` بقت نضيفة فعلًا."""
    try:
        proc = subprocess.run(
            ["bash", "-c", f'set -e; source "{path}" >/dev/null 2>&1; echo CLEAN'],
            capture_output=True, text=True, timeout=30, check=False)
        return "CLEAN" in (proc.stdout or ""), (proc.stderr or "").strip()
    except Exception as error:
        return False, f"{type(error).__name__}: {error}"


def main():
    p = argparse.ArgumentParser(description="تصليح أسطر .env التالفة")
    p.add_argument("--path", default=str(BASE / ".env"))
    p.add_argument("--write", action="store_true", help="اكتب فعلًا (الافتراضي معاينة)")
    args = p.parse_args()

    path = Path(args.path)
    if not path.is_file():
        sys.exit(f"مفيش ملف: {path}")

    ok_before, err_before = verify(path)
    print(f"الملف: {path}")
    print(f"حالة `source` قبل: {'نضيفة' if ok_before else 'فيها أخطاء'}")
    if err_before:
        for line in err_before.splitlines()[:6]:
            print(f"   {line}")

    before = {k: v for _, k, v in env_loader.parse_file(path)}
    new_lines, changes, suspect = analyse(path)

    if not changes:
        print("\nمفيش أسطر محتاجة تصليح.")
    else:
        print(f"\n{len(changes)} سطر محتاج تصليح:\n")
        for num, old, new in changes:
            print(f"  سطر {num}:")
            print(f"    قبل:  {old}")
            print(f"    بعد:  {new}")

    if not args.write:
        print("\n(معاينة بس — مااتكتبش حاجة. ضيف --write عشان يتصلّح)")
        return 0

    if changes:
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_suffix(f".bak-{stamp}")
        shutil.copy2(path, backup)
        os.chmod(backup, 0o600)
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        os.chmod(path, 0o600)
        print(f"\nاتصلّح. نسخة احتياطية: {backup}")

    # الضمان: مفيش قيمة اتغيرت
    after = {k: v for _, k, v in env_loader.parse_file(path)}
    lost = sorted(set(before) - set(after))
    moved = sorted(k for k in set(before) & set(after) if before[k] != after[k])
    print("\nالتحقق:")
    print(f"  متغيرات قبل: {len(before)} | بعد: {len(after)}")
    if lost:
        print(f"  ⚠ ضاع: {lost}")
    if moved:
        print(f"  ⚠ اتغيرت قيمته: {moved}")
    if not lost and not moved:
        print("  ✓ كل القيم زي ما هي بالظبط")

    ok_after, err_after = verify(path)
    print(f"  `source` بعد: {'✓ نضيفة' if ok_after else '⚠ لسه فيها أخطاء'}")
    if err_after:
        for line in err_after.splitlines()[:6]:
            print(f"     {line}")

    if suspect:
        print("\n⚠ قيم شكلها غلط في المعنى (السكربت مابيلمسهاش — محتاجة قرار منك):")
        for num, key, value in suspect:
            print(f"  سطر {num}: {key} = {value!r}")
            print("     رقم طويل وبعده كلام — غالبًا التعليق ضايع منه #")

    return 0 if (ok_after and not lost and not moved) else 1


if __name__ == "__main__":
    sys.exit(main())
