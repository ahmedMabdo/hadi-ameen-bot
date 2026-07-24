#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
"""
8Orders — Daily Product Intelligence Report generator (verified pipeline).

Design goal: reproduce the "v4" Arabic report at the SAME accuracy every day,
WITHOUT the LLM re-deriving queries (the original source of errors).

Everything is data-driven:
  * Reporting day = "yesterday" in Africa/Cairo (UTC+3) unless --date given.
  * Revenue/AOV measured directly from order_placed.total_amount (NOT estimated).
  * Comparison day = previous Cairo day; baseline = mean of the 3 prior days.
  * Junk/zero-funnel app versions detected generically and excluded from DAU.
  * Featured session chosen from events (0 orders + highest rage/errors),
    then confirmed against the session_recordings API.
  * Issues + actions emitted from rules, so the narrative reflects the day.

Env: POSTHOG_API_KEY (personal API key), optional POSTHOG_HOST.
Usage:  python3 8orders_report_generator.py [--date 2026-06-18] [--out report.pdf]
"""
import os, sys, json, argparse, datetime as dt, requests

PROJECT = "400872"
UI_HOST = "https://us.posthog.com"                 # browser/replay links
API = f"{UI_HOST}/api/projects/{PROJECT}"
HEADERS = {"Authorization": f"Bearer {os.environ.get('POSTHOG_API_KEY','')}"}
CAIRO_OFFSET = 3                                   # June: UTC+3

# ── نافذة يوم العمل (القاهرة) ──
# 8Orders زودوا ساعات العمل (2026-07-24): اليوم بيقفل 04:00 بدل 02:00.
# غيّر الرقمين دول بس لو الساعات اتغيرت تاني — كل الاستعلامات بتقرا منهم.
# لازم يفضلوا متطابقين مع posthog_cli.business_day() عشان الرقم اللايف
# والرقم اللي في التقرير ما يختلفوش.
BIZ_START = "08:00:00"
BIZ_END = "04:00:00"   # على اليوم اللي بعده
BIZ_END_HOUR = 4

# ── App-specific event/property mapping (verified against PostHog) ──
EV = dict(
    app_open="Application Opened", product="product_viewed", cart="add_to_cart",
    store="store_opened", order="order_placed", rage="$rageclick", error="app_error",
    voucher="voucher_applied", reorder="reorder_initiated", search_no="search_no_results",
    support="customer_service", cancel="Cancel_Unpaid_Online_Order",
    rating="rate_order_event", install="Application Installed", account="account_created",
)
FUNNEL_EVENTS = (EV["product"], EV["cart"], EV["order"])   # used for junk detection
# App-lifecycle events that fire without any real user interaction. A user whose
# only events are these is NOT an active user — PostHog's default DAU counts them,
# so we exclude lifecycle-only users to get a real DAU.
LIFECYCLE_EVENTS = (
    "Application Opened", "Application Backgrounded",
    "Application Updated", "Application Installed",
)

# Stable upstream-payment context baked into the report so the daily routine frames
# electronic payments correctly (PostHog can't measure payment success — failures are
# not tracked; source of truth is the Paymob dashboard). Card payments are healthy;
# mobile-wallet success is low but is a KNOWN issue under active investigation by
# Paymob + the bank (upstream PSP/issuer) — NOT an 8Orders defect, so it must not be
# raised as an engineering/product action on our side. No hardcoded percentages here
# (they change per period); this is the durable qualitative framing.
PAYMENT_CONTEXT_NOTE = (
    "سياق نجاح الدفع (المصدر: لوحة Paymob — خارج PostHog): الدفع بالبطاقات أداؤه جيد ومستقر. "
    "أما المحافظ الإلكترونية فنسبة نجاحها منخفضة، وهي <strong>مشكلة معروفة قيد المتابعة حاليًا "
    "من Paymob والبنك (طرف upstream)</strong> — وليست خللًا من جانب 8Orders، فلا تُعامَل كإجراء "
    "هندسي/منتج على فريقنا."
)

# ───────────────────────── PostHog query helper ─────────────────────────
def hogql(q, retries=3):
    last = None
    for i in range(retries):
        try:
            r = requests.post(f"{API}/query/", headers=HEADERS,
                              json={"query": {"kind": "HogQLQuery", "query": q}}, timeout=90)
            if r.status_code == 200:
                return r.json().get("results", [])
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:
            last = str(e)
    raise RuntimeError(f"HogQL failed after {retries} tries: {last}\nQuery: {q[:200]}")

def D(day):
    """Business-day predicate (NOT calendar day).
    A business day labelled `day` runs Cairo 08:00 of `day` -> Cairo 04:00 next day.
    The PostHog project timezone is Africa/Cairo, so HogQL interprets BOTH the
    `timestamp` column and the toDateTime() literals below in Cairo local time.
    We therefore express the window directly as the true Cairo business-day edges
    [day 08:00, next-day 04:00).
    (Historical note: until 2026-06-23 the project was on UTC, so this window was
    written as [day 05:00, day 23:00) in UTC. The project tz was then switched to
    Africa/Cairo, which shifted the literal interpretation by +3h — hence the
    bounds are now the real Cairo wall-clock edges.)
    The routine runs ~07:00 Cairo (delayed from 03:00 so PostHog finishes
    de-duplicating the just-ended day's events) and reports the business day
    that just ended. The default-day logic is correct for any run time between
    Cairo 04:00 and midnight.
    (2026-07-24: window end moved 02:00 -> 04:00 — 8Orders extended trading
    hours. Edges live in BIZ_START/BIZ_END; do not re-hardcode them here.)"""
    nxt = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()
    return (f"timestamp >= toDateTime('{day} {BIZ_START}') "
            f"AND timestamp < toDateTime('{nxt} {BIZ_END}')")

# ───────────────────────── formatting helpers ─────────────────────────
def fmt(n):
    try: return f"{int(round(float(n))):,}"
    except Exception: return str(n)

def money_k(v):
    return f"{round(float(v)/1000):,}K"

def trend(cur, prev, good_up=True, decimals=1):
    """Return dict with pct text, arrow, and css class (up=green/down=red/flat)."""
    if not prev:
        return dict(pct="—", arrow="~", cls="flat")
    ch = (cur - prev) / prev * 100.0
    arrow = "↑" if ch > 0.5 else ("↓" if ch < -0.5 else "~")
    good = (ch > 0 and good_up) or (ch < 0 and not good_up)
    cls = "flat" if abs(ch) < 1 else ("up" if good else "down")
    return dict(pct=f"{abs(ch):.{decimals}f}%", arrow=arrow, cls=cls, raw=ch)

# ───────────────────────── data collection ─────────────────────────
def event_counts(day):
    rows = hogql(f"SELECT event, count() FROM events WHERE {D(day)} GROUP BY event")
    return {e: c for e, c in rows}

def revenue(day):
    r = hogql(f"""SELECT count(), round(sum(toFloat(properties.total_amount)),0),
        round(avg(toFloat(properties.total_amount)),0)
        FROM events WHERE event='{EV['order']}' AND {D(day)}""")
    o, rev, aov = (r[0] if r else (0, 0, 0))
    return dict(orders=int(o or 0), revenue=float(rev or 0), aov=float(aov or 0))

def payment_breakdown(day):
    rows = hogql(f"""SELECT properties.payment_method, count(),
        round(avg(toFloat(properties.total_amount)),0)
        FROM events WHERE event='{EV['order']}' AND {D(day)}
        GROUP BY properties.payment_method ORDER BY count() DESC""")
    groups = {"cash": [0, []], "online": [0, []], "applePay": [0, []],
              "onlineWallet": [0, []], "wallet": [0, []], "mixed": [0, []]}
    for pm, c, aov in rows:
        c = int(c); aov = float(aov or 0)
        key = pm if pm in groups else ("mixed" if (pm or "").startswith("wallet_") else "online")
        groups[key][0] += c; groups[key][1].append(aov)
    out = []
    labels = {"cash": "كاش عند التسليم", "online": "دفع إلكتروني (online)", "applePay": "Apple Pay",
              "onlineWallet": "محفظة إلكترونية", "wallet": "محفظة", "mixed": "محفظة + كاش/إلكتروني"}
    total = sum(g[0] for g in groups.values()) or 1
    for k in ["cash", "online", "applePay", "onlineWallet", "wallet", "mixed"]:
        cnt, aovs = groups[k]
        if cnt == 0: continue
        if k == "mixed" and aovs:
            aov_txt = f"{int(min(aovs))}–{int(max(aovs))} ج"
        else:
            aov_txt = f"{int(round(sum(aovs)/len(aovs)))} ج" if aovs else "—"
        out.append(dict(label=labels[k], count=cnt, pct=f"{cnt/total*100:.1f}%", aov=aov_txt))
    return out, total

def conversion_series(days):
    out = {}
    for d in days:
        r = hogql(f"""SELECT countIf(event='{EV['cart']}'), countIf(event='{EV['order']}')
            FROM events WHERE {D(d)} AND event IN ('{EV['cart']}','{EV['order']}')""")
        atc, orders = (r[0] if r else (0, 0))
        out[d] = dict(cart=int(atc or 0), orders=int(orders or 0),
                      conv=(int(orders or 0) / int(atc) * 100) if atc else 0.0)
    return out

def version_table(day):
    rows = hogql(f"""SELECT properties.$app_version, properties.$os_name,
        countIf(event='{EV['order']}'), countIf(event='{EV['error']}'),
        countIf(event='{EV['rage']}'), countIf(event='{EV['product']}'),
        countIf(event='{EV['cart']}'), count(), uniq(person_id)
        FROM events WHERE {D(day)}
        GROUP BY properties.$app_version, properties.$os_name
        HAVING count() > 200 ORDER BY count() DESC LIMIT 12""")
    vers = []
    for v, osn, o, err, rage, pv, atc, tot, users in rows:
        vers.append(dict(version=v or "—", os=osn or "—", orders=int(o), errors=int(err),
                         rage=int(rage), pv=int(pv), cart=int(atc), total=int(tot), users=int(users)))
    # NOTE: the old "junk version" heuristic (high event volume + zero funnel
    # activity) flagged versions like 8.1.513 as suspicious bot traffic. Those
    # are actually lifecycle-only sessions (app opened/updated, no interaction) —
    # normal behaviour, not junk. They're now correctly excluded from DAU by the
    # real-DAU definition, so we no longer raise a false "suspicious traffic" alarm.
    junk = []
    return vers, junk

def dau(day):
    """Return (all_users, real_users) for the business day.
    real_users (the headline DAU) counts only users with >=1 NON-lifecycle event
    in the day — i.e. users who actually interacted. PostHog's default counts
    anyone who merely opened/updated the app; excluding lifecycle-only users
    removes that inflation. all_users is kept for transparency (excluded count)."""
    notin = ", ".join(f"'{e}'" for e in LIFECYCLE_EVENTS)
    r = hogql(f"""SELECT uniq(person_id), uniqIf(person_id, event NOT IN ({notin}))
        FROM events WHERE {D(day)}""")
    allu, real = (r[0] if r else (0, 0))
    return int(allu or 0), int(real or 0)

def errors_by_screen(day):
    rows = hogql(f"""SELECT properties.$screen_name, count() FROM events
        WHERE event='{EV['error']}' AND {D(day)} GROUP BY properties.$screen_name
        ORDER BY count() DESC LIMIT 8""")
    return [(s or "—", int(c)) for s, c in rows]

def dns_error_count(day):
    r = hogql(f"""SELECT count() FROM events WHERE event='{EV['error']}' AND {D(day)}
        AND (properties.error_message ILIKE '%host lookup%'
             OR properties.stack_trace ILIKE '%ids.8orders.com%'
             OR properties.error_message ILIKE '%SocketException%')""")
    return int(r[0][0]) if r else 0

def top_error_message(day):
    r = hogql(f"""SELECT properties.error_message, count() FROM events
        WHERE event='{EV['error']}' AND {D(day)} GROUP BY properties.error_message
        ORDER BY count() DESC LIMIT 1""")
    return (r[0][0], int(r[0][1])) if r else ("—", 0)

# ── Error classification for session scoring ──────────────────────────
# Two large error classes used to dominate (and mislead) the "critical
# sessions" ranking. Neither reflects an 8Orders product defect:
#   NET   = client-side connectivity — connection drops/refused/reset/closed,
#           DNS host-lookup failures, socket timeouts. This is the customer's
#           own network, NOT our bug (a real outage would hit users uniformly;
#           these are concentrated on a handful of devices).
#   NOISE = caught, NON-FATAL log-spam from our own Flutter code: the
#           ImageStream teardown race ("Stream has been disposed") and
#           UnimplementedError (an unimplemented-but-caught code path). Logged
#           but invisible to the user and non-blocking (the day still completes
#           hundreds of orders while these fire for the majority of sessions).
# Both are excluded from the friction score so only genuine, user-affecting
# product errors (and real rage clicks) make a session rank as critical.
NET_ERR_SQL = ("(properties.error_message ILIKE '%Connection%' "
               "OR properties.error_message ILIKE '%host lookup%' "
               "OR properties.error_message ILIKE '%SocketException%' "
               "OR properties.error_message ILIKE '%timed out%' "
               "OR properties.error_message ILIKE '%Network is unreachable%' "
               # socket-level failures that don't contain the word "Connection"
               # (verified 2026-06-24 on real sessions — "Can't assign requested
               # address" had wrongly scored a network-only session as critical):
               "OR properties.error_message ILIKE '%Can''t assign requested address%' "
               "OR properties.error_message ILIKE '%Software caused connection abort%' "
               "OR properties.error_message ILIKE '%Broken pipe%' "
               "OR properties.error_message ILIKE '%No route to host%')")
# CAVEAT: NOISE is a *heuristic*. "UnimplementedError" is USUALLY caught/non-fatal,
# but on real sessions it has also been confirmed (via PostHog AI replay summary with
# visual confirmation) to be a BLOCKING crash — e.g. a crash right after tapping a home
# ad. The event stream alone can't tell the two apart; the daily routine's per-session
# AI-summary pass (see ROUTINE_INSTRUCTIONS.md) is what reclassifies these to technical.
NOISE_ERR_SQL = ("(properties.error_message ILIKE '%Stream has been disposed%' "
                 "OR properties.error_message = 'UnimplementedError' "
                 # Image-thumbnail loading crash spam: fires in sub-second bursts on
                 # ANY screen with product/store images, never blocks the flow (35%
                 # of sessions carrying it still complete an order — verified
                 # 2026-07-01 over the trailing 10 days).
                 "OR properties.error_message ILIKE 'Exception: Image upload failed due to loss of GPU access%' "
                 "OR properties.error_message = 'Null check operator used on a null value')")
REAL_ERR_SQL = f"(NOT {NET_ERR_SQL} AND NOT {NOISE_ERR_SQL})"

