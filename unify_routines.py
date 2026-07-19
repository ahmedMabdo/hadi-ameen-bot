#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بند 8.2 — توحيد الروتينات الأربعة على مكتبة مشتركة (ترحيل لمرة واحدة).

الخطر في أي refactor للسكربتات دي إن الجدولة برّه السيرفر — لو السلوك اتغير،
هنكتشف بكرة الصبح لما التقرير ميجيش. عشان كده السكربت ده **مابيكتبش كود من دماغه**:

  1) بيقرا الأربع سكربتات بـ ast ويطلع سورس كل دالة.
  2) الدالة تتنقل للمكتبة **بس** لو نسختها متطابقة حرفيًا في 3 ملفات أو أكتر
     (بعد تطبيع المسافات في آخر السطر). أي اختلاف = تفضل مكانها.
  3) بيبني routines_common.py من **نفس السورس الأصلي** (نسخ، مش إعادة كتابة).
  4) بيشيل النسخ المكررة ويحط import، ثم يتحقق إن كل اسم كان متعرّف في الملف
     لسه متاح (معرَّف أو مستورد)، وإن الملف بيتكومبايل.

أي خطوة تفشل → مفيش أي ملف بيتلمس (بيشتغل على نسخة في الذاكرة ويكتب في الآخر).

الاستخدام:
    unify_routines.py --check     # تحليل بس: إيه اللي هيتنقل (مفيش كتابة)
    unify_routines.py --apply
