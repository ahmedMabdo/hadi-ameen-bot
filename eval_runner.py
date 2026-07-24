#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مشغّل حالات هادي الذهبية (بند 5.1/5.3) — قياس قبل/بعد أي تعديل تعليمات.

الفكرة: بدل ما نجرب الـ 10 حالات يدوي على Discord بعد كل تعديل، الحالات بتتنفذ
**بنفس دالة بناء البرومبت اللي البوت بيستخدمها** (`discord_bot.ask_claude`) —
مش نسخة تانية، عشان الاختبار ميكدبش.

الفحص deterministic (مفيش LLM-as-judge لسه — معايرته بتاخد جولات، والحالات دي
بتتفحص بالكود بصفر تكلفة إضافية وصفر خلاف).

الاستخدام:
    eval_runner.py list                       # الحالات من غير أي تشغيل (مجاني)
    eval_runner.py run [--case id] [--category X] [--limit N] [--concurrency 2]
    eval_runner.py baseline                   # يعلّم آخر تشغيل كخط أساس
    eval_runner.py diff                       # آخر تشغيل مقابل خط الأساس (قبل/بعد)

تنبيه تكلفة: كل حالة = تشغيلة Claude حقيقية. ابدأ بـ --limit صغير.
النتايج بتتحفظ في evals/runs/*.json (في .gitignore — حالة تشغيل).
"""
import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
CASES_FILE = BASE / "evals" / "cases.json"
RUNS_DIR = BASE / "evals" / "runs"
BASELINE_LINK = BASE / "evals" / "baseline.json"

REACT_RX = re.compile(r"^REACT:\s*\S+", re.MULTILINE)
NO_REPLY_RX = re.compile(r"^\s*NO_REPLY\s*$", re.IGNORECASE)


def load_cases():
    if not CASES_FILE.exists():
        sys.exit(f"مفيش ملف حالات: {CASES_FILE}")
    data = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    return data.get("cases", [])


# --- الفحوص ---------------------------------------------------------------
def is_silent(reply: str) -> bool:
    clean = (reply or "").strip()
    return bool(NO_REPLY_RX.match(clean)) or clean[:8].upper() == "NO_REPLY"


def check(expect: dict, reply: str):
    """بيرجّع (نجح؟, وصف)."""
    kind = expect["type"]
    body = (reply or "")
    silent = is_silent(body)

    if kind == "no_reply":
        return silent, "لازم يسكت"
    if kind == "replies":
        return (not silent) and len(body.strip()) > 3, "لازم يرد"
    if kind == "react_line":
        if silent:
            return False, "سطر REACT مطلوب (والرد كان صمت)"
        return bool(REACT_RX.match(body.strip())), "أول سطر REACT: <إيموجي>"
    if kind == "contains_all":
        missing = [v for v in expect["values"] if v not in body]
        return not missing, f"لازم يحتوي: {expect['values']}" + (f" — ناقص {missing}" if missing else "")
    if kind == "contains_any":
        hit = [v for v in expect["values"] if v in body]
        return bool(hit), f"لازم يحتوي واحد من: {expect['values']}"
    if kind == "not_contains":
        bad = [v for v in expect["values"] if v in body]
        return not bad, f"ممنوع يحتوي: {expect['values']}" + (f" — ظهر {bad}" if bad else "")
    if kind == "regex":
        return bool(re.search(expect["pattern"], body, re.MULTILINE)), f"نمط: {expect['pattern']}"
    return False, f"نوع شرط مش معروف: {kind}"


# --- التشغيل ---------------------------------------------------------------
def normalize_case(case: dict) -> dict:
    """ترجمة الحالات القديمة السكيما (F2) لسكيما الـ runner — دفاع في العمق حتى
    بعد تصليح الملف: prompt→input.message، expect النصي بيتشال،
    must_include→contains_all، must_not_include→not_contains."""
    if "input" in case and isinstance(case.get("expect"), list):
        return case
    c = dict(case)
    if "input" not in c:
        c["input"] = {"message": c.pop("prompt", ""), "author": "آسر جميل",
                      "channel": "رسالة خاصة (DM)"}
    expect = c.get("expect")
    checks = list(expect) if isinstance(expect, list) else []
    if isinstance(expect, str):
        c["note"] = expect  # الوصف النصي بيتحفظ كملاحظة مش كفحص
        checks = []
    mi = c.pop("must_include", None)
    if mi:
        checks.append({"type": "contains_all", "values": mi})
    mni = c.pop("must_not_include", None)
    if mni:
        checks.append({"type": "not_contains", "values": mni})
    c["expect"] = checks or [{"type": "replies"}]
    return c


def validate_cases(cases) -> list:
    """فحص سكيما الحالات — بيرجع قايمة أخطاء (فاضية = سليم). بيمنع تكرار F2."""
    errors, seen = [], set()
    known = {"no_reply", "replies", "react_line", "contains_all", "contains_any",
             "not_contains", "regex"}
    for i, c in enumerate(cases):
        cid = c.get("id") or f"#{i}"
        if not c.get("id"):
            errors.append(f"{cid}: مفيش id")
        elif c["id"] in seen:
            errors.append(f"{cid}: id مكرر")
        seen.add(cid)
        if not isinstance(c.get("input"), dict) or not c["input"].get("message"):
            errors.append(f"{cid}: مفيش input.message (سكيما قديمة؟ شغّل normalize)")
        exp = c.get("expect")
        if not isinstance(exp, list) or not exp:
            errors.append(f"{cid}: expect لازم يكون list فيها فحص واحد على الأقل")
            continue
        for e in exp:
            if not isinstance(e, dict) or e.get("type") not in known:
                errors.append(f"{cid}: فحص غير معروف: {e}")
            elif e["type"] in ("contains_all", "contains_any", "not_contains") \
                    and not e.get("values"):
                errors.append(f"{cid}: {e['type']} من غير values")
            elif e["type"] == "regex" and not e.get("pattern"):
                errors.append(f"{cid}: regex من غير pattern")
    return errors


async def run_case(case: dict, sem: asyncio.Semaphore) -> dict:
    import discord_bot  # آمن: client.run متغلّف بـ __main__ (بند 5.3)

    case = normalize_case(case)
    inp = case["input"]
    forwarded = inp.get("forwarded", "")
    message = inp["message"]
    if forwarded:
        message = f"{message}\n\n[رسالة منقولة]\n{forwarded}"

    started = time.time()
    async with sem:
        try:
            reply = await discord_bot.ask_claude(
                message,
                inp.get("author", "آسر"),
                inp.get("history", ""),
                inp.get("reply_context", ""),
                inp.get("channel", "#team-mars-po"),
                [],
                "eval",
                "",
                conv_key="",  # جلسة نظيفة — الاختبار مايلوثش جلسات القنوات الحقيقية
            )
            error = ""
        except Exception as err:  # noqa: BLE001
            reply, error = "", f"{type(err).__name__}: {err}"

    checks = []
    for expect in case.get("expect", []):
        ok, label = (False, f"مااتفحصش (خطأ): {error}") if error else check(expect, reply)
        checks.append({"type": expect["type"], "ok": ok, "label": label})

    return {
        "id": case["id"],
        "category": case.get("category", ""),
        "passed": bool(checks) and all(c["ok"] for c in checks) and not error,
        "error": error,
        "latency_s": round(time.time() - started, 1),
        "reply_excerpt": (reply or "")[:300].replace("\n", " "),
        "checks": checks,
    }


async def run_all(cases, concurrency: int) -> dict:
    sem = asyncio.Semaphore(max(1, concurrency))
    # F2: return_exceptions — حالة واحدة بايظة عمرها ما توقف الـ suite كله تاني
    raw = await asyncio.gather(*(run_case(c, sem) for c in cases),
                               return_exceptions=True)
    results = []
    for c, r in zip(cases, raw):
        if isinstance(r, BaseException):
            results.append({"id": c.get("id", "?"), "category": c.get("category", ""),
                            "passed": False, "error": f"{type(r).__name__}: {r}",
                            "latency_s": 0, "reply_excerpt": "", "checks": []})
        else:
            results.append(r)
    passed = sum(1 for r in results if r["passed"])
    return {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(100.0 * passed / len(results), 1) if results else 0.0,
        "results": results,
    }


def save_run(run: dict) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / f"run_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def latest_run():
    runs = sorted(RUNS_DIR.glob("run_*.json")) if RUNS_DIR.exists() else []
    return json.loads(runs[-1].read_text(encoding="utf-8")) if runs else None


def print_run(run: dict):
    print(f"\nالنتيجة: {run['passed']}/{run['total']} ناجحة ({run['pass_rate']}%) — {run['ts']}")
    for r in sorted(run["results"], key=lambda x: (x["passed"], x["id"])):
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"\n[{mark}] {r['id']} ({r['category']}) — {r['latency_s']}s")
        for c in r["checks"]:
            if not c["ok"]:
                print(f"   ✗ {c['label']}")
        if r["error"]:
            print(f"   ! {r['error']}")
        if not r["passed"]:
            print(f"   رد: {r['reply_excerpt'][:160]}")


def main():
    parser = argparse.ArgumentParser(description="مشغّل حالات هادي الذهبية (بند 5.1/5.3)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("--case"); r.add_argument("--category")
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--concurrency", type=int, default=2)
    sub.add_parser("baseline")
    sub.add_parser("diff")
    sub.add_parser("validate")  # F2: فحص سكيما الحالات من غير أي تشغيل (مجاني)
    args = parser.parse_args()

    cases = load_cases()

    if args.cmd == "validate":
        errors = validate_cases([normalize_case(c) for c in load_cases()])
        if errors:
            print(f"❌ {len(errors)} مشكلة سكيما:")
            for e in errors:
                print(" -", e)
            sys.exit(1)
        print(f"✅ السكيما سليمة — {len(load_cases())} حالة")
        return

    if args.cmd == "list":
        print(f"{len(cases)} حالة:")
        for c in cases:
            print(f"  {c['id']:28} [{c.get('category','')}] — {c.get('why','')[:70]}")
        return

    if args.cmd == "run":
        if args.case:
            cases = [c for c in cases if c["id"] == args.case]
        if args.category:
            cases = [c for c in cases if c.get("category") == args.category]
        if args.limit:
            cases = cases[: args.limit]
        if not cases:
            sys.exit("مفيش حالات مطابقة.")
        print(f"بشغّل {len(cases)} حالة (تشغيلات Claude حقيقية) — concurrency={args.concurrency}…")
        run = asyncio.run(run_all(cases, args.concurrency))
        path = save_run(run)
        print_run(run)
        print(f"\nاتحفظت: {path.name}")
        return

    if args.cmd == "baseline":
        run = latest_run()
        if not run:
            sys.exit("مفيش تشغيلات لسه — شغّل run الأول.")
        BASELINE_LINK.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"خط الأساس اتظبط على تشغيلة {run['ts']} ({run['pass_rate']}%)")
        return

    if args.cmd == "diff":
        run = latest_run()
        if not run:
            sys.exit("مفيش تشغيلات لسه.")
        if not BASELINE_LINK.exists():
            sys.exit("مفيش خط أساس — شغّل baseline الأول.")
        base = json.loads(BASELINE_LINK.read_text(encoding="utf-8"))
        bmap = {r["id"]: r for r in base["results"]}
        print(f"قبل: {base['pass_rate']}% ({base['ts']})  →  بعد: {run['pass_rate']}% ({run['ts']})")
        regressions, fixes = [], []
        for r in run["results"]:
            b = bmap.get(r["id"])
            if not b:
                continue
            if b["passed"] and not r["passed"]:
                regressions.append(r["id"])
            elif not b["passed"] and r["passed"]:
                fixes.append(r["id"])
        print(f"\nاتصلح: {', '.join(fixes) if fixes else 'مفيش'}")
        print(f"اتكسر: {', '.join(regressions) if regressions else 'مفيش'}")
        if regressions:
            print("\n⚠ في انحدار — راجع قبل ما تنشر التعديل.")
            sys.exit(1)


if __name__ == "__main__":
    main()
