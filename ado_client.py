#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Push 8Orders PostHog shift-issues (flagged critical sessions) to the Azure
DevOps "Support Team" board as `Issue` work items.

Classification is driven by PostHog's real AI session-recording summary,
fetched straight over REST by the report generator (`fetch_session_summaries`
in `8orders_report_generator.py`, called before `push_sessions` below) —
NO MCP server needed, this works in the cloud routine. For each flagged
session we (a) drop false positives where `session_outcome.success = true`
(the session actually completed fine despite the raw rage-click/error
signal that flagged it), (b) classify TECHNICAL vs UX from the real
per-event `exception` flag (`blocking` -> High severity technical,
`non-blocking` -> Medium technical, no exception at all but
confusion/abandonment signals -> UX), and (c) write a title from the AI's
own name for the failing segment plus a brief built from its own
segment/outcome descriptions — see `classify_from_summary()` and
`_brief()` below.

Fallback: if the summary could not be fetched/generated for a session
(network hiccup, PostHog outage, no recording data), we fall back to the
old crude heuristic in `classify_session_basic()` — genuine app error
present -> technical, else UX — so a PostHog hiccup never blocks the run.
That heuristic has no false-positive filtering, which is the known root
cause of previously mistagged "ux-enhancement" tickets that turned out to
have nothing to do with UX.

Every ticket gets the mandatory `posthog` tag plus a `posthog-session-<id>`
tag used purely for same-day dedup, so the same session is never filed twice
across daily runs.

Swimlane caveat (verified live against this org on 2026-06-24): `System.
BoardLane` is locked ReadOnly at the field-definition level for the `Issue`
work item type in this process — even `bypassRules=true` is rejected. So the
card is filed with the category as a TAG only; an ADO admin needs to relax
that field rule (Org Settings -> Process -> Issue -> Layout/Rules) before
this script can also drop the card straight into the right lane. Once that's
done, `_set_board_lane()` below (already wired in, just currently a no-op
on failure) will start working with no other change needed.

Two more fields turned out to be `alwaysRequired` for `Issue` in this
process and aren't part of the original spec — discovered the same way, by
inspecting existing Support Team tickets: `myagile.Customer` ("8Orders") and
`Custom.Application` ("App - Customer", the customer-facing app PostHog
instruments). Hardcoded since every PostHog-sourced issue is the same app/customer.

Env (read from a `.env` file alongside this script if present, else the
process environment):
  AZURE_DEVOPS_PAT   personal access token, scope: Work Items (Read & Write)
  ADO_ORG            org name ("hadafsolutions") OR full URL
                      ("https://hadafsolutions.visualstudio.com") — both accepted
  ADO_PROJECT        default "0_Projects_Team"
  ADO_AREA_PATH      default "0_Projects_Team\\Support Team"

