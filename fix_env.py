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

# قيمة محتاجة علامات لو فيها حاجة الشِل بتفسّرها.
# ' و " مقصودين: قيمة زي it's بتخلي bash تدوّر على علامة قافلة وتطلّع syntax
# error يبوّظ الملف كله مش السطر بس.
_NEEDS_QUOTING = re.compile(r"""[\s#&|;<>()$`\\!*?\[\]{}~'"]""")
# قيمة شكلها غلط في المعنى مش في الشكل: رقم طويل وبعده كلام
_SUSPECT_ID = re.compile(r"^\d{5,}\s+\S")
# bash بيقول رقم السطر في رسالة العطل: «.env: line 5: ...»
_BASH_LINE = re.compile(r":\s*line\s+(\d+):\s*(.*)$")


def bash_complaints(path):
    """(كود_الخروج, الرسالة_الخام, {رقم_السطر: الشكوى}) من `source` نفسها.

    bash هو المرجع مش تخميني: أي سطر هو بيشتكي منه لازم يتصلّح حتى لو
    الهيوريستيك بتاعتي شايفاه سليم. من غير ده السكربت ممكن يقول «مفيش أسطر
    محتاجة تصليح» بينما `source` لسه بتقع — وده اللي حصل فعلًا.
    """
    try:
        proc = subprocess.run(
            ["bash", "-c", f'source "{path}"'],
            capture_output=True, text=True, timeout=30, check=False)
    except Exception as error:
        return 1, f"{type(error).__name__}: {error}", {}
    err = (proc.stderr or "").strip()
    flagged = {}
    for line in err.splitlines():
        hit = _BASH_LINE.search(line)
        if hit:
            flagged[int(hit.group(1))] = hit.group(2).strip()
    return proc.returncode, err, flagged


def _quote(value):
    """بيحط القيمة بين علامات بحيث الشِل تقراها زي ما بايثون بيقراها دلوقتي."""
    if "'" not in value:
        return f"'{value}'"
    # فيها ' فبنستخدم " ونهرب اللي الشِل بتفسّره جوه العلامات المزدوجة
    escaped = re.sub(r'([$`"\\])', r"\\\1", value)
    return f'"{escaped}"'


def analyse(path, flagged=None):
    """(الأسطر_الجديدة, التغييرات, المشبوه) — من غير ما يكتب حاجة.

    flagged = أرقام الأسطر اللي bash اشتكى منها. أي سطر فيها بيتصلّح حتى لو
    الهيوريستيك شايفاه سليم.
    """
    flagged = flagged or {}
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    out, changes, suspect = [], [], []

    for i, raw in enumerate(lines, 1):
        s = raw.strip()
        # BOM في أول الملف بيخلي bash تشوف السطر أمر مش تعليق
        if i == 1:
            s = s.lstrip("﻿")

        # فاضي أو تعليق — سيبه، إلا لو bash نفسها بتشتكي منه
        if (not s or s.startswith("#")) and i not in flagged:
            out.append(raw.lstrip("﻿") if i == 1 else raw)
            continue

        parsed = env_loader.parse_line(s)

        # مش تعيين أصلًا: فتافيت أو تعليق ضايع منه #. بنعلّق عليه —
        # الشِل مش بتعمل منه متغير أصلًا، فالتعليق مابيضيّعش أي إعداد.
        if parsed is None:
            why = flagged.get(i, "مش تعيين صالح")
            out.append(f"# [اتعلّق آليًا — {why}] {s}")
            changes.append((i, s, f"اتعلّق ({why})"))
            continue

        key, value = parsed
        after_eq = s.split("=", 1)[1].strip()
        already_quoted = (len(after_eq) >= 2 and after_eq[0] == after_eq[-1]
                          and after_eq[0] in ("'", '"'))

        needs = _NEEDS_QUOTING.search(value) or (i in flagged)
        if already_quoted and i not in flagged:
            out.append(raw)
        elif needs:
            fixed = f"{key}={_quote(value)}"
            if fixed.strip() == s:
                out.append(raw)
            else:
                out.append(fixed)
                changes.append((i, s, fixed))
        else:
            out.append(raw)

        if _SUSPECT_ID.match(value):
            suspect.append((i, key, value))

    return out, changes, suspect


