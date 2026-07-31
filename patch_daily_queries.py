#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch intel/8orders_report_generator.py to stop hitting PostHog's max execution time.

ROOT CAUSE
  Three functions filter with nested `person_id IN (SELECT ... FROM events ...)` and
  `NOT IN (SELECT ... FROM events ...)`. Every one of those subqueries re-scans the
  whole events table, so a single query with three of them costs four full scans.
  While tracking was paused the tables were tiny and it worked; now that live traffic
  is back at ~40k events/day PostHog rejects them:
      "Query has hit the max execution time before completing"
      "Queries are a little too busy right now"

FIX
  Replace every nested-subquery filter with a single-pass `GROUP BY person_id`
  aggregation (`maxIf(...)` flags), and do set arithmetic in Python where a
  lifetime-history comparison is needed. Same numbers, one scan instead of many.
  Verified against PostHog: the aggregation form returns instantly on the exact
  window that made the old form fail.

  Also hardens hogql(): longer HTTP timeout, and treats PostHog's "busy" /
  "max execution time" responses as retryable instead of fatal.

USAGE
    python3 patch_daily_queries.py intel/8orders_report_generator.py
    python3 patch_daily_queries.py intel/8orders_report_generator.py --dry-run
"""
import re, sys, shutil, argparse, py_compile, tempfile, os

HELPERS = '''
# ─────────── fast person-set helpers (single pass, no nested re-scans) ───────────
# PostHog rejects `person_id IN (SELECT ... FROM events ...)` once volume grows:
# each subquery re-scans the whole events table, so a query carrying three of them
# costs four full scans and trips the max-execution-time limit. One GROUP BY
# person_id pass produces the same person flags, and callers filter on a cheap
# literal IN list (or plain Python set math for lifetime comparisons).
MAX_INLINE_PERSONS = 20000

def _flag(event_expr):
    """Per-person boolean: did this person emit an event matching `event_expr`?"""
    return f"maxIf(1, {event_expr})"

def _person_set(pred, having="1=1"):
    """One scan -> list of person_ids inside `pred` satisfying `having`."""
    rows = hogql(f"SELECT person_id FROM events WHERE {pred} "
                 f"GROUP BY person_id HAVING {having}")
    return [str(r[0]) for r in rows if r and r[0]]

def _in_list(ids, fallback_sql=None):
    """Literal `person_id IN (...)`. An empty set yields a never-true predicate so
    the caller's query stays valid and honestly returns zero rather than raising."""
    if not ids:
        return "1=0"
    if len(ids) <= MAX_INLINE_PERSONS:
        quoted = ",".join("'" + str(i).replace("'", "") + "'" for i in ids)
        return f"person_id IN ({quoted})"
    if fallback_sql:
        return fallback_sql
    raise RuntimeError(f"person set too large to inline ({len(ids)}) and no fallback given")

'''

ACQUISITION = '''def acquisition(day):
    """New-user funnel + non-conversion counts for the business `day`.
    - cart_no       : reached add_to_cart but placed NO order that day.
    - new_browse_no : users who NEVER ordered (lifetime) who browsed but didn't order.
    - new_cart_no   : subset of the above that reached add_to_cart.
    - acc_*         : same-day activation of accounts created that day.

    One aggregation pass covers every same-day flag. The lifetime "ever ordered"
    comparison is done as Python set arithmetic so no nested subquery is needed."""
    end = f"{(dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()} {BIZ_END}"
    P = D(day)
    row = hogql(f"""SELECT
        countIf(f_browse=1), countIf(f_cart=1), countIf(f_order=1),
        countIf(f_cart=1 AND f_order=0),
        countIf(f_acc=1), countIf(f_acc=1 AND f_browse=1),
        countIf(f_acc=1 AND f_cart=1), countIf(f_acc=1 AND f_order=1),
        countIf(f_acc=1 AND f_addr=1)
      FROM (SELECT person_id,
              {_flag("event IN ('product_viewed','store_opened','add_to_cart')")} AS f_browse,
              {_flag("event='add_to_cart'")} AS f_cart,
              {_flag("event='order_placed'")} AS f_order,
              {_flag("event='account_created'")} AS f_acc,
              {_flag("event='address_created'")} AS f_addr
            FROM events WHERE {P} GROUP BY person_id)""")[0]
    (browsers, cart, ordered, cart_no,
     acc, a_browse, a_cart, a_order, a_addr) = (int(x or 0) for x in row)

    # lifetime buyers (both the legacy "Purchase" and current "order_placed"),
    # fetched once as a set instead of being re-scanned inside every query
    ever = set(_person_set(f"event IN ('order_placed','Purchase') AND timestamp < '{end}'"))
    _browse_ev = "event IN ('product_viewed','store_opened','add_to_cart')"
    day_browsers = set(_person_set(P, _flag(_browse_ev) + "=1"))
    day_carts = set(_person_set(P, _flag("event='add_to_cart'") + "=1"))
    new_browse_no = len(day_browsers - ever)
    new_cart_no = len(day_carts - ever)

    return dict(browsers=browsers, cart=cart, ordered=ordered, cart_no=cart_no,
                new_browse_no=new_browse_no, new_cart_no=new_cart_no,
                acc=acc, acc_browse=a_browse, acc_cart=a_cart, acc_order=a_order,
                acc_addr=a_addr)
