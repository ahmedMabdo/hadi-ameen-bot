#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بند 8.1/8.3 — ربط النبضة بالبوت (حلقة كل ساعة + DM لآسر). تحقق كامل قبل أي كتابة."""
import py_compile
import sys
from pathlib import Path

BASE = Path.home() / "hadi-ameen-bot"

HEARTBEAT_LOOP = '''@tasks.loop(hours=1)
async def heartbeat_loop():
    """بند 8.1/8.3 — نبضة الاستباقية: فحوصات مجدولة، والصمت لو مفيش حاجة.

    نفس فلسفة NO_REPLY: تنبيه من غير داعي أسوأ من مفيش تنبيه، لأنه بيخلي الفريق
    يتجاهل التنبيهات كلها. الضوابط (cooldown / ساعات الهدوء / حد أقصى للتنبيهات)
    كلها جوه heartbeat.py وقابلة للضبط من .env."""
    if not heartbeat.ENABLED:
        return
    if heartbeat.in_quiet_hours():
        return
    try:
        alerts, _ = await asyncio.to_thread(heartbeat.run_checks, None, False)
    except Exception as error:
        print(f"HEARTBEAT FAIL: {type(error).__name__}: {error}")
        return
    if not alerts:
        return  # الصمت قرار مصمم
    message = heartbeat.format_message(alerts)
    print(f"HEARTBEAT: {len(alerts)} تنبيه — {[a['key'] for a in alerts]}")
    await dm_allowed_users(message)


@heartbeat_loop.before_loop
async def _before_heartbeat_loop():
    await client.wait_until_ready()


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
'''

PATCHES = {
    "discord_bot.py": [
        ("import eval_store  # بند 5.3 — تسجيل نتيجة كل تفاعل + تقييم الرياكشنز\n",
         "import eval_store  # بند 5.3 — تسجيل نتيجة كل تفاعل + تقييم الرياكشنز\n"
         "import heartbeat  # بند 8.1/8.3 — الفحوصات الاستباقية والأحداث\n"),

        ("@client.event\nasync def on_raw_reaction_add(payload: discord.RawReactionActionEvent):\n",
         HEARTBEAT_LOOP),

        ("    if not pending_tickets_loop.is_running():\n        pending_tickets_loop.start()\n",
         "    if not pending_tickets_loop.is_running():\n        pending_tickets_loop.start()\n"
         "    if heartbeat.ENABLED and not heartbeat_loop.is_running():  # بند 8.1\n"
         "        heartbeat_loop.start()\n"
         "    print(f\"HADI HEARTBEAT: {'on' if heartbeat.ENABLED else 'off'}\"\n"
         "          f\" (كل ساعة | هدوء {heartbeat.QUIET_START}:00-{heartbeat.QUIET_END}:00\"\n"
         "          f\" | cooldown {heartbeat.COOLDOWN_H:g}س | حد أقصى {heartbeat.MAX_ALERTS} تنبيهات)\")\n"),
    ],
}

APPENDS = [
    (".gitignore", "heartbeat_state.json",
     "\n# حالة النبضة (بند 8.1) — آخر تنبيه لكل عنصر. حالة تشغيل محلية\n"
     "logs/heartbeat_state.json\nlogs/heartbeat_state.json.tmp\n"),
    (".env.example", "HADI_HEARTBEAT",
     "\n# --- بند 8.1/8.3 — النبضة الاستباقية (الافتراضيات محافظة عمدًا) ---\n"
     "# off بيوقف النبضة بالكامل من غير تعديل كود\n"
     "HADI_HEARTBEAT=\n"
     "# تذكرة P0/P1 واقفة كام يوم من غير حركة تعتبر مهملة (افتراضي 3)\n"
     "HADI_HB_STALE_DAYS=\n"
     "# نقطة سابورت من غير رد كام ساعة (افتراضي 48)\n"
     "HADI_HB_SUPPORT_HOURS=\n"
     "# مايتكررش نفس التنبيه قبل كام ساعة (افتراضي 24)\n"
     "HADI_HB_COOLDOWN_HOURS=\n"
     "# ساعات الهدوء بتوقيت القاهرة — مفيش تنبيهات فيها (افتراضي 22 إلى 9)\n"
     "HADI_HB_QUIET_START=\nHADI_HB_QUIET_END=\n"
     "# أقصى عدد تنبيهات في النبضة الواحدة (افتراضي 3)\n"
     "HADI_HB_MAX_ALERTS=\n"),
    ("MIGRATION_SDK.md", "## المحور السادس — الاستباقية",
     "\n---\n\n## المحور السادس — الاستباقية (بنود 8.1 / 8.2 / 8.3)\n\n"
     "### 8.2 — توحيد الروتينات\n\n"
     "القياس قبل الشغل: `podaily` و`marsteam` كانوا بيشتركوا في **138 سطر جوهري متطابق**، "
     "و`followup` بيشترك 130-132 مع كل واحد فيهم. `routines_common.py` اتولّد بـ "
     "`unify_routines.py` اللي **بينقل الدالة بس لو نسختها متطابقة حرفيًا في 3 ملفات أو أكتر** — "
     "مفيش إعادة كتابة سلوك، ومفيش دالة مختلفة اتلمست.\n\n"
     "### 8.1 — النبضة (كل ساعة)\n\n"
     "| الفحص | العتبة الافتراضية |\n|-------|------------------|\n"
     "| تذكرة P0/P1 واقفة من غير حركة | 3 أيام |\n"
     "| سيكون بكرة (من `sprints.md`) | يوم واحد قدام |\n"
     "| نقطة سابورت من غير رد | 48 ساعة |\n\n"
     "**ضد الإزعاج:** cooldown 24 ساعة لكل عنصر • ساعات هدوء 22:00–09:00 القاهرة • "
     "حد أقصى 3 تنبيهات للنبضة • **الصمت الكامل لو مفيش حاجة** (نفس فلسفة NO_REPLY) • "
     "`HADI_HEARTBEAT=off` بيوقفها فورًا.\n\n"
     "**الوجهة دلوقتي:** DM للمصرح لهم بس — لحد ما العتبات تتظبط على أرض الواقع.\n\n"
     "### 8.3 — تقارير بالحدث\n\n"
     "يوم الريليز (من `sprints.md`) → يعرض يجهّز تقرير regression. "
     "Iteration جديد على ADO → يطلب مواعيد السيكونات عشان يحدّث `sprints.md`. "
     "أول تشغيل بيسجّل السبرنتات الموجودة من غير أي تنبيه (مفيش إغراق).\n\n"
     "**التجربة من غير إرسال:** `python3 heartbeat.py check` — بيطبع اللي كان هيتبعت. "
     "`python3 heartbeat.py state` بيوري آخر التنبيهات.\n\n"
     "**Rollback:** `HADI_HEARTBEAT=off` في `.env` + restart. للكود: شيل بلوك "
     "`heartbeat_loop` من `discord_bot.py`.\n"),
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
                problems.append(f"{fname} anchor#{i}: count={n} — {old.strip()[:60]}")
    for req in ("heartbeat.py", "routines_common.py"):
        if not (BASE / req).exists():
            problems.append(f"{req}: مش موجود (شغّل unify_routines.py --apply الأول)")
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

    for fname in ("heartbeat.py", "discord_bot.py", "routines_common.py"):
        py_compile.compile(str(BASE / fname), doraise=True)
    print("PY_COMPILE OK — بند 8.1/8.3 اتربطوا")


if __name__ == "__main__":
    main()
