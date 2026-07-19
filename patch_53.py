#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بند 5.3 — ربط حلقة التحسين بالبوت. تحقق كامل من الـ anchors قبل أي كتابة."""
import py_compile
import shutil
import sys
from pathlib import Path

BASE = Path.home() / "hadi-ameen-bot"
EVALS = BASE / "evals"

REACTION_HANDLERS = '''@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """بند 5.3: رياكشن على رد هادي = تقييم بشري مجاني (أرخص إشارة جودة متاحة).

    attach_feedback بيرجّع False لو الرسالة مش رد من ردود هادي المسجلة — فالرياكشنز
    على رسايل الناس العادية بتتجاهل لوحدها."""
    if client.user and payload.user_id == client.user.id:
        return
    if eval_store.attach_feedback(payload.message_id, str(payload.emoji), payload.user_id):
        print(f"EVAL FEEDBACK: {payload.emoji} على رد #{payload.message_id}")


@client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """شيل الرياكشن = سحب التقييم."""
    if client.user and payload.user_id == client.user.id:
        return
    eval_store.remove_feedback(payload.message_id, str(payload.emoji), payload.user_id)


@client.event
async def on_message(message: discord.Message):
'''

RECORD_ARGS = (
    "                conv_key=conv_key,\n"
    "                channel=channel_label,\n"
    "                author=author_name,\n"
    "                user_message_id=message.id,\n"
    "                prompt=content,\n"
    "                latency_ms=int((time.time() - _t0) * 1000),\n"
    "                stats=eval_stats,\n"
    "                engine=hadi_engine.describe().split()[0],\n"
)

