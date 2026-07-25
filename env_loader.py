#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""env_loader.py — قراءة .env بنفس دلالات `source` بالظبط.

كان في تلات نسخ يدوية من `_load_dotenv` (ado_client، ado_features،
intel/discord_delivery) وكلها بتعمل `split("=", 1)` وخلاص. الپارسر البسيط ده
بيختلف عن الشِل في تلات حاجات، وكل واحدة فيهم بتطلّع قيمة غلط في صمت:

    FOO="123"          الشِل بيدي 123        اليدوي كان بيدي "123" بالعلامتين
    FOO=123  # تعليق   الشِل بيدي 123        اليدوي كان بيدي "123  # تعليق"
    export FOO=123     الشِل بيدي FOO=123    اليدوي كان بيعمل متغير اسمه "export FOO"

النتيجة العملية: أي حد بيحاول ينضّف .env عشان `source` تبقى نضيفة (بإضافة
quotes مثلًا) كان بيبوّظ الپايثون من غير ما ياخد باله — الكود بياخد القيمة
بعلاماتها ويفشل بصمت في المقارنات و int().

الوحدة دي بتوحّد السلوك: `source .env` والكود بيقروا نفس القيم بالظبط.

الاختبار: python3 env_loader.py
"""
import os
import re
import sys

# اسم المتغير زي ما الشِل بيقبله: حرف أو _ في الأول، وبعدين حروف/أرقام/_
_KEY_RX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_line(line):
    """(key, value) من سطر .env — أو None لو السطر مش تعيين صالح.

    None معناها «الشِل مش هيعمل من ده متغير»: سطر فاضي، تعليق، فتافيت، أو
    اسم متغير ممنوع (زي اللي بيبدأ برقم أو فيه شرطة).
    """
    s = (line or "").strip()
    if not s or s.startswith("#"):
        return None
    if s.startswith("export "):
        s = s[len("export "):].lstrip()
    if "=" not in s:
        return None
    key, value = s.split("=", 1)
    key = key.strip()
    if not _KEY_RX.match(key):
        return None
    value = value.strip()
    # قيمة بين علامتين متطابقتين: بتتاخد كما هي والتعليق مابيتقصّش من جوّاها
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return key, value[1:-1]
    # قيمة من غير علامات: التعليق بيبدأ من أول # مسبوق بمسافة (زي الشِل).
    # «#» ملزوقة في نص القيمة مش تعليق — FOO=a#b قيمتها a#b.
    hit = re.search(r"\s#", value)
    if hit:
        value = value[:hit.start()]
    return key, value.strip()


def parse_file(path):
    """[(رقم_السطر, key, value)] لكل تعيين صالح في الملف."""
    out = []
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return out
    for i, line in enumerate(lines, 1):
        got = parse_line(line)
        if got:
            out.append((i, got[0], got[1]))
    return out


def bad_lines(path):
    """[(رقم_السطر, النص)] للأسطر اللي `source` هتقع فيها.

    يعني: مش فاضية، مش تعليق، ومش تعيين صالح. دي اللي بتطلّع
    «command not found» مع كل source.
    """
    out = []
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return out
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if parse_line(line) is None:
            out.append((i, line.rstrip("\n")))
    return out


def load_dotenv(path, override=False):
    """بيحمّل .env في os.environ. بيرجّع عدد المتغيرات اللي اتحطت.

    override=False (الافتراضي): بيئة العملية أقوى من الملف — عشان تقدر تجرّب
    قيمة مؤقتة بـ `VAR=x python3 ...` من غير ما تعدّل الملف.

    مابيرميش أبدًا: ملف ناقص أو تالف بيرجّع 0 والكود بيكمّل بالافتراضيات.
    """
    if not os.path.isfile(path):
        return 0
    count = 0
    for _, key, value in parse_file(path):
        if override:
            os.environ[key] = value
        elif key not in os.environ:
            os.environ[key] = value
        else:
            continue
        count += 1
    return count


def load_for(module_file, override=False):
    """بيحمّل .env اللي جنب الموديول، وبعدين اللي في الفولدر الأب.

    الفولدر الأب مهم لـ intel/: الملفات هناك كانت بتدوّر على intel/.env بس
    وماكانتش بتلاقي .env بتاع الريبو أبدًا.
    """
    here = os.path.dirname(os.path.abspath(module_file))
    total = load_dotenv(os.path.join(here, ".env"), override)
    parent = os.path.dirname(here)
    if parent and parent != here:
        total += load_dotenv(os.path.join(parent, ".env"), override)
    return total


def selftest():
    ok = True

    def check(label, cond):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + label)
        ok = ok and bool(cond)

    check("تعيين عادي", parse_line("FOO=123") == ("FOO", "123"))
    check("مسافات حوالين =", parse_line("  FOO = 123  ") == ("FOO", "123"))
    check("قيمة فيها مسافة بتتاخد كاملة",
          parse_line(r"AREA=0_Projects_Team\Support Team")
          == ("AREA", r"0_Projects_Team\Support Team"))

    # (١) العلامات — دي اللي كانت بتبوّظ الكود لما حد ينضّف الملف
    check("علامات مزدوجة بتتشال", parse_line('FOO="123"') == ("FOO", "123"))
    check("علامات مفردة بتتشال", parse_line("FOO='123'") == ("FOO", "123"))
    check("علامات مش متطابقة بتفضل", parse_line("FOO=\"123'") == ("FOO", "\"123'"))
    check("مسافة جوه العلامات بتتحفظ",
          parse_line('AREA="a b"') == ("AREA", "a b"))
    check("# جوه العلامات مش تعليق",
          parse_line('FOO="a # b"') == ("FOO", "a # b"))

    # (٢) التعليق الجانبي
    check("تعليق جانبي بيتقص", parse_line("FOO=123  # قناة") == ("FOO", "123"))
    check("# ملزوقة مش تعليق", parse_line("FOO=a#b") == ("FOO", "a#b"))

    # (٣) export
    check("export بيتشال", parse_line("export FOO=123") == ("FOO", "123"))

    # الأسطر اللي الشِل بتقع فيها
    check("سطر فاضي", parse_line("   ") is None)
    check("تعليق", parse_line("# FOO=1") is None)
    check("مفيش =", parse_line("قناة 8orders-issues") is None)
    check("اسم بيبدأ برقم مرفوض", parse_line("8orders-issues=1") is None)
    check("اسم فيه شرطة مرفوض", parse_line("FOO-BAR=1") is None)

    # العرض اللي المستخدم شايفه: قيمة من غير علامات وبعدها كلام
    # الشِل بتقراها «حط VAR مؤقتًا وشغّل 8orders-issues» → command not found
    line = "ISSUES_CHANNEL_ID=1179369466279235584 8orders-issues"
    got = parse_line(line)
    check("سطر العطل بيتقرا كتعيين في بايثون (فبيعدّي بصمت)", got is not None)
    check("وقيمته ملوثة بالكلام الزيادة",
          got[1] == "1179369466279235584 8orders-issues")

    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False,
                                     encoding="utf-8") as handle:
        handle.write("# تعليق\nA=1\n\nقناة 8orders-issues\nB='2'\n"
                     "8bad-name=3\nexport C=4  # تعليق\n")
        tmp = handle.name
    try:
        rows = parse_file(tmp)
        check("parse_file بيلقط الصالح بس",
              [(r[1], r[2]) for r in rows] == [("A", "1"), ("B", "2"), ("C", "4")])
        bad = bad_lines(tmp)
        check("bad_lines بيلقط التالف بأرقام السطور",
              [b[0] for b in bad] == [4, 6])

        os.environ.pop("A", None)
        os.environ["B"] = "موجود قبل"
        n = load_dotenv(tmp)
        check("load_dotenv بيحمّل الناقص", os.environ.get("A") == "1")
        check("بيئة العملية أقوى من الملف", os.environ.get("B") == "موجود قبل")
        check("العدّ بيستثني اللي كان موجود", n == 2)
        load_dotenv(tmp, override=True)
        check("override=True بيغلب البيئة", os.environ.get("B") == "2")
    finally:
        os.unlink(tmp)
        for key in ("A", "B", "C"):
            os.environ.pop(key, None)

    check("ملف مش موجود بيرجّع 0 من غير استثناء",
          load_dotenv("/nonexistent/none.env") == 0)

    print("\n" + ("ALL PASS" if ok else "THERE ARE FAILURES"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest())
