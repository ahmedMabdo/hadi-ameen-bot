"""طبقة صلاحيات PostHog في hadi-ameen-bot — مستويين: admin و team.

السياسة:
    admin  → كل البيانات من غير أي قيد.
    team   → نفس الإجابة، بس المبالغ المالية بتتعرض كمؤشر نسبي (الأساس=100)
             بدل الرقم المطلق. البيانات الشخصية (PII) محجوبة تماماً — مفيش
             مقابل نسبي ليها، ودي قيد قانوني مش سياسة داخلية.

الصلاحية بتتحدد من معرّف مستخدم Discord في HADI_PH_ACTOR.

⚠️ قاعدة أمنية حاكمة: HADI_PH_ACTOR لازم تتحقن من message.author.id في كود
البوت قبل تشغيل العملية. ممنوع منعاً باتاً استخراجها من نص الرسالة — لو
اتقرأت من النص، أي حد يكتب "أنا آسر" ويعدّي، والطبقة كلها تبقى بلا معنى.
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import re

# ── الأدمن: معرّفات Discord ─────────────────────────────────────────
ADMIN_IDS = {
    "1378684355148386355": "آسر",
    "1016738618267664485": "محمود",
    "544050652037513227": "أحمد",
}

# ── حقول مالية: التيم يشوفها كنسبة، مش كرقم مطلق ────────────────────
MONEY_FIELDS = frozenset({
    "total_amount", "total_payment", "subtotal", "discount_amount",
    "delivery_fee", "tip_amount", "voucher_value", "revenue", "gmv",
    "aov", "commission", "take_rate", "margin", "cogs",
})

# ── بيانات شخصية: محجوبة عن التيم تماماً ────────────────────────────
PII_FIELDS = frozenset({
    "email", "phone", "mobile", "geoip_latitude", "geoip_longitude",
    "geoip_postal_code", "address", "customer_name", "ai_input",
    "ai_output", "ip",
})

_AGGREGATES = ("count(", "sum(", "avg(", "min(", "max(", "uniq(",
               "median(", "quantile(", "round(", "topk(")

LOG_PATH = pathlib.Path(__file__).resolve().parent / "logs" / "posthog_guard.log"


class GuardDenied(Exception):
    """استعلام مرفوض لعدم كفاية الصلاحية."""


# ── الهوية ──────────────────────────────────────────────────────────
def actor() -> str:
    return (os.environ.get("HADI_PH_ACTOR") or "").strip()


def is_admin() -> bool:
    return actor() in ADMIN_IDS


def clearance() -> str:
    return "admin" if is_admin() else "team"


def actor_label() -> str:
    a = actor()
    return ADMIN_IDS.get(a) or (a if a else "unknown")


# ── أدوات ───────────────────────────────────────────────────────────
def _tokens(query: str) -> set[str]:
    """معرّفات الاستعلام بعد تجريد $ — يغطي properties.x و properties['x']."""
    return {t.lstrip("$").lower() for t in re.findall(r"[A-Za-z_$][A-Za-z0-9_$]*", query)}


def audit(action: str, query: str, reason: str = "") -> None:
    """سجل تدقيق لكل محاولة — مسموحة كانت أو مرفوضة."""
    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "actor": actor() or "unknown",
        "actor_name": actor_label(),
        "clearance": clearance(),
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


def touches(query: str, fields: frozenset) -> list[str]:
    return sorted(_tokens(query) & fields)


def is_aggregate_only(query: str) -> bool:
    """يمنع سحب صفوف خام — لازم دالة تجميع ومفيش SELECT *."""
    low = " ".join(query.split()).lower()
    if re.search(r"select\s+\*", low):
        return False
    head = low.split(" from ", 1)[0]
    return any(a in head for a in _AGGREGATES)


# ── البوابات ────────────────────────────────────────────────────────
def guard_query(query: str) -> str:
    """البوابة المركزية قبل أي تنفيذ. المالي بيعدّي (بيتقنّع وقت العرض)،
    الشخصي بيتحجب."""
    if is_admin():
        audit("allow", query)
        return query

    pii = touches(query, PII_FIELDS)
    if pii:
        audit("deny", query, f"pii:{pii}")
        raise GuardDenied(f"مرفوض — بيانات شخصية: {'، '.join(pii)}")

    if not is_aggregate_only(query):
        audit("deny", query, "raw_rows")
        raise GuardDenied(
            "مرفوض — صلاحيتك تسمح بنتائج مجمّعة فقط (count/sum/avg)، مش صفوف خام.")

    audit("allow", query, "money_masked" if touches(query, MONEY_FIELDS) else "")
    return query


def guard_free_sql(query: str) -> str:
    """بوابة أمر sql الحر.

    الاستعلام الحر مش ممكن تقنيع ناتجه تلقائياً — الطبقة مش عارفة أي عمود
    يمثّل فلوس. فلو التيم طلب حقل مالي في SQL حر بيتحوّل للأوامر الجاهزة
    اللي بتعرف تحوّله لنسبة.
    """
    if is_admin():
        return guard_query(query)

    money = touches(query, MONEY_FIELDS)
    if money:
        audit("deny", query, f"money_in_free_sql:{money}")
        raise GuardDenied(
            f"مرفوض — حقول مالية في استعلام حر: {'، '.join(money)}. "
            "استخدم today أو orders وهتوصلك كنسبة مقارنة.")

    return guard_query(query)


# ── العرض ───────────────────────────────────────────────────────────
def as_index(value: float, baseline: float | None) -> str:
    """مؤشر نسبي: الأساس = 100 نقطة."""
    if not baseline:
        return "— (مفيش أساس مقارنة)"
    pct = value / baseline * 100
    return f"{pct:.0f} نقطة مقابل الأساس ({pct - 100:+.0f}%)"


def as_share(part: float, whole: float) -> str:
    """نسبة الجزء من الكل."""
    if not whole:
        return "—"
    return f"{100.0 * part / whole:.1f}%"


# ── غلاف مولّد التقرير ──────────────────────────────────────────────
class GuardedGen:
    """بروكسي حول 8orders_report_generator — يفحص كل استعلام قبل تنفيذه."""

    def __init__(self, module):
        self._module = module

    def hogql(self, q, *args, **kwargs):
        guard_query(q)
        return self._module.hogql(q, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._module, name)
