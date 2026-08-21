#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""8Orders — Weekly Product Metrics: DATA LAYER (v2).

WHAT CHANGED IN v2 (per the PO, Aug 2026)
─────────────────────────────────────────
1. ONE DENOMINATOR: every rate in the report is now `uniq(person_id)` — unique
   users. v1 mixed three bases (events / sessions / people) which made rates
   uncomparable. The clearest casualty: v1 reported "only 44% of carts reach
   checkout" because it divided checkout_started EVENTS by add_to_cart EVENTS.
   A user adds many items to one cart and starts checkout once. On a per-USER
   basis the same week reads ~96%. Every rate here now carries an explicit
   denominator label so the reader can never guess wrong again.

2. SEGMENTATION: every headline metric is broken down by CITY (Hurghada /
   Assiut), PLATFORM ($os) and APP VERSION ($app_version), so a team can act on
   a number instead of just reading it.

   City attribution: IP geolocation is useless here — Egyptian mobile carriers
   route through a Cairo gateway, so ~40% of orders "come from" Cairo where the
   app does not operate. Instead we build a STORE -> CITY map from WiFi-only
   events (where the IP really is local), then attribute each USER to the city
   of the stores they actually browsed. Measured coverage: 99.9% of users who
   touched any store. The separation is effectively binary — every store is
   ~100% one city, 0% the other — so the map is stable week over week.

3. WINDOW: the report now uses the LAST 7 ACTIVE BUSINESS DAYS, scanning back up
   to LOOKBACK_DAYS. PostHog tracking has paused twice on the free-tier cap
   (9-26 Jul 2026, and again from 16 Aug 2026). Anchoring on "the last 7 calendar
   days" produced a 3-day report that could not be compared to anything. The
   previous window is the 7 active days immediately before, so week-over-week is
   always like-for-like.

Business day = Cairo 08:00 -> next 04:00 (20h window).

