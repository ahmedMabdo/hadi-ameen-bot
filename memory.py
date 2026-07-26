#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداة الذاكرة الدائمة لهادي. بتضيف ملاحظات مؤرَّخة ومنسوبة لصاحبها في
knowledge/memory.md، وبتعمل commit + push (best-effort) عشان الذاكرة تبقى
دائمة وليها audit trail. البوت بيحمّل الذاكرة مع كل محادثة (بند 4.2:
النواة + قواعد السلوك + الملاحظات ذات الصلة عبر memory_store)، فأي حاجة
اتحفظت تبقى متاحة في كل القنوات.

أوامر:
    memory.py show
    memory.py add --section <decisions|sprint|notes|general> --text "..." --author "الاسم"
                  [--type <semantic|episodic|procedural>] [--expires YYYY-MM-DD]
    memory.py search --query "..."

أنواع الملاحظات (بند 4.2 مرحلة ب):
    semantic   (الافتراضي) حقيقة دائمة — زي أي ملاحظة قديمة.
    episodic   حدث بصلاحية — مع --expires بيسقط من حقن البرومبت بعد تاريخه
               (بيفضل مؤرشف في الملف). مثال: أزمة كوتا بتخلص بتاريخ معروف.
    procedural قاعدة سلوك متعلمة («متكتبش توقيع») — بتتحقن دايمًا.

