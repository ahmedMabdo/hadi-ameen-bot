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

الوحدة بتقرا .env جنبها بنفسها، فالتشغيل المباشر من الشِل بيدي نفس أرقام
الإنتاج بالظبط — من غير كده أداة التشخيص بتقيس نظام تاني غير اللي بيرفع.

CLI:
    ado_features.py suggest --text "..." [--k 3]   # المرشحين بالدرجات
    ado_features.py best --text "..."              # أنسب واحدة أو لا شيء
    ado_features.py epics                          # الـ Epics المتاحة
    ado_features.py status                         # حالة الكاش
    ado_features.py calibrate                      # معايرة MIN_SCORE على الداتا
    ado_features.py selftest                       # اختبار من غير شبكة
"""
import argparse
import math
import os
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))


def _load_dotenv():
    """يقرا .env جنب الملف — نفس نمط ado_client.py و intel/discord_delivery.py.

    من غير ده الوحدة دي كانت بتتقرا إعداداتها من بيئة العملية بس، فالتشغيل
    المباشر من الشِل (`ado_features.py suggest`) كان بياخد الـ defaults بينما
    الإنتاج (اللي بيتنادى من discord_bot بعد load_dotenv) بياخد قيم .env.
    يعني أداة التشخيص كانت بتقيس نظام تاني غير اللي بيرفع فعلًا.

    setdefault مقصود: بيئة العملية أقوى من الملف — عشان تقدر تجرّب قيمة مؤقتة
    بـ `HADI_FEATURE_MIN_SCORE=0.5 ado_features.py suggest ...` من غير ما تعدّل .env.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(path):
        return
    try:
        lines = open(path, encoding="utf-8").readlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

DB_PATH = os.environ.get(
    "ADO_SNAPSHOT_DB", str(BASE / "ado_snapshot.db"))
PROJECT_ITEM_ID = int(os.environ.get("ADO_PROJECT_ITEM", "53585") or "53585")

# أقل درجة نقبل عندها الربط. تحتها بنرجّع None ونرفع من غير أب.
#
# ‼ القيمة دي مبدئية ولسه مش معايرة على الداتا الحقيقية. معادلة الدرجة
# اتغيّرت بالكامل في _score، فرقم 0.95 القديم (ولا 0.34) مالوش أي معنى على
# المقياس الجديد — النقل المباشر غلط.
#
# 0.42 مشتقة من نمذجة تقريبية لتوزيع الـ df على ~182 فيتشر: بترفض عنوان كله
# توكنز عامة حتى لو تطابق بالكامل (~0.39)، وبتقبل تطابق كامل لعنوان فيه كلمة
# نادرة (~0.56). الانحياز للأعلى مقصود ومتوافق مع القاعدة الحاكمة: ربط غلط
# أسوأ من مفيش ربط، فالخطأ في اتجاه «مايربطش» مقبول.
#
# ⇒ شغّل `python3 ado_features.py calibrate` على السيرفر واضبط الرقم بالأرقام
#   اللي هيطلعها، مش بالتخمين.
MIN_SCORE = float(os.environ.get("HADI_FEATURE_MIN_SCORE", "0.42") or "0.42")

# كتلة المعلومات اللي عندها الدرجة بتوصل نص قيمتها. توكن نادر واحد (وزنه ~1.0)
# بيدي عامل 0.5، واتنين بيدوا 0.67. ده الحاجز اللي بيمنع عنوان زي
# «Customer Order» (توكنز عامة أوزانها مجموعة ~0.6) إنه يوصل للحد حتى لو
# تطابق بالكامل. رفع الرقم = تشدّد أكتر في «كام كلمة نادرة تكفي».
INFO_SATURATION = float(os.environ.get("HADI_FEATURE_INFO_SAT", "1.0") or "1.0")

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


