#!/usr/bin/env python3
"""
component_evals.py - component-level evals (module B3).

Tests individual steps in isolation (not just end-to-end): issue CLASSIFICATION
and duplicate DETECTION. Complements the behavioral evals/eval_runner.py.

Cases live in evals/component_cases.json (created here with samples if missing):
  {"classify":[{"text":..., "expect_category":...}],
   "dedup":[{"a":..., "b":..., "expect_duplicate":true}]}

Wire the real functions:
  run(classify_fn, dedup_fn)
where classify_fn(text)->category and dedup_fn(a,b)->bool. Until wired, the cases
are printed and skipped (exit 0) so CI stays green. Returns exit 1 on any FAIL.
"""
import os
import sys
import json

CASES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evals", "component_cases.json")

DEFAULT = {
    "classify": [
        {"text": "الدفع بيفشل عند تأكيد الأوردر", "expect_category": "Payment"},
        {"text": "الشاشة بتحمّل بطيء جدًا", "expect_category": "Performance"},
        {"text": "الزرار مكانه غلط في الموبايل", "expect_category": "UI"},
        {"text": "الأوردر مبيوصلش للمطعم", "expect_category": "Operational"},
    ],
    "dedup": [
        {"a": "الدفع بيفشل مع فيزا", "b": "مش عارف ادفع بالفيزا", "expect_duplicate": True},
        {"a": "السيرش مش شغال", "b": "الدفع بيفشل", "expect_duplicate": False},
    ],
}


def _load():
    if os.path.exists(CASES):
        return json.load(open(CASES, encoding="utf-8"))
    os.makedirs(os.path.dirname(CASES), exist_ok=True)
    json.dump(DEFAULT, open(CASES, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return DEFAULT


def run(classify_fn=None, dedup_fn=None):
    cases = _load()
    passed = failed = skipped = 0
    for c in cases.get("classify", []):
        if not classify_fn:
            skipped += 1
            continue
        got = classify_fn(c["text"])
        ok = str(got).lower() == str(c["expect_category"]).lower()
        passed += ok
        failed += (not ok)
        print(("PASS" if ok else "FAIL"), "classify:", c["text"][:40], "->", got)
    for c in cases.get("dedup", []):
        if not dedup_fn:
            skipped += 1
            continue
        got = bool(dedup_fn(c["a"], c["b"]))
        ok = got == c["expect_duplicate"]
        passed += ok
        failed += (not ok)
        print(("PASS" if ok else "FAIL"), "dedup:", c["a"][:25], "|", c["b"][:25], "->", got)
    print(f"\ncomponent evals: {passed} passed, {failed} failed, {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