أي عضو في التيم يقدر يحفظ. كل سطر بيتسجّل: [التاريخ — مين] المعلومة.
"""
import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import memory_guard  # تحصين الذاكرة ضد التسميم (OWASP ASI06)
import state_lock  # بند 3.3 — تسلسل الكتابات المشتركة مع باقي أدوات الحالة

BASE = Path(__file__).resolve().parent
MEM = BASE / "knowledge" / "memory.md"
TZ = ZoneInfo("Africa/Cairo")

SECTIONS = {
    "decisions": "## قرارات",
    "sprint": "## سبرنت",
    "notes": "## ملاحظات",
    "general": "## عام",
}

MEMORY_TYPES = ("semantic", "episodic", "procedural")


def _now():
    return dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M")


def _ensure():
    if not MEM.exists():
        MEM.parent.mkdir(parents=True, exist_ok=True)
        body = ("# ذاكرة هادي الدائمة\n\n"
                "> ملف بيتحدّث آليًا عبر memory.py. كل سطر: [التاريخ — مين] المعلومة.\n"
                "> بيتحمّل مع كل محادثة، فهادي عارف اللي هنا في أي قناة.\n\n")
        for h in ("decisions", "sprint", "notes", "general"):
            body += SECTIONS[h] + "\n\n"
        MEM.write_text(body, encoding="utf-8")


def cmd_show(args):
    _ensure()
    print(MEM.read_text(encoding="utf-8"))


def _meta_suffix(mtype: str, expires: str, source: str = "",
                 trust: str = "direct") -> str:
    """بند 4.2 + تحصين الذاكرة: النوع/الصلاحية/المصدر/الثقة جوه السطر نفسه.
    الملف يفضل مصدر الحقيقة الوحيد — الفهرس مشتق منه."""
    return memory_guard.build_meta(mtype, expires, source, trust)


def cmd_add(args):
    _ensure()
    header = SECTIONS.get(args.section, SECTIONS["general"])
    author = (args.author or "غير معروف").strip()

    mtype = (args.mtype or "semantic").strip()
    expires = (args.expires or "").strip()
    if expires:
        try:
            dt.datetime.strptime(expires, "%Y-%m-%d")
        except ValueError:
            sys.exit(f"ERROR: صيغة --expires غلط '{expires}'. استخدم YYYY-MM-DD.")
        if mtype == "semantic":
            mtype = "episodic"  # تاريخ صلاحية = حدث بطبيعته

    # تحصين الذاكرة (1)(3): المصدر إجباري، والمنقول ممنوع يبقى قاعدة سلوك
    try:
        source = memory_guard.clean_source(getattr(args, "source", ""))
        trust = memory_guard.validate_trust(getattr(args, "trust", "direct"))
        memory_guard.enforce_policy(mtype, trust)
    except memory_guard.GuardError as e:
        sys.exit(str(e))

    # تحصين الذاكرة (2): قواعد السلوك بتستنى موافقة بني آدم
    if mtype == "procedural":
        pid = memory_guard.queue_pending(args.text.strip(), author,
                                         args.section, source, trust)
        print(f"QUEUED [{pid}] قاعدة سلوك مستنية مراجعة بشرية — "
              "مادخلتش الذاكرة.\n"
              f"  الموافقة (بني آدم على SSH): python3 memory.py approve --id {pid} --by \"اسمك\"\n"
              f"  الرفض (هادي مسموح):        python3 memory.py reject --id {pid} --by \"آسر\"\n"
              "  الخطوة الجاية لهادي: شاور آسر في الـ DM بـ notify.py وقوله الـ id ده.")
        return

    line = f"- [{_now()} — {author}] {args.text.strip()}{_meta_suffix(mtype, expires, source, trust)}\n"
    text = MEM.read_text(encoding="utf-8")

    if header in text:
        idx = text.index(header)
        nl = text.index("\n", idx) + 1  # بعد سطر العنوان
        while nl < len(text) and text[nl] == "\n":  # تخطّي السطر الفاضي
            nl += 1
        tail = text[nl:]
        sep = "\n" if tail.startswith("#") else ""  # سطر فاصل قبل العنوان اللي بعده
        text = text[:nl] + line + sep + tail
    else:
        text += f"\n{header}\n\n{line}"

    MEM.write_text(text, encoding="utf-8")
    print(f"SAVED [{args.section}]: {args.text.strip()}")
    _git_persist(f"memory: {args.section} note by {author}")
    _index_note(line, args.section)


def _index_note(line: str, section: str):
    """بند 4.2: فهرسة السطر الجديد في memory_index.db — فشلها عمره ما يمنع الحفظ."""
    try:
        import memory_store
        memory_store.index_note(line.rstrip("\n"), section)
        print("INDEXED (memory_index.db)")
    except Exception as e:
        print(f"WARN: الفهرسة فشلت ({type(e).__name__}) — الملف اتحفظ عادي؛ "
              "صلّح الفهرس بـ: python3 memory_store.py rebuild")


def cmd_search(args):
    _ensure()
    q = args.query.strip()
    # بند 4.2: بحث مرتب بالصلة (FTS5/BM25 + تطبيع عربي) بدل substring — بfallback آمن
    try:
        import memory_store
        hits = memory_store.search(q, k=10)
        print("\n".join(h["raw"] for h in hits) if hits else "مفيش نتيجة في الذاكرة.")
        return
    except Exception as e:
        print(f"WARN: بحث الفهرس فشل ({type(e).__name__}) — رجوع للبحث النصي")
    hits = [l for l in MEM.read_text(encoding="utf-8").splitlines()
            if q.lower() in l.lower() and l.strip().startswith("-")]
    print("\n".join(hits) if hits else "مفيش نتيجة في الذاكرة.")


def _git_commit_only(msg):
    """commit محلي بس — سريع، وبيتنفّذ جوّه قفل الكتابة."""
    try:
        for cmd in (["add", str(MEM)], ["commit", "-m", msg]):
            subprocess.run(["git", "-C", str(BASE), *cmd],
                           check=True, capture_output=True, timeout=30)
        return True
    except Exception as e:
        print(f"WARN: git commit فشل: {type(e).__name__} "
              "(الذاكرة محفوظة على القرص)")
        return False


def _git_push_async():
    """push **بره** قفل الكتابة.

    2026-07-26: كان الـ push (لحد 60 ثانية شبكة) بيتنفّذ جوّه state_lock اللي
    مهلة المنتظرين فيه 60 ثانية — فأي حفظ تاني أو reminder_loop كان بياخد
    TimeoutError لما GitHub يبطّأ. القاعدة: عمليات الشبكة مابتتحطش جوّه أقفال
    بتحمي حالة محلية.
    """
    try:
        subprocess.run(["git", "-C", str(BASE), "push"],
                       check=True, capture_output=True, timeout=60)
        print("PERSISTED (committed + pushed)")
    except Exception as e:
        print(f"WARN: push فشل: {type(e).__name__} "
              "(الـ commit محلي وهيتزامن مع أول push ناجح)")


def _git_persist(msg):
    """للتوافق: commit جوّه القفل، والـ push بيتأجل للمُنادي."""
    return _git_commit_only(msg)


def cmd_pending(args):
    rows = memory_guard.load_pending()
    if not rows:
        print("الطابور فاضي — مفيش قواعد سلوك مستنية.")
        return
    print(f"# قواعد سلوك مستنية مراجعة ({len(rows)})\n")
    for r in rows:
        print(f"[{r['id']}] {r['text']}")
        print(f"      قالها: {r['author']} | المصدر: {r['source']} | "
              f"الثقة: {r['trust']} | الوقت: {r['queued_at']}\n")


def cmd_approve(args):
    try:
        memory_guard.require_human("approve")
        rec = memory_guard.drop_pending(args.pid)
    except memory_guard.GuardError as e:
        sys.exit(str(e))
    by = (args.by or "").strip()
    if not by:
        sys.exit("ERROR: --by إجباري — مين اللي وافق؟")
    _ensure()
    header = SECTIONS.get(rec["section"], SECTIONS["general"])
    meta = _meta_suffix("procedural", "", rec["source"], rec["trust"])
    line = (f"- [{_now()} — {rec['author']}] {rec['text']}"
            f" (وافق: {by}){meta}\n")
    text = MEM.read_text(encoding="utf-8")
    if header in text:
        idx = text.index(header)
        nl = text.index("\n", idx) + 1
        while nl < len(text) and text[nl] == "\n":
            nl += 1
        tail = text[nl:]
        sep = "\n" if tail.startswith("#") else ""
        text = text[:nl] + line + sep + tail
    else:
        text += f"\n{header}\n\n{line}"
    MEM.write_text(text, encoding="utf-8")
    print(f"APPROVED [{args.pid}] بواسطة {by}: {rec['text']}")
    _git_persist(f"memory: procedural rule approved by {by}")
    _index_note(line, rec["section"])


def cmd_reject(args):
    """يشيل قاعدة سلوك من طابور المراجعة — **مسموح لهادي** (2026-07-26).

    ليه approve محتاج بني آدم و reject لأ: الاتجاه الآمن. approve بيضيف قاعدة
    بتغيّر سلوك هادي (خطر لو اتحقن)، أما reject بيمنع قاعدة من الدخول —
    أسوأ نتيجة إن قاعدة شرعية مادخلتش، وده فشل آمن.

    وكان مفيش مسار «رفض» أصلًا: drop_pending كان بيتنادى من approve بس، فأي
    قاعدة آسر يرفضها كانت بتفضل في الطابور للأبد.
    """
    try:
        rec = memory_guard.drop_pending(args.pid)
    except memory_guard.GuardError as e:
        sys.exit(str(e))
    by = (args.by or "").strip() or "غير محدد"
    print(f"REJECTED [{args.pid}] بقرار {by}: {rec['text']}")
    if args.reason:
        print(f"السبب: {args.reason}")


def cmd_revoke(args):
    try:
        memory_guard.require_human("revoke")
        _ensure()
        n = memory_guard.revoke_lines(args.match, args.by, args.reason)
    except memory_guard.GuardError as e:
        sys.exit(str(e))
    print(f"REVOKED {n} سطر — اتنقلوا لقسم «مسحوبة».")
    _git_persist(f"memory: revoke {n} note(s) by {args.by or 'unknown'}")
    try:
        import memory_store
        memory_store.rebuild()
        print("REBUILT (memory_index.db)")
    except Exception as e:
        print(f"WARN: إعادة بناء الفهرس فشلت ({type(e).__name__}) — "
              "شغّل: python3 memory_store.py rebuild")


def cmd_diff(args):
    try:
        print(memory_guard.memory_diff(args.days))
    except memory_guard.GuardError as e:
        sys.exit(str(e))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="اطبع الذاكرة كلها")
    s.set_defaults(func=cmd_show)

    a = sub.add_parser("add", help="احفظ ملاحظة جديدة")
    a.add_argument("--section", default="general", choices=list(SECTIONS))
    a.add_argument("--text", required=True)
    a.add_argument("--author", default="")
    a.add_argument("--source", default="",
                   help="تحصين الذاكرة (1): إجباري — الملاحظة جاية منين "
                        "(مثال: discord:#mars-team أو dm:asser)")
    a.add_argument("--trust", default="direct",
                   choices=list(memory_guard.TRUST_LEVELS),
                   help="تحصين الذاكرة (3): مصدر الكلام — direct لعضو "
                        "في الفريق، forwarded/external لمحتوى منقول")
    a.add_argument("--type", dest="mtype", default="semantic", choices=list(MEMORY_TYPES),
                   help="بند 4.2: نوع الملاحظة (افتراضي semantic)")
    a.add_argument("--expires", default="",
                   help="بند 4.2: YYYY-MM-DD — بعده الملاحظة بتسقط من حقن البرومبت (episodic)")
    a.set_defaults(func=cmd_add)

    pn = sub.add_parser("pending", help="اعرض قواعد السلوك المستنية مراجعة")
    pn.set_defaults(func=cmd_pending)

    ap = sub.add_parser("approve", help="وافق على قاعدة سلوك (بني آدم بس)")
    ap.add_argument("--id", dest="pid", required=True)
    ap.add_argument("--by", required=True, help="مين اللي وافق")
    ap.set_defaults(func=cmd_approve)

    rj = sub.add_parser("reject", help="ارفض قاعدة سلوك من الطابور (مسموح لهادي)")
    rj.add_argument("--id", dest="pid", required=True)
    rj.add_argument("--by", default="", help="مين اللي رفض")
    rj.add_argument("--reason", default="", help="السبب")
    rj.set_defaults(func=cmd_reject)

    rv = sub.add_parser("revoke", help="اسحب ملاحظة من الذاكرة (بني آدم بس)")
    rv.add_argument("--match", required=True, help="نص موجود في السطر")
    rv.add_argument("--by", default="", help="مين اللي سحبها")
    rv.add_argument("--reason", default="", help="السبب")
    rv.set_defaults(func=cmd_revoke)

    df = sub.add_parser("diff", help="إيه اللي اتغير في الذاكرة بالفترة")
    df.add_argument("--days", type=int, default=7)
    df.set_defaults(func=cmd_diff)

    q = sub.add_parser("search", help="دوّر في الذاكرة")
    q.add_argument("--query", required=True)
    q.set_defaults(func=cmd_search)

    args = p.parse_args()
    # reject مش في القايمة: الطابور ملف حالة محلي، مفيش commit ولا push
    _needs_push = args.cmd in ("add", "approve", "revoke")
    if args.cmd == "add":
        # بند 3.3: الكتابة (memory.md + git commit/push) بتتسلسل في طابور كتابة
        # واحد (flock) مشترك مع schedule.py وreminder_loop — منع سباقات الملف
        # وتصادم git index.lock بين محادثتين متوازيتين.
        with state_lock.write_lock():
            args.func(args)
    else:
        args.func(args)
    if _needs_push:
        _git_push_async()   # بره القفل — الشبكة مش بتحجز الطابور


if __name__ == "__main__":
    main()