PATCHES = {
    "discord_bot.py": [
        # 1) استيراد المخزن
        ("import hadi_engine\nimport state_lock  # بند 3.3 — قفل الكتابة المشترك (flock) لملفات الحالة\n",
         "import hadi_engine\nimport state_lock  # بند 3.3 — قفل الكتابة المشترك (flock) لملفات الحالة\n"
         "import eval_store  # بند 5.3 — تسجيل نتيجة كل تفاعل + تقييم الرياكشنز\n"),

        # 2) send_long_message يرجّع أول رسالة (عشان نربط الرياكشن بالتفاعل)
        ("async def send_long_message(channel, text: str, reply_to: discord.Message = None) -> None:\n",
         "async def send_long_message(channel, text: str, reply_to: discord.Message = None):\n"),
        ("    for i, chunk in enumerate(chunks):\n"
         "        if i == 0 and reply_to is not None:\n"
         "            await reply_to.reply(chunk, mention_author=False)\n"
         "        else:\n"
         "            await channel.send(chunk)\n",
         "    first = None\n"
         "    for i, chunk in enumerate(chunks):\n"
         "        if i == 0 and reply_to is not None:\n"
         "            sent = await reply_to.reply(chunk, mention_author=False)\n"
         "        else:\n"
         "            sent = await channel.send(chunk)\n"
         "        if first is None:\n"
         "            first = sent\n"
         "    return first  # بند 5.3: id الرد بيربط التقييم بالتفاعل\n"),

        # 3) ask_claude بتمرّر stats للمحرك
        ('    conv_key: str = "",\n    on_progress=None,\n) -> str:\n',
         '    conv_key: str = "",\n    on_progress=None,\n    stats: dict | None = None,\n) -> str:\n'),
        ("    return await hadi_engine.run_agent(\n"
         "        prompt, conv_key=conv_key, timeout=480, on_progress=on_progress\n"
         "    )\n",
         "    return await hadi_engine.run_agent(\n"
         "        prompt, conv_key=conv_key, timeout=480, on_progress=on_progress, stats=stats\n"
         "    )\n"),

        # 4) هاندلرز الرياكشنز قبل on_message
        ("@client.event\nasync def on_message(message: discord.Message):\n", REACTION_HANDLERS),

        # 5) تجهيز الحاوية قبل التشغيل
        ("    conv_lock = get_conv_lock(conv_key)\n    status = StatusReporter(message)\n",
         "    conv_lock = get_conv_lock(conv_key)\n"
         "    status = StatusReporter(message)\n"
         "    eval_stats: dict = {}  # بند 5.3: المحرك بيملاها بالتوكنز والتكلفة\n"
         "    _t0 = time.time()\n"),

        # 6) تمرير stats في نداء ask_claude
        ("                    conv_key=conv_key,\n                    on_progress=status.on_engine_event,\n                )\n",
         "                    conv_key=conv_key,\n"
         "                    on_progress=status.on_engine_event,\n"
         "                    stats=eval_stats,\n"
         "                )\n"),

        # 7) تسجيل الصمت
        ('                print(f"HADI: NO_REPLY skip — {author_name}: {content[:80]}")\n                return\n',
         "                eval_store.record_interaction(\n" + RECORD_ARGS +
         '                outcome="no_reply",\n'
         "                )\n"
         '                print(f"HADI: NO_REPLY skip — {author_name}: {content[:80]}")\n'
         "                return\n"),

        # 8) تسجيل الرد الناجح
        ("            await send_long_message(\n"
         "                message.channel,\n"
         "                resp_clean,\n"
         "                reply_to=message if message.guild is not None else None,\n"
         "            )\n",
         "            sent = await send_long_message(\n"
         "                message.channel,\n"
         "                resp_clean,\n"
         "                reply_to=message if message.guild is not None else None,\n"
         "            )\n"
         "            eval_store.record_interaction(\n" + RECORD_ARGS +
         '                reply_message_id=getattr(sent, "id", ""),\n'
         "                reply=resp_clean,\n"
         '                outcome="replied",\n'
         "            )\n"),

        # 9) تسجيل المهلة
        ('        except hadi_engine.EngineTimeout:\n            print(f"HADI: TIMEOUT (480s) - {author_name}: {content[:60]}")\n',
         "        except hadi_engine.EngineTimeout:\n"
         "            eval_store.record_interaction(\n" + RECORD_ARGS +
         '                outcome="timeout",\n                error_type="EngineTimeout",\n'
         "            )\n"
         '            print(f"HADI: TIMEOUT (480s) - {author_name}: {content[:60]}")\n'),

        # 10) تسجيل الخطأ
        ('        except Exception as error:\n            print(f"ERROR: {type(error).__name__}: {error}")\n',
         "        except Exception as error:\n"
         "            eval_store.record_interaction(\n" + RECORD_ARGS +
         '                outcome="error",\n                error_type=type(error).__name__,\n'
         "            )\n"
         '            print(f"ERROR: {type(error).__name__}: {error}")\n'),

        # 11) main guard — عشان eval_runner يقدر يستورد الملف من غير ما يشغّل البوت
        ("client.run(TOKEN)\n",
         "if __name__ == \"__main__\":  # بند 5.3: الاستيراد من eval_runner مايشغلش البوت\n"
         "    client.run(TOKEN)\n"),
    ],
    "hadi_engine.py": [
        ("async def _run_sdk_once(prompt: str, conv_key: str, timeout: int, on_progress=None) -> str:\n",
         "async def _run_sdk_once(prompt: str, conv_key: str, timeout: int, on_progress=None, stats=None) -> str:\n"),
        ("    _log_usage(conv_key, resume_id, final)\n",
         "    _log_usage(conv_key, resume_id, final)\n"
         "    if stats is not None:  # بند 5.3: نفس الأرقام بتتسجل في مخزن التقييم\n"
         "        stats.update({\n"
         '            "cost": final.get("cost"), "usage": u, "num_turns": final.get("num_turns"),\n'
         '            "duration_ms": final.get("duration"), "resumed": bool(resume_id),\n'
         "        })\n"),
        ("async def _run_sdk(prompt: str, conv_key: str, timeout: int, on_progress=None) -> str:\n"
         "    try:\n"
         "        return await _run_sdk_once(prompt, conv_key, timeout, on_progress)\n",
         "async def _run_sdk(prompt: str, conv_key: str, timeout: int, on_progress=None, stats=None) -> str:\n"
         "    try:\n"
         "        return await _run_sdk_once(prompt, conv_key, timeout, on_progress, stats)\n"),
        ("            reset_session(conv_key)\n            return await _run_sdk_once(prompt, conv_key, timeout, on_progress)\n",
         "            reset_session(conv_key)\n            return await _run_sdk_once(prompt, conv_key, timeout, on_progress, stats)\n"),
        ("            await asyncio.sleep(5)\n            return await _run_sdk_once(prompt, conv_key, timeout, on_progress)\n",
         "            await asyncio.sleep(5)\n            return await _run_sdk_once(prompt, conv_key, timeout, on_progress, stats)\n"),
        ('async def run_agent(prompt: str, conv_key: str = "", timeout: int = 480, on_progress=None) -> str:\n',
         'async def run_agent(prompt: str, conv_key: str = "", timeout: int = 480, on_progress=None,\n'
         "                    stats: dict | None = None) -> str:\n"),
        ("                return await _run_sdk(prompt, conv_key, timeout, on_progress)\n",
         "                return await _run_sdk(prompt, conv_key, timeout, on_progress, stats)\n"),
    ],
}

