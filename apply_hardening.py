#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يطبّق تحصين الذاكرة على memory.py و memory_store.py و CLAUDE.md.
بيتحقق من كل مرساة قبل ما يعدّل — لو مرساة ناقصة بيقف من غير ما يغيّر حاجة."""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
edits = []
cache = {}


def patch(path, old, new, label):
    p = BASE / path
    t = cache.get(path)
    if t is None:
        t = p.read_text(encoding="utf-8")
    if new in t:
        cache[path] = t
        print(f"SKIP  {label} (متطبّق قبل كده)")
        return t, False
    if t.count(old) != 1:
        sys.exit(f"ABORT: المرساة '{label}' اتلقت {t.count(old)} مرة في {path} — متوقع 1")
    cache[path] = t.replace(old, new, 1)
    print(f"OK    {label}")
    return cache[path], True


# ---------------------------------------------------------- memory_store.py
patch("memory_store.py",
      '_META_RX = re.compile(\n'
      '    r"\\s*\\{type=(semantic|episodic|procedural)(?:\\s+expires=(\\d{4}-\\d{2}-\\d{2}))?\\}\\s*$"\n'
      ')',
      '# تحصين الذاكرة: الميتا بقت بتحمل كمان مصدر الملاحظة ومستوى الثقة.\n'
      '# الجروبات الاختيارية بتخلي السطور القديمة (من غير src/trust) تفضل تتقرا عادي.\n'
      '_META_RX = re.compile(\n'
      '    r"\\s*\\{type=(semantic|episodic|procedural)"\n'
      '    r"(?:\\s+expires=(\\d{4}-\\d{2}-\\d{2}))?"\n'
      '    r"(?:\\s+src=([^\\s{}]+))?"\n'
      '    r"(?:\\s+trust=(direct|forwarded|external))?"\n'
      '    r"\\}\\s*$"\n'
      ')',
      "memory_store: توسيع META_RX للمصدر والثقة")

patch("memory_store.py",
      '    mtype, expires = "semantic", ""\n'
      '    meta = _META_RX.search(body)\n'
      '    if meta:\n'
      '        mtype = meta.group(1)\n'
      '        expires = meta.group(2) or ""\n'
      '        body = body[: meta.start()].strip()\n'
      '    return {\n'
      '        "section": section, "mtype": mtype, "author": author,\n'
      '        "noted_at": noted_at, "expires": expires, "body": body,\n'
      '        "raw": raw.strip(), "norm": normalize(body),\n'
      '    }',
      '    mtype, expires, source, trust = "semantic", "", "", "direct"\n'
      '    meta = _META_RX.search(body)\n'
      '    if meta:\n'
      '        mtype = meta.group(1)\n'
      '        expires = meta.group(2) or ""\n'
      '        source = meta.group(3) or ""\n'
      '        trust = meta.group(4) or "direct"\n'
      '        body = body[: meta.start()].strip()\n'
      '    return {\n'
      '        "section": section, "mtype": mtype, "author": author,\n'
      '        "noted_at": noted_at, "expires": expires, "body": body,\n'
      '        "source": source, "trust": trust,\n'
      '        "raw": raw.strip(), "norm": normalize(body),\n'
      '    }',
      "memory_store: parse_line بيرجّع المصدر والثقة")

# ---------------------------------------------------------------- memory.py
patch("memory.py",
      "import state_lock",
      "import memory_guard  # تحصين الذاكرة ضد التسميم (OWASP ASI06)\nimport state_lock",
      "memory.py: استيراد الحارس")

patch("memory.py",
      'def _meta_suffix(mtype: str, expires: str) -> str:\n'
      '    """بند 4.2: وسم النوع/الصلاحية جوه السطر نفسه — الملف يفضل مصدر الحقيقة الوحيد."""\n'
      '    if mtype == "semantic" and not expires:\n'
      '        return ""\n'
      '    parts = [f"type={mtype}"]\n'
      '    if expires:\n'
      '        parts.append(f"expires={expires}")\n'
      '    return " {" + " ".join(parts) + "}"',
      'def _meta_suffix(mtype: str, expires: str, source: str = "",\n'
      '                 trust: str = "direct") -> str:\n'
      '    """بند 4.2 + تحصين الذاكرة: النوع/الصلاحية/المصدر/الثقة جوه السطر نفسه.\n'
      '    الملف يفضل مصدر الحقيقة الوحيد — الفهرس مشتق منه."""\n'
      '    return memory_guard.build_meta(mtype, expires, source, trust)',
      "memory.py: الميتا بقت من الحارس")

