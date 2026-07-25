#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ado_features.py — اختيار الـ Feature الأب المناسبة لأي work item جديد.

الشجرة الحقيقية على ADO (متحقق منها 2026-07-25):

    Project 53585 «8Orders»  →  Epic (12)  →  Feature (~87)

يعني الـ Features **مش** أولاد مباشرين لـ 53585 — هي أحفاده. الوحدة دي بتمشي
المستويين وتختار أنسب Feature لنص الطلب.

مصدر البيانات: جدول project_items في كاش ado_snapshot (بيتحدّث كل 15 دقيقة).
مفيش نداء شبكة هنا خالص — قراءة محلية بس، فآمنة تتنادى في أي مسار.

القاعدة الحاكمة (قرار آسر 2026-07-25):
    لقى Feature مناسبة  →  يربطها parent
    مالقاش               →  **يرفع من غير parent** ومايسألش ومايعطّلش

الفلسفة: ربط غلط أسوأ من مفيش ربط. الثقة الواطية بترجّع None بدل ما تخمّن.

CLI:
    ado_features.py suggest --text "..." [--k 3]   # المرشحين بالدرجات
    ado_features.py best --text "..."              # أنسب واحدة أو لا شيء
    ado_features.py epics                          # الـ Epics المتاحة
    ado_features.py status                         # حالة الكاش
    ado_features.py selftest                       # اختبار من غير شبكة
