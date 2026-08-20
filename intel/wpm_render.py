# -*- coding: utf-8 -*-
"""8Orders — Weekly Product Metrics: RENDER LAYER (v2).

WHAT CHANGED IN v2 (per the PO, Aug 2026)
─────────────────────────────────────────
· THREE LAYERS, one per audience, in one PDF:
    Layer 1 — top management: verdict, north star, the decisions to make.
    Layer 2 — marketing / operations / business / delivery: the operating detail.
    Layer 3 — UX + backend/mobile engineering: defects, users affected, action items.
  A reader stops at the end of their layer. Nothing is repeated across layers.

· NO DUPLICATION. v1 stated the same funnel in sections 2, 3, 4, 5 and 7, and the
  same action list in sections 17, 18, 19 and 20. Each fact now appears exactly
  once, in the layer that can act on it.

· EVERY PERCENTAGE SHOWS ITS DENOMINATOR inline — "62% (3,321 من 5,356 مستخدم)" —
  and the denominator is always unique users. See wpm_data.v2 for why.

· EVERY METRIC IS SEGMENTED by city / platform / version wherever the data allows.

· THE GLOSSARY IS GENERATED FROM THE SAME DICT THE REPORT RENDERS FROM, so a rate
  can never appear in the report without its definition, and a definition can
  never drift from the formula that produced the number.

Arabic RTL, Western digits, arrowheads pointing left (←) for RTL flows.
No business number is hardcoded in this file.
"""
import datetime as dt

CBLUE = "#1e3a5f"; CBLUE2 = "#2563eb"; CGREEN = "#16a34a"
CRED = "#dc2626"; CYEL = "#ca8a04"; CGRAY = "#64748b"; CORANGE = "#ea580c"
CPURPLE = "#7c3aed"; CTEAL = "#0d9488"
BG_G = "#f0fdf4"; BG_Y = "#fefce8"; BG_R = "#fef2f2"; BG_B = "#eff6ff"; BORD = "#e2e8f0"

# One colour per layer, used on the layer banner, its dividers and its page edge.
L1_C, L2_C, L3_C = CBLUE, CTEAL, CPURPLE