patch("memory.py",
      '    line = f"- [{_now()} — {author}] {args.text.strip()}{_meta_suffix(mtype, expires)}\\n"',
      '    # تحصين الذاكرة (1)(3): المصدر إجباري، والمنقول ممنوع يبقى قاعدة سلوك\n'
      '    try:\n'
      '        source = memory_guard.clean_source(getattr(args, "source", ""))\n'
      '        trust = memory_guard.validate_trust(getattr(args, "trust", "direct"))\n'
      '        memory_guard.enforce_policy(mtype, trust)\n'
      '    except memory_guard.GuardError as e:\n'
      '        sys.exit(str(e))\n'
      '\n'
      '    # تحصين الذاكرة (2): قواعد السلوك بتستنى موافقة بني آدم\n'
      '    if mtype == "procedural":\n'
      '        pid = memory_guard.queue_pending(args.text.strip(), author,\n'
      '                                         args.section, source, trust)\n'
      '        print(f"QUEUED [{pid}] قاعدة سلوك مستنية مراجعة بشرية — "\n'
      '              "مادخلتش الذاكرة.\\n"\n'
      '              "المراجعة: python3 memory.py pending  ثم  "\n'
      '              f"python3 memory.py approve --id {pid} --by \\"اسمك\\"")\n'
      '        return\n'
      '\n'
      '    line = f"- [{_now()} — {author}] {args.text.strip()}{_meta_suffix(mtype, expires, source, trust)}\\n"',
      "memory.py: بوابة procedural + المصدر")

# ---- أوامر جديدة قبل main()
patch("memory.py",
      "def main():",
      'def cmd_pending(args):\n'
      '    rows = memory_guard.load_pending()\n'
      '    if not rows:\n'
      '        print("الطابور فاضي — مفيش قواعد سلوك مستنية.")\n'
      '        return\n'
      '    print(f"# قواعد سلوك مستنية مراجعة ({len(rows)})\\n")\n'
      '    for r in rows:\n'
      '        print(f"[{r[\'id\']}] {r[\'text\']}")\n'
      '        print(f"      قالها: {r[\'author\']} | المصدر: {r[\'source\']} | "\n'
      '              f"الثقة: {r[\'trust\']} | الوقت: {r[\'queued_at\']}\\n")\n'
      '\n'
      '\n'
      'def cmd_approve(args):\n'
      '    try:\n'
      '        memory_guard.require_human("approve")\n'
      '        rec = memory_guard.drop_pending(args.pid)\n'
      '    except memory_guard.GuardError as e:\n'
      '        sys.exit(str(e))\n'
      '    by = (args.by or "").strip()\n'
      '    if not by:\n'
      '        sys.exit("ERROR: --by إجباري — مين اللي وافق؟")\n'
      '    _ensure()\n'
      '    header = SECTIONS.get(rec["section"], SECTIONS["general"])\n'
      '    meta = _meta_suffix("procedural", "", rec["source"], rec["trust"])\n'
      '    line = (f"- [{_now()} — {rec[\'author\']}] {rec[\'text\']}"\n'
      '            f" (وافق: {by}){meta}\\n")\n'
      '    text = MEM.read_text(encoding="utf-8")\n'
      '    if header in text:\n'
      '        idx = text.index(header)\n'
      '        nl = text.index("\\n", idx) + 1\n'
      '        while nl < len(text) and text[nl] == "\\n":\n'
      '            nl += 1\n'
      '        tail = text[nl:]\n'
      '        sep = "\\n" if tail.startswith("#") else ""\n'
      '        text = text[:nl] + line + sep + tail\n'
      '    else:\n'
      '        text += f"\\n{header}\\n\\n{line}"\n'
      '    MEM.write_text(text, encoding="utf-8")\n'
      '    print(f"APPROVED [{args.pid}] بواسطة {by}: {rec[\'text\']}")\n'
      '    _git_persist(f"memory: procedural rule approved by {by}")\n'
      '    _index_note(line, rec["section"])\n'
      '\n'
      '\n'
      'def cmd_revoke(args):\n'
      '    try:\n'
      '        memory_guard.require_human("revoke")\n'
      '        _ensure()\n'
      '        n = memory_guard.revoke_lines(args.match, args.by, args.reason)\n'
      '    except memory_guard.GuardError as e:\n'
      '        sys.exit(str(e))\n'
      '    print(f"REVOKED {n} سطر — اتنقلوا لقسم «مسحوبة».")\n'
      '    _git_persist(f"memory: revoke {n} note(s) by {args.by or \'unknown\'}")\n'
      '    try:\n'
      '        import memory_store\n'
      '        memory_store.rebuild()\n'
      '        print("REBUILT (memory_index.db)")\n'
      '    except Exception as e:\n'
      '        print(f"WARN: إعادة بناء الفهرس فشلت ({type(e).__name__}) — "\n'
      '              "شغّل: python3 memory_store.py rebuild")\n'
      '\n'
      '\n'
      'def cmd_diff(args):\n'
      '    try:\n'
      '        print(memory_guard.memory_diff(args.days))\n'
      '    except memory_guard.GuardError as e:\n'
      '        sys.exit(str(e))\n'
      '\n'
      '\n'
      'def main():',
      "memory.py: أوامر pending/approve/revoke/diff")

