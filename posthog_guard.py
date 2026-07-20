"""طبقة صلاحيات لاستعلامات PostHog في hadi-ameen-bot.

المبدأ: الاستعلام الحر غير متاح للتيم العام إطلاقاً (allowlist مش blocklist).
الفلترة النصية هنا طبقة دفاع ثانية فقط — الضمانة الأساسية إن صلاحية team
مالهاش وصول لأمر sql الحر أصلاً، لأن فلترة SQL نصياً مش موثوقة بطبيعتها.

يُفعّل عبر متغيري بيئة:
    HADI_PH_CLEARANCE = team | lead | exec      (الافتراضي: team)
    HADI_PH_ACTOR     = معرّف الطالب للـ audit trail
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import re

CLEARANCES = ("team", "lead", "exec")

# ── تصنيف الحقول حسب أقل صلاحية مطلوبة ──────────────────────────────
TIER1_FINANCIAL = (
    "total_amount", "total_payment", "subtotal", "discount_amount",
    "delivery_fee", "tip_amount", "voucher_value", "revenue", "gmv",
    "aov", "commission", "take_rate", "margin", "cogs",
)
TIER2_COMMERCIAL = (
    "store_id", "store_name", "merchant_id", "merchant_name",
    "vendor_id", "vendor_name", "branch_id",
)
TIER3_PII = (
    "email", "phone", "mobile", "geoip_latitude", "geoip_longitude",
    "geoip_postal_code", "address", "payment_method", "ai_input",
    "ai_output", "ip", "person_id", "customer_name",
)

MIN_CLEARANCE: dict[str, str] = {}
MIN_CLEARANCE.update({f: "exec" for f in TIER1_FINANCIAL})
MIN_CLEARANCE.update({f: "lead" for f in TIER2_COMMERCIAL})
MIN_CLEARANCE.update({f: "exec" for f in TIER3_PII})

_AGGREGATES = ("count(", "sum(", "avg(", "min(", "max(", "uniq(",
               "median(", "quantile(", "any(", "topk(")

LOG_PATH = pathlib.Path(__file__).resolve().parent / "logs" / "posthog_guard.log"


class GuardDenied(Exception):
    """استعلام مرفوض لعدم كفاية الصلاحية."""


# ── أدوات مساعدة ────────────────────────────────────────────────────
def rank(c: str) -> int:
    return CLEARANCES.index(c) if c in CLEARANCES else 0


def clearance() -> str:
    c = (os.environ.get("HADI_PH_CLEARANCE") or "team").strip().lower()
    return c if c in CLEARANCES else "team"


def actor() -> str:
    return (os.environ.get("HADI_PH_ACTOR") or "unknown").strip()


def _tokens(q: str) -> set[str]:
    """كل المعرّفات في الاستعلام بعد تجريد $ — يغطي properties.x و properties['x']."""
    return {t.lstrip("$").lower() for t in re.findall(r"[A-Za-z_$][A-Za-z0-9_$]*", q)}


def audit(action: str, query: str, c: str, reason: str = "") -> None:
    """سجل تدقيق لكل محاولة — مسموحة كانت أو مرفوضة."""
    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "actor": actor(),
        "clearance": c,
        "action": action,
        "reason": reason,
        "query": " ".join(query.split())[:500],
    }
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass  # فشل التسجيل ما يوقفش التشغيل


# ── الفحوصات ────────────────────────────────────────────────────────
def field_violations(query: str, c: str) -> list[tuple[str, str]]:
    """الحقول اللي الاستعلام بيلمسها والصلاحية مش كفاية ليها."""
    toks = _tokens(query)
    return sorted(
        (f, need) for f, need in MIN_CLEARANCE.items()
        if f in toks and rank(c) < rank(need)
    )


def is_aggregate_only(query: str) -> bool:
    """يمنع سحب صفوف خام — لازم دالة تجميع ومفيش SELECT *."""
    low = " ".join(query.split()).lower()
    if re.search(r"select\s+\*", low):
        return False
    head = low.split(" from ", 1)[0]
    return any(a in head for a in _AGGREGATES)


def guard_query(query: str, c: str | None = None) -> str:
    """البوابة المركزية — تُستدعى قبل أي تنفيذ. ترجّع الاستعلام أو ترمي GuardDenied."""
    c = c or clearance()

    if rank(c) < rank("exec") and not is_aggregate_only(query):
        audit("deny", query, c, "raw_rows")
        raise GuardDenied(
            "مرفوض — صلاحيتك تسمح بنتائج مجمّعة فقط (count/sum/avg)، "
            "مش صفوف خام. ده بيمنع تسريب بيانات شخصية."
        )

    bad = field_violations(query, c)
    if bad:
        names = "، ".join(f"{f} (يحتاج {need})" for f, need in bad)
        audit("deny", query, c, f"fields:{[f for f, _ in bad]}")
        raise GuardDenied(f"مرفوض — حقول مقيّدة: {names}")

    audit("allow", query, c)
    return query


def guard_free_sql(query: str, c: str | None = None) -> str:
    """بوابة أمر sql الحر — من lead فأعلى فقط."""
    c = c or clearance()
    if rank(c) < rank("lead"):
        audit("deny", query, c, "free_sql_forbidden")
        raise GuardDenied(
            "مرفوض — الاستعلام الحر مقفول لصلاحية team. "
            "استخدم: health / today / orders / errors / since"
        )
    return guard_query(query, c)


# ── تحويل القيم المطلقة لنسب (سياسة التيم العام) ────────────────────
def as_ratio(value: float, baseline: float | None) -> str:
    """يحوّل رقم مطلق لنسبة تغيّر مقابل خط الأساس."""
    if not baseline:
        return "—"
    return f"{(value / baseline - 1) * 100:+.1f}%"


def as_index(value: float, baseline: float | None) -> str:
    """رقم قياسي: الأساس = 100 نقطة."""
    if not baseline:
        return "—"
    return f"{value / baseline * 100:.0f} نقطة"


def present(value: float, baseline: float | None = None, c: str | None = None) -> str:
    """يعرض القيمة المطلقة لـ exec/lead، ونسبة فقط لـ team."""
    c = c or clearance()
    if rank(c) >= rank("lead"):
        return f"{value:,.0f}"
    return as_index(value, baseline)


# ── غلاف مولّد التقرير ──────────────────────────────────────────────
class GuardedGen:
    """بروكسي حول 8orders_report_generator — يفحص كل استعلام قبل تنفيذه."""

    def __init__(self, module, c: str | None = None):
        self._module = module
        self._clearance = c or clearance()

    def hogql(self, q, *args, **kwargs):
        guard_query(q, self._clearance)
        return self._module.hogql(q, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._module, name)
