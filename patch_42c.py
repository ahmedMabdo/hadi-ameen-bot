#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بند 4.2 مرحلة ج + RAG — ربط knowledge_store بالبوت وبتعليمات هادي.

نفس المنهج: تحقق كامل من الـ anchors قبل أي كتابة، ثم py_compile.
"""
import py_compile
import sys
from pathlib import Path

BASE = Path.home() / "hadi-ameen-bot"

PATCHES = {
    "discord_bot.py": [
        (
            '    print(f"HADI ENGINE: {hadi_engine.describe()}")\n',
            '    print(f"HADI ENGINE: {hadi_engine.describe()}")\n'
            "    try:  # بند 4.2 (RAG): يعيد بناء فهرس /knowledge بس لو الملفات اتغيرت\n"
            "        import knowledge_store\n"
            '        print(f"HADI KNOWLEDGE: {knowledge_store.ensure_fresh()}")\n'
            "    except Exception as error:\n"
            '        print(f"HADI KNOWLEDGE: الفهرس مش شغال ({type(error).__name__}: {error})"\n'
            '              " — هادي هيقرا ملفات المعرفة كاملة زي الأول")\n',
        ),
    ],
}

APPENDS = [
    (
        ".gitignore",
        "knowledge_index.db",
        "\n# فهرس قاعدة المعرفة (بند 4.2 RAG) — مشتق من ملفات knowledge/، بيتبني بـ rebuild\n"
        "knowledge/knowledge_index.db\n"
        "knowledge/knowledge_index.db-wal\n"
        "knowledge/knowledge_index.db-shm\n",
    ),
    (
        ".env.example",
        "HADI_RAG_TOP_K",
        "\n# --- بند 4.2 — RAG على قاعدة المعرفة (اختياري) ---\n"
        "# عدد المقاطع اللي بترجع مع كل بحث (افتراضي 4)\n"
        "HADI_RAG_TOP_K=\n"
        "# الحجم المستهدف للمقطع بالحروف (افتراضي 900)\n"
        "HADI_RAG_CHUNK=\n",
    ),
    (
        "CLAUDE.md",
        "## قاعدة المعرفة — ابحث، متقراش الملف كامل",
        "\n---\n\n"
        "## قاعدة المعرفة — ابحث، متقراش الملف كامل\n\n"
        "ملفات `knowledge/` (مرجع القيود المحاسبية في الـ ERP، مراحل الدورة المحاسبية، "
        "فلو Robo Call، توثيق Order Complaint وItems Replacement) **مفهرسة مقاطع**. "
        "لأي سؤال محاسبي أو عن فيتشر موثّق:\n\n"
        "```bash\n"
        "python3 knowledge_store.py search --query \"سؤال المستخدم بالنص\"\n"
        "python3 knowledge_store.py get --id 42     # لو محتاج المقطع كامل\n"
        "```\n\n"
        "**القاعدة:** ابدأ بالبحث ده قبل ما تفتح أي ملف في `knowledge/` بالـ Read. "
        "اقرا الملف كامل بس لو البحث رجع فاضي أو المقاطع مش مغطية السؤال.\n\n"
        "**في ردك:** قول المصدر (اسم الملف + العنوان) زي ما بترجعه الأداة — "
        "ولو المعلومة مش موجودة في المقاطع، قول كده صراحة بدل ما تفترض.\n\n"
        "**الذاكرة:** `memory.py` (الحفظ والبحث) — وسّم اللي ليه تاريخ انتهاء بـ "
        "`--expires YYYY-MM-DD` واللي قاعدة سلوك بـ `--type procedural`.\n",
    ),
    (
        "MIGRATION_SDK.md",
        "## بند 4.2 — مرحلة ج + RAG",
        "\n---\n\n"
        "## بند 4.2 — مرحلة ج + RAG على /knowledge\n\n"
        "| المكوّن | الدور |\n"
        "|---------|-------|\n"
        "| `knowledge_store.py` (جديد) | فهرسة مقاطع لملفات `knowledge/` (docx بـ zipfile من stdlib + txt/md) في FTS5 بنفس التطبيع العربي؛ `search` / `get` / `rebuild` / `status` / `selftest` |\n"
        "| `memory_maintenance.py` (جديد) | صيانة شهرية: منتهي / مكرر / محتاج مراجعة → اقتراح للمراجعة البشرية (dry-run افتراضي)، و`apply --yes` **بيأرشف مش بيمسح** |\n"
        "| `discord_bot.py` | عند الإقلاع: `ensure_fresh()` بيعيد بناء الفهرس بس لو ملفات المعرفة اتغيرت — سطر `HADI KNOWLEDGE:` في اللوج |\n"
        "| `CLAUDE.md` | قاعدة صريحة: ابحث في المقاطع قبل قراءة أي ملف معرفة كامل، واذكر المصدر |\n\n"
        "**الأمان:** الفهرسان (`memory_index.db` و`knowledge_index.db`) حالة مشتقة في `.gitignore` — "
        "الملفات الأصلية وgit هما مصدر الحقيقة. الصيانة عمرها ما بتحذف: بتنقل لـ "
        "`knowledge/memory_archive.md` وبتعمل commit، فالتراجع `git revert` واحد.\n\n"
        "**التشغيل الشهري (اختياري):** `0 9 1 * * cd ~/hadi-ameen-bot && .venv/bin/python "
        "memory_maintenance.py review --write-report` — التقرير بس، والتنفيذ بعد المراجعة.\n\n"
        "**Rollback:** شيل بلوك `knowledge_store` من `on_ready` — الفهرس مالوش أي أثر على السلوك، "
        "وهادي بيرجع يقرا الملفات كاملة زي الأول.\n",
    ),
]


def main():
    problems, sources = [], {}
    for fname, pairs in PATCHES.items():
        path = BASE / fname
        if not path.exists():
            problems.append(f"{fname}: مش موجود")
            continue
        src = path.read_text(encoding="utf-8")
        sources[fname] = src
        for i, (old, _new) in enumerate(pairs, 1):
            n = src.count(old)
            if n != 1:
                problems.append(f"{fname} anchor#{i}: count={n} (المطلوب 1)")
    for req in ("knowledge_store.py", "memory_maintenance.py", "memory_store.py", "state_lock.py"):
        if not (BASE / req).exists():
            problems.append(f"{req}: انسخه للريبو الأول")
    if problems:
        print("ABORT — مفيش أي ملف اتلمس:")
        for p in problems:
            print("  -", p)
        sys.exit(1)

    for fname, pairs in PATCHES.items():
        src = sources[fname]
        for old, new in pairs:
            src = src.replace(old, new)
        (BASE / fname).write_text(src, encoding="utf-8")
        print(f"PATCHED {fname} ({len(pairs)} تعديل)")

    for fname, marker, text in APPENDS:
        path = BASE / fname
        src = path.read_text(encoding="utf-8") if path.exists() else ""
        if marker in src:
            print(f"SKIP append {fname} (موجود قبل كده)")
            continue
        path.write_text(src.rstrip("\n") + "\n" + text, encoding="utf-8")
        print(f"APPENDED {fname}")

    for fname in ("knowledge_store.py", "memory_maintenance.py", "discord_bot.py"):
        py_compile.compile(str(BASE / fname), doraise=True)
    print("PY_COMPILE OK — بند 4.2 مرحلة ج + RAG اتطبقوا")


if __name__ == "__main__":
    main()