def idf_weights(titles):
    """وزن ندرة لكل توكن في مجموعة العناوين — القيمة في [0, 1].

    الوزن = log(N/df) / log(N). التوكن اللي بيظهر في عنوان واحد بس بياخد 1.0،
    واللي بيظهر في كل العناوين بياخد 0.0.

    ليه ده لازم: مع ~182 فيتشر، توكنز زي order/customer/store/item بتظهر في
    عشرات العناوين، فهي مابتفرّقش بين فيتشر وفيتشر. العدّ المجرد (القديم) كان
    بيدّي «Customer Order» درجة كاملة لأي طلب فيه كلمة أوردر، وبكده الفيتشر
    العامة بتكسب الفيتشر المتخصصة الصح. الترجيح بيخلي الكلمة النادرة — اللي
    بتحدد النطاق فعلًا — هي اللي بتقرر.
    """
    df = {}
    n = 0
    for title in titles:
        toks = _tokens(title)
        if not toks:
            continue
        n += 1
        for tok in toks:
            df[tok] = df.get(tok, 0) + 1
    if n < 2:
        return {}
    ln_n = math.log(n)
    return {tok: max(0.0, math.log(n / c) / ln_n) for tok, c in df.items()}


_IDF_CACHE = {}


def _corpus_idf():
    """أوزان الـ IDF من الفيتشرز الحية في الكاش. {} لو مفيش كاش.

    الكاش مفتاحه DB_PATH عشان selftest بيبدّل المسار وقت التشغيل.
    """
    key = DB_PATH
    if key not in _IDF_CACHE:
        _, features = load_tree()
        _IDF_CACHE[key] = idf_weights(
            [f["title"] or "" for f in features if _alive(f)])
    return _IDF_CACHE[key]