Ticket destination is ALWAYS Project=0_Projects_Team / Support Team, regardless
of any other taskboard URL (e.g. a Mars Team sprint board) seen elsewhere.
"""
import os, sys, base64, datetime as dt, requests

def _load_dotenv():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

_load_dotenv()

def _org_base_url(org):
    return org if "://" in org else f"https://{org}.visualstudio.com"

ADO_ORG = os.environ.get("ADO_ORG", "hadafsolutions")
ADO_PROJECT = os.environ.get("ADO_PROJECT") or os.environ.get("AZURE_DEVOPS_DEFAULT_PROJECT", "0_Projects_Team")
ADO_AREA_PATH = os.environ.get("ADO_AREA_PATH", r"0_Projects_Team\Support Team")
ADO_CUSTOMER = os.environ.get("ADO_CUSTOMER", "8Orders")
ADO_APPLICATION = os.environ.get("ADO_APPLICATION", "App - Customer")
ADO_ORG_BASE = _org_base_url(ADO_ORG)
ADO_BASE = f"{ADO_ORG_BASE}/{ADO_PROJECT}/_apis"
ADO_API_VERSION = "7.1"
# نقطة 4 (F3): النوع من مصدر الحقيقة الواحد — "Issue" هو نوع مسار PostHog اليومي
# على بورد السابورت (عن قصد، مختلف عن "Customer Issue" بتاع مسار المحادثات).
try:
    import ado_fields
    WORK_ITEM_TYPE = ado_fields.TYPE_POSTHOG_ISSUE
except Exception:  # لو الروتين اتشغل من مكان مفيهوش الموديول — نفس القيمة يدوي
    WORK_ITEM_TYPE = "Issue"


def _auth_headers():
    pat = os.environ.get("AZURE_DEVOPS_PAT")
    if not pat:
        sys.exit("ERROR: AZURE_DEVOPS_PAT not set")
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def classify_session_basic(s):
    """FALLBACK ONLY (no AI summary available): technical (genuine app error
    present) vs ux (rage-only, no real error). No false-positive filtering —
    this is the crude heuristic that mistagged sessions as ux-enhancement
    when they had nothing to do with UX; classify_from_summary() below is
    preferred whenever a summary was fetched."""
    if s.get("err", 0) > 0:
        return dict(category="تقني", swimlane="Internal PROD Issues",
                    tag="technical", severity="2 - High")
    return dict(category="UX", swimlane="Design Issue",
                tag="ux-enhancement", severity="3 - Medium")


# PostHog's AI tags an event `exception='blocking'/'non-blocking'` whenever the
# app surfaced a message and stopped the user's flow at that moment — but it
# can't tell an actual crash/bug apart from the app CORRECTLY enforcing a
# business rule (out-of-stock, delivery-zone conflict, voucher minimum...).
# Confirmed on real mistagged tickets (#121353, #121382 — 2026-07-01): "items
# aren't available" was tagged exception=blocking, and "multiple delivery
# zones" / "minimum order required" were counted as repeated errors, even
# though all three are intended validation copy, not defects. Any key-action
# whose own description matches one of these known business-rule messages is
# therefore excluded before we decide technical vs UX.
BUSINESS_VALIDATION_PATTERNS = [
    "unavailable", "not available", "aren't available", "isn't available",
    "out of stock", "sold out", "no longer available",
    "multiple delivery zones", "different zones", "mix stores", "can't mix",
    "minimum order", "voucher minimum",
    "quantity limit", "maximum quantity", "max quantity", "quantity left",
    "quantity remaining", "items left", "left in stock",
    "no results found", "no results",
]

def _is_business_validation(text):
    """True if `text` (an AI-written key-action description) is describing
    the app correctly enforcing a business/stock/checkout rule rather than a
    real bug. See BUSINESS_VALIDATION_PATTERNS above for the confirmed cases."""
    if not text:
        return False
    t = text.lower()
    return any(p in t for p in BUSINESS_VALIDATION_PATTERNS)


def classify_from_summary(summary):
    """Real classification from PostHog's AI session-recording summary.
    Returns None if the session actually succeeded (session_outcome.success
    = true) -> false positive, should NOT be filed as a ticket at all.
    Otherwise, after dropping exceptions that are just business-validation
    copy (see _is_business_validation): any remaining exception='blocking'
    -> technical/High; exception='non-blocking' only -> technical/Medium (a
    genuine error, but recoverable); no real exception at all (pure
    rage-click/confusion/abandonment signals, or only business-validation
    messages) -> ux-enhancement/Medium."""
    if not summary:
        return False  # caller falls back to classify_session_basic
    outcome = summary.get("session_outcome") or {}
    if outcome.get("success"):
        return None
    exceptions = {e.get("exception") for seg in (summary.get("key_actions") or [])
                  for e in (seg.get("events") or [])
                  if e.get("exception") and not _is_business_validation(e.get("description"))}
    if "blocking" in exceptions:
        return dict(category="تقني", swimlane="Internal PROD Issues",
                    tag="technical", severity="2 - High")
    if "non-blocking" in exceptions:
        return dict(category="تقني", swimlane="Internal PROD Issues",
                    tag="technical", severity="3 - Medium")
    return dict(category="UX", swimlane="Design Issue",
                tag="ux-enhancement", severity="3 - Medium")


def classify_session(s):
    """Dispatcher: use the real AI summary when present, else the basic
    heuristic. Returns None to mean 'false positive — skip, do not file'."""
    info = classify_from_summary(s.get("ai_summary"))
    if info is False:
        return classify_session_basic(s)
    return info


def _dedup_tag(s):
    return f"posthog-session-{s['sid']}"


def _stackrank(day, index):
    """Board cards sort by StackRank ASC (smaller = higher in the column). To keep
    PostHog issues at the TOP of New with no scrolling, we use deeply-negative ranks
    (normal items here start ~351+). The base shrinks by ~100 per calendar day, so
    each new daily batch sits above all earlier ones; `index` (0 = most critical
    first) orders within the batch. Negative StackRank is valid in ADO."""
    try:
        epoch_day = (dt.date.fromisoformat(day) - dt.date(1970, 1, 1)).days
    except Exception:
        epoch_day = (dt.date.today() - dt.date(1970, 1, 1)).days
    return -(epoch_day * 100) + index


def already_filed(s, headers):
    """WIQL lookup for an existing work item carrying this session's dedup tag."""
    wiql = {
        "query": (
            "SELECT [System.Id] FROM WorkItems "
            f"WHERE [System.TeamProject] = '{ADO_PROJECT}' "
            f"AND [System.Tags] CONTAINS '{_dedup_tag(s)}'"
        )
    }
    r = requests.post(f"{ADO_BASE}/wit/wiql?api-version={ADO_API_VERSION}",
                       headers={**headers, "Content-Type": "application/json"},
                       json=wiql, timeout=30)
    r.raise_for_status()
    return bool(r.json().get("workItems"))