APPENDS = [
    (".gitignore", "evals/runs/",
     "\n# نتايج تشغيل الـ suite والمراجعات (بند 5.3) — حالة تشغيل. الحالات نفسها (evals/cases.json) في git\n"
     "evals/runs/\nevals/baseline.json\nevals/review_*.md\n"),
    (".env.example", "HADI_EVAL_EXCERPT",
     "\n# --- بند 5.3 — حلقة التحسين (اختياري) ---\n"
     "# طول المقتطف المحفوظ من الطلب/الرد في مخزن التقييم (افتراضي 400 حرف)\n"
     "HADI_EVAL_EXCERPT=\n"),
    ("MIGRATION_SDK.md", "## بند 5.3",
     "\n---\n\n## بند 5.3 — حلقة التحسين المستمرة\n\n"
     "الحلقة: **تقييم حقيقي ← حالات في الـ suite ← قياس قبل/بعد**.\n\n"
     "| المكوّن | الدور |\n|---------|-------|\n"
     "| `eval_store.py` | صف لكل تفاعل (نتيجة/زمن/تكلفة/توكنز) + تقييم من رياكشنز الفريق على ردود هادي. مقتطفات 400 حرف بس، محلي وفي `.gitignore` |\n"
     "| `discord_bot.py` | `on_raw_reaction_add/remove` بيربطوا 👍/👎 بالتفاعل؛ وكل مسار (رد/صمت/خطأ/مهلة) بيتسجل |\n"
     "| `evals/cases.json` | 12 حالة ذهبية مبنية على أصعب السلوكيات: NO_REPLY، بروتوكول REACT، existing-ticket-first، قواعد النداء، الاستشهاد بالمعرفة، رفض تسريب `.env`، ومقاومة الحقن |\n"
     "| `eval_runner.py` | بيشغّل الحالات **بنفس `ask_claude`** بتاعة البوت (مش نسخة تانية) وبيطلع `run/baseline/diff` |\n"
     "| `weekly_review.py` | أسوأ التفاعلات + حالات مقترحة جاهزة للنسخ + مقارنة الـ suite بخط الأساس |\n\n"
     "**الروتين الأسبوعي:**\n\n"
     "```bash\n"
     "python3 weekly_review.py --days 7 --write-report   # (1) اقرا وقرر\n"
     "# (2) ضيف الحالات في evals/cases.json وعدّل التعليمات\n"
     "python3 eval_runner.py run && python3 eval_runner.py diff   # (3) اتقاس قبل/بعد\n"
     "```\n\n"
     "**تنبيه:** `eval_runner run` بيعمل تشغيلات Claude حقيقية (تكلفة) — ابدأ بـ `--limit`.\n"
     "`diff` بيرجّع exit code 1 لو في انحدار، فينفع يتحط في CI.\n\n"
     "**Rollback:** التسجيل best-effort ومالوش أي أثر على السلوك؛ لإيقافه بالكامل شيل "
     "`import eval_store` ونداءاته من `discord_bot.py`.\n"),
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
                problems.append(f"{fname} anchor#{i}: count={n} (المطلوب 1) — {old.strip()[:60]}")
    for req in ("eval_store.py", "eval_runner.py", "weekly_review.py"):
        if not (BASE / req).exists():
            problems.append(f"{req}: انسخه للريبو الأول")
    if not (BASE / "eval_cases.json").exists() and not (EVALS / "cases.json").exists():
        problems.append("eval_cases.json: مش موجود")
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

    EVALS.mkdir(exist_ok=True)
    root_cases = BASE / "eval_cases.json"
    if root_cases.exists():
        shutil.move(str(root_cases), str(EVALS / "cases.json"))
        print("MOVED eval_cases.json → evals/cases.json")

    for fname, marker, text in APPENDS:
        path = BASE / fname
        src = path.read_text(encoding="utf-8") if path.exists() else ""
        if marker in src:
            print(f"SKIP append {fname} (موجود قبل كده)")
            continue
        path.write_text(src.rstrip("\n") + "\n" + text, encoding="utf-8")
        print(f"APPENDED {fname}")

    for fname in ("eval_store.py", "eval_runner.py", "weekly_review.py",
                  "discord_bot.py", "hadi_engine.py"):
        py_compile.compile(str(BASE / fname), doraise=True)
    print("PY_COMPILE OK — بند 5.3 اتطبق")


if __name__ == "__main__":
    main()