def _score(query_tokens, title, idf=None):
    """درجة تطابق العنوان مع الطلب في [0, 1] — تغطية موزونة × كتلة معلومات.

        تغطية = مجموع أوزان التوكنز المشتركة ÷ مجموع أوزان توكنز العنوان
        كتلة   = مجموع أوزان التوكنز المشتركة ÷ (نفسها + INFO_SATURATION)
        الدرجة = تغطية × كتلة

    العامل الأول بيحافظ على السلوك القديم المقصود: القسمة على توكنز العنوان
    (مش الاتحاد) عشان العنوان القصير المطابق يكسب الطلب الطويل.

    العامل التاني هو الجديد وهو اللي بيقفل الثغرة: التغطية لوحدها بتدّي 1.0
    لعنوان كله توكنز عامة لو الطلب صادف إنه فيها كلها («Customer Order» مع أي
    طلب أوردر). ضرب التغطية في كتلة المعلومات بيخلي العنوان اللي مافيهوش أي
    كلمة نادرة مايوصلش للحد أصلًا، مهما كانت تغطيته كاملة.

    idf=None (نداء مباشر من غير كاش) معناه أوزان موحّدة 1.0 لكل توكن — نفس
    المقياس بالظبط عشان الدرجات تفضل قابلة للمقارنة مع نفس MIN_SCORE.
    """
    title_tokens = _tokens(title)
    if not title_tokens or not query_tokens:
        return 0.0
    hits = title_tokens & query_tokens
    if not hits:
        return 0.0

    def w(tok):
        return 1.0 if idf is None else idf.get(tok, 1.0)

    total = sum(w(t) for t in title_tokens)
    if total <= 0:
        return 0.0
    info = sum(w(t) for t in hits)
    if info <= 0:
        return 0.0
    coverage = info / total
    return coverage * (info / (info + INFO_SATURATION))


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
    idf = _corpus_idf()

    scored = []
    for f in features:
        if not include_dead and not _alive(f):
            continue
        base = _score(qt, f["title"] or "", idf)
        if base <= 0:
            continue
        in_epic = (want_epic is not None and f["parent"] == want_epic)
        # الإيبك الصح بيرفع الدرجة 25% — إشارة مساعدة مش حاسمة.
        # القصّ على 1.0 عشان الدرجة تفضل على نفس مقياس MIN_SCORE بعد الرفع.
        scored.append({
            "id": f["id"], "title": f["title"], "state": f["state"],
            "epic": epic_title.get(f["parent"], f["parent"]),
            "epic_id": f["parent"], "in_epic": in_epic,
            "score": round(min(1.0, base * (1.25 if in_epic else 1.0)), 3),
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


def _pct(sorted_vals, p):
    """المئين p من قايمة مرتبة تصاعديًا."""
    if not sorted_vals:
        return 0.0
    i = min(len(sorted_vals) - 1, max(0, int(round((p / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[i]


def calibrate(top_collisions=12, top_tokens=15):
    """معايرة MIN_SCORE على الداتا الحقيقية — من غير أي لايبلينج يدوي.

    الفكرة: كل عنوان فيتشر بيتستخدم كطلب، وبنقيس حاجتين:

      • درجة الفيتشر مع نفسها  → سقف «التطابق الصح»
      • أعلى درجة لأي فيتشر تانية → توزيع «التطابق الغلط»

    التوزيع التاني هو المهم: هو بيقيس بشكل مباشر «أعلى درجة تقدر فيتشر غلط
    توصلها». الحد الصح بيتحط فوق الكتلة الأساسية من التوزيع ده.

    تحذير في القراءة: استخدام العنوان كطلب أسهل من طلب عربي حقيقي، فأرقام
    «التطابق الصح» متفائلة ومش مؤشر على أداء الإنتاج. أرقام «التطابق الغلط»
    هي اللي يعتمد عليها في اختيار الحد.
    """
    epics, features = load_tree()
    live = [f for f in features if _alive(f) and _tokens(f["title"] or "")]
    if len(live) < 5:
        print("مفيش داتا كفاية للمعايرة — شغّل: python3 ado_snapshot.py refresh")
        return 1

    idf = _corpus_idf()
    print(f"الكاش: {DB_PATH}")
    print(f"Epics: {len(epics)} | Features نشطة بعناوين صالحة: {len(live)}")
    print(f"المعادلة: تغطية موزونة × كتلة/(كتلة+{INFO_SATURATION})  |  "
          f"MIN_SCORE الحالي: {MIN_SCORE}\n")

    print(f"أعم {top_tokens} توكن (أقل أوزان — دي اللي كانت بتكسب في العدّ المجرد):")
    for tok, w in sorted(idf.items(), key=lambda kv: kv[1])[:top_tokens]:
        print(f"   {w:.3f}  {tok}")

    selves, impostors, collisions = [], [], []
    for f in live:
        qt = _tokens(f["title"] or "")
        selves.append(_score(qt, f["title"] or "", idf))
        best_other, best_row = 0.0, None
        for g in live:
            if g["id"] == f["id"]:
                continue
            s = _score(qt, g["title"] or "", idf)
            if s > best_other:
                best_other, best_row = s, g
        impostors.append(best_other)
        if best_row is not None:
            collisions.append((best_other, f["title"], best_row["title"]))

    selves.sort()
    impostors.sort()

    print("\nتوزيع درجة «التطابق الغلط» (أعلى فيتشر تانية لكل طلب):")
    for p in (50, 75, 90, 95, 99):
        print(f"   p{p:<3} {_pct(impostors, p):.3f}")
    print(f"   max  {impostors[-1]:.3f}")

    print("\nتوزيع درجة «التطابق الصح» (متفائل — اقراه كسقف مش كتوقع):")
    for p in (1, 5, 10, 25, 50):
        print(f"   p{p:<3} {_pct(selves, p):.3f}")

    suggested = round(_pct(impostors, 95) + 0.02, 2)
    kept = sum(1 for s in selves if s >= suggested)
    print(f"\nحد مقترح (p95 للتطابق الغلط + هامش): {suggested}")
    print(f"   عنده بيترفض ~95% من التطابقات الغلط، "
          f"وبيعدّي {kept}/{len(selves)} من التطابقات الصح")
    at_current = sum(1 for s in impostors if s >= MIN_SCORE)
    print(f"   عند MIN_SCORE الحالي ({MIN_SCORE}): "
          f"{at_current}/{len(impostors)} تطابق غلط كان هيعدّي")

    collisions.sort(reverse=True)
    print(f"\nأسوأ {top_collisions} تصادم (طلب ← الفيتشر الغلط اللي كسبت):")
    for s, q, wrong in collisions[:top_collisions]:
        print(f"   {s:.3f}  «{q}»  ←  «{wrong}»")

    print("\nبعد ما تختار رقم: حطه في .env كـ HADI_FEATURE_MIN_SCORE "
          "وشغّل الأمر ده تاني للتأكيد.")
    return 0


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
    full = _score(qt, "Promo Code")
    check(f"تطابق كامل للعنوان القصير بيدي درجة عالية ({full:.3f})", full > 0.6)
    check("الدرجة مابتعدّيش 1", full <= 1.0)
    check("عنوان مالوش علاقة = صفر", _score(qt, "Cash Collection From Delivery") == 0.0)

    qt2 = _tokens("عايز تقرير جديد لتاريخ الطلبات")
    part = _score(qt2, "Order History")
    check(f"تطابق جزئي بين 0 و1 ({part:.3f})", 0 < part <= 1.0)

    # ---------------- ترجيح الندرة (IDF) ----------------
    # كوربوس تركيبي بيحاكي المشكلة الحقيقية: «order» و«customer» في كل حتة،
    # و«promo» نادرة. المفروض الندرة هي اللي تقرر مش العدّ.
    corpus = [
        "Customer Order", "Order List", "Order Details", "Order Status",
        "Customer Profile", "Customer Orders Report", "Order Tracking",
        "Customer Order History", "Promo Code Engine",
    ]
    w = idf_weights(corpus)
    check("وزن التوكن العام أقل من النادر", w.get("order", 1) < w.get("promo", 0))
    check("كل الأوزان في [0,1]", all(0.0 <= v <= 1.0 for v in w.values()))
    check("توكن في عنوان واحد بس وزنه أعلى قيمة", w.get("promo", 0) == max(w.values()))
    check("مفيش أوزان من كوربوس صغير جدًا", idf_weights(["Order List"]) == {})

    # نفس الطلب على العنوانين: واحد عام بيتطابق بالكامل، وواحد متخصص جزئيًا.
    q = _tokens("عايز كود خصم جديد على طلبات العميل")
    generic_u = _score(q, "Customer Order")            # أوزان موحّدة (السلوك القديم)
    special_u = _score(q, "Promo Code Engine")
    generic_w = _score(q, "Customer Order", w)         # أوزان IDF (السلوك الجديد)
    special_w = _score(q, "Promo Code Engine", w)
    check(f"قبل الترجيح: العنوان العام كان بيكسب "
          f"({generic_u:.3f} ≥ {special_u:.3f})", generic_u >= special_u)
    check(f"بعد الترجيح: المتخصص بيكسب "
          f"({special_w:.3f} > {generic_w:.3f})", special_w > generic_w)
    check(f"العنوان العام بيقع تحت الحد ({generic_w:.3f} < {MIN_SCORE})",
          generic_w < MIN_SCORE)
    check("الترجيح مابيكسرش المدى [0,1]", 0 <= generic_w <= 1 and 0 <= special_w <= 1)

    # التغطية الكاملة لوحدها مابقتش تكفي — دي الثغرة اللي كانت بتنتج ربط غلط
    check("تغطية كاملة لعنوان عام ≠ درجة كاملة",
          _score(_tokens("customer order"), "Customer Order", w) < 1.0)

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
    c = sub.add_parser("calibrate", help="معايرة MIN_SCORE على الداتا الحقيقية")
    c.add_argument("--collisions", type=int, default=12)
    c.add_argument("--tokens", type=int, default=15)
    sub.add_parser("selftest")
    args = p.parse_args()

    if args.cmd == "selftest":
        sys.exit(selftest())

    if args.cmd == "calibrate":
        sys.exit(calibrate(top_collisions=args.collisions, top_tokens=args.tokens))

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