def _brief(s, day):
    """Generic fallback brief — used only when no AI summary was available."""
    fric = []
    if s.get("rage"):
        fric.append(f"{s['rage']} نقرة غاضبة")
    if s.get("err"):
        fric.append(f"{s['err']} خطأ حقيقي في التطبيق")
    friction_txt = " و".join(fric) if fric else "احتكاك"
    cart_lead = f"أضاف {s['cart']} للسلة ثم " if s.get("cart") else ""
    return (f"مستخدم {s.get('os','—')} (v{s.get('version','—')}) {cart_lead}"
            f"واجه {friction_txt} في جلسة بتاريخ {day} — ولم يُتم أي طلب.")


def _title_topic(summary):
    """The AI's own name for the first segment that failed — a descriptive
    ticket-title topic instead of the generic 'جلسة <date>'. None if no
    summary or every segment succeeded."""
    if not summary:
        return None
    segs = {seg.get("index"): seg.get("name") for seg in (summary.get("segments") or [])}
    for so in summary.get("segment_outcomes") or []:
        if not so.get("success"):
            return segs.get(so.get("segment_index"))
    return None


def _brief_from_summary(s, summary):
    """HTML description built entirely from PostHog AI's own generated text
    (the session/segment outcome descriptions and per-event key-action
    descriptions) — structured, not invented. Only the failed segments are
    listed, each tagged Technical-Blocking / Technical / UX from the real
    per-event `exception` flag so the team can see why it was classified
    the way it was."""
    outcome = summary.get("session_outcome") or {}
    segs = {seg.get("index"): seg.get("name") for seg in (summary.get("segments") or [])}
    actions_by_seg = {}
    for ka in summary.get("key_actions") or []:
        idx = ka.get("segment_index")
        actions_by_seg.setdefault(idx, []).extend(ka.get("events") or [])

    rows = []
    for so in summary.get("segment_outcomes") or []:
        if so.get("success"):
            continue
        idx = so.get("segment_index")
        name = segs.get(idx, f"مرحلة {idx}")
        events = actions_by_seg.get(idx, [])
        exc_kinds = {e.get("exception") for e in events
                     if e.get("exception") and not _is_business_validation(e.get("description"))}
        kind = ("Technical — Blocking" if "blocking" in exc_kinds
                else "Technical" if "non-blocking" in exc_kinds else "UX")
        detail = " ".join(e.get("description", "") for e in events) or so.get("summary", "")
        rows.append(f"<tr><td>{name}</td><td>{detail}</td><td>{kind}</td></tr>")

    table = (
        "<table border=\"1\" cellpadding=\"6\" cellspacing=\"0\" style=\"border-collapse:collapse; width:100%;\">"
        "<tr><th>المرحلة</th><th>المشكلة</th><th>التصنيف</th></tr>"
        + "".join(rows) + "</table>"
    ) if rows else ""

    return (
        "<div><strong>تحليل الجلسة (PostHog AI)</strong></div>"
        f"<div>Outcome: {'Success' if outcome.get('success') else 'Failure'}</div>"
        f"<div>{outcome.get('description', '')}</div>"
        f"{table}"
        f"<div>تسجيل الجلسة: <a href=\"{s['url']}\">{s['url']}</a></div>"
    )