patch("memory.py",
      '    a.add_argument("--author", default="")',
      '    a.add_argument("--author", default="")\n'
      '    a.add_argument("--source", default="",\n'
      '                   help="تحصين الذاكرة (1): إجباري — الملاحظة جاية منين "\n'
      '                        "(مثال: discord:#mars-team أو dm:asser)")\n'
      '    a.add_argument("--trust", default="direct",\n'
      '                   choices=list(memory_guard.TRUST_LEVELS),\n'
      '                   help="تحصين الذاكرة (3): مصدر الكلام — direct لعضو "\n'
      '                        "في الفريق، forwarded/external لمحتوى منقول")',
      "memory.py: وسايط --source و --trust")

patch("memory.py",
      '    q = sub.add_parser("search", help="دوّر في الذاكرة")\n'
      '    q.add_argument("--query", required=True)',
      '    pn = sub.add_parser("pending", help="اعرض قواعد السلوك المستنية مراجعة")\n'
      '    pn.set_defaults(func=cmd_pending)\n'
      '\n'
      '    ap = sub.add_parser("approve", help="وافق على قاعدة سلوك (بني آدم بس)")\n'
      '    ap.add_argument("--id", dest="pid", required=True)\n'
      '    ap.add_argument("--by", required=True, help="مين اللي وافق")\n'
      '    ap.set_defaults(func=cmd_approve)\n'
      '\n'
      '    rv = sub.add_parser("revoke", help="اسحب ملاحظة من الذاكرة (بني آدم بس)")\n'
      '    rv.add_argument("--match", required=True, help="نص موجود في السطر")\n'
      '    rv.add_argument("--by", default="", help="مين اللي سحبها")\n'
      '    rv.add_argument("--reason", default="", help="السبب")\n'
      '    rv.set_defaults(func=cmd_revoke)\n'
      '\n'
      '    df = sub.add_parser("diff", help="إيه اللي اتغير في الذاكرة بالفترة")\n'
      '    df.add_argument("--days", type=int, default=7)\n'
      '    df.set_defaults(func=cmd_diff)\n'
      '\n'
      '    q = sub.add_parser("search", help="دوّر في الذاكرة")\n'
      '    q.add_argument("--query", required=True)',
      "memory.py: تسجيل الأوامر الجديدة")

for path, t in cache.items():
    (BASE / path).write_text(t, encoding="utf-8")
print(f"\nتم تطبيق {len(cache)} تعديل.")
