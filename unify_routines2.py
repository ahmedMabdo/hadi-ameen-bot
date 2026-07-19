#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بند 8.2 — التوحيد الكامل بتغيير محسوب (ترحيل لمرة واحدة).

المحاولة الميكانيكية البحتة وقفت عند 3 سطور، لأن كل الدوال المكررة بتنادي
`log` و`resolve_guild_id` — ودول مش متطابقين. القياس الفعلي للفرق:

  log               الفرق **بادئة اللوج بس**: FOLLOWUP / PODAILY / MARSTEAM
  resolve_guild_id  marsteam و followup متطابقين بالحرف؛ podaily **ناقصه**
                    حارس `if len(guilds) == 0` (بيرجع None برسالة واضحة).

القرارات المتخدة (وده اللي بيخليه «تغيير محسوب» مش نسخ):
  1) اللوج بيتحول لـ prefix على مستوى المكتبة، وكل سكربت بيضبط بادئته عند
     الاستيراد → **مخرجات اللوج بتفضل مطابقة بالحرف**.
  2) النسخة الأشمل من resolve_guild_id (marsteam/followup — 2 من 3) هي القياسية،
     و podaily بياخد الحارس الناقص. ده **إصلاح**: قبل كده لو البوت مش عضو في أي
     guild كان بيكمل على list فاضية بدل ما يقف برسالة مفهومة.

التحقق: أسماء محفوظة + compile + تنفيذ المكتبة + مقارنة `fetch` قبل/بعد.

الاستخدام:
    unify_routines2.py            # تحليل بس
    unify_routines2.py --apply
"""
import argparse
import ast
import py_compile
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

BASE = Path.home() / "hadi-ameen-bot"
FILES = ["discord_followup.py", "discord_podaily.py", "discord_marsteam.py"]
CANONICAL_SOURCE = "discord_marsteam.py"  # النسخة الأشمل من resolve_guild_id
COMMON = BASE / "routines_common.py"

HEADER = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مكتبة الروتينات المشتركة (بند 8.2) — مصدر واحد للكود المتكرر.

مولَّدة بـ unify_routines2.py من السورس الأصلي لسكربتات الروتين. كانت الدوال دي
متكررة حرفيًا في 3 سكربتات (followup / podaily / marsteam) = ~240 سطر صيانة مكررة.

**بادئة اللوج:** كل سكربت بينادي `set_prefix("PODAILY")` وهكذا عند الاستيراد،
فمخرجات stderr بتفضل زي ما كانت بالظبط.

**resolve_guild_id:** النسخة المعتمدة هنا هي بتاعة marsteam/followup (المتطابقين)
اللي فيها حارس «البوت مش عضو في أي guild» — podaily كان ناقصه الحارس ده وبقى عنده.

أي تعديل هنا بيأثر على الروتينات الثلاثة: شغّل `fetch` لكل واحد وقارن قبل/بعد.
"""
'''

LOG_BLOCK = '''# بادئة اللوج لكل روتين — بتتضبط من السكربت المستورد (بند 8.2)
PREFIX = "ROUTINE"


def set_prefix(name: str) -> None:
    """بيحدد بادئة اللوج (FOLLOWUP / PODAILY / MARSTEAM) — نفس المخرجات القديمة."""
    global PREFIX
    PREFIX = name


def log(msg: str) -> None:
    print(f"{PREFIX}: {msg}", file=sys.stderr)