"""
import argparse
import ast
import py_compile
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

BASE = Path.home() / "hadi-ameen-bot"
FILES = ["discord_followup.py", "discord_orderpo.py", "discord_podaily.py", "discord_marsteam.py"]
COMMON = BASE / "routines_common.py"
MIN_COPIES = 3  # الدالة لازم تكون مكررة في 3 ملفات على الأقل عشان تتنقل

HEADER = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مكتبة الروتينات المشتركة (بند 8.2) — مصدر واحد للكود المتكرر.

الملف ده **مولَّد من السورس الأصلي** بـ unify_routines.py: كل دالة هنا كانت
متطابقة حرفيًا في 3 سكربتات روتين أو أكتر (followup / orderpo / podaily /
marsteam)، فاتنقلت مرة واحدة بدل ما تتصان في أربع نسخ.

اللي **مااتنقلش** عن قصد: أي دالة نسختها مختلفة بين السكربتات — التوحيد
بيتم بالتطابق الحرفي بس، مفيش إعادة كتابة سلوك.

بعد أي تعديل هنا: شغّل الروتينات بـ --dry-run وقارن قبل/بعد.
"""
'''


def load(path: Path):
    src = path.read_text(encoding="utf-8")
    return src, ast.parse(src)


def norm(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def collect(paths):
    """{(اسم, سورس منظّم): [ملفات]} لكل دالة top-level."""
    table = defaultdict(list)
    per_file = {}
    for path in paths:
        src, tree = load(path)
        funcs = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                segment = ast.get_source_segment(src, node)
                if segment:
                    funcs[node.name] = (norm(segment), node)
                    table[(node.name, norm(segment))].append(path.name)
        per_file[path.name] = (src, tree, funcs)
    return table, per_file


def shared_functions(table):
    out = {}
    for (name, body), files in table.items():
        if len(files) >= MIN_COPIES:
            # لو نفس الاسم ليه أكتر من نسخة مشتركة (نادر) — نتخطاه بدل ما نخمّن
            if name in out:
                out[name] = None
            else:
                out[name] = (body, files)
    return {k: v for k, v in out.items() if v}


def free_globals(source: str) -> set:
    """الأسماء العامة اللي الكود بيقراها (مش معرّفة جواه ولا builtins)."""
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
    return {n for n in loaded - assigned if n not in dir(__builtins__) and not hasattr(__builtins__, n)}


def shared_constants(paths, per_file, needed: set):
    """ثوابت module-level متطابقة في نفس الملفات ومحتاجة للدوال المنقولة.

    ده اللي اتكسر في المحاولة الأولى: api_get بتستخدم API_BASE، والثابت مااتنقلش.
    """
    table = defaultdict(list)
    for name in FILES:
        src, tree, _ = per_file[name]
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                target = node.targets[0].id
                if target in needed:
                    table[(target, norm(ast.get_source_segment(src, node)))].append(name)
    out = {}
    for (target, body), files in table.items():
        if len(files) >= MIN_COPIES:
            out[target] = out.get(target) or body
    return out


def needed_imports(bodies: str, src_sample: str) -> str:
    """يجيب سطور الاستيراد اللي الدوال المنقولة محتاجاها من ملف مرجعي."""
    tree = ast.parse(src_sample)
    lines = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            segment = ast.get_source_segment(src_sample, node)
            names = [a.asname or a.name.split(".")[0] for a in node.names]
            if any(n and n in bodies for n in names):
                lines.append(segment)
    return "\n".join(lines)


def build_common(shared, per_file, paths):
    """بيبني المكتبة — وبيتحقق إن كل اسم عام محتاجه الكود المنقول موجود فعلًا.

    لو أي اسم ناقص → استثناء وإجهاض كامل، بدل ما نكتشف NameError في الإنتاج بكرة.
    """
    ordered = sorted(shared.items(), key=lambda kv: kv[0])
    bodies = "\n\n\n".join(body for _, (body, _) in ordered)
    sample = per_file["discord_podaily.py"][0]
    imports = needed_imports(bodies, sample)

    imported_names = set()
    for node in ast.parse(imports or "pass").body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imported_names |= {a.asname or a.name.split(".")[0] for a in node.names}

    moved_names = {name for name, _ in ordered}
    needed = free_globals(bodies) - moved_names - imported_names
    constants = shared_constants(paths, per_file, needed)
    missing = needed - set(constants)
    if missing:
        raise RuntimeError(
            "أسماء عامة محتاجة ومش متاحة في المكتبة: " + ", ".join(sorted(missing)) +
            " — الترحيل اتوقف (مفيش أي ملف اتغير).")

    const_block = "\n".join(constants[k] for k in sorted(constants))
    note = "\n".join(
        f"#   {name:22} (كان مكرر في {len(files)} ملفات)" for name, (_, files) in ordered)
    const_note = ("\n# ثوابت منقولة معاها: " + ", ".join(sorted(constants))) if constants else ""
    return (f"{HEADER}\n{imports}\n\n# الدوال المنقولة:\n{note}{const_note}\n\n\n"
            f"{const_block}\n\n\n{bodies}\n"), set(constants)


def rewrite_file(name, src, tree, funcs, shared):
    """يشيل الدوال المتطابقة ويحط import — وبيتأكد إن مفيش اسم ضاع."""
    moving = [n for n in funcs if n in shared and funcs[n][0] == shared[n][0]]
    if not moving:
        return None, []
    lines = src.splitlines(keepends=True)
    drop = set()
    for n in moving:
        node = funcs[n][1]
        start = node.lineno - 1
        if node.decorator_list:
            start = min(d.lineno for d in node.decorator_list) - 1
        for i in range(start, node.end_lineno):
            drop.add(i)
    kept = [line for i, line in enumerate(lines) if i not in drop]
    body = "".join(kept)

    # حط الاستيراد بعد آخر سطر import في أول 60 سطر
    body_lines = body.splitlines(keepends=True)
    insert_at = 0
    for i, line in enumerate(body_lines[:60]):
        if line.startswith(("import ", "from ")):
            insert_at = i + 1
    imported = ", ".join(sorted(moving))
    import_line = (
        f"\n# بند 8.2: الدوال دي كانت متكررة حرفيًا في باقي الروتينات — مصدر واحد دلوقتي\n"
        f"from routines_common import {imported}\n"
    )
    body_lines.insert(insert_at, import_line)
    new_src = "".join(body_lines)

    # تحقق: كل اسم كان متعرّف لسه متاح
    old_names = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    new_tree = ast.parse(new_src)
    new_names = {n.name for n in new_tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for node in new_tree.body:
        if isinstance(node, ast.ImportFrom):
            new_names |= {a.asname or a.name for a in node.names}
    missing = old_names - new_names
    if missing:
        raise RuntimeError(f"{name}: أسماء ضاعت بعد النقل: {missing}")
    return new_src, moving


def main():
    parser = argparse.ArgumentParser(description="توحيد روتينات هادي (بند 8.2)")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    paths = [BASE / f for f in FILES]
    for p in paths:
        if not p.exists():
            sys.exit(f"ABORT: {p.name} مش موجود")

    table, per_file = collect(paths)
    shared = shared_functions(table)
    if not shared:
        sys.exit("مفيش دوال متطابقة في 3 ملفات أو أكتر — مفيش حاجة تتوحد.")

    print(f"دوال هتتنقل للمكتبة ({len(shared)}):")
    for name, (_, files) in sorted(shared.items()):
        print(f"  {name:24} ← {len(files)} ملفات")

    common_src, consts = build_common(shared, per_file, paths)
    if consts:
        print(f"ثوابت اتنسخت معاها: {', '.join(sorted(consts))}")
    # تشغيل المكتبة فعليًا (تعريفات وثوابت بس — مفيش شبكة) لكشف أي اسم ناقص
    namespace = {"__name__": "routines_common_check"}
    exec(compile(common_src, "routines_common.py", "exec"), namespace)  # noqa: S102
    for name in shared:
        if name not in namespace:
            sys.exit(f"ABORT: {name} مش متعرّفة في المكتبة بعد التنفيذ")
    print("MODULE EXEC OK (كل الأسماء متاحة)")
    results = {}
    for name in FILES:
        src, tree, funcs = per_file[name]
        new_src, moved = rewrite_file(name, src, tree, funcs, shared)
        if new_src:
            results[name] = new_src
            saved = len(src.splitlines()) - len(new_src.splitlines())
            print(f"  {name}: -{saved} سطر ({len(moved)} دالة)")

    # فحص التكوين على ملفات مؤقتة قبل أي كتابة حقيقية
    tmp = Path(tempfile.mkdtemp(prefix="unify_check_"))
    (tmp / "routines_common.py").write_text(common_src, encoding="utf-8")
    py_compile.compile(str(tmp / "routines_common.py"), doraise=True)
    for name, new_src in results.items():
        (tmp / name).write_text(new_src, encoding="utf-8")
        py_compile.compile(str(tmp / name), doraise=True)
    print("\nPY_COMPILE OK (على نسخ مؤقتة)")

    if not args.apply:
        print("\n--check فقط: مفيش أي ملف اتغير. للتنفيذ: unify_routines.py --apply")
        return

    COMMON.write_text(common_src, encoding="utf-8")
    for name, new_src in results.items():
        (BASE / name).write_text(new_src, encoding="utf-8")
    for name in list(results) + ["routines_common.py"]:
        py_compile.compile(str(BASE / name), doraise=True)
    total = sum(len(per_file[n][0].splitlines()) - len(s.splitlines()) for n, s in results.items())
    print(f"\nAPPLIED — {len(shared)} دالة اتوحدت، {total} سطر مكرر اتشال.")


if __name__ == "__main__":
    main()