PRINCIPLE (unchanged): every NUMBER is computed here in Python from live PostHog
data. The LLM never computes, changes, or invents a number — it only writes the
qualitative reading. If the LLM is unavailable the report still renders.
"""
import os, sys, json, datetime as dt
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

# A day is "active" if it carries at least this many events. The paused periods
# trickled 0-700 events/day; live days carry 45k-58k. 5,000 separates them safely.
ACTIVE_DAY_MIN_EVENTS = 5000

# How far back to scan for active days before giving up.
LOOKBACK_DAYS = int(os.environ.get("WPM_LOOKBACK_DAYS", "45"))
WEEK_LEN = 7

# Cities the app actually operates in, and the geoip city names that mean each.
# Anything else (Cairo, Giza, Alexandria...) is carrier-gateway noise, not a market.
CITY_HURGHADA = "الغردقة"
CITY_ASSIUT = "أسيوط"
CITY_UNKNOWN = "غير محدد"
GEO_HURGHADA = ["Hurghada", "El Gouna", "Safaga", "Ras Gharib"]
GEO_ASSIUT = ["Asyut", "Assiut", "Dayrūţ", "Dayrut", "Abnūb", "Abnub",
              "Manfalūţ", "Manfalut", "Abu Tij", "Şadfā", "Al Qūşīyah"]

PAYMENT_CONTEXT_NOTE = (
    "سياق نجاح الدفع (المصدر: لوحة Paymob — خارج PostHog): الدفع بالبطاقات مستقر. "
    "أما المحافظ الإلكترونية فنسبة نجاحها منخفضة، وهي مشكلة معروفة قيد المتابعة من "
    "Paymob والبنك (طرف upstream) — وليست خللًا من جانب 8Orders."
)

AMOUNT = "toFloat(properties.total_amount)"


def _headers():
    return {"Authorization": f"Bearer {os.environ.get('POSTHOG_API_KEY', '')}"}


def cairo_today():
    return dt.datetime.now(CAIRO_TZ).replace(tzinfo=None).date()


def day_after(d):
    return (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat()


def _sql_list(vals):
    return ", ".join("'" + str(v).replace("'", "''") + "'" for v in vals)


def WD(days):
    """Predicate restricted to an explicit list of business days."""
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
                              json={"query": {"kind": "HogQLQuery", "query": q}}, timeout=180)
            if r.status_code == 200:
                return r.json().get("results", [])
            if r.status_code in (401, 403):
                raise PosthogAuthError(f"HTTP {r.status_code}: {r.text[:200]}")
            last = f"HTTP {r.status_code}: {r.text[:300]}"
        except PosthogAuthError:
            raise
        except Exception as e:
            last = str(e)
        if i < retries - 1:
            _t.sleep(min(2.0 ** (i + 1), 30.0) * (0.5 + random.random()))
    raise RuntimeError(f"HogQL failed after {retries}: {last}\nQ: {q[:300]}")


def preflight():
    """Fail LOUD instead of silently emitting an all-zeros report.

    The 30 Jul 2026 incident: POSTHOG_API_KEY was not exported to the child
    process, every query 403'd, failures were swallowed and returned 0, and a
    fully-zeroed PDF was DM'd to the PO as if it were real. Never again.
    """
    key = os.environ.get("POSTHOG_API_KEY", "")
    if not key:
        raise PosthogAuthError(
            "POSTHOG_API_KEY is empty in this process.\n"
            "  .env values are not exported to child processes unless you either\n"
            "  (a) run:  set -a; source .env; set +a\n"
            "  (b) or prefix the var:  POSTHOG_API_KEY=phx_... python3 ...\n"
            "  systemd/Dokploy handle this correctly via EnvironmentFile / env_file.")
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


def _qrow(q):
    rows = hogql(q)
    return list(rows[0]) if rows else []


def _qrows(q):
    return hogql(q) or []


def _i(v):
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def pct(num, den):
    """The single rate helper. Returns 0.0 on an empty denominator — never divides blind."""
    return (num / den * 100.0) if den else 0.0


# ───────────────────────── window: last N ACTIVE days ─────────────────────────
def find_active_days(end_day, need=WEEK_LEN * 2, lookback=LOOKBACK_DAYS):
    """Scan back from end_day and return active business days, oldest first.

    Returns (active_days, per_day_events). A day counts only if it carries real
    traffic — this is what makes the report survive a tracking outage instead of
    silently reporting a 3-day week as if it were 7.
    """
    end = dt.date.fromisoformat(end_day)
    start = end - dt.timedelta(days=lookback - 1)
    counts = {}
    for row in _qrows(
        "SELECT if(toHour(timestamp) < 4, toDate(timestamp) - 1, toDate(timestamp)) AS d, count() "
        f"FROM events WHERE timestamp >= toDateTime('{start.isoformat()} {BIZ_START}') "
        f"AND timestamp < toDateTime('{day_after(end.isoformat())} {BIZ_END}') "
        "AND (toHour(timestamp) >= 8 OR toHour(timestamp) < 4) GROUP BY d ORDER BY d"):
        counts[str(row[0])] = _i(row[1])
    active = [d for d in sorted(counts) if counts[d] >= ACTIVE_DAY_MIN_EVENTS
              and d <= end.isoformat()]
    return active[-need:], counts


# ───────────────────────── city attribution (store-based) ─────────────────────
def build_store_city_map(days):
    """STORE -> CITY, learned from WiFi-only events where the IP is genuinely local.

    Mobile carriers in Egypt NAT through a Cairo gateway, so cellular geoip says
    "Cairo" for a user standing in Hurghada. On WiFi the IP is the local ISP and
    the city is real. A store is physically fixed, so the majority WiFi city of
    everyone who opened it IS the store's city. Measured separation is binary:
    each store reads ~100% one city and ~0% the other, so a simple max() is safe.
    """
    pred = WD(days)
    rows = _qrows(
        "SELECT toString(properties.store_id) AS sid, "
        f"countIf(toString(properties.$geoip_city_name) IN ({_sql_list(GEO_HURGHADA)})) AS h, "
        f"countIf(toString(properties.$geoip_city_name) IN ({_sql_list(GEO_ASSIUT)})) AS a "
        "FROM events WHERE properties.$network_wifi = true "
        f"AND notEmpty(toString(properties.store_id)) AND {pred} "
        "GROUP BY sid HAVING (h + a) > 0")
    hurghada, assiut = [], []
    for sid, h, a in rows:
        (hurghada if _i(h) >= _i(a) else assiut).append(str(sid))
    return hurghada, assiut


def _city_cohorts(pred, h_ids, a_ids):
    """SQL for the two person cohorts: users of Hurghada stores, users of Assiut stores.

    Emitted as CTEs rather than an inline CASE because the classification is an
    AGGREGATE over each person's events (which store did they open most?), and you
    cannot GROUP BY an aggregate. So we resolve people to a city first, then group.

    Tie-break order per person:
      1. the city of the stores they actually opened (majority)
      2. their own WiFi geoip, if they never opened a store
      3. otherwise unclassified — never guessed
    """
    h = f"countIf(toString(properties.store_id) IN ({_sql_list(h_ids)}))" if h_ids else "0"
    a = f"countIf(toString(properties.store_id) IN ({_sql_list(a_ids)}))" if a_ids else "0"
    gh = (f"countIf(properties.$network_wifi = true AND "
          f"toString(properties.$geoip_city_name) IN ({_sql_list(GEO_HURGHADA)}))")
    ga = (f"countIf(properties.$network_wifi = true AND "
          f"toString(properties.$geoip_city_name) IN ({_sql_list(GEO_ASSIUT)}))")
    base = f"SELECT person_id FROM events WHERE {pred} GROUP BY person_id HAVING "
    hp = base + f"({h} > {a}) OR ({h} = {a} AND {gh} > {ga})"
    ap = base + f"({a} > {h}) OR ({a} = {h} AND {ga} > {gh})"
    return hp, ap


# ───────────────────────── the user-first metric block ────────────────────────
# Every entry: (key, arabic label, HogQL predicate identifying the behaviour).
# Each becomes uniq(person_id) — one user counted once, however many events they fired.
USER_METRICS = [
    ("active",        "فتح التطبيق",              "1=1"),
    ("store",         "فتح متجر",                 "event='store_opened'"),
    ("product",       "شاف منتج",                 "event='product_viewed'"),
    ("cart",          "حطّ في السلة",             "event='add_to_cart'"),
    ("checkout",      "بدأ الدفع",                "event='checkout_started'"),
    ("buyer",         "أتمّ طلب",                 "event='order_placed'"),
    ("payfail",       "فشل معه الدفع",            "event='payment_failed'"),
    ("error",         "قابله خطأ",                "event='app_error'"),
    ("rage",          "نقر بغضب",                 "event='$rageclick'"),
    ("uncovered",     "منطقته غير مخدومة",        "event='area_not_covered'"),
    ("voucher",       "استخدم فاوتشر",            "event='voucher_applied'"),
    ("reorder",       "أعاد طلب سابق",            "event='reorder_initiated'"),
    ("search_fail",   "بحث بدون نتيجة",           "event='search_no_results'"),
    ("cancelled",     "ألغى طلب",                 "event IN ('order_cancelled','Cancel_Unpaid_Online_Order')"),
    ("rating",        "قيّم طلب",                 "event='rate_order_event'"),
    ("share",         "شارك التطبيق",             "event='share_app_event'"),
    ("signup",        "أنشأ حساب",                "event='account_created'"),
    ("guest",         "دخل كضيف",                 "event='guest_session_started'"),
    ("login",         "سجّل دخول",                "event='login_event'"),
    ("install",       "ثبّت التطبيق",             "event='Application Installed'"),
    ("multi_store",   "فتح سلة أكتر من متجر",     "event='user_open_multi_merchant_sheet'"),
    ("remove_acct",   "حذف حسابه",                "event='remove_account'"),
    ("ads_click",     "نقر إعلان الرئيسية",       "event='click_on_home_ads'"),
    ("ads_discard",   "تجاهل إعلان الرئيسية",     "event='discard_home_ads'"),
    ("filter",        "استخدم الفلاتر",           "event='filter_applied'"),
    ("category",      "تصفّح الأصناف",            "event='category_tapped'"),
    ("address",       "أضاف عنوان",               "event='address_created'"),
    ("addr_changed",  "غيّر العنوان بعد الطلب",   "event='address_changed_post_order'"),
]

USER_SELECT = ", ".join(f"uniqIf(person_id, {p})" for _, _, p in USER_METRICS)
USER_KEYS = [k for k, _, _ in USER_METRICS]
USER_LABELS = {k: lbl for k, lbl, _ in USER_METRICS}

# Volume counters kept alongside — absolute totals the business still needs
# (money, order count). These are NEVER used as a denominator for a rate.
VOL_SELECT = (
    "countIf(event='order_placed'), "
    f"round(sumIf({AMOUNT}, event='order_placed')), "
    "countIf(event='app_error'), countIf(event='payment_failed'), "
    "countIf(event='$rageclick'), countIf(event='area_not_covered'), "
    "countIf(event='order_cancelled') + countIf(event='Cancel_Unpaid_Online_Order'), "
    "countIf(event='search_no_results'), countIf(event='voucher_applied'), "
    "countIf(event='reorder_initiated'), countIf(event='share_app_event'), "
    "countIf(event='rate_order_event'), countIf(event='user_open_multi_merchant_sheet')"
)
VOL_KEYS = ["orders", "revenue", "error_events", "payfail_events", "rage_events",
            "uncovered_events", "cancel_events", "search_fail_events", "voucher_events",
            "reorder_events", "share_events", "rating_events", "multi_store_events"]


def _users_and_volume(pred):
    row = _qrow(f"SELECT {USER_SELECT}, {VOL_SELECT} FROM events WHERE {pred}")
    if not row:
        return {k: 0 for k in USER_KEYS}, {k: 0 for k in VOL_KEYS}
    n = len(USER_KEYS)
    users = {k: _i(v) for k, v in zip(USER_KEYS, row[:n])}
    vol = {}
    for k, v in zip(VOL_KEYS, row[n:]):
        vol[k] = _f(v) if k == "revenue" else _i(v)
    return users, vol


def _rates(u, vol):
    """Every rate in the report, each with ONE stated denominator: unique users.

    `basis` is carried through to the PDF so the reader always sees what the
    percentage is a percentage OF. That is the whole point of v2.
    """
    pay_attempt = u["buyer"] + max(0, u["payfail"] - 0)
    return {
        # funnel — each step as a share of the users at the step before it
        "activation":      dict(v=pct(u["cart"], u["active"]),    n=u["cart"],     d=u["active"],   basis="من كل مستخدم فتح التطبيق"),
        "browse":          dict(v=pct(u["product"], u["active"]), n=u["product"],  d=u["active"],   basis="من كل مستخدم فتح التطبيق"),
        "cart_to_checkout":dict(v=pct(u["checkout"], u["cart"]),  n=u["checkout"], d=u["cart"],     basis="من كل مستخدم حطّ في السلة"),
        "checkout_to_order":dict(v=pct(u["buyer"], u["checkout"]),n=u["buyer"],    d=u["checkout"], basis="من كل مستخدم بدأ الدفع"),
        "cart_to_order":   dict(v=pct(u["buyer"], u["cart"]),     n=u["buyer"],    d=u["cart"],     basis="من كل مستخدم حطّ في السلة"),
        "purchase":        dict(v=pct(u["buyer"], u["active"]),   n=u["buyer"],    d=u["active"],   basis="من كل مستخدم فتح التطبيق"),
        # quality — incidence, i.e. how many REAL PEOPLE were hit, not event volume
        "error_hit":       dict(v=pct(u["error"], u["active"]),   n=u["error"],    d=u["active"],   basis="من كل مستخدم فتح التطبيق"),
        "rage_hit":        dict(v=pct(u["rage"], u["active"]),    n=u["rage"],     d=u["active"],   basis="من كل مستخدم فتح التطبيق"),
        "pay_success":     dict(v=pct(u["buyer"], pay_attempt),   n=u["buyer"],    d=pay_attempt,   basis="من كل مستخدم حاول يدفع"),
        "cancel":          dict(v=pct(u["cancelled"], u["buyer"]),n=u["cancelled"],d=u["buyer"],    basis="من كل مستخدم أتمّ طلب"),
        # engagement / marketing
        "voucher_use":     dict(v=pct(u["voucher"], u["buyer"]),  n=u["voucher"],  d=u["buyer"],    basis="من كل مستخدم أتمّ طلب"),
        "reorder_use":     dict(v=pct(u["reorder"], u["buyer"]),  n=u["reorder"],  d=u["buyer"],    basis="من كل مستخدم أتمّ طلب"),
        "rating_rate":     dict(v=pct(u["rating"], u["buyer"]),   n=u["rating"],   d=u["buyer"],    basis="من كل مستخدم أتمّ طلب"),
        "multi_store":     dict(v=pct(u["multi_store"], u["cart"]),n=u["multi_store"],d=u["cart"],  basis="من كل مستخدم حطّ في السلة"),
        "search_fail":     dict(v=pct(u["search_fail"], u["active"]),n=u["search_fail"],d=u["active"],basis="من كل مستخدم فتح التطبيق"),
        "uncovered":       dict(v=pct(u["uncovered"], u["active"]),n=u["uncovered"],d=u["active"],  basis="من كل مستخدم فتح التطبيق"),
        "guest_share":     dict(v=pct(u["guest"], u["active"]),   n=u["guest"],    d=u["active"],   basis="من كل مستخدم فتح التطبيق"),
        "ads_ignore":      dict(v=pct(u["ads_discard"], u["ads_discard"] + u["ads_click"]),
                                n=u["ads_discard"], d=u["ads_discard"] + u["ads_click"],
                                basis="من كل مستخدم تعامل مع إعلان الرئيسية"),
    }


# ───────────────────────────── segmentation ───────────────────────────────────
SEG_METRICS = ("uniq(person_id), uniqIf(person_id, event='add_to_cart'), "
               "uniqIf(person_id, event='checkout_started'), "
               "uniqIf(person_id, event='order_placed'), "
               "uniqIf(person_id, event='app_error'), "
               "uniqIf(person_id, event='payment_failed'), "
               "uniqIf(person_id, event='$rageclick'), "
               "countIf(event='order_placed'), "
               f"round(sumIf({AMOUNT}, event='order_placed')), "
               "countIf(event='app_error')")
SEG_KEYS = ["users", "cart_users", "checkout_users", "buyers", "error_users",
            "payfail_users", "rage_users", "orders", "revenue", "error_events"]


def _segment(pred, dim_expr, limit=12, having="", with_="", order="ORDER BY 2 DESC"):
    out = []
    for row in _qrows(f"{with_}SELECT {dim_expr} AS dim, {SEG_METRICS} FROM events "
                      f"WHERE {pred} GROUP BY dim {having} {order} LIMIT {limit}"):
        d = {"dim": str(row[0] or "—")}
        for k, v in zip(SEG_KEYS, row[1:]):
            d[k] = _f(v) if k == "revenue" else _i(v)
        d["purchase_rate"] = pct(d["buyers"], d["users"])
        d["cart_to_order"] = pct(d["buyers"], d["cart_users"])
        d["error_rate"] = pct(d["error_users"], d["users"])
        d["rage_rate"] = pct(d["rage_users"], d["users"])
        d["aov"] = (d["revenue"] / d["orders"]) if d["orders"] else 0.0
        out.append(d)
    return out


# Network-fault signatures. A user's connection dropping is not a code defect, and
# mixing the two makes the engineering backlog look twice as big as it is.
NETP = ("properties.error_message ILIKE '%disconnect%' OR properties.error_message ILIKE '%connection%' "
        "OR properties.error_message ILIKE '%host lookup%' OR properties.error_message ILIKE '%timed out%' "
        "OR properties.error_message ILIKE '%timeout%' OR properties.error_message ILIKE '%socket%' "
        "OR properties.error_message ILIKE '%unreachable%' OR properties.error_message ILIKE '%handshake%' "
        "OR properties.error_message ILIKE '%header was received%' OR properties.error_message ILIKE '%network%'")


def _error_split(pred):
    """EXACT unique users hit by network vs code errors.

    Summing the per-message rows would double-count anyone who hit two different
    errors, which is most people. These two numbers are counted independently so
    each is a true headcount; they still overlap with each other (one person can
    hit both), and that is stated in the report rather than hidden.
    """
    row = _qrow(f"SELECT uniqIf(person_id, {NETP}), uniqIf(person_id, NOT ({NETP})), "
                f"countIf({NETP}), countIf(NOT ({NETP})) "
                f"FROM events WHERE event='app_error' AND {pred}")
    if not row:
        return dict(net_users=0, code_users=0, net_events=0, code_events=0)
    return dict(net_users=_i(row[0]), code_users=_i(row[1]),
                net_events=_i(row[2]), code_events=_i(row[3]))


def _errors_segmented(pred):
    """Top errors with the three dimensions a developer needs to reproduce them:
    how many REAL USERS were hit, on which platform, which version, which city."""
    rows = _qrows(
        "SELECT substring(replaceAll(coalesce(nullIf(toString(properties.error_message),''),'—'), "
        "'\\n', ' '), 1, 110) AS msg, "
        "uniq(person_id) AS users, count() AS events, "
        "arrayStringConcat(arraySort(groupUniqArray(coalesce(nullIf(toString(properties.$os),''),'—'))), ' / ') AS oses, "
        "topK(2)(coalesce(nullIf(toString(properties.$app_version),''),'—')) AS vers, "
        "uniqIf(person_id, toString(properties.$os)='Android') AS and_users, "
        "uniqIf(person_id, toString(properties.$os) IN ('iOS','iPadOS')) AS ios_users "
        f"FROM events WHERE event='app_error' AND {pred} "
        "GROUP BY msg ORDER BY users DESC LIMIT 12")
    NET = ("disconnect", "connection", "host lookup", "timed out", "timeout", "socket",
           "unreachable", "handshake", "header was received", "network")
    out = []
    for msg, users, events, oses, vers, au, iu in rows:
        m = str(msg or "—")
        kind = "net" if any(t in m.lower() for t in NET) else "code"
        vlist = vers if isinstance(vers, list) else [vers]
        out.append(dict(msg=m, users=_i(users), events=_i(events), os=str(oses or "—"),
                        versions=" / ".join(str(v) for v in vlist if v),
                        android_users=_i(au), ios_users=_i(iu), kind=kind))
    return out


def _payfails_segmented(pred):
    rows = _qrows(
        "SELECT coalesce(nullIf(toString(properties.payment_method),''),'—') AS pm, "
        "coalesce(nullIf(toString(properties.failure_reason),''),'—') AS reason, "
        "uniq(person_id) AS users, count() AS events, "
        "uniqIf(person_id, toString(properties.$os)='Android') AS and_users, "
        "uniqIf(person_id, toString(properties.$os) IN ('iOS','iPadOS')) AS ios_users "
        f"FROM events WHERE event='payment_failed' AND {pred} "
        "GROUP BY pm, reason ORDER BY users DESC LIMIT 10")
    return [dict(method=str(a or "—"), reason=str(b or "—"), users=_i(c), events=_i(d),
                 android_users=_i(e), ios_users=_i(f)) for a, b, c, d, e, f in rows]


def _feature_adoption(pred, active_users):
    """Feature adoption measured in USERS, not event volume. v1 ranked features by
    raw event count, which flattered anything a user taps repeatedly."""
    feats = [("تصفّح الأصناف", "category_tapped"), ("استخدام الفلاتر", "filter_applied"),
             ("نقر إعلانات الرئيسية", "click_on_home_ads"), ("تجاهل إعلانات الرئيسية", "discard_home_ads"),
             ("نقر البانر", "banner_tapped"), ("تطبيق فاوتشر", "voucher_applied"),
             ("تسجيل الدخول", "login_event"), ("تقييم الطلب", "rate_order_event"),
             ("الأماكن الأقرب", "nearest_places_clicked"), ("الأماكن الأحدث", "newest_places_clicked"),
             ("تعليمات التوصيل", "delivery_instruction_selected"), ("إضافة عنوان", "address_created"),
             ("سلة أكتر من متجر", "user_open_multi_merchant_sheet"), ("اختيار مطعم", "user_select_restaurant"),
             ("إعادة الطلب", "reorder_initiated"), ("مشاركة التطبيق", "share_app_event"),
             ("بحث بدون نتيجة", "search_no_results"), ("تغيير عنوان بعد الطلب", "address_changed_post_order"),
             ("ظهور دعوة التسجيل", "signup_prompt_shown"), ("حذف الحساب", "remove_account")]
    sel = ", ".join(f"uniqIf(person_id, event='{ev}'), countIf(event='{ev}')" for _, ev in feats)
    row = _qrow(f"SELECT {sel} FROM events WHERE {pred}")
    out = []
    if row:
        for i, (ar, ev) in enumerate(feats):
            users, events = _i(row[i * 2]), _i(row[i * 2 + 1])
            out.append(dict(label=ar, event=ev, users=users, events=events,
                            reach=pct(users, active_users),
                            per_user=(events / users) if users else 0.0))
    return sorted(out, key=lambda x: -x["users"])


def _data_quality(pred):
    """Fields that are instrumented but arrive empty or always-zero.

    This is the check v1 could not make: it assumed store_id / delivery_fee /
    items_count were simply absent. They are present on the wire and carrying 0,
    which is worse — it looks like data until you aggregate it.
    """
    row = _qrow(
        "SELECT count(), "
        "countIf(toFloat(properties.subtotal) > 0), "
        "countIf(toFloat(properties.delivery_fee) > 0), "
        "countIf(toFloat(properties.discount_amount) > 0), "
        "countIf(toFloat(properties.items_count) > 0), "
        "countIf(toFloat(properties.tip_amount) > 0), "
        "countIf(properties.has_voucher = true), "
        "countIf(properties.is_reorder = true), "
        "countIf(notEmpty(toString(properties.store_id))) "
        f"FROM events WHERE event='order_placed' AND {pred}")
    if not row:
        return []
    n = _i(row[0]) or 1
    checks = [
        ("subtotal", "قيمة الطلب قبل الرسوم", _i(row[1])),
        ("delivery_fee", "رسوم التوصيل", _i(row[2])),
        ("discount_amount", "قيمة الخصم", _i(row[3])),
        ("items_count", "عدد العناصر في الطلب", _i(row[4])),
        ("tip_amount", "الإكرامية", _i(row[5])),
        ("has_voucher", "الطلب استخدم فاوتشر", _i(row[6])),
        ("is_reorder", "الطلب إعادة لطلب سابق", _i(row[7])),
        ("store_id", "المتجر صاحب الطلب", _i(row[8])),
    ]
    return [dict(field=f, label=lbl, filled=v, total=n, fill_rate=pct(v, n)) for f, lbl, v in checks]


# ───────────────────────────── collection ─────────────────────────────────────
def collect_week(end_day):
    all_active, day_events = find_active_days(end_day)
    if len(all_active) < 2:
        raise RuntimeError(
            f"Only {len(all_active)} active business day(s) found in the {LOOKBACK_DAYS} days "
            f"before {end_day} (need >= 2). PostHog tracking looks paused — refusing to build "
            f"a report on a dead window.")

    active = all_active[-WEEK_LEN:]
    prev_active = all_active[-(WEEK_LEN + len(active)):-len(active)] if len(all_active) > len(active) else []
    AD, PAD = len(active), len(prev_active)

    APRED, PPRED = WD(active), (WD(prev_active) if PAD else None)
    ws, we = active[0], active[-1]

    # gap days inside the span the report covers — what the reader must be told
    span = [(dt.date.fromisoformat(ws) + dt.timedelta(days=i)).isoformat()
            for i in range((dt.date.fromisoformat(we) - dt.date.fromisoformat(ws)).days + 1)]
    gap_days = [d for d in span if d not in active]
    # days between the last active day and the day the report is being built
    stale_days = [(dt.date.fromisoformat(we) + dt.timedelta(days=i)).isoformat()
                  for i in range(1, (dt.date.fromisoformat(end_day)
                                     - dt.date.fromisoformat(we)).days + 1)]

    users, vol = _users_and_volume(APRED)
    pusers, pvol = _users_and_volume(PPRED) if PPRED else (None, None)
    rates = _rates(users, vol)
    prates = _rates(pusers, pvol) if pusers else None

    # ── city map, then all three segmentations ───────────────────────────────
    h_ids, a_ids = build_store_city_map(all_active)
    hp_sql, ap_sql = _city_cohorts(APRED, h_ids, a_ids)
    cities = _segment(
        APRED,
        f"multiIf(person_id IN (SELECT person_id FROM hp), '{CITY_HURGHADA}', "
        f"person_id IN (SELECT person_id FROM ap), '{CITY_ASSIUT}', '{CITY_UNKNOWN}')",
        limit=4, with_=f"WITH hp AS ({hp_sql}), ap AS ({ap_sql}) ")
    platforms = _segment(APRED, "coalesce(nullIf(toString(properties.$os),''),'—')", limit=5)
    versions = _segment(APRED, "coalesce(nullIf(toString(properties.$app_version),''),'—')",
                        limit=8, having="HAVING uniq(person_id) >= 5")

    # per-day series (unique users + orders) across the active window
    series = {}
    for row in _qrows(
        "SELECT if(toHour(timestamp) < 4, toDate(timestamp) - 1, toDate(timestamp)) AS d, "
        "uniq(person_id), uniqIf(person_id, event='order_placed'), "
        f"countIf(event='order_placed'), round(sumIf({AMOUNT}, event='order_placed')), "
        "uniqIf(person_id, event='app_error') "
        f"FROM events WHERE {APRED} GROUP BY d ORDER BY d"):
        series[str(row[0])] = dict(users=_i(row[1]), buyers=_i(row[2]), orders=_i(row[3]),
                                   revenue=_f(row[4]), error_users=_i(row[5]))

    # payments split — by users, ordered by users
    pay_methods = [dict(method=str(m or "—"), users=_i(u), orders=_i(o))
                   for m, u, o in _qrows(
                       "SELECT coalesce(nullIf(toString(properties.payment_method),''),'—'), "
                       "uniq(person_id), count() FROM events "
                       f"WHERE event='order_placed' AND {APRED} GROUP BY 1 ORDER BY 2 DESC")]

    # hourly demand — orders per hour of day across the window
    hours = {}
    for h, c in _qrows("SELECT toHour(timestamp), countIf(event='order_placed') "
                       f"FROM events WHERE {APRED} GROUP BY 1 ORDER BY 1"):
        hours[_i(h)] = _i(c)

    # repeat purchase — measurable only because the window is a full week
    rb = _qrow("WITH b AS (SELECT person_id, count() AS n FROM events "
               f"WHERE event='order_placed' AND {APRED} GROUP BY person_id) "
               "SELECT count(), countIf(n >= 2), countIf(n >= 3), round(sum(n)/count(), 2) FROM b")
    buyers_n, repeat_buyers, loyal_buyers, opb = (
        (_i(rb[0]), _i(rb[1]), _i(rb[2]), _f(rb[3])) if rb else (0, 0, 0, 0.0))

    # uncovered demand, by the address the USER TYPED (not their IP)
    cov_regions = [dict(region=str(r), users=_i(u), attempts=_i(a)) for r, u, a in _qrows(
        "SELECT multiIf("
        "properties.address ILIKE '%Assiut%' OR properties.address ILIKE '%Asyut%','قرى ومراكز محافظة أسيوط',"
        "properties.address ILIKE '%Hurghada%' OR properties.address ILIKE '%Red Sea%','أطراف الغردقة والبحر الأحمر',"
        "properties.address ILIKE '%October%' OR properties.address ILIKE '%Giza%' OR properties.address ILIKE '%Cairo%','القاهرة الكبرى والجيزة (خارج التغطية)',"
        "'عناوين أخرى غير محددة') AS region, uniq(person_id), count() "
        f"FROM events WHERE event='area_not_covered' AND {APRED} GROUP BY region ORDER BY 2 DESC")]

    # top stores — by unique users, with the city they belong to
    hset, aset = set(h_ids), set(a_ids)
    top_stores = []
    for sid, name, u, o in _qrows(
        "SELECT toString(properties.store_id), "
        "any(coalesce(nullIf(toString(properties.store_name),''),'—')), "
        "uniq(person_id), count() FROM events WHERE event='store_opened' "
        f"AND notEmpty(toString(properties.store_id)) AND {APRED} "
        "GROUP BY 1 ORDER BY 3 DESC LIMIT 12"):
        s = str(sid)
        top_stores.append(dict(store_id=s, name=str(name or "—"), users=_i(u), opens=_i(o),
                               city=(CITY_HURGHADA if s in hset else
                                     CITY_ASSIUT if s in aset else CITY_UNKNOWN)))

    orders = vol["orders"]
    D = dict(
        # window
        active=active, active_days=AD, prev_active=prev_active, prev_active_days=PAD,
        week_start=ws, week_end=we,
        prev_start=(prev_active[0] if PAD else None), prev_end=(prev_active[-1] if PAD else None),
        gap_days=gap_days, stale_days=stale_days, day_events=day_events,
        end_day=end_day, wow_ok=(PAD >= 3), lookback_days=LOOKBACK_DAYS,
        # core
        users=users, vol=vol, prev_users=pusers, prev_vol=pvol,
        rates=rates, prev_rates=prates, user_labels=USER_LABELS,
        series=series,
        # money
        aov=((vol["revenue"] / orders) if orders else 0.0),
        prev_aov=((pvol["revenue"] / pvol["orders"]) if pvol and pvol["orders"] else 0.0),
        arpu=((vol["revenue"] / users["active"]) if users["active"] else 0.0),
        arpb=((vol["revenue"] / users["buyer"]) if users["buyer"] else 0.0),
        orders_per_buyer=opb, repeat_buyers=repeat_buyers, loyal_buyers=loyal_buyers,
        repeat_rate=pct(repeat_buyers, buyers_n),
        loyal_rate=pct(loyal_buyers, buyers_n),
        # segmentation
        cities=cities, platforms=platforms, versions=versions,
        store_city_counts=dict(hurghada=len(h_ids), assiut=len(a_ids)),
        top_stores=top_stores,
        # detail
        errors=_errors_segmented(APRED),
        payfails=_payfails_segmented(APRED),
        pay_methods=pay_methods, hours=hours, cov_regions=cov_regions,
        features=_feature_adoption(APRED, users["active"]),
        data_quality=_data_quality(APRED),
        payment_context=PAYMENT_CONTEXT_NOTE,
        generated_at=dt.datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %H:%M"),
    )
    D["error_split"] = _error_split(APRED)
    # per-active-day averages — the only honest way to compare two windows
    D["per_day"] = {k: (vol[k] / AD) for k in VOL_KEYS}
    D["prev_per_day"] = ({k: (pvol[k] / PAD) for k in VOL_KEYS} if pvol and PAD else None)
    return D


# ───────────────────────────── assessment ─────────────────────────────────────
def rule_based_assessment(d):
    r, u = d["rates"], d["users"]
    verdict = "🟡 مستقر مع تنبيهات"
    if r["cart_to_order"]["v"] > 85 and r["error_hit"]["v"] < 20:
        verdict = "🟢 صحّي"
    if r["error_hit"]["v"] > 35 or r["pay_success"]["v"] < 85:
        verdict = "🟠 تحذير"
    worst_city = min(d["cities"], key=lambda c: c["purchase_rate"]) if d["cities"] else None
    return dict(
        verdict=verdict,
        reading=("النية الشرائية سليمة: أغلب اللي بيوصل للسلة بيكمّل الطلب فعلًا. "
                 "الضغط الحقيقي مش في التحويل، هو في جودة التطبيق — نسبة المستخدمين "
                 "اللي بيقابلوا خطأ عالية. والقرار الأهم دلوقتي هو تقليل الأخطاء "
                 "غير الشبكية، مش تعديل شاشة الدفع."),
        wins=[f"{r['cart_to_order']['v']:.0f}% ممن حطّوا في السلة أتمّوا طلبًا فعلًا.",
              f"تكرار الشراء داخل الأسبوع: {d['repeat_rate']:.0f}% من المشترين.",
              f"نجاح الدفع على مستوى المستخدم: {r['pay_success']['v']:.0f}%."],
        risks=[f"{r['error_hit']['v']:.0f}% من المستخدمين قابلهم خطأ في التطبيق.",
               f"{r['rage_hit']['v']:.0f}% نقروا بغضب — إحباط في الواجهة.",
               (f"أضعف مدينة تحويلًا: {worst_city['dim']} عند "
                f"{worst_city['purchase_rate']:.0f}%." if worst_city else
                "طلب من مناطق غير مخدومة مستمر.")],
        takeaway=(f"{d['vol']['orders']:,} طلب من {u['buyer']:,} مشترٍ. "
                  f"أكبر رافعة = تقليل الأخطاء اللي بتضرب {u['error']:,} مستخدم."),
        note="(تقييم تلقائي احتياطي — الـ LLM كان غير متاح وقت التشغيل.)")


def _call_model(prompt, timeout=180):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key and requests is not None:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": os.environ.get("HADI_MODEL", "claude-sonnet-5"),
                  "max_tokens": 1500,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=timeout)
        if r.status_code == 200:
            return "".join(b.get("text", "") for b in r.json().get("content", []))
        raise RuntimeError(f"anthropic HTTP {r.status_code}: {r.text[:200]}")
    try:
        import asyncio
        from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

        async def _ask():
            opts = ClaudeAgentOptions(model=os.environ.get("HADI_MODEL", "claude-sonnet-5"),
                                      max_turns=1)
            parts = []
            async for msg in query(prompt=prompt, options=opts):
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            parts.append(block.text)
            return "".join(parts)

        result = asyncio.run(_ask())
        if result.strip():
            return result
        raise RuntimeError("SDK returned empty response")
    except ImportError:
        pass
    raise RuntimeError("no model backend (set ANTHROPIC_API_KEY, or install claude-agent-sdk)")


def llm_assessment(d, enabled=True):
    if not enabled:
        return rule_based_assessment(d)
    r, u = d["rates"], d["users"]
    facts = dict(
        window=f"{d['week_start']}..{d['week_end']}", active_days=d["active_days"],
        DENOMINATOR_RULE="كل النسب دي محسوبة على المستخدمين الفريدين، مش على الأحداث ولا الجلسات",
        active_users=u["active"], buyers=u["buyer"], orders=d["vol"]["orders"],
        revenue=round(d["vol"]["revenue"]), aov=round(d["aov"]),
        activation_pct=round(r["activation"]["v"], 1),
        cart_to_checkout_pct=round(r["cart_to_checkout"]["v"], 1),
        checkout_to_order_pct=round(r["checkout_to_order"]["v"], 1),
        cart_to_order_pct=round(r["cart_to_order"]["v"], 1),
        purchase_pct=round(r["purchase"]["v"], 1),
        payment_success_pct=round(r["pay_success"]["v"], 1),
        users_hit_by_error=u["error"], error_incidence_pct=round(r["error_hit"]["v"], 1),
        users_rageclicking=u["rage"], rage_incidence_pct=round(r["rage_hit"]["v"], 1),
        repeat_buyer_pct=round(d["repeat_rate"], 1), orders_per_buyer=d["orders_per_buyer"],
        uncovered_users=u["uncovered"],
        by_city=[{k: c[k] for k in ("dim", "users", "buyers", "purchase_rate", "aov", "error_rate")}
                 for c in d["cities"]],
        by_platform=[{k: p[k] for k in ("dim", "users", "purchase_rate", "error_rate", "rage_rate")}
                     for p in d["platforms"]],
        top_code_errors=[{"msg": e["msg"][:70], "users": e["users"], "os": e["os"]}
                         for e in d["errors"] if e["kind"] == "code"][:3],
    )
    prompt = (
        "انت محلل منتج أول (Senior Product Analyst) في تطبيق توصيل طعام وبقالة اسمه 8Orders "
        "بيشتغل في الغردقة وأسيوط. جاي لك أرقام أسبوعية نهائية محسوبة بالفعل من PostHog.\n"
        "قواعد صارمة: ممنوع تحسب أو تعدّل أو تخترع أي رقم. استخدم الأرقام زي ما هي بالحرف. "
        "لو رقم مش موجود، ماتذكرهوش.\n"
        "مهم: كل النسب محسوبة على المستخدمين الفريدين. لما تتكلم عن نسبة، قول مبنية على "
        "كام مستخدم.\n"
        "سياق مهم: فشل دفع المحافظ الإلكترونية مشكلة upstream معروفة من Paymob والبنك، "
        "مش خلل من جانبنا، فماتحطهاش كمهمة هندسية.\n"
        "ركّز على الفروق بين الغردقة وأسيوط وبين أندرويد وiOS لو الفرق واضح في الأرقام.\n"
        "اكتب بالعامية المصرية المهنية المبسطة (كلام إدارة، مش كلام مطوّرين). "
        "رجّع JSON فقط بالمفاتيح: verdict (واحد من: 🟢 صحّي / 🟡 مستقر مع تنبيهات / "
        "🟠 تحذير / 🔴 حرِج)، reading (3 جمل قراءة للأسبوع)، wins (3 عناصر)، "
        "risks (3 عناصر)، takeaway (جملة واحدة خلاصة تنفيذية).\n"
        f"الأرقام:\n{json.dumps(facts, ensure_ascii=False, indent=1)}")
    try:
        out = _call_model(prompt)
        data = json.loads(out[out.find("{"): out.rfind("}") + 1])
        base = rule_based_assessment(d)
        for k in ("verdict", "reading", "wins", "risks", "takeaway"):
            if not data.get(k):
                data[k] = base[k]
        data["note"] = ""
        return data
    except Exception as e:
        print(f"WARN LLM assessment unavailable ({e}); using rule-based.", file=sys.stderr)
        return rule_based_assessment(d)