'''


def norm(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def parse_file(path: Path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    funcs = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[node.name] = (norm(ast.get_source_segment(src, node)), node)
    return src, tree, funcs


def free_globals(source: str) -> set:
    tree = ast.parse(source)
    loaded, assigned = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            (loaded if isinstance(node.ctx, ast.Load) else assigned).add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assigned.add(node.name)
            args = node.args
            for arg in [*args.args, *args.kwonlyargs, *args.posonlyargs]:
                assigned.add(arg.arg)
            if args.vararg:
                assigned.add(args.vararg.arg)
            if args.kwarg:
                assigned.add(args.kwarg.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            assigned.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                assigned.add(alias.asname or alias.name.split(".")[0])
    return {n for n in loaded - assigned if not hasattr(__builtins__, n)}


def log_prefix_of(src: str) -> str:
    match = re.search(r'print\(f"([A-Z_]+): \{msg\}"', src)
    return match.group(1) if match else "ROUTINE"


def main():
    parser = argparse.ArgumentParser(description="توحيد روتينات هادي — تغيير محسوب (بند 8.2)")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    parsed = {}
    for name in FILES:
        path = BASE / name
        if not path.exists():
            sys.exit(f"ABORT: {name} مش موجود")
        parsed[name] = parse_file(path)

    # 1) الدوال المتطابقة في التلاتة + resolve_guild_id (النسخة القياسية)
    table = defaultdict(list)
    for name in FILES:
        for fname, (body, _) in parsed[name][2].items():
            table[(fname, body)].append(name)
    shared = {}
    for (fname, body), files in table.items():
        if len(files) == len(FILES) and fname not in ("log",):
            shared[fname] = body

    canonical_guild = parsed[CANONICAL_SOURCE][2].get("resolve_guild_id")
    if not canonical_guild:
        sys.exit("ABORT: resolve_guild_id مش موجودة في النسخة القياسية")
    shared["resolve_guild_id"] = canonical_guild[0]

    prefixes = {name: log_prefix_of(parsed[name][0]) for name in FILES}
    print("بادئات اللوج المكتشفة:", ", ".join(f"{k[8:-3]}={v}" for k, v in prefixes.items()))
    print(f"دوال هتتوحد ({len(shared)}): {', '.join(sorted(shared))}")
    changed = [n for n in FILES
               if parsed[n][2].get("resolve_guild_id", ("",))[0] != shared["resolve_guild_id"]]
    if changed:
        print(f"تغيير سلوك محسوب: {', '.join(c[8:-3] for c in changed)} هياخد حارس "
              "«البوت مش عضو في أي guild» من النسخة الأشمل")

    # 2) الاستيرادات والثوابت المطلوبة
    bodies = LOG_BLOCK + "\n\n" + "\n\n\n".join(shared[k] for k in sorted(shared))
    sample_src, sample_tree, _ = parsed[CANONICAL_SOURCE]
    import_lines, imported_names = [], set()
    for node in sample_tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = {a.asname or a.name.split(".")[0] for a in node.names}
            if names & free_globals(bodies) or "sys" in names:
                import_lines.append(ast.get_source_segment(sample_src, node))
                imported_names |= names
    needed = free_globals(bodies) - set(shared) - imported_names - {"PREFIX"}
    consts = []
    for node in sample_tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in needed:
                consts.append(ast.get_source_segment(sample_src, node))
                needed.discard(node.targets[0].id)
    if needed:
        sys.exit(f"ABORT: أسماء ناقصة: {sorted(needed)} — مفيش أي ملف اتغير")

    common_src = (HEADER + "\n" + "\n".join(import_lines) + "\n\n\n" +
                  ("\n".join(consts) + "\n\n\n" if consts else "") +
                  LOG_BLOCK + "\n\n" +
                  "\n\n\n".join(shared[k] for k in sorted(shared)) + "\n")

    namespace = {"__name__": "rc_check"}
    exec(compile(common_src, "routines_common.py", "exec"), namespace)  # noqa: S102
    for fname in [*shared, "log", "set_prefix"]:
        if fname not in namespace:
            sys.exit(f"ABORT: {fname} مش متعرّفة في المكتبة")
    print("MODULE EXEC OK")

    # 3) إعادة كتابة السكربتات
    results = {}
    for name in FILES:
        src, tree, funcs = parsed[name]
        removing = [f for f in [*shared, "log"] if f in funcs]
        lines = src.splitlines(keepends=True)
        drop = set()
        for fname in removing:
            node = funcs[fname][1]
            for i in range(node.lineno - 1, node.end_lineno):
                drop.add(i)
        body_lines = [l for i, l in enumerate(lines) if i not in drop]
        insert_at = 0
        for i, line in enumerate(body_lines[:60]):
            if line.startswith(("import ", "from ")):
                insert_at = i + 1
        block = (
            "\n# بند 8.2: الكود ده كان متكرر في الروتينات التلاتة — مصدر واحد دلوقتي\n"
            "import routines_common\n"
            f"from routines_common import log, {', '.join(sorted(shared))}\n\n"
            f'routines_common.set_prefix("{prefixes[name]}")  # اللوج يفضل زي ما هو\n'
        )
        body_lines.insert(insert_at, block)
        new_src = "".join(body_lines)

        old_names = set(funcs)
        new_tree = ast.parse(new_src)
        new_names = {n.name for n in new_tree.body
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for node in new_tree.body:
            if isinstance(node, ast.ImportFrom):
                new_names |= {a.asname or a.name for a in node.names}
        missing = old_names - new_names
        if missing:
            sys.exit(f"ABORT: {name} — أسماء ضاعت: {missing}")
        results[name] = new_src
        print(f"  {name}: -{len(src.splitlines()) - len(new_src.splitlines())} سطر "
              f"({len(removing)} دالة)")

    tmp = Path(tempfile.mkdtemp(prefix="unify2_"))
    (tmp / "routines_common.py").write_text(common_src, encoding="utf-8")
    py_compile.compile(str(tmp / "routines_common.py"), doraise=True)
    for name, new_src in results.items():
        (tmp / name).write_text(new_src, encoding="utf-8")
        py_compile.compile(str(tmp / name), doraise=True)
    print("PY_COMPILE OK (نسخ مؤقتة)")

    if not args.apply:
        print("\nتحليل بس — مفيش أي ملف اتغير. للتنفيذ: unify_routines2.py --apply")
        return

    COMMON.write_text(common_src, encoding="utf-8")
    for name, new_src in results.items():
        (BASE / name).write_text(new_src, encoding="utf-8")
    total = sum(len(parsed[n][0].splitlines()) - len(s.splitlines()) for n, s in results.items())
    print(f"\nAPPLIED — {len(shared) + 1} دالة اتوحدت، {total} سطر مكرر اتشال.")
    print("دلوقتي: قارن مخرجات fetch قبل/بعد قبل أي commit.")


if __name__ == "__main__":
    main()