def selftest():
    """بيصلّح ملفات تجريبية ويتأكد إن `source` بقت نضيفة والقيم زي ما هي.

    النسخة الأولى من السكربت ده كانت بتقول «مفيش أسطر محتاجة تصليح» بينما
    `source` لسه بتقع — لأن الهيوريستيك كانت شايفة نفسها المرجع. الاختبار ده
    بيقفل الباب ده: المعيار الوحيد إن bash تسكت والقيم ماتتغيرش.
    """
    import tempfile
    ok = True
    cases = {
        "علامة مفردة جوه القيمة": "A=don't\nB=2\n",
        "قيمة فيها مسافة": "A=1179369466279235584 8orders-issues\nB=2\n",
        "سطر مش تعيين": "A=1\nقناة تايهة 8orders-issues\nB=2\n",
        "مسار فيه مسافة": r"A=0_Projects_Team\Support Team" + "\nB=2\n",
        "علامات مزدوجة سليمة": 'A="claude-opus-5"\nB=2\n',
        "export + تعليق جانبي": "export A=sdk\nB=22  # تعليق\n",
        "ملف نضيف أصلًا": "A=1\nB=2\n# تعليق\n",
        "علامة مزدوجة مفتوحة": 'A=he said "hi\nB=2\n',
        "BOM في أول الملف": "﻿# تعليق\nA=1\nB=2\n",
    }
    for label, body in cases.items():
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False,
                                         encoding="utf-8") as handle:
            handle.write(body)
            tmp = Path(handle.name)
        try:
            before = {k: v for _, k, v in env_loader.parse_file(tmp)}
            _, _, flagged = bash_complaints(tmp)
            new_lines, _, _ = analyse(tmp, flagged)
            tmp.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            rc, err, _ = bash_complaints(tmp)
            after = {k: v for _, k, v in env_loader.parse_file(tmp)}
            clean = (rc == 0 and not err)
            same = (before == after)
            good = clean and same
            ok = ok and good
            note = "" if good else (
                f"  [source={'نضيفة' if clean else 'واقعة'}"
                f" | القيم={'زي ما هي' if same else f'اتغيرت {before} → {after}'}]")
            print(("PASS  " if good else "FAIL  ") + label + note)
        finally:
            tmp.unlink(missing_ok=True)

    print("\n" + ("ALL PASS" if ok else "THERE ARE FAILURES"))
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description="تصليح أسطر .env التالفة")
    p.add_argument("--path", default=str(BASE / ".env"))
    p.add_argument("--write", action="store_true", help="اكتب فعلًا (الافتراضي معاينة)")
    p.add_argument("--selftest", action="store_true", help="اختبار على ملفات تجريبية")
    args = p.parse_args()

    if args.selftest:
        return selftest()

    path = Path(args.path)
    if not path.is_file():
        sys.exit(f"مفيش ملف: {path}")

    rc_before, err_before, flagged = bash_complaints(path)
    print(f"الملف: {path}")
    print(f"حالة `source` قبل: {'نضيفة' if rc_before == 0 and not err_before else 'فيها أخطاء'}")
    if err_before:
        print("\nرسالة bash بالنص (دي المرجع — أنا بصلّح اللي هو بيشتكي منه):")
        for line in err_before.splitlines()[:12]:
            print(f"   {line}")
        if flagged:
            print(f"\n   أرقام الأسطر اللي bash حددها: {sorted(flagged)}")
        else:
            print("\n   ⚠ bash مادّاش رقم سطر — العطل غالبًا علامة تنصيص مفتوحة")
            print("     بتخلي باقي الملف يتقرا غلط. شوف السطور المقترحة تحت.")

    before = {k: v for _, k, v in env_loader.parse_file(path)}
    new_lines, changes, suspect = analyse(path, flagged)

    if not changes:
        print("\nمفيش أسطر محتاجة تصليح.")
        if err_before:
            print("⚠ بس `source` لسه بتشتكي — يبقى العطل شكله مش متوقع.")
            print("  شغّل ده وابعتلي الناتج:")
            print(f"    bash -c 'source {path}' 2>&1 | head -20")
            print(f"    grep -nP '[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\ufeff]' {path}")
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

    rc_after, err_after, _ = bash_complaints(path)
    clean = (rc_after == 0 and not err_after)
    print(f"  `source` بعد: {'✓ نضيفة' if clean else '⚠ لسه فيها أخطاء'}")
    if err_after:
        for line in err_after.splitlines()[:8]:
            print(f"     {line}")

    if suspect:
        print("\n⚠ قيم شكلها غلط في المعنى (السكربت مابيلمسهاش — محتاجة قرار منك):")
        for num, key, value in suspect:
            print(f"  سطر {num}: {key} = {value!r}")
            print("     رقم طويل وبعده كلام — غالبًا التعليق ضايع منه #")

    return 0 if (clean and not lost and not moved) else 1


if __name__ == "__main__":
    sys.exit(main())
