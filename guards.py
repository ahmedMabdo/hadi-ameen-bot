#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guards.py — أنماط حارس الـ Bash وأدوات الملفات، معزولة عن المحرك.

ليه ملف لوحده (2026-07-26): الأنماط دي **آخر خط دفاع برمجي** وكانت جوّه
hadi_engine.py اللي بيستورد claude_agent_sdk — فماكانش ينفع تتستورد في اختبار
من غير الـ SDK متثبت، وبالتالي **مكانش عليها ولا اختبار واحد**. أي تعديل على
regex هنا كان يقدر يفتح ثغرة في صمت.

الأنماط نفسها **مانتغيرتش** في النقل، عدا إضافتين موثقتين تحت.

⚠️ تصنيف صحيح: ده **denylist = طبقة دفاع إضافية**. الجدار الحقيقي هو allow-list
الأوامر في .claude/settings.local.json. متعتمدش على الملف ده لوحده.
"""
import re

# .env هو ملف الأسرار — ممنوع قراءته أو نقله بأي أمر. (.env.example عادي.)
_ENV_FILE_RX = re.compile(r"\.env(?!\.example)\b")
_SECRET_NAMES = r"(AZURE_DEVOPS_PAT|DISCORD_BOT_TOKEN|POSTHOG_API_KEY|ANTHROPIC_API_KEY)"

_DANGEROUS_BASH = [
    (re.compile(r"\brm\s+(-[a-zA-Z]*[rR][a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*[rR])\s+(/|~|\$HOME)"),
     "حذف جذري خارج مجلد المشروع"),
    (re.compile(r"\bgit\s+push\b.*(--force|-f\b)"), "git push بالقوة"),
    (re.compile(r"\bgit\s+reset\s+--hard"), "git reset --hard"),
    (re.compile(r"\b(shutdown|reboot|poweroff|halt|mkfs\w*|dd\s+if=)"), "أوامر نظام خطرة"),
    (re.compile(r"(?<![.\w-])(printenv|env)\s*(\||>|$)"), "تفريغ متغيرات البيئة"),
    # 2026-07-26: `printenv AZURE_DEVOPS_PAT` كان بيعدّي — النمط اللي فوق عايز
    # pipe أو redirect أو نهاية سطر، فمتغير كأرجيومنت كان بيفلت.
    (re.compile(r"\bprintenv\s+\w"), "طباعة متغير بيئة بالاسم"),
    (re.compile(r"\becho\b[^\n]*\$\{?" + _SECRET_NAMES), "طباعة قيمة توكن"),
    (re.compile(r"\b(cat|less|more|head|tail|grep|awk|sed|cut|sort|xxd|od|base64|strings|cp|mv|scp|rsync|curl|wget|tar|zip)\b[^\n|;&]*" + _ENV_FILE_RX.pattern),
     "قراءة/نقل ملف .env"),
    (re.compile(r"\bsource\s+[^\n;|&]*" + _ENV_FILE_RX.pattern), "تحميل .env في شل ظاهر"),
    (re.compile(r"\bopen\s*\(\s*['\"][^'\"]*\.env(?!\.example)"),
     "قراءة .env عبر open() في مفسّر"),
    (re.compile(r"\b(python3?|perl|ruby|node|php)\b[^\n]*(?:-c|-e|<<)[^\n]*" + _ENV_FILE_RX.pattern),
     "قراءة .env عبر كود inline/heredoc"),
    # 2026-07-26: قراءة الأسرار من os.environ في مفسّر كانت بتعدّي بالكامل.
    (re.compile(r"os\s*\.\s*environ"), "قراءة الأسرار من os.environ"),
    (re.compile(r"/proc/(?:self|\d+)/environ"), "قراءة بيئة العملية من /proc"),
    (re.compile(r"\bdotenv\b[^\n]*\.env(?!\.example)|load_dotenv"),
     "تحميل .env برمجيًا في أمر"),
    (re.compile(r"HADI_MEMORY_ADMIN"), "محاولة تخطي بوابة المراجعة البشرية للذاكرة"),
    # 2026-07-26: نفس منطق HADI_MEMORY_ADMIN — تمرير هوية PostHog inline كان
    # بيرفّع الصلاحية لأدمن (بيانات مالية + PII) على نفس سطر الأمر.
    (re.compile(r"HADI_PH_ACTOR\s*="), "محاولة تزوير هوية طالب PostHog"),
]


def bash_reason(cmd: str):
    """سبب الرفض لو الأمر خطر، أو None لو عادي."""
    for rx, why in _DANGEROUS_BASH:
        if rx.search(cmd or ""):
            return why
    return None


def touches_env_file(text: str) -> bool:
    return bool(_ENV_FILE_RX.search(text or ""))