AR_MONTHS = {1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
             7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"}
AR_DOW = {0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس",
          4: "الجمعة", 5: "السبت", 6: "الأحد"}


def ar_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {AR_MONTHS[d.month]} {d.year}"


def ar_short(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {AR_MONTHS[d.month]}"


def ar_full(iso):
    d = dt.date.fromisoformat(iso)
    return f"{AR_DOW[d.weekday()]} {d.day} {AR_MONTHS[d.month]}"


# ───────────────────────────── primitives ─────────────────────────────────────
def fmt(n):
    try:
        return f"{int(round(float(n))):,}"
    except Exception:
        return str(n)


def en(txt):
    """Isolate an English/numeric run so RTL text around it stays correctly ordered."""
    return f'<span class="en" dir="ltr">{txt}</span>'


def na(txt="غير متاح"):
    return f'<span style="color:{CGRAY};font-weight:600;font-size:7.6pt;">{txt}</span>'


def delta(cur, prev, good_up=True, unit="", pct_only=False):
    if prev in (None, 0):
        return na("—")
    d = cur - prev
    p = d / prev * 100
    if abs(p) < 0.5:
        return f'<span style="color:{CGRAY};font-weight:700;">ثابت</span>'
    col = CGREEN if ((d > 0) == good_up) else CRED
    body = f'{"▲" if d > 0 else "▼"}&nbsp;{abs(p):.0f}%'
    if not pct_only:
        body += f'&nbsp;({fmt(abs(d))}{unit})'
    return f'<span style="color:{col};font-weight:800;" dir="ltr">{body}</span>'


def light(c):
    return (f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
            f'background:{c};vertical-align:middle;"></span>')


def bar_row(label, value, maxv, color, right_txt="", sub=""):
    w = max(1.5, (value / maxv * 100) if maxv else 0)
    s = f'<div class="br-s">{sub}</div>' if sub else ''
    return (f'<div class="br"><div class="br-l">{label}{s}</div>'
            f'<div class="br-t"><div class="br-f" style="width:{w:.1f}%;background:{color};"></div></div>'
            f'<div class="br-v" dir="ltr">{right_txt or fmt(value)}</div></div>')


def heat_color(r):
    a, b = (239, 246, 255), (30, 58, 95)
    c = tuple(int(a[i] + (b[i] - a[i]) * r) for i in range(3))
    return f'rgb({c[0]},{c[1]},{c[2]})'


def kpi_card(t_ar, t_en, value, unit, d_html, status, sub="", width="calc(25% - 6px)"):
    return (f'<div class="kpi" style="border-top:3px solid {status};width:{width};">'
            f'<div class="kpi-t">{t_ar} <span class="kpi-en">{t_en}</span></div>'
            f'<div class="kpi-v" dir="ltr">{value}<span class="kpi-u">{unit}</span></div>'
            f'<div class="kpi-d">{d_html}</div>'
            + (f'<div class="kpi-s">{sub}</div>' if sub else '') + '</div>')


def box(kind, title, body):
    m = {"info": (BG_B, CBLUE2, "ℹ"), "risk": (BG_R, CRED, "⚠"), "opp": (BG_G, CGREEN, "✚"),
         "warn": (BG_Y, CYEL, "◆"), "gap": ("#f1f5f9", CGRAY, "⊘"),
         "fix": ("#faf5ff", CPURPLE, "⚙")}
    bg, bd, ic = m[kind]
    return (f'<div class="box" style="background:{bg};border-right:4px solid {bd};">'
            f'<div class="box-t" style="color:{bd};">{ic} {title}</div>'
            f'<div class="box-b">{body}</div></div>')


def verdict_badge(v):
    """The host has no emoji font, so a literal 🟢 renders as tofu. Map to a CSS dot."""
    txt = str(v or "").strip()
    col = CYEL
    for emoji, c in [("🔴", CRED), ("🟠", CORANGE), ("🟡", CYEL), ("🟢", CGREEN)]:
        if emoji in txt:
            col, txt = c, txt.replace(emoji, "").strip()
            break
    else:
        for word, c in [("حرِج", CRED), ("حرج", CRED), ("تحذير", CORANGE),
                        ("صحّي", CGREEN), ("صحي", CGREEN)]:
            if word in txt:
                col = c
                break
    return (f'{light(col)} <span class="hbadge" style="color:{col};">'
            f'{txt or "مستقر مع تنبيهات"}</span>')


def layer_banner(num, ar, en_, who, color):
    return (f'<div class="lbanner" style="background:{color};">'
            f'<div class="lb-n" dir="ltr">{num}</div>'
            f'<div><div class="lb-t">{ar} <span class="lb-en">{en_}</span></div>'
            f'<div class="lb-w">موجّهة إلى: {who}</div></div></div>')


def divider(num, ar, en_, color=CBLUE):
    return (f'<div class="divider" style="border-color:{color};">'
            f'<div class="dnum" style="background:{color};" dir="ltr">{num}</div>'
            f'<div class="dttl" style="color:{color};">{ar}<span class="dttl-en">{en_}</span></div></div>')


# ── the v2 signature component: a percentage that can never be misread ────────
def rate(r, decimals=0, color=None):
    """Render a rate WITH its numerator, denominator and basis. This component is
    the whole point of v2 — a bare '58%' is exactly what made v1 untrustworthy."""
    c = color or CBLUE
    return (f'<span class="rate"><b style="color:{c};" dir="ltr">{r["v"]:.{decimals}f}%</b>'
            f'<span class="rate-d" dir="ltr">{fmt(r["n"])} / {fmt(r["d"])}</span></span>')


def rate_line(label, r, color=None):
    return (f'<div class="rl"><div class="rl-l">{label}</div>'
            f'<div class="rl-v">{rate(r, color=color)}</div>'
            f'<div class="rl-b">{r["basis"]}</div></div>')


def daybars(series, active, w=210, h=58):
    """Per-active-day unique users (bar) with orders labelled. Newest on the LEFT (RTL)."""
    vals = [(d, series[d]["users"], series[d]["orders"]) for d in active if series.get(d)]
    if not vals:
        return ''
    mx = max(v for _, v, _ in vals) or 1
    n = len(vals)
    bw = (w - 8) / n - 4
    out = ''
    for i, (d, v, o) in enumerate(vals):
        bh = max(3, v / mx * (h - 30))
        x = w - 4 - (i + 1) * (bw + 4)
        out += (f'<rect x="{x:.1f}" y="{h - 13 - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
                f'rx="2" fill="{CGREEN if v == mx else CBLUE2}"/>'
                f'<text x="{x + bw / 2:.1f}" y="{h - 3}" font-size="5.4" fill="#94a3b8" '
                f'text-anchor="middle">{dt.date.fromisoformat(d).day}</text>'
                f'<text x="{x + bw / 2:.1f}" y="{h - 16 - bh:.1f}" font-size="5.6" '
                f'fill="#475569" text-anchor="middle" font-weight="700">{fmt(v)}</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{out}</svg>'


def funnel_html(steps, maxh=76):
    """User funnel as HTML, RTL: first step on the RIGHT, each bar a share of step one.

    Deliberately NOT an SVG. WeasyPrint does not shape or bidi-order Arabic inside
    <svg><text>, so Arabic step labels came out as disconnected reversed glyphs.
    Plain HTML gets the browser text pipeline and renders correctly.
    """
    if not steps:
        return ''
    top = steps[0][1] or 1
    cells = ""
    for label, val, color in steps:
        h = max(5, (val / top) * maxh)
        cells += (f'<div class="fb"><div class="fb-v" dir="ltr">{fmt(val)}</div>'
                  f'<div class="fb-bar" style="height:{h:.0f}px;background:{color};"></div>'
                  f'<div class="fb-l">{label}</div>'
                  f'<div class="fb-p" dir="ltr">{val / top * 100:.0f}%</div></div>')
    return f'<div class="fun">{cells}</div>'


# ───────────────────────────── glossary source of truth ───────────────────────
# key -> (arabic term, english term, plain-language formula, how to read it)
# The report NEVER shows a rate that is missing from here — see build_glossary().
RATE_DEFS = {
    "activation":       ("نسبة التفعيل", "Activation Rate",
                         "المستخدمون اللي حطّوا حاجة في السلة ÷ المستخدمون اللي فتحوا التطبيق",
                         "بتقيس: من كل مية واحد فتح التطبيق، كام واحد وصل لنية شراء حقيقية."),
    "browse":           ("نسبة التصفّح", "Browse Rate",
                         "المستخدمون اللي شافوا منتج ÷ المستخدمون اللي فتحوا التطبيق",
                         "بتقيس: كام واحد اتخطّى الشاشة الرئيسية ودخل يبص على منتج فعلًا."),
    "cart_to_checkout": ("السلة ← بدء الدفع", "Cart → Checkout",
                         "المستخدمون اللي بدؤوا الدفع ÷ المستخدمون اللي حطّوا في السلة",
                         "بتقيس: من اللي ملا سلة، كام واحد كمّل لشاشة الدفع."),
    "checkout_to_order": ("بدء الدفع ← الطلب", "Checkout → Order",
                          "المستخدمون اللي أتمّوا طلب ÷ المستخدمون اللي بدؤوا الدفع",
                          "بتقيس: من اللي دخل شاشة الدفع، كام واحد الطلب بتاعه نجح."),
    "cart_to_order":    ("السلة ← الطلب (كلي)", "Cart → Order",
                         "المستخدمون اللي أتمّوا طلب ÷ المستخدمون اللي حطّوا في السلة",
                         "أهم نسبة تحويل في التقرير: من اللي أبدى نية شراء، كام واحد اشترى."),
    "purchase":         ("نسبة الشراء", "Purchase Rate",
                         "المستخدمون اللي أتمّوا طلب ÷ المستخدمون اللي فتحوا التطبيق",
                         "بتقيس: من كل مية واحد فتح التطبيق، كام واحد طلع بطلب."),
    "pay_success":      ("نجاح الدفع", "Payment Success Rate",
                         "المستخدمون اللي أتمّوا طلب ÷ (اللي أتمّوا طلب + اللي فشل معاهم الدفع)",
                         "بتقيس بالمستخدم مش بالمحاولة: من كل مية حاولوا يدفعوا، كام واحد نجح."),
    "error_hit":        ("نسبة المستخدمين المتأثرين بخطأ", "Error Incidence",
                         "المستخدمون اللي قابلهم خطأ واحد على الأقل ÷ المستخدمون اللي فتحوا التطبيق",
                         "الرقم ده بيقول كام شخص حقيقي اتضرب، مش كام خطأ اتسجّل."),
    "rage_hit":         ("نسبة نقرات الغضب", "Rageclick Incidence",
                         "المستخدمون اللي نقروا بغضب ÷ المستخدمون اللي فتحوا التطبيق",
                         "نقرة الغضب = ضغط سريع متكرر في نفس المكان، علامة إحباط."),
    "cancel":           ("نسبة الإلغاء", "Cancellation Rate",
                         "المستخدمون اللي ألغوا طلب ÷ المستخدمون اللي أتمّوا طلب",
                         "بتقيس: من كل مية مشترٍ، كام واحد لغى طلب في نفس الأسبوع."),
    "voucher_use":      ("استخدام الفاوتشر", "Voucher Usage",
                         "المستخدمون اللي طبّقوا فاوتشر ÷ المستخدمون اللي أتمّوا طلب",
                         "بتقيس اعتماد المشترين على الخصومات."),
    "reorder_use":      ("استخدام إعادة الطلب", "Reorder Usage",
                         "المستخدمون اللي ضغطوا إعادة الطلب ÷ المستخدمون اللي أتمّوا طلب",
                         "بتقيس: كام مشترٍ استخدم الاختصار بدل ما يبني الطلب من الأول."),
    "rating_rate":      ("نسبة التقييم", "Rating Rate",
                         "المستخدمون اللي قيّموا طلب ÷ المستخدمون اللي أتمّوا طلب",
                         "بتقيس استعداد العميل يدّي رأيه — مؤشر تفاعل مش رضا."),
    "multi_store":      ("سلة أكتر من متجر", "Multi-store Cart",
                         "المستخدمون اللي فتحوا شيت أكتر من متجر ÷ المستخدمون اللي حطّوا في السلة",
                         "بتقيس النيّة لاستخدام الميزة، مش إتمامها."),
    "search_fail":      ("بحث بدون نتيجة", "Failed Search",
                         "المستخدمون اللي بحثوا وماجاش نتيجة ÷ المستخدمون اللي فتحوا التطبيق",
                         "كل واحد هنا دوّر على حاجة مش موجودة — فرصة توسيع كتالوج."),
    "uncovered":        ("طلب من منطقة غير مخدومة", "Uncovered Demand",
                         "المستخدمون اللي منطقتهم غير مخدومة ÷ المستخدمون اللي فتحوا التطبيق",
                         "طلب حقيقي مكبوت — ناس عايزة تطلب والتغطية مش واصلاهم."),
    "guest_share":      ("الدخول كضيف", "Guest Share",
                         "المستخدمون اللي دخلوا كضيف ÷ المستخدمون اللي فتحوا التطبيق",
                         "الضيف مش بيتعمله ريتنشن ولا إشعارات — فرصة تحويل لحساب."),
    "ads_ignore":       ("تجاهل إعلانات الرئيسية", "Home Ads Ignore Rate",
                         "المستخدمون اللي تجاهلوا الإعلان ÷ (اللي تجاهلوه + اللي نقروا عليه)",
                         "فوق 50% معناها المساحة بتضايق أكتر ما بتفيد."),
}

# Terms that are not rates but still need defining for a non-analyst reader.
CONCEPT_DEFS = [
    ("المستخدم الفريد", "Unique User",
     "الشخص الواحد بيتحسب مرة واحدة مهما عمل أحداث كتير أو فتح التطبيق كذا مرة.",
     "ده المقام الوحيد المستخدم في كل نسب التقرير — عشان الأرقام تبقى قابلة للمقارنة."),
    ("اليوم النشط", "Active Day",
     "يوم عمل (8ص لـ 4ص القاهرة) فيه بيانات تتبّع حقيقية — أكتر من 5,000 حدث.",
     "التقرير بيرجع لورا لحد ما يجمع 7 أيام نشطة، فمايتأثرش بانقطاع التتبّع."),
    ("المؤشر الأهم", "North Star Metric",
     "الرقم الواحد اللي بيلخّص نجاح المنتج. هنا: عدد الطلبات الناجحة.",
     "أي قرار المفروض في الآخر يحرّك الرقم ده."),
    ("متوسط قيمة الطلب", "AOV — Average Order Value",
     "إجمالي الإيراد ÷ عدد الطلبات.",
     "بيقول الطلب الواحد بيجيب كام — الإيراد = عدد الطلبات × الرقم ده."),
    ("الإيراد لكل مستخدم", "ARPU",
     "إجمالي الإيراد ÷ المستخدمين اللي فتحوا التطبيق.",
     "بيقيس كفاءة تحويل الزيارات لفلوس، مش بس عدد الطلبات."),
    ("الإيراد لكل مشترٍ", "ARPB",
     "إجمالي الإيراد ÷ المستخدمين اللي أتمّوا طلب.",
     "بيقيس قيمة العميل الفعلي في الأسبوع."),
    ("طلبات لكل مشترٍ", "Orders per Buyer",
     "إجمالي الطلبات ÷ عدد المشترين.",
     "فوق 1 معناها فيه تكرار شراء داخل نفس الأسبوع."),
    ("العميل المتكرر", "Repeat Buyer",
     "مشترٍ عمل طلبين أو أكتر داخل نفس نافذة التقرير.",
     "مؤشر ولاء قصير المدى — مش نفس كوهورت D7."),
    ("العميل الوفي", "Loyal Buyer",
     "مشترٍ عمل 3 طلبات أو أكتر داخل نفس نافذة التقرير.",
     "دي النواة اللي بتحمل أغلب الإيراد المتكرر."),
    ("القمع", "Funnel",
     "خطوات المستخدم من فتح التطبيق للطلب، وكل خطوة بتتقاس بعدد المستخدمين الفريدين.",
     "التسرّب = الفرق بين خطوة والخطوة اللي قبلها."),
    ("الخطأ الشبكي مقابل غير الشبكي", "Network vs Code Error",
     "الشبكي سببه نت المستخدم (قطع/إشارة ضعيفة)؛ غير الشبكي خلل في كود التطبيق.",
     "الشبكي مابيتصلحش بالكود — غير الشبكي هو اللي عليه شغل هندسي."),
    ("نسبة تعبئة الحقل", "Field Fill Rate",
     "عدد الأحداث اللي الحقل فيها بقيمة حقيقية ÷ إجمالي الأحداث.",
     "حقل بيتبعت دايمًا بصفر بيبان كأنه بيانات — وهو في الحقيقة فجوة."),
    ("إسناد المدينة", "City Attribution",
     "المستخدم بيتنسب لمدينة المتاجر اللي فتحها فعلًا، مش لموقع الإنترنت بتاعه.",
     "موقع الإنترنت غلط هنا لأن شركات المحمول بتوجّه الترافيك لبوابة في القاهرة."),
]


def build_glossary(d):
    """Generate the glossary from the SAME rates dict the report rendered from.

    A rate cannot appear in the report without appearing here with its formula and
    this week's value — and the value shown here is literally the value shown above.
    """
    items = []
    for key, r in d["rates"].items():
        if key not in RATE_DEFS:
            continue
        ar, en_, formula, howto = RATE_DEFS[key]
        items.append(dict(ar=ar, en=en_, formula=formula, howto=howto,
                          value=f'{r["v"]:.1f}%', detail=f'{fmt(r["n"])} / {fmt(r["d"])}',
                          basis=r["basis"]))
    return items


# ───────────────────────────── stylesheet ─────────────────────────────────────
def CSS(week_start, week_end):
    return r"""
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
@page { size:A4; margin:14mm 12mm 15mm 12mm;
  @bottom-right { content:"صفحة " counter(page) " / " counter(pages); font-family:'Cairo',Arial,sans-serif; font-size:7.5pt; color:#94a3b8; }
  @bottom-left { content:"8Orders · تقرير مؤشرات المنتج الأسبوعي · """ + f"{ar_date(week_start)} – {ar_date(week_end)}" + r""""; font-family:'Cairo',Arial,sans-serif; font-size:7.5pt; color:#94a3b8; }
}
* { box-sizing:border-box; }
body { font-family:'Cairo',Arial,sans-serif; direction:rtl; text-align:right; color:#1e293b; font-size:9pt; line-height:1.55; margin:0; }
h1,h2,h3 { margin:0; }
.en { font-family:'Cairo',Arial,sans-serif; direction:ltr; unicode-bidi:isolate; font-weight:600; }
.gloss { font-size:7pt; color:#94a3b8; font-weight:500; }
.cover { background:linear-gradient(135deg,#1e3a5f 0%,#2b4a70 100%); color:#fff; padding:22px 22px; border-radius:14px; margin-bottom:11px; }
.cover .logo { direction:ltr; font-weight:900; font-size:24pt; letter-spacing:-1px; }
.cover .logo b { color:#4ade80; }
.cover h1 { font-size:19pt; font-weight:900; margin:8px 0 3px; }
.cover .sub { font-size:10pt; opacity:.9; font-weight:500; }
.cover .meta { margin-top:12px; display:flex; gap:18px; flex-wrap:wrap; font-size:8.2pt; }
.cover .meta b { display:block; font-size:10.5pt; font-weight:800; }
.note-avail { background:#fefce8; border:1px solid #fde68a; border-radius:8px; padding:8px 11px; font-size:7.9pt; color:#854d0e; margin-bottom:9px; }
.note-rule { background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:8px 11px; font-size:8pt; color:#1e40af; margin-bottom:9px; }
.lbanner { display:flex; align-items:center; gap:11px; color:#fff; border-radius:11px; padding:10px 14px; margin:14px 0 9px; break-inside:avoid; break-after:avoid; }
.lb-n { font-size:20pt; font-weight:900; opacity:.55; line-height:1; }
.lb-t { font-size:14pt; font-weight:900; }
.lb-en { font-size:8.5pt; font-weight:600; opacity:.75; direction:ltr; margin-right:6px; }
.lb-w { font-size:8pt; opacity:.85; font-weight:600; }
.divider { display:flex; align-items:center; gap:9px; margin:13px 0 7px; border-bottom:2px solid; padding-bottom:5px; break-after:avoid; break-inside:avoid; }
.dnum { color:#fff; font-weight:900; font-size:9.5pt; min-width:26px; height:26px; padding:0 5px; border-radius:7px; display:flex; align-items:center; justify-content:center; }
.dttl { font-size:12pt; font-weight:800; }
.dttl-en { direction:ltr; font-weight:600; font-size:8pt; color:#94a3b8; margin-right:7px; }
.kpi-grid { display:flex; flex-wrap:wrap; gap:8px; }
.kpi { background:#fff; border:1px solid #e2e8f0; border-radius:9px; padding:8px 10px; box-shadow:0 1px 2px rgba(0,0,0,.03); break-inside:avoid; }
.kpi-t { font-size:7.5pt; color:#64748b; font-weight:600; min-height:20px; }
.kpi-en { direction:ltr; color:#b0bac9; font-size:6.5pt; }
.kpi-v { font-size:16pt; font-weight:900; color:#1e293b; line-height:1.1; margin:1px 0; }
.kpi-u { font-size:8pt; font-weight:700; color:#94a3b8; margin-right:3px; }
.kpi-d { font-size:7.6pt; } .kpi-s { font-size:6.9pt; color:#94a3b8; margin-top:1px; }
.br { display:flex; align-items:center; gap:8px; margin:3px 0; font-size:8pt; }
.br-l { width:28%; color:#334155; font-weight:600; }
.br-s { font-size:6.8pt; color:#94a3b8; font-weight:500; }
.br-t { flex:1; background:#f1f5f9; border-radius:5px; height:13px; overflow:hidden; }
.br-f { height:100%; border-radius:5px; }
.br-v { width:88px; text-align:left; font-weight:800; color:#1e293b; font-size:7.6pt; }
.box { border-radius:8px; padding:8px 11px; margin:6px 0; break-inside:avoid; }
.box-t { font-weight:800; font-size:8.8pt; margin-bottom:2px; }
.box-b { font-size:8.1pt; color:#334155; line-height:1.5; }
table.tb { width:100%; border-collapse:collapse; font-size:8pt; margin:5px 0; }
table.tb th { background:#1e3a5f; color:#fff; font-weight:700; padding:5px 7px; text-align:right; font-size:7.6pt; }
table.tb td { padding:4px 7px; border-bottom:1px solid #eef2f7; vertical-align:top; }
table.tb tr:nth-child(even) td { background:#f8fafc; }
.tb .en { font-size:7.5pt; }
.tb-t td { background:#f1f5f9 !important; font-weight:800; }
.row2 { display:flex; gap:11px; } .col { flex:1; }
.card { background:#fff; border:1px solid #e2e8f0; border-radius:9px; padding:10px 12px; margin:6px 0; break-inside:avoid; }
.card h3 { font-size:9.6pt; color:#1e3a5f; font-weight:800; margin-bottom:5px; }
.chip { display:inline-block; font-size:6.6pt; font-weight:800; padding:1px 6px; border-radius:20px; white-space:nowrap; }
.c-p0 { background:#dc2626; color:#fff; } .c-p1 { background:#ea580c; color:#fff; } .c-p2 { background:#ca8a04; color:#fff; }
.c-and { background:#dcfce7; color:#15803d; } .c-ios { background:#e0e7ff; color:#3730a3; } .c-both { background:#f1f5f9; color:#475569; }
.c-hrg { background:#cffafe; color:#0e7490; } .c-asy { background:#fae8ff; color:#a21caf; }
.hbadge { font-size:13pt; font-weight:900; }
.heat { display:flex; gap:2px; direction:ltr; }
.heat .hc { flex:1; text-align:center; }
.heat .hcell { height:24px; border-radius:3px; display:flex; align-items:center; justify-content:center; color:#fff; font-size:6pt; font-weight:800; }
.heat .hlab { font-size:5.6pt; color:#94a3b8; margin-top:1px; }
.small { font-size:7.6pt; color:#64748b; } .mini { font-size:7.3pt; color:#94a3b8; line-height:1.45; }
ul.tl { margin:3px 0; padding-right:15px; } ul.tl li { margin:2px 0; font-size:8.1pt; }
.rate { display:inline-block; white-space:nowrap; }
.rate b { font-size:11pt; font-weight:900; }
.rate-d { font-size:6.8pt; color:#94a3b8; font-weight:600; margin-right:4px; }
.rl { display:flex; align-items:center; gap:8px; padding:4px 0; border-bottom:1px solid #f1f5f9; }
.rl-l { width:33%; font-weight:700; font-size:8.1pt; color:#334155; }
.rl-v { width:26%; }
.rl-b { flex:1; font-size:7.2pt; color:#94a3b8; }
.gl { display:flex; flex-wrap:wrap; gap:6px; }
.gl .g { width:calc(50% - 3px); background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:6px 9px; break-inside:avoid; }
.gl .g .gt { font-weight:800; color:#1e3a5f; font-size:8.3pt; }
.gl .g .ge { direction:ltr; font-size:6.6pt; color:#94a3b8; font-weight:600; }
.gl .g .gf { font-size:7.4pt; color:#334155; margin-top:2px; }
.gl .g .gh { font-size:7.1pt; color:#64748b; margin-top:1px; font-style:italic; }
.gl .g .gv { font-size:7.4pt; font-weight:800; color:#2563eb; margin-top:2px; direction:ltr; text-align:left; }
.src { background:#f8fafc; border:1px dashed #cbd5e1; border-radius:8px; padding:7px 10px; font-size:7.3pt; color:#64748b; margin-top:7px; }
.src b { color:#475569; }
.toc { background:#f8fafc; border:1px solid #e2e8f0; border-radius:9px; padding:9px 12px; font-size:8.2pt; margin-bottom:10px; }
.toc .t { font-weight:800; color:#1e3a5f; margin-bottom:3px; font-size:9pt; }
.toc .r { display:flex; gap:7px; align-items:baseline; margin:2px 0; }
.toc .b { display:inline-block; width:9px; height:9px; border-radius:2px; }
.pagebreak { break-before:page; }
.fun { display:flex; gap:6px; align-items:flex-end; direction:rtl; padding:2px 4px; }
.fun .fb { flex:1; text-align:center; }
.fun .fb-v { font-size:8pt; font-weight:900; color:#1e293b; margin-bottom:2px; }
.fun .fb-bar { border-radius:4px 4px 0 0; }
.fun .fb-l { font-size:7pt; color:#475569; margin-top:3px; font-weight:600; }
.fun .fb-p { font-size:6.8pt; color:#94a3b8; font-weight:700; }
.pstrip { display:flex; gap:7px; }
.pstrip .p { flex:1; background:#fff; border:1px solid #e2e8f0; border-radius:8px; padding:6px 9px; }
.pstrip .p .pn { font-weight:800; font-size:8.6pt; color:#1e3a5f; direction:ltr; }
.pstrip .p .pr { display:flex; justify-content:space-between; font-size:7.2pt; margin-top:2px;
  border-top:1px solid #f1f5f9; padding-top:1px; color:#475569; }
.pstrip .p .pr b { direction:ltr; }
"""


# ═══════════════════════════════ THE REPORT ═══════════════════════════════════
def render(d, a):
    d["hours"] = {int(k): int(v) for k, v in (d.get("hours") or {}).items()}
    U, V, R = d["users"], d["vol"], d["rates"]
    AD, PAD = d["active_days"], d["prev_active_days"]
    PD, PPD = d["per_day"], d["prev_per_day"]
    wow_ok = d["wow_ok"]

    def wow(key, good_up=True):
        if not (wow_ok and PPD):
            return na("مقارنة أسبوعية غير متاحة")
        return delta(PD[key], PPD[key], good_up=good_up, pct_only=True)

    def uwow(key, good_up=True):
        """Week-over-week on a unique-user metric, normalised per active day."""
        if not (wow_ok and d.get("prev_users") and PAD):
            return na("—")
        return delta(U[key] / AD, d["prev_users"][key] / PAD, good_up=good_up, pct_only=True)

    P = []
    HEAD = ('<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>'
            + CSS(d["week_start"], d["week_end"]) + '</style></head><body>')

    # ═══════════════════════ COVER ═══════════════════════
    P.append(f'''
<div class="cover">
  <div class="logo">8<b>Orders</b></div>
  <h1>تقرير مؤشرات المنتج — أسبوعي</h1>
  <div class="sub">تطبيق توصيل طعام وبقالة (الغردقة وأسيوط) · المؤشر الأهم: عدد الطلبات الناجحة</div>
  <div class="meta">
    <div>نافذة التقرير<b style="font-size:9pt;">{ar_date(d["week_start"])} – {ar_date(d["week_end"])}</b></div>
    <div>أيام نشطة<b>{AD} يوم</b></div>
    <div>مستخدمون فريدون<b style="color:#4ade80;">{fmt(U["active"])}</b></div>
    <div>الطلبات الناجحة<b style="color:#4ade80;">{fmt(V["orders"])}</b></div>
    <div>الإيراد<b>{fmt(V["revenue"])} ج.م</b></div>
    <div>المصدر<b>PostHog · 8orders</b></div>
  </div>
</div>''')

    # data-scope honesty banner
    bits = []
    if d["gap_days"]:
        bits.append(f"<b>{len(d['gap_days'])} يوم جوّه الفترة مفيهم بيانات</b> "
                    f"({'، '.join(ar_short(x) for x in d['gap_days'])}) — اتشالوا من الحساب.")
    if d["stale_days"]:
        bits.append(f"<b>التتبّع واقف من {ar_date(d['stale_days'][0])}</b> "
                    f"({len(d['stale_days'])} يوم لحد تاريخ التقرير) — غالبًا تجاوز حد باقة "
                    f"PostHog. عشان كده التقرير رجع لورا وجمّع آخر <b>{AD}</b> يوم فيهم "
                    f"بيانات حقيقية بدل آخر 7 أيام تقويمية.")
    if not wow_ok:
        bits.append("<b>مقارنة الأسبوع اللي فات غير متاحة</b> — مفيش أسبوع سابق متصل "
                    "فيه بيانات كافية، فأي نسبة تغيّر هتكون مضلِّلة ومش معروضة.")
    if bits:
        P.append('<div class="note-avail"><b>نطاق البيانات:</b> ' + " ".join(bits) + '</div>')

    # THE denominator rule — stated once, at the top, and never repeated
    P.append(f'''<div class="note-rule"><b>قاعدة قراءة التقرير (مهمة):</b>
  كل نسبة في التقرير ده محسوبة على <b>المستخدمين الفريدين</b> — الشخص بيتحسب مرة واحدة
  مهما عمل أحداث كتير. وكل نسبة مكتوب جنبها البسط والمقام
  ({en("مثال: 91% — 3,321 / 3,648")}) وعلى إيه بالظبط اتحسبت.
  <b>مافيش أي نسبة في التقرير مبنية على عدد الأحداث أو عدد الجلسات.</b>
  التعريف الكامل لكل مؤشر في قاموس المؤشرات آخر التقرير.</div>''')

    P.append(f'''<div class="toc"><div class="t">التقرير 3 طبقات — كل طبقة لجمهور مختلف</div>
  <div class="r"><span class="b" style="background:{L1_C};"></span>
    <b>الطبقة 1 — القرار التنفيذي:</b> للإدارة العليا. الحالة العامة، المؤشر الأهم، والقرارات المطلوبة.</div>
  <div class="r"><span class="b" style="background:{L2_C};"></span>
    <b>الطبقة 2 — التشغيل والنمو:</b> للماركتنج، الأوبريشن، البيزنس، والديليفري. التفاصيل التشغيلية والمدن.</div>
  <div class="r"><span class="b" style="background:{L3_C};"></span>
    <b>الطبقة 3 — المنتج والتطوير:</b> للـ {en("UX")} والمطوّرين ({en("Backend / Mobile")}). الأعطال ومهام كل فريق.</div>
  <div class="mini" style="margin-top:3px;">لو وقتك ضيق: اقرا طبقتك بس — مفيش تكرار بين الطبقات،
    وكل معلومة مذكورة مرة واحدة في المكان اللي يقدر يتصرّف فيها.</div>
</div>''')

    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 1 — EXECUTIVE
    # ══════════════════════════════════════════════════════════════════════════
    P.append(layer_banner("1", "القرار التنفيذي", "Executive", "الإدارة العليا", L1_C))

    P.append(divider("1.1", "حالة المنتج هذا الأسبوع", "Product Health", L1_C))
    wins_html = "<br>".join(f"• {x}" for x in (a.get("wins") or [])[:3])
    risks_html = "<br>".join(f"• {x}" for x in (a.get("risks") or [])[:3])
    P.append(f'''
<div class="card" style="border-top:4px solid {L1_C};">
  <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
    <div style="font-size:11.5pt;font-weight:900;">الحالة: {verdict_badge(a.get("verdict"))}</div>
    <div style="text-align:center;">{daybars(d["series"], d["active"])}
      <div class="mini">مستخدمون فريدون في كل يوم نشط</div></div>
  </div>
  <div class="box-b" style="margin-top:5px;">{a.get("reading", "")}</div>
  {("<div class='mini'>" + a["note"] + "</div>") if a.get("note") else ""}
</div>
<div class="row2">
  <div class="col">{box("opp", "أحسن اللي حصل", wins_html)}</div>
  <div class="col">{box("risk", "محتاج متابعة", risks_html)}</div>
</div>''')

    P.append('<div class="kpi-grid">')
    P.append(kpi_card("الطلبات الناجحة", "Orders", fmt(V["orders"]), "", wow("orders"), CGREEN,
                      f"متوسط {fmt(V['orders'] / AD)} في اليوم النشط"))
    P.append(kpi_card("المشترون", "Buyers", fmt(U["buyer"]), "", uwow("buyer"), CGREEN,
                      f"{R['purchase']['v']:.0f}% من المستخدمين"))
    P.append(kpi_card("الإيراد", "Revenue", fmt(V["revenue"]), "ج.م", wow("revenue"), CYEL,
                      f"{fmt(V['revenue'] / AD)} ج.م في اليوم"))
    P.append(kpi_card("متوسط قيمة الطلب", "AOV", f'{d["aov"]:.0f}', "ج.م",
                      delta(d["aov"], d["prev_aov"], pct_only=True) if wow_ok else na("—"), CBLUE2))
    P.append(kpi_card("مستخدمون فريدون", "Unique Users", fmt(U["active"]), "", uwow("active"), CBLUE2,
                      "مقام كل النسب"))
    P.append(kpi_card("السلة ← الطلب", "Cart → Order", f'{R["cart_to_order"]["v"]:.0f}', "%",
                      f'<span class="mini">{fmt(R["cart_to_order"]["n"])} / {fmt(R["cart_to_order"]["d"])}</span>',
                      CGREEN, "أهم نسبة تحويل"))
    P.append(kpi_card("نجاح الدفع", "Payment Success", f'{R["pay_success"]["v"]:.0f}', "%",
                      f'<span class="mini">{fmt(R["pay_success"]["n"])} / {fmt(R["pay_success"]["d"])}</span>',
                      CYEL if R["pay_success"]["v"] < 95 else CGREEN, "المستهدف 98%+"))
    P.append(kpi_card("مستخدمون قابلهم خطأ", "Users Hit by Error", fmt(U["error"]), "",
                      f'<span class="mini">{R["error_hit"]["v"]:.0f}% من المستخدمين</span>',
                      CRED, "أشخاص مش أحداث"))
    P.append('</div>')

    P.append(divider("1.2", "أين نقف — المدينة والمنصة", "City & Platform", L1_C))
    UNK = "غير محدد"
    real_cities = [c for c in d["cities"] if c["dim"] != UNK]
    unknown_city = next((c for c in d["cities"] if c["dim"] == UNK), None)
    city_rows = "".join(
        f'<tr><td><b>{c["dim"]}</b></td><td class="en">{fmt(c["users"])}</td>'
        f'<td class="en">{fmt(c["buyers"])}</td><td class="en">{c["purchase_rate"]:.1f}%</td>'
        f'<td class="en">{fmt(c["orders"])}</td><td class="en">{fmt(c["revenue"])}</td>'
        f'<td class="en">{c["aov"]:.0f}</td><td class="en">{c["error_rate"]:.0f}%</td></tr>'
        for c in real_cities)
    if unknown_city:
        u_ = unknown_city
        city_rows += (
            f'<tr class="tb-t"><td>غير منسوب<div class="mini">مافتحوش أي متجر — '
            f'فتحوا التطبيق وخرجوا</div></td><td class="en">{fmt(u_["users"])}</td>'
            f'<td class="en">{fmt(u_["buyers"])}</td><td colspan="5" class="mini">'
            f'{u_["users"] / U["active"] * 100:.0f}% من المستخدمين — دول مش مشكلة إسناد، '
            f'دول ناس فتحت التطبيق ومادخلتش أي متجر أصلًا.</td></tr>')
    plat_cards = ""
    for p_ in d["platforms"][:3]:
        plat_cards += (
            f'<div class="p"><div class="pn">{p_["dim"]}</div>'
            f'<div class="pr"><span>مستخدمون</span><b>{fmt(p_["users"])}</b></div>'
            f'<div class="pr"><span>نسبة الشراء</span><b>{p_["purchase_rate"]:.1f}%</b></div>'
            f'<div class="pr"><span>نسبة الخطأ</span><b>{p_["error_rate"]:.0f}%</b></div>'
            f'<div class="pr"><span>متوسط الطلب</span><b>{p_["aov"]:.0f} ج.م</b></div></div>')
    P.append(f'''
<table class="tb"><tr><th>المدينة</th><th>مستخدمون</th><th>مشترون</th>
  <th>نسبة الشراء</th><th>طلبات</th><th>إيراد (ج.م)</th><th>متوسط الطلب</th><th>نسبة الخطأ</th></tr>
  {city_rows}</table>
<div class="mini" style="margin-bottom:6px;">المدينة متحسبة من المتاجر اللي المستخدم فتحها فعلًا،
  مش من موقع الإنترنت — المنهجية آخر التقرير. المقارنة الكاملة بين المدينتين في الطبقة 2.</div>
<div class="pstrip">{plat_cards}</div>''')

    # ── the three decisions ──
    P.append(divider("1.3", "القرارات المطلوبة من الإدارة", "Decisions Needed", L1_C))
    top_code = next((e for e in d["errors"] if e["kind"] == "code"), None)
    zero_fields = [q for q in d["data_quality"] if q["fill_rate"] < 1]
    # best/worst must ignore the unattributed bucket — it has 0 buyers by construction
    # (those users never opened a store), so it would always "win" as the worst city.
    best_city = max(real_cities, key=lambda c: c["purchase_rate"]) if real_cities else None
    worst_city = min(real_cities, key=lambda c: c["purchase_rate"]) if real_cities else None
    decisions = []
    if top_code:
        decisions.append((
            "اعتماد إصلاح أعلى خطأ برمجي في التطبيق",
            f'خطأ {en(top_code["msg"][:52])} ضرب <b>{fmt(top_code["users"])}</b> مستخدم '
            f'({top_code["os"]}) — إجمالي المتأثرين بأخطاء {fmt(U["error"])} '
            f'({R["error_hit"]["v"]:.0f}% من المستخدمين).',
            "تقليل التسرّب وتحسين الثبات", "الهندسة", "p0"))
    if zero_fields:
        decisions.append((
            "إلزام تعبئة حقول الطلب الفارغة",
            f'<b>{len(zero_fields)}</b> حقل على حدث الطلب بيتبعت فاضي أو بصفر '
            f'({en("، ".join(q["field"] for q in zero_fields[:4]))}) — '
            f'فمفيش هامش ربح ولا تحليل متاجر ولا تكلفة توصيل.',
            "يفتح تحليل الربحية بالكامل", "الهندسة + البيانات", "p0"))
    decisions.append((
        "ترقية باقة PostHog أو ضبط حد تنبيه",
        f'التتبّع وقف مرتين في شهرين (يوليو، وتاني من {ar_date(d["stale_days"][0])} '
        f'لو موجود). كل انقطاع بيضيّع أسبوع مقارنة.'
        if d["stale_days"] else
        'التتبّع وقف قبل كده في يوليو وضيّع أسبوعين مقارنة — الحد لسه من غير تنبيه.',
        "استمرارية القرار المبني على بيانات", "البيانات + المالية", "p1"))
    if best_city and worst_city and best_city["dim"] != worst_city["dim"]:
        decisions.append((
            f'تخصيص خطة نمو لـ{worst_city["dim"]}',
            f'{worst_city["dim"]}: {fmt(worst_city["users"])} مستخدم بنسبة شراء '
            f'{worst_city["purchase_rate"]:.0f}% مقابل {best_city["purchase_rate"]:.0f}% في '
            f'{best_city["dim"]} — الفجوة '
            f'{best_city["purchase_rate"] - worst_city["purchase_rate"]:.0f} نقطة.',
            "سوق قائم غير مستغل", "التشغيل + التسويق", "p1"))
    if U["uncovered"]:
        decisions.append((
            "دراسة توسّع التغطية القريبة",
            f'<b>{fmt(U["uncovered"])}</b> مستخدم ({R["uncovered"]["v"]:.1f}% من المستخدمين) '
            f'حاولوا يطلبوا من مناطق غير مخدومة، وأغلبهم جوّه نفس المحافظتين.',
            "طلب مكبوت جاهز", "التشغيل", "p2"))
    dec_rows = "".join(
        f'<tr><td><b>{i + 1}. {t}</b><div class="mini">{why}</div></td>'
        f'<td>{imp}</td><td>{own}</td><td><span class="chip c-{pr}">{pr.upper()}</span></td></tr>'
        for i, (t, why, imp, own, pr) in enumerate(decisions[:4]))
    P.append(f'''
<table class="tb"><tr><th style="width:52%;">القرار / السبب بالأرقام</th><th>الأثر</th>
  <th>المالك</th><th>الأولوية</th></tr>{dec_rows}</table>
<div class="card" style="background:{L1_C};color:#fff;border:none;text-align:center;padding:12px;">
  <div style="font-size:7.8pt;opacity:.75;font-weight:700;">الخلاصة التنفيذية — Executive Takeaway</div>
  <div style="font-size:12pt;font-weight:900;line-height:1.5;margin-top:3px;">
    {a.get("takeaway", f"{fmt(V['orders'])} طلب من {fmt(U['buyer'])} مشترٍ.")}</div>
</div>
<div class="mini">نهاية الطبقة 1. الإدارة العليا ممكن تقف هنا — الباقي تفاصيل تنفيذية.</div>''')

    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 2 — BUSINESS / OPERATIONS / MARKETING / DELIVERY
    # ══════════════════════════════════════════════════════════════════════════
    P.append('<div class="pagebreak"></div>')
    P.append(layer_banner("2", "التشغيل والنمو", "Growth & Operations",
                          "الماركتنج · الأوبريشن · البيزنس · الديليفري", L2_C))

    # ── 2.1 the user funnel, and the correction that makes it trustworthy ──
    P.append(divider("2.1", "رحلة المستخدم — فين بيقعوا بالظبط", "User Funnel", L2_C))
    steps = [("فتح التطبيق", U["active"], "#93c5fd"), ("شاف منتج", U["product"], "#60a5fa"),
             ("حطّ في السلة", U["cart"], "#3b82f6"), ("بدأ الدفع", U["checkout"], "#1d4ed8"),
             ("أتمّ طلب", U["buyer"], CGREEN)]
    drop_browse = U["active"] - U["product"]
    drop_cart = U["product"] - U["cart"]
    drop_checkout = U["cart"] - U["checkout"]
    drop_order = U["checkout"] - U["buyer"]
    biggest = max([("من فتح التطبيق لمشاهدة منتج", drop_browse),
                   ("من مشاهدة منتج لإضافة للسلة", drop_cart),
                   ("من السلة لبدء الدفع", drop_checkout),
                   ("من بدء الدفع لإتمام الطلب", drop_order)], key=lambda x: x[1])
    P.append(f'''
<div class="card"><h3>القمع بالمستخدمين الفريدين — كل عمود = عدد أشخاص</h3>
  <div style="text-align:center;">{funnel_html(steps)}</div>
</div>
<div class="row2">
  <div class="col"><div class="card"><h3>نِسَب التحويل بين الخطوات</h3>
    {rate_line("فتح التطبيق ← شاف منتج", R["browse"], CBLUE2)}
    {rate_line("فتح التطبيق ← حطّ في السلة", R["activation"], CBLUE2)}
    {rate_line("السلة ← بدء الدفع", R["cart_to_checkout"], CGREEN)}
    {rate_line("بدء الدفع ← أتمّ الطلب", R["checkout_to_order"], CGREEN)}
    {rate_line("السلة ← الطلب (كلي)", R["cart_to_order"], CGREEN)}
    {rate_line("فتح التطبيق ← الطلب", R["purchase"], CBLUE)}
  </div></div>
  <div class="col">{box("info", "أكبر تسرّب فعلي هذا الأسبوع",
    f"<b>{biggest[0]}</b> — <b>{fmt(biggest[1])}</b> مستخدم خرجوا في الخطوة دي. "
    f"باقي التسرّب: من التطبيق للمنتج {fmt(drop_browse)}، "
    f"من المنتج للسلة {fmt(drop_cart)}، من السلة للدفع {fmt(drop_checkout)}، "
    f"من الدفع للطلب {fmt(drop_order)}.")}
    {box("warn", "تصحيح مهم عن التقارير السابقة",
    f"التقارير القديمة كانت بتقول إن أكبر تسرّب هو «السلة ← بدء الدفع» بنسبة تسرّب عالية. "
    f"ده كان <b>خطأ في المقام</b>: كانت بتقسم <b>أحداث</b> بدء الدفع على <b>أحداث</b> "
    f"إضافة للسلة — والمستخدم بيضيف كذا صنف للسلة وبيبدأ الدفع مرة واحدة، فالنسبة كانت "
    f"بتطلع منخفضة بشكل مصطنع. بالمستخدمين الفريدين، النسبة الحقيقية "
    f"<b>{R['cart_to_checkout']['v']:.0f}%</b>. "
    f"يعني <b>مشكلة التحويل مش هي أكبر مشكلة عندنا</b> — الجودة هي المشكلة.")}
  </div>
</div>''')

    # ── 2.2 city deep dive ──
    P.append(divider("2.2", "الغردقة مقابل أسيوط", "City Deep-Dive", L2_C))
    if len(real_cities) >= 2:
        c1, c2 = real_cities[0], real_cities[1]
        cmp_rows = "".join(
            f'<tr><td>{lbl}</td><td class="en">{v1}</td><td class="en">{v2}</td><td>{note}</td></tr>'
            for lbl, v1, v2, note in [
                ("مستخدمون فريدون", fmt(c1["users"]), fmt(c2["users"]),
                 f'{c1["dim"]} أكبر بـ {c1["users"] / c2["users"] if c2["users"] else 0:.1f}×'),
                ("مشترون", fmt(c1["buyers"]), fmt(c2["buyers"]), "عدد الأشخاص اللي طلبوا"),
                ("نسبة الشراء", f'{c1["purchase_rate"]:.1f}%', f'{c2["purchase_rate"]:.1f}%',
                 "من المستخدمين اللي فتحوا التطبيق"),
                ("السلة ← الطلب", f'{c1["cart_to_order"]:.1f}%', f'{c2["cart_to_order"]:.1f}%',
                 "جودة نية الشراء"),
                ("الطلبات", fmt(c1["orders"]), fmt(c2["orders"]), "إجمالي الطلبات الناجحة"),
                ("الإيراد (ج.م)", fmt(c1["revenue"]), fmt(c2["revenue"]), "إجمالي الأسبوع"),
                ("متوسط قيمة الطلب", f'{c1["aov"]:.0f}', f'{c2["aov"]:.0f}', "ج.م لكل طلب"),
                ("نسبة المتأثرين بخطأ", f'{c1["error_rate"]:.0f}%', f'{c2["error_rate"]:.0f}%',
                 "أقل = أحسن"),
                ("نقرات الغضب", f'{c1["rage_rate"]:.0f}%', f'{c2["rage_rate"]:.0f}%',
                 "أقل = أحسن"),
                ("عدد المتاجر", fmt(d["store_city_counts"]["hurghada"]),
                 fmt(d["store_city_counts"]["assiut"]), "متاجر متعرّف عليها في المدينة"),
            ])
        gap = c1["purchase_rate"] - c2["purchase_rate"]
        P.append(f'''
<table class="tb"><tr><th>المؤشر</th><th>{c1["dim"]}</th><th>{c2["dim"]}</th><th>القراءة</th></tr>
  {cmp_rows}</table>
{box("opp" if abs(gap) < 5 else "warn", "قراءة الفرق",
  f"الفرق في نسبة الشراء بين المدينتين <b>{abs(gap):.1f}</b> نقطة "
  f"({'لصالح ' + c1['dim'] if gap > 0 else 'لصالح ' + c2['dim']}). "
  + (f"{c2['dim']} فيها {fmt(d['store_city_counts']['assiut'])} متجر مقابل "
     f"{fmt(d['store_city_counts']['hurghada'])} في {c1['dim']} — "
     f"عمق الكتالوج على الأرجح أهم سبب، وده قرار توريد مش قرار منتج."
     if d["store_city_counts"]["assiut"] < d["store_city_counts"]["hurghada"] else ""))}''')
    else:
        P.append(box("gap", "المقارنة بين المدن غير متاحة",
                     "مافيش مدينتين بأحجام كافية في نافذة التقرير دي."))

    # top stores
    store_rows = "".join(
        f'<tr><td>{s["name"]}</td><td class="en">{s["store_id"]}</td>'
        f'<td><span class="chip {"c-hrg" if s["city"] == "الغردقة" else "c-asy" if s["city"] == "أسيوط" else "c-both"}">{s["city"]}</span></td>'
        f'<td class="en">{fmt(s["users"])}</td><td class="en">{fmt(s["opens"])}</td></tr>'
        for s in d["top_stores"][:10])
    P.append(f'''
<div class="card"><h3>أكتر المتاجر جذبًا للمستخدمين</h3>
  <table class="tb" style="margin:0;"><tr><th>المتجر</th><th>المعرّف</th><th>المدينة</th>
    <th>مستخدمون فريدون</th><th>مرات الفتح</th></tr>{store_rows}</table>
  <div class="mini" style="margin-top:3px;">مرتّبة بعدد الأشخاص مش بعدد الفتحات — عشان متجر
    المستخدم بيرجعله كتير مايبانش أكبر من متجر بيجذب ناس أكتر.</div>
</div>''')

    # ── 2.3 retention ──
    P.append(divider("2.3", "الاحتفاظ وتكرار الشراء", "Retention", L2_C))
    P.append('<div class="kpi-grid">')
    P.append(kpi_card("عميل طلب مرتين+", "Repeat Buyers", f'{d["repeat_rate"]:.1f}', "%",
                      f'<span class="mini">{fmt(d["repeat_buyers"])} / {fmt(U["buyer"])} مشترٍ</span>',
                      CGREEN, width="calc(25% - 6px)"))
    P.append(kpi_card("عميل طلب 3 مرات+", "Loyal Buyers", f'{d["loyal_rate"]:.1f}', "%",
                      f'<span class="mini">{fmt(d["loyal_buyers"])} / {fmt(U["buyer"])} مشترٍ</span>',
                      CGREEN))
    P.append(kpi_card("طلبات لكل مشترٍ", "Orders / Buyer", f'{d["orders_per_buyer"]:.2f}', "",
                      f'<span class="mini">على {AD} يوم نشط</span>', CYEL))
    P.append(kpi_card("إعادة الطلب", "Reorder", f'{R["reorder_use"]["v"]:.1f}', "%",
                      f'<span class="mini">{fmt(R["reorder_use"]["n"])} / {fmt(R["reorder_use"]["d"])} مشترٍ</span>',
                      CBLUE2, "استخدام الزر"))
    P.append('</div>')
    P.append(f'''
<div class="row2">
  <div class="col">{box("info", "قراءة الاحتفاظ",
    f"من كل 10 مشترين، حوالي <b>{d['repeat_rate'] / 10:.0f}</b> رجعوا طلبوا تاني في نفس "
    f"النافذة، و<b>{d['loyal_rate'] / 10:.0f}</b> طلبوا 3 مرات أو أكتر. "
    f"لكن استخدام زر «إعادة الطلب» "
    f"<b>{R['reorder_use']['v']:.0f}%</b> بس — يعني الناس بتعيد الطلب "
    f"<b>يدوي</b> بدل الاختصار. الزر إما مش ظاهر أو مش في المكان الصح.")}</div>
  <div class="col">{box("gap", "اللي لسه مش قابل للقياس",
    "كوهورت D1/D7 الحقيقي (نسبة الرجوع بعد يوم/بعد أسبوع) محتاج أسبوعين متصلين من البيانات "
    "من غير انقطاع. الرقم المعروض فوق هو <b>تكرار داخل نفس النافذة</b> — مؤشر سليم بس مش "
    "نفس D7. هيتفعّل تلقائيًا أول ما البيانات تتراكم.")}</div>
</div>''')

    # ── 2.4 revenue ──
    P.append(divider("2.4", "الإيراد ومتوسط قيمة الطلب", "Revenue & AOV", L2_C))
    P.append('<div class="kpi-grid">')
    P.append(kpi_card("الإيراد", "Revenue", fmt(V["revenue"]), "ج.م", wow("revenue"), CYEL))
    P.append(kpi_card("متوسط قيمة الطلب", "AOV", f'{d["aov"]:.0f}', "ج.م",
                      delta(d["aov"], d["prev_aov"], pct_only=True) if wow_ok else na("—"), CBLUE2))
    P.append(kpi_card("إيراد لكل مستخدم", "ARPU", f'{d["arpu"]:.0f}', "ج.م",
                      f'<span class="mini">على {fmt(U["active"])} مستخدم</span>', CBLUE2))
    P.append(kpi_card("إيراد لكل مشترٍ", "ARPB", f'{d["arpb"]:.0f}', "ج.م",
                      f'<span class="mini">على {fmt(U["buyer"])} مشترٍ</span>', CGREEN))
    P.append('</div>')
    pmax = max((p["users"] for p in d["pay_methods"]), default=1) or 1
    pm_bars = "".join(
        bar_row(p["method"], p["users"], pmax,
                CGREEN if "cash" in p["method"].lower() else CBLUE2,
                f'{fmt(p["users"])} مستخدم · {p["users"] / U["buyer"] * 100 if U["buyer"] else 0:.0f}%')
        for p in d["pay_methods"][:6])
    P.append(f'''
<div class="row2">
  <div class="col"><div class="card"><h3>طرق الدفع (بعدد المستخدمين)</h3>{pm_bars}
    <div class="mini">النسبة من إجمالي المشترين. المستخدم ممكن يستخدم أكتر من طريقة
      في الأسبوع، فمجموع النسب ممكن يعدّي 100%.</div>
  </div></div>
  <div class="col">{box("risk", "أهم قيد على الإيراد",
    f"الإيراد = عدد الطلبات × متوسط الطلب. متوسط الطلب دلوقتي <b>{d['aov']:.0f}</b> ج.م، "
    f"فأي نمو في العدد لوحده مش بيكبّر الإيراد بنفس النسبة. "
    f"وأخطر من كده: حقول <span class='en'>subtotal / delivery_fee / discount_amount</span> "
    f"كلها بتوصل بصفر، فمش قادرين نحسب <b>صافي</b> الإيراد ولا هامش الطلب — "
    f"التفصيل في الطبقة 3.")}
    {box("opp", "أسرع رافعة على الإيراد",
    f"رفع متوسط الطلب 10% بس = "
    f"<b>{fmt(V['revenue'] * 0.10)}</b> ج.م زيادة في الأسبوع من غير ما نجيب مستخدم واحد جديد. "
    f"الأدوات: حد أدنى للتوصيل المجاني، باقات، أو اقتراح إضافات وقت الدفع.")}
  </div>
</div>''')

    # ── 2.5 demand & coverage ──
    P.append(divider("2.5", "الطلب والتغطية", "Demand & Coverage", L2_C))
    cov_rows = "".join(f'<tr><td>{c["region"]}</td><td class="en">{fmt(c["users"])}</td>'
                       f'<td class="en">{fmt(c["attempts"])}</td></tr>' for c in d["cov_regions"])
    P.append(f'''
<div class="row2">
  <div class="col"><div class="card"><h3>مناطق بتحاول تطلب وهي غير مخدومة</h3>
    <table class="tb" style="margin:0;"><tr><th>المنطقة</th><th>مستخدمون</th><th>محاولات</th></tr>
      {cov_rows}</table>
    <div class="mini" style="margin-top:3px;">العناوين دي كتبها المستخدم بنفسه — مش تخمين موقع
      إنترنت. إجمالي <b>{fmt(U["uncovered"])}</b> مستخدم
      ({R["uncovered"]["v"]:.1f}% من المستخدمين). نفس الشخص ممكن يحاول في أكتر من منطقة.</div>
  </div></div>
  <div class="col">{box("opp", "أقرب توسّع منطقي",
    f"أغلب الطلب المكبوت جوّه نفس المحافظتين (أطراف الغردقة وقرى أسيوط) — يعني التوسّع "
    f"مايحتاجش مدينة جديدة بلوجستيات جديدة، محتاج بس مدّ نطاق التوصيل الحالي. "
    f"ده أرخص توسّع متاح.")}
    {box("info", "البحث كمؤشر طلب",
    f"<b>{fmt(U['search_fail'])}</b> مستخدم ({R['search_fail']['v']:.1f}%) بحثوا وماجاش نتيجة. "
    f"كل واحد فيهم قال لنا بالظبط إيه اللي ناقص في الكتالوج — بس <b>الكلمة نفسها مش متسجّلة</b>، "
    f"فمش عارفين دوّروا على إيه. مطلوب حدث "
    f"<span class='en'>search_performed (query, results_count)</span>.")}
  </div>
</div>''')

    # ── 2.6 peak hours ──
    P.append(divider("2.6", "ساعات الذروة والتخطيط التشغيلي", "Peak Hours", L2_C))
    hmax = max(d["hours"].values()) if d["hours"] else 1
    heat_cells = ""
    for h in range(24):
        v = d["hours"].get(h, 0)
        r_ = (v / hmax) if hmax else 0
        col = heat_color(r_) if v else "#eef2f7"
        heat_cells += (f'<div class="hc"><div class="hcell" style="background:{col};'
                       f'color:{"#fff" if r_ > 0.4 else "#334155"};">{v if v else ""}</div>'
                       f'<div class="hlab">{h:02d}</div></div>')
    peak_h = max(d["hours"], key=lambda k: d["hours"][k]) if d["hours"] else 0
    night = sum(v for h, v in d["hours"].items() if h in (0, 1, 2, 3))
    P.append(f'''
<div class="card"><h3>الطلبات حسب ساعة اليوم (مجموع النافذة)</h3>
  <div class="heat">{heat_cells}</div>
  <div class="mini" style="margin-top:4px;">الذروة الساعة <b>{peak_h}:00</b>
    ({fmt(d["hours"].get(peak_h, 0))} طلب). وفيه <b>استمرار قوي بعد منتصف الليل</b>:
    {fmt(night)} طلب من 12ص لـ 4ص =
    {night / V["orders"] * 100 if V["orders"] else 0:.0f}% من الطلبات — دي وردية كاملة
    محتاجة تغطية سائقين. من 4 لـ 8 صباحًا التطبيق شبه واقف (المطاعم مقفولة)، وعشان كده
    نافذة اليوم في التقرير بتبدأ 8 صباحًا.</div>
</div>''')

    # ── 2.7 marketing ──
    P.append(divider("2.7", "التسويق والتفاعل", "Marketing & Engagement", L2_C))
    P.append(f'''
<div class="row2">
  <div class="col"><div class="card"><h3>مؤشرات التسويق (كلها بالمستخدمين)</h3>
    {rate_line("استخدام الفاوتشر", R["voucher_use"], CBLUE2)}
    {rate_line("تقييم الطلب", R["rating_rate"], CGREEN)}
    {rate_line("الدخول كضيف", R["guest_share"], CYEL)}
    {rate_line("تجاهل إعلان الرئيسية", R["ads_ignore"], CRED)}
    {rate_line("سلة أكتر من متجر", R["multi_store"], CPURPLE)}
  </div></div>
  <div class="col">{box("risk", "إعلانات الرئيسية",
    f"<b>{fmt(U['ads_discard'])}</b> مستخدم تجاهلوا إعلان الرئيسية مقابل "
    f"<b>{fmt(U['ads_click'])}</b> نقروا عليه — نسبة تجاهل "
    f"<b>{R['ads_ignore']['v']:.0f}%</b>. المساحة دي أغلى مساحة في التطبيق وبتضايق "
    f"أكتر ما بتحوّل. قرار مطلوب: نغيّر المحتوى، نغيّر المكان، أو نقلّل التكرار.")}
    {box("opp", "تحويل الضيوف",
    f"<b>{fmt(U['guest'])}</b> مستخدم دخلوا كضيف ({R['guest_share']['v']:.0f}% من المستخدمين). "
    f"الضيف مش بيتعملّه ريتنشن ولا بيوصله إشعار ولا عرض — كل واحد فيهم فرصة ضايعة. "
    f"مقابل <b>{fmt(U['signup'])}</b> حساب جديد اتعمل في نفس النافذة.")}
  </div>
</div>
{box("info", "قناة الإحالة",
  f"«مشاركة التطبيق» استخدمها <b>{fmt(U['share'])}</b> مستخدم بس هذا الأسبوع. "
  f"الرقم صغير جدًا مقارنة بـ {fmt(U['buyer'])} مشترٍ — يعني القناة موجودة بس مش مفعّلة. "
  f"عرض إحالة مقيس (خصم للطرفين) هو أرخص قناة نمو متاحة، بس محتاج أول حاجة "
  f"<b>تتبّع للإحالة نفسها</b> عشان نعرف جابت كام مستخدم.")}''')

    # ── 2.8 ops actions ──
    P.append(divider("2.8", "مهام الإدارات التشغيلية", "Operational Action Items", L2_C))
    ops_teams = [
        ("التشغيل — Operations", CTEAL, [
            f"تغطية وردية 12ص–4ص: {fmt(night)} طلب ({night / V['orders'] * 100 if V['orders'] else 0:.0f}% من الطلبات).",
            f"تعزيز الطاقة حوالي الساعة {peak_h}:00 (الذروة).",
            f"دراسة مدّ نطاق التوصيل لأطراف المدينتين ({fmt(U['uncovered'])} مستخدم مكبوت)."]),
        ("التسويق — Marketing", CTEAL, [
            f"مراجعة إعلانات الرئيسية (نسبة تجاهل {R['ads_ignore']['v']:.0f}%).",
            f"حملة تحويل الضيوف لحسابات ({fmt(U['guest'])} ضيف).",
            f"قياس عائد الفاوتشر ({fmt(U['voucher'])} مستخدم طبّقوه)."]),
        ("البيزنس — Business", CTEAL, [
            f"خطة رفع متوسط الطلب من {d['aov']:.0f} ج.م (باقات / حد أدنى للتوصيل المجاني).",
            (f"خطة توريد لتعميق كتالوج {real_cities[1]['dim']}."
             if len(real_cities) >= 2 else "خطة تعميق الكتالوج في المدينة الأصغر."),
            "تحديد هامش الطلب المستهدف (محتاج أولًا تعبئة حقول الطلب — الطبقة 3)."]),
        ("الديليفري — Delivery", CTEAL, [
            f"متابعة الإلغاء: {fmt(U['cancelled'])} مستخدم ألغوا ({R['cancel']['v']:.1f}% من المشترين).",
            "تسجيل سبب الإلغاء يدويًا لحد ما يتضاف كخاصية.",
            "ربط زمن التوصيل بالتقييم (المؤشرين مش متتبعين حاليًا)."]),
    ]
    cards = ""
    for name, col, items in ops_teams:
        lis = "".join(f"<li>{x}</li>" for x in items)
        cards += (f'<div class="kpi" style="width:calc(50% - 4px);border-top:3px solid {col};">'
                  f'<div style="font-weight:800;font-size:8.5pt;color:{CBLUE};margin-bottom:2px;">{name}</div>'
                  f'<ul class="tl">{lis}</ul></div>')
    P.append(f'<div class="kpi-grid">{cards}</div>')
    P.append('<div class="mini">نهاية الطبقة 2.</div>')

    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 3 — PRODUCT / UX / ENGINEERING
    # ══════════════════════════════════════════════════════════════════════════
    P.append('<div class="pagebreak"></div>')
    P.append(layer_banner("3", "المنتج والتصميم والتطوير", "Product · UX · Engineering",
                          "الـ UX designers والمطوّرين (Backend & Mobile)", L3_C))

    # ── 3.1 errors ──
    P.append(divider("3.1", "الأخطاء — مين اتأثر وعلى إيه", "Errors by Impact", L3_C))
    es = d["error_split"]

    def plat_chip(e):
        if e["android_users"] and e["ios_users"]:
            return '<span class="chip c-both">الاتنين</span>'
        if e["android_users"]:
            return '<span class="chip c-and">أندرويد</span>'
        if e["ios_users"]:
            return '<span class="chip c-ios">iOS</span>'
        return '<span class="chip c-both">—</span>'

    err_rows = "".join(
        f'<tr><td class="en" style="direction:ltr;text-align:left;font-size:7.2pt;">{e["msg"]}</td>'
        f'<td class="en" style="font-weight:800;">{fmt(e["users"])}</td>'
        f'<td class="en">{fmt(e["events"])}</td>'
        f'<td>{plat_chip(e)}</td>'
        f'<td class="en" style="font-size:7pt;">{e["versions"]}</td>'
        f'<td>{"<span style=color:" + CGRAY + ";font-weight:800;>شبكي</span>" if e["kind"] == "net" else "<span style=color:" + CRED + ";font-weight:800;>برمجي</span>"}</td></tr>'
        for e in d["errors"])
    code_errors = [e for e in d["errors"] if e["kind"] == "code"]
    P.append(f'''
<div class="row2">
  <div class="col">{box("warn", "تصنيف الأخطاء",
    f"<b>{fmt(U['error'])}</b> مستخدم قابلهم خطأ واحد على الأقل = "
    f"<b>{R['error_hit']['v']:.0f}%</b> من كل المستخدمين.<br>"
    f"منهم <b>{fmt(es['code_users'])}</b> مستخدم قابلهم خطأ <b>برمجي</b> — "
    f"<b>دي شغل الهندسة</b>، و<b>{fmt(es['net_users'])}</b> قابلهم خطأ <b>شبكي</b> "
    f"(نت المستخدم) مابيتصلحش بالكود.<br>"
    f"<span class='mini'>الرقمين متداخلين — الشخص الواحد ممكن يكون قابله النوعين، "
    f"فمجموعهم أكبر من {fmt(U['error'])}. كل رقم فيهم عدد أشخاص حقيقي لوحده، "
    f"محسوب مستقل مش بجمع صفوف الجدول.</span>")}</div>
  <div class="col">{box("risk", "أولوية الإصلاح",
    (f"أعلى خطأ برمجي: <span class='en'>{code_errors[0]['msg'][:70]}</span> — "
     f"<b>{fmt(code_errors[0]['users'])}</b> مستخدم على "
     f"{code_errors[0]['os']} نسخة {en(code_errors[0]['versions'])}."
     if code_errors else "مافيش خطأ برمجي بارز هذا الأسبوع.")
    + " <b>ملاحظة منهجية:</b> التصنيف مبني على نص رسالة الخطأ فهو تقريبي — "
      "المطوّر لازم يأكّد كل واحدة قبل ما تتحوّل لتذكرة.")}</div>
</div>
<table class="tb">
  <tr><th style="text-align:left;width:38%;">رسالة الخطأ</th><th>مستخدمون متأثرون</th>
    <th>عدد المرات</th><th>المنصة</th><th>النسخة</th><th>النوع</th></tr>
  {err_rows}
</table>
<div class="mini">مرتّبة بعدد <b>الأشخاص</b> المتأثرين مش بعدد المرات — خطأ بيضرب شخص واحد
  ألف مرة أقل أهمية من خطأ بيضرب ألف شخص مرة واحدة.</div>''')

    # ── 3.2 payment failures ──
    P.append(divider("3.2", "فشل الدفع", "Payment Failures", L3_C))
    pf_rows = "".join(
        f'<tr><td class="en" style="direction:ltr;text-align:left;">{p["method"]}</td>'
        f'<td class="en" style="direction:ltr;text-align:left;">{p["reason"]}</td>'
        f'<td class="en" style="font-weight:800;">{fmt(p["users"])}</td>'
        f'<td class="en">{fmt(p["events"])}</td>'
        f'<td class="en">{fmt(p["android_users"])} / {fmt(p["ios_users"])}</td></tr>'
        for p in d["payfails"])
    P.append(f'''
<div class="row2">
  <div class="col"><div class="card"><h3>تفصيل فشل الدفع</h3>
    <table class="tb" style="margin:0;"><tr><th style="text-align:left;">الطريقة</th>
      <th style="text-align:left;">السبب</th><th>مستخدمون</th><th>مرات</th>
      <th>أندرويد / iOS</th></tr>{pf_rows}</table>
  </div></div>
  <div class="col">{box("warn", "السياق قبل ما تفتح تذكرة",
    f"نجاح الدفع على مستوى المستخدم <b>{R['pay_success']['v']:.1f}%</b> "
    f"({fmt(R['pay_success']['n'])} نجحوا من {fmt(R['pay_success']['d'])} حاولوا). "
    + d["payment_context"])}
    {box("fix", "المطلوب من الباك إند",
    f"<span class='en'>success_query_false</span> مش سبب فشل — دي نتيجة استعلام تحقق. "
    f"محتاجين نعرف: هل الدفع فشل فعلًا عند البوابة، ولا نجح والتطبيق ماقراش النتيجة صح؟ "
    f"لو التانية، فإحنا بنخسر طلبات ناجحة. مطلوب تسجيل كود الاستجابة الحقيقي من "
    f"<span class='en'>Paymob</span> في خاصية منفصلة.")}
  </div>
</div>''')

    # ── 3.3 UX friction ──
    P.append(divider("3.3", "احتكاك الواجهة", "UX Friction", L3_C))
    and_plat = next((p for p in d["platforms"] if p["dim"] == "Android"), None)
    ios_plat = next((p for p in d["platforms"] if p["dim"] == "iOS"), None)
    rage_note = ""
    if and_plat and ios_plat:
        if and_plat["rage_rate"] < 1 and ios_plat["rage_rate"] > 5:
            rage_note = (f"<b>أندرويد بيقول {and_plat['rage_rate']:.1f}% نقر غضب و iOS "
                         f"{ios_plat['rage_rate']:.0f}%.</b> الفرق ده مش معقول سلوكيًا — "
                         f"الأرجح إن <b>رصد نقرة الغضب مش شغّال على أندرويد أصلًا</b>. "
                         f"يعني الرقم الحقيقي أعلى من المعروض، ومينفعش نبني عليه قرار "
                         f"قبل ما الرصد يتفعّل على المنصتين.")
        else:
            rage_note = (f"نقر الغضب: أندرويد {and_plat['rage_rate']:.0f}% مقابل "
                         f"iOS {ios_plat['rage_rate']:.0f}% من مستخدمي كل منصة.")
    P.append(f'''
<div class="row2">
  <div class="col">{box("risk", "نقرات الغضب",
    f"<b>{fmt(U['rage'])}</b> مستخدم ({R['rage_hit']['v']:.0f}% من المستخدمين) نقروا بغضب — "
    f"ضغط سريع متكرر في نفس المكان، يعني حاجة مش بتستجيب أو مش واضحة. " + rage_note)}</div>
  <div class="col">{box("gap", "أكبر عائق أمام تصميم الحل",
    "اسم الشاشة راجع دايمًا <span class='en'>«Flutter»</span> بدل اسم الشاشة الحقيقية، "
    "فإحنا عارفين إن فيه إحباط بس <b>مش عارفين فين</b>. "
    "المطلوب من الموبايل: تمرير <span class='en'>$screen_name</span> حقيقي مع كل حدث. "
    "من غيره أي إعادة تصميم هتبقى تخمين.")}</div>
</div>
{box("fix", "مهام تصميم قابلة للتنفيذ دلوقتي (من غير انتظار تتبّع جديد)",
  f"1) زر «إعادة الطلب»: بيستخدمه {R['reorder_use']['v']:.0f}% بس من المشترين رغم إن "
  f"{d['repeat_rate']:.0f}% منهم بيكرروا الشراء فعلًا — الزر مش مكتشَف، يتنقل لمكان أوضح. "
  f"2) إعلانات الرئيسية: نسبة تجاهل {R['ads_ignore']['v']:.0f}% — تقليل التكرار أو تصغير المساحة. "
  f"3) شاشة «منطقتك غير مخدومة»: {fmt(U['uncovered'])} مستخدم بيوصلوها — تتحوّل من رسالة "
  f"رفض لنموذج تسجيل اهتمام («ابلغني لما توصلوا لعندي»).")}''')

    # ── 3.4 feature adoption ──
    P.append(divider("3.4", "تبنّي الميزات — بعدد المستخدمين", "Feature Adoption", L3_C))
    feat_rows = ""
    for f_ in d["features"][:14]:
        w = f_["reach"]
        feat_rows += (f'<tr><td>{f_["label"]}</td>'
                      f'<td class="en" style="direction:ltr;text-align:left;font-size:7pt;color:#94a3b8;">{f_["event"]}</td>'
                      f'<td class="en" style="font-weight:800;">{fmt(f_["users"])}</td>'
                      f'<td class="en">{f_["reach"]:.1f}%</td>'
                      f'<td class="en">{f_["per_user"]:.1f}</td>'
                      f'<td style="width:22%;"><div style="background:#f1f5f9;border-radius:4px;height:9px;">'
                      f'<div style="width:{min(100, w):.1f}%;background:{CPURPLE};height:100%;border-radius:4px;"></div>'
                      f'</div></td></tr>')
    P.append(f'''
<table class="tb">
  <tr><th>الميزة</th><th style="text-align:left;">الحدث</th><th>مستخدمون</th>
    <th>نسبة الوصول</th><th>مرات/مستخدم</th><th>المدى</th></tr>
  {feat_rows}
</table>
<div class="mini">«نسبة الوصول» = المستخدمون اللي استخدموا الميزة ÷ كل المستخدمين.
  «مرات/مستخدم» بتفرّق بين ميزة كتير ناس بتستخدمها مرة، وميزة ناس قليلة بتستخدمها كتير —
  التقارير القديمة كانت بترتّب بعدد الأحداث فبتخلط بين الاتنين.</div>''')

    # ── 3.5 data quality ──
    P.append(divider("3.5", "جودة البيانات والتتبّع", "Data Quality & Tracking", L3_C))
    dq_rows = "".join(
        f'<tr><td class="en" style="direction:ltr;text-align:left;">{q["field"]}</td>'
        f'<td>{q["label"]}</td>'
        f'<td class="en" style="font-weight:800;color:{CRED if q["fill_rate"] < 1 else CGREEN};">'
        f'{q["fill_rate"]:.1f}%</td>'
        f'<td class="en">{fmt(q["filled"])} / {fmt(q["total"])}</td>'
        f'<td>{"<b style=color:" + CRED + ";>فارغ تمامًا</b>" if q["fill_rate"] < 1 else "شغّال"}</td></tr>'
        for q in d["data_quality"])
    P.append(f'''
{box("risk", "أخطر اكتشاف في التقرير ده",
  f"حقول قيمة الطلب <b>موجودة على الحدث وبتوصل PostHog</b> — بس بقيمة <b>صفر</b> دايمًا. "
  f"ده أسوأ من إنها مش موجودة، لأنها بتبان كأنها بيانات لحد ما تتجمّع. "
  f"النتيجة: مفيش صافي إيراد، مفيش هامش لكل طلب، مفيش تكلفة توصيل، ومفيش متوسط عدد أصناف. "
  f"كل تحليل ربحية متوقّف على الإصلاح ده.")}
<table class="tb">
  <tr><th style="text-align:left;">الحقل على <span class="en">order_placed</span></th>
    <th>معناه</th><th>نسبة التعبئة</th><th>العدد</th><th>الحالة</th></tr>
  {dq_rows}
</table>
<table class="tb">
  <tr><th>الفجوة</th><th>أثرها على القرار</th><th>المطلوب</th><th>الأولوية</th></tr>
  <tr><td>قيم الطلب بتوصل صفر</td><td>لا صافي إيراد ولا هامش ولا تكلفة توصيل</td>
    <td class="en">subtotal, delivery_fee, discount_amount, items_count</td>
    <td><span class="chip c-p0">P0</span></td></tr>
  <tr><td>إسناد المتجر على الطلب</td>
    <td>store_id موجود على السلة والدفع لكن <b>مش على الطلب</b> — فمفيش ترتيب متاجر ولا هامش لكل متجر</td>
    <td class="en">store_id, stores_count on order_placed</td>
    <td><span class="chip c-p0">P0</span></td></tr>
  <tr><td>تسمية الشاشات</td><td>{fmt(U["rage"])} مستخدم محبط والشاشة مجهولة</td>
    <td class="en">$screen_name على كل حدث</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>رصد نقر الغضب على أندرويد</td><td>الرقم الحالي منحاز لـ iOS فمش قابل للمقارنة</td>
    <td>تفعيل الرصد في SDK أندرويد</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>منطقة التوصيل كخاصية</td><td>المدينة متحسبة بالاستنتاج من المتجر بدل ما تكون مسجّلة</td>
    <td class="en">zone / city on order_placed</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>سبب فشل الدفع الحقيقي</td><td>success_query_false مش سبب — مش عارفين فشل ولا خلل تحقق</td>
    <td class="en">gateway_response_code</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>بحث ناجح + الكلمة</td><td>{fmt(U["search_fail"])} مستخدم بحثوا وفشلوا ومش عارفين على إيه</td>
    <td class="en">search_performed (query, results_count)</td><td><span class="chip c-p2">P2</span></td></tr>
  <tr><td>سبب الإلغاء</td><td>{fmt(U["cancelled"])} مستخدم ألغوا بدون تشخيص</td>
    <td class="en">cancel_reason</td><td><span class="chip c-p2">P2</span></td></tr>
  <tr><td>خطأ منظّم للكراش</td><td>لا معدل كراش منفصل عن أخطاء الشبكة</td>
    <td class="en">$exception (type, is_fatal)</td><td><span class="chip c-p2">P2</span></td></tr>
  <tr><td>استمرارية باقة PostHog</td><td>انقطاع التتبّع بيلغي المقارنة الأسبوعية</td>
    <td>ترقية الباقة + حد تنبيه</td><td><span class="chip c-p1">P1</span></td></tr>
</table>
{box("info", "ملاحظة إيجابية",
  "أسماء الأحداث الأساسية (طلب / سلة / دفع / تغطية) نظيفة ومتّسقة ومفيش تكرار، "
  "و<span class='en'>store_id</span> موجود فعلًا على أحداث التصفّح والسلة والدفع — "
  "وده اللي خلّى إسناد المدينة ممكن أصلًا. الفجوات دي إضافات مطلوبة، "
  "مش إصلاح لحاجة مكسورة من الأساس.")}''')

    # ── 3.6 engineering action items ──
    P.append(divider("3.6", "مهام الفرق التقنية", "Engineering Action Items", L3_C))
    top3_code = code_errors[:3]
    eng_teams = [
        ("الباك إند — Backend", CPURPLE, [
            "تعبئة <span class='en'>subtotal / delivery_fee / discount_amount / items_count</span> "
            "بقيم حقيقية على <span class='en'>order_placed</span>.",
            "إضافة <span class='en'>store_id</span> و<span class='en'>stores_count</span> "
            "على <span class='en'>order_placed</span> (موجودين على السلة والدفع بالفعل).",
            "تسجيل كود استجابة <span class='en'>Paymob</span> الحقيقي بدل "
            "<span class='en'>success_query_false</span>."]),
        ("الموبايل — Mobile", CPURPLE, (
            [f"إصلاح <span class='en'>{e['msg'][:56]}</span> — {fmt(e['users'])} مستخدم "
             f"({e['os']}، نسخة {e['versions']})." for e in top3_code]
            or ["مافيش خطأ برمجي بارز هذا الأسبوع — يتراجع الأسبوع الجاي."])
            + ["تمرير <span class='en'>$screen_name</span> حقيقي بدل "
               "<span class='en'>Flutter</span> على كل حدث."]),
        ("التصميم — UX/UI", CPURPLE, [
            f"إعادة تموضع زر «إعادة الطلب» (استخدام {R['reorder_use']['v']:.0f}% مقابل "
            f"تكرار شراء فعلي {d['repeat_rate']:.0f}%).",
            f"مراجعة إعلانات الرئيسية (تجاهل {R['ads_ignore']['v']:.0f}%).",
            "تحويل شاشة «منطقة غير مخدومة» لنموذج تسجيل اهتمام."]),
        ("البيانات — Data", CPURPLE, [
            "حد تنبيه على استهلاك باقة PostHog قبل الوصول للسقف.",
            "إضافة <span class='en'>search_performed</span> و<span class='en'>cancel_reason</span>.",
            "تفعيل رصد <span class='en'>$rageclick</span> على أندرويد."]),
        ("الجودة — QA", CPURPLE, [
            f"اختبار الدفع لكل الطرق ({', '.join(p['method'] for p in d['pay_methods'][:4])}).",
            f"متابعة أخطاء أحدث النسخ ({', '.join(v['dim'] for v in d['versions'][:2])}).",
            "التأكد إن حقول الطلب بترجع قيم حقيقية بعد إصلاح الباك إند."]),
    ]
    cards = ""
    for name, col, items in eng_teams:
        lis = "".join(f"<li>{x}</li>" for x in items)
        cards += (f'<div class="kpi" style="width:calc(50% - 4px);border-top:3px solid {col};">'
                  f'<div style="font-weight:800;font-size:8.5pt;color:{CBLUE};margin-bottom:2px;">{name}</div>'
                  f'<ul class="tl">{lis}</ul></div>')
    P.append(f'<div class="kpi-grid">{cards}</div>')

    # version table — which build to watch
    ver_rows = "".join(
        f'<tr><td class="en">{v["dim"]}</td><td class="en">{fmt(v["users"])}</td>'
        f'<td class="en">{v["purchase_rate"]:.1f}%</td><td class="en">{v["error_rate"]:.0f}%</td>'
        f'<td class="en">{v["rage_rate"]:.0f}%</td>'
        f'<td class="en">{v["error_events"] / v["users"] if v["users"] else 0:.1f}</td></tr>'
        for v in d["versions"])
    P.append(f'''
<div class="card"><h3>حسب نسخة التطبيق — أي بيلد محتاج متابعة</h3>
  <table class="tb" style="margin:0;"><tr><th>النسخة</th><th>مستخدمون</th><th>نسبة الشراء</th>
    <th>نسبة الخطأ</th><th>نقر الغضب</th><th>أخطاء/مستخدم</th></tr>{ver_rows}</table>
  <div class="mini" style="margin-top:3px;">لو نسخة أحدث بتوري «نسبة خطأ» أعلى من اللي قبلها،
    دي إشارة انحدار (regression) تستاهل وقفة قبل ما التبنّي يكمّل.</div>
</div>
<div class="mini">نهاية الطبقة 3.</div>''')

    # ══════════════════════════════════════════════════════════════════════════
    # APPENDIX — GLOSSARY (generated from the same dict the report rendered from)
    # ══════════════════════════════════════════════════════════════════════════
    P.append('<div class="pagebreak"></div>')
    P.append(divider("+", "ملحق: قاموس المؤشرات", "Glossary of Metrics", CBLUE))
    P.append('''<div class="mini" style="margin-bottom:6px;">كل مؤشر ظهر في التقرير موجود هنا
      بمعادلته ومقامه وقيمته هذا الأسبوع. القيمة المكتوبة هنا هي <b>نفس</b> القيمة المعروضة فوق —
      متولّدة من نفس الرقم، فمستحيل تختلف.</div>''')
    gl = ""
    for g in build_glossary(d):
        gl += (f'<div class="g"><div class="gt">{g["ar"]} <span class="ge">{g["en"]}</span></div>'
               f'<div class="gf"><b>المعادلة:</b> {g["formula"]}</div>'
               f'<div class="gh">{g["howto"]}</div>'
               f'<div class="gv">هذا الأسبوع: {g["value"]} &nbsp;({g["detail"]})</div></div>')
    P.append(f'<div class="gl">{gl}</div>')

    P.append(divider("+", "مصطلحات عامة", "General Terms", CBLUE))
    gl2 = "".join(
        f'<div class="g"><div class="gt">{t} <span class="ge">{e}</span></div>'
        f'<div class="gf">{f_}</div><div class="gh">{h}</div></div>'
        for t, e, f_, h in CONCEPT_DEFS)
    P.append(f'<div class="gl">{gl2}</div>')

    # methodology
    P.append(f'''
<div class="src">
  <b>المنهجية:</b>
  <br>· <b>المقام الموحّد:</b> كل نسبة = مستخدمون فريدون ÷ مستخدمون فريدون
    (<span class="en">uniq(person_id)</span>). مافيش نسبة مبنية على أحداث أو جلسات.
  <br>· <b>نافذة اليوم:</b> 8 صباحًا لـ 4 صباحًا اليوم اللي بعده بتوقيت القاهرة (20 ساعة) —
    لأن من 4 لـ 8 ص التطبيق شبه واقف.
  <br>· <b>اليوم النشط:</b> يوم فيه {en(f"{5000:,}")} حدث أو أكتر. التقرير بيرجع لورا لحد
    {d["lookback_days"]} يوم لحد ما يجمع {AD} يوم نشط، فبيفضل قابل للمقارنة حتى لو التتبّع اتقطع.
  <br>· <b>إسناد المدينة:</b> موقع الإنترنت غير صالح هنا — شركات المحمول بتوجّه الترافيك
    لبوابة في القاهرة، فبتظهر طلبات «من القاهرة» والتطبيق أصلًا مش شغّال هناك. البديل:
    بنبني خريطة <b>متجر ← مدينة</b> من أحداث الـ {en("WiFi")} بس (اللي فيها الـ IP محلي حقيقي)،
    وبعدين بننسب كل مستخدم لمدينة المتاجر اللي فتحها فعلًا. الفصل بين المدينتين شبه تام
    (كل متجر ~100% مدينة واحدة)، والتغطية بتوصل ~99% من المستخدمين اللي فتحوا أي متجر.
  <br>· <b>الأطر المرجعية:</b> {en("North Star")} (Amplitude / Sean Ellis) ·
    {en("AARRR")} (Dave McClure) · {en("HEART")} (Google — Rodden et al.) ·
    {en("Lean Analytics")} (Croll &amp; Yoskovitz).
  <br>· <b>البيانات:</b> كل الأرقام محسوبة برمجيًا من PostHog (مشروع 8orders) للأيام:
    {'، '.join(ar_short(x) for x in d["active"])}.
    القراءة النوعية مكتوبة على الأرقام دي بدون أي إعادة حساب.
  <br>· <b>وقت التوليد:</b> {en(d["generated_at"])} (توقيت القاهرة).
</div>''')

    return HEAD + "".join(P) + '</body></html>'