'''

COVERAGE = '''def coverage(day, days=7):
    """Delivery-coverage proxy over a trailing `days` window, WITHOUT GeoIP.
    GeoIP is NOT usable here: Egyptian ISP IP ranges register centrally, so IP
    geolocation collapses users from across the country onto 'Cairo' (a city the
    app does not even serve). The app currently serves only Hurghada & Asyut.
    Since the app does not send the selected delivery area as an event property,
    we use a behavioural proxy: a new user who creates a delivery address but
    never sees a store (no store_opened / add_to_cart) is very likely OUTSIDE the
    delivery footprint (the store list came back empty for their address).

    All nine figures now come from ONE aggregation pass. The previous version ran
    three queries carrying ten nested subqueries between them, which is what
    exceeded PostHog's execution limit once live traffic resumed."""
    start = (dt.date.fromisoformat(day) - dt.timedelta(days=days - 1)).isoformat()
    nxt = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()
    # Project tz is Africa/Cairo: express the trailing window in Cairo wall-clock
    # (start 08:00 of the first day -> 04:00 after the last business day).
    w = f"timestamp >= '{start} {BIZ_START}' AND timestamp < '{nxt} {BIZ_END}'"
    row = hogql(f"""SELECT
        countIf(f_inst=1), countIf(f_inst=1 AND f_acc=1),
        countIf(f_inst=1 AND f_saw=1), countIf(f_inst=1 AND f_ord=1),
        countIf(f_acc=1), countIf(f_acc=1 AND f_addr=1),
        countIf(f_acc=1 AND f_saw=1), countIf(f_acc=1 AND f_ord=1),
        countIf(f_acc=1 AND f_addr=1 AND f_saw=0)
      FROM (SELECT person_id,
              {_flag(f"event='{EV['install']}'")} AS f_inst,
              {_flag("event='account_created'")} AS f_acc,
              {_flag("event='address_created'")} AS f_addr,
              {_flag("event IN ('store_opened','add_to_cart')")} AS f_saw,
              {_flag("event='order_placed'")} AS f_ord
            FROM events WHERE {w} GROUP BY person_id)""")[0]
    (installed, i_reg, i_saw, i_ord,
     a_acc, a_addr, a_saw, a_ord, addr_no_store) = (int(x or 0) for x in row)
    return dict(window_days=days, served="الغردقة وأسيوط",
                installed=installed, inst_reg=i_reg, inst_saw=i_saw, inst_ord=i_ord,
                acc=a_acc, made_address=a_addr, saw_store=a_saw, ordered=a_ord,
                addr_no_store=addr_no_store)
'''

CART_PROBLEMS = '''def cart_problems(day):
    """Errors / friction for users who added to cart but did NOT order (business day).

    The target person set is resolved once in a single aggregation pass, then reused
    as a cheap literal IN filter — instead of re-scanning the events table twice
    inside every one of the four queries."""
    P = D(day)
    ids = _person_set(P, _flag("event='add_to_cart'") + "=1 AND "
                         + _flag("event='order_placed'") + "=0")
    if not ids:
        return dict(err_events=0, err_users=0, messages=[], screens=[], rage=0)
    inn = _in_list(ids)
    tot = hogql(f"""SELECT countIf(event='{EV['error']}'),
        uniqIf(person_id, event='{EV['error']}'), countIf(event='{EV['rage']}')
        FROM events WHERE {P} AND {inn}""")[0]
    msgs = hogql(f"""SELECT properties.error_message, count() FROM events
        WHERE {P} AND event='{EV['error']}' AND {inn}
        GROUP BY 1 ORDER BY 2 DESC LIMIT 5""")
    screens = hogql(f"""SELECT properties.$screen_name, count() FROM events
        WHERE {P} AND event='{EV['error']}' AND {inn}
        GROUP BY 1 ORDER BY 2 DESC LIMIT 5""")
    return dict(err_events=int(tot[0] or 0), err_users=int(tot[1] or 0),
                messages=[(m or "—", int(c)) for m, c in msgs],
                screens=[(s or "—", int(c)) for s, c in screens],
                rage=int(tot[2] or 0))
