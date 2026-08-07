#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""8Orders — Weekly Product Metrics: DATA LAYER.

PRINCIPLE (per PO): every NUMBER is computed here in Python from live PostHog data.
The LLM never computes, changes, or invents a number — it only writes the qualitative
"reading". If the LLM is unavailable the report still renders (rule-based assessment).

Business day = Cairo 08:00 -> next 04:00 (20h window).
Week = 7 business days ending on `end_day`.

IMPORTANT — partial weeks: PostHog tracking was paused 9–26 Jul 2026 (free-tier cap).
A business day only counts as "active" if it carries real traffic. All per-day averages
and all week-over-week comparisons are computed over ACTIVE days only, and the report
states the active-day count explicitly. Never divide by 7 blindly.
"""
import os, sys, json, datetime as dt, shutil, subprocess
from zoneinfo import ZoneInfo

try:
    import requests
except Exception:
    requests = None

PROJECT = os.environ.get("POSTHOG_PROJECT_ID", "400872")
UI_HOST = os.environ.get("POSTHOG_UI_HOST", "https://us.posthog.com")
API = f"{UI_HOST}/api/projects/{PROJECT}"
CAIRO_TZ = ZoneInfo("Africa/Cairo")
BIZ_START, BIZ_END = "08:00:00", "04:00:00"

# A day is "active" if it carries at least this many events. The paused period
# trickled 20–700 events/day; live days carry 30k–46k. 5,000 separates them safely.
ACTIVE_DAY_MIN_EVENTS = 5000

PAYMENT_CONTEXT_NOTE = (
    "سياق نجاح الدفع (المصدر: لوحة Paymob — خارج PostHog): الدفع بالبطاقات مستقر. "
    "أما المحافظ الإلكترونية فنسبة نجاحها منخفضة، وهي مشكلة معروفة قيد المتابعة من "
    "Paymob والبنك (طرف upstream) — وليست خللًا من جانب 8Orders."
)

FLOAT = "toFloat64OrNull(toString(properties.total_amount))"


def _headers():
    return {"Authorization": f"Bearer {os.environ.get('POSTHOG_API_KEY', '')}"}


def cairo_today():
    return dt.datetime.now(CAIRO_TZ).replace(tzinfo=None).date()


def day_after(d):
    return (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat()


def business_days(end_day, n=7):
    end = dt.date.fromisoformat(end_day)
    return [(end - dt.timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]


def W(start_day, end_day):
    """Business-week predicate: [start 08:00, end+1 04:00) minus the 04:00–08:00 gap."""
    return (f"timestamp >= toDateTime('{start_day} {BIZ_START}') "
            f"AND timestamp < toDateTime('{day_after(end_day)} {BIZ_END}') "
            f"AND (toHour(timestamp) >= 8 OR toHour(timestamp) < 4)")


def WD(days):
    """Predicate restricted to an explicit list of business days (the ACTIVE ones)."""
    if not days:
        return "1=0"
    parts = [f"(timestamp >= toDateTime('{d} {BIZ_START}') "
             f"AND timestamp < toDateTime('{day_after(d)} {BIZ_END}') "
             f"AND (toHour(timestamp) >= 8 OR toHour(timestamp) < 4))" for d in days]
    return "(" + " OR ".join(parts) + ")"


# ───────────────────────────── transport ──────────────────────────────────────
class PosthogAuthError(RuntimeError):
    pass


def hogql(q, retries=3):
    import random, time as _t
    if requests is None:
        raise RuntimeError("requests not installed")
    last = None
    for i in range(retries):
        try:
            r = requests.post(f"{API}/query/", headers=_headers(),
                              json={"query": {"kind": "HogQLQuery", "query": q}}, timeout=120)
            if r.status_code == 200:
                return r.json().get("results", [])
            if r.status_code in (401, 403):
                raise PosthogAuthError(f"HTTP {r.status_code}: {r.text[:200]}")
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except PosthogAuthError:
            raise
        except Exception as e:
            last = str(e)
        if i < retries - 1:
            _t.sleep(min(2.0 ** (i + 1), 30.0) * (0.5 + random.random()))
    raise RuntimeError(f"HogQL failed after {retries}: {last}\nQ: {q[:200]}")


def preflight():
    """Fail LOUD instead of silently emitting an all-zeros report.

    The 30 Jul 2026 incident: POSTHOG_API_KEY was not exported to the child
    process, every query 403'd, _q1 swallowed each failure and returned 0, and a
    fully-zeroed PDF was DM'd to the PO as if it were real. Never again.
    """
    key = os.environ.get("POSTHOG_API_KEY", "")
    if not key:
        raise PosthogAuthError(
            "POSTHOG_API_KEY is empty in this process.\n"
            "  .env values are not exported to child processes unless you either\n"
            "  (a) run:  set -a; source .env; set +a\n"
            "  (b) or prefix the var:  POSTHOG_API_KEY=phx_... python3 ...\n"
            "  systemd handles this correctly via EnvironmentFile.")
    if not key.startswith("phx_"):
        print(f"WARN POSTHOG_API_KEY starts with {key[:4]!r}; HogQL needs a *Personal* "
              f"API key (phx_...). Project keys (phc_...) cannot query.", file=sys.stderr)
    rows = hogql("SELECT count() FROM events LIMIT 1")
    n = int(rows[0][0]) if rows and rows[0] else 0
    if n <= 0:
        raise RuntimeError("PostHog reachable but the project reports 0 events — refusing "
                           "to build a report on empty data.")
    print(f"PREFLIGHT ok — PostHog authenticated, project {PROJECT} has {n:,} events.")
    return True


def _q1(q, default=0):
    """First cell of first row. Auth errors propagate; data errors degrade."""
    rows = hogql(q)
    if rows and rows[0] and rows[0][0] is not None:
        return rows[0][0]
    return default


def _qrow(q):
    rows = hogql(q)
    return list(rows[0]) if rows else []


def _qrows(q):
    return hogql(q) or []


# ───────────────────────────── collection ─────────────────────────────────────
CORE_SELECT = (
    "countIf(event='order_placed'), "
    f"round(sumIf({FLOAT}, event='order_placed')), "
    "count(DISTINCT $session_id), count(DISTINCT person_id), "
    "count(DISTINCT if(event='order_placed',person_id,NULL)), "
    "count(DISTINCT if(event='order_placed',$session_id,NULL)), "
    "count(DISTINCT if(event='add_to_cart',$session_id,NULL)), "
    "countIf(event='Application Opened'), countIf(event='store_opened'), "
    "countIf(event='product_viewed'), countIf(event='add_to_cart'), "
    "countIf(event='checkout_started'), countIf(event='app_error'), "
    "countIf(event='payment_failed'), countIf(event='$rageclick'), "
    "countIf(event='$rageclick' AND properties.$os='iOS'), "
    "countIf(event='share_app_event'), countIf(event='rate_order_event'), "
    "countIf(event='Application Installed'), countIf(event='account_created'), "
    "countIf(event='guest_session_started'), countIf(event='reorder_initiated'), "
    "countIf(event='voucher_applied'), countIf(event='search_no_results'), "
    "countIf(event='Cancel_Unpaid_Online_Order'), countIf(event='order_cancelled'), "
    "countIf(event='user_open_multi_merchant_sheet'), countIf(event='user_select_restaurant'), "
    "countIf(event='area_not_covered'), "
    "count(DISTINCT if(event='area_not_covered',person_id,NULL)), "
    "countIf(event='login_event'), countIf(event='remove_account')"
)
CORE_KEYS = ["orders", "revenue", "sessions", "people", "buyers", "conv_sess", "cart_sess",
             "app_open", "store", "product", "cart", "checkout", "errors", "payfail",
             "rage", "rage_ios", "share", "ratings", "installs", "signups", "guest",
             "reorder", "voucher", "search_fail", "cancel_unpaid", "cancelled",
             "multi_sheet", "select_rest", "cov_events", "cov_users", "logins",
             "remove_account"]

FEATS = [("تصفّح الأصناف", "category_tapped"), ("تجاهل إعلانات الرئيسية", "discard_home_ads"),
         ("استخدام الفلاتر", "filter_applied"), ("نقر إعلانات الرئيسية", "click_on_home_ads"),
         ("نقر البانر", "banner_tapped"), ("تطبيق فاوتشر", "voucher_applied"),
         ("تسجيل الدخول", "login_event"), ("تقييم الطلب", "rate_order_event"),
         ("الأماكن الأقرب", "nearest_places_clicked"), ("تعليمات التوصيل", "delivery_instruction_selected"),
         ("إضافة عنوان", "address_created"), ("سلة أكتر من متجر", "user_open_multi_merchant_sheet"),
         ("الأماكن الأحدث", "newest_places_clicked"), ("اختيار مطعم", "user_select_restaurant"),
         ("إعادة الطلب", "reorder_initiated"), ("مشاركة التطبيق", "share_app_event"),
         ("بحث بدون نتيجة", "search_no_results"), ("تغيير عنوان بعد الطلب", "address_changed_post_order"),
         ("ظهور دعوة التسجيل", "signup_prompt_shown"), ("حذف الحساب", "remove_account")]

NETP = ("properties.error_message ILIKE '%disconnect%' OR properties.error_message ILIKE '%connection%' "
        "OR properties.error_message ILIKE '%host lookup%' OR properties.error_message ILIKE '%timed out%' "
        "OR properties.error_message ILIKE '%timeout%' OR properties.error_message ILIKE '%socket%' "
        "OR properties.error_message ILIKE '%unreachable%' OR properties.error_message ILIKE '%handshake%' "
        "OR properties.error_message ILIKE '%header was received%'")


def _core(pred):
    row = _qrow(f"SELECT {CORE_SELECT} FROM events WHERE {pred}")
    if not row:
        return {k: 0 for k in CORE_KEYS}
    out = {}
    for k, v in zip(CORE_KEYS, row):
        out[k] = float(v or 0) if k == "revenue" else int(v or 0)
    return out


def _active_days(days):
    """Return (active_days, per_day_events) — a day is active if it carries real traffic."""
    counts = {d: 0 for d in days}
    for row in _qrows(
        "SELECT if(toHour(timestamp) < 4, toDate(timestamp) - 1, toDate(timestamp)) AS d, count() "
        f"FROM events WHERE {W(days[0], days[-1])} GROUP BY d ORDER BY d"):
        d = str(row[0])
        if d in counts:
            counts[d] = int(row[1] or 0)
    return [d for d in days if counts[d] >= ACTIVE_DAY_MIN_EVENTS], counts


def collect_week(end_day):
    days = business_days(end_day, 7)
    ws, we = days[0], days[-1]
    prev = business_days((dt.date.fromisoformat(ws) - dt.timedelta(days=1)).isoformat(), 7)
    pws, pwe = prev[0], prev[-1]

    active, day_events = _active_days(days)
    prev_active, prev_day_events = _active_days(prev)
    AD, PAD = len(active), len(prev_active)
    if AD == 0:
        raise RuntimeError(f"No active business day in {ws}..{we} "
                           f"(max {max(day_events.values()) if day_events else 0} events/day) — "
                           f"refusing to build a report on a dead window.")

    APRED = WD(active)                     # this week, active days only
    PPRED = WD(prev_active) if PAD else None

    week = _core(APRED)
    pweek = _core(PPRED) if PPRED else None

    # per-day series across ALL 7 calendar days (inactive ones stay None -> shown as gap)
    series = {d: None for d in days}
    for row in _qrows(
        "SELECT if(toHour(timestamp) < 4, toDate(timestamp) - 1, toDate(timestamp)) AS d, "
        "countIf(event='order_placed'), "
        f"round(sumIf({FLOAT}, event='order_placed')), count(DISTINCT $session_id), "
        "countIf(event='add_to_cart'), countIf(event='checkout_started'), "
        "countIf(event='app_error') "
        f"FROM events WHERE {APRED} GROUP BY d ORDER BY d"):
        d = str(row[0])
        if d in series:
            series[d] = dict(orders=int(row[1] or 0), revenue=float(row[2] or 0),
                             sessions=int(row[3] or 0), cart=int(row[4] or 0),
                             checkout=int(row[5] or 0), errors=int(row[6] or 0))

    # payments
    pay = [(str(m or "—"), int(c)) for m, c in _qrows(
        "SELECT coalesce(nullIf(toString(properties.payment_method),''),'—'), count() "
        f"FROM events WHERE event='order_placed' AND {APRED} GROUP BY 1 ORDER BY 2 DESC")]
    payfail_rows = [(str(m or "—"), str(r or "—"), int(c)) for m, r, c in _qrows(
        "SELECT coalesce(nullIf(toString(properties.payment_method),''),'—'), "
        "coalesce(nullIf(toString(properties.failure_reason),''),'—'), count() "
        f"FROM events WHERE event='payment_failed' AND {APRED} GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10")]
    sqf = sum(c for _, r, c in payfail_rows if r == "success_query_false")

    # errors
    er = _qrow(f"SELECT countIf({NETP}), countIf(NOT ({NETP})) "
               f"FROM events WHERE event='app_error' AND {APRED}")
    e_net, e_non = (int(er[0] or 0), int(er[1] or 0)) if er else (0, 0)
    err_top = []
    for m, c, isnet in _qrows(
        "SELECT coalesce(nullIf(toString(properties.error_message),''),'—') AS m, count(), "
        f"max(if({NETP},1,0)) FROM events WHERE event='app_error' AND {APRED} "
        "GROUP BY m ORDER BY 2 DESC LIMIT 10"):
        msg = str(m or "—").split("\n")[0][:96]
        err_top.append((msg, int(c), "net" if int(isnet or 0) else "code"))

    # coverage by real user-entered address
    cov_regions = [(str(r), int(u), int(a)) for r, u, a in _qrows(
        "SELECT multiIf("
        "properties.address ILIKE '%Assiut%' OR properties.address ILIKE '%Asyut%','قرى ومراكز محافظة أسيوط',"
        "properties.address ILIKE '%Hurghada%' OR properties.address ILIKE '%Red Sea%','أطراف الغردقة والبحر الأحمر',"
        "properties.address ILIKE '%October%' OR properties.address ILIKE '%Giza%' OR properties.address ILIKE '%Cairo%','القاهرة الكبرى والجيزة (خارج التغطية)',"
        "'عناوين أخرى غير محددة') AS region, count(DISTINCT person_id), count() "
        f"FROM events WHERE event='area_not_covered' AND {APRED} GROUP BY region ORDER BY 2 DESC")]

    # features
    ci = ", ".join(f"countIf(event='{ev}')" for _, ev in FEATS)
    frow = _qrow(f"SELECT {ci} FROM events WHERE {APRED}")
    feats = sorted([(ar, ev, int(v or 0)) for (ar, ev), v in zip(FEATS, frow)],
                   key=lambda x: -x[2]) if frow else []

    # segments
    os_split = [(str(o or "—"), int(s), int(od), int(e)) for o, s, od, e in _qrows(
        "SELECT coalesce(nullIf(toString(properties.$os),''),'—'), count(DISTINCT $session_id), "
        "countIf(event='order_placed'), countIf(event='app_error') "
        f"FROM events WHERE {APRED} GROUP BY 1 ORDER BY 2 DESC LIMIT 6")]
    versions = [(str(v or "—"), int(s)) for v, s in _qrows(
        "SELECT coalesce(nullIf(toString(properties.$app_version),''),'—'), count(DISTINCT $session_id) "
        f"FROM events WHERE {APRED} GROUP BY 1 ORDER BY 2 DESC LIMIT 8")]

    # hours (orders per hour of day, summed over the active window)
    hours = {}
    for h, c in _qrows("SELECT toHour(timestamp), countIf(event='order_placed') "
                       f"FROM events WHERE {APRED} GROUP BY 1 ORDER BY 1"):
        try:
            hours[int(h)] = int(c or 0)
        except (TypeError, ValueError):
            continue   # one odd bucket must not kill the whole report

    # retention proxies that a WEEK of data makes real (the daily report could not do this)
    rb = _qrow(
        "WITH b AS (SELECT person_id, count() AS n FROM events "
        f"WHERE event='order_placed' AND {APRED} GROUP BY person_id) "
        "SELECT count(), countIf(n >= 2), countIf(n >= 3), round(sum(n)/count(), 2) FROM b")
    buyers_n, repeat_buyers, loyal_buyers, opb = (
        (int(rb[0] or 0), int(rb[1] or 0), int(rb[2] or 0), float(rb[3] or 0)) if rb else (0, 0, 0, 0.0))

    # orders that used a voucher (voucher_applied in the same session as an order)
    with_voucher = int(_q1(
        "SELECT count(DISTINCT $session_id) FROM events "
        f"WHERE {APRED} AND $session_id IN (SELECT $session_id FROM events "
        f"WHERE event='voucher_applied' AND {APRED}) AND event='order_placed'", default=0))

    # multi-store attribution honesty check
    store_id_empty = (str(_q1(
        "SELECT toString(properties.store_id) FROM events WHERE event='order_placed' "
        f"AND {APRED} GROUP BY 1 ORDER BY count() DESC LIMIT 1", default="")).strip() == "")

    orders = week["orders"]
    checkout, cart = week["checkout"], week["cart"]
    D = dict(
        days=days, active=active, active_days=AD, day_events=day_events,
        prev_days=prev, prev_active=prev_active, prev_active_days=PAD,
        week_start=ws, week_end=we, prev_start=pws, prev_end=pwe,
        wow_ok=(PAD > 0), series=series, week=week, pweek=pweek,
        aov=(week["revenue"] / orders) if orders else 0.0,
        prev_aov=((pweek["revenue"] / pweek["orders"]) if pweek and pweek["orders"] else 0.0),
        sess_conv=(week["conv_sess"] / week["sessions"] * 100) if week["sessions"] else 0.0,
        buyer_conv=(week["buyers"] / week["people"] * 100) if week["people"] else 0.0,
        cart_to_checkout=(checkout / cart * 100) if cart else 0.0,
        checkout_to_order=(orders / checkout * 100) if checkout else 0.0,
        cart_to_order=(orders / cart * 100) if cart else 0.0,
        pay_success=(orders / (orders + week["payfail"]) * 100) if (orders + week["payfail"]) else 0.0,
        pay=pay, payfail_rows=payfail_rows, sqf=sqf,
        e_net=e_net, e_non=e_non, err_top=err_top,
        cov_regions=cov_regions, feats=feats, os_split=os_split, versions=versions,
        hours=hours, repeat_buyers=repeat_buyers, loyal_buyers=loyal_buyers,
        repeat_rate=(repeat_buyers / buyers_n * 100) if buyers_n else 0.0,
        orders_per_buyer=opb, with_voucher=with_voucher, store_id_empty=store_id_empty,
        rage_ios_pct=(week["rage_ios"] / week["rage"] * 100) if week["rage"] else 0.0,
        new_ver_pct=(sum(s for v, s in versions[:2]) / max(1, sum(s for _, s in versions)) * 100),
        generated_at=dt.datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %H:%M"),
        payment_context=PAYMENT_CONTEXT_NOTE,
    )
    # per-active-day averages (the only honest way to compare partial weeks)
    D["per_day"] = {k: (week[k] / AD) for k in CORE_KEYS}
    D["prev_per_day"] = ({k: (pweek[k] / PAD) for k in CORE_KEYS} if pweek and PAD else None)
    return D


# ───────────────────────────── assessment ─────────────────────────────────────
def rule_based_assessment(d):
    w = d["week"]
    verdict = "🟡 مستقر مع تنبيهات"
    if d["cart_to_checkout"] > 55 and d["e_non"] < 3000:
        verdict = "🟢 صحّي"
    if d["e_non"] > 8000 or d["pay_success"] < 90:
        verdict = "🟠 تحذير"
    return dict(
        verdict=verdict,
        reading=("الأسبوع بيوري إن الطلبات موجودة والتحويل شغّال، وأكبر رافعة مفردة هي "
                 "التسرّب بين السلة وبدء الدفع. فشل دفع المحافظ سياقه upstream من Paymob "
                 "ومش أولوية هندسية عندنا. الأخطاء غير الشبكية هي اللي محتاجة مراجعة فعلية."),
        wins=["الطلبات مستمرة بمعدل يومي ثابت خلال الأيام النشطة.",
              "تبنّي أحدث نسختين من التطبيق شبه كامل.",
              f"العميل اللي طلب أكتر من مرة في الأسبوع: "
              f"<span dir=\"ltr\">{d['repeat_rate']:.0f}%</span> من المشترين."],
        risks=[f"تسرّب السلة قبل الدفع — <span dir=\"ltr\">"
               f"{100 - d['cart_to_checkout']:.0f}%</span> مايبدؤوش الدفع.",
               f"أخطاء غير شبكية محتاجة مراجعة — <span dir=\"ltr\">{d['e_non']:,}</span>.",
               f"طلب من مناطق غير مخدومة — <span dir=\"ltr\">"
               f"{d['week']['cov_users']:,}</span> مستخدم."],
        note="(تقييم تلقائي احتياطي — الـ LLM كان غير متاح وقت التشغيل.)")


def _call_model(prompt, timeout=180):
    if requests is not None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
        if api_key:
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01",
                       "content-type": "application/json"}
        elif oauth_token:
            headers = {"Authorization": f"Bearer {oauth_token}",
                       "anthropic-version": "2023-06-01",
                       "content-type": "application/json"}
        else:
            headers = None
        if headers:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={"model": os.environ.get("HADI_MODEL", "claude-sonnet-5"),
                      "max_tokens": 1500,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=timeout)
            if r.status_code == 200:
                return "".join(b.get("text", "") for b in r.json().get("content", []))
            raise RuntimeError(f"anthropic HTTP {r.status_code}: {r.text[:200]}")
    exe = shutil.which("claude")
    if exe:
        p = subprocess.run([exe, "-p", prompt], capture_output=True, text=True, timeout=timeout)
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout
        raise RuntimeError(f"claude CLI rc={p.returncode}: {(p.stderr or '')[:200]}")
    raise RuntimeError("no model backend (set ANTHROPIC_API_KEY, or install the claude CLI)")


def llm_assessment(d, enabled=True):
    if not enabled:
        return rule_based_assessment(d)
    facts = dict(
        window=f"{d['week_start']}..{d['week_end']}", active_days=d["active_days"],
        orders=d["week"]["orders"], revenue=round(d["week"]["revenue"]),
        aov=round(d["aov"], 1), sessions=d["week"]["sessions"], people=d["week"]["people"],
        buyers=d["week"]["buyers"], session_conversion_pct=round(d["sess_conv"], 1),
        cart_to_checkout_pct=round(d["cart_to_checkout"], 1),
        checkout_to_order_pct=round(d["checkout_to_order"], 1),
        payment_success_pct=round(d["pay_success"], 1), payment_fails=d["week"]["payfail"],
        success_query_false=d["sqf"], errors_network=d["e_net"], errors_non_network=d["e_non"],
        rageclicks=d["week"]["rage"], rage_ios_pct=round(d["rage_ios_pct"], 1),
        repeat_buyer_pct=round(d["repeat_rate"], 1), orders_per_buyer=d["orders_per_buyer"],
        uncovered_users=d["week"]["cov_users"], top_features=d["feats"][:6],
        multi_store_sheet_opens=d["week"]["multi_sheet"],
    )
    prompt = (
        "انت محلل منتج أول (Senior Product Analyst) في تطبيق توصيل طعام وبقالة اسمه 8Orders "
        "بيشتغل في الغردقة وأسيوط. جاي لك أرقام أسبوعية نهائية محسوبة بالفعل من PostHog.\n"
        "قواعد صارمة: ممنوع تحسب أو تعدّل أو تخترع أي رقم. استخدم الأرقام زي ما هي بالحرف. "
        "لو رقم مش موجود، ماتذكرهوش.\n"
        "سياق مهم: فشل دفع المحافظ الإلكترونية مشكلة upstream معروفة من Paymob والبنك، "
        "مش خلل من جانبنا، فماتحطهاش كمهمة هندسية.\n"
        "اكتب بالعامية المصرية المهنية المبسطة (كلام إدارة، مش كلام مطوّرين). "
        "رجّع JSON فقط بالمفاتيح: verdict (واحد من: 🟢 صحّي / 🟡 مستقر مع تنبيهات / "
        "🟠 تحذير / 🔴 حرِج)، reading (3 جمل قراءة للأسبوع)، wins (3 عناصر)، "
        "risks (3 عناصر)، takeaway (جملة واحدة خلاصة تنفيذية).\n"
        f"الأرقام:\n{json.dumps(facts, ensure_ascii=False, indent=1)}")
    try:
        out = _call_model(prompt)
        data = json.loads(out[out.find("{"): out.rfind("}") + 1])
        base = rule_based_assessment(d)
        for k in ("verdict", "reading", "wins", "risks"):
            if not data.get(k):
                data[k] = base[k]
        data["note"] = ""
        return data
    except Exception as e:
        print(f"WARN LLM assessment unavailable ({e}); using rule-based.", file=sys.stderr)
        return rule_based_assessment(d)