def code_noise(day):
    """Widespread CAUGHT, non-fatal errors from our own Flutter code (NOISE
    class): logged but non-blocking. High volume here pollutes telemetry and
    used to inflate the critical-session ranking. Surfaced with LIVE counts,
    reach (users) and the screen they concentrate on, so engineering can decide
    what to silence/fix — never hard-coded."""
    buckets = [
        ("مسار كود غير مكتمل (UnimplementedError)",
         "properties.error_message = 'UnimplementedError'"),
        ("سباق دورة حياة الصور (ImageStream disposed)",
         "properties.error_message ILIKE '%Stream has been disposed%'"),
        ("كراش تحميل صور (GPU/Null check)",
         "(properties.error_message ILIKE 'Exception: Image upload failed due to loss of GPU access%' "
         "OR properties.error_message = 'Null check operator used on a null value')"),
    ]
    out = []
    for label, cond in buckets:
        r = hogql(f"""SELECT count(), uniq(person_id) FROM events
            WHERE event='{EV['error']}' AND {D(day)} AND {cond}""")
        cnt, users = (r[0] if r else (0, 0))
        if not int(cnt or 0):
            continue
        top = hogql(f"""SELECT properties.$screen_name, count() FROM events
            WHERE event='{EV['error']}' AND {D(day)} AND {cond}
            GROUP BY properties.$screen_name ORDER BY count() DESC LIMIT 1""")
        scr, scr_c = (top[0] if top else ("—", 0))
        out.append(dict(label=label, count=int(cnt or 0), users=int(users or 0),
                        screen=scr or "—", screen_c=int(scr_c or 0)))
    out.sort(key=lambda x: x["count"], reverse=True)
    return out

def featured_sessions(day, n=5):
    """Return up to `n` MOST-CRITICAL customer-experience sessions for the day,
    ranked by a friction score that reflects OUR product quality ONLY.
    Score = rage*3 + real_err*2, where real_err counts genuine, user-affecting
    app errors and EXCLUDES client-network errors and caught non-fatal code
    noise (see NET_ERR_SQL / NOISE_ERR_SQL). net_err / noise_err are still
    captured per session for transparency. Confirmed against the
    session_recordings API."""
    e = EV['error']
    cands = hogql(f"""SELECT properties.$session_id,
        countIf(event='{EV['rage']}'),
        countIf(event='{e}' AND {REAL_ERR_SQL}),
        countIf(event='{e}' AND {NET_ERR_SQL}),
        countIf(event='{e}' AND {NOISE_ERR_SQL}),
        countIf(event='{EV['cart']}'), countIf(event='{EV['order']}'),
        countIf(event='{EV['product']}'), countIf(event='{EV['store']}'), count()
        FROM events WHERE {D(day)} AND properties.$session_id != ''
        GROUP BY properties.$session_id
        HAVING countIf(event='{EV['order']}')=0
            AND (countIf(event='{EV['rage']}')>0
                 OR countIf(event='{e}' AND {REAL_ERR_SQL})>0)
        ORDER BY (countIf(event='{EV['rage']}')*3
                  + countIf(event='{e}' AND {REAL_ERR_SQL})*2) DESC
        LIMIT 30""")
    out = []
    for sid, rage, real_err, net_err, noise_err, cart, orders, pv, stores, tot in cands:
        try:
            rr = requests.get(f"{API}/session_recordings/{sid}/", headers=HEADERS, timeout=30)
            if rr.status_code != 200:
                continue
            rec = rr.json()
            meta = hogql(f"""SELECT properties.$os_name, properties.$app_version
                FROM events WHERE properties.$session_id='{sid}' LIMIT 1""")
            osn, ver = (meta[0] if meta else ("—", "—"))
            active = rec.get("active_seconds") or 0
            out.append(dict(sid=sid, rage=int(rage), err=int(real_err),
                            net_err=int(net_err), noise_err=int(noise_err),
                            cart=int(cart), pv=int(pv),
                            stores=int(stores), clicks=int(rec.get("click_count") or 0),
                            active_min=round(active/60) if active else None,
                            os=osn or "—", version=ver or "—",
                            score=int(rage) * 3 + int(real_err) * 2,
                            url=f"{UI_HOST}/project/{PROJECT}/replay/{sid}"))
            if len(out) >= n:
                break
        except Exception:
            continue
    return out

def fetch_session_summaries(sids, timeout=240):
    """Fetch PostHog's real AI session-recording summary for each session id,
    via REST (no MCP needed): GET the cached summary if one already exists,
    else POST to generate it for whichever ids are missing (single batched
    call). Returns {sid: summary_dict_or_None} — a None entry means the
    summary could not be fetched/generated (network issue, timeout, no
    recording data), and callers should fall back to the basic heuristic
    rather than block the run on it."""
    out, missing = {}, []
    for sid in sids:
        try:
            r = requests.get(f"{API}/single_session_summaries/{sid}/", headers=HEADERS, timeout=30)
            out[sid] = r.json().get("summary") if r.status_code == 200 else None
            if out[sid] is None:
                missing.append(sid)
        except Exception:
            out[sid] = None
            missing.append(sid)
    if missing:
        try:
            r = requests.post(f"{API}/session_summaries/create_session_summaries_individually/",
                               headers=HEADERS, json={"session_ids": missing}, timeout=timeout)
            if r.status_code == 200:
                batch = r.json()
                for sid in missing:
                    if sid in batch:
                        out[sid] = batch[sid]
        except Exception:
            pass
    return out