"""
import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

DB_PATH = os.environ.get(
    "ADO_SNAPSHOT_DB", str(BASE / "ado_snapshot.db"))
PROJECT_ITEM_ID = int(os.environ.get("ADO_PROJECT_ITEM", "53585") or "53585")

# أقل درجة تشابه نقبل عندها الربط. تحتها بنرجّع None ونرفع من غير أب.
MIN_SCORE = float(os.environ.get("HADI_FEATURE_MIN_SCORE", "0.34") or "0.34")

# الحالة الوحيدة اللي مانربطش بيها (قرار آسر 2026-07-25): Removed — دي متشالة
# نهائي. الـ Closed عادي نربطها: الشغل الجديد بيرجع لنفس نطاق الفيتشر حتى لو
# دورتها اتقفلت، والربط بيحافظ على التتبع.
DEAD_STATES = {"removed"}

# ربط StoryApplication (اللي ado_fields بيستنتجه من النص) بالـ Epic المقابل.
# الأرقام متحقق منها من ADO الحي 2026-07-25.
APP_TO_EPIC = {
    "Admin Web": 42293,                  # 8Order - Admin
    "CST App": 53065,                    # 8Order - Customer Mobile App
    "Customer Web": 53065,               # نفس الإيبك — مفيش إيبك ويب منفصل للعميل
    "Merchant App": 53064,               # Merchant OPS Mobile App
    "Delivery App": 53401,               # 8Order - Delivery Mobile App
    "Delivery Web": 79646,               # Delivery Web
    "Stores Web - Operator Web": 55508,  # Stores - Admin
}

try:
    from memory_store import normalize as _normalize, _TOKEN_RX, _STOPWORDS
except Exception:  # نسخة احتياطية لو اتشغّل لوحده
    _DIA = re.compile(r"[ً-ْٰـ]")
    _TOKEN_RX = re.compile(r"[0-9A-Za-zء-ي٠-٩]+")
    _STOPWORDS = set()

    def _normalize(text):
        text = _DIA.sub("", text or "")
        for src, dst in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"),
                         ("ة", "ه"), ("ؤ", "و"), ("ئ", "ي")):
            text = text.replace(src, dst)
        return text.lower()

# مرادفات عربي↔إنجليزي — عناوين الـ Features كلها إنجليزي والطلبات عربي.
# من غير الجسر ده التطابق بيبقى صفر تقريبًا في كل الحالات الحقيقية.
SYNONYMS = {
    "اوردر": "order", "الاوردر": "order", "اوردرات": "order", "طلب": "order",
    "الطلب": "order", "طلبات": "order", "الطلبات": "order",
    "سله": "cart", "السله": "cart", "عربه": "cart",
    "دفع": "payment", "الدفع": "payment", "مدفوعات": "payment", "فلوس": "payment",
    "فاتوره": "invoice", "الفاتوره": "invoice",
    "خصم": "promo", "كوبون": "promo", "برومو": "promo", "بروموكود": "promo",
    "كود": "code", "الكود": "code", "اكواد": "code",
    "قسيمه": "voucher", "فاوتشر": "voucher",
    "توصيل": "delivery", "التوصيل": "delivery", "كابتن": "delivery",
    "الكابتن": "delivery", "سائق": "delivery", "مندوب": "delivery",
    "متجر": "store", "المتجر": "store", "متاجر": "store", "مطعم": "restaurant",
    "المطعم": "restaurant", "مطاعم": "restaurant",
    "صنف": "item", "الصنف": "item", "اصناف": "item", "منتج": "product",
    "منيو": "menu", "المنيو": "menu", "قائمه": "menu",
    "تقرير": "report", "التقرير": "report", "تقارير": "report",
    "اشعار": "notification", "اشعارات": "notification", "تنبيه": "notification",
    "دخول": "login", "تسجيل": "login", "باسورد": "password", "كلمه": "password",
    "مستخدم": "user", "المستخدم": "user", "مستخدمين": "user", "عميل": "customer",
    "العميل": "customer", "عملاء": "customer",
    "شكوي": "complaint", "شكاوي": "complaint", "شكوى": "complaint",
    "استرداد": "refund", "ارجاع": "refund", "مرتجع": "refund",
    "تعويض": "compensation", "محفظه": "wallet", "المحفظه": "wallet",
    "خريطه": "map", "الخريطه": "map", "عنوان": "address", "العنوان": "address",
    "بحث": "search", "البحث": "search", "فلتر": "filter", "تصفيه": "filter",
    "لغه": "localization", "اللغه": "localization", "ترجمه": "localization",
    "عربي": "localization", "صلاحيه": "permission", "صلاحيات": "permission",
    "اعدادات": "settings", "الاعدادات": "settings", "ضبط": "settings",
    "تسعير": "pricing", "السعر": "pricing", "اسعار": "pricing",
    "كاش": "cash", "نقدي": "cash", "تحصيل": "collection",
    "توفر": "availability", "متاح": "availability", "متوفر": "availability",
    "اعلان": "ads", "اعلانات": "ads", "بانر": "banner",
    "تقييم": "rating", "نجوم": "rating", "مراجعه": "review",
    "تاريخ": "history", "سجل": "history", "ارشيف": "history",
    "رئيسيه": "home", "الرئيسيه": "home", "هوم": "home",
}


def _lookup(tok):
    """مرادف التوكن — بيجرّب الكلمة زي ما هي وبعدين من غير أداة التعريف.

    تجريد «ال» مقصود: الجدول مايتكتبش مرتين لكل كلمة، و«الخصم» و«خصم»
    بيوصلوا لنفس المرادف. من غير ده كان «كود الخصم» مايطابقش «Promo Code».
    """
    hit = SYNONYMS.get(tok)
    if hit:
        return hit
    if tok.startswith("ال") and len(tok) > 3:
        return SYNONYMS.get(tok[2:])
    return None


def _tokens(text):
    """توكنز مطبّعة + ترجمة المرادفات العربية لمقابلها الإنجليزي."""
    out = set()
    for tok in _TOKEN_RX.findall(_normalize(text)):
        if len(tok) < 2 or tok in _STOPWORDS:
            continue
        out.add(tok)
        mapped = _lookup(tok)
        if mapped:
            out.add(mapped)
    return out


def _connect():
    if not os.path.exists(DB_PATH):
        return None
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def load_tree():
    """(epics, features) من كاش ado_snapshot. بيرجع ([], []) لو الكاش مش موجود."""
    con = _connect()
    if con is None:
        return [], []
    try:
        rows = con.execute(
            "SELECT id, type, title, state, parent FROM project_items").fetchall()
    except sqlite3.Error:
        return [], []
    finally:
        con.close()

    epics = [dict(r) for r in rows
             if (r["type"] or "") == "Epic" and r["parent"] == PROJECT_ITEM_ID]
    epic_ids = {e["id"] for e in epics}
    features = [dict(r) for r in rows
                if (r["type"] or "") == "Feature" and r["parent"] in epic_ids]
    return epics, features


def _alive(item):
    return (item.get("state") or "").strip().lower() not in DEAD_STATES


def _score(query_tokens, title):
    """نسبة توكنز عنوان الـ Feature اللي ظهرت في الطلب (Jaccard مائل للعنوان).

    القسمة على توكنز العنوان مش على الاتحاد: عنوان قصير ومطابق زي «Promo Code»
    يكسب طلب طويل، وده المطلوب — العنوان هو اللي بيوصف النطاق.
    """
    title_tokens = _tokens(title)
    if not title_tokens or not query_tokens:
        return 0.0
    hits = title_tokens & query_tokens
    if not hits:
        return 0.0
    return len(hits) / len(title_tokens)


def target_epic(text):
    """الإيبك المرشح من StoryApplication اللي ado_fields بيستنتجه. None لو مفيش."""
    try:
        import ado_fields
        inferred = ado_fields.infer_cr_fields(text)
        if not inferred.get("_inferred"):
            return None
        return APP_TO_EPIC.get(inferred.get("Custom.StoryApplication"))
    except Exception:
        return None


def suggest(text, k=3, include_dead=False):
    """أفضل k مرشحين مرتبين. كل عنصر: id, title, state, epic, score, in_epic."""
    epics, features = load_tree()
    if not features:
        return []
    epic_title = {e["id"]: e["title"] for e in epics}
    want_epic = target_epic(text)
    qt = _tokens(text)

    scored = []
    for f in features:
        if not include_dead and not _alive(f):
            continue
        base = _score(qt, f["title"] or "")
        if base <= 0:
            continue
        in_epic = (want_epic is not None and f["parent"] == want_epic)
        # الإيبك الصح بيرفع الدرجة 25% — إشارة مساعدة مش حاسمة
        scored.append({
            "id": f["id"], "title": f["title"], "state": f["state"],
            "epic": epic_title.get(f["parent"], f["parent"]),
            "epic_id": f["parent"], "in_epic": in_epic,
            "score": round(base * (1.25 if in_epic else 1.0), 3),
        })
    scored.sort(key=lambda r: (-r["score"], r["id"]))
    return scored[:k]


def best(text):
    """أنسب Feature أو None.

    None معناها «ارفع من غير parent» — مش خطأ ومش سبب لتعطيل الرفع.
    """
    top = suggest(text, k=1)
    if not top:
        return None
    return top[0] if top[0]["score"] >= MIN_SCORE else None


def selftest():
    ok = True

    def check(label, cond):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + label)
        ok = ok and bool(cond)

    check("التطبيع بيوحّد الألف", _tokens("أوردر") == _tokens("اوردر"))
    check("المرادف بيبني الجسر عربي↔إنجليزي", "order" in _tokens("الاوردر اتلغى"))
    check("أداة التعريف بتتجرّد في البحث", _lookup("الخصم") == "promo")

    qt = _tokens("مشكلة في كود الخصم مش شغال")
    check("تطابق كامل للعنوان القصير", _score(qt, "Promo Code") == 1.0)
    check("عنوان مالوش علاقة = صفر", _score(qt, "Cash Collection From Delivery") == 0.0)

    qt2 = _tokens("عايز تقرير جديد لتاريخ الطلبات")
    part = _score(qt2, "Order History")
    check(f"تطابق جزئي بين 0 و1 ({part})", 0 < part <= 1.0)

    check("Removed بترفض", not _alive({"state": "Removed"}))
    check("Closed بتتقبل (قرار آسر)", _alive({"state": "Closed"}))
    check("الحالة النشطة بتتقبل", _alive({"state": "Active"}))
    check("كل إيبك في الخريطة رقم", all(isinstance(v, int) for v in APP_TO_EPIC.values()))

    # من غير كاش لازم يرجّع فاضي بهدوء — مايكسرش مسار الرفع
    global DB_PATH
    keep, DB_PATH = DB_PATH, "/nonexistent/none.db"
    try:
        check("مفيش كاش = مفيش اقتراح (من غير استثناء)", suggest("أي حاجة") == [])
        check("مفيش كاش = best بترجّع None", best("أي حاجة") is None)
    finally:
        DB_PATH = keep

    print("\n" + ("ALL PASS" if ok else "THERE ARE FAILURES"))
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description="اختيار الـ Feature الأب من شجرة 8Orders")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("suggest", help="أفضل المرشحين بالدرجات")
    s.add_argument("--text", required=True)
    s.add_argument("--k", type=int, default=3)
    s.add_argument("--include-dead", action="store_true")

    s = sub.add_parser("best", help="أنسب Feature أو لا شيء")
    s.add_argument("--text", required=True)

    sub.add_parser("epics", help="الـ Epics تحت مشروع 8Orders")
    sub.add_parser("status", help="حالة الكاش")
    sub.add_parser("selftest")
    args = p.parse_args()

    if args.cmd == "selftest":
        sys.exit(selftest())

    if args.cmd == "status":
        epics, features = load_tree()
        alive = [f for f in features if _alive(f)]
        print(f"الكاش: {DB_PATH}")
        print(f"موجود: {os.path.exists(DB_PATH)}")
        print(f"Epics: {len(epics)} | Features: {len(features)} (منها {len(alive)} نشطة)")
        if not features:
            print("\nمفيش شجرة — شغّل: python3 ado_snapshot.py refresh")
        return

    if args.cmd == "epics":
        epics, features = load_tree()
        if not epics:
            print("مفيش إيبكس في الكاش — شغّل ado_snapshot.py refresh")
            return
        per = {}
        for f in features:
            per[f["parent"]] = per.get(f["parent"], 0) + 1
        for e in sorted(epics, key=lambda x: x["id"]):
            print(f"  #{e['id']:<7} {e['state']:<9} {e['title']}  ({per.get(e['id'], 0)} feature)")
        return

    if args.cmd == "best":
        hit = best(args.text)
        if hit is None:
            print("مفيش Feature مناسبة — ارفع من غير parent (ده سلوك صحيح مش خطأ).")
            sys.exit(0)
        print(f"#{hit['id']}  {hit['title']}  [{hit['state']}]  "
              f"درجة {hit['score']}  ← {hit['epic']}")
        return

    rows = suggest(args.text, k=args.k, include_dead=args.include_dead)
    if not rows:
        print("مفيش مرشحين — ارفع من غير parent.")
        return
    for r in rows:
        mark = "★" if r["score"] >= MIN_SCORE else " "
        print(f" {mark} #{r['id']:<7} {r['score']:<6} {r['state']:<9} "
              f"{r['title']}   ← {r['epic']}")
    print(f"\n(الحد الأدنى للربط {MIN_SCORE} — اللي تحته بيترفع من غير parent)")


if __name__ == "__main__":
    main()
