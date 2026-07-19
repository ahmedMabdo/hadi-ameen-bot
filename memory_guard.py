#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
حرّاس ذاكرة هادي — تحصين ضد تسميم الذاكرة (OWASP ASI06:2026).

المشكلة: بعد ما بقى لهادي ذاكرة دائمة + حلقة تحسين ذاتي، معلومة واحدة
مغلوطة تتحفظ ممكن تفضل تأثر على قراراته في جلسات كتير جاية. الضوابط هنا
بتقلّل قدرة أي حقن ناجح — احتواء مش فلترة.

أربع ضوابط:
  1) المصدر إجباري   — كل ملاحظة لازم يتسجل معاها مصدرها (--source).
  2) الإجرائي مقفول  — ملاحظات type=procedural مابتدخلش الذاكرة على طول،
                       بتروح طابور مراجعة (knowledge/memory_pending.jsonl)
                       ولازم بني آدم يوافق عليها.
  3) المنقول موسوم   — trust=forwarded/external بيتوسم في السطر نفسه،
                       وممنوع نهائيًا يبقى procedural.
  4) تراجع + فرق     — revoke بيسحب ملاحظة، وdiff بيعرض تغيّر الذاكرة.

ليه بوابة الطرفية (TTY)؟
  هادي بينفّذ الأوامر عبر أداة Bash من غير طرفية حقيقية، فـ
  sys.stdin.isatty() بيبقى False. البني آدم على SSH بيبقى True.
  يعني بوابة الموافقة غير قابلة للتجاوز من جوه الجلسة — منع حتمي في
  الكود، مش سطر تعليمات بيعتمد على طاعة الموديل.
  للأتمتة المقصودة بس: HADI_MEMORY_ADMIN=1
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
MEM = BASE / "knowledge" / "memory.md"
PENDING = BASE / "knowledge" / "memory_pending.jsonl"
REVOKED_HEADER = "## مسحوبة"

TRUST_LEVELS = ("direct", "forwarded", "external")
UNTRUSTED = ("forwarded", "external")

# مصدر مقبول: من غير مسافات ولا أقواس — عشان ميكسرش صيغة الميتا في السطر
_SRC_CLEAN_RX = re.compile(r"[^0-9A-Za-zء-ي_.:#/@\-]+")
_MIN_SRC = 3


class GuardError(Exception):
    """خرق سياسة — الرسالة بتتعرض للمستخدم زي ما هي."""


# ---------------------------------------------------------------- المصدر (1)

def clean_source(source: str) -> str:
    """يطبّع المصدر لصيغة آمنة جوه الميتا. بيرمي GuardError لو ناقص."""
    src = _SRC_CLEAN_RX.sub("-", (source or "").strip()).strip("-")
    if len(src) < _MIN_SRC:
        raise GuardError(
            "ERROR: --source إجباري (بند تحصين الذاكرة 1).\n"
            "لازم تحدد الملاحظة جاية منين، مثال:\n"
            '  --source "discord:#mars-team"   أو   --source "dm:asser"'
        )
    return src[:60]


# ------------------------------------------------------- الثقة والمنقول (3)

def validate_trust(trust: str) -> str:
    t = (trust or "direct").strip().lower()
    if t not in TRUST_LEVELS:
        raise GuardError(f"ERROR: --trust لازم يكون واحد من {'/'.join(TRUST_LEVELS)}")
    return t


def enforce_policy(mtype: str, trust: str) -> None:
    """الضابط 3: محتوى منقول/خارجي عمره ما يبقى قاعدة سلوك."""
    if mtype == "procedural" and trust in UNTRUSTED:
        raise GuardError(
            "REJECTED: ممنوع تتحول لقاعدة سلوك (procedural) ملاحظة مصدرها "
            f"'{trust}'.\nالمحتوى المنقول بيانات مش أوامر — لو القاعدة دي "
            "صح، لازم عضو في الفريق يقولها بنفسه مباشرة."
        )


def build_meta(mtype: str, expires: str, source: str, trust: str) -> str:
    """صيغة الميتا الموحّدة: {type=.. expires=.. src=.. trust=..}"""
    parts = [f"type={mtype}"]
    if expires:
        parts.append(f"expires={expires}")
    parts.append(f"src={source}")
    if trust != "direct":
        parts.append(f"trust={trust}")
    return " {" + " ".join(parts) + "}"


# ----------------------------------------------------- بوابة البني آدم (2)

def is_human() -> bool:
    if os.environ.get("HADI_MEMORY_ADMIN", "").strip() == "1":
        return True
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


def require_human(action: str) -> None:
    if is_human():
        return
    raise GuardError(
        f"BLOCKED: '{action}' محتاج مراجعة بشرية (بند تحصين الذاكرة 2).\n"
        "الأمر ده مايتنفذش من جوه جلسة هادي — لازم عضو في الفريق يشغّله\n"
        "بنفسه على السيرفر:\n"
        f"  ssh → cd ~/hadi-ameen-bot && python3 memory.py {action}"
    )


def _now() -> str:
    return dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")


def queue_pending(text: str, author: str, section: str,
                  source: str, trust: str) -> str:
    """الضابط 2: القاعدة السلوكية بتستنى في الطابور لحد ما بني آدم يوافق."""
    PENDING.parent.mkdir(parents=True, exist_ok=True)
    pid = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    rec = {"id": pid, "text": text, "author": author, "section": section,
           "source": source, "trust": trust, "queued_at": _now()}
    with PENDING.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return pid


