# -*- coding: utf-8 -*-
"""8Orders — Weekly Product Metrics: RENDER LAYER.

Same visual language, section order and components as the executive report that went
to management (build_report2.py) — 21 numbered sections + glossary appendix — but every
figure is driven by the weekly data dict from wpm_data.collect_week(). No hardcoded
business numbers live in this file.

Arabic RTL, Western digits, arrowheads pointing left (←) for RTL flows.
"""
import datetime as dt

CBLUE = "#1e3a5f"; CBLUE2 = "#2563eb"; CGREEN = "#16a34a"
CRED = "#dc2626"; CYEL = "#ca8a04"; CGRAY = "#64748b"
BG_G = "#f0fdf4"; BG_Y = "#fefce8"; BG_R = "#fef2f2"; BG_B = "#eff6ff"; BORD = "#e2e8f0"

AR_MONTHS = {1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
             7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"}
AR_DOW = {0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس",
          4: "الجمعة", 5: "السبت", 6: "الأحد"}


def ar_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {AR_MONTHS[d.month]} {d.year}"


def ar_full(iso):
    d = dt.date.fromisoformat(iso)
    return f"{AR_DOW[d.weekday()]} {d.day} {AR_MONTHS[d.month]}"


# ───────────────────────────── components ─────────────────────────────────────
def fmt(n):
    try:
        return f"{int(round(float(n))):,}"
    except Exception:
        return str(n)


def na(txt="غير متاح"):
    return f'<span style="color:{CGRAY};font-weight:600;font-size:7.6pt;">{txt}</span>'


def delta(cur, prev, good_up=True, pct=True, unit=""):
    if prev in (None, 0):
        return na("—")
    d = cur - prev
    p = d / prev * 100
    if abs(d) < 1e-9:
        return f'<span style="color:{CGRAY};font-weight:700;">ثابت</span>'
    up = d > 0
    col = CGREEN if (up == good_up) else CRED
    body = f'{"▲" if up else "▼"}&nbsp;{fmt(abs(d))}{unit}'
    if pct:
        body += f'&nbsp;({abs(p):.1f}%)'
    return f'<span style="color:{col};font-weight:800;" dir="ltr">{body}</span>'


def light(c):
    return (f'<span style="display:inline-block;width:11px;height:11px;border-radius:50%;'
            f'background:{c};vertical-align:middle;"></span>')


def flow(frm, to):
    """RTL 'from -> to': target sits on the LEFT with the arrowhead pointing at it."""
    return f'<span class="en" dir="ltr">{fmt(to)}&nbsp;←&nbsp;{fmt(frm)}</span>'


def gloss(term_txt, g):
    return f'{term_txt} <span class="gloss">({g})</span>'


def bar_row(label, value, maxv, color, right_txt=""):
    w = max(2, (value / maxv * 100) if maxv else 0)
    return (f'<div class="br"><div class="br-l">{label}</div>'
            f'<div class="br-t"><div class="br-f" style="width:{w:.1f}%;background:{color};"></div></div>'
            f'<div class="br-v" dir="ltr">{right_txt or fmt(value)}</div></div>')


def heat_color(r):
    a, b = (239, 246, 255), (30, 58, 95)
    c = tuple(int(a[i] + (b[i] - a[i]) * r) for i in range(3))
    return f'rgb({c[0]},{c[1]},{c[2]})'


def kpi_card(t_ar, t_en, value, unit, d_html, status, sub=""):
    return (f'<div class="kpi" style="border-top:3px solid {status};">'
            f'<div class="kpi-t">{t_ar} <span class="kpi-en">{t_en}</span></div>'
            f'<div class="kpi-v" dir="ltr">{value}<span class="kpi-u">{unit}</span></div>'
            f'<div class="kpi-d">{d_html}</div>'
            + (f'<div class="kpi-s">{sub}</div>' if sub else '') + '</div>')


def box(kind, title, body):
    m = {"info": (BG_B, CBLUE2, "ℹ"), "risk": (BG_R, CRED, "⚠"), "opp": (BG_G, CGREEN, "✚"),
         "warn": (BG_Y, CYEL, "◆"), "gap": ("#f1f5f9", CGRAY, "⊘")}
    bg, bd, ic = m[kind]
    return (f'<div class="box" style="background:{bg};border-right:4px solid {bd};">'
            f'<div class="box-t" style="color:{bd};">{ic} {title}</div>'
            f'<div class="box-b">{body}</div></div>')


def verdict_badge(v):
    """Render the health verdict as a CSS dot + text.

    The host has no emoji font, so a literal 🟢/🟡/🟠/🔴 renders as a tofu box.
    Map the colour word to a real coloured circle instead.
    """
    txt = str(v or "").strip()
    palette = [("🔴", CRED), ("🟠", "#ea580c"), ("🟡", CYEL), ("🟢", CGREEN)]
    col = CYEL
    for emoji, c in palette:
        if emoji in txt:
            col, txt = c, txt.replace(emoji, "").strip()
            break
    else:
        for word, c in [("حرِج", CRED), ("حرج", CRED), ("تحذير", "#ea580c"),
                        ("صحّي", CGREEN), ("صحي", CGREEN)]:
            if word in txt:
                col = c
                break
    return (f'{light(col)} <span class="hbadge" style="color:{col};">'
            f'{txt or "مستقر مع تنبيهات"}</span>')


def divider(num, ar, en):
    return (f'<div class="divider"><div class="dnum" dir="ltr">{num}</div>'
            f'<div class="dttl">{ar}<span class="dttl-en">{en}</span></div></div>')


def trend_svg(vals, labels, w=170, h=48, color=CBLUE2):
    """RTL time axis: oldest on the RIGHT, newest on the LEFT."""
    if len(vals) < 2:
        return ''
    mn, mx = min(vals), max(vals)
    rng = (mx - mn) or 1
    n = len(vals)
    pts = [(w - (8 + i * (w - 16) / (n - 1)), h - 11 - ((v - mn) / rng) * (h - 22))
           for i, v in enumerate(vals)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{color}"/>' for x, y in pts)
    labs = "".join(f'<text x="{pts[i][0]:.1f}" y="{h - 1}" font-size="6" fill="#94a3b8" '
                   f'text-anchor="middle">{labels[i]}</text>' for i in range(n))
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2.2"/>'
            f'{dots}{labs}</svg>')


def daybars(series, active, w=190, h=56):
    """Per-active-day order bars, newest on the LEFT (RTL)."""
    vals = [(d, series[d]["orders"]) for d in active if series.get(d)]
    if not vals:
        return ''
    mx = max(v for _, v in vals) or 1
    n = len(vals)
    bw = (w - 8) / n - 4
    out = ''
    for i, (d, v) in enumerate(vals):
        bh = max(3, v / mx * (h - 30))   # leave headroom for the value label
        x = w - 4 - (i + 1) * (bw + 4)
        out += (f'<rect x="{x:.1f}" y="{h - 12 - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
                f'rx="2" fill="{CGREEN if v == mx else CBLUE2}"/>'
                f'<text x="{x + bw / 2:.1f}" y="{h - 3}" font-size="5.6" fill="#94a3b8" '
                f'text-anchor="middle">{dt.date.fromisoformat(d).day}</text>'
                f'<text x="{x + bw / 2:.1f}" y="{h - 15 - bh:.1f}" font-size="5.8" '
                f'fill="#475569" text-anchor="middle" font-weight="700">{v}</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{out}</svg>'


def CSS(week_start, week_end):
    return r"""
@page { size:A4; margin:15mm 13mm 16mm 13mm;
  @bottom-right { content:"صفحة " counter(page) " / " counter(pages); font-family:"Cairo"; font-size:7.5pt; color:#94a3b8; }
  @bottom-left { content:"8Orders · تقرير مؤشرات المنتج الأسبوعي · """ + f"{ar_date(week_start)} – {ar_date(week_end)}" + r""""; font-family:"Cairo"; font-size:7.5pt; color:#94a3b8; }
}
* { box-sizing:border-box; }
body { font-family:"Cairo","Tajawal",sans-serif; direction:rtl; text-align:right; color:#1e293b; font-size:9pt; line-height:1.6; margin:0; }
h1,h2,h3 { margin:0; }
.en { font-family:"Cairo"; direction:ltr; unicode-bidi:isolate; font-weight:600; }
.gloss { font-size:7pt; color:#94a3b8; font-weight:500; }
.cover { background:linear-gradient(135deg,#1e3a5f 0%,#2b4a70 100%); color:#fff; padding:26px 24px; border-radius:14px; margin-bottom:14px; }
.cover .logo { direction:ltr; font-weight:900; font-size:26pt; letter-spacing:-1px; }
.cover .logo b { color:#4ade80; }
.cover h1 { font-size:20pt; font-weight:900; margin:10px 0 4px; }
.cover .sub { font-size:10.5pt; opacity:.9; font-weight:500; }
.cover .meta { margin-top:14px; display:flex; gap:20px; flex-wrap:wrap; font-size:8.5pt; }
.cover .meta b { display:block; font-size:11pt; font-weight:800; }
.note-avail { background:#fefce8; border:1px solid #fde68a; border-radius:8px; padding:9px 12px; font-size:8pt; color:#854d0e; margin-bottom:12px; }
.divider { display:flex; align-items:center; gap:10px; margin:17px 0 9px; border-bottom:2px solid #1e3a5f; padding-bottom:6px; break-after:avoid; }
.dnum { background:#1e3a5f; color:#fff; font-weight:900; font-size:11pt; width:30px; height:30px; border-radius:8px; display:flex; align-items:center; justify-content:center; }
.dttl { font-size:13pt; font-weight:800; color:#1e3a5f; }
.dttl-en { direction:ltr; font-weight:600; font-size:8.5pt; color:#94a3b8; margin-right:8px; }
.kpi-grid { display:flex; flex-wrap:wrap; gap:8px; }
.kpi { background:#fff; border:1px solid #e2e8f0; border-radius:9px; padding:9px 11px; width:calc(25% - 6px); box-shadow:0 1px 2px rgba(0,0,0,.03); break-inside:avoid; }
.kpi-t { font-size:7.6pt; color:#64748b; font-weight:600; min-height:22px; }
.kpi-en { direction:ltr; color:#b0bac9; font-size:6.6pt; }
.kpi-v { font-size:17pt; font-weight:900; color:#1e293b; line-height:1.1; margin:2px 0; }
.kpi-u { font-size:8pt; font-weight:700; color:#94a3b8; margin-right:3px; }
.kpi-d { font-size:7.8pt; } .kpi-s { font-size:7pt; color:#94a3b8; margin-top:2px; }
.br { display:flex; align-items:center; gap:8px; margin:3px 0; font-size:8pt; }
.br-l { width:36%; color:#334155; font-weight:600; }
.br-t { flex:1; background:#f1f5f9; border-radius:5px; height:14px; overflow:hidden; }
.br-f { height:100%; border-radius:5px; }
.br-v { width:76px; text-align:left; font-weight:800; color:#1e293b; }
.box { border-radius:8px; padding:9px 12px; margin:7px 0; break-inside:avoid; }
.box-t { font-weight:800; font-size:9pt; margin-bottom:3px; }
.box-b { font-size:8.2pt; color:#334155; line-height:1.55; }
table.tb { width:100%; border-collapse:collapse; font-size:8pt; margin:6px 0; }
table.tb th { background:#1e3a5f; color:#fff; font-weight:700; padding:6px 8px; text-align:right; font-size:7.8pt; }
table.tb td { padding:5px 8px; border-bottom:1px solid #eef2f7; }
table.tb tr:nth-child(even) td { background:#f8fafc; }
.tb .en { font-size:7.6pt; }
.row2 { display:flex; gap:12px; } .col { flex:1; }
.card { background:#fff; border:1px solid #e2e8f0; border-radius:9px; padding:11px 13px; margin:7px 0; break-inside:avoid; }
.card h3 { font-size:10pt; color:#1e3a5f; font-weight:800; margin-bottom:6px; }
.chip { display:inline-block; font-size:6.8pt; font-weight:800; padding:1px 6px; border-radius:20px; }
.c-p0 { background:#dc2626; color:#fff; } .c-p1 { background:#ea580c; color:#fff; } .c-p2 { background:#ca8a04; color:#fff; }
.c-mob { background:#ede9fe; color:#6d28d9; } .c-dt { background:#dbeafe; color:#1e40af; }
.c-ops { background:#fef9c3; color:#854d0e; } .c-eng { background:#e0e7ff; color:#3730a3; }
.hbadge { font-size:14pt; font-weight:900; }
.heat { display:flex; gap:2px; direction:ltr; }
.heat .hc { flex:1; text-align:center; }
.heat .hcell { height:26px; border-radius:3px; display:flex; align-items:center; justify-content:center; color:#fff; font-size:6.2pt; font-weight:800; }
.heat .hlab { font-size:5.8pt; color:#94a3b8; margin-top:1px; }
.small { font-size:7.6pt; color:#64748b; } .mini { font-size:7.4pt; color:#94a3b8; }
ul.tl { margin:4px 0; padding-right:16px; } ul.tl li { margin:2px 0; font-size:8.3pt; }
.gl { display:flex; flex-wrap:wrap; gap:7px; }
.gl .g { width:calc(50% - 4px); background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:7px 10px; break-inside:avoid; }
.gl .g b { color:#1e3a5f; font-size:8.6pt; } .gl .g div { font-size:7.8pt; color:#475569; margin-top:1px; }
.src { background:#f8fafc; border:1px dashed #cbd5e1; border-radius:8px; padding:8px 11px; font-size:7.4pt; color:#64748b; margin-top:8px; }
.src b { color:#475569; }
"""


# ───────────────────────────── the report ─────────────────────────────────────
def render(d, a):
    # JSON round-trips turn integer dict keys into strings; normalise so the
    # hour-of-day heatmap works whether the data came from PostHog or a fixture.
    d["hours"] = {int(k): int(v) for k, v in (d.get("hours") or {}).items()}

    W_ = d["week"]
    PW = d["pweek"]
    AD = d["active_days"]
    PD = d["per_day"]
    PPD = d["prev_per_day"]
    wow_ok = d["wow_ok"]

    def wow(key, good_up=True, unit=""):
        """Week-over-week on a per-ACTIVE-DAY basis — the only fair comparison when
        the two windows contain a different number of live days."""
        if not (wow_ok and PPD):
            return na("مقارنة أسبوعية غير متاحة")
        return delta(PD[key], PPD[key], good_up=good_up, unit=unit)

    P = []
    HEAD = ('<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>'
            + CSS(d["week_start"], d["week_end"]) + '</style></head><body>')

    # ===== Cover =====
    gap_days = [x for x in d["days"] if x not in d["active"]]
    P.append(f'''
<div class="cover">
  <div class="logo">8<b>Orders</b></div>
  <h1>تقرير مؤشرات المنتج — أسبوعي</h1>
  <div class="sub">تطبيق توصيل طعام وبقالة (الغردقة وأسيوط) · المؤشر الأهم: عدد الطلبات الناجحة</div>
  <div class="meta">
    <div>الأسبوع<b style="font-size:9.5pt;">{ar_date(d["week_start"])} – {ar_date(d["week_end"])}</b></div>
    <div>أيام فيها بيانات<b>{AD} من 7</b></div>
    <div>نافذة اليوم<b style="font-size:8.5pt;">8 صباحًا ← 4 صباحًا (20 ساعة)</b></div>
    <div>الطلبات الناجحة<b style="color:#4ade80;">{fmt(W_["orders"])} طلب</b></div>
    <div>المصدر<b>PostHog · 8orders</b></div>
  </div>
</div>''')

    if gap_days or not wow_ok:
        bits = []
        if gap_days:
            bits.append(
                f"<b>{len(gap_days)} يوم من الأسبوع مفيهم بيانات فعلية</b> "
                f"({'، '.join(ar_date(x) for x in gap_days)}) — بسبب توقّف تتبّع PostHog "
                f"(تجاوز حد الباقة المجانية). فكل المتوسطات في التقرير محسوبة على "
                f"<b>{AD} يوم نشط</b> فقط، مش على 7، والإجماليات بتمثّل الأيام النشطة دي.")
        if not wow_ok:
            bits.append("<b>مقارنة «الأسبوع اللي فات» غير متاحة</b> لأن الأسبوع السابق "
                        "مفيهوش بيانات صالحة — فأي نسبة تغيّر أسبوعية هتكون مضلِّلة، "
                        "وعشان كده مش معروضة. هتشتغل لوحدها لما يتراكم أسبوعان متصلان.")
        P.append('<div class="note-avail"><b>ملاحظة مهمة عن نطاق البيانات:</b> '
                 + " ".join(bits) + '</div>')

    # ===== 1. Executive Summary =====
    P.append(divider("01", "الملخص التنفيذي", "Executive Summary"))
    wins = a.get("wins") or []
    risks = a.get("risks") or []
    wins_html = "<br>".join(f"• {x}" for x in wins[:4])
    risks_html = "<br>".join(f"• {x}" for x in risks[:4])
    avg_day = W_["orders"] / AD
    P.append(f'''
<div class="card" style="border-top:4px solid {CYEL};">
  <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
    <div style="font-size:12pt;font-weight:900;">حالة المنتج هذا الأسبوع:
      {verdict_badge(a.get("verdict"))}</div>
    <div style="text-align:center;">{daybars(d["series"], d["active"])}
      <div class="mini">الطلبات في كل يوم نشط</div></div>
  </div>
  <div class="box-b" style="margin-top:6px;">{a.get("reading", "")}</div>
  {("<div class='mini'>" + a["note"] + "</div>") if a.get("note") else ""}
</div>
<div class="row2">
  <div class="col">{box("opp", "أحسن اللي حصل الأسبوع", wins_html)}
    {box("info", "الفرص",
       f"• سدّ التسرّب بين السلة وبدء الدفع ({100 - d['cart_to_checkout']:.0f}% بيخرجوا قبل الدفع).<br>"
       f"• استغلال «مشاركة التطبيق» ({fmt(W_['share'])} مرة) في عرض إحالة.<br>"
       f"• التقاط الطلب المكبوت القريب ({fmt(W_['cov_users'])} مستخدم من مناطق غير مخدومة).<br>"
       f"• رفع متوسط الطلب — دلوقتي {d['aov']:.0f} ج.م.")}</div>
  <div class="col">{box("risk", "محتاج متابعة", risks_html)}
    {box("warn", "المخاطر",
       f"• نسبة نجاح الدفع {d['pay_success']:.1f}% (المستهدف 98%+).<br>"
       f"• الاعتماد على مدينتين بس (الغردقة وأسيوط).<br>"
       f"• {fmt(W_['rage'])} نقرة غضب، {d['rage_ios_pct']:.0f}% منها على iOS "
       f"وبدون اسم شاشة — تفصيل في القسم 12.<br>"
       f"• {'مقارنة أسبوعية مش متاحة لحد ما البيانات تتراكم.' if not wow_ok else 'تتبّع ناقص بيعمّي بعض القرارات (القسم 13).'}")}</div>
</div>
<div class="mini">خلاصة للمدير في 15 ثانية: {a.get("takeaway",
  f"متوسط {fmt(avg_day)} طلب في اليوم النشط بمتوسط طلب {d['aov']:.0f} ج.م. "
  f"أكبر رافعة مفردة = تسرّب السلة قبل الدفع.")}</div>''')

    # ===== 2. North Star =====
    P.append(divider("02", "المؤشر الأهم (الطلبات الناجحة)", "North Star Metric"))
    act_rows = "".join(
        f'<tr><td>{ar_full(x)}</td><td class="en" style="font-weight:800;">{fmt(d["series"][x]["orders"])}</td>'
        f'<td class="en">{fmt(d["series"][x]["revenue"])}</td>'
        f'<td class="en">{(d["series"][x]["revenue"] / d["series"][x]["orders"]) if d["series"][x]["orders"] else 0:.0f}</td></tr>'
        for x in d["active"] if d["series"].get(x))
    best = max(d["active"], key=lambda x: d["series"][x]["orders"])
    worst = min(d["active"], key=lambda x: d["series"][x]["orders"])
    P.append(f'''
<div class="row2">
  <div class="col" style="flex:1.05;">
    <div class="card" style="border-top:4px solid {CGREEN};text-align:center;">
      <div style="font-size:9pt;color:{CGRAY};font-weight:700;">
        {gloss("إجمالي الطلبات الناجحة", "الطلب اللي اتعمل فعلاً واتأكد")} — <span class="en">Successful Orders</span></div>
      <div style="font-size:42pt;font-weight:900;color:{CGREEN};line-height:1.05;" dir="ltr">{fmt(W_["orders"])}</div>
      <div style="font-size:9.5pt;">متوسط <b dir="ltr">{fmt(avg_day)}</b> طلب في اليوم النشط</div>
      <div style="font-size:8.4pt;margin-top:3px;">مقابل الأسبوع اللي فات: {wow("orders")}</div>
    </div>
  </div>
  <div class="col" style="flex:1.25;">
    <table class="tb" style="margin:0;">
      <tr><th>اليوم</th><th>الطلبات</th><th>الإيراد (ج.م)</th><th>متوسط الطلب</th></tr>
      {act_rows}
      <tr><td><b>الإجمالي / المتوسط</b></td><td class="en" style="font-weight:800;">{fmt(W_["orders"])}</td>
        <td class="en" style="font-weight:800;">{fmt(W_["revenue"])}</td>
        <td class="en" style="font-weight:800;">{d["aov"]:.0f}</td></tr>
    </table>
  </div>
</div>
{box("info", "إزاي الرقم بيتكوّن؟",
  f"<b>السلسلة:</b> {fmt(W_['people'])} شخص دخل التطبيق ← {fmt(W_['cart_sess'])} جلسة حطّت في السلة "
  f"← {fmt(W_['checkout'])} بدء دفع ← <b>{fmt(W_['orders'])} طلب ناجح</b>. "
  f"<b>أعلى يوم:</b> {ar_full(best)} بـ {fmt(d['series'][best]['orders'])} طلب · "
  f"<b>أقل يوم:</b> {ar_full(worst)} بـ {fmt(d['series'][worst]['orders'])} طلب "
  f"(الفرق {fmt(d['series'][best]['orders'] - d['series'][worst]['orders'])} طلب). "
  f"<b>الإيراد الأسبوعي:</b> {fmt(W_['revenue'])} ج.م.")}''')

    # ===== 2B. Driver tree =====
    P.append(divider("★", "المؤشر الأهم ومحرّكاته الداعمة", "North Star & Input KPIs"))
    P.append(f'''<div style="text-align:center;margin:4px 0 10px;">
  <div style="display:inline-block;background:#1e3a5f;color:#fff;border-radius:10px;padding:8px 30px;">
    <div style="font-size:8pt;opacity:.85;">المؤشر الأهم — الطلبات الناجحة في الأسبوع</div>
    <div style="font-size:26pt;font-weight:900;color:#4ade80;line-height:1;" dir="ltr">{fmt(W_["orders"])}</div>
  </div>
  <div style="font-size:7.5pt;color:#94a3b8;margin-top:4px;">▼ الرقم ده بتكوّنه 5 محرّكات داعمة ▼</div>
</div>''')
    drivers = [
        ("1. الطلب", "Demand", CBLUE2, [
            ("مستخدم نشط", fmt(W_["people"])), ("جلسات", fmt(W_["sessions"])),
            ("تثبيتات", fmt(W_["installs"])), ("حسابات جديدة", fmt(W_["signups"]))]),
        ("2. التفعيل", "Activation", CBLUE2, [
            ("جلسات وصلت للسلة", fmt(W_["cart_sess"])),
            ("نسبة التفعيل", f'{W_["cart_sess"] / W_["sessions"] * 100 if W_["sessions"] else 0:.0f}%'),
            ("دخول كضيف", fmt(W_["guest"]))]),
        ("3. التحويل", "Conversion", CRED, [
            ("السلة ← الدفع", f'{d["cart_to_checkout"]:.0f}%'),
            ("الدفع ← طلب", f'{d["checkout_to_order"]:.0f}%'),
            ("تحويل الجلسة", f'{d["sess_conv"]:.1f}%')]),
        ("4. الجودة", "Quality", CYEL, [
            ("نجاح الدفع", f'{d["pay_success"]:.1f}%'),
            ("أخطاء غير شبكية", fmt(d["e_non"])),
            ("نقرات الغضب", fmt(W_["rage"]))]),
        ("5. التكرار", "Frequency", CYEL, [
            ("طلبات/مشترٍ", f'{d["orders_per_buyer"]:.2f}'),
            ("عميل طلب مرتين+", f'{d["repeat_rate"]:.0f}%'),
            ("إعادة الطلب", fmt(W_["reorder"]))]),
    ]
    dcards = ""
    for ar, en, color, rows in drivers:
        rws = "".join(
            f'<div style="display:flex;justify-content:space-between;font-size:7.4pt;margin-top:3px;'
            f'border-top:1px solid #f1f5f9;padding-top:2px;"><span style="color:#475569;">{k}</span>'
            f'<b dir="ltr">{v}</b></div>' for k, v in rows)
        dcards += (f'<div style="width:calc(20% - 6px);background:#fff;border:1px solid {BORD};'
                   f'border-top:3px solid {color};border-radius:9px;padding:8px 9px;break-inside:avoid;">'
                   f'<div style="font-weight:800;font-size:8.6pt;color:{CBLUE};">{ar}'
                   f'<div style="font-weight:600;font-size:6.6pt;color:#94a3b8;direction:ltr;">{en}</div>'
                   f'</div>{rws}</div>')
    P.append(f'<div style="display:flex;gap:7px;">{dcards}</div>')
    weakest = min([("3. التحويل", d["cart_to_checkout"])], key=lambda x: x[1])
    P.append(f'''
<div style="background:#f8fafc;border:1px solid {BORD};border-radius:9px;padding:9px 12px;margin:9px 0;font-size:8.2pt;color:#334155;">
  <b style="color:{CBLUE};">القيمة (Value) — بجانب المحرّكات:</b> مبتزوّدش <b>عدد</b> الطلبات،
  لكن بتحدّد لو الزيادة تتحوّل فلوس. متوسط الطلب <b dir="ltr">{d["aov"]:.0f}</b> ج.م ·
  الإيراد <b dir="ltr">{fmt(W_["revenue"])}</b> ج.م ·
  إيراد لكل مستخدم <b dir="ltr">{W_["revenue"] / W_["people"] if W_["people"] else 0:.0f}</b> ج.م.
</div>
{box("risk", "أضعف حلقة الأسبوع",
  f"المحرّك رقم 3 (التحويل): «السلة ← بدء الدفع» عند <b>{d['cart_to_checkout']:.0f}%</b> فقط. "
  f"ده أعلى محرّك أثرًا لو اشتغلنا عليه — تحسينه بيرفع المؤشر الأهم مباشرة.")}
<div class="mini">ملاحظة: دي محرّكات بنقرأها كاتجاهات، مش معادلة ضرب مظبوطة (فيه طلبات معادة بتتخطى بعض الخطوات).</div>''')

    # ===== 3. KPI Dashboard =====
    P.append(divider("03", "لوحة المؤشرات السريعة", "Executive KPI Dashboard"))
    P.append('<div class="kpi-grid">')
    P.append(kpi_card("الطلبات الناجحة", "Orders", fmt(W_["orders"]), "", wow("orders"), CGREEN,
                      f"متوسط {fmt(avg_day)}/يوم"))
    P.append(kpi_card("الإيراد", "Revenue", fmt(W_["revenue"]), "ج.م", wow("revenue"), CYEL))
    P.append(kpi_card("متوسط قيمة الطلب", "AOV", f'{d["aov"]:.0f}', "ج.م",
                      delta(d["aov"], d["prev_aov"]) if wow_ok else na("—"), CBLUE2))
    P.append(kpi_card("تحويل الجلسة", "Session Conv.", f'{d["sess_conv"]:.1f}', "%",
                      '<span class="mini">من كل 100 جلسة</span>', CBLUE2))
    P.append(kpi_card("مستخدم نشط", "Active Users", fmt(W_["people"]), "", wow("people"), CBLUE2,
                      "أفراد في الأسبوع"))
    P.append(kpi_card("الجلسات", "Sessions", fmt(W_["sessions"]), "", wow("sessions"), CGREEN))
    P.append(kpi_card("عدد المشترين", "Buyers", fmt(W_["buyers"]), "",
                      f'<span class="mini">تحويل {d["buyer_conv"]:.0f}%</span>', CGREEN))
    P.append(kpi_card("طلبات لكل مشترٍ", "Orders/Buyer", f'{d["orders_per_buyer"]:.2f}', "",
                      f'<span class="mini">طلب مرتين+: {d["repeat_rate"]:.0f}%</span>', CYEL))
    P.append(kpi_card("نجاح الدفع", "Payment Success", f'{d["pay_success"]:.1f}', "%",
                      '<span class="mini">المستهدف 98%+</span>', CYEL))
    P.append(kpi_card("فشل الدفع", "Payment Fails", fmt(W_["payfail"]), "",
                      wow("payfail", good_up=False), CRED, f"منها {fmt(d['sqf'])} تحقق"))
    P.append(kpi_card("أخطاء التطبيق", "Errors", fmt(W_["errors"]), "",
                      wow("errors", good_up=False), CRED,
                      f"{d['e_net'] / W_['errors'] * 100 if W_['errors'] else 0:.0f}% مشاكل نت"))
    P.append(kpi_card("أخطاء غير شبكية", "Non-network", fmt(d["e_non"]), "",
                      '<span class="mini">محتاجة مراجعة</span>', CYEL))
    P.append(kpi_card("نقرات الغضب", "Rageclicks", fmt(W_["rage"]), "",
                      f'<span class="mini">{d["rage_ios_pct"]:.0f}% على iOS</span>', CYEL,
                      "الشاشة غير محددة"))
    P.append(kpi_card("طلب من مناطق غير مخدومة", "Uncovered", fmt(W_["cov_users"]), "",
                      f'<span class="mini">{fmt(W_["cov_events"])} محاولة</span>', CYEL, "أفراد"))
    P.append(kpi_card("مشاركة التطبيق", "App Shares", fmt(W_["share"]), "",
                      wow("share"), CGREEN, "قناة إحالة"))
    P.append(kpi_card("تقييمات الطلبات", "Ratings", fmt(W_["ratings"]), "", wow("ratings"), CGREEN,
                      f'{W_["ratings"] / W_["orders"] * 100 if W_["orders"] else 0:.0f}% من الطلبات'))
    P.append('</div>')
    P.append('<div class="mini">مؤشرات لسه مش متتبَّعة (فجوة): زمن فتح التطبيق، زمن استجابة '
             'السيرفر، معدل الكراش المنفصل، مدة الجلسة، زمن التوصيل — التفصيل في القسم 13.</div>')

    # ===== 4. AARRR =====
    P.append(divider("04", "رحلة العميل (نموذج AARRR)", "Growth · AARRR"))
    P.append(f'''
<div class="mini" style="margin-bottom:4px;">{gloss("AARRR", "5 مراحل: جذب، تفعيل، احتفاظ، إحالة، إيراد — إطار Dave McClure لقياس نمو المنتج")}</div>
<table class="tb">
  <tr><th>المرحلة</th><th>المقياس</th><th>القيمة</th><th>القراءة بالبسيط</th></tr>
  <tr><td><b>الجذب</b> — Acquisition</td><td>تثبيتات · حسابات جديدة · دخول كضيف</td>
    <td class="en">{fmt(W_["installs"])} · {fmt(W_["signups"])} · {fmt(W_["guest"])}</td>
    <td>ناس بتحمّل التطبيق، بس اللي بيعمل حساب أقل بكتير ({W_["signups"] / W_["installs"] * 100 if W_["installs"] else 0:.0f}% من التثبيتات).</td></tr>
  <tr><td><b>التفعيل</b> — Activation</td><td>جلسات وصلت للسلة</td>
    <td class="en">{fmt(W_["cart_sess"])} ({W_["cart_sess"] / W_["sessions"] * 100 if W_["sessions"] else 0:.0f}%)</td>
    <td>دي بداية نية الشراء الحقيقية.</td></tr>
  <tr><td><b>الاحتفاظ</b> — Retention</td>
    <td>{gloss("عميل طلب أكتر من مرة", "خلال نفس الأسبوع")}</td>
    <td class="en">{fmt(d["repeat_buyers"])} ({d["repeat_rate"]:.1f}%)</td>
    <td>الأسبوع كامل خلّانا نقيسها فعليًا — مش تقدير (التفصيل في القسم 11).</td></tr>
  <tr><td><b>الإحالة</b> — Referral</td><td>مشاركة التطبيق</td>
    <td class="en">{fmt(W_["share"])}</td>
    <td>«الزباين بيرشّحوا التطبيق لبعض» — قناة مجانية تستاهل نستغلها.</td></tr>
  <tr><td><b>الإيراد</b> — Revenue</td><td>الفلوس · متوسط الطلب</td>
    <td class="en">{fmt(W_["revenue"])} · {d["aov"]:.0f}</td>
    <td>الإيراد بيتحدّد بمتوسط الطلب أكتر من عدد الطلبات.</td></tr>
</table>
{box("opp", "التوصية",
  f"بالترتيب: (1) تحويل الضيوف ({fmt(W_['guest'])}) لحسابات مسجّلة — بيفتح الاحتفاظ والإشعارات، "
  f"(2) استغلال المشاركة ({fmt(W_['share'])}) في عرض إحالة مقيس، "
  f"(3) رفع متوسط الطلب من {d['aov']:.0f} ج.م بباقات أو حد أدنى للتوصيل المجاني.")}''')

    # ===== 5. HEART =====
    P.append(divider("05", "تجربة المستخدم (نموذج HEART)", "HEART Framework"))
    P.append(f'''
<div class="mini" style="margin-bottom:4px;">{gloss("HEART", "إطار Google لقياس التجربة: سعادة، تفاعل، تبنّي، احتفاظ، نجاح المهمة")}</div>
<table class="tb">
  <tr><th>البُعد</th><th>المتاح للقياس</th><th>القيمة</th><th>الحالة</th></tr>
  <tr><td><b>السعادة</b> — Happiness</td><td>تقييمات الطلبات</td>
    <td class="en">{fmt(W_["ratings"])}</td>
    <td>{light(CGREEN)} {W_["ratings"] / W_["orders"] * 100 if W_["orders"] else 0:.0f}% من الطلبات اتقيّمت؛ متوسط الدرجة و{gloss("NPS", "مقياس الولاء")} لسه مش متتبعين.</td></tr>
  <tr><td><b>التفاعل</b> — Engagement</td><td>جلسات · مشاهدات منتج · نقرات غضب</td>
    <td class="en">{fmt(W_["sessions"])} · {fmt(W_["product"])} · {fmt(W_["rage"])}</td>
    <td>{light(CYEL)} تفاعل عالي، بس نقرات الغضب علامة إحباط.</td></tr>
  <tr><td><b>التبنّي</b> — Adoption</td><td>تبنّي أحدث نسختين</td>
    <td class="en">{d["new_ver_pct"]:.0f}%</td>
    <td>{light(CGREEN)} النسخ القديمة بتختفي.</td></tr>
  <tr><td><b>الاحتفاظ</b> — Retention</td><td>عميل طلب مرتين+ · طلبات/مشترٍ</td>
    <td class="en">{d["repeat_rate"]:.1f}% · {d["orders_per_buyer"]:.2f}</td>
    <td>{light(CYEL)} مقياس حقيقي بقى متاح بفضل الأسبوع الكامل.</td></tr>
  <tr><td><b>نجاح المهمة</b> — Task Success</td><td>تحويل الجلسة · نجاح الدفع</td>
    <td class="en">{d["sess_conv"]:.1f}% · {d["pay_success"]:.1f}%</td>
    <td>{light(CYEL)} نجاح الدفع المفروض يوصل 98%+.</td></tr>
</table>''')

    # ===== 6. Marketplace & Coverage =====
    P.append(divider("06", "صحة السوق والتغطية", "Marketplace & Coverage"))
    cov_rows = "".join(f'<tr><td>{r}</td><td class="en">{fmt(u)}</td><td class="en">{fmt(att)}</td></tr>'
                       for r, u, att in d["cov_regions"])
    cancel_total = W_["cancel_unpaid"] + W_["cancelled"]
    P.append(f'''
<div class="row2">
  <div class="col">{box("info", "جانب الطلب (Demand)",
    f"مستخدمون نشطون: <b>{fmt(W_['people'])}</b> · جلسات: <b>{fmt(W_['sessions'])}</b> · "
    f"طلبات ناجحة: <b>{fmt(W_['orders'])}</b>.<br>التطبيق بيخدم <b>الغردقة وأسيوط</b> بس.")}</div>
  <div class="col">{box("warn", "جانب العرض (Supply)",
    f"المتاح: <b>{fmt(W_['store'])}</b> فتح متجر و<b>{fmt(W_['select_rest'])}</b> اختيار مطعم. "
    f"أما عدد التجار النشطين، ونسبة قبول الطلب، وزمن التوصيل، والتأخير — "
    f"<b>مش متتبَّعة في PostHog</b> (غالبًا في السيرفر). القرار التشغيلي ناقص من غيرها.")}</div>
</div>
<div class="card"><h3>الطلب المكبوت — مناطق بيحاولوا يطلبوا منها وهي مش مخدومة</h3>
  <div class="box-b" style="margin-bottom:5px;">حدث <span class="en">area_not_covered</span> =
    <b>{fmt(W_["cov_events"])} محاولة</b> من <b>{fmt(W_["cov_users"])} مستخدم</b>
    (نفس الشخص بيحاول أكتر من مرة، فالعبرة بعدد الأشخاص).
    العناوين حقيقية — المستخدم كتبها بنفسه، مش تخمين موقع الإنترنت:</div>
  <table class="tb" style="margin:0;"><tr><th>المنطقة</th><th>عدد المستخدمين</th><th>عدد المحاولات</th></tr>{cov_rows}</table>
  <div class="mini" style="margin-top:4px;">بعض المستخدمين حاولوا في أكتر من منطقة، فمجموع الصفوف أكبر شوية من
    {fmt(W_["cov_users"])}. أقرب توسّع منطقي = جوه نفس المحافظتين، مش مدن بعيدة.</div>
</div>
<div class="row2">
  <div class="col"><table class="tb"><tr><th>مؤشر السوق</th><th>القيمة</th><th>الحالة</th></tr>
    <tr><td>{gloss("إلغاء أونلاين غير مدفوع", "Cancel_Unpaid_Online_Order")}</td>
      <td class="en">{fmt(W_["cancel_unpaid"])}</td><td>{light(CYEL)} يستحق متابعة</td></tr>
    <tr><td>{gloss("إلغاء طلب", "order_cancelled")}</td>
      <td class="en">{fmt(W_["cancelled"])}</td>
      <td>{light(CYEL)} {cancel_total / (W_["orders"] + cancel_total) * 100 if (W_["orders"] + cancel_total) else 0:.1f}% من إجمالي الطلبات</td></tr>
    <tr><td>نسبة القبول · زمن التوصيل · التأخير · سبب الإلغاء</td><td>—</td>
      <td>{light(CGRAY)} فجوة تتبّع (سيرفر)</td></tr>
  </table></div>
  <div class="col">{box("gap", "تنبيه دقة",
    "المدن اللي بتظهر في بيانات الموقع (<span class='en'>IP</span>) مش مكان التوصيل الحقيقي — "
    "شركات المحمول بتوجّه الإنترنت لبوابة في القاهرة. عشان كده مافيش «إيراد حسب المدينة» في التقرير، "
    "وبدالها تحليل التغطية الحقيقي فوق المبني على العنوان اللي المستخدم كتبه.")}</div>
</div>''')

    # ===== 7. Funnel =====
    P.append(divider("07", "قمع الشراء", "Product Funnel"))
    mx = W_["app_open"] or 1
    funnel_bars = "".join([
        bar_row("فتح التطبيق", W_["app_open"], mx, "#93c5fd"),
        bar_row("فتح متجر", W_["store"], mx, "#60a5fa"),
        bar_row("مشاهدة منتج", W_["product"], mx, "#3b82f6"),
        bar_row("إضافة للسلة", W_["cart"], mx, "#2563eb"),
        bar_row("بدء الدفع", W_["checkout"], mx, "#1d4ed8"),
        bar_row("طلب ناجح", W_["orders"], mx, CGREEN)])
    lift10 = 0.10 * W_["cart"]
    lift_orders = lift10 * (d["checkout_to_order"] / 100)
    P.append(f'''
<div class="mini" style="margin-bottom:4px;">{gloss("القمع", "خطوات العميل من فتح التطبيق للطلب؛ في كل خطوة ناس بتقع")}</div>
<div class="row2">
  <div class="col" style="flex:1.2;">
    <div class="card"><h3>عدد الأحداث في كل خطوة (الأسبوع)</h3>{funnel_bars}
    <div class="mini">المشاهدات أكتر من فتح المتجر لأن العميل بيتفرّج على كذا منتج في المتجر الواحد —
      الأرقام هنا بالأحداث مش بالأشخاص.</div></div>
  </div>
  <div class="col">
    <div class="card"><h3>أهم تحويل: السلة ← الطلب</h3>
      {bar_row("إضافة للسلة ← بدء الدفع", W_["checkout"], W_["cart"], CRED, f'{d["cart_to_checkout"]:.0f}%')}
      {bar_row("بدء الدفع ← طلب ناجح", W_["orders"], W_["checkout"], CGREEN, f'{d["checkout_to_order"]:.0f}%')}
      {bar_row("السلة ← الطلب (كلي)", W_["orders"], W_["cart"], CYEL, f'{d["cart_to_order"]:.0f}%')}
      <div class="mini" style="margin-top:4px;">أكبر تسرّب:
        <b style="color:{CRED};">{100 - d["cart_to_checkout"]:.0f}% ممّن حطّوا في السلة مايبدؤوش الدفع أصلاً</b>.
        اللي يبدأ الدفع، {d["checkout_to_order"]:.0f}% منهم بيكمّل بنجاح.</div>
    </div>
  </div>
</div>
{box("risk", "نقطة التدخّل الأولى — بالأرقام",
  f"من كل 100 واحد حطّ في السلة، {d['cart_to_checkout']:.0f} بس بيبدؤوا الدفع "
  f"({fmt(W_['checkout'])} من {fmt(W_['cart'])}) والباقي بيخرج. "
  f"لو حسّنّا الرقم ده 10 نقط بس، يبقى: 10% × {fmt(W_['cart'])} ≈ "
  f"<b>{fmt(lift10)} عملية بدء دفع زيادة في الأسبوع</b> ≈ حوالي "
  f"<b>{fmt(lift_orders)} طلب إضافي محتمل</b> (بنفس نسبة إتمام الدفع الحالية "
  f"{d['checkout_to_order']:.0f}%) ≈ {fmt(lift_orders * d['aov'])} ج.م إيراد. "
  f"الخطوات الوسط (الرئيسية/المنيو/عرض السلة/شاشة الدفع) لسه مش متتبَّعة كأحداث منفصلة — "
  f"إضافتها هتورّينا الخطوة الدقيقة اللي بيقعوا فيها.")}''')

    # ===== 8. Behaviour =====
    P.append(divider("08", "سلوك العميل", "Customer Behaviour"))
    hmax = max(d["hours"].values()) if d["hours"] else 1
    heat_cells = ""
    for h in range(24):
        v = d["hours"].get(h, 0)
        r = (v / hmax) if hmax else 0
        col = heat_color(r) if v else "#eef2f7"
        heat_cells += (f'<div class="hc"><div class="hcell" style="background:{col};'
                       f'color:{"#fff" if r > 0.4 else "#334155"};">{v if v else ""}</div>'
                       f'<div class="hlab">{h:02d}</div></div>')
    peak_h = max(d["hours"], key=lambda k: d["hours"][k]) if d["hours"] else 0
    night = sum(v for h, v in d["hours"].items() if h in (0, 1, 2, 3))
    pmax = max((c for _, c in d["pay"]), default=1) or 1
    pm_bars = "".join(
        bar_row(m, c, pmax, (CGREEN if "cash" in m.lower() else CBLUE2),
                f'{fmt(c)} · {c / W_["orders"] * 100 if W_["orders"] else 0:.0f}%')
        for m, c in d["pay"][:7])
    cash_share = sum(c for m, c in d["pay"] if "cash" in m.lower())
    P.append(f'''
<div class="card"><h3>أكتر ساعات الطلب (مجموع الأسبوع) — الرقم = عدد الطلبات في الساعة</h3>
  <div class="heat">{heat_cells}</div>
  <div class="mini" style="margin-top:5px;">الذروة الساعة <b>{peak_h}:00</b>
    ({fmt(d["hours"].get(peak_h, 0))} طلب على مدار الأسبوع). وفيه
    <b>استمرار قوي للطلبات بعد منتصف الليل</b> ({fmt(night)} طلب من 12ص لـ 4ص =
    {night / W_["orders"] * 100 if W_["orders"] else 0:.0f}% من الطلبات).
    من 4 لـ 8 صباحًا التطبيق شبه متوقّف (المطاعم مقفولة) — وعشان كده نافذة اليوم بتبدأ 8 صباحًا.</div>
</div>
<div class="row2">
  <div class="col"><div class="card"><h3>طرق الدفع (الأسبوع)</h3>{pm_bars}
    <div class="mini">الكاش <b>{cash_share / W_["orders"] * 100 if W_["orders"] else 0:.0f}%</b>
      من الطلبات، والباقي دفع رقمي. أعلى فشل في
      <span class="en">online / onlineWallet</span> — السياق في القسم 12.</div></div></div>
  <div class="col"><div class="card"><h3>سلوكيات تانية</h3>
    {bar_row("طلبات استخدمت فاوتشر", d["with_voucher"], W_["orders"], CBLUE2, f'{fmt(d["with_voucher"])} · {d["with_voucher"] / W_["orders"] * 100 if W_["orders"] else 0:.0f}%')}
    {bar_row("طلبات معادة (reorder)", W_["reorder"], W_["orders"], "#60a5fa", f'{fmt(W_["reorder"])} · {W_["reorder"] / W_["orders"] * 100 if W_["orders"] else 0:.0f}%')}
    {bar_row("طلبات اتقيّمت", W_["ratings"], W_["orders"], CGREEN, f'{fmt(W_["ratings"])} · {W_["ratings"] / W_["orders"] * 100 if W_["orders"] else 0:.0f}%')}
    {bar_row("سلة أكتر من متجر (فتح الشيت)", W_["multi_sheet"], W_["orders"], "#a78bfa", fmt(W_["multi_sheet"]))}
    <div class="mini">«سلة أكتر من متجر» بقت قابلة للقياس عن طريق
      <span class="en">user_open_multi_merchant_sheet</span> — التفصيل في القسم 10.</div>
  </div></div>
</div>''')

    # ===== 9. Search =====
    P.append(divider("09", "تحليلات البحث", "Search Analytics"))
    P.append(f'''
<div class="row2">
  <div class="col">{box("info", "المتاح هذا الأسبوع",
    f"بحث بدون نتيجة (<span class='en'>search_no_results</span>): <b>{fmt(W_['search_fail'])}</b> "
    f"على مدار {AD} يوم نشط (متوسط {fmt(W_['search_fail'] / AD)} في اليوم). "
    f"استخدام الفلاتر: <b>{fmt(next((c for _, ev, c in d['feats'] if ev == 'filter_applied'), 0))}</b>. "
    f"يعني الناس بتلاقي نتايجها في الأغلب، والفلاتر مستخدمة بكثافة.")}</div>
  <div class="col">{box("gap", "فجوة تتبّع البحث",
    "المتاح هو «بحث بدون نتيجة» بس. مفيش حدث «بحث ناجح» بيحمل الكلمة، فـ"
    "<span class='en'>CTR</span> البحث، وأكتر الكلمات بحثًا، ومعدل التخلّي بعد البحث "
    "<b>مش ممكن نحسبهم</b>. المطلوب من التطوير: حدث <span class='en'>search_performed</span> "
    "بخاصية الكلمة وعدد النتائج — ساعتها نعرف الناس بتدوّر على إيه ومش بتلاقيه.")}</div>
</div>''')

    # ===== 10. Feature Adoption =====
    P.append(divider("10", "استخدام الميزات", "Feature Adoption"))
    fmax = d["feats"][0][2] if d["feats"] else 1
    feat_rows = ""
    for ar, ev, c in d["feats"]:
        w = (c / fmax * 100) if fmax else 0
        feat_rows += (f'<tr><td>{ar}</td>'
                      f'<td class="en" style="direction:ltr;text-align:left;font-size:7.2pt;color:#94a3b8;">{ev}</td>'
                      f'<td class="en" style="font-weight:800;">{fmt(c)}</td>'
                      f'<td style="width:30%;"><div style="background:#f1f5f9;border-radius:4px;height:10px;">'
                      f'<div style="width:{w:.1f}%;background:{CBLUE2};height:100%;border-radius:4px;"></div>'
                      f'</div></td></tr>')
    def _f(ev):
        return next((c for _, e, c in d["feats"] if e == ev), 0)
    discard, click_ads = _f("discard_home_ads"), _f("click_on_home_ads")
    P.append(f'''
<div class="mini" style="margin-bottom:4px;">كل دي أحداث حقيقية راجعة من PostHog على مدار
  {AD} يوم نشط، مرتّبة بالاستخدام:</div>
<table class="tb">
  <tr><th>الميزة</th><th style="text-align:left;">الحدث</th><th>الاستخدام</th><th>المقياس</th></tr>
  {feat_rows}
</table>
<div class="row2">
  <div class="col">{box("warn", "ملاحظة عن الإعلانات",
    f"المستخدمون بيتجاهلوا إعلانات الرئيسية (<b>{fmt(discard)}</b>) بمعدل "
    f"<b>{discard / click_ads if click_ads else 0:.1f}×</b> أكتر من ما بيدوسوا عليها "
    f"(<b>{fmt(click_ads)}</b>) — الإعلانات في الرئيسية مزعجة أكتر ما هي فعّالة، "
    f"محتاجة مراجعة لمكانها أو محتواها.")}</div>
  <div class="col">{box("opp", "الفرص",
    f"«تصفّح الأصناف» (<b>{fmt(_f('category_tapped'))}</b>) هو السلوك الأساسي للاكتشاف — "
    f"نستثمر فيه بترتيب أذكى للأصناف. و«مشاركة التطبيق» ({fmt(W_['share'])}) قناة إحالة "
    f"مجانية نربطها بعرض مقيس.")}</div>
</div>
{box("opp", "الطلب من أكتر من متجر — بقى قابل للقياس",
  f"فيه حدث حقيقي اسمه <span class='en'>user_open_multi_merchant_sheet</span> = "
  f"<b>{fmt(W_['multi_sheet'])} مرة</b> هذا الأسبوع، يعني المستخدم فتح شيت «أكتر من متجر». "
  f"مع <span class='en'>user_select_restaurant</span> = <b>{fmt(W_['select_rest'])}</b>. "
  f"دي أقرب قياس متاح لتبنّي الميزة، ونسبتها للطلبات = "
  f"<b>{W_['multi_sheet'] / W_['orders'] * 100 if W_['orders'] else 0:.0f}%</b>.")}
{box("gap", "اللي لسه ناقص لقياس الميزة صح",
  f"حقل <span class='en'>store_id</span> على حدث الطلب "
  f"{'<b>فاضي في الطلبات</b>' if d['store_id_empty'] else 'موجود جزئيًا'}، فمفيش إسناد للمتجر — "
  f"يعني مش قادرين نقول <b>كام طلب فعلاً اتعمل من أكتر من متجر</b>، ولا نرتّب المتاجر حسب الطلبات، "
  f"ولا نحسب متوسط طلب لكل متجر. المطلوب من التطوير: تعبئة "
  f"<span class='en'>store_id</span> و<span class='en'>stores_count</span> على كل طلب. "
  f"فتح الشيت بيقيس <b>النية</b>، مش <b>الإتمام</b>.")}''')

    # ===== 11. Retention =====
    P.append(divider("11", "الاحتفاظ بالعملاء", "Retention"))
    P.append(f'''
{box("opp", "الأسبوع الكامل خلّى الاحتفاظ قابل للقياس",
  f"التقرير اليومي مكانش يقدر يقيس الاحتفاظ (محتاج أكتر من يوم). "
  f"مع {AD} يوم نشط بقى عندنا قياس حقيقي: من <b>{fmt(W_['buyers'])}</b> مشترٍ، "
  f"<b>{fmt(d['repeat_buyers'])}</b> طلبوا أكتر من مرة = <b>{d['repeat_rate']:.1f}%</b>، "
  f"ومنهم <b>{fmt(d['loyal_buyers'])}</b> طلبوا 3 مرات أو أكتر.")}
<div class="kpi-grid" style="margin-bottom:6px;">
  {kpi_card("عميل طلب مرتين+", "Repeat Buyers", f'{d["repeat_rate"]:.1f}', "%",
            f'<span class="mini">{fmt(d["repeat_buyers"])} من {fmt(W_["buyers"])}</span>', CGREEN)}
  {kpi_card("عميل طلب 3 مرات+", "Loyal Buyers", fmt(d["loyal_buyers"]), "",
            f'<span class="mini">{d["loyal_buyers"] / W_["buyers"] * 100 if W_["buyers"] else 0:.1f}% من المشترين</span>', CGREEN)}
  {kpi_card("طلبات لكل مشترٍ", "Orders/Buyer", f'{d["orders_per_buyer"]:.2f}', "",
            f'<span class="mini">على {AD} يوم</span>', CYEL)}
  {kpi_card("إعادة الطلب", "Reorder", fmt(W_["reorder"]), "",
            f'<span class="mini">{W_["reorder"] / W_["orders"] * 100 if W_["orders"] else 0:.1f}% من الطلبات</span>', CBLUE2)}
</div>
<table class="tb">
  <tr><th>مؤشر</th><th>القيمة</th><th>القراءة</th></tr>
  <tr><td>نسبة تكرار الشراء خلال الأسبوع</td><td class="en">{d["repeat_rate"]:.1f}%</td>
    <td>كل 10 مشترين، حوالي {d["repeat_rate"] / 10:.0f} رجعوا طلبوا تاني في نفس الأسبوع.</td></tr>
  <tr><td>زر «إعادة الطلب» (<span class="en">reorder_initiated</span>)</td>
    <td class="en">{fmt(W_["reorder"])}</td>
    <td>استخدام الزر أقل بكتير من التكرار الفعلي — يعني الناس بتعيد الطلب يدوي. فرصة لتسهيل الزر.</td></tr>
  <tr><td>حذف الحساب (<span class="en">remove_account</span>)</td>
    <td class="en">{fmt(W_["remove_account"])}</td>
    <td>{"إشارة تسرّب محدودة." if W_["remove_account"] < 50 else "يستحق تحقيق."}</td></tr>
</table>
{box("gap", "اللي لسه ناقص",
  f"{gloss('كوهورت D1/D7', 'نسبة الرجوع بعد يوم / بعد 7 أيام')} الحقيقي محتاج أسبوعين متصلين "
  f"من البيانات. لما يتوفّروا هيتفعّل تلقائيًا في التقرير. الرقم المعروض فوق هو "
  f"<b>تكرار داخل الأسبوع</b> — مؤشر سليم بس مش نفس D7.")}''')

    # ===== 12. Performance / Errors =====
    P.append(divider("12", "الأداء والأخطاء", "Performance & Errors"))
    def _err_kind(k):
        return (f'<span style="color:{CGRAY};font-weight:800;">مشكلة نت</span>' if k == "net"
                else f'<span style="color:{CRED};font-weight:800;">غير شبكي</span>')
    err_rows = "".join(
        f'<tr><td class="en" style="direction:ltr;text-align:left;">{m}</td>'
        f'<td class="en">{fmt(c)}</td><td>{_err_kind(k)}</td></tr>' for m, c, k in d["err_top"])
    top_code = next((f"{m} ({fmt(c)} مرة)" for m, c, k in d["err_top"] if k == "code"), "—")
    pf_rows = "".join(f'<tr><td class="en" style="direction:ltr;text-align:left;">{m}</td>'
                      f'<td class="en" style="direction:ltr;text-align:left;">{r}</td>'
                      f'<td class="en">{fmt(c)}</td></tr>' for m, r, c in d["payfail_rows"])
    P.append(f'''
<div class="row2">
  <div class="col">{box("warn", "تصنيف الأخطاء (الأسبوع)",
    f"الإجمالي: <b>{fmt(W_['errors'])}</b> على {AD} يوم نشط "
    f"(متوسط {fmt(W_['errors'] / AD)} في اليوم).<br>"
    f"شكلها مشاكل نت عند المستخدم (النت قطع / إشارة ضعيفة): "
    f"<b>{fmt(d['e_net'])}</b> ({d['e_net'] / W_['errors'] * 100 if W_['errors'] else 0:.0f}%) — "
    f"دي مش بتتصلح بالكود.<br>"
    f"<b>الباقي {fmt(d['e_non'])} "
    f"({d['e_non'] / W_['errors'] * 100 if W_['errors'] else 0:.0f}%) غير شبكية</b> — "
    f"دي المحتاجة مراجعة من المطوّر.")}</div>
  <div class="col">{box("risk", "محتاج مراجعة هندسية",
    f"أعلى خطأ غير شبكي: <span class='en'>{top_code}</span> — بيوقف تجربة ناس حقيقيين. "
    f"<b>مهم:</b> التصنيف مبني على نص رسالة الخطأ فهو تقريبي — المطوّر لازم يأكّد كل واحدة "
    f"قبل ما نعتبرها خلل مؤكد.")}</div>
</div>
<table class="tb">
  <tr><th style="text-align:left;">رسالة الخطأ</th><th>العدد</th><th>النوع</th></tr>
  {err_rows}
</table>
<div class="row2">
  <div class="col"><div class="card"><h3>فشل الدفع — التفصيل</h3>
    <table class="tb" style="margin:0;"><tr><th style="text-align:left;">الطريقة</th>
      <th style="text-align:left;">السبب</th><th>العدد</th></tr>{pf_rows}</table>
  </div></div>
  <div class="col">{box("warn", "فشل الدفع — سياق مهم",
    f"إجمالي المحاولات الفاشلة: <b>{fmt(W_['payfail'])}</b>، منها "
    f"<b>{fmt(d['sqf'])}</b> <span class='en'>success_query_false</span>. "
    f"نسبة نجاح الدفع الكلية <b>{d['pay_success']:.1f}%</b>. " + d["payment_context"])}</div>
</div>
{box("gap", "النقرات الغاضبة — الحقيقة الكاملة",
  f"<b>{fmt(W_['rage'])}</b> نقرة غضب، لكن: (1) "
  f"<b>{d['rage_ios_pct']:.0f}% منها على iOS</b> — وده يرجّح إن الرصد شغّال على iOS بس، "
  f"مش إن أندرويد مريح؛ (2) اسم الشاشة راجع دايمًا "
  f"<span class='en'>«Flutter»</span> فـ<b>مش قادرين نحدّد الشاشة</b>. "
  f"المطلوب: تسمية الشاشات + تفعيل الرصد على أندرويد قبل ما نبني عليها أي قرار.")}''')

    # ===== 13. Tracking Quality =====
    P.append(divider("13", "جودة التتبّع (الفجوات)", "Tracking Quality"))
    P.append(f'''
<table class="tb">
  <tr><th>الفجوة</th><th>أثرها على القرار</th><th>المطلوب</th><th>الأولوية</th></tr>
  <tr><td>تسمية الشاشات</td><td>{fmt(W_["rage"])} نقرة غضب بدون شاشة معروفة</td>
    <td class="en">$screen_name لكل شاشة</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>إسناد المتجر</td><td>مش عارفين الطلب من أنهي متجر ولا كام متجر</td>
    <td class="en">store_id, stores_count on order_placed</td><td><span class="chip c-p0">P0</span></td></tr>
  <tr><td>منطقة التوصيل كخاصية</td><td>مفيش تحليل جغرافي حقيقي للطلبات</td>
    <td class="en">zone / area on order_placed</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>تفاصيل قيمة الطلب</td><td>لا فصل رسوم/خصم/عناصر → مش قادرين نحسب صافي</td>
    <td class="en">delivery_fee, discount, items_count</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>خطوات القمع الوسط</td><td>مش عارفين الشاشة اللي بيتسرّبوا فيها بالظبط</td>
    <td class="en">cart_viewed, payment_screen_viewed</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>سبب الإلغاء</td><td>{fmt(W_["cancel_unpaid"] + W_["cancelled"])} إلغاء بدون تشخيص</td>
    <td class="en">cancel_reason</td><td><span class="chip c-p2">P2</span></td></tr>
  <tr><td>بحث ناجح + الكلمة</td><td>لا CTR بحث ولا كلمات مطلوبة</td>
    <td class="en">search_performed (query, results_count)</td><td><span class="chip c-p2">P2</span></td></tr>
  <tr><td>خطأ منظّم للكراش</td><td>لا معدل كراش منفصل عن أخطاء الشبكة</td>
    <td class="en">$exception (type, is_fatal)</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>استمرارية باقة PostHog</td><td>انقطاع 9–26 يوليو ضيّع أسبوعين مقارنة</td>
    <td>ترقية الباقة / حد تنبيه</td><td><span class="chip c-p1">P1</span></td></tr>
</table>
{box("info", "ملاحظة إيجابية",
  "أسماء الأحداث الأساسية (طلب / سلة / دفع / تغطية) نظيفة ومتّسقة ومفيش تكرار. "
  "الفجوات دي إضافات مطلوبة، مش إصلاح لحاجة مكسورة.")}''')

    # ===== 14. Segments =====
    P.append(divider("14", "شرائح المستخدمين", "User Segments"))
    os_rows = "".join(
        f'<tr><td>{n}</td><td class="en">{fmt(s)}</td><td class="en">{fmt(o)}</td>'
        f'<td class="en">{o / s * 100 if s else 0:.1f}%</td>'
        f'<td class="en">{e / s if s else 0:.2f}</td></tr>' for n, s, o, e in d["os_split"])
    vmax = d["versions"][0][1] if d["versions"] else 1
    ver_bars = "".join(bar_row(v, s, vmax, (CGREEN if i < 2 else "#cbd5e1"), fmt(s))
                       for i, (v, s) in enumerate(d["versions"][:6]))
    and_row = next((x for x in d["os_split"] if x[0] == "Android"), None)
    ios_row = next((x for x in d["os_split"] if x[0] == "iOS"), None)
    seg_note = "—"
    if and_row and ios_row and and_row[1] and ios_row[1]:
        ac = and_row[2] / and_row[1] * 100
        ic = ios_row[2] / ios_row[1] * 100
        hi, lo = ("iOS", "أندرويد") if ic > ac else ("أندرويد", "iOS")
        seg_note = (f'{hi} بيحوّل أعلى (<b>{max(ic, ac):.1f}%</b> مقابل {min(ic, ac):.1f}% لـ{lo}) '
                    f'مع إن أندرويد {and_row[1] / sum(x[1] for x in d["os_split"]) * 100:.0f}% '
                    f'من الجلسات — فرصة لتحسين تجربة {lo}.')
    P.append(f'''
<div class="row2">
  <div class="col"><div class="card"><h3>حسب نظام التشغيل</h3>
    <table class="tb" style="margin:0;"><tr><th>النظام</th><th>جلسات</th><th>طلبات</th>
      <th>تحويل</th><th>خطأ/جلسة</th></tr>{os_rows}</table>
    <div class="mini" style="margin-top:4px;">{seg_note}</div>
  </div></div>
  <div class="col"><div class="card"><h3>حسب نسخة التطبيق (جلسات)</h3>
    {ver_bars}
    <div class="mini" style="margin-top:4px;">تبنّي أحدث نسختين ≈
      <b>{d["new_ver_pct"]:.0f}%</b> — النسخ القديمة بتختفي.</div>
  </div></div>
</div>
<div class="row2">
  <div class="col">{box("info", "جديد مقابل عائد",
    f"تثبيتات جديدة <b>{fmt(W_['installs'])}</b> · حسابات جديدة <b>{fmt(W_['signups'])}</b> · "
    f"دخول كضيف <b>{fmt(W_['guest'])}</b> · تسجيل دخول <b>{fmt(W_['logins'])}</b>. "
    f"أغلب الطلبات من عملاء عايدين — المشترين <b>{fmt(W_['buyers'])}</b> مقابل "
    f"{fmt(W_['signups'])} حساب جديد.")}</div>
  <div class="col">{box("warn", "الاعتماد على مدينتين",
    "التطبيق في الغردقة وأسيوط بس، فأي مشكلة تشغيلية في وحدة منهم تأثّر على المؤشر الأهم كله. "
    "التوسّع المدروس (القسم 6) يقلّل المخاطرة دي.")}</div>
</div>''')

    # ===== 15. Revenue =====
    P.append(divider("15", "الإيراد", "Revenue"))
    P.append(f'''
<div class="kpi-grid" style="margin-bottom:6px;">
  {kpi_card("الإيراد (الأسبوع)", "Revenue", fmt(W_["revenue"]), "ج.م", wow("revenue"), CYEL)}
  {kpi_card("متوسط الطلب", "AOV", f'{d["aov"]:.0f}', "ج.م",
            delta(d["aov"], d["prev_aov"]) if wow_ok else na("—"), CBLUE2)}
  {kpi_card("إيراد لكل مستخدم", "Rev/User",
            f'{W_["revenue"] / W_["people"] if W_["people"] else 0:.0f}', "ج.م",
            '<span class="mini">تقريبي</span>', CBLUE2)}
  {kpi_card("إيراد لكل جلسة", "Rev/Session",
            f'{W_["revenue"] / W_["sessions"] if W_["sessions"] else 0:.0f}', "ج.م",
            '<span class="mini">تقريبي</span>', CBLUE2)}
  {kpi_card("إيراد يومي متوسط", "Rev/Day", fmt(W_["revenue"] / AD), "ج.م",
            f'<span class="mini">على {AD} يوم نشط</span>', CGREEN)}
  {kpi_card("إيراد لكل مشترٍ", "Rev/Buyer",
            f'{W_["revenue"] / W_["buyers"] if W_["buyers"] else 0:.0f}', "ج.م",
            f'<span class="mini">{d["orders_per_buyer"]:.2f} طلب لكل مشترٍ</span>', CGREEN)}
  {kpi_card("طلبات بفاوتشر", "Voucher Orders", fmt(d["with_voucher"]), "",
            f'<span class="mini">{d["with_voucher"] / W_["orders"] * 100 if W_["orders"] else 0:.0f}% من الطلبات</span>', CYEL)}
  {kpi_card("نسبة نجاح الدفع", "Payment Success", f'{d["pay_success"]:.1f}', "%",
            '<span class="mini">المستهدف 98%+</span>', CYEL)}
</div>
<div class="row2">
  <div class="col">{box("risk", "أهم قيد على الإيراد",
    f"الإيراد = عدد الطلبات × متوسط الطلب. متوسط الطلب دلوقتي "
    f"<b>{d['aov']:.0f}</b> ج.م، فأي نمو في العدد لوحده مش بيكبّر الإيراد بنفس النسبة. "
    f"كمان تفاصيل {gloss('GMV', 'إجمالي قيمة البضاعة')} (رسوم التوصيل / الخصم / عدد العناصر) "
    f"مش متتبَّعة، فمش قادرين نفصل <b>صافي</b> الإيراد عن الإجمالي — "
    f"وده بيمنع حساب هامش حقيقي لكل طلب.")}</div>
  <div class="col">{box("gap", "مش موجود في التقرير — وليه",
    "«الإيراد حسب المدينة» مش معروض لأن المدينة بتتحسب من موقع الإنترنت "
    "(<span class='en'>IP</span>) وهو غير دقيق لمكان التوصيل. البديل الصح = تحليل التغطية "
    "بالعناوين الحقيقية في القسم 6. وأفضل المطاعم / الأصناف كمان مش متتبَّعة كخصائص على الطلب "
    "(نفس فجوة <span class='en'>store_id</span>).")}</div>
</div>''')

    # ===== 16. Anomaly Detection =====
    P.append(divider("16", "كشف الشذوذ الآلي", "Anomaly Detection"))
    anoms = []
    if wow_ok and PPD:
        for key, label, good_up in [("orders", "الطلبات (متوسط يومي)", True),
                                    ("revenue", "الإيراد (متوسط يومي)", True),
                                    ("payfail", "فشل الدفع (متوسط يومي)", False),
                                    ("errors", "أخطاء التطبيق (متوسط يومي)", False),
                                    ("share", "مشاركة التطبيق", True),
                                    ("search_fail", "بحث بدون نتيجة", False)]:
            cur, prv = PD[key], PPD[key]
            if not prv:
                continue
            ch = (cur - prv) / prv * 100
            if abs(ch) < 15:
                continue
            good = (ch > 0) == good_up
            anoms.append((label, flow(prv, cur),
                          f'{light(CGREEN if good else CRED)} {"إيجابي" if good else "سلبي"}',
                          f'{"نضخّمه" if good else "نراجعه"} — تغيّر {abs(ch):.0f}%.'))
    if not anoms:
        # No baseline: flag internal outliers instead of inventing a comparison.
        if d["cart_to_checkout"] < 55:
            anoms.append(("تسرّب السلة قبل الدفع",
                          f'<span class="en" dir="ltr">{d["cart_to_checkout"]:.0f}%</span>',
                          f'{light(CRED)} سلبي', "أعلى رافعة تحويل — القسم 7."))
        if d["pay_success"] < 98:
            anoms.append(("نجاح الدفع تحت المستهدف",
                          f'<span class="en" dir="ltr">{d["pay_success"]:.1f}% / 98%</span>',
                          f'{light(CYEL)} تنبيه', "سياق Paymob للمحافظ — القسم 12."))
        if d["rage_ios_pct"] > 90:
            anoms.append(("نقرات الغضب مركّزة على منصة واحدة",
                          f'<span class="en" dir="ltr">{d["rage_ios_pct"]:.0f}% iOS</span>',
                          f'{light(CGRAY)} فجوة رصد', "الأرجح رصد ناقص على أندرويد."))
        if d["store_id_empty"]:
            anoms.append(("إسناد المتجر مفقود على كل الطلبات",
                          '<span class="en" dir="ltr">store_id = ∅</span>',
                          f'{light(CGRAY)} فجوة تتبّع', "يمنع تحليل المتاجر — القسم 10."))
        peak = max(d["hours"], key=lambda k: d["hours"][k]) if d["hours"] else 0
        anoms.append((f"تركّز الطلب في ساعة الذروة {peak}:00",
                      f'<span class="en" dir="ltr">{fmt(d["hours"].get(peak, 0))}</span>',
                      f'{light(CBLUE2)} تشغيلي', "تعزيز الطاقة التشغيلية وقت الذروة."))
    an_rows = "".join(f'<tr><td>{t}</td><td>{v}</td><td>{k}</td><td>{act}</td></tr>'
                      for t, v, k, act in anoms)
    P.append(f'''
<div class="mini" style="margin-bottom:4px;">{
  "المقارنة مع الأسبوع اللي فات على أساس <b>المتوسط اليومي</b> (لأن عدد الأيام النشطة مختلف)."
  if wow_ok else
  "مقارنة أسبوعية مش متاحة هذا الأسبوع، فالكشف هنا بيقارن المؤشرات <b>بمستهدفاتها</b> وبيرصد الفجوات الداخلية."
}</div>
<table class="tb">
  <tr><th>الإشارة</th><th>القيمة</th><th>النوع</th><th>الإجراء</th></tr>
  {an_rows}
</table>''')

    # ===== 17. Top Insights =====
    P.append(divider("17", "أهم الملاحظات", "Top Insights"))
    insights = [
        ("أكبر تسرّب: السلة ← بدء الدفع",
         f"{100 - d['cart_to_checkout']:.0f}% ممّن حطّوا في السلة مايبدؤوش الدفع "
         f"(السلة {fmt(W_['cart'])} ثم الدفع {fmt(W_['checkout'])})",
         f"أكبر رافعة تحويل مفردة ≈ {fmt(lift_orders)} طلب/أسبوع", "Product/UX", "p0", "عالية"),
        ("إسناد المتجر مفقود بالكامل",
         "store_id فاضي على الطلبات، فتبنّي «أكتر من متجر» بيتقاس بالنية بس "
         f"({fmt(W_['multi_sheet'])} فتح شيت)",
         "يمنع تحليل المتاجر والهامش", "Engineering/Data", "p0", "عالية"),
        ("خلل تحقق الدفع محتاج مراجعة",
         f"{fmt(d['sqf'])} من {fmt(W_['payfail'])} فشل دفع سببها success_query_false",
         "لو خلل تحقق بنخسر طلبات ناجحة", "Engineering", "p1", "متوسطة"),
        ("أخطاء غير شبكية محتاجة مراجعة",
         f"{fmt(d['e_non'])} خطأ غير شبكي، أبرزها {top_code}",
         "تعطّل تجربة + فقد تحويل", "Engineering", "p1", "متوسطة"),
        ("نقرات الغضب مجهولة الشاشة",
         f"{fmt(W_['rage'])} نقرة، {d['rage_ios_pct']:.0f}% على iOS، والشاشة غير محددة",
         "مش قابلة للتنفيذ قبل تسمية الشاشات", "UX + Data", "p1", "عالية"),
        ("الاحتفاظ بقى مقيسًا",
         f"{d['repeat_rate']:.1f}% من المشترين طلبوا أكتر من مرة، وطلبات/مشترٍ {d['orders_per_buyer']:.2f}",
         "أساس لقياس الولاء والـ LTV", "Product", "p2", "عالية"),
        ("الطلب المكبوت قريب مش بعيد",
         f"{fmt(W_['cov_users'])} مستخدم من مناطق غير مخدومة، أغلبهم أطراف الغردقة وقرى أسيوط",
         "توسّع داخل نفس المحافظتين", "Operations", "p2", "عالية"),
        ("إعلانات الرئيسية بتتجاهل أكتر مما بتتنقر",
         f"{fmt(discard)} تجاهل مقابل {fmt(click_ads)} نقرة "
         f"({discard / click_ads if click_ads else 0:.1f}× )",
         "مساحة مهدرة في أهم شاشة", "Product/Marketing", "p2", "عالية"),
        ("الطلب مستمر بعد منتصف الليل",
         f"{fmt(night)} طلب بين 12ص و4ص = "
         f"{night / W_['orders'] * 100 if W_['orders'] else 0:.0f}% من الطلبات",
         "تخطيط تشغيلي ليلي", "Operations", "p2", "عالية"),
        ("الاعتماد على مدينتين", "الغردقة وأسيوط بس", "مخاطرة تركّز", "Strategy", "p2", "عالية"),
    ]
    ins_rows = "".join(
        f'<tr><td><b>{i + 1}. {t}</b><div class="mini">{ev}</div></td><td>{im}</td><td>{o}</td>'
        f'<td><span class="chip c-{pr}">{pr.upper()}</span></td><td>{cf}</td></tr>'
        for i, (t, ev, im, o, pr, cf) in enumerate(insights))
    P.append(f'''
<table class="tb">
  <tr><th style="width:40%;">الملاحظة / الدليل</th><th>الأثر</th><th>المالك</th>
    <th>الأولوية</th><th>الثقة</th></tr>
  {ins_rows}
</table>''')

    # ===== 18. Opportunities (ICE) =====
    P.append(divider("18", "الفرص (ترتيب ICE)", "Opportunities · ICE"))
    opps = [
        ("تعبئة store_id و stores_count على الطلب", 8, 9, 8, "مكسب سريع",
         "يفتح تحليل المتاجر وقياس ميزة «أكتر من متجر» فعليًا"),
        ("تفعيل التتبّع الناقص (شاشات / منطقة / خطوات القمع)", 7, 9, 8, "مكسب سريع",
         "يفتح تحليل تشغيلي كامل بجهد بسيط"),
        ("مراجعة تحقق الدفع success_query_false", 9, 7, 6, "مكسب سريع",
         f"استرجاع طلبات نخسرها ({fmt(d['sqf'])} حالة/أسبوع)"),
        ("سدّ تسرّب السلة ← بدء الدفع", 9, 6, 5, "متوسط",
         f"أكبر رافعة تحويل ≈ {fmt(lift_orders)} طلب/أسبوع"),
        ("مراجعة الأخطاء غير الشبكية", 7, 7, 7, "متوسط",
         f"تقليل {fmt(d['e_non'])} خطأ وتحسين الثبات"),
        ("مراجعة إعلانات الرئيسية", 6, 7, 8, "مكسب سريع",
         "استرجاع مساحة أهم شاشة في التطبيق"),
        ("حملة إحالة على «شارك التطبيق»", 7, 6, 6, "متوسط",
         f"تضخيم قناة مجانية ({fmt(W_['share'])} مشاركة)"),
        ("رفع متوسط الطلب (باقات / حد أدنى للتوصيل)", 8, 5, 5, "استراتيجي",
         f"تحويل النمو لفلوس (AOV {d['aov']:.0f} ج.م)"),
        ("توسّع داخل أسيوط والغردقة", 6, 6, 4, "استراتيجي",
         f"التقاط طلب مكبوت ({fmt(W_['cov_users'])} مستخدم/أسبوع)"),
    ]
    opp_rows = "".join(
        f'<tr><td><b>{t}</b></td><td>{cat}</td><td class="en">{I}</td><td class="en">{C}</td>'
        f'<td class="en">{E}</td><td class="en" style="font-weight:800;">{(I + C + E) / 3:.1f}</td>'
        f'<td class="mini">{note}</td></tr>'
        for (t, I, C, E, cat, note) in sorted(opps, key=lambda x: -(x[1] + x[2] + x[3])))
    P.append(f'''
<div class="mini" style="margin-bottom:4px;">{gloss("ICE", "ترتيب الفرص بمتوسط ثلاثة: الأثر Impact + الثقة Confidence + السهولة Ease، من 10")}</div>
<table class="tb">
  <tr><th>الفرصة</th><th>الفئة</th><th>Impact</th><th>Confidence</th><th>Ease</th>
    <th>ICE</th><th>العائد المتوقّع</th></tr>
  {opp_rows}
</table>
<div class="mini">الصدارة لإصلاح فجوات التتبّع ومراجعة الدفع — أثر عالي وجهد قليل.</div>''')

    # ===== 19. Actions by team =====
    P.append(divider("19", "المهام حسب الفريق", "Action Items by Team"))
    teams = [
        ("المنتج — Product", [
            f"سدّ تسرّب السلة ← بدء الدفع (تجربة A/B) — العائد ≈ {fmt(lift_orders)} طلب/أسبوع.",
            "تعريف أحداث خطوات القمع الوسط والشاشات والمنطقة.",
            f"خطة رفع متوسط الطلب من {d['aov']:.0f} ج.م (باقات / حد أدنى)."]),
        ("الهندسة — Engineering", [
            f"تعبئة <span class='en'>store_id</span> و<span class='en'>stores_count</span> على كل طلب.",
            f"مراجعة <span class='en'>success_query_false</span>: فشل حقيقي ولا خلل تحقق؟ ({fmt(d['sqf'])} حالة).",
            f"مراجعة أعلى خطأ غير شبكي: <span class='en'>{top_code}</span>."]),
        ("البيانات — Data", [
            "تسمية الشاشات <span class='en'>$screen_name</span> وتفعيل رصد النقرات على أندرويد.",
            "إضافة <span class='en'>search_performed</span> و<span class='en'>cancel_reason</span>.",
            "حد تنبيه على باقة PostHog لمنع تكرار انقطاع 9–26 يوليو."]),
        ("الجودة — QA", [
            "اختبار الدفع لكل الطرق (<span class='en'>online / wallet / applePay</span>).",
            "اختبار سلة أكتر من متجر من فتح الشيت لحد إتمام الطلب.",
            f"متابعة أخطاء أحدث نسختين ({', '.join(v for v, _ in d['versions'][:2])})."]),
        ("التصميم — UX/UI", [
            "تبسيط الانتقال من السلة لشاشة الدفع (أكبر تسرّب).",
            "مراجعة مكان ومحتوى إعلانات الرئيسية (بتتجاهل أكتر مما بتتنقر).",
            "مراجعة تحميل الصور (أخطاء الصور متكررة)."]),
        ("التسويق — Marketing", [
            f"حملة إحالة مبنية على «شارك التطبيق» ({fmt(W_['share'])} مشاركة).",
            f"قياس عائد الفاوتشر ({fmt(W_['voucher'])} استخدام، {fmt(d['with_voucher'])} طلب).",
            f"تحويل الضيوف ({fmt(W_['guest'])}) لحسابات مسجّلة."]),
        ("العمليات — Operations", [
            f"خطة تغطية للطلب المكبوت القريب ({fmt(W_['cov_users'])} مستخدم/أسبوع).",
            f"تعزيز التشغيل وقت الذروة حوالي الساعة {peak_h}:00.",
            f"تغطية الطلب الليلي ({fmt(night)} طلب بين 12ص و4ص)."]),
        ("الدعم — Support", [
            f"تواصل مع مستخدمي الدفع الفاشل ({fmt(W_['payfail'])} محاولة).",
            f"متابعة أسباب الإلغاء يدويًا ({fmt(W_['cancel_unpaid'] + W_['cancelled'])}) لحد ما تتسجّل.",
            "رصد شكاوى ما بعد أخطاء الصور والمشاركة."]),
    ]
    team_cards = ""
    for name, items in teams:
        lis = "".join(f"<li>{x}</li>" for x in items)
        team_cards += (f'<div class="kpi" style="width:calc(33.33% - 6px);border-top:3px solid #1e3a5f;">'
                       f'<div style="font-weight:800;font-size:8.6pt;color:{CBLUE};margin-bottom:3px;">{name}</div>'
                       f'<ul class="tl">{lis}</ul></div>')
    P.append(f'<div class="kpi-grid">{team_cards}</div>')

    # ===== 20. Executive Decisions =====
    P.append(divider("20", "القرارات المقترحة للإدارة", "Executive Decisions"))
    P.append(f'''
<div class="row2">
  <div class="col">{box("risk", "أهم 5 مشاكل",
    f"1) تسرّب السلة ← بدء الدفع ({100 - d['cart_to_checkout']:.0f}%).<br>"
    f"2) إسناد المتجر مفقود بالكامل (store_id فاضي).<br>"
    f"3) خلل تحقق الدفع محتاج مراجعة ({fmt(d['sqf'])} حالة).<br>"
    f"4) أخطاء غير شبكية ({fmt(d['e_non'])}) محتاجة مراجعة.<br>"
    f"5) فجوات تتبّع بتعمّي القرار (القسم 13).")}</div>
  <div class="col">{box("opp", "أهم 5 فرص",
    f"1) سدّ تسرّب الدفع (≈ {fmt(lift_orders)} طلب/أسبوع).<br>"
    f"2) تفعيل التتبّع الناقص (أقل جهد وأعلى أثر).<br>"
    f"3) استرجاع الدفع الفاشل.<br>"
    f"4) رفع متوسط الطلب من {d['aov']:.0f} ج.م.<br>"
    f"5) التوسّع القريب داخل المحافظتين.")}</div>
</div>
<div class="card" style="border-top:3px solid {CBLUE};"><h3>أهم 10 قرارات هذا الأسبوع</h3>
<table class="tb" style="margin:0;">
  <tr><th>القرار</th><th>السبب</th><th>الأثر المتوقّع</th><th>المالك</th><th>الأولوية</th></tr>
  <tr><td>اعتماد تعبئة <span class="en">store_id</span></td><td>مفيش إسناد للمتجر</td>
    <td>تحليل متاجر + قياس ميزة متعدد المتاجر</td><td>Eng/Data</td>
    <td><span class="chip c-p0">P0</span></td></tr>
  <tr><td>تمويل إصلاح تسرّب السلة ← الدفع</td><td>أكبر رافعة تحويل</td>
    <td>≈ {fmt(lift_orders)} طلب/أسبوع ({fmt(lift_orders * d["aov"])} ج.م)</td>
    <td>Product</td><td><span class="chip c-p0">P0</span></td></tr>
  <tr><td>مراجعة خلل الدفع</td><td>يمكن يخفي طلبات ناجحة</td>
    <td>استرجاع طلبات</td><td>Eng</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>اعتماد أحداث التتبّع الناقصة</td><td>قرارات ناقصة الأدلة</td>
    <td>تحليل كامل</td><td>Data</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>ترقية باقة PostHog / حد تنبيه</td><td>انقطاع 9–26 يوليو ضيّع المقارنات</td>
    <td>رؤية مستمرة</td><td>Data/Fin</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>مراجعة أعلى 3 أخطاء غير شبكية</td><td>ثبات التطبيق</td>
    <td>− أخطاء وتخلّي</td><td>Eng</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>تسمية الشاشات + رصد أندرويد</td><td>{fmt(W_["rage"])} نقرة غضب مجهولة الشاشة</td>
    <td>رؤية للإحباط</td><td>UX/Data</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>اختبار رفع متوسط الطلب</td><td>الإيراد مقيّد بـ AOV</td>
    <td>+ فلوس لكل طلب</td><td>Product</td><td><span class="chip c-p1">P1</span></td></tr>
  <tr><td>مراجعة إعلانات الرئيسية</td><td>تجاهل {discard / click_ads if click_ads else 0:.1f}× النقر</td>
    <td>+ فعالية أهم شاشة</td><td>Product/Mkt</td><td><span class="chip c-p2">P2</span></td></tr>
  <tr><td>دراسة التوسّع القريب</td><td>طلب مكبوت جوه المحافظتين</td>
    <td>سوق إضافي</td><td>Ops</td><td><span class="chip c-p2">P2</span></td></tr>
</table></div>
<div class="row2">
  <div class="col">{box("info", "المؤشرات اللي نراقبها الأسبوع الجاي",
    f"(1) نسبة «السلة ← بدء الدفع» — دلوقتي {d['cart_to_checkout']:.0f}%. "
    f"(2) نسبة نجاح الدفع — دلوقتي {d['pay_success']:.1f}%. "
    f"(3) الأخطاء غير الشبكية — دلوقتي {fmt(d['e_non'])}. "
    f"(4) متوسط الطلب — دلوقتي {d['aov']:.0f} ج.م.")}
    {box("warn", "المخاطر",
    "استمرار فجوة إسناد المتجر · تسرّب السلة من غير تدخّل · "
    "الاعتماد على مدينتين · انقطاع بيانات جديد.")}</div>
  <div class="col">{box("risk", "أكتر مشكلة ممكن تأثّر على الفلوس",
    f"تسرّب «السلة ← بدء الدفع» عند {d['cart_to_checkout']:.0f}% — "
    f"أكبر رافعة مفردة على المؤشر الأهم.")}
    {box("risk", "أكتر فجوة بتعمّي القرار",
    "<span class='en'>store_id</span> فاضي — بيمنعنا نعرف الطلب من أنهي متجر، "
    "وبالتالي مفيش تحليل متاجر ولا هامش ولا قياس حقيقي لميزة «أكتر من متجر».")}
    {box("warn", "أكتر تجربة محتاجة تحسين",
    f"تجربة الدفع (نجاح {d['pay_success']:.1f}% لازم يوصل 98%+) "
    f"وشاشة الانتقال من السلة للدفع.")}</div>
</div>
<div style="break-inside:avoid;">
<div class="card" style="background:#1e3a5f;color:#fff;border:none;text-align:center;padding:14px;">
  <div style="font-size:8pt;opacity:.75;font-weight:700;">الخلاصة التنفيذية — Executive Takeaway</div>
  <div style="font-size:12.5pt;font-weight:900;line-height:1.55;margin-top:4px;">
    {a.get("takeaway",
      f"{fmt(W_['orders'])} طلب ناجح بمتوسط {fmt(avg_day)} في اليوم النشط و{d['aov']:.0f} ج.م لكل طلب.")}<br>
    أكبر رافعة = تسرّب السلة قبل الدفع · أكبر فجوة = إسناد المتجر.
  </div>
</div>
<div class="src">
  <b>المنهجية والمصادر:</b> المؤشرات مبنية على أطر عالمية معتمدة —
  المؤشر الأهم <span class="en">North Star</span> (Amplitude / Sean Ellis) ·
  رحلة العميل <span class="en">AARRR</span> (Dave McClure, 500 Startups) ·
  تجربة المستخدم <span class="en">HEART</span> (Google — Rodden et al.) ·
  مقاييس السوق (<span class="en">a16z Marketplace Metrics</span>) ·
  ترتيب الأولويات <span class="en">ICE</span> (Sean Ellis) / <span class="en">RICE</span> (Intercom) ·
  <span class="en">Lean Analytics</span> (Croll &amp; Yoskovitz).
  <br><b>البيانات:</b> كل الأرقام محسوبة برمجيًا من PostHog (مشروع 8orders) على نافذة عمل
  8ص–4ص بتوقيت القاهرة، لأيام: {'، '.join(ar_date(x) for x in d["active"])}.
  القراءة النوعية مكتوبة على الأرقام دي بدون أي إعادة حساب.
  <br><b>وقت التوليد:</b> <span class="en">{d["generated_at"]}</span> (توقيت القاهرة).
</div>
</div>''')

    # ===== Glossary =====
    P.append('<div style="break-before:page;"></div>')
    P.append(divider("+", "ملحق: قاموس المصطلحات", "Glossary"))
    glossary = [
        ("المؤشر الأهم — North Star", "الرقم الوحيد اللي بيلخّص نجاح المنتج. هنا: عدد الطلبات الناجحة."),
        ("محرّكات المؤشر — Input KPIs", "المؤشرات الداعمة اللي بتكوّن المؤشر الأهم: طلب، تفعيل، تحويل، جودة، تكرار."),
        ("اليوم النشط — Active Day", f"يوم عمل فيه بيانات تتبّع حقيقية. الأسبوع ده فيه {AD} يوم نشط من 7."),
        ("تحويل الجلسة — Session Conversion", f"من كل 100 جلسة، كام واحدة خلصت بطلب. الأسبوع ده {d['sess_conv']:.1f}."),
        ("طلبات لكل مشترٍ — Orders/Buyer", f"المشتري الواحد عمل كام طلب. الأسبوع ده {d['orders_per_buyer']:.2f}."),
        ("عميل متكرر — Repeat Buyer", f"عميل طلب أكتر من مرة في نفس الفترة. الأسبوع ده {d['repeat_rate']:.1f}%."),
        ("متوسط قيمة الطلب — AOV", "إجمالي الفلوس ÷ عدد الطلبات."),
        ("مستخدم نشط — DAU/WAU/MAU", "عدد الأشخاص اللي فتحوا التطبيق في يوم / أسبوع / شهر."),
        ("إجمالي المبيعات — GMV", "قيمة كل البضاعة المباعة قبل خصم أي عمولات أو رسوم."),
        ("الكوهورت — Cohort D1/D7", "مجموعة بدؤوا نفس اليوم، نشوف كام % رجع بعد يوم (D1) وبعد 7 أيام (D7)."),
        ("رحلة العميل — AARRR", "5 مراحل: جذب، تفعيل، احتفاظ، إحالة، إيراد."),
        ("تجربة المستخدم — HEART", "إطار جوجل: سعادة، تفاعل، تبنّي، احتفاظ، نجاح المهمة."),
        ("مقياس الولاء — NPS", "«هتنصح بالتطبيق لصاحبك؟» من 0 لـ 10. (مش متتبَّع حاليًا)."),
        ("الإحالة — Referral", "عميل حالي بيجيب عميل جديد عن طريق «شارك التطبيق»."),
        ("القمع — Funnel", "خطوات العميل من فتح التطبيق للطلب؛ في كل خطوة ناس بتقع."),
        ("التسرّب — Drop-off", "نسبة اللي بيخرجوا في خطوة قبل ما يكمّلوا."),
        ("نقرة الغضب — Rageclick", "المستخدم بيدوس بسرعة ومتكرر في نفس المكان = علامة إحباط."),
        ("ترتيب الأولويات — ICE/RICE", "تقييم كل فكرة بالأثر والثقة والسهولة عشان نرتّب الأهم."),
        ("خطأ شبكي مقابل غير شبكي", "الشبكي سببه نت المستخدم (مش بيتصلح بالكود)؛ غير الشبكي خلل في التطبيق."),
        ("إسناد المتجر — store_id", "خاصية على الطلب بتقول الطلب من أنهي متجر. حاليًا فاضية = فجوة."),
    ]
    P.append('<div class="gl">'
             + "".join(f'<div class="g"><b>{t}</b><div>{g}</div></div>' for t, g in glossary)
             + '</div>')

    return HEAD + "".join(P) + '</body></html>'