def build_payload(s, day, info, index=0):
    summary = s.get("ai_summary")
    topic = _title_topic(summary)
    title = (f"[PostHog] {info['category']} — {topic} — {s.get('os','—')} v{s.get('version','—')}"
              if topic else
              f"[PostHog] {info['category']} — جلسة {day} — {s.get('os','—')} v{s.get('version','—')}")
    desc = (_brief_from_summary(s, summary) if summary else
            f"<div>{_brief(s, day)}</div>"
            f"<div>تسجيل الجلسة: <a href=\"{s['url']}\">{s['url']}</a></div>")
    return [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": desc},
        {"op": "add", "path": "/fields/System.Tags",
         "value": f"posthog; {info['tag']}; {_dedup_tag(s)}"},
        {"op": "add", "path": "/fields/System.AreaPath", "value": ADO_AREA_PATH},
        {"op": "add", "path": "/fields/myagile.Customer", "value": ADO_CUSTOMER},
        {"op": "add", "path": "/fields/Custom.Application", "value": ADO_APPLICATION},
        # PostHog issues always land in the New column at top priority.
        # (State=New is the default on creation; set explicitly for clarity.)
        {"op": "add", "path": "/fields/System.State", "value": "New"},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Common.Priority", "value": 1},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Common.Severity",
         "value": info["severity"]},
        # keep PostHog cards pinned to the TOP of the New column (smaller = higher)
        {"op": "add", "path": "/fields/Microsoft.VSTS.Common.StackRank",
         "value": _stackrank(day, index)},
    ]


def _set_board_lane(work_item_id, swimlane, headers):
    """Best-effort: System.BoardLane is currently locked ReadOnly for `Issue`
    in this org's process (confirmed even with bypassRules=true) -> swap the
    card into the right lane manually until an ADO admin relaxes that field
    rule. Once they do, this starts working with no other change needed."""
    patch = [{"op": "add", "path": "/fields/System.BoardLane", "value": swimlane}]
    r = requests.patch(
        f"{ADO_BASE}/wit/workitems/{work_item_id}?api-version={ADO_API_VERSION}",
        headers={**headers, "Content-Type": "application/json-patch+json"},
        json=patch, timeout=30)
    return r.status_code in (200, 201)


def create_ticket(s, day, headers, dry_run=False, index=0):
    """Returns one of: 'created', 'skipped', 'false-positive', 'failed', 'dry-run'.
    `index` is the session's rank in the day's batch (0 = most critical) and
    drives StackRank so the most-critical card sits highest in the New column."""
    info = classify_session(s)
    if info is None:
        print(f"  SKIP (false positive — AI summary shows the session actually "
              f"succeeded)  session {s['sid']}")
        return "false-positive"
    if already_filed(s, headers):
        print(f"  SKIP (already filed)  session {s['sid']}  [{info['category']}]")
        return "skipped"
    payload = build_payload(s, day, info, index)
    if dry_run:
        print(f"  DRY-RUN would create [{info['category']} / intended lane {info['swimlane']}]: "
              f"{payload[0]['value']}")
        return "dry-run"
    r = requests.post(
        f"{ADO_BASE}/wit/workitems/${WORK_ITEM_TYPE}?api-version={ADO_API_VERSION}",
        headers={**headers, "Content-Type": "application/json-patch+json"},
        json=payload, timeout=30)
    if r.status_code not in (200, 201):
        print(f"  FAILED  session {s['sid']}: HTTP {r.status_code} {r.text[:300]}")
        return "failed"
    wi = r.json()
    html_url = wi.get("_links", {}).get("html", {}).get("href", "")
    lane_set = _set_board_lane(wi["id"], info["swimlane"], headers)
    lane_note = info["swimlane"] if lane_set else f"{info['swimlane']} (NOT set — field locked, move manually)"
    print(f"  CREATED #{wi['id']}  [{info['category']} / lane: {lane_note}]  "
          f"session {s['sid']} -> {html_url}")
    return "created"


def push_sessions(sessions, day, dry_run=False):
    headers = _auth_headers()
    print(f"\n================ ADO PUSH ({'DRY-RUN' if dry_run else 'LIVE'}) ================")
    tally = {}
    # sessions arrive most-critical first; index keeps that order at the top of New.
    for index, s in enumerate(sessions):
        result = create_ticket(s, day, headers, dry_run=dry_run, index=index)
        tally[result] = tally.get(result, 0) + 1
    print(f"ADO push done: {tally}")
    print("====================================================================\n")
    return tally