def load_pending() -> list:
    if not PENDING.exists():
        return []
    out = []
    for ln in PENDING.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def drop_pending(pid: str) -> dict:
    rows = load_pending()
    keep, hit = [], None
    for r in rows:
        if r.get("id") == pid and hit is None:
            hit = r
        else:
            keep.append(r)
    if hit is None:
        raise GuardError(f"ERROR: مفيش عنصر في الطابور بالرقم '{pid}'")
    PENDING.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep),
        encoding="utf-8")
    return hit


# ---------------------------------------------------------- تراجع + فرق (4)

def revoke_lines(match: str, by: str, reason: str) -> int:
    """بيسحب أي سطر فيه النص ده: بيشيله من قسمه ويأرشفه تحت '## مسحوبة'."""
    if len(match.strip()) < 4:
        raise GuardError("ERROR: --match لازم يكون 4 حروف على الأقل (أمان)")
    text = MEM.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    kept, pulled = [], []
    for ln in lines:
        if ln.lstrip().startswith("- ") and match in ln:
            pulled.append(ln.rstrip("\n"))
        else:
            kept.append(ln)
    if not pulled:
        raise GuardError(f"مفيش ولا سطر فيه '{match}' — مفيش حاجة اتسحبت.")
    body = "".join(kept).rstrip("\n") + "\n"
    if REVOKED_HEADER not in body:
        body += f"\n{REVOKED_HEADER}\n\n"
    idx = body.index(REVOKED_HEADER) + len(REVOKED_HEADER)
    nl = body.index("\n", idx) + 1
    while nl < len(body) and body[nl] == "\n":
        nl += 1
    stamp = f"[مسحوبة {_now()} — {by or 'غير معروف'}"
    stamp += f" | السبب: {reason}]" if reason else "]"
    block = "".join(f"- {stamp} {p.lstrip('- ')}\n" for p in pulled)
    MEM.write_text(body[:nl] + block + body[nl:], encoding="utf-8")
    return len(pulled)


def memory_diff(days: int) -> str:
    """الضابط 4: إيه اللي اتغير في الذاكرة خلال الفترة — من git."""
    try:
        out = subprocess.run(
            ["git", "-C", str(BASE), "log", f"--since={days} days ago",
             "-p", "--no-color", "--", str(MEM)],
            check=True, capture_output=True, timeout=45).stdout.decode("utf-8", "replace")
    except Exception as e:
        raise GuardError(f"ERROR: قراءة تاريخ git فشلت ({type(e).__name__})")
    added, removed, commits = [], [], 0
    for ln in out.splitlines():
        if ln.startswith("commit "):
            commits += 1
        elif ln.startswith("+- ["):
            added.append(ln[1:])
        elif ln.startswith("-- ["):
            removed.append(ln[1:])
    rep = [f"# فرق الذاكرة — آخر {days} يوم ({commits} commit)", ""]
    rep.append(f"## اتضاف ({len(added)})")
    rep += added or ["(ولا حاجة)"]
    rep += ["", f"## اتشال ({len(removed)})"]
    rep += removed or ["(ولا حاجة)"]
    untrusted = [a for a in added if "trust=forwarded" in a or "trust=external" in a]
    if untrusted:
        rep += ["", f"## ⚠ ملاحظات من مصدر غير موثوق ({len(untrusted)}) — راجعها"]
        rep += untrusted
    nosrc = [a for a in added if "src=" not in a]
    if nosrc:
        rep += ["", f"## ⚠ ملاحظات من غير مصدر ({len(nosrc)}) — قديمة أو اتكتبت يدوي"]
        rep += nosrc
    return "\n".join(rep)


def selftest() -> int:
    ok = True

    def check(label, cond):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + label)
        ok = ok and bool(cond)

    try:
        clean_source("")
        check("المصدر الفاضي بيترفض", False)
    except GuardError:
        check("المصدر الفاضي بيترفض", True)

    check("تنظيف المصدر", clean_source("discord:#mars team") == "discord:#mars-team")
    check("trust افتراضي", validate_trust("") == "direct")

    try:
        validate_trust("whatever")
        check("trust غلط بيترفض", False)
    except GuardError:
        check("trust غلط بيترفض", True)

    try:
        enforce_policy("procedural", "forwarded")
        check("منقول+procedural بيترفض", False)
    except GuardError:
        check("منقول+procedural بيترفض", True)

    enforce_policy("semantic", "forwarded")
    check("منقول+semantic بيعدي", True)

    meta = build_meta("episodic", "2026-08-01", "dm:asser", "direct")
    check("صيغة الميتا", meta == " {type=episodic expires=2026-08-01 src=dm:asser}")
    meta2 = build_meta("semantic", "", "discord:#po", "forwarded")
    check("ميتا المنقول", meta2 == " {type=semantic src=discord:#po trust=forwarded}")

    os.environ.pop("HADI_MEMORY_ADMIN", None)
    check("tty gate follows isatty", is_human() == sys.stdin.isatty())
    os.environ["HADI_MEMORY_ADMIN"] = "1"
    check("تجاوز مقصود شغّال", is_human() is True)
    os.environ.pop("HADI_MEMORY_ADMIN", None)

    try:
        revoke_lines("ab", "x", "")
        check("match قصير بيترفض", False)
    except GuardError:
        check("match قصير بيترفض", True)

    print("\n" + ("ALL PASS" if ok else "THERE ARE FAILURES"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest())
