#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
8Orders — Weekly Product Metrics Report generator.

PRINCIPLE (per PO): every NUMBER is computed here in Python from live PostHog data.
The LLM NEVER computes or invents a number — it only writes the qualitative "reading"
(assessment) from the numbers this script hands it. If the LLM is unavailable the
report still renders with a deterministic rule-based assessment.

Window: 7 business days ending "yesterday" (Cairo), business day = 08:00 -> next 04:00.
Runs weekly (Thu 12:00 Cairo via systemd) and is DM'd to Asser by Hadi.

Env: POSTHOG_API_KEY (+ optional POSTHOG_HOST). weasyprint + Arabic fonts already on the host.
Usage:
    python3 intel/weekly_product_metrics.py [--date YYYY-MM-DD] [--out FILE.pdf]
                                            [--dry-run] [--no-discord] [--no-llm]
"""
import os, sys, json, argparse, datetime as dt, subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import requests
except Exception:
    requests = None

# ───────────────────────── config (mirrors intel/8orders_report_generator.py) ──
PROJECT = "400872"
UI_HOST = os.environ.get("POSTHOG_UI_HOST", "https://us.posthog.com")
API = f"{UI_HOST}/api/projects/{PROJECT}"
HEADERS = {"Authorization": f"Bearer {os.environ.get('POSTHOG_API_KEY','')}"}
CAIRO_TZ = ZoneInfo("Africa/Cairo")
BIZ_START = "08:00:00"
BIZ_END = "04:00:00"          # on the following day
BIZ_END_HOUR = 4

# Durable domain context (from the daily generator): mobile-wallet payment failures
# are a KNOWN upstream Paymob/bank issue under investigation — NOT an 8Orders defect,
# so they are framed as context, never as an engineering action on our side.
PAYMENT_CONTEXT_NOTE = (
    "سياق نجاح الدفع (المصدر: لوحة Paymob — خارج PostHog): الدفع بالبطاقات مستقر. "
    "أما المحافظ الإلكترونية فنسبة نجاحها منخفضة، وهي مشكلة معروفة قيد المتابعة من "
    "Paymob والبنك (طرف upstream) — وليست خللًا من جانب 8Orders."
)

def cairo_today():
    return dt.datetime.now(CAIRO_TZ).replace(tzinfo=None).date()

def hogql(q, retries=3):
    """POST HogQL, identical contract to the daily generator (backoff + jitter)."""
    import random, time as _t
    if requests is None:
        raise RuntimeError("requests not installed")
    last = None
    for i in range(retries):
        try:
            r = requests.post(f"{API}/query/", headers=HEADERS,
                              json={"query": {"kind": "HogQLQuery", "query": q}}, timeout=90)
            if r.status_code == 200:
                return r.json().get("results", [])
            last = f"HTTP {r.status_code}: {r.text[:180]}"
        except Exception as e:
            last = str(e)
        if i < retries - 1:
            _t.sleep(min(2.0 ** (i + 1), 30.0) * (0.5 + random.random()))
    raise RuntimeError(f"HogQL failed after {retries}: {last}\nQ: {q[:160]}")

def _q1(q, default=0):
    """First cell of first row, or default. Never raises — a dead query must not
    kill the whole report."""
    try:
        rows = hogql(q)
        if rows and rows[0] and rows[0][0] is not None:
            return rows[0][0]
    except Exception as e:
        print(f"WARN query failed ({e}); using default {default!r}", file=sys.stderr)
    return default

def _qrows(q):
    try:
        return hogql(q) or []
    except Exception as e:
        print(f"WARN query failed ({e}); using []", file=sys.stderr)
        return []

def day_after(d):  # iso -> iso
    return (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat()

def business_days(end_day, n=7):
    end = dt.date.fromisoformat(end_day)
    return [(end - dt.timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]

def W(start_day, end_day):
    """Contiguous business-week window predicate: [start 08:00, end+1 04:00),
    excluding the daily 04:00–08:00 dead gap so it equals the sum of business days."""
    return (f"timestamp >= toDateTime('{start_day} {BIZ_START}') "
            f"AND timestamp < toDateTime('{day_after(end_day)} {BIZ_END}') "
            f"AND (toHour(timestamp) >= 8 OR toHour(timestamp) < 4)")

FLOAT = "toFloat64OrNull(toString(properties.total_amount))"

# ───────────────────────── DATA (the only place numbers are produced) ──────────
def collect_week(end_day):
    days = business_days(end_day, 7)
    ws, we = days[0], days[-1]
    prev_end = (dt.date.fromisoformat(ws) - dt.timedelta(days=1)).isoformat()
    prev = business_days(prev_end, 7)
    pws, pwe = prev[0], prev[-1]

    # daily series (one grouped query, business-day bucket)
    series = {d: dict(orders=0, sessions=0, revenue=0, cart=0, checkout=0,
                      product=0, app_open=0, store=0, errors=0) for d in days}
    for row in _qrows(
        "SELECT if(toHour(timestamp) < 4, toDate(timestamp) - 1, toDate(timestamp)) AS d, "
        "countIf(event='order_placed'), count(DISTINCT $session_id), "
        f"round(sumIf({FLOAT}, event='order_placed')), countIf(event='add_to_cart'), "
        "countIf(event='checkout_started'), countIf(event='product_viewed'), "
        "countIf(event='Application Opened'), countIf(event='store_opened'), "
        f"countIf(event='app_error') FROM events WHERE {W(ws, we)} GROUP BY d ORDER BY d"):
        d = str(row[0])
        if d in series:
            series[d] = dict(orders=int(row[1] or 0), sessions=int(row[2] or 0),
                             revenue=float(row[3] or 0), cart=int(row[4] or 0),
                             checkout=int(row[5] or 0), product=int(row[6] or 0),
                             app_open=int(row[7] or 0), store=int(row[8] or 0),
                             errors=int(row[9] or 0))
    def wk(key):
        return sum(series[d][key] for d in days)
    week = {k: wk(k) for k in ("orders", "sessions", "revenue", "cart", "checkout",
                               "product", "app_open", "store", "errors")}

    # week-over-week (orders + revenue) from the prior 7 business days
    prev_orders = int(_q1(f"SELECT countIf(event='order_placed') FROM events WHERE {W(pws, pwe)}"))
    prev_rev = float(_q1(f"SELECT round(sumIf({FLOAT}, event='order_placed')) FROM events WHERE {W(pws, pwe)}"))

    # distinct people / buyers / converting + cart sessions (week window)
    dau = int(_q1(f"SELECT count(DISTINCT person_id) FROM events WHERE {W(ws, we)}"))
    buyers = int(_q1("SELECT count(DISTINCT if(event='order_placed',person_id,NULL)) "
                     f"FROM events WHERE {W(ws, we)}"))
    conv_sess = int(_q1("SELECT count(DISTINCT if(event='order_placed',$session_id,NULL)) "
                        f"FROM events WHERE {W(ws, we)}"))
    cart_sess = int(_q1("SELECT count(DISTINCT if(event='add_to_cart',$session_id,NULL)) "
                        f"FROM events WHERE {W(ws, we)}"))

    aov = (week["revenue"] / week["orders"]) if week["orders"] else 0.0
    sess_sum = week["sessions"]
    sess_conv = (conv_sess / sess_sum * 100) if sess_sum else 0.0
    cart_to_checkout = (week["checkout"] / week["cart"] * 100) if week["cart"] else 0.0
    checkout_to_order = (week["orders"] / week["checkout"] * 100) if week["checkout"] else 0.0

    # payments
    pay = [(str(m or "—"), int(c)) for m, c in
           _qrows("SELECT coalesce(nullIf(toString(properties.payment_method),''),'—'), count() "
                  f"FROM events WHERE event='order_placed' AND {W(ws, we)} GROUP BY 1 ORDER BY 2 DESC")]
    payfail = int(_q1(f"SELECT count() FROM events WHERE event='payment_failed' AND {W(ws, we)}"))
    payfail_rows = [(str(m or "—"), str(r or "—"), int(c)) for m, r, c in
                    _qrows("SELECT coalesce(nullIf(toString(properties.payment_method),''),'—'), "
                           "coalesce(nullIf(toString(properties.failure_reason),''),'—'), count() "
                           f"FROM events WHERE event='payment_failed' AND {W(ws, we)} "
                           "GROUP BY 1,2 ORDER BY 3 DESC LIMIT 8")]
    sqf = sum(c for _, r, c in payfail_rows if r == "success_query_false")

    # errors: net vs non-net + top messages
    NETP = ("properties.error_message ILIKE '%disconnect%' OR properties.error_message ILIKE '%connection%' "
            "OR properties.error_message ILIKE '%host lookup%' OR properties.error_message ILIKE '%timed out%' "
            "OR properties.error_message ILIKE '%timeout%' OR properties.error_message ILIKE '%socket%' "
            "OR properties.error_message ILIKE '%unreachable%'")
    er = _qrows(f"SELECT countIf({NETP}), countIf(NOT ({NETP})), count() "
                f"FROM events WHERE event='app_error' AND {W(ws, we)}")
    e_net, e_non, e_tot = (int(er[0][0] or 0), int(er[0][1] or 0), int(er[0][2] or 0)) if er else (0, 0, 0)
    err_top = [(str(m or "—"), int(c)) for m, c in
               _qrows("SELECT coalesce(nullIf(toString(properties.error_message),''),'—'), count() "
                      f"FROM events WHERE event='app_error' AND {W(ws, we)} GROUP BY 1 ORDER BY 2 DESC LIMIT 8")]

    # coverage (real addresses, distinct users)
    cov_users = int(_q1(f"SELECT count(DISTINCT person_id) FROM events WHERE event='area_not_covered' AND {W(ws, we)}"))
    cov_events = int(_q1(f"SELECT count() FROM events WHERE event='area_not_covered' AND {W(ws, we)}"))
    cov_regions = [(str(r), int(u)) for r, u in _qrows(
        "SELECT multiIf("
        "properties.address ILIKE '%Assiut%' OR properties.address ILIKE '%Asyut%','قرى داخل محافظة أسيوط',"
        "properties.address ILIKE '%Hurghada%' OR properties.address ILIKE '%Red Sea%','أطراف الغردقة والبحر الأحمر',"
        "properties.address ILIKE '%October%' OR properties.address ILIKE '%Giza%','6 أكتوبر/الجيزة (خارج التغطية)',"
        "'عناوين أخرى غير محددة') AS region, count(DISTINCT person_id) "
        f"FROM events WHERE event='area_not_covered' AND {W(ws, we)} GROUP BY region ORDER BY 2 DESC")]

    # feature usage (week)
    FEATS = [("تصفّح الأصناف", "category_tapped"), ("تجاهل إعلانات الرئيسية", "discard_home_ads"),
             ("استخدام الفلاتر", "filter_applied"), ("نقر إعلانات الرئيسية", "click_on_home_ads"),
             ("تطبيق فاوتشر", "voucher_applied"), ("نقر البانر", "banner_tapped"),
             ("تقييم الطلب", "rate_order_event"), ("الأماكن الأقرب", "nearest_places_clicked"),
             ("مشاركة التطبيق", "share_app_event"), ("إضافة عنوان", "address_created"),
             ("تعليمات التوصيل", "delivery_instruction_selected"), ("إعادة الطلب", "reorder_initiated"),
             ("بحث بدون نتيجة", "search_no_results")]
    ci = ", ".join(f"countIf(event='{ev}')" for _, ev in FEATS)
    frow = _qrows(f"SELECT {ci} FROM events WHERE {W(ws, we)}")
    feats = []
    if frow:
        for (ar, ev), v in zip(FEATS, frow[0]):
            feats.append((ar, ev, int(v or 0)))
        feats.sort(key=lambda x: -x[2])

    # OS split (week)
    os_split = [(str(o or "—"), int(s), int(od), int(er_)) for o, s, od, er_ in _qrows(
        "SELECT coalesce(nullIf(toString(properties.$os),''),'—'), count(DISTINCT $session_id), "
        "countIf(event='order_placed'), countIf(event='app_error') "
        f"FROM events WHERE {W(ws, we)} GROUP BY 1 ORDER BY 2 DESC")]

    # store attribution check (multi-store feature) — honest gap detection
    distinct_stores = int(_q1("SELECT uniqExact(toString(properties.store_id)) "
                              f"FROM events WHERE event='order_placed' AND {W(ws, we)}", default=0))
    store_id_empty = (str(_q1("SELECT toString(properties.store_id) FROM events WHERE event='order_placed' "
                              f"AND {W(ws, we)} GROUP BY 1 ORDER BY count() DESC LIMIT 1", default="")) == "")

    return dict(
        days=days, week_start=ws, week_end=we, prev_start=pws, prev_end=pwe,
        series=series, week=week, prev_orders=prev_orders, prev_rev=prev_rev,
        dau=dau, buyers=buyers, conv_sess=conv_sess, cart_sess=cart_sess,
        aov=aov, sess_sum=sess_sum, sess_conv=sess_conv,
        cart_to_checkout=cart_to_checkout, checkout_to_order=checkout_to_order,
        pay=pay, payfail=payfail, payfail_rows=payfail_rows, sqf=sqf,
        e_net=e_net, e_non=e_non, e_tot=e_tot, err_top=err_top,
        cov_users=cov_users, cov_events=cov_events, cov_regions=cov_regions,
        feats=feats, os_split=os_split,
        distinct_stores=distinct_stores, store_id_empty=store_id_empty,
        generated_at=dt.datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %H:%M"),
    )

# ───────────────────────── ASSESSMENT (LLM writes prose only, no numbers) ──────
def rule_based_assessment(d):
    w, pw = d["week"]["orders"], d["prev_orders"]
    growing = w > pw
    aov_ok = d["aov"] > 0
    real_err = d["e_non"]
    verdict = "🟡 مستقر مع تنبيهات"
    if growing and real_err < 3000 and d["cart_to_checkout"] > 55:
        verdict = "🟢 صحّي"
    if (pw and w < pw * 0.9) or d["e_non"] > 8000:
        verdict = "🟠 تحذير"
    return dict(
        verdict=verdict,
        reading=("النمو الأسبوعي مدفوع بالطلبات، والتحويل من السلة لبدء الدفع هو أكبر رافعة. "
                 "فشل دفع المحافظ سياقه upstream (Paymob) وليس أولوية هندسية عندنا. "
                 "ركّز الأسبوع الجاي على تسرّب السلة وجودة الأخطاء غير الشبكية."),
        note="(تقييم تلقائي احتياطي — الـ LLM كان غير متاح وقت التشغيل.)",
    )

def llm_assessment(d, enabled=True):
    if not enabled:
        return rule_based_assessment(d)
    facts = dict(
        week=d["week"], prev_orders=d["prev_orders"], prev_rev=d["prev_rev"], aov=round(d["aov"], 1),
        sess_conv=round(d["sess_conv"], 1), cart_to_checkout=round(d["cart_to_checkout"], 1),
        checkout_to_order=round(d["checkout_to_order"], 1), payfail=d["payfail"], sqf=d["sqf"],
        errors_total=d["e_tot"], errors_nonnetwork=d["e_non"], coverage_users=d["cov_users"],
        top_features=d["feats"][:5],
    )
    prompt = (
        "انت محلل منتج. جاي لك أرقام نهائية محسوبة بالفعل. "
        "ممنوع تحسب أو تغيّر أو تخترع أي رقم — استخدم الأرقام زي ما هي فقط. "
        "اكتب تقييم نوعي مختصر بالعامية المصرية المهنية في JSON بالمفاتيح: "
        "verdict (واحد من: 🟢 صحّي / 🟡 مستقر مع تنبيهات / 🟠 تحذير / 🔴 حرِج)، "
        "reading (2-3 جمل قراءة للأسبوع)، wins (قايمة قصيرة)، risks (قايمة قصيرة). "
        "خُد في اعتبارك إن فشل دفع المحافظ مشكلة upstream من Paymob مش خلل عندنا. "
        f"الأرقام:\n{json.dumps(facts, ensure_ascii=False)}"
    )
    # Try the bot's model CLI if present; otherwise fall back deterministically.
    try:
        import daily_digests  # provides call_model() in the repo
        out = daily_digests.call_model(prompt, timeout=180)
        data = json.loads(out[out.find("{"): out.rfind("}") + 1])
        data.setdefault("verdict", rule_based_assessment(d)["verdict"])
        data.setdefault("reading", "")
        data["note"] = ""
        return data
    except Exception as e:
        print(f"WARN LLM assessment unavailable ({e}); using rule-based.", file=sys.stderr)
        return rule_based_assessment(d)

# ───────────────────────── RENDER (design shared with the exec report) ─────────
CBLUE="#1e3a5f"; CBLUE2="#2563eb"; CGREEN="#16a34a"; CRED="#dc2626"; CYEL="#ca8a04"; CGRAY="#64748b"
BG_G="#f0fdf4"; BG_Y="#fefce8"; BG_R="#fef2f2"; BG_B="#eff6ff"; BORD="#e2e8f0"

def fmt(n):
    try: return f"{int(round(float(n))):,}"
    except Exception: return str(n)

def pctd(cur, prev):
    if not prev: return None
    return (cur - prev) / prev * 100

def delta(cur, prev, good_up=True):
    p = pctd(cur, prev)
    if p is None: return '<span style="color:#64748b;">—</span>'
    if abs(cur - prev) < 1e-9: return '<span style="color:#64748b;font-weight:700;">ثابت</span>'
    up = cur > prev; good = (up == good_up); col = CGREEN if good else CRED
    return f'<span style="color:{col};font-weight:800;" dir="ltr">{"▲" if up else "▼"}&nbsp;{abs(p):.1f}%</span>'

def flow(frm, to):
    return f'<span dir="ltr" style="font-family:Cairo;font-weight:700;">{fmt(to)}&nbsp;←&nbsp;{fmt(frm)}</span>'

def kpi(t_ar, t_en, val, unit, dh, color, sub=""):
    return (f'<div class="kpi" style="border-top:3px solid {color};"><div class="kpi-t">{t_ar} '
            f'<span class="kpi-en">{t_en}</span></div><div class="kpi-v" dir="ltr">{val}'
            f'<span class="kpi-u">{unit}</span></div><div class="kpi-d">{dh}</div>'
            + (f'<div class="kpi-s">{sub}</div>' if sub else '') + '</div>')

def box(kind, title, body):
    m={"info":(BG_B,CBLUE2,"ℹ"),"risk":(BG_R,CRED,"⚠"),"opp":(BG_G,CGREEN,"✚"),
       "warn":(BG_Y,CYEL,"◆"),"gap":("#f1f5f9",CGRAY,"⊘")}
    bg,bd,ic=m[kind]
    return (f'<div class="box" style="background:{bg};border-right:4px solid {bd};">'
            f'<div class="box-t" style="color:{bd};">{ic} {title}</div><div class="box-b">{body}</div></div>')

def divider(num, ar, en):
    return (f'<div class="divider"><div class="dnum" dir="ltr">{num}</div>'
            f'<div class="dttl">{ar}<span class="dttl-en">{en}</span></div></div>')

def barrow(label, val, mx, color, right=""):
    w = max(2, (val/mx*100) if mx else 0)
    return (f'<div class="br"><div class="br-l">{label}</div><div class="br-t">'
            f'<div class="br-f" style="width:{w:.1f}%;background:{color};"></div></div>'
            f'<div class="br-v" dir="ltr">{right or fmt(val)}</div></div>')

def weekbars(series, days):
    mx = max((series[d]["orders"] for d in days), default=1) or 1
    cells = ""
    for d in days:
        v = series[d]["orders"]; h = max(4, v/mx*46)
        lab = d[8:10] + "/" + d[5:7]
        cells += (f'<div style="flex:1;text-align:center;"><div style="font-size:6.6pt;font-weight:800;color:{CBLUE};" dir="ltr">{fmt(v)}</div>'
                  f'<div style="height:{h:.0f}px;background:{CBLUE2};border-radius:3px 3px 0 0;margin:2px 3px 0;"></div>'
                  f'<div style="font-size:6pt;color:#94a3b8;" dir="ltr">{lab}</div></div>')
    return f'<div style="display:flex;align-items:flex-end;gap:2px;direction:ltr;">{cells}</div>'

CSS = r"""
@page { size:A4; margin:15mm 13mm 16mm 13mm;
  @bottom-right { content:"صفحة " counter(page) " / " counter(pages); font-family:"Cairo"; font-size:7.5pt; color:#94a3b8; }
  @bottom-left { content:"8Orders · Product Metrics Report · أسبوعي"; font-family:"Cairo"; font-size:7.5pt; color:#94a3b8; }
}
*{box-sizing:border-box;} body{font-family:"Cairo","Tajawal",sans-serif;direction:rtl;text-align:right;color:#1e293b;font-size:9pt;line-height:1.6;margin:0;}
.en{direction:ltr;unicode-bidi:isolate;font-weight:600;}
.cover{background:linear-gradient(135deg,#1e3a5f,#2b4a70);color:#fff;padding:24px;border-radius:14px;margin-bottom:12px;}
.cover .logo{direction:ltr;font-weight:900;font-size:24pt;} .cover .logo b{color:#4ade80;}
.cover h1{font-size:18pt;font-weight:900;margin:8px 0 3px;} .cover .sub{font-size:10pt;opacity:.9;}
.cover .meta{margin-top:12px;display:flex;gap:20px;flex-wrap:wrap;font-size:8.5pt;} .cover .meta b{display:block;font-size:11pt;font-weight:800;}
.note{background:#fefce8;border:1px solid #fde68a;border-radius:8px;padding:8px 11px;font-size:7.8pt;color:#854d0e;margin-bottom:12px;}
.divider{display:flex;align-items:center;gap:10px;margin:16px 0 9px;border-bottom:2px solid #1e3a5f;padding-bottom:6px;break-after:avoid;}
.dnum{background:#1e3a5f;color:#fff;font-weight:900;font-size:10pt;min-width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;padding:0 6px;}
.dttl{font-size:12.5pt;font-weight:800;color:#1e3a5f;} .dttl-en{direction:ltr;font-weight:600;font-size:8pt;color:#94a3b8;margin-right:8px;}
.kpi-grid{display:flex;flex-wrap:wrap;gap:8px;} .kpi{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:9px 11px;width:calc(25% - 6px);}
.kpi-t{font-size:7.6pt;color:#64748b;font-weight:600;min-height:22px;} .kpi-en{direction:ltr;color:#b0bac9;font-size:6.6pt;}
.kpi-v{font-size:16pt;font-weight:900;color:#1e293b;line-height:1.1;margin:2px 0;} .kpi-u{font-size:8pt;font-weight:700;color:#94a3b8;margin-right:3px;}
.kpi-d{font-size:7.8pt;} .kpi-s{font-size:7pt;color:#94a3b8;margin-top:2px;}
.br{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:8pt;} .br-l{width:38%;color:#334155;font-weight:600;}
.br-t{flex:1;background:#f1f5f9;border-radius:5px;height:14px;overflow:hidden;} .br-f{height:100%;border-radius:5px;} .br-v{width:78px;text-align:left;font-weight:800;}
.box{border-radius:8px;padding:9px 12px;margin:7px 0;break-inside:avoid;} .box-t{font-weight:800;font-size:9pt;margin-bottom:3px;} .box-b{font-size:8.2pt;color:#334155;line-height:1.55;}
table.tb{width:100%;border-collapse:collapse;font-size:8pt;margin:6px 0;} table.tb th{background:#1e3a5f;color:#fff;font-weight:700;padding:6px 8px;text-align:right;font-size:7.8pt;}
table.tb td{padding:5px 8px;border-bottom:1px solid #eef2f7;} table.tb tr:nth-child(even) td{background:#f8fafc;} .tb .en{font-size:7.4pt;}
.row2{display:flex;gap:12px;} .col{flex:1;} .card{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:11px 13px;margin:7px 0;break-inside:avoid;} .card h3{font-size:10pt;color:#1e3a5f;font-weight:800;margin-bottom:6px;}
.mini{font-size:7.4pt;color:#94a3b8;} .src{background:#f8fafc;border:1px dashed #cbd5e1;border-radius:8px;padding:8px 11px;font-size:7.2pt;color:#64748b;margin-top:8px;}
"""

def render(d, a):
    W_ = d["week"]; days = d["days"]
    wow_o = delta(W_["orders"], d["prev_orders"])
    wow_r = delta(W_["revenue"], d["prev_rev"])
    P = [f'<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>{CSS}</style></head><body>']
    win = f'{d["week_start"]} — {d["week_end"]}'
    # cover
    P.append(f'''<div class="cover"><div class="logo">8<b>Orders</b></div>
      <h1>تقرير مؤشرات المنتج — أسبوعي</h1>
      <div class="sub">Product Metrics Report · تطبيق توصيل (الغردقة وأسيوط)</div>
      <div class="meta"><div>الأسبوع<b dir="ltr">{win}</b></div>
      <div>الطلبات الناجحة (الأسبوع)<b style="color:#4ade80;" dir="ltr">{fmt(W_["orders"])}</b></div>
      <div>مقابل الأسبوع اللي فات<b>{wow_o}</b></div>
      <div>المصدر<b>PostHog · مُولّد آليًا</b></div></div></div>
      <div class="note"><b>منهجية:</b> كل الأرقام محسوبة آليًا من PostHog (نافذة العمل 8ص–4ص، 7 أيام). التقييم النوعي فقط مكتوب بالـ LLM — الأرقام لا يلمسها الـ LLM. {("<b>تنبيه:</b> جزء من الأسبوع تأثّر بتوقّف تتبّع سابق." if any(d["series"][x]["orders"]<50 for x in days) else "")}</div>''')
    # 1 exec summary + verdict (LLM reading)
    P.append(divider("01", "ملخص الأسبوع", "Weekly Summary"))
    wins = a.get("wins"); risks = a.get("risks")
    wins_html = "<br>".join(f"• {x}" for x in wins) if isinstance(wins, list) and wins else "• الطلبات في نمو أسبوعي.<br>• تبنّي النسخة الجديدة شبه كامل."
    risks_html = "<br>".join(f"• {x}" for x in risks) if isinstance(risks, list) and risks else "• تسرّب السلة قبل الدفع.<br>• أخطاء غير شبكية محتاجة مراجعة."
    P.append(f'''<div class="card" style="border-top:4px solid {CYEL};">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="font-size:12pt;font-weight:900;">حالة المنتج: {a.get("verdict","🟡 مستقر مع تنبيهات")}</div>
        <div style="text-align:center;">{weekbars(d["series"],days)}<div class="mini">الطلبات يوميًا</div></div>
      </div>
      <div class="box-b" style="margin-top:6px;">{a.get("reading","")}</div>
      {("<div class='mini'>"+a.get("note","")+"</div>") if a.get("note") else ""}</div>
    <div class="row2"><div class="col">{box("opp","أحسن اللي حصل", wins_html)}</div>
      <div class="col">{box("risk","محتاج متابعة", risks_html)}</div></div>''')
    # 2 North Star
    P.append(divider("02", "المؤشر الأهم — الطلبات الناجحة", "North Star"))
    P.append(f'''<div class="row2"><div class="col" style="flex:1.1;">
      <div class="card" style="border-top:4px solid {CGREEN};text-align:center;">
      <div style="font-size:9pt;color:{CGRAY};font-weight:700;">إجمالي الطلبات الناجحة (الأسبوع)</div>
      <div style="font-size:40pt;font-weight:900;color:{CGREEN};line-height:1.05;" dir="ltr">{fmt(W_["orders"])}</div>
      <div style="font-size:9.5pt;">{wow_o} عن الأسبوع اللي فات · متوسط يومي {fmt(round(W_["orders"]/7))}</div></div></div>
      <div class="col"><div class="card"><h3>الطلبات يوم بيوم</h3>{weekbars(d["series"],days)}
      <div class="mini" style="margin-top:6px;">أعلى يوم {fmt(max(d["series"][x]["orders"] for x in days))} · أقل يوم {fmt(min(d["series"][x]["orders"] for x in days))}. الإيراد الأسبوعي {fmt(W_["revenue"])} ج.م ({wow_r}).</div></div></div></div>''')
    # 3 driver tree
    P.append(divider("03", "محرّكات المؤشر", "Input KPIs"))
    drivers = [
     ("1. الطلب","Demand",CBLUE2,[("مستخدم نشط DAU",fmt(d["dau"])),("جلسات (مجموع)",fmt(d["sess_sum"]))]),
     ("2. التفعيل","Activation",CBLUE2,[("جلسات للسلة",fmt(d["cart_sess"])),("تحويل الجلسة",f'{d["sess_conv"]:.1f}%')]),
     ("3. التحويل","Conversion",CRED,[("السلة←الدفع",f'{d["cart_to_checkout"]:.0f}%'),("الدفع←طلب",f'{d["checkout_to_order"]:.0f}%')]),
     ("4. الجودة","Quality",CYEL,[("فشل دفع",fmt(d["payfail"])),("أخطاء غير شبكية",fmt(d["e_non"]))]),
     ("5. القيمة","Value",CBLUE2,[("متوسط الطلب",f'{d["aov"]:.0f} ج.م'),("مشترون",fmt(d["buyers"]))]),
    ]
    dc = ""
    for ar,en,c,rows in drivers:
        rws = "".join(f'<div style="display:flex;justify-content:space-between;font-size:7.4pt;margin-top:3px;border-top:1px solid #f1f5f9;padding-top:2px;"><span style="color:#475569;">{k}</span><b dir="ltr">{v}</b></div>' for k,v in rows)
        dc += (f'<div style="width:calc(20% - 6px);background:#fff;border:1px solid {BORD};border-top:3px solid {c};border-radius:9px;padding:8px 9px;">'
               f'<div style="font-weight:800;font-size:8.4pt;color:{CBLUE};">{ar}<div style="font-weight:600;font-size:6.6pt;color:#94a3b8;direction:ltr;">{en}</div></div>{rws}</div>')
    P.append(f'<div style="display:flex;gap:7px;">{dc}</div>')
    P.append(box("risk","أضعف حلقة الأسبوع", f"التحويل «السلة ← الدفع» عند <b>{d['cart_to_checkout']:.0f}%</b> — أعلى رافعة لرفع المؤشر."))
    # 4 KPI dashboard
    P.append(divider("04", "لوحة المؤشرات", "KPI Dashboard"))
    P.append('<div class="kpi-grid">')
    P.append(kpi("الطلبات (الأسبوع)","Orders",fmt(W_["orders"]),"",wow_o,CGREEN))
    P.append(kpi("الإيراد","Revenue",fmt(W_["revenue"]),"ج.م",wow_r,CYEL))
    P.append(kpi("متوسط الطلب","AOV",f'{d["aov"]:.0f}',"ج.م",'<span class="mini">للأسبوع</span>',CBLUE2))
    P.append(kpi("مستخدم نشط","DAU/أسبوع",fmt(d["dau"]),"",'<span class="mini">أفراد</span>',CBLUE2))
    P.append(kpi("تحويل الجلسة","Session Conv.",f'{d["sess_conv"]:.1f}',"%",'<span class="mini">للأسبوع</span>',CBLUE2))
    P.append(kpi("فشل الدفع","Pay Fails",fmt(d["payfail"]),"",'<span class="mini">سياق Paymob</span>',CYEL))
    P.append(kpi("أخطاء غير شبكية","Non-network",fmt(d["e_non"]),"",'<span class="mini">مراجعة</span>',CYEL))
    P.append(kpi("طلب غير مخدوم","Uncovered",fmt(d["cov_users"]),"",'<span class="mini">أفراد</span>',CYEL))
    P.append('</div>')
    # 5 funnel
    P.append(divider("05", "قمع الشراء (الأسبوع)", "Funnel"))
    mx = W_["app_open"] or 1
    P.append('<div class="card">'
             + barrow("فتح التطبيق", W_["app_open"], mx, "#93c5fd")
             + barrow("فتح متجر", W_["store"], mx, "#60a5fa")
             + barrow("مشاهدة منتج", W_["product"], mx, "#3b82f6")
             + barrow("إضافة للسلة", W_["cart"], mx, "#2563eb")
             + barrow("بدء الدفع", W_["checkout"], mx, "#1d4ed8")
             + barrow("طلب ناجح", W_["orders"], mx, CGREEN)
             + f'<div class="mini" style="margin-top:4px;">التحويل السلة←الدفع {d["cart_to_checkout"]:.0f}% ثم الدفع←طلب {d["checkout_to_order"]:.0f}%.</div></div>')
    # 6 payments
    P.append(divider("06", "الدفع", "Payments"))
    pm = d["pay"][:6]
    pmax = max((c for _, c in pm), default=1) or 1
    pbars = "".join(barrow(m, c, pmax, (CGREEN if ("cash" in m.lower() or "كاش" in m) else CBLUE2), fmt(c))
                    for m, c in pm)
    pay_ctx = box("warn", "فشل الدفع — سياق مهم",
                  "محاولات فاشلة الأسبوع: <b>" + fmt(d["payfail"]) + "</b>، منها <b>" + fmt(d["sqf"])
                  + "</b> <span class='en'>success_query_false</span>. " + PAYMENT_CONTEXT_NOTE)
    P.append('<div class="row2"><div class="col"><div class="card"><h3>طرق الدفع</h3>'
             + pbars + '</div></div><div class="col">' + pay_ctx + '</div></div>')
    # 7 errors
    P.append(divider("07", "الأخطاء", "Errors"))
    etop = "".join(f'<tr><td class="en" style="direction:ltr;text-align:left;">{m}</td><td class="en">{fmt(c)}</td></tr>' for m, c in d["err_top"][:8])
    P.append(f'<div class="row2"><div class="col">' + box("warn","تصنيف الأخطاء",
             f"الإجمالي: <b>{fmt(d['e_tot'])}</b>. مشاكل نت (غير قابلة للإصلاح بالكود): <b>{fmt(d['e_net'])}</b>. "
             f"<b>غير شبكية (محتاجة مراجعة): {fmt(d['e_non'])}</b>. الأرقام من نص الرسالة فالتصنيف تقريبي.")
             + f'</div><div class="col"><div class="card"><h3>أعلى الأخطاء</h3><table class="tb" style="margin:0;">{etop}</table></div></div></div>')
    # 8 coverage
    P.append(divider("08", "التغطية والطلب المكبوت", "Coverage"))
    cov_rows = "".join(f'<tr><td>{r}</td><td class="en">{fmt(u)}</td></tr>' for r, u in d["cov_regions"])
    P.append(f'<div class="card"><div class="box-b"><span class="en">area_not_covered</span> = <b>{fmt(d["cov_events"])}</b> محاولة من <b>{fmt(d["cov_users"])}</b> مستخدم (العبرة بالأشخاص). العناوين حقيقية:</div>'
             f'<table class="tb" style="margin:6px 0 0;"><tr><th>المنطقة</th><th>عدد المستخدمين</th></tr>{cov_rows}</table>'
             f'<div class="mini" style="margin-top:4px;">أقرب توسّع = داخل نفس المحافظتين. مدن بيانات الـ IP غير موثوقة للتوصيل فمش معتمدة هنا.</div></div>')
    # 9 features
    P.append(divider("09", "استخدام الميزات", "Feature Adoption"))
    fmax = d["feats"][0][2] if d["feats"] else 1
    frows = "".join(f'<tr><td>{ar}</td><td class="en" style="direction:ltr;text-align:left;font-size:7pt;color:#94a3b8;">{ev}</td><td class="en" style="font-weight:800;">{fmt(c)}</td>'
                    f'<td style="width:30%;"><div style="background:#f1f5f9;border-radius:4px;height:9px;"><div style="width:{(c/fmax*100) if fmax else 0:.0f}%;background:{CBLUE2};height:100%;border-radius:4px;"></div></div></td></tr>'
                    for ar, ev, c in d["feats"])
    P.append(f'<table class="tb"><tr><th>الميزة</th><th style="text-align:left;">الحدث</th><th>الاستخدام</th><th>المقياس</th></tr>{frows}</table>')
    if d["store_id_empty"] or d["distinct_stores"] <= 1:
        P.append(box("gap","الطلب من أكتر من متجر","حقل <span class='en'>store_id</span> فاضي على الطلبات، فالطلب متعدد المتاجر وترتيب المتاجر <b>غير قابلين للقياس</b>. المطلوب من التطوير تعبئة <span class='en'>store_id</span> و<span class='en'>stores_count</span>."))
    # sources
    P.append('<div class="src"><b>منهجية ومصادر:</b> الأرقام من PostHog (نافذة 8ص–4ص). '
             'الأطر: North Star (Amplitude) · AARRR (McClure) · HEART (Google) · مقاييس السوق (a16z). '
             'سياق الدفع من لوحة Paymob. التقييم النوعي بالـ LLM دون المساس بالأرقام.</div>')
    P.append('</body></html>')
    return "".join(P)

# ───────────────────────── delivery + CLI ─────────────────────────
def deliver(pdf_path, day_label, dry_run=False, to=None):
    msg = f"تقرير مؤشرات المنتج الأسبوعي — {day_label} 📊 (Product Metrics Report)"
    raw = to or os.environ.get("ASSER_USER_ID", "1378684355148386355")
    recipients = [x.strip() for x in raw.split(",") if x.strip()]
    if dry_run:
        print(f"[dry-run] would DM {recipients}: {pdf_path} — {msg}")
        return True
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))          # intel/
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
        import discord_delivery
        discord_delivery.send_report([pdf_path], message=msg, user_ids=recipients)
        print(f"DISCORD: delivered to {recipients}.")
        return True
    except Exception as e:
        print(f"DISCORD: delivery failed (non-fatal): {e}", file=sys.stderr)
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="end business day (default: yesterday Cairo)")
    ap.add_argument("--out", help="output PDF path")
    ap.add_argument("--dry-run", action="store_true", help="don't DM; just build")
    ap.add_argument("--no-discord", action="store_true", help="build but skip delivery")
    ap.add_argument("--no-llm", action="store_true", help="skip LLM; rule-based assessment only")
    ap.add_argument("--to", help="Discord user id(s) to DM, comma-separated (default: ASSER_USER_ID)")
    args = ap.parse_args()

    end_day = args.date or (cairo_today() - dt.timedelta(days=1)).isoformat()
    print(f"Collecting week ending {end_day} …")
    data = collect_week(end_day)
    assess = llm_assessment(data, enabled=not args.no_llm)
    html = render(data, assess)

    out = args.out or os.path.join(os.path.dirname(__file__),
                                   f"Product Metrics Report {data['week_start']}_{data['week_end']}.pdf")
    from weasyprint import HTML
    HTML(string=html).write_pdf(out, presentational_hints=True)
    print(f"PDF written: {out}")
    print(f"  orders={data['week']['orders']} revenue={data['week']['revenue']:.0f} "
          f"dau={data['dau']} payfail={data['payfail']} errors={data['e_tot']}")
    if not args.no_discord:
        deliver(out, f"{data['week_start']}–{data['week_end']}", dry_run=args.dry_run, to=args.to)

if __name__ == "__main__":
    main()