'''

REPLACEMENTS = {"acquisition": ACQUISITION, "coverage": COVERAGE,
                "cart_problems": CART_PROBLEMS}


def replace_function(src, name, new_body):
    """Swap a top-level `def name(...)` block, up to the next top-level def/comment."""
    m = re.search(rf"^def {re.escape(name)}\(", src, re.M)
    if not m:
        raise SystemExit(f"FAIL could not find `def {name}(` — file layout changed.")
    start = m.start()
    nxt = re.search(r"^(def |# ─|# ==|if __name__)", src[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(src)
    return src[:start] + new_body.rstrip() + "\n\n" + src[end:], (end - start)


RETRY_LOOP_OLD = """            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:
            last = str(e)
        if i < retries - 1:
            _t.sleep(min(2.0 ** (i + 1), 30.0) * (0.5 + random.random()))"""

RETRY_LOOP_NEW = """            last = f"HTTP {r.status_code}: {r.text[:200]}"
            # A malformed query fails identically on every attempt — retrying it
            # just burns 3x the time. Only capacity/time errors deserve a retry.
            if 400 <= r.status_code < 500 and not _is_retryable_sql(last):
                break
        except Exception as e:
            last = str(e)
        if i < retries - 1:
            # capacity errors need a longer breather than a transient network blip
            cap = 90.0 if _is_retryable_sql(last) else 30.0
            _t.sleep(min(2.0 ** (i + 1) * (3.0 if _is_retryable_sql(last) else 1.0), cap)
                     * (0.5 + random.random()))"""


def harden_hogql(src):
    changed = []
    if "timeout=90)" in src:
        src = src.replace("timeout=90)", "timeout=240)", 1)
        changed.append("hogql HTTP timeout 90s -> 240s")
    if RETRY_LOOP_OLD in src:
        src = src.replace(RETRY_LOOP_OLD, RETRY_LOOP_NEW, 1)
        changed.append("retry loop: back off longer on capacity errors, "
                       "fail fast on malformed queries")
    else:
        changed.append("WARN retry loop not matched — classifier added but not wired; "
                       "check hogql() manually")
    # make PostHog's capacity/time errors retryable rather than fatal
    if "_RETRYABLE_SQL_ERRORS" not in src:
        anchor = "def hogql(q, retries=3):"
        if anchor in src:
            src = src.replace(anchor,
                '_RETRYABLE_SQL_ERRORS = ("max execution time", "too busy", '
                '"try again later", "timeout", "503", "504")\n\n'
                'def _is_retryable_sql(msg):\n'
                '    m = (msg or "").lower()\n'
                '    return any(t in m for t in _RETRYABLE_SQL_ERRORS)\n\n'
                + anchor, 1)
            changed.append("added retryable-error classifier for PostHog capacity errors")
    return src, changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="path to intel/8orders_report_generator.py")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = open(args.target, encoding="utf-8").read()
    original = src

    if "_person_set(" in src and "MAX_INLINE_PERSONS" in src:
        print("Already patched — nothing to do.")
        return

    # insert helpers just above the first function that needs them
    anchor = re.search(r"^def _ever_ordered_subq\(|^def _scalar\(|^def acquisition\(", src, re.M)
    if not anchor:
        raise SystemExit("FAIL no anchor found for helper insertion.")
    src = src[:anchor.start()] + HELPERS.lstrip("\n") + src[anchor.start():]
    print("+ inserted fast person-set helpers")

    for name, body in REPLACEMENTS.items():
        src, removed = replace_function(src, name, body)
        print(f"+ rewrote {name}()  (replaced {removed} chars)")

    src, changed = harden_hogql(src)
    for c in changed:
        print(f"+ {c}")

    # syntax gate before touching anything on disk
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as t:
        t.write(src)
        tmp = t.name
    try:
        py_compile.compile(tmp, doraise=True)
    except py_compile.PyCompileError as e:
        raise SystemExit(f"FAIL patched file does not compile:\n{e}")
    finally:
        os.unlink(tmp)
    print("+ patched file compiles cleanly")

    nested = len(re.findall(r"person_id (?:NOT )?IN \(SELECT", src))
    print(f"  nested person_id subqueries remaining: {nested} "
          f"(was {len(re.findall(r'person_id (?:NOT )?IN .SELECT', original))})")

    if args.dry_run:
        print("DRY-RUN: no files written.")
        return
    shutil.copy2(args.target, args.target + ".bak")
    open(args.target, "w", encoding="utf-8").write(src)
    print(f"WROTE {args.target}  (backup at {args.target}.bak)")


if __name__ == "__main__":
    main()
