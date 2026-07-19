#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بند 9.2 — تعليمات هادي لاستخدام PostHog التفاعلي (مع قاعدة الحارس)."""
import py_compile
import sys
from pathlib import Path

BASE = Path.home() / "hadi-ameen-bot"

APPENDS = [
    (".env.example", "HADI_PH_STALE_HOURS",
     "\n# --- بند 9.2 — PostHog التفاعلي (اختياري) ---\n"
     "# آخر حدث أقدم من كام ساعة يعتبر «متأخر» (افتراضي 2)\n"
     "HADI_PH_STALE_HOURS=\n"
     "# وأقدم من كام ساعة يعتبر «التتبع واقف» (افتراضي 24)\n"
     "HADI_PH_DOWN_HOURS=\n"),
    ("CLAUDE.md", "## أرقام المنتج — PostHog لايف",
     "\n---\n\n"
     "## أرقام المنتج — PostHog لايف (بند 9.2)\n\n"
     "لأي سؤال عن أرقام التطبيق (أوردرات، إيراد، تحويل، أخطاء، مستخدمين، «إيه اللي حصل "
     "في آخر ساعة»): استخدم الأداة، متستناش تقرير الصبح.\n\n"
     "```bash\n"
     "python3 posthog_cli.py health                 # حالة البيانات (لو مش متأكد ابدأ بيها)\n"
     "python3 posthog_cli.py today                  # ملخص يوم العمل الحالي\n"
     "python3 posthog_cli.py orders --date 2026-07-18\n"
     "python3 posthog_cli.py errors --limit 5\n"
     "python3 posthog_cli.py since --hours 2        # لأسئلة «في آخر ساعة/ساعتين»\n"
     "python3 posthog_cli.py sql --query \"SELECT ...\"   # SELECT فقط\n"
     "```\n\n"
     "**قاعدة إلزامية — حالة البيانات قبل أي رقم:**\n\n"
     "الأداة بتطبع سطر حالة (🟢 LIVE / 🟡 STALE / 🔴 DOWN) قبل الأرقام. **انقل الحالة دي "
     "للمستخدم**، وتحديدًا:\n\n"
     "- **DOWN** → قول صراحة إن التتبع واقف والأرقام مش حقيقية. **ممنوع تقول «صفر أوردرات»** "
     "كأنه واقع — الصح: «التتبع واقف من [التاريخ]، فمفيش أرقام موثوقة النهاردة».\n"
     "- **STALE** → قول إن الأرقام ناقصة غالبًا لأن البيانات لسه بتوصل.\n"
     "- **LIVE** → عادي، بس اذكر إنها لايف دلوقتي مش من تقرير الصبح.\n\n"
     "PostHog بيرد `200 OK` وهو بيرمي الأحداث لما الكوتا تتعدى — يعني الصفر ممكن يكون "
     "عطل تتبع مش واقع بيزنس. لو الانقطاع معروف السبب هتلاقيه في الذاكرة "
     "(`memory.py search`) — اذكر السبب بدل ما تفتح تحقيق جديد.\n\n"
     "**النافذة:** «اليوم» عند الأداة = يوم العمل (القاهرة 08:00 → 02:00 اليوم اللي بعده) "
     "— نفس نافذة التقرير اليومي، عشان الأرقام تبقى مقارنة بعضها.\n\n"
     "**الحدود:** الأداة قراءة فقط (SELECT بس) ومابتعدّلش أي حاجة في PostHog.\n"),
    ("MIGRATION_SDK.md", "## بند 9.2",
     "\n---\n\n## بند 9.2 — PostHog تفاعلي\n\n"
     "`posthog_cli.py` على نمط `ado_cli.py`: قراءة فقط، وبيعيد استخدام تعريفات التقرير "
     "اليومي نفسها (`intel/8orders_report_generator.py` بيتحمّل بـ importlib لأن اسمه "
     "بيبدأ برقم) — نفس `hogql` ونفس خريطة `EV` ونفس نافذة يوم العمل `D()`. "
     "يعني **الرقم اللايف والرقم في تقرير الصبح بيتحسبوا بنفس الطريقة**.\n\n"
     "### الحارس (السبب الأساسي لوجود الملف بالشكل ده)\n\n"
     "PostHog بيرد `200 OK` وبيرمي الأحداث بصمت لما الكوتا تتعدى. من غير حارس، "
     "«كام أوردر النهاردة؟» بترجع **صفر** بثقة. كل أمر بيطبع الحالة قبل الأرقام:\n\n"
     "| الحالة | المعنى |\n|--------|--------|\n"
     "| 🟢 LIVE | آخر حدث < ساعتين — الأرقام موثوقة |\n"
     "| 🟡 STALE | 2–24 ساعة — ناقصة غالبًا |\n"
     "| 🔴 DOWN | > 24 ساعة — **الأرقام مش حقيقية**، انقطاع تتبع |\n\n"
     "العتبات في `.env` (`HADI_PH_STALE_HOURS` / `HADI_PH_DOWN_HOURS`)، والقاعدة "
     "مكتوبة لهادي في `CLAUDE.md`: ينقل الحالة قبل أي رقم.\n\n"
     "### المفتاح\n\n"
     "محتاج `POSTHOG_API_KEY` (Personal API key، قراءة) في `.env` في الجذر — "
     "**بيتحط يدويًا من صاحب الحساب**. من غيره الأداة بتقف برسالة واضحة بدل ما ترمي "
     "traceback.\n\n"
     "### التحقق\n\n"
     "`posthog_cli.py selftest` (من غير شبكة): تصنيف الحارس، نافذة يوم العمل عند 01:30 "
     "و14:00 القاهرة، ورفض أي استعلام مش SELECT.\n"),
]


def main():
    for req in ("posthog_cli.py",):
        if not (BASE / req).exists():
            sys.exit(f"ABORT: {req} مش موجود")

    for fname, marker, text in APPENDS:
        path = BASE / fname
        src = path.read_text(encoding="utf-8") if path.exists() else ""
        if marker in src:
            print(f"SKIP {fname} (موجود قبل كده)")
            continue
        path.write_text(src.rstrip("\n") + "\n" + text, encoding="utf-8")
        print(f"APPENDED {fname}")

    py_compile.compile(str(BASE / "posthog_cli.py"), doraise=True)
    print("PY_COMPILE OK — بند 9.2 اتربط")


if __name__ == "__main__":
    main()