# ───────────────────────── HTML rendering ─────────────────────────
CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Cairo',Arial,sans-serif; font-size:9.5pt; color:#0f172a; background:#fff; direction:rtl; line-height:1.7; }
.cover { background:#0f172a; padding:36px 44px 28px; page-break-after:always; direction:rtl; }
.cover-top { overflow:hidden; margin-bottom:22px; }
.cover-logo { float:right; font-size:22pt; font-weight:900; color:#fff; }
.cover-logo span { color:#f97316; }
.cover-meta { float:left; font-size:7.5pt; color:#94a3b8; text-align:left; line-height:1.9; }
.cover-clear { clear:both; }
.cover-title { clear:both; font-size:26pt; font-weight:900; color:#fff; line-height:1.1; margin-top:10px; margin-bottom:6px; }
.cover-sub { font-size:10pt; color:#94a3b8; margin-bottom:18px; }
.health-pill { display:inline-block; background:rgba(234,88,12,0.2); border:1.5px solid rgba(234,88,12,0.6); color:#fed7aa; padding:6px 18px; border-radius:100px; font-size:9.5pt; font-weight:700; }
.session-box { margin-top:20px; background:rgba(249,115,22,0.1); border:1.5px solid rgba(249,115,22,0.45); border-radius:10px; padding:14px 18px; }
.session-label { font-size:7pt; font-weight:700; color:#f97316; text-transform:uppercase; letter-spacing:1px; margin-bottom:5px; }
.session-title { font-size:10pt; font-weight:800; color:#fff; margin-bottom:4px; }
.session-link { font-size:7.5pt; color:#fed7aa; direction:ltr; display:block; }
.stags { margin-top:8px; }
.stag { display:inline-block; background:rgba(255,255,255,0.1); color:#e2e8f0; padding:2px 9px; border-radius:20px; font-size:7pt; margin-left:4px; margin-top:3px; }
.body { padding:0 36px; direction:rtl; }
.section { margin-top:22px; }
.section-hdr { border-bottom:2px solid #e2e8f0; padding-bottom:7px; margin-bottom:12px; overflow:hidden; }
.sec-num { display:inline-block; background:#fff7ed; color:#f97316; font-size:7pt; font-weight:800; padding:2px 8px; border-radius:4px; margin-left:8px; }
.sec-title { font-size:13pt; font-weight:800; }
.sec-badge { float:left; display:inline-block; font-size:7pt; font-weight:700; padding:2px 8px; border-radius:4px; text-transform:uppercase; }
.sec-badge.cr { background:#fee2e2; color:#991b1b; }
.note { background:#f0f9ff; border:1px solid #bae6fd; border-radius:7px; padding:8px 12px; font-size:8pt; color:#0c4a6e; margin-bottom:12px; }
.verify-note { background:#ecfdf5; border:1px solid rgba(5,150,105,0.4); border-radius:7px; padding:8px 12px; font-size:7.5pt; color:#065f46; margin-bottom:12px; line-height:1.6; }
.kpi-grid { width:100%; border-collapse:separate; border-spacing:6px; }
.kc { background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:11px 13px; vertical-align:top; width:25%; }
.kc.warn { background:#fffbeb; border-color:rgba(217,119,6,0.45); }
.kc.alert { background:#fef2f2; border-color:rgba(220,38,38,0.45); }
.kc.good { background:#f0fdf4; border-color:rgba(22,163,74,0.35); }
.kc-lbl { font-size:6.5pt; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:4px; }
.kc-val { font-size:18pt; font-weight:900; color:#0f172a; line-height:1.05; margin-bottom:5px; }
.kc-chg { font-size:7.5pt; font-weight:700; display:block; margin-bottom:2px; }
.up { color:#16a34a; } .down { color:#dc2626; } .flat { color:#64748b; }
.kc-sub { font-size:7pt; color:#64748b; line-height:1.5; }
.dt { width:100%; border-collapse:collapse; font-size:8.5pt; }
.dt th { text-align:right; font-size:7pt; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.5px; padding:6px 8px; background:#f8fafc; border-bottom:2px solid #e2e8f0; }
.dt td { padding:6px 8px; border-bottom:1px solid #f1f5f9; }
.dt tr:last-child td { border-bottom:none; }
.dt .n { text-align:left; font-weight:700; direction:ltr; font-variant-numeric:tabular-nums; }
.dt .hl td { background:#fff7ed; } .dt .cr td { background:#fef2f2; } .dt .gd td { background:#f0fdf4; }
.tc { width:100%; border-collapse:collapse; }
.tc td { vertical-align:top; padding:0; }
.tc td:first-child { padding-left:7px; } .tc td:last-child { padding-right:7px; }
.box { background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px 14px; }
.box-t { font-size:7pt; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:0.7px; margin-bottom:8px; }
.exec-section { background:#0f172a; border-radius:10px; padding:20px 24px; margin-bottom:16px; direction:rtl; }
.exec-section p { font-size:9pt; color:#cbd5e1; line-height:1.8; margin-bottom:6px; }
.exec-section strong { color:#fff; }
.exec-action { background:rgba(249,115,22,0.18); border-right:3px solid #f97316; padding:9px 13px; border-radius:8px 0 0 8px; margin-top:10px; font-size:9pt; color:#fed7aa; font-weight:600; line-height:1.7; }
.issue { border-radius:8px; padding:12px 14px; margin-bottom:9px; border:1px solid; page-break-inside:avoid; direction:rtl; }
.issue.cr { background:#fef2f2; border-color:rgba(220,38,38,0.35); }
.issue.hi { background:#fff7ed; border-color:rgba(234,88,12,0.35); }
.issue.md { background:#fffbeb; border-color:rgba(217,119,6,0.35); }
.issue-top { overflow:hidden; margin-bottom:6px; }
.issue-title { float:right; font-size:10pt; font-weight:800; }
.issue-badges { float:left; }
.sev { display:inline-block; padding:2px 8px; border-radius:20px; font-size:6.5pt; font-weight:800; margin-right:3px; }
.sev.cr { background:#dc2626; color:#fff; } .sev.hi { background:#ea580c; color:#fff; } .sev.md { background:#d97706; color:#fff; }
.sev.cf-h { background:#dbeafe; color:#1e40af; } .sev.cf-m { background:#fef9c3; color:#854d0e; }
.iclear { clear:both; }
.issue-row-grid { width:100%; border-collapse:collapse; }
.issue-row-grid td { padding:2px 0; vertical-align:top; font-size:8pt; }
.issue-row-grid td:first-child { width:70px; font-weight:700; color:#64748b; padding-left:10px; }
.action { padding:11px 14px; border-radius:8px; margin-bottom:8px; border:1px solid; overflow:hidden; page-break-inside:avoid; direction:rtl; }
.action.p0 { background:#fef2f2; border-color:rgba(220,38,38,0.4); }
.action.p1 { background:#fff7ed; border-color:rgba(234,88,12,0.4); }
.action.p2 { background:#fffbeb; border-color:rgba(217,119,6,0.4); }
.action-num { float:left; width:30px; height:30px; border-radius:50%; text-align:center; line-height:30px; font-size:9pt; font-weight:900; color:#fff; margin-left:12px; }
.p0 .action-num { background:#dc2626; } .p1 .action-num { background:#ea580c; } .p2 .action-num { background:#d97706; }
.action-body { overflow:hidden; }
.action-title { font-size:9.5pt; font-weight:800; margin-bottom:3px; }
.action-why { font-size:8pt; color:#334155; line-height:1.6; }
.tag { display:inline-block; padding:2px 8px; border-radius:20px; font-size:7pt; font-weight:600; margin-right:4px; direction:ltr; }
.t-mob { background:#ede9fe; color:#5b21b6; } .t-bk { background:#dbeafe; color:#1d4ed8; }
.t-dt { background:#d1fae5; color:#065f46; } .t-op { background:#fef9c3; color:#854d0e; }
.gap { border-right:3px solid #d97706; padding:8px 12px; background:#fffbeb; border-radius:8px 0 0 8px; margin-bottom:7px; }
.gap-title { font-weight:800; font-size:8.5pt; margin-bottom:2px; }
.gap-body { font-size:8pt; color:#0f172a; line-height:1.6; }
.p0-t { background:#dc2626; color:#fff; font-size:6.5pt; font-weight:800; padding:1px 6px; border-radius:20px; }
.p1-t { background:#ea580c; color:#fff; font-size:6.5pt; font-weight:800; padding:1px 6px; border-radius:20px; }
.p2-t { background:#d97706; color:#fff; font-size:6.5pt; font-weight:800; padding:1px 6px; border-radius:20px; }
.rec { background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px 14px; margin-bottom:8px; overflow:hidden; page-break-inside:avoid; }
.rec.main { border-color:rgba(220,38,38,0.5); background:#fef2f2; }
.rec-icon { float:right; font-size:18pt; margin-left:12px; }
.rec-body { overflow:hidden; }
.rec-title { font-size:9pt; font-weight:800; margin-bottom:2px; }
.rec-meta { font-size:7pt; color:#64748b; margin-bottom:3px; }
.rec-link { font-size:8pt; color:#f97316; direction:ltr; display:block; word-break:break-all; }
.rec-why { font-size:8pt; color:#334155; margin-top:6px; line-height:1.6; }
.pb { page-break-after:always; } .avoid { page-break-inside:avoid; }
.b { display:inline-block; padding:1px 7px; border-radius:20px; font-size:7pt; font-weight:700; }
.b-g { background:#dcfce7; color:#166534; } .b-y { background:#fef9c3; color:#854d0e; } .b-r { background:#fee2e2; color:#991b1b; }
.footer { margin-top:24px; padding:13px 36px; background:#f8fafc; border-top:2px solid #e2e8f0; overflow:hidden; }
.footer-r { float:right; font-size:7.5pt; color:#64748b; } .footer-l { float:left; font-size:7.5pt; color:#64748b; }
.fb-bg { background:#e2e8f0; border-radius:3px; height:7px; width:100%; margin-top:4px; }
.fb { height:7px; border-radius:3px; }
ul.ar { margin:6px 18px 0 0; } ul.ar li { font-size:8.5pt; line-height:1.8; color:#0f172a; }
.watch-box { background:#fffbeb; border:1px solid rgba(217,119,6,0.4); border-radius:8px; padding:12px 14px; margin-top:12px; }
.data-note { background:#f0f9ff; border:1px solid #bae6fd; border-radius:8px; padding:10px 14px; margin-top:12px; font-size:8pt; color:#0c4a6e; line-height:1.7; }
"""

AR_MONTHS = {1:"يناير",2:"فبراير",3:"مارس",4:"أبريل",5:"مايو",6:"يونيو",
             7:"يوليو",8:"أغسطس",9:"سبتمبر",10:"أكتوبر",11:"نوفمبر",12:"ديسمبر"}

def chg_span(t, prefix=""):
    return f'<span class="kc-chg {t["cls"]}">{t["arrow"]} {t["pct"]} {prefix}</span>'

def _iso(t):
    # Isolate a token's bidi direction so Latin/number/Arabic tokens never collide
    return f'<span style="unicode-bidi:isolate; display:inline-block;">{t}</span>'

def toks(*items):
    # Join meta tokens, each direction-isolated, for clean RTL alignment
    return ' &nbsp;·&nbsp; '.join(_iso(x) for x in items if x)

def _session_title(s):
    return toks(s["os"], f'v{s["version"]}', f'{fmt(s["clicks"])} ضغطة',
                f'{s["rage"]} نقرة غاضبة' if s["rage"] else None,
                f'{s["err"]} خطأ' if s["err"] else None,
                f'{s["cart"]} إضافات للسلة' if s["cart"] else None, 'صفر طلبات')

def _rec_card(s, ar_date, rank, main=False):
    """One Section-07 recording card for a flagged session."""
    fric = []
    if s["rage"]: fric.append(f'{s["rage"]} نقرة غاضبة')
    if s["err"]:  fric.append(f'{s["err"]} خطأ حقيقي في التطبيق')
    friction_txt = ' و'.join(fric) if fric else 'احتكاك'
    excl = []
    if s.get("net_err"):   excl.append(f'{s["net_err"]} خطأ شبكة (نِت العميل)')
    if s.get("noise_err"): excl.append(f'{s["noise_err"]} ضوضاء كود مُلتقَطة')
    excl_txt = (f' <span style="color:#94a3b8;">— مُستبعَد من التقييم: '
                f'{" و".join(excl)}</span>') if excl else ''
    cart_lead = f'أضاف {s["cart"]} للسلة ثم ' if s["cart"] else ''
    rec_meta = toks(ar_date, s["os"], f'v{s["version"]}',
                    (f'{s["active_min"]}د نشاط' if s["active_min"] else None),
                    (f'{s["pv"]} منتج' if s["pv"] else None),
                    (f'{s["stores"]} متاجر' if s["stores"] else None),
                    f'{s["err"]} خطأ', 'تم التحقق من القيم')
    cls = 'rec main' if main else 'rec'
    icon = '⚠' if main else f'#{rank}'
    head = '★ الأخطر — ' if main else f'#{rank} — '
    return (f'<div class="{cls}"><div class="rec-icon">{icon}</div><div class="rec-body">'
            f'<div class="rec-title">{head}{_session_title(s)}</div>'
            f'<div class="rec-meta">{rec_meta}</div>'
            f'<a class="rec-link" href="{s["url"]}">{s["url"]}</a>'
            f'<div class="rec-why">مستخدم {s["os"]} {cart_lead}واجه {friction_txt} — ولم يُتم أي طلب.{excl_txt} '
            'افتح في PostHog بعد تسجيل الدخول.</div></div></div>')

def session_blocks(d, ar_date):
    """Build the cover session box (single worst session) + Section-07 recording
    block (TOP-5 most-critical sessions, ranked). Shared by both reports so the
    session copy stays identical across them."""
    sessions = d.get("sessions") or ([d["session"]] if d.get("session") else [])
    if not sessions:
        sess_box = '<div class="session-box"><div class="session-label">لا توجد جلسات مطابقة لمعايير "أخطر جلسة" اليوم.</div></div>'
        featured_block = '<div class="note">لا توجد جلسات مطابقة اليوم.</div>'
        return sess_box, featured_block
    s = sessions[0]  # the single worst — highlighted on the cover
    stags = [f'{fmt(s["clicks"])} ضغطة']
    if s["rage"]: stags.append(f'{s["rage"]} نقرة غاضبة')
    if s["err"]:  stags.append(f'{s["err"]} خطأ في التطبيق')
    if s["cart"]: stags.append(f'{s["cart"]} إضافات للسلة')
    if s["pv"]:   stags.append(f'{s["pv"]} منتج مُشاهَد')
    stags.append('صفر طلبات')
    stags_html = ''.join(f'<span class="stag">{t}</span>' for t in stags)
    sess_box = f'''
  <div class="session-box">
    <div class="session-label">★ أخطر جلسة مسجلة · {ar_date} · (أعلى {len(sessions)} في التقرير)</div>
    <div class="session-title">{_session_title(s)}</div>
    <a class="session-link" href="{s['url']}">{s['url']}</a>
    <div class="stags">{stags_html}</div>
  </div>'''
    cards = ''.join(_rec_card(sess, ar_date, i + 1, main=(i == 0)) for i, sess in enumerate(sessions))
    featured_block = (
        f'<div class="note">أخطر <strong>{len(sessions)}</strong> جلسات اليوم (صفر طلبات + أعلى احتكاك حقيقي: '
        'نقرات غاضبة + أخطاء تطبيق حقيقية فقط). أخطاء الشبكة (نِت العميل) وضوضاء الكود المُلتقَطة '
        '<strong>مُستبعَدة</strong> من التقييم. ملاحظة: rageclick يُلتقَط على iOS فقط، '
        'لذا الترتيب منحاز لـiOS (راجع ثغرات التتبع). افتح كلًّا في PostHog بعد تسجيل الدخول.</div>' + cards)
    return sess_box, featured_block

def build_html(d):
    day = d["day"]; prev = d["prev"]
    dd = dt.date.fromisoformat(day)
    ar_date = f"{dd.day} {AR_MONTHS[dd.month]} {dd.year}"
    gen_now = dt.datetime.utcnow() + dt.timedelta(hours=CAIRO_OFFSET)
    gen_date = gen_now.date()
    gen_ar = f"{gen_date.day} {AR_MONTHS[gen_date.month]} {gen_date.year}"
    gen_clock = gen_now.strftime("%H:%M")

    # cover featured session + Section-07 recording block
    s = d["session"]
    sess_box, featured_block = session_blocks(d, ar_date)

    # KPI trends
    rev, prev_rev = d["rev"], d["prev_rev"]
    t_dau = trend(d["dau"], d["prev_dau"], good_up=True)
    t_install = trend(d["installs"], d["prev_installs"], good_up=True)
    t_orders = trend(rev["orders"], prev_rev["orders"], good_up=True)
    t_rev = trend(rev["revenue"], prev_rev["revenue"], good_up=True)
    t_err = trend(d["errors"], d["prev_errors"], good_up=False)
    t_cancel = trend(d["cancel"], d["prev_cancel"], good_up=False)
    t_reorder = trend(d["reorder"], d["prev_reorder"], good_up=True)
    t_voucher = trend(d["voucher"], d["prev_voucher"], good_up=True)
    conv = d["conv_today"]; base_conv = d["conv_baseline"]
    conv_drop = (base_conv - conv) / base_conv * 100 if base_conv else 0  # +ve = dropped, -ve = improved
    # Direction-aware display tokens for conversion vs baseline (avoids hardcoded ↓ when it rose/held)
    conv_arrow = "↓" if conv_drop > 0.5 else ("↑" if conv_drop < -0.5 else "~")
    conv_cls = "down" if conv_drop > 0.5 else ("up" if conv_drop < -0.5 else "flat")
    conv_abs = abs(conv_drop)
    cancel_rate = d["cancel"] / rev["orders"] * 100 if rev["orders"] else 0
    prev_cancel_rate = d["prev_cancel"] / prev_rev["orders"] * 100 if prev_rev["orders"] else 0
    err_per_100 = d["errors"] / d["app_opens"] * 100 if d["app_opens"] else 0

    junk_note = ""
    if d["junk"]:
        jv = d["junk"][0]
        junk_note = (f'<div class="kc-sub" style="color:#b45309;">بدون {jv["version"]}: '
                     f'~{fmt(d["dau_clean"])} فقط — الباقي جلسات صفرية</div>')
    # DAU = interacting users only; show how many lifecycle-only sessions were excluded
    _dau_excluded = d.get("dau_all", d["dau"]) - d["dau"]
    dau_note = ('<div class="kc-sub">مستخدمون متفاعلون فقط · يستثني '
                f'~{fmt(_dau_excluded)} جلسة بلا تفاعل</div>' if _dau_excluded > 0
                else '<div class="kc-sub">مستخدمون متفاعلون فقط</div>')

    # conversion trend rows
    conv_rows = ""
    series = d["conv_series"]; sdays = sorted(series.keys())
    for i, sd in enumerate(sdays):
        v = series[sd]; ddo = dt.date.fromisoformat(sd)
        last = (i == len(sdays)-1)
        cls = ' class="cr"' if last else ""
        nm = f'<strong>{ddo.day} {AR_MONTHS[ddo.month]}</strong>' if last else f'{ddo.day} {AR_MONTHS[ddo.month]}'
        cv = f'<span class="n {conv_cls}"><strong>{v["conv"]:.1f}% {conv_arrow}</strong></span>' if last else f'{v["conv"]:.1f}%'
        conv_rows += f'<tr{cls}><td>{nm}</td><td class="n">{fmt(v["cart"])}</td><td class="n">{fmt(v["orders"])}</td><td class="n">{cv}</td></tr>'

    # payment rows
    pay_rows = ""
    for i, p in enumerate(d["payment"]):
        cls = ' class="hl"' if i == 0 else ""
        bold = f'<strong>{p["pct"]}</strong>' if i == 0 else p["pct"]
        pay_rows += f'<tr{cls}><td>{p["label"]}</td><td class="n">{fmt(p["count"])}</td><td class="n">{bold}</td><td class="n">{p["aov"]}</td></tr>'

    # error-by-screen rows
    err_total = d["errors"]; scr_rows = ""
    for i, (scr, c) in enumerate(d["err_screens"]):
        cls = ' class="cr"' if i == 0 else (' class="hl"' if i in (1, 2) else "")
        pct = f'{c/err_total*100:.1f}%' if err_total else "—"
        pctcell = f'<span class="down"><strong>{pct}</strong></span>' if i == 0 else pct
        scr_rows += f'<tr{cls}><td>{scr}</td><td class="n">{fmt(c)}</td><td class="n">{pctcell}</td></tr>'

    # version rows
    ver_rows = ""
    for v in d["versions"][:5]:
        is_junk = v in d["junk"]
        cls = ' class="cr"' if is_junk else ""
        orders_cell = f'<span class="down"><strong>0 ⚠</strong></span>' if is_junk else fmt(v["orders"])
        name = f'<strong>{v["version"]}</strong>' if is_junk else v["version"]
        rage_cell = fmt(v["rage"]) if v["rage"] else "0"
        ver_rows += (f'<tr{cls}><td>{name}</td><td>{v["os"]}</td><td class="n">{orders_cell}</td>'
                     f'<td class="n">{fmt(v["errors"])}</td><td class="n">{rage_cell}</td></tr>')

    # ── dynamic ISSUES (rule-based) ──
    issues = []
    if d["junk"]:
        jv = d["junk"][0]
        issues.append(('cr', f'{jv["version"]}: ~{fmt(jv["users"])} جلسة يومية بصفر نشاط — traffic مشبوه يضخّم المقاييس', 'ثقة عالية', [
            ('الدليل', f'{ar_date}: {fmt(jv["total"])} حدثًا من {fmt(jv["users"])} مستخدمًا — <strong>0 مشاهدة منتج، 0 إضافة للسلة، 0 طلب</strong>.'),
            ('التأثير', f'يضخّم الـDAU (بدونه ~{fmt(d["dau_clean"])} مقابل {fmt(d["dau"])}) ويولّد {fmt(jv["errors"])} خطأ/يوم — يلوّث مقاييس الصحة.'),
            ('الإجراء', '<span class="tag t-dt">Data</span><span class="tag t-bk">Backend</span> فحص الأجهزة/الـIP وتدفق الشاشات: bots ← فلترة، إصدار معطّل ← تحديث إجباري. لا يُحتسب كخسارة قبل التحقق.')]))
    if d["dns"] > 200:
        issues.append(('cr', f'فشل DNS في ids.8orders.com عبر عدة شاشات', 'ثقة عالية', [
            ('الدليل', f'{fmt(d["dns"])} خطأ "Failed host lookup / SocketException" مرتبط بـids.8orders.com.'),
            ('التأثير', 'خدمة الهوية غير متاحة ← فشل صامت في المصادقة/التخصيص ← احتكاك محتمل في الـCheckout.'),
            ('الإجراء', '<span class="tag t-bk">Backend</span> التحقق من DNS/CDN لـids.8orders.com · إضافة معالجة بديلة عند فشل الاتصال')]))
    top_scr, top_scr_c = (d["err_screens"][0] if d["err_screens"] else ("—", 0))
    if err_total and top_scr_c / err_total > 0.35:
        issues.append(('hi', f'أخطاء مركّزة في {top_scr} — {top_scr_c/err_total*100:.0f}% من كل الأخطاء', 'ثقة عالية', [
            ('الدليل', f'{fmt(top_scr_c)} خطأ على {top_scr} · أبرز رسالة: {d["top_err"][0]} ({fmt(d["top_err"][1])}).'),
            ('التأثير', 'يغمر PostHog ويخفي الأخطاء الحقيقية.'),
            ('الإجراء', '<span class="tag t-mob">Mobile</span> تحديد السبب · إضافة platform guard أو try/catch')]))
    if conv_drop > 5:
        issues.append(('hi', f'تراجع التحويل من السلة إلى الطلب: {conv:.1f}% مقابل {base_conv:.1f}% (↓{conv_drop:.0f}%)', 'ثقة عالية', [
            ('الدليل', f'الإضافة للسلة {chg_arrow(t_dau_cart(d))} ({fmt(rev["orders"])} طلب) · ~{d["lost_orders"]} طلب مفقود/يوم · ~{fmt(d["lost_rev"])} جنيه.'),
            ('الفرضية', 'احتكاك في الـCheckout (أخطاء الشاشة، رسوم التوصيل، الحد الأدنى للطلب).'),
            ('الإجراء', '<span class="tag t-mob">Mobile</span> إضافة checkout_started · مراجعة أخطاء شاشة السلة · مراجعة تسجيلات "أضاف للسلة ولم يطلب"')]))
    ios_rage = sum(v["rage"] for v in d["versions"] if "ios" in (v["os"] or "").lower() or "ipad" in (v["os"] or "").lower())
    and_rage = sum(v["rage"] for v in d["versions"] if "android" in (v["os"] or "").lower())
    if d["rage"] > 100 and and_rage == 0:
        issues.append(('hi', 'كل الـRage Clicks على iOS — Android يُظهر صفرًا', 'ثقة متوسطة', [
            ('الدليل', f'{fmt(ios_rage)} Rage Click من iOS · Android: صفر تمامًا.'),
            ('تحفظ', 'قد تكون مشكلة Tracking على Android لا مشكلة UX على iOS. يجب التحقق أولًا.'),
            ('الإجراء', f'<span class="tag t-mob">Mobile</span> التحقق من دعم Rage Click على Flutter Android' + (f' · أفضل جلسة: <span style="direction:ltr;display:inline-block;font-size:7.5pt;">{s["sid"]}</span>' if s else ''))]))
    if t_reorder.get("raw", 0) < -25:
        issues.append(('md', f'تراجع نية إعادة الطلب بـ{t_reorder["pct"]} في يوم واحد', 'ثقة متوسطة', [
            ('الدليل', f'reorder_initiated: {d["reorder"]} مقابل {d["prev_reorder"]} ({t_reorder["arrow"]}{t_reorder["pct"]}).'),
            ('الإجراء', '<span class="tag t-op">Ops</span> ربط جودة طلبات اليوم السابق بهذا التراجع · فحص مسار Reorder')]))

    issues_html = ""
    for sev, title, conf, rows in issues:
        cf = 'cf-h' if 'عالية' in conf else 'cf-m'
        sev_ar = {'cr':'حرج','hi':'عالي','md':'متوسط'}[sev]
        rows_html = "".join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in rows)
        issues_html += f'''
  <div class="issue {sev}">
    <div class="issue-top"><div class="issue-title">{title}</div>
      <div class="issue-badges"><span class="sev {sev}">{sev_ar}</span><span class="sev {cf}">{conf}</span></div>
      <div class="iclear"></div></div>
    <div class="issue-body"><table class="issue-row-grid">{rows_html}</table></div>
  </div>'''

    # ── dynamic ACTIONS ──
    actions = []
    if d["junk"]:
        jv = d["junk"][0]
        actions.append(('p0', f'التحقق من طبيعة traffic الإصدار {jv["version"]}',
            f'~{fmt(jv["users"])} جلسة/يوم بصفر تصفّح/سلة/طلب و{fmt(jv["total"])} حدثًا تضخّم DAU والأخطاء. افحص الأجهزة/الـIP: bots ← فلترة؛ إصدار معطّل ← تحديث إجباري. لا تُحتسب كخسارة قبل التحقق.',
            '<span class="tag t-dt">Data</span><span class="tag t-bk">Backend</span>'))
    if d["dns"] > 200:
        actions.append(('p0', 'فحص DNS وCDN لـ ids.8orders.com وإضافة fallback',
            f'{fmt(d["dns"])} فشل اتصال عبر عدة شاشات. خدمة الهوية غير متاحة قد تسبب فشلًا صامتًا في تسجيل الدخول وإتمام الطلب.',
            '<span class="tag t-bk">Backend</span>'))
    actions.append(('p0', 'إضافة حدثَي checkout_started و payment_failed',
        'التحويل من السلة لا يمكن تشخيصه بدون checkout_started. فشل الدفع نقطة عمياء تامة حاليًا.',
        '<span class="tag t-mob">Mobile</span><span class="tag t-dt">Data</span>'))
    if err_total and top_scr_c / err_total > 0.35:
        actions.append(('p1', f'إصلاح الأخطاء في {top_scr}',
            f'{fmt(top_scr_c)} خطأ/يوم = {top_scr_c/err_total*100:.0f}% من كل الأخطاء. يغمر PostHog ويخفي المشاكل الحقيقية.',
            '<span class="tag t-mob">Mobile</span>'))
    if conv_drop > 5:
        actions.append(('p1', 'مراجعة تسجيلات "أضاف للسلة ولم يطلب"',
            'جوهر تراجع التحويل. افتح أخطر جلسة وجلسات مماثلة لتحديد نقطة الاحتكاك بين السلة وإتمام الطلب.',
            '<span class="tag t-op">Ops</span><span class="tag t-mob">Mobile</span>'))
    actions.append(('p2', 'إضافة خصائص: المدينة/المنطقة + سبب الإلغاء + كلمة البحث',
        'ثغرات قابلة للحل في sprint واحد بإضافة properties فقط. تفتح: التحليل الجغرافي، تشخيص الإلغاءات، تحسين البحث.',
        '<span class="tag t-dt">Data</span><span class="tag t-mob">Mobile</span>'))
    actions_html = ""
    for i, (p, title, why, tags) in enumerate(actions):
        actions_html += f'''
  <div class="action {p}"><div class="action-num">{p.upper()}</div>
    <div class="action-body"><div class="action-title">{title}</div>
    <div class="action-why">{why}</div><div style="margin-top:5px;">{tags}</div></div></div>'''

    health = "تحتاج متابعة" if (conv_drop > 5 or t_orders.get("raw", 0) < -3) else "مستقرة"
    health_icon = "⚠" if health != "مستقرة" else "✓"
    cart_t = trend(d["conv_series"][day]["cart"], d["conv_series"][prev]["cart"], good_up=True)

    # ── "الإيجابي اليوم" card: pick a metric that actually improved, color by good/bad ──
    # Each candidate: (label, trend-dict, good_up). cls=="up" means it moved the good way.
    _pos_candidates = [
        ("الإضافة للسلة", cart_t, True),
        ("الإيرادات", t_rev, True),
        ("الطلبات", t_orders, True),
        ("الإلغاء", t_cancel, False),
        ("الأخطاء", t_err, False),
        ("إعادة الطلب", t_reorder, True),
        ("الكوبونات", t_voucher, True),
    ]
    _good = [c for c in _pos_candidates if c[1]["cls"] == "up"]
    _good.sort(key=lambda c: abs(c[1].get("raw", 0)), reverse=True)
    _pos_color = {"up": "#16a34a", "down": "#dc2626", "flat": "#64748b"}
    if _good:
        _lead_label, _lead_t, _ = _good[0]
        pos_headline = f'{_lead_label} {_lead_t["arrow"]}{_lead_t["pct"]}'
        pos_headline_color = "#16a34a"
        # next-best improvements as support; fall back to errors/cancel if only one improved
        _support = _good[1:3] or [("الأخطاء", t_err, False), ("الإلغاء", t_cancel, False)]
    else:
        # nothing genuinely improved today — say so honestly instead of greenwashing
        pos_headline = "لا تحسّن واضح اليوم"
        pos_headline_color = "#64748b"
        _support = [("الأخطاء", t_err, False), ("الإلغاء", t_cancel, False)]
    pos_sub = " · ".join(
        f'<span style="color:{_pos_color[t["cls"]]};">{lbl} {t["arrow"]}{t["pct"]}</span>'
        for lbl, t, *_ in _support
    )

    # ── "أكبر خطر" card: reflect the real top risk, not a hardcoded conversion drop ──
    if conv_drop > 5:
        risk_color = "#dc2626"
        risk_title = f'السلة ← الطلب {conv_arrow}{conv_abs:.0f}%'
        risk_sub = f'خسارة ~{fmt(d["lost_rev"])} جنيه/يوم'
    elif d["junk"]:
        jv0 = d["junk"][0]
        risk_color = "#dc2626"
        risk_title = f'جلسات junk · {jv0["version"]}'
        risk_sub = f'~{fmt(jv0["users"])} جلسة بصفر نشاط'
    elif d["dns"] > 200:
        risk_color = "#dc2626"
        risk_title = f'فشل DNS · {fmt(d["dns"])}'
        risk_sub = 'ids.8orders.com'
    else:
        risk_color = "#16a34a"
        risk_title = 'لا مخاطر حرجة'
        risk_sub = 'كل المؤشرات ضمن النطاق'

    # ── executive conversion sentence: phrased by actual direction ──
    if conv_drop > 0.5:
        conv_sentence = (f'التحويل من السلة إلى الطلب هبط من {base_conv:.1f}% إلى {conv:.1f}% — '
                         f'أي فقدان ~{d["lost_orders"]} طلبًا و<strong>{fmt(d["lost_rev"])} جنيه يوميًا</strong> '
                         f'لو ظلّ التحويل عند خطه الأساسي.')
    elif conv_drop < -0.5:
        conv_sentence = (f'التحويل من السلة إلى الطلب ارتفع من {base_conv:.1f}% إلى {conv:.1f}% — '
                         f'أعلى من خطه الأساسي، دون فقدان طلبات.')
    else:
        conv_sentence = (f'التحويل من السلة إلى الطلب مستقر عند {conv:.1f}% '
                         f'(الأساس {base_conv:.1f}%) — ضمن النطاق الطبيعي.')

    # ── conversion-funnel loss box (section 03): loss framing only when it actually dropped ──
    if conv_drop > 0.5:
        loss_box = f'''<div class="box" style="background:#fef2f2; border-color:rgba(220,38,38,0.3);">
      <div class="box-t" style="color:#dc2626;">⚠ خسارة تقديرية من تراجع التحويل</div>
      <table class="dt"><tbody>
        <tr><td>التحويل الأساسي</td><td class="n">{base_conv:.1f}%</td></tr>
        <tr><td>التحويل اليوم</td><td class="n down"><strong>{conv:.1f}%</strong></td></tr>
        <tr><td>الطلبات المتوقعة عند الأساس</td><td class="n">~{fmt(d["expected_orders"])}</td></tr>
        <tr class="cr"><td><strong>طلبات مفقودة/يوم</strong></td><td class="n down"><strong>~{d["lost_orders"]}</strong></td></tr>
        <tr class="cr"><td><strong>خسارة (× AOV {fmt(rev["aov"])})</strong></td><td class="n down"><strong>~{fmt(d["lost_rev"])} ج/يوم</strong></td></tr>
      </tbody></table>
      <div style="font-size:7.5pt; color:#991b1b; margin-top:6px;">لا يوجد checkout_started ← لا يمكن تحديد نقطة التسرب بدقة.</div></div>'''
    else:
        _conv_word = "ارتفع" if conv_drop < -0.5 else "ظل مستقرًا"
        loss_box = f'''<div class="box" style="background:#f0fdf4; border-color:rgba(22,163,74,0.3);">
      <div class="box-t" style="color:#16a34a;">✓ التحويل ضمن النطاق — لا خسارة مقدّرة</div>
      <table class="dt"><tbody>
        <tr><td>التحويل الأساسي</td><td class="n">{base_conv:.1f}%</td></tr>
        <tr><td>التحويل اليوم</td><td class="n"><strong>{conv:.1f}%</strong></td></tr>
        <tr><td>الطلبات المتوقعة عند الأساس</td><td class="n">~{fmt(d["expected_orders"])}</td></tr>
        <tr><td><strong>طلبات مفقودة/يوم</strong></td><td class="n"><strong>0</strong></td></tr>
        <tr><td><strong>خسارة مقدّرة</strong></td><td class="n"><strong>0 ج/يوم</strong></td></tr>
      </tbody></table>
      <div style="font-size:7.5pt; color:#166534; margin-top:6px;">التحويل {_conv_word} مقارنةً بالخط الأساسي (متوسط 3 أيام عمل) — لا تسرب يستوجب التحقيق.</div></div>'''

    # ── Section: acquisition / activation / coverage ──
    _a = d["acq"]; _cov = d["coverage"]; _cp = d["cart_problems"]
    _act_pct = (_a["acc_order"] / _a["acc"] * 100) if _a["acc"] else 0.0
    acq_cards = (
        '<table class="kpi-grid"><tr>'
        f'<td class="kc"><div class="kc-lbl">حسابات جديدة اليوم</div><div class="kc-val">{fmt(_a["acc"])}</div>'
        f'<div class="kc-sub">account_created · أنشأ عنوانًا: {fmt(_a["acc_addr"])}</div></td>'
        f'<td class="kc {"good" if _act_pct >= 20 else "warn"}"><div class="kc-lbl">تفعيل نفس اليوم</div>'
        f'<div class="kc-val">{_act_pct:.0f}%</div><div class="kc-sub">{fmt(_a["acc_order"])} من {fmt(_a["acc"])} طلبوا في نفس اليوم</div></td>'
        f'<td class="kc warn"><div class="kc-lbl">حاولوا الطلب ولم يطلبوا</div><div class="kc-val">{fmt(_a["cart_no"])}</div>'
        f'<div class="kc-sub">أضافوا للسلة بلا طلب اليوم (من {fmt(_a["cart"])} وصلوا للسلة)</div></td>'
        f'<td class="kc alert"><div class="kc-lbl">عملاء جدد تصفّحوا ولم يطلبوا</div><div class="kc-val">{fmt(_a["new_browse_no"])}</div>'
        f'<div class="kc-sub">لم يطلبوا قَط · منهم {fmt(_a["new_cart_no"])} وصلوا للسلة</div></td>'
        '</tr></table>'
    )
    def _pct(n, base):
        return f'{n / base * 100:.0f}%' if base else '—'
    _inst = _cov["installed"] or 1
    funnel_rows = (
        f'<tr><td>ثبّتوا التطبيق</td><td class="n">{fmt(_cov["installed"])}</td><td class="n">100%</td></tr>'
        f'<tr class="hl"><td>أنشأوا حسابًا</td><td class="n">{fmt(_cov["inst_reg"])}</td><td class="n">{_pct(_cov["inst_reg"], _inst)}</td></tr>'
        f'<tr><td>شاهدوا متجرًا (داخل التغطية)</td><td class="n">{fmt(_cov["inst_saw"])}</td><td class="n">{_pct(_cov["inst_saw"], _inst)}</td></tr>'
        f'<tr class="cr"><td>طلبوا فعليًا</td><td class="n">{fmt(_cov["inst_ord"])}</td><td class="n">{_pct(_cov["inst_ord"], _inst)}</td></tr>'
    )
    _ono = _cov["addr_no_store"]; _onp = _pct(_ono, _cov["acc"])
    cov_callout = (
        '<div style="margin-top:8px; background:#fef2f2; border:1px solid rgba(220,38,38,0.3); '
        'border-radius:6px; padding:8px 10px; font-size:8pt; color:#991b1b; line-height:1.7;">'
        f'<strong>⚠ مؤشّر خارج نطاق التوصيل:</strong> {fmt(_ono)} عميلًا جديدًا ({_onp}) أنشأوا عنوان توصيل '
        'ولم يظهر لهم أي متجر — أي على الأرجح خارج تغطية الغردقة/أسيوط. الإعلانات تجلب مستخدمين من خارج نطاق الخدمة.</div>')
    _top_err_line = ""
    if _cp["messages"]:
        m0 = _cp["messages"][0]
        _top_err_line = (
            '<div style="font-size:8pt; color:#334155; margin-top:10px; line-height:1.7;">'
            f'<strong>أبرز عائق فني لغير المُكمِّلين:</strong> {m0[0]} ({fmt(m0[1])}) — '
            f'إجمالي {fmt(_cp["err_events"])} خطأ على {fmt(_cp["err_users"])} مستخدم، و{fmt(_cp["rage"])} نقرة غضب (Rage).</div>')
    growth_section = f'''
<div class="section">
  <div class="section-hdr"><span class="sec-num">09</span><span class="sec-title">اكتساب وتفعيل العملاء الجدد والتغطية</span></div>
  {acq_cards}
  <table class="tc" style="margin-top:12px;"><tr>
    <td style="width:54%;"><div class="box-t">قمع المثبّتين → الطلب · آخر {_cov["window_days"]} أيام (بدون GeoIP)</div>
      <table class="dt"><thead><tr><th>الخطوة</th><th class="n">أشخاص</th><th class="n">% من المثبّتين</th></tr></thead>
      <tbody>{funnel_rows}</tbody></table>
      {cov_callout}</td>
    <td style="width:46%;"><div class="box">
      <div class="box-t">قراءة سريعة · التغطية</div>
      <div style="font-size:8.5pt; color:#0f172a; line-height:1.8;">الخدمة حاليًا في <strong>الغردقة وأسيوط فقط</strong>. لا نعتمد على GeoIP لتحديد الموقع لأنه غير موثوق في مصر (يكوّم مستخدمين من كل المحافظات تحت «القاهرة»). البديل الموثوق: من ينشئ عنوان توصيل ولا يظهر له متجر فهو غالبًا خارج التغطية.</div>
      {_top_err_line}
    </div></td>
  </tr></table>
  <div class="data-note">مقاسة آليًا من PostHog (بدون GeoIP). أعمق خطوة شراء متتبَّعة بثقة هي add_to_cart (لا يوجد checkout_started). «لم يطلب قَط» محسوب على order_placed وPurchase معًا. لقياس التغطية مباشرةً: على التطبيق إرسال المنطقة/المدينة المختارة كخاصية على account_created وaddress_created.</div>
</div>
'''

    body = f'''
<div class="cover">
  <div class="cover-top">
    <div class="cover-logo">8<span>Orders</span></div>
    <div class="cover-meta" style="direction:ltr; text-align:left;">
      Daily Product Intelligence Report<br>
      <strong style="color:#fff">{dd.strftime("%a, %d %B %Y")}</strong><br>
      Business day 08:00→04:00 · Africa/Cairo<br>
      PostHog #{PROJECT} · Generated {gen_date.strftime("%d %b %Y")} {gen_clock} Cairo
    </div>
    <div class="cover-clear"></div>
  </div>
  <div class="cover-title">تقرير الذكاء اليومي للمنتج</div>
  <div class="cover-sub">توصيل طعام وبقالة · ملخص لمدير المنتج</div>
  <div class="health-pill">{health_icon} حالة المنتج: {health}</div>
  {sess_box}
</div>

<div class="body">

<div class="section">
  <div class="section-hdr"><span class="sec-num">01</span><span class="sec-title">الخلاصة التنفيذية</span></div>
  <div class="verify-note">✓ <strong>كل الأرقام مسحوبة ومتحقَّق منها آليًا من PostHog عند التوليد ({gen_ar}).</strong> الإيرادات مقاسة فعليًا من <span style="direction:ltr;display:inline-block;">order_placed.total_amount</span> (وليست تقديرية).</div>
  <table style="width:100%; border-collapse:separate; border-spacing:6px; margin-bottom:12px;"><tr>
    <td style="background:#0f172a; color:#fff; border-radius:8px; padding:12px 14px; width:33%; text-align:center;">
      <div style="font-size:7pt; font-weight:700; color:#94a3b8; letter-spacing:1px; margin-bottom:4px;">حالة المنتج</div>
      <div style="font-size:14pt; font-weight:900; color:#fb923c;">{health}</div></td>
    <td style="background:#f0fdf4; border:1px solid rgba(22,163,74,0.3); border-radius:8px; padding:12px 14px; width:33%; text-align:center;">
      <div style="font-size:7pt; font-weight:700; color:#64748b; letter-spacing:1px; margin-bottom:4px;">الإيجابي اليوم</div>
      <div style="font-size:12pt; font-weight:900; color:{pos_headline_color};">{pos_headline}</div>
      <div style="font-size:7pt; color:#64748b;">{pos_sub}</div></td>
    <td style="background:{'#f0fdf4' if risk_color=='#16a34a' else '#fef2f2'}; border:1px solid {'rgba(22,163,74,0.3)' if risk_color=='#16a34a' else 'rgba(220,38,38,0.3)'}; border-radius:8px; padding:12px 14px; width:33%; text-align:center;">
      <div style="font-size:7pt; font-weight:700; color:#64748b; letter-spacing:1px; margin-bottom:4px;">أكبر خطر</div>
      <div style="font-size:12pt; font-weight:900; color:{risk_color};">{risk_title}</div>
      <div style="font-size:7pt; color:#64748b;">{risk_sub}</div></td>
  </tr></table>
  <div class="exec-section">
    <p>الإقبال على المنتجات والإضافة للسلة {cart_t["arrow"]}{cart_t["pct"]}، بينما الطلبات {t_orders["arrow"]}{t_orders["pct"]} والإيرادات {t_rev["arrow"]}{t_rev["pct"]}.</p>
    <p><strong>{fmt(rev["orders"])} طلبًا · {money_k(rev["revenue"])} جنيه إيرادات (مقاسة) · متوسط طلب {fmt(rev["aov"])} جنيهًا.</strong> {conv_sentence}</p>
    {"<p><strong>تنبيه جودة بيانات:</strong> الإصدار " + d["junk"][0]["version"] + f" يُنتج ~{fmt(d['junk'][0]['users'])} جلسة يومية بصفر نشاط رغم {fmt(d['junk'][0]['total'])} حدثًا — يحتاج تحقيقًا قبل اعتباره خسارة.</p>" if d["junk"] else ""}
    <div class="exec-action">⚡ راجع قسمي المشاكل والإجراءات أدناه — كلها مبنية على بيانات اليوم.</div>
  </div>
</div>

<div class="section">
  <div class="section-hdr"><span class="sec-num">02</span><span class="sec-title">مؤشرات صحة المنتج</span></div>
  <div class="note"><strong>السياق:</strong> يوم العمل يُحسب من 8 صباحًا حتى 2 صباحًا اليوم التالي (نافذة 18 ساعة، توقيت القاهرة) — وليس اليوم التقويمي. كل المقارنات مقابل يوم العمل السابق ({dt.date.fromisoformat(prev).day} {AR_MONTHS[dt.date.fromisoformat(prev).month]}). الخط الأساسي للتحويل = متوسط 3 أيام عمل سابقة.</div>
  <table class="kpi-grid">
    <tr>
      <td class="kc"><div class="kc-lbl">المستخدمون اليوميون (DAU)</div><div class="kc-val">{fmt(d["dau"])}</div>
        {chg_span(t_dau, "مقارنة بالأمس")}{junk_note}{dau_note}</td>
      <td class="kc {'good' if t_install['cls']=='up' else ''}"><div class="kc-lbl">تثبيتات جديدة</div><div class="kc-val">{fmt(d["installs"])}</div>
        {chg_span(t_install, "مقارنة بالأمس")}<div class="kc-sub">حسابات جديدة: {fmt(d["accounts"])}</div></td>
      <td class="kc"><div class="kc-lbl">فتحات التطبيق</div><div class="kc-val">{fmt(d["app_opens"])}</div>
        {chg_span(trend(d["app_opens"], d["prev_app_opens"]), "مقارنة بالأمس")}<div class="kc-sub">حدث Application Opened</div></td>
      <td class="kc warn"><div class="kc-lbl">إجمالي الطلبات</div><div class="kc-val">{fmt(rev["orders"])}</div>
        {chg_span(t_orders, "مقارنة بالأمس")}<div class="kc-sub">إيراد: {money_k(rev["revenue"])} جنيه</div></td>
    </tr>
    <tr>
      <td class="kc {'warn' if t_rev['cls']=='down' else 'good'}"><div class="kc-lbl">الإيرادات (مقاسة)</div><div class="kc-val" style="font-size:15pt;">{money_k(rev["revenue"])}</div>
        {chg_span(t_rev)}<div class="kc-sub">AOV: {fmt(rev["aov"])} جنيه</div></td>
      <td class="kc {'alert' if conv_drop>5 else ''}"><div class="kc-lbl">تحويل السلة ← طلب</div><div class="kc-val">{conv:.1f}%</div>
        <span class="kc-chg {conv_cls}">{conv_arrow} {conv_abs:.0f}% عن الأساس {base_conv:.1f}%</span>
        <div class="kc-sub" style="{'color:#dc2626; font-weight:700;' if conv_drop>5 else 'color:#64748b;'}">{'مؤشر شذوذ — يستوجب التحقيق' if conv_drop>5 else 'ضمن النطاق'}</div></td>
      <td class="kc {'good' if t_cancel['cls']=='up' else 'warn'}"><div class="kc-lbl">معدل الإلغاء</div><div class="kc-val">{cancel_rate:.1f}%</div>
        {chg_span(t_cancel)}<div class="kc-sub">{fmt(d["cancel"])} إلغاء (غير مدفوع)</div></td>
      <td class="kc {'good' if t_err['cls']=='up' else 'alert'}"><div class="kc-lbl">أخطاء التطبيق</div><div class="kc-val">{fmt(d["errors"])}</div>
        {chg_span(t_err)}<div class="kc-sub">~{err_per_100:.0f} خطأ لكل 100 فتح</div></td>
    </tr>
    <tr>
      <td class="kc alert"><div class="kc-lbl">Rage Clicks</div><div class="kc-val">{fmt(d["rage"])}</div>
        <span class="kc-chg down">{'100% من iOS' if and_rage==0 else 'موزّعة'}</span><div class="kc-sub">iOS مقابل Android</div></td>
      <td class="kc {'alert' if t_reorder['cls']=='down' else ''}"><div class="kc-lbl">نية إعادة الطلب</div><div class="kc-val">{fmt(d["reorder"])}</div>
        {chg_span(t_reorder)}<div class="kc-sub">reorder_initiated</div></td>
      <td class="kc {'good' if t_voucher['cls']=='up' else ''}"><div class="kc-lbl">كوبونات مُفعَّلة</div><div class="kc-val">{fmt(d["voucher"])}</div>
        {chg_span(t_voucher)}<div class="kc-sub">voucher_applied</div></td>
      <td class="kc warn"><div class="kc-lbl">بحث بلا نتائج</div><div class="kc-val">{fmt(d["search_no"])}</div>
        <span class="kc-chg flat">search_no_results</span><div class="kc-sub">عدد صغير — يُراقَب</div></td>
    </tr>
  </table>
</div>

<div class="pb"></div>

<div class="section">
  <div class="section-hdr"><span class="sec-num">03</span><span class="sec-title">تحليل مسار التحويل</span>{'<span class="sec-badge cr" style="float:left;">الأهم</span>' if conv_drop>5 else ''}</div>
  <div class="note"><strong>ملاحظة:</strong> أعداد أحداث مستقلة وليست مسارًا تسلسليًا صارمًا. أهم علاقة: <strong>إضافة للسلة ← طلب</strong>.</div>
  <table class="tc"><tr>
    <td style="width:50%;"><div class="box"><div class="box-t">اتجاه التحويل من السلة</div>
      <table class="dt"><thead><tr><th>اليوم</th><th class="n">سلة</th><th class="n">طلبات</th><th class="n">تحويل</th></tr></thead>
      <tbody>{conv_rows}</tbody></table></div></td>
    <td style="width:50%;">{loss_box}</td>
  </tr></table>
</div>

<div class="section avoid">
  <div class="section-hdr"><span class="sec-num">04</span><span class="sec-title">الطلبات والإيرادات وطرق الدفع</span></div>
  <table class="tc"><tr>
    <td style="width:48%;"><table class="dt"><thead><tr><th>المؤشر</th><th class="n">اليوم</th><th class="n">الأمس</th><th class="n">التغيير</th></tr></thead>
      <tbody>
        <tr><td>إجمالي الطلبات</td><td class="n">{fmt(rev["orders"])}</td><td class="n">{fmt(prev_rev["orders"])}</td><td class="n {t_orders['cls']}">{t_orders['arrow']} {t_orders['pct']}</td></tr>
        <tr><td>الإيرادات (مقاسة)</td><td class="n">{money_k(rev["revenue"])} ج</td><td class="n">{money_k(prev_rev["revenue"])} ج</td><td class="n {t_rev['cls']}">{t_rev['arrow']} {t_rev['pct']}</td></tr>
        <tr><td>متوسط الطلب (AOV)</td><td class="n">{fmt(rev["aov"])} ج</td><td class="n">{fmt(prev_rev["aov"])} ج</td><td class="n {trend(rev['aov'],prev_rev['aov'])['cls']}">{trend(rev['aov'],prev_rev['aov'])['arrow']}</td></tr>
        <tr class="gd"><td>الإلغاءات</td><td class="n">{fmt(d["cancel"])}</td><td class="n">{fmt(d["prev_cancel"])}</td><td class="n {t_cancel['cls']}">{t_cancel['arrow']} {t_cancel['pct']}</td></tr>
        <tr class="hl"><td>إعادة الطلب</td><td class="n">{fmt(d["reorder"])}</td><td class="n">{fmt(d["prev_reorder"])}</td><td class="n {t_reorder['cls']}">{t_reorder['arrow']} {t_reorder['pct']}</td></tr>
        <tr><td>تقييمات الطلبات</td><td class="n">{fmt(d["rating"])}</td><td class="n">{fmt(d["prev_rating"])}</td><td class="n {trend(d['rating'],d['prev_rating'])['cls']}">{trend(d['rating'],d['prev_rating'])['arrow']} {trend(d['rating'],d['prev_rating'])['pct']}</td></tr>
        <tr class="gd"><td>تواصل مع الدعم</td><td class="n">{fmt(d["support"])}</td><td class="n">{fmt(d["prev_support"])}</td><td class="n {trend(d['support'],d['prev_support'],good_up=False)['cls']}">{trend(d['support'],d['prev_support'],good_up=False)['arrow']} {trend(d['support'],d['prev_support'],good_up=False)['pct']}</td></tr>
      </tbody></table></td>
    <td style="width:52%;"><div class="box-t">توزيع طرق الدفع · {ar_date} ({fmt(d["pay_total"])} طلب)</div>
      <table class="dt"><thead><tr><th>طريقة الدفع</th><th class="n">الطلبات</th><th class="n">النسبة</th><th class="n">متوسط الطلب</th></tr></thead>
      <tbody>{pay_rows}</tbody></table>
      <div style="margin-top:7px; font-size:7.5pt; color:#334155; line-height:1.6;">⚠ لا يوجد حدث payment_failed ← فشل الدفع نقطة عمياء داخل PostHog (التوزيع أعلاه للطلبات الناجحة فقط).</div>
      <div style="margin-top:6px; background:#eff6ff; border:1px solid rgba(37,99,235,0.25); border-radius:6px; padding:7px 9px; font-size:7.5pt; color:#1e3a8a; line-height:1.65;">{PAYMENT_CONTEXT_NOTE}</div></td>
  </tr></table>
</div>

<div class="pb"></div>

<div class="section">
  <div class="section-hdr"><span class="sec-num">05</span><span class="sec-title">جودة التطبيق والأخطاء والإصدارات</span></div>
  <table class="tc"><tr>
    <td style="width:50%;"><div class="box-t">الأخطاء حسب الشاشة · {ar_date} (المجموع: {fmt(err_total)})</div>
      <table class="dt"><thead><tr><th>الشاشة</th><th class="n">أخطاء</th><th class="n">من الإجمالي</th></tr></thead>
      <tbody>{scr_rows}</tbody></table></td>
    <td style="width:50%;"><div class="box-t">أداء الإصدارات · {ar_date}</div>
      <table class="dt"><thead><tr><th>الإصدار</th><th>المنصة</th><th class="n">الطلبات</th><th class="n">الأخطاء</th><th class="n">Rage</th></tr></thead>
      <tbody>{ver_rows}</tbody></table>
      {("<div style='margin-top:8px; background:#fef2f2; border:1px solid rgba(220,38,38,0.3); border-radius:6px; padding:8px 10px; font-size:8pt; color:#991b1b; line-height:1.6;'><strong>⚠ الإصدار " + d["junk"][0]["version"] + " — ~" + fmt(d["junk"][0]["users"]) + " جلسة و" + fmt(d["junk"][0]["total"]) + " حدثًا بصفر تصفّح/سلة/طلب.</strong><br>نمط غير بشري أو إصدار معطّل. يحتاج تحقيقًا، وليس مجرد تحديث إجباري.</div>") if d["junk"] else ""}
      <div style="margin-top:8px; font-size:8pt; color:#334155; line-height:1.7;"><strong>أبرز رسالة خطأ:</strong> {d["top_err"][0]} ({fmt(d["top_err"][1])}).</div></td>
  </tr></table>
</div>

<div class="section">
  <div class="section-hdr"><span class="sec-num">06</span><span class="sec-title">المشاكل والشذوذات</span><span class="sec-badge cr" style="float:left;">القسم الحرج</span></div>
  {issues_html if issues_html else '<div class="note">لا توجد شذوذات حرجة اليوم وفق القواعد المحددة.</div>'}
</div>

<div class="pb"></div>

<div class="section">
  <div class="section-hdr"><span class="sec-num">07</span><span class="sec-title">تسجيلات الجلسات</span><span class="sec-badge cr" style="float:left;">مهم جدًا</span></div>
  {featured_block}
  <div style="font-size:7.5pt; color:#64748b; margin-top:4px;">ملاحظة: مدة النشاط من API؛ قد يعرض المشغّل مدة أقصر بعد ضغط فترات الخمول.</div>
</div>

<div class="section">
  <div class="section-hdr"><span class="sec-num">08</span><span class="sec-title">الإجراءات الفورية المطلوبة</span></div>
  {actions_html}
</div>

{growth_section}
<div class="section avoid">
  <div class="section-hdr"><span class="sec-num">10</span><span class="sec-title">ثغرات البيانات والتتبع</span></div>
  <div class="data-note" style="margin-top:0; margin-bottom:10px;">✓ <strong>متاح فعليًا:</strong> الإيرادات (total_amount)، طريقة الدفع، رسوم التوصيل، الخصم، إصدار التطبيق — خصائص على order_placed. لذلك الإيرادات والـAOV مقاسة بدقة.</div>
  <div class="gap"><div class="gap-title"><span class="p0-t">P0</span> &nbsp; checkout_started غير مسجَّل</div><div class="gap-body">لا يمكن تحديد نقطة تسرب التحويل. أضف: cart_value، delivery_fee، vertical، city.</div></div>
  <div class="gap"><div class="gap-title"><span class="p1-t">P1</span> &nbsp; منطقة التوصيل غير مُرسَلة كخاصية</div><div class="gap-body">التغطية تُقاس حاليًا تقديريًا بالـGeoIP. أضف area_id/area_name وwithin_coverage على account_created وSelect Area وaddress_created لقياسها مباشرةً.</div></div>
  <div class="gap"><div class="gap-title"><span class="p0-t">P0</span> &nbsp; payment_failed غير مسجَّل</div><div class="gap-body">لا معدل فشل حسب طريقة الدفع. أضف: payment_method، failure_reason، error_code.</div></div>
  <div class="gap"><div class="gap-title"><span class="p1-t">P1</span> &nbsp; المدينة/المنطقة غير موجودة على order_placed</div><div class="gap-body">store_id فارغ غالبًا ولا city/zone. أضف: city، zone_id، store_id.</div></div>
  <div class="gap"><div class="gap-title"><span class="p1-t">P1</span> &nbsp; سبب الإلغاء وكلمة البحث غير مسجَّلين</div><div class="gap-body">أضف reason على الإلغاء، وsearch_query وresult_count على البحث.</div></div>
  <div class="gap"><div class="gap-title"><span class="p1-t">P1</span> &nbsp; النقرات الغاضبة (Rage) تُلتقَط على iOS فقط</div><div class="gap-body">أندرويد يُصدِّر صفر rageclick، فترتيب "الجلسات الأكثر احتكاكًا" منحاز هيكليًا لـiOS (لا يعني أن iOS أسوأ). فعِّل التقاط rageclick على أندرويد، وأرسِل اسم الشاشة/العنصر مع الحدث (حاليًا screen=Flutter بلا تفاصيل).</div></div>
</div>

</div>
<div class="footer">
  <div class="footer-r">8Orders · تقرير الذكاء اليومي · {ar_date} · Africa/Cairo</div>
  <div class="footer-l">PostHog #{PROJECT} · posthog-flutter · أرقام مُتحقَّق منها آليًا · سري</div>
</div>'''

    return f'<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><style>{CSS}</style></head><body>{body}</body></html>'

def build_html_tech(d):
    """Technical-team edition: keeps ONLY technical signals (errors, versions,
    rage, DNS, tracking gaps) + session recordings. All revenue/money/business
    content (orders, revenue, AOV, conversion, payments, cancellations,
    vouchers, reorder) is removed.
    NOTE: the technical issue/action rules below intentionally mirror the
    technical subset of build_html(); keep them in sync if those rules change."""
    day = d["day"]; prev = d["prev"]
    dd = dt.date.fromisoformat(day)
    ar_date = f"{dd.day} {AR_MONTHS[dd.month]} {dd.year}"
    gen_now = dt.datetime.utcnow() + dt.timedelta(hours=CAIRO_OFFSET)
    gen_date = gen_now.date()
    gen_ar = f"{gen_date.day} {AR_MONTHS[gen_date.month]} {gen_date.year}"
    gen_clock = gen_now.strftime("%H:%M")

    sess_box, featured_block = session_blocks(d, ar_date)

    # technical trends / derived values
    t_dau = trend(d["dau"], d["prev_dau"], good_up=True)
    t_install = trend(d["installs"], d["prev_installs"], good_up=True)
    t_app_opens = trend(d["app_opens"], d["prev_app_opens"], good_up=True)
    t_err = trend(d["errors"], d["prev_errors"], good_up=False)
    err_total = d["errors"]
    err_per_100 = d["errors"] / d["app_opens"] * 100 if d["app_opens"] else 0
    ios_rage = sum(v["rage"] for v in d["versions"] if "ios" in (v["os"] or "").lower() or "ipad" in (v["os"] or "").lower())
    and_rage = sum(v["rage"] for v in d["versions"] if "android" in (v["os"] or "").lower())
    top_scr, top_scr_c = (d["err_screens"][0] if d["err_screens"] else ("—", 0))
    s = d["session"]

    junk_note = ""
    if d["junk"]:
        jv = d["junk"][0]
        junk_note = (f'<div class="kc-sub" style="color:#b45309;">بدون {jv["version"]}: '
                     f'~{fmt(d["dau_clean"])} فقط — الباقي جلسات صفرية</div>')
    # DAU = interacting users only; show how many lifecycle-only sessions were excluded
    _dau_excluded = d.get("dau_all", d["dau"]) - d["dau"]
    dau_note = ('<div class="kc-sub">مستخدمون متفاعلون فقط · يستثني '
                f'~{fmt(_dau_excluded)} جلسة بلا تفاعل</div>' if _dau_excluded > 0
                else '<div class="kc-sub">مستخدمون متفاعلون فقط</div>')

    # error-by-screen rows
    scr_rows = ""
    for i, (scr, c) in enumerate(d["err_screens"]):
        cls = ' class="cr"' if i == 0 else (' class="hl"' if i in (1, 2) else "")
        pct = f'{c/err_total*100:.1f}%' if err_total else "—"
        pctcell = f'<span class="down"><strong>{pct}</strong></span>' if i == 0 else pct
        scr_rows += f'<tr{cls}><td>{scr}</td><td class="n">{fmt(c)}</td><td class="n">{pctcell}</td></tr>'

    # version rows — technical columns only (users/errors/rage; NO orders)
    ver_rows = ""
    for v in d["versions"][:6]:
        is_junk = v in d["junk"]
        cls = ' class="cr"' if is_junk else ""
        name = f'<strong>{v["version"]}</strong>' if is_junk else v["version"]
        rage_cell = fmt(v["rage"]) if v["rage"] else "0"
        ver_rows += (f'<tr{cls}><td>{name}</td><td>{v["os"]}</td><td class="n">{fmt(v["users"])}</td>'
                     f'<td class="n">{fmt(v["errors"])}</td><td class="n">{rage_cell}</td></tr>')

    # ── technical ISSUES (subset of build_html rules; no business issues) ──
    issues = []
    if d["junk"]:
        jv = d["junk"][0]
        issues.append(('cr', f'{jv["version"]}: ~{fmt(jv["users"])} جلسة يومية بصفر نشاط — traffic مشبوه يضخّم المقاييس', 'ثقة عالية', [
            ('الدليل', f'{ar_date}: {fmt(jv["total"])} حدثًا من {fmt(jv["users"])} مستخدمًا — <strong>0 مشاهدة منتج، 0 إضافة للسلة، 0 طلب</strong>.'),
            ('التأثير', f'يضخّم الـDAU (بدونه ~{fmt(d["dau_clean"])} مقابل {fmt(d["dau"])}) ويولّد {fmt(jv["errors"])} خطأ/يوم — يلوّث مقاييس الصحة.'),
            ('الإجراء', '<span class="tag t-dt">Data</span><span class="tag t-bk">Backend</span> فحص الأجهزة/الـIP وتدفق الشاشات: bots ← فلترة، إصدار معطّل ← تحديث إجباري.')]))
    if d["dns"] > 200:
        issues.append(('cr', f'فشل DNS في ids.8orders.com عبر عدة شاشات', 'ثقة عالية', [
            ('الدليل', f'{fmt(d["dns"])} خطأ "Failed host lookup / SocketException" مرتبط بـids.8orders.com.'),
            ('التأثير', 'خدمة الهوية غير متاحة ← فشل صامت في المصادقة/التخصيص ← احتكاك تقني محتمل.'),
            ('الإجراء', '<span class="tag t-bk">Backend</span> التحقق من DNS/CDN لـids.8orders.com · إضافة معالجة بديلة عند فشل الاتصال')]))
    if err_total and top_scr_c / err_total > 0.35:
        issues.append(('hi', f'أخطاء مركّزة في {top_scr} — {top_scr_c/err_total*100:.0f}% من كل الأخطاء', 'ثقة عالية', [
            ('الدليل', f'{fmt(top_scr_c)} خطأ على {top_scr} · أبرز رسالة: {d["top_err"][0]} ({fmt(d["top_err"][1])}).'),
            ('التأثير', 'يغمر PostHog ويخفي الأخطاء الحقيقية.'),
            ('الإجراء', '<span class="tag t-mob">Mobile</span> تحديد السبب · إضافة platform guard أو try/catch')]))
    if d["rage"] > 100 and and_rage == 0:
        issues.append(('hi', 'كل الـRage Clicks على iOS — Android يُظهر صفرًا', 'ثقة متوسطة', [
            ('الدليل', f'{fmt(ios_rage)} Rage Click من iOS · Android: صفر تمامًا.'),
            ('تحفظ', 'قد تكون مشكلة Tracking على Android لا مشكلة UX على iOS. يجب التحقق أولًا.'),
            ('الإجراء', f'<span class="tag t-mob">Mobile</span> التحقق من دعم Rage Click على Flutter Android' + (f' · أفضل جلسة: <span style="direction:ltr;display:inline-block;font-size:7.5pt;">{s["sid"]}</span>' if s else ''))]))

    issues_html = ""
    for sev, title, conf, rows in issues:
        cf = 'cf-h' if 'عالية' in conf else 'cf-m'
        sev_ar = {'cr':'حرج','hi':'عالي','md':'متوسط'}[sev]
        rows_html = "".join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in rows)
        issues_html += f'''
  <div class="issue {sev}">
    <div class="issue-top"><div class="issue-title">{title}</div>
      <div class="issue-badges"><span class="sev {sev}">{sev_ar}</span><span class="sev {cf}">{conf}</span></div>
      <div class="iclear"></div></div>
    <div class="issue-body"><table class="issue-row-grid">{rows_html}</table></div>
  </div>'''

    # ── technical ACTIONS (subset of build_html rules; no business actions) ──
    actions = []
    if d["junk"]:
        jv = d["junk"][0]
        actions.append(('p0', f'التحقق من طبيعة traffic الإصدار {jv["version"]}',
            f'~{fmt(jv["users"])} جلسة/يوم بصفر تصفّح/سلة/طلب و{fmt(jv["total"])} حدثًا تضخّم DAU والأخطاء. افحص الأجهزة/الـIP: bots ← فلترة؛ إصدار معطّل ← تحديث إجباري.',
            '<span class="tag t-dt">Data</span><span class="tag t-bk">Backend</span>'))
    if d["dns"] > 200:
        actions.append(('p0', 'فحص DNS وCDN لـ ids.8orders.com وإضافة fallback',
            f'{fmt(d["dns"])} فشل اتصال عبر عدة شاشات. خدمة الهوية غير متاحة قد تسبب فشلًا صامتًا في تسجيل الدخول.',
            '<span class="tag t-bk">Backend</span>'))
    if err_total and top_scr_c / err_total > 0.35:
        actions.append(('p1', f'إصلاح الأخطاء في {top_scr}',
            f'{fmt(top_scr_c)} خطأ/يوم = {top_scr_c/err_total*100:.0f}% من كل الأخطاء. يغمر PostHog ويخفي المشاكل الحقيقية.',
            '<span class="tag t-mob">Mobile</span>'))
    actions_html = ""
    for p, title, why, tags in actions:
        actions_html += f'''
  <div class="action {p}"><div class="action-num">{p.upper()}</div>
    <div class="action-body"><div class="action-title">{title}</div>
    <div class="action-why">{why}</div><div style="margin-top:5px;">{tags}</div></div></div>'''
    if not actions_html:
        actions_html = '<div class="note">لا توجد إجراءات تقنية عاجلة اليوم وفق القواعد المحددة.</div>'

    tech_alert = bool(d["junk"]) or d["dns"] > 200 or (err_total and top_scr_c/err_total > 0.35) or d["rage"] > 100
    tech_health = "تحتاج تدخّل" if tech_alert else "مستقرة"

    junk_kpi = (f'<td class="kc alert"><div class="kc-lbl">جلسات Junk ({d["junk"][0]["version"]})</div>'
                f'<div class="kc-val">{fmt(d["junk"][0]["users"])}</div>'
                f'<span class="kc-chg down">صفر نشاط</span><div class="kc-sub">{fmt(d["junk"][0]["total"])} حدثًا</div></td>'
                if d["junk"] else
                f'<td class="kc"><div class="kc-lbl">أبرز رسالة خطأ</div><div class="kc-val" style="font-size:11pt;">{fmt(d["top_err"][1])}</div>'
                f'<div class="kc-sub">{d["top_err"][0]}</div></td>')

    # ── Tech section: barriers for users who added to cart but did not order ──
    _cp = d["cart_problems"]; _a = d["acq"]
    def _barrier_rows(pairs, first_cls):
        out = ""
        for i, (label, c) in enumerate(pairs):
            cls = f' class="{first_cls}"' if i == 0 else ""
            out += f'<tr{cls}><td>{label}</td><td class="n">{fmt(c)}</td></tr>'
        return out or '<tr><td>—</td><td class="n">0</td></tr>'
    _msg_rows = _barrier_rows(_cp["messages"], "cr")
    _scr_rows = _barrier_rows(_cp["screens"], "hl")
    barriers_section = f'''
<div class="section avoid">
  <div class="section-hdr"><span class="sec-num">06</span><span class="sec-title">عوائق إتمام الطلب (أضافوا للسلة ولم يطلبوا)</span></div>
  <div class="note">في يوم التقرير: <strong>{fmt(_a["cart_no"])}</strong> مستخدمًا أضافوا للسلة ولم يُكملوا الطلب. عندهم <strong>{fmt(_cp["err_events"])}</strong> خطأ على <strong>{fmt(_cp["err_users"])}</strong> مستخدمًا، و<strong>{fmt(_cp["rage"])}</strong> نقرة غضب (Rage).</div>
  <table class="tc"><tr>
    <td style="width:58%;"><div class="box-t">أبرز رسائل الخطأ لغير المُكمِّلين</div>
      <table class="dt"><thead><tr><th>الرسالة</th><th class="n">عدد</th></tr></thead><tbody>{_msg_rows}</tbody></table></td>
    <td style="width:42%;"><div class="box-t">أكثر الشاشات تعثّرًا</div>
      <table class="dt"><thead><tr><th>الشاشة</th><th class="n">عدد</th></tr></thead><tbody>{_scr_rows}</tbody></table></td>
  </tr></table>
  <div class="data-note" style="margin-top:10px;">العيّنة = مستخدمو هذا اليوم الذين سجّلوا add_to_cart بلا order_placed. أعمق خطوة شراء متتبَّعة هي add_to_cart (لا يوجد checkout_started).</div>
</div>
'''

    # ── Tech section: widespread CAUGHT, non-fatal code errors (NOISE class) ──
    _cn = d.get("code_noise") or []
    if _cn:
        _cn_rows = "".join(
            f'<tr><td>{c["label"]}</td><td class="n">{fmt(c["count"])}</td>'
            f'<td class="n">{fmt(c["users"])}</td><td>{c["screen"]} ({fmt(c["screen_c"])})</td></tr>'
            for c in _cn)
        code_noise_section = f'''
<div class="section avoid">
  <div class="section-hdr"><span class="sec-num">07</span><span class="sec-title">ضوضاء كود غير قاتلة (مُلتقَطة وواسعة الانتشار)</span></div>
  <div class="note">أخطاء من كودنا تُسجَّل لكنها <strong>لا توقف</strong> تجربة المستخدم (مُلتقَطة/غير قاتلة) — اليوم أكمل مئات الطلبات بينما تُطلَق هذه على غالبية الجلسات. <strong>لا تُحتسب</strong> في تقييم الجلسات الحرجة، لكنها تُضخّم عدّادات الأخطاء وتُخفي المشاكل الحقيقية. يُنصح بكتمها/إصلاحها لتنظيف الـtelemetry.</div>
  <table class="dt"><thead><tr><th>الخطأ (من كودنا)</th><th class="n">عدد/يوم</th><th class="n">مستخدمون</th><th>أبرز شاشة (عدد)</th></tr></thead>
  <tbody>{_cn_rows}</tbody></table>
</div>
'''
    else:
        code_noise_section = ""

    body = f'''
<div class="cover">
  <div class="cover-top">
    <div class="cover-logo">8<span>Orders</span></div>
    <div class="cover-meta" style="direction:ltr; text-align:left;">
      Daily Technical Quality Report<br>
      <strong style="color:#fff">{dd.strftime("%a, %d %B %Y")}</strong><br>
      Business day 08:00→04:00 · Africa/Cairo<br>
      PostHog #{PROJECT} · Generated {gen_date.strftime("%d %b %Y")} {gen_clock} Cairo
    </div>
    <div class="cover-clear"></div>
  </div>
  <div class="cover-title">تقرير الجودة التقنية اليومي</div>
  <div class="cover-sub">أخطاء · إصدارات · جلسات — نسخة الفريق التقني</div>
  <div class="health-pill">⚠ الحالة التقنية: {tech_health}</div>
  {sess_box}
</div>

<div class="body">

<div class="section">
  <div class="section-hdr"><span class="sec-num">01</span><span class="sec-title">مؤشرات الجودة التقنية</span></div>
  <div class="verify-note">✓ <strong>كل الأرقام مسحوبة ومتحقَّق منها آليًا من PostHog عند التوليد ({gen_ar}).</strong></div>
  <div class="note"><strong>السياق:</strong> يوم العمل من 8 صباحًا حتى 2 صباحًا اليوم التالي (نافذة 18 ساعة، توقيت القاهرة). كل المقارنات مقابل يوم العمل السابق ({dt.date.fromisoformat(prev).day} {AR_MONTHS[dt.date.fromisoformat(prev).month]}).</div>
  <table class="kpi-grid">
    <tr>
      <td class="kc"><div class="kc-lbl">المستخدمون اليوميون (DAU)</div><div class="kc-val">{fmt(d["dau"])}</div>
        {chg_span(t_dau, "مقارنة بالأمس")}{junk_note}{dau_note}</td>
      <td class="kc"><div class="kc-lbl">فتحات التطبيق</div><div class="kc-val">{fmt(d["app_opens"])}</div>
        {chg_span(t_app_opens, "مقارنة بالأمس")}<div class="kc-sub">حدث Application Opened</div></td>
      <td class="kc {'good' if t_install['cls']=='up' else ''}"><div class="kc-lbl">تثبيتات جديدة</div><div class="kc-val">{fmt(d["installs"])}</div>
        {chg_span(t_install, "مقارنة بالأمس")}<div class="kc-sub">Application Installed</div></td>
      <td class="kc {'good' if t_err['cls']=='up' else 'alert'}"><div class="kc-lbl">أخطاء التطبيق</div><div class="kc-val">{fmt(d["errors"])}</div>
        {chg_span(t_err)}<div class="kc-sub">~{err_per_100:.0f} خطأ لكل 100 فتح</div></td>
    </tr>
    <tr>
      <td class="kc alert"><div class="kc-lbl">Rage Clicks</div><div class="kc-val">{fmt(d["rage"])}</div>
        <span class="kc-chg down">{'100% من iOS' if and_rage==0 else 'موزّعة'}</span><div class="kc-sub">iOS مقابل Android</div></td>
      <td class="kc {'alert' if d['dns']>200 else 'warn'}"><div class="kc-lbl">أخطاء DNS</div><div class="kc-val">{fmt(d["dns"])}</div>
        <span class="kc-chg down">ids.8orders.com</span><div class="kc-sub">Failed host lookup</div></td>
      <td class="kc warn"><div class="kc-lbl">بحث بلا نتائج</div><div class="kc-val">{fmt(d["search_no"])}</div>
        <span class="kc-chg flat">search_no_results</span><div class="kc-sub">عدد صغير — يُراقَب</div></td>
      {junk_kpi}
    </tr>
  </table>
</div>

<div class="pb"></div>

<div class="section">
  <div class="section-hdr"><span class="sec-num">02</span><span class="sec-title">جودة التطبيق والأخطاء والإصدارات</span></div>
  <table class="tc"><tr>
    <td style="width:50%;"><div class="box-t">الأخطاء حسب الشاشة · {ar_date} (المجموع: {fmt(err_total)})</div>
      <table class="dt"><thead><tr><th>الشاشة</th><th class="n">أخطاء</th><th class="n">من الإجمالي</th></tr></thead>
      <tbody>{scr_rows}</tbody></table></td>
    <td style="width:50%;"><div class="box-t">أداء الإصدارات · {ar_date}</div>
      <table class="dt"><thead><tr><th>الإصدار</th><th>المنصة</th><th class="n">المستخدمون</th><th class="n">الأخطاء</th><th class="n">Rage</th></tr></thead>
      <tbody>{ver_rows}</tbody></table>
      {("<div style='margin-top:8px; background:#fef2f2; border:1px solid rgba(220,38,38,0.3); border-radius:6px; padding:8px 10px; font-size:8pt; color:#991b1b; line-height:1.6;'><strong>⚠ الإصدار " + d["junk"][0]["version"] + " — ~" + fmt(d["junk"][0]["users"]) + " جلسة و" + fmt(d["junk"][0]["total"]) + " حدثًا بصفر تصفّح/سلة/طلب.</strong><br>نمط غير بشري أو إصدار معطّل. يحتاج تحقيقًا، وليس مجرد تحديث إجباري.</div>") if d["junk"] else ""}
      <div style="margin-top:8px; font-size:8pt; color:#334155; line-height:1.7;"><strong>أبرز رسالة خطأ:</strong> {d["top_err"][0]} ({fmt(d["top_err"][1])}).</div></td>
  </tr></table>
</div>

<div class="section">
  <div class="section-hdr"><span class="sec-num">03</span><span class="sec-title">المشاكل التقنية والشذوذات</span><span class="sec-badge cr" style="float:left;">القسم الحرج</span></div>
  {issues_html if issues_html else '<div class="note">لا توجد شذوذات تقنية حرجة اليوم وفق القواعد المحددة.</div>'}
</div>

<div class="pb"></div>

<div class="section">
  <div class="section-hdr"><span class="sec-num">04</span><span class="sec-title">تسجيلات الجلسات</span><span class="sec-badge cr" style="float:left;">مهم جدًا</span></div>
  {featured_block}
  <div style="font-size:7.5pt; color:#64748b; margin-top:4px;">ملاحظة: مدة النشاط من API؛ قد يعرض المشغّل مدة أقصر بعد ضغط فترات الخمول.</div>
</div>

<div class="section">
  <div class="section-hdr"><span class="sec-num">05</span><span class="sec-title">الإجراءات التقنية المطلوبة</span></div>
  {actions_html}
</div>

{barriers_section}
{code_noise_section}
<div class="section avoid">
  <div class="section-hdr"><span class="sec-num">08</span><span class="sec-title">ثغرات التتبع التقنية</span></div>
  <div class="gap"><div class="gap-title"><span class="p0-t">P0</span> &nbsp; checkout_started غير مسجَّل</div><div class="gap-body">لا يمكن تتبّع خطوات الـCheckout تقنيًا. أضف الحدث مع cart_value، delivery_fee، vertical.</div></div>
  <div class="gap"><div class="gap-title"><span class="p0-t">P0</span> &nbsp; payment_failed غير مسجَّل</div><div class="gap-body">لا يمكن رصد فشل الدفع تقنيًا. أضف: payment_method، failure_reason، error_code.</div></div>
  <div class="gap"><div class="gap-title"><span class="p1-t">P1</span> &nbsp; منطقة التوصيل غير مُرسَلة كخاصية</div><div class="gap-body">أضف area_id/area_name وwithin_coverage على account_created وSelect Area وaddress_created لقياس التغطية مباشرةً بدل تقدير الـGeoIP.</div></div>
  <div class="gap"><div class="gap-title"><span class="p1-t">P1</span> &nbsp; المدينة/المنطقة غير موجودة على order_placed</div><div class="gap-body">store_id فارغ غالبًا ولا city/zone. أضف: city، zone_id، store_id.</div></div>
  <div class="gap"><div class="gap-title"><span class="p1-t">P1</span> &nbsp; سبب الإلغاء وكلمة البحث غير مسجَّلين</div><div class="gap-body">أضف reason على الإلغاء، وsearch_query وresult_count على البحث.</div></div>
  <div class="gap"><div class="gap-title"><span class="p1-t">P1</span> &nbsp; rageclick على iOS فقط — أندرويد صفر</div><div class="gap-body">الـSDK يلتقط rageclick على iOS فقط (iOS 21k+ مقابل 0 على أندرويد/30 يوم)، فأي ترتيب احتكاك معتمد على rage منحاز لـiOS. فعِّل rageclick على أندرويد وأرسِل screen/element (حاليًا screen=Flutter).</div></div>
</div>

</div>
<div class="footer">
  <div class="footer-r">8Orders · تقرير الجودة التقنية · {ar_date} · Africa/Cairo</div>
  <div class="footer-l">PostHog #{PROJECT} · posthog-flutter · أرقام مُتحقَّق منها آليًا · سري</div>
</div>'''

    return f'<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><style>{CSS}</style></head><body>{body}</body></html>'

# helper used inside issues
def chg_arrow(t): return f'{t["arrow"]}{t["pct"]}'
def t_dau_cart(d):
    return trend(d["conv_series"][d["day"]]["cart"], d["conv_series"][d["prev"]]["cart"])

# ──────────────── acquisition / activation / coverage ────────────────
# NOTE on the order event: the app switched its success event from the legacy
# "Purchase" to "order_placed" around 2026-06-15. "order_placed" is the current
# source of truth for orders; for a correct *lifetime* "has this person ever
# ordered" signal we must consider BOTH events (Purchase carries the older
# history). checkout_started is still not instrumented, so the deepest reliably
# tracked purchase-intent step is add_to_cart.
def _ever_ordered_subq(end_ts):
    return (f"(SELECT person_id FROM events WHERE event IN ('order_placed','Purchase') "
            f"AND timestamp < '{end_ts}')")

def _scalar(q):
    r = hogql(q)
    return int((r[0][0] if r and r[0] and r[0][0] is not None else 0))

def acquisition(day):
    """New-user funnel + non-conversion counts for the business `day`.
    - cart_no       : reached add_to_cart but placed NO order that day (tried to order, didn't).
    - new_browse_no : users who NEVER ordered (lifetime) who browsed but didn't order that day.
    - new_cart_no   : subset of the above that reached add_to_cart (highest-intent lost new users).
    - acc_*         : same-day activation of accounts created that day."""
    end = f"{(dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()} {BIZ_END}"
    ever = _ever_ordered_subq(end)
    base = hogql(f"""SELECT
        uniqIf(person_id, event IN ('product_viewed','store_opened','add_to_cart')),
        uniqIf(person_id, event='add_to_cart'),
        uniqIf(person_id, event='order_placed')
        FROM events WHERE {D(day)}""")[0]
    browsers, cart, ordered = (int(x or 0) for x in base)
    cart_no = _scalar(f"""SELECT uniq(person_id) FROM events WHERE {D(day)} AND event='add_to_cart'
        AND person_id NOT IN (SELECT person_id FROM events WHERE {D(day)} AND event='order_placed')""")
    new_browse_no = _scalar(f"""SELECT uniq(person_id) FROM events WHERE {D(day)}
        AND event IN ('product_viewed','store_opened','add_to_cart') AND person_id NOT IN {ever}""")
    new_cart_no = _scalar(f"""SELECT uniq(person_id) FROM events WHERE {D(day)} AND event='add_to_cart'
        AND person_id NOT IN {ever}""")
    act = hogql(f"""WITH reg AS (SELECT DISTINCT person_id FROM events WHERE {D(day)} AND event='account_created')
        SELECT (SELECT count() FROM reg),
          uniqIf(person_id, event IN ('product_viewed','store_opened','add_to_cart')),
          uniqIf(person_id, event='add_to_cart'),
          uniqIf(person_id, event='order_placed'),
          uniqIf(person_id, event='address_created')
        FROM events WHERE {D(day)} AND person_id IN (SELECT person_id FROM reg)""")[0]
    acc, a_browse, a_cart, a_order, a_addr = (int(x or 0) for x in act)
    return dict(browsers=browsers, cart=cart, ordered=ordered, cart_no=cart_no,
                new_browse_no=new_browse_no, new_cart_no=new_cart_no,
                acc=acc, acc_browse=a_browse, acc_cart=a_cart, acc_order=a_order, acc_addr=a_addr)

def coverage(day, days=7):
    """Delivery-coverage proxy over a trailing `days` window, WITHOUT GeoIP.
    GeoIP is NOT usable here: Egyptian ISP IP ranges register centrally, so IP
    geolocation collapses users from across the country onto 'Cairo' (a city the
    app does not even serve). The app currently serves only Hurghada & Asyut.
    Since the app does not send the selected delivery area as an event property,
    we use a behavioural proxy: a new user who creates a delivery address but
    never sees a store (no store_opened / add_to_cart) is very likely OUTSIDE the
    delivery footprint (the store list came back empty for their address)."""
    start = (dt.date.fromisoformat(day) - dt.timedelta(days=days - 1)).isoformat()
    nxt = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()
    # Project tz is Africa/Cairo: express the trailing window in Cairo wall-clock
    # (start 08:00 of the first day -> 04:00 after the last business day).
    w = f"timestamp >= '{start} {BIZ_START}' AND timestamp < '{nxt} {BIZ_END}'"
    inst = hogql(f"""WITH inst AS (SELECT DISTINCT person_id FROM events WHERE {w} AND event='{EV['install']}')
        SELECT (SELECT count() FROM inst),
          uniqIf(person_id, event='account_created'),
          uniqIf(person_id, event IN ('store_opened','add_to_cart')),
          uniqIf(person_id, event='order_placed')
        FROM events WHERE {w} AND person_id IN (SELECT person_id FROM inst)""")[0]
    installed, i_reg, i_saw, i_ord = (int(x or 0) for x in inst)
    acc = hogql(f"""WITH reg AS (SELECT DISTINCT person_id FROM events WHERE {w} AND event='account_created')
        SELECT (SELECT count() FROM reg),
          uniqIf(person_id, event='address_created'),
          uniqIf(person_id, event IN ('store_opened','add_to_cart')),
          uniqIf(person_id, event='order_placed')
        FROM events WHERE {w} AND person_id IN (SELECT person_id FROM reg)""")[0]
    a_acc, a_addr, a_saw, a_ord = (int(x or 0) for x in acc)
    addr_no_store = _scalar(f"""SELECT uniq(person_id) FROM events WHERE {w} AND event='address_created'
        AND person_id IN (SELECT person_id FROM events WHERE {w} AND event='account_created')
        AND person_id NOT IN (SELECT person_id FROM events WHERE {w} AND event IN ('store_opened','add_to_cart'))""")
    return dict(window_days=days, served="الغردقة وأسيوط",
                installed=installed, inst_reg=i_reg, inst_saw=i_saw, inst_ord=i_ord,
                acc=a_acc, made_address=a_addr, saw_store=a_saw, ordered=a_ord,
                addr_no_store=addr_no_store)

def cart_problems(day):
    """Errors / friction for users who added to cart but did NOT order (business day)."""
    inn = f"person_id IN (SELECT person_id FROM events WHERE {D(day)} AND event='add_to_cart')"
    notord = f"person_id NOT IN (SELECT person_id FROM events WHERE {D(day)} AND event='order_placed')"
    tot = hogql(f"""SELECT count(), uniq(person_id) FROM events
        WHERE {D(day)} AND event='{EV['error']}' AND {inn} AND {notord}""")[0]
    msgs = hogql(f"""SELECT properties.error_message, count() FROM events
        WHERE {D(day)} AND event='{EV['error']}' AND {inn} AND {notord}
        GROUP BY 1 ORDER BY 2 DESC LIMIT 5""")
    screens = hogql(f"""SELECT properties.$screen_name, count() FROM events
        WHERE {D(day)} AND event='{EV['error']}' AND {inn} AND {notord}
        GROUP BY 1 ORDER BY 2 DESC LIMIT 5""")
    rage = _scalar(f"""SELECT count() FROM events WHERE {D(day)} AND event='{EV['rage']}' AND {inn} AND {notord}""")
    return dict(err_events=int(tot[0] or 0), err_users=int(tot[1] or 0),
                messages=[(m or "—", int(c)) for m, c in msgs],
                screens=[(s or "—", int(c)) for s, c in screens], rage=rage)

# ───────────────────────── orchestration ─────────────────────────
def collect(day):
    prev = (dt.date.fromisoformat(day) - dt.timedelta(days=1)).isoformat()
    days4 = [(dt.date.fromisoformat(day) - dt.timedelta(days=i)).isoformat() for i in range(3, -1, -1)]
    base_days = days4[:-1]  # 3 prior days

    ec = event_counts(day); pc = event_counts(prev)
    rev = revenue(day); prev_rev = revenue(prev)
    pay, pay_total = payment_breakdown(day)
    series = conversion_series(days4)
    versions, junk = version_table(day)
    dau_all, dau_real = dau(day)
    prev_dau_all, prev_dau_real = dau(prev)
    sessions = featured_sessions(day)

    conv_today = series[day]["conv"]
    conv_base = sum(series[b]["conv"] for b in base_days) / len(base_days)
    cart_today = series[day]["cart"]
    expected = round(cart_today * conv_base / 100)
    lost_orders = max(0, expected - rev["orders"])
    lost_rev = round(lost_orders * rev["aov"])

    return dict(
        day=day, prev=prev,
        rev=rev, prev_rev=prev_rev, payment=pay, pay_total=pay_total,
        conv_series=series, conv_today=conv_today, conv_baseline=conv_base,
        expected_orders=expected, lost_orders=lost_orders, lost_rev=lost_rev,
        versions=versions, junk=junk, dau=dau_real, dau_clean=dau_real,
        dau_all=dau_all, prev_dau=prev_dau_real,
        app_opens=ec.get(EV["app_open"], 0), prev_app_opens=pc.get(EV["app_open"], 0),
        errors=ec.get(EV["error"], 0), prev_errors=pc.get(EV["error"], 0),
        rage=ec.get(EV["rage"], 0),
        installs=ec.get(EV["install"], 0), prev_installs=pc.get(EV["install"], 0),
        accounts=ec.get(EV["account"], 0),
        cancel=ec.get(EV["cancel"], 0), prev_cancel=pc.get(EV["cancel"], 0),
        reorder=ec.get(EV["reorder"], 0), prev_reorder=pc.get(EV["reorder"], 0),
        voucher=ec.get(EV["voucher"], 0), prev_voucher=pc.get(EV["voucher"], 0),
        rating=ec.get(EV["rating"], 0), prev_rating=pc.get(EV["rating"], 0),
        support=ec.get(EV["support"], 0), prev_support=pc.get(EV["support"], 0),
        search_no=ec.get(EV["search_no"], 0),
        err_screens=errors_by_screen(day), dns=dns_error_count(day), top_err=top_error_message(day),
        sessions=sessions, session=(sessions[0] if sessions else None),
        acq=acquisition(day), coverage=coverage(day), cart_problems=cart_problems(day),
        code_noise=code_noise(day),
    )

def sanity_print(d):
    print("\n================ SANITY CHECK ================")
    print(f"Day: {d['day']}  (vs {d['prev']})")
    print(f"DAU (real/interacting): {d['dau']:,}  (all users incl. lifecycle-only: {d['dau_all']:,}; "
          f"excluded {d['dau_all']-d['dau']:,})  | app opens {d['app_opens']:,}")
    print(f"Orders: {d['rev']['orders']:,}  Revenue: {d['rev']['revenue']:,.0f}  AOV: {d['rev']['aov']:,.0f}")
    print(f"Conversion today {d['conv_today']:.1f}% vs baseline {d['conv_baseline']:.1f}%  -> lost ~{d['lost_orders']} orders / {d['lost_rev']:,} EGP")
    print(f"Errors: {d['errors']:,}  Rage: {d['rage']:,}  DNS errs: {d['dns']:,}")
    print(f"Cancel {d['cancel']} | Reorder {d['reorder']} | Voucher {d['voucher']} | Support {d['support']}")
    a = d['acq']
    act_pct = (a['acc_order'] / a['acc'] * 100) if a['acc'] else 0
    print(f"Acquisition: new accounts {a['acc']} -> ordered same-day {a['acc_order']} ({act_pct:.0f}%)  | "
          f"tried-to-order(cart, no order) {a['cart_no']}  | new-never-ordered browsed-no-order {a['new_browse_no']} (cart {a['new_cart_no']})")
    cov = d['coverage']
    inst_pct = (cov['inst_ord'] / cov['installed'] * 100) if cov['installed'] else 0
    ono_pct = (cov['addr_no_store'] / cov['acc'] * 100) if cov['acc'] else 0
    print(f"Coverage (no GeoIP, served={cov['served']}, {cov['window_days']}d): installed {cov['installed']} -> registered {cov['inst_reg']} -> saw store {cov['inst_saw']} -> ordered {cov['inst_ord']} ({inst_pct:.0f}%)")
    print(f"  out-of-coverage proxy: {cov['addr_no_store']} new accounts ({ono_pct:.0f}%) created an address but saw NO store")
    cp = d['cart_problems']
    top_msg = cp['messages'][0] if cp['messages'] else ('—', 0)
    print(f"Cart-no-order problems: {cp['err_events']} errors / {cp['err_users']} users, rage {cp['rage']}; top: {str(top_msg[0])[:60]} ({top_msg[1]})")
    print(f"Junk versions: {[(v['version'], v['users'], v['total']) for v in d['junk']]}")
    cn = d.get('code_noise') or []
    if cn:
        print("Caught non-fatal code noise (excluded from scoring): "
              + " | ".join(f"{c['label'].split('(')[0].strip()} {c['count']} ({c['users']}u, {c['screen']})" for c in cn))
    sess = d.get('sessions') or []
    if sess:
        print(f"Top {len(sess)} critical sessions (zero-order + REAL friction; net/noise excluded from score):")
        for i, s in enumerate(sess, 1):
            print(f"  #{i} {s['sid']}  score {s['score']} (rage {s['rage']} real_err {s['err']}"
                  f" | excl: net {s.get('net_err',0)} noise {s.get('noise_err',0)})  cart {s['cart']} clicks {s['clicks']}  {s['os']} v{s['version']}")
    else:
        print("Critical sessions: NONE matched (no genuine product friction after excluding network + caught noise)")
    print("==============================================\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="Business-day start date YYYY-MM-DD (default: yesterday's business day)")
    ap.add_argument("--out", help="Output PDF path for the business edition (default: 'PostHog Report DDMonYYYY.pdf')")
    ap.add_argument("--outdir", default=".", help="Directory for the default-named PDF(s)")
    ap.add_argument("--audience", choices=["business", "tech", "both"], default="both",
                    help="Which edition(s) to produce: business (as-is), tech (technical-only), or both (default)")
    ap.add_argument("--html", help="also write raw HTML of the business edition to this path")
    ap.add_argument("--push-ado", action="store_true",
                    help="also file the day's flagged critical sessions as Issue work items "
                         "on the ADO Support Team board (classified technical/UX, deduped)")
    ap.add_argument("--ado-dry-run", action="store_true",
                    help="with --push-ado: print what would be created without calling ADO")
    ap.add_argument("--ado-max", type=int, default=5,
                    help="max number of flagged sessions to file as ADO tickets per run (default 5)")
    ap.add_argument("--no-discord", action="store_true",
                    help="skip sending the generated PDF(s) as a Discord DM")
    args = ap.parse_args()

    if not os.environ.get("POSTHOG_API_KEY"):
        sys.exit("ERROR: POSTHOG_API_KEY not set")

    if args.date:
        day = args.date
    else:
        # Routine runs ~07:00 Cairo; the business day that just ended started "yesterday".
        # (Works for any run time from Cairo 04:00 to midnight — picks the same day.)
        now_cairo = dt.datetime.utcnow() + dt.timedelta(hours=CAIRO_OFFSET)
        day = (now_cairo.date() - dt.timedelta(days=1)).isoformat()

    dd = dt.date.fromisoformat(day)
    biz_out = args.out or os.path.join(args.outdir, f"PostHog Report {dd.strftime('%d%b%Y')}.pdf")
    tech_out = os.path.join(os.path.dirname(biz_out) or ".",
                            f"PostHog Report {dd.strftime('%d%b%Y')} - Tech.pdf")

    print(f"Generating 8Orders report for BUSINESS DAY {day} (Cairo {BIZ_START[:5]} → next-day {BIZ_END[:5]}) ...")
    d = collect(day)
    sanity_print(d)
    from weasyprint import HTML

    biz_written = False
    if args.audience in ("business", "both"):
        html = build_html(d)
        if args.html:
            open(args.html, "w", encoding="utf-8").write(html)
        HTML(string=html).write_pdf(biz_out, presentational_hints=True, optimize_images=True)
        print(f"PDF written (business): {biz_out}")
        biz_written = True

    if args.audience in ("tech", "both"):
        html_tech = build_html_tech(d)
        HTML(string=html_tech).write_pdf(tech_out, presentational_hints=True, optimize_images=True)
        print(f"PDF written (tech): {tech_out}")

    if args.push_ado:
        import ado_client
        ado_sessions = featured_sessions(day, n=args.ado_max)
        summaries = fetch_session_summaries([s["sid"] for s in ado_sessions])
        print("\n============== SESSION SUMMARIES (PostHog AI) ==============")
        for s in ado_sessions:
            summ = summaries.get(s["sid"])
            s["ai_summary"] = summ
            if summ is None:
                print(f"  {s['sid']}: unavailable -> falling back to basic (err/rage) heuristic")
            else:
                outcome = summ.get("session_outcome") or {}
                print(f"  {s['sid']}: fetched, success={outcome.get('success')} — "
                      f"{str(outcome.get('description'))[:90]}")
        print("==============================================================\n")
        ado_client.push_sessions(ado_sessions, day, dry_run=args.ado_dry_run)

    if not args.no_discord:
        # Best-effort: delivery failure here must never fail the routine run —
        # the PDF is already written either way. Mahmoud gets the business
        # edition only (he doesn't need the tech-only edition) — if this run
        # was started with --audience tech, there's nothing to send.
        if biz_written:
            try:
                import discord_delivery
                discord_delivery.send_report([biz_out], message=f"تقرير PostHog اليومي — {day} 📊")
            except Exception as e:
                print(f"DISCORD: delivery step failed (non-fatal): {e}")
        else:
            print("DISCORD: skipped — no business-edition PDF in this run (--audience tech)")

if __name__ == "__main__":
    main()
