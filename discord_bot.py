import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

import discord
from discord.ext import tasks
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# محرك هادي (Claude Agent SDK + fallback CLI) — لازم يتستورد بعد load_dotenv
# عشان يقرا إعدادات .env (HADI_ENGINE / CLAUDE_MODEL / HADI_MAX_CONCURRENCY ...).
import hadi_engine
import file_extract
import state_lock  # بند 3.3 — قفل الكتابة المشترك (flock) لملفات الحالة
import eval_store  # بند 5.3 — تسجيل نتيجة كل تفاعل + تقييم الرياكشنز
import heartbeat  # بند 8.1/8.3 — الفحوصات الاستباقية والأحداث
import ambient_gate  # نقطة 1 — بوابة الحضور الذكي الثلاثية (صامت/رياكشن/رد)
import honorifics  # نقطة 1 — حارس الألقاب (باشمهندس للأونرز على أي مخرج)
import process_state  # نقطة 3 — نموذج العملية الحي (كانبان/سبرنت + البوردات)
import ado_snapshot  # نقطة 2 — الدرج المحلي (سبرنت + بوردات + مشروع 8Orders)
import sprint_intake  # نقطة 2 — سؤال آسر في DM عن إيفنتات السبرنت
import identity  # نقطة 9 — هوية هادي الإنسانية (العمر الحقيقي + عيد الميلاد)

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()

ALLOWED_USER_IDS = {
    int(user_id.strip())
    for user_id in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if user_id.strip().isdigit()
}

# قرار آسر: كل الـ DM الاستباقية (تنبيهات/تذكيرات/معلقات) لآسر فقط — مثبّت في الكود
# مش معتمد على إعداد بيئة. (استثناء تقرير PostHog لمحمود بيتم في intel/discord_delivery.)
ASSER_USER_ID = int(os.getenv("ASSER_USER_ID", "1378684355148386355") or "1378684355148386355")

if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN غير موجود في ملف .env")

if not ALLOWED_USER_IDS:
    raise RuntimeError("ALLOWED_USER_IDS غير موجود في ملف .env")

HADAF_GUILD_ID = 1016740895544049724
AUTHORIZED_CHANNEL_IDS = {
    1136668686044909761,  # mars-team
    1179369466279235584,  # 8orders-issues
    1358833733699899704,  # 8orders-po
}

# عدد رسايل السياق اللي بتتقرا من القناة قبل الرد (قابل للتعديل من .env)
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "80") or "80")

# ذاكرة هادي الدائمة + مخزن التذكيرات
MEMORY_FILE = BASE_DIR / "knowledge" / "memory.md"
REMINDERS_FILE = Path(os.environ.get("HADI_REMINDERS_FILE", str(BASE_DIR / "reminders.json")))
IMAGES_DIR = BASE_DIR / "tmp_images"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
VIDEO_EXTS = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v")
MAX_VIDEO_BYTES = 25 * 1024 * 1024  # نفس حد إرفاق ADO في cr_media.py

# --- تفريغ صوت الفيديو (faster-whisper محلي — من غير أي نداء شبكة) ---
# الفريمات بتوري هادي «الشاشة»، والتفريغ بيوريه «الكلام». أغلب فيديوهات
# القنوات دي شخص بيشرح مشكلة بصوته وبيأشر على الشاشة — الفريمات لوحدها
# بتضيّع نص القصة.
WHISPER_ENABLED = (os.getenv("HADI_WHISPER_ENABLED", "1") or "1").strip().lower() \
    not in ("0", "false", "no", "off")
# small: توازن مقبول للعامية المصرية على CPU (~460MB). base أضعف بوضوح،
# وmedium بيوصل 4-6x realtime على CPU وده بطيء على مسار تفاعلي.
WHISPER_MODEL_NAME = (os.getenv("HADI_WHISPER_MODEL", "small") or "small").strip()
WHISPER_DEVICE = (os.getenv("HADI_WHISPER_DEVICE", "cpu") or "cpu").strip()
WHISPER_COMPUTE = (os.getenv("HADI_WHISPER_COMPUTE", "int8") or "int8").strip()
# سقف المدة اللي بتتفرّغ. الفيديو الأطول بيتقص وبيتقال في الملاحظات إنه اتقص —
# من غير السقف ده فيديو ١٠ دقايق بيقفل الـ worker دقايق على مسار تفاعلي.
WHISPER_MAX_SECONDS = int(os.getenv("HADI_WHISPER_MAX_SECONDS", "300") or "300")
# سقف طول النص الداخل للبرومبت لكل فيديو
WHISPER_MAX_CHARS = int(os.getenv("HADI_WHISPER_MAX_CHARS", "4000") or "4000")

_whisper_model = None
_whisper_load_failed = False
# قفل: التفريغ بياكل CPU بالكامل، ولو اتنين اشتغلوا مع بعض الاتنين بيبقوا أبطأ
# من التسلسل. القفل بيضمن تفريغ واحد في المرة عبر كل الرسايل.
# بيتعمل كسول جوه اللوب مش هنا: بناء asyncio.Lock وقت الاستيراد بيربطه بلوب
# غلط (أو ملوش لوب) على بايثون < 3.10.
_whisper_lock = None


def _get_whisper_lock():
    global _whisper_lock
    if _whisper_lock is None:
        _whisper_lock = asyncio.Lock()
    return _whisper_lock


# --- مناعة الـ ADO: فحص دوري + إنذار مبكر قبل انتهاء الـ PAT + طابور طلبات معلقة ---
ADO_ORG_URL = os.getenv(
    "AZURE_DEVOPS_ORG_URL", "https://hadafsolutions.visualstudio.com"
).strip().rstrip("/")
# اختياري في .env: AZURE_DEVOPS_PAT_EXPIRES=YYYY-MM-DD (تاريخ انتهاء التوكن للإنذار المبكر)
# اختياري في .env: ADO_WARN_DAYS (افتراضي 14) — قبل الانتهاء بكام يوم يبدأ التنبيه
ADO_WARN_DAYS = int(os.getenv("ADO_WARN_DAYS", "14") or "14")
PENDING_TICKETS_FILE = BASE_DIR / "knowledge" / "pending_tickets.md"

# الرد على النداء بالاسم من غير مينشن (هادي / يا هادي / Hadi) — on افتراضيًا.
# للتعطيل: NAME_TRIGGER=off في .env
NAME_TRIGGER = os.getenv("NAME_TRIGGER", "on").strip().lower() not in {
    "0", "off", "false", "no",
}

# نداء صريح فقط — عشان كلمة "هادي" كصفة ("الوضع هادي") متشغلش البوت:
NAME_CALL_RE = re.compile(
    r"(?:^\s*(?:يا\s+)?هاد[يى](?:\s+[أا]مين)?\b)"
    r"|(?:\bيا\s+هاد[يى]\b)"
    r"|(?:^\s*hadi(?:\s+amin)?\b)"
    r"|(?:\bya\s+hadi\b)",
    re.IGNORECASE,
)


def is_addressed_to_hadi(text: str) -> bool:
    """هل الرسالة بتنادي هادي بالاسم؟ (نداء صريح، مش مجرد ذكر)"""
    return bool(NAME_CALL_RE.search(text or ""))


# ── نقطة 4 — الرد البشري بدون منشن + أتمتة التذاكر ─────────────────────────
# نافذة استمرار المحادثة: لو هادي اتكلم في القناة خلال المدة دي، أي رسالة متابعة
# (مش موجّهة لحد تاني) تتعامل كأنها موجّهة له — رد فوري بدون منشن وبدون سقف الردود.
# لو عايزها تبقى كامل عمر السيشن (6 ساعات) خليها 360.
CONTINUATION_WINDOW_S = max(0, int(os.getenv("HADI_CONTINUATION_MINUTES", "20") or "20")) * 60

# أتمتة رفع Customer Issue لما حد يبلّغ عن مشكلة (من غير طلب). off لإيقافها.
AUTO_TICKET = os.getenv("HADI_AUTO_TICKET", "on").strip().lower() not in {
    "0", "off", "false", "no",
}

# إشارة بلاغ مشكلة في التطبيق/السيستم — بتضمن إن البلاغ يوصل للمحرك (يحلّل ويرفع
# تذكرة) حتى لو محدش نادى هادي، ومن غير ما يتحسب على سقف الردّين/ساعة.
_ISSUE_RX = re.compile(
    r"مشكل|عطل|مش شغال|مش بيشتغل|مش بيفتح|مابيفتحش|مابيحملش|مش بيحمل|بايظ|واقع|"
    r"وقع|هنج|بيهنج|بيعلق|بيطلع خطأ|بيطلع error|error|bug|crash|down|failed|"
    r"fail|خطأ|مش قادر",
    re.IGNORECASE,
)


def _looks_like_issue(text: str) -> bool:
    """بلاغ مشكلة تطبيق/سيستم يستاهل يوصل للمحرك ويترفع تذكرة (نقطة 4)."""
    if not AUTO_TICKET:
        return False
    t = (text or "").strip()
    return len(t) >= 8 and bool(_ISSUE_RX.search(t))


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# قفل لكل محادثة (قناة أو DM) بدل القفل العالمي القديم — محادثات مختلفة بتتخدم
# بالتوازي، والحد الأقصى الإجمالي متحكم فيه بـ HADI_MAX_CONCURRENCY جوه hadi_engine.
_conv_locks: dict = {}

# نقطة 4 — آخر مرة هادي اتكلم في كل قناة (channel_id -> ts) لتحديد استمرار المحادثة.
_last_hadi_reply: dict = {}

# مهام fire-and-forget: asyncio بيمسك مرجع ضعيف بس، فالـ GC ممكن يلغي المهمة
# قبل ما تخلص. القاموس ده بيمسك مرجع قوي لحد ما تنتهي.
_bg_tasks: set = set()


def _spawn(coro):
    task = asyncio.ensure_future(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    return task


def get_conv_lock(key: str) -> asyncio.Lock:
    """قفل خاص بالمحادثة دي — بيحافظ على ترتيب الرسايل جوه نفس القناة/الـ DM.

    F18: القاموس محدود — لما يعدي 256 مفتاح بنشيل الأقفال غير المستخدمة
    (كان بيكبر للأبد مع كل DM جديد)."""
    lock = _conv_locks.get(key)
    if lock is None:
        if len(_conv_locks) > 256:
            for old_key in [k for k, v in _conv_locks.items() if not v.locked()][:64]:
                _conv_locks.pop(old_key, None)
        lock = _conv_locks.setdefault(key, asyncio.Lock())
    return lock


def load_memory() -> str:
    """يقرأ ذاكرة هادي الدائمة عشان تتحقن في كل محادثة (أي قناة)."""
    try:
        txt = MEMORY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    has_notes = any(l.strip().startswith("-") for l in txt.splitlines())
    return txt if has_notes else ""


def get_memory_context(query_text: str) -> str:
    """بند 4.2 — الذاكرة المتدرجة: نواة + قواعد سلوك + ملاحظات حسب صلة الرسالة.

    الفهرس (memory_index.db) مشتق من knowledge/memory.md — المصدر والـ audit trail
    لسه الملف وgit زي ما هما. تحت HADI_MEMORY_FULL_LIMIT حرف بيتحقن كله (سلوك
    النهارده)، وفوقه بيتدرج لأقرب HADI_MEMORY_TOP_K ملاحظات. أي مشكلة في الفهرس
    → رجوع آمن للحقن الكامل القديم."""
    try:
        import memory_store
        return memory_store.memory_block(query_text)
    except Exception as error:
        print(f"MEMORY STORE WARN: {type(error).__name__}: {error} — رجوع للحقن الكامل")
        return load_memory()


async def ask_claude(
    user_message: str,
    author_name: str,
    history: str = "",
    reply_context: str = "",
    channel_label: str = "",
    images: list | None = None,
    message_id: str = "",
    media_notes: str = "",
    conv_key: str = "",
    on_progress=None,
    stats: dict | None = None,
    author_id: str = "",
) -> str:
    history_block = (
        f"""
آخر رسايل المحادثة دي (الأقدم فالأحدث) — سياق فقط، دوّر فيها قبل ما تقول "مش لاقي معلومة".
رسايلك انت معلّمة بـ [هادي (أنت)] — استخدمها عشان تفهم لو الطلب الحالي متابعة لحاجة انت عملتها:
{history}
"""
        if history
        else ""
    )

    mem = get_memory_context(user_message)
    memory_block = (
        f"""
ذاكرة هادي الدائمة (معلومات محفوظة سابقًا — اعتمد عليها وهي صحيحة لحد ما تتحدّث):
{mem}
"""
        if mem
        else ""
    )

    reply_block = (
        f"""
الرسالة الحالية معمولها ريبلاي (رد مباشر) على الرسالة دي — دي السياق الأساسي للطلب:
{reply_context}
"""
        if reply_context
        else ""
    )

    images_list = "\n".join(images) if images else ""
    images_block = (
        f"""
مرفق مع الرسالة صور محفوظة كملفات محلية (ومنها فريمات متاخدة من الفيديوهات المرفقة لو موجودة).
اقرأ كل ملف منها بأداة Read — دي صور هتشوفها فعليًا — وحلل محتواها كجزء أساسي من ردك،
ومن غير ما تذكر مسارات الملفات في ردك:
{images_list}
"""
        if images_list
        else ""
    )

    media_block = (
        f"""
ميديا الرسالة (الحالية + الريبلاي + الفورورد):
{media_notes}
قدراتك على الميديا حقيقية ومتاحة فعلًا — ممنوع تمامًا تقول "مش قادر أشوف الصور/الفيديوهات" أو "مش قادر أرفعها على Azure":
- الصور بتشوفها فعليًا (بأداة Read)، والفيديوهات بتشوف فريمات مستخرجة منها لو متاحة.
- **الصوت**: لو مفيش سطر "تفريغ صوت" في ملاحظات الميديا تحت، يبقى التفريغ مش متاح على السيرفر — قول كده بصراحة لو حد سألك عن كلام في الفيديو، ومتدّعيش إنك سمعته.
- رفع/إرفاق الميديا على Azure DevOps بيتم عن طريق التذاكر:
  * مع إنشاء تذكرة جديدة: po_channel_cr.py file-cr أو ado_cli.py create-work-item/add-child
    مع --source-msg {message_id} و --channel <channel_id بتاع الرسالة> —
    بيرفق كل صور/فيديوهات الرسالة (والريبلاي بتاعها) تلقائيًا (الملف لحد 25MB، والأكبر بيتحط لينكه في الـ discussion).
  * على تذكرة موجودة: ado_cli.py attach-media <work_item_id> --source-msg {message_id} --channel <channel_id>.
- id الرسالة الحالية: {message_id} — ده اللي بتحطه في --source-msg، وid القناة موجود في سطر "القناة الحالية للرسالة".
"""
        if media_notes
        else ""
    )

    # نقطة 2 — سطر وعي مكثف من الـ snapshot المحلي (قراءة SQLite بالميلي ثانية):
    # تذكير إن الدرج موجود وطازة + قاعدة «شغّل brief قبل أي رد عن البورد/السبرنت».
    snapshot_block = ""
    try:
        ptr = await asyncio.to_thread(ado_snapshot.pointer_line)
        if ptr:
            snapshot_block = f"""
نبض الشغل دلوقتي (من snapshot محلي بيتحدث كل ~15 دقيقة): {ptr}
لأي سؤال عن بورد/سبرنت/تذاكر/مواعيد/«إيه الجديد» شغّل python3 ado_snapshot.py brief
(أو boards/whatsnew/project حسب الحاجة) ورد من نتيجته بالـ freshness banner — ممنوع ترد من الذاكرة.
"""
    except Exception as _sp_err:
        print(f"SNAPSHOT POINTER WARN: {type(_sp_err).__name__}: {_sp_err}")

    # نقطة 3 — نموذج العملية الحي (كانبان/سبرنت + حالة البوردات) بيتحقن في كل
    # محادثة عشان هادي يمشي بانسجام مع الوضع الحالي ومايرجعش لافتراضات السبرنت القديمة.
    process_block = ""
    try:
        _ps = process_state.human_summary()
        if _ps:
            process_block = "\n" + _ps + "\n"
    except Exception as _pe:
        print(f"PROCESS STATE WARN: {type(_pe).__name__}: {_pe}")

    # نقطة 4 — أتمتة التذاكر: لو الرسالة بلاغ مشكلة، هادي يرفع Customer Issue على
    # السابورت لوحده، يبعت اللينك، ويحدّث نفس التذكرة من سياق المحادثة بعدين.
    auto_ticket_block = ""
    if AUTO_TICKET:
        auto_ticket_block = f"""
أتمتة التذاكر (نقطة 4 — من غير ما حد يطلب):
- لو الرسالة الحالية **بلاغ عن مشكلة/عطل في التطبيق أو السيستم** (مش فكرة ولا طلب تحسين) ولسه **مفيش تذكرة** ليها:
  * ارفع **Customer Issue على بورد السابورت** فورًا بأدوات ADO الموثّقة (التزم بجودة التذاكر في CLAUDE.md #14) مع `--source-msg {message_id} --channel <id القناة من سطر «القناة الحالية للرسالة»>` عشان الميديا ومنع التكرار.
  * رجّع في ردك **لينك التذكرة** باختصار كده: «رفعت تذكرة على السابورت: <url>».
- **متعملش تذكرة جديدة** لو نفس المشكلة اترفعت قبل كده في الجلسة/الشات، أو لو حد قال «التذكرة/التيكت» بأل التعريف (اتبع قاعدة CLAUDE.md #13).
- **تحديث من السياق**: لو رسالة بعدين بتضيف تفاصيل أو تطوّر لمشكلة انت رفعتلها تذكرة في نفس المحادثة، متعملش تذكرة تانية — ضيف تعليق على نفس التذكرة (`python3 ado_cli.py add-comment <id> ...`) وقول إنك حدّثتها.
- الأفكار وطلبات التحسين = Change Request مش Customer Issue، وماتترفعش تلقائيًا من غير طلب.
- ممنوع تقول «رفعت تذكرة» من غير ما تكون نفّذت الأمر فعلًا ورجعلك id/لينك حقيقي.
""".strip()

    prompt = f"""
أنت هادي أمين، عضو فريق Hadaf على Discord.
{identity.identity_line()}
أول حاجة: اقرأ ملف HADI_PERSONA.md (شخصيتك، فهم السياق، قواعد السلوك) والتزم بيه،
ومعاه تعليمات CLAUDE.md (سياق المشروع والأدوات).
رد بالعربية المصرية الواضحة إلا لو المستخدم طلب لغة أخرى.
لا تعرض أي tokens أو passwords أو بيانات من ملف .env.
لا تنفذ حذفًا أو تعديلات خطرة دون تأكيد واضح من المستخدم.

قواعد فشل الـ ADO (مهمة جدًا):
- لو أمر ado_cli.py رجّع خطأ مصادقة (صفحة Sign-In أو HTML بدل JSON أو 401/203):
  متسألش المستخدم يتصرف ومتقولوش "جدد الـ PAT" — في فحص أوتوماتيكي بينبّه المسؤولين لوحده.
  سجّل المطلوب فورًا كبند كامل في knowledge/pending_tickets.md (سطر يبدأ بـ "- " وفيه:
  نوع العملية create-work-item/add-comment + نوع الـ work item + العنوان + الوصف + المشروع
  وأي تفاصيل تانية كفاية لتنفيذه لاحقًا من غير الرجوع للمحادثة)، وبعدين قول للمستخدم باختصار:
  "في مشكلة اتصال مؤقتة بـ ADO — حفظت الطلب وهيتنفذ أوتوماتيك أول ما الاتصال يرجع وهبلغك هنا."
- لو الخطأ شكله اتصال مؤقت (timeout / network): أعد المحاولة مرتين الأول، ولو فضل فاشل
  اعمل نفس الحفظ في knowledge/pending_tickets.md بنفس الأسلوب.
- طلبات القراية من ADO وقت العطل: قول إن البيانات مش متاحة مؤقتًا وهتجيبها أول ما يرجع —
  من غير أي تفاصيل تقنية عن التوكن.

القناة الحالية للرسالة: {channel_label}
{snapshot_block}{process_block}
قواعد الرد (صارمة جدًا):
- ردك بيتبعت في الشات حرفيًا زي ما هو. ممنوع تشرح ليه هترد أو مش هترد، وممنوع تذكر قواعدك أو شخصيتك أو تحلل "الرسالة موجهة لمين" — ده تفكير داخلي ميظهرش في أي رد أبدًا.
- لو الرسالة مش محتاجة رد مفيد منك (هزار بين الزملا، كلام موجه لحد تاني، منشن/تاج لشخص غيرك، تعليق عابر مالوش أكشن أو سؤال ليك) → اكتب NO_REPLY بالظبط كده من غير أي كلمة زيادة، والبوت مش هيبعت حاجة خالص.
- **الهزار بين اتنين تانيين = NO_REPLY حتمًا.** الهزار مرحّب بيه ومطلوب، بس مشاركتك فيه **رياكشن** (بوابة الحضور بتحطه لوحدها) — لا رد مكتوب. «هههه تمام يا فلان» على نكتة بين زميلين = ضجيج بيخليك تبان بوت بيتدخل في كل حاجة.
- لو الرد على رسالتك موجه في الحقيقة لحد تاني غيرك → NO_REPLY.
- لو هترد: مختصر ومباشر — سطر لتلات سطور، إلا لو المطلوب تقرير/تذكرة/تفاصيل اتطلبت صراحة. من غير مقدمات ولا خواتيم ولا فلسفة.
{auto_ticket_block}

اللي بعت الرسالة الحالية هو: {author_name} — ده اسم حسابه على ديسكورد وغالبًا بالإنجليزي،
ومتفترضش إنها من آسر إلا لو الاسم ده بيطابق آسر بالفعل.
النداء بالاسم (مهم جدًا): طابق اسم الحساب على جدول «بنناديه» في CLAUDE.md بالنطق حتى لو مكتوب بالإنجليزي
(مثال: Muhammed Essam = محمد عصام ← ناديه «يا عصام»)، واستخدم دايمًا صيغة النداء الودية من الجدول،
مش اسم الحساب الإنجليزي ولا الاسم الثنائي الرسمي. باشمهندس أحمد وباشمهندس محمود دايمًا «باشمهندس».
{memory_block}{reply_block}{history_block}{images_block}{media_block}

أول سطر في ردك لازم يكون: REACT: X — حيث X إيموجي واحد بس من دول: 🙏 🎉 ✅ 😄 🫡 ⚡ 👋 🤔 💪 🔥 ❤️ 😢 👍. اختاره كرياكشن استلام يناسب رسالة {author_name} دي بالذات (مضمونها ونبرتها والميديا بتاعتها): طلب شغل/تنفيذ → 🫡 أو 👍، استفسار أو سؤال محايد → 🤔، سلام/تحية → 👋، مجهود أو إنجاز كبير → 💪 أو 🔥، خبر محزن → 😢. ممنوع تستخدم إيموجي العينين 👀 خالص. بعد سطر REACT سيب سطر فاضي وابتدي ردك الطبيعي، ومتكتبش REACT في أي حتة تانية. لو مش هترد، اكتب NO_REPLY من غير سطر REACT.
رسالة {author_name} [Discord ID: {author_id}]:
{user_message}
""".strip()

    return await hadi_engine.run_agent(
        prompt, conv_key=conv_key, timeout=900, on_progress=on_progress, stats=stats,
        actor_id=author_id
    )


def extract_forwarded_text(message: discord.Message) -> str:
    """لو الرسالة فورورد (Forward)، بيطلّع محتوى الرسالة الأصلية من الـ snapshots.

    الرسالة المحوّلة بتوصل بـ content فاضي — المحتوى الحقيقي بيبقى في
    message.message_snapshots (محتاجة discord.py 2.5+). بيرجّع "" لو مفيش فورورد،
    وبيتعامل بأمان مع الإصدارات الأقدم عن طريق getattr."""
    snapshots = getattr(message, "message_snapshots", None) or []
    parts = []
    for snap in snapshots:
        block_lines = []
        text = (getattr(snap, "content", "") or "").strip()
        if text:
            block_lines.append(text)
        for emb in getattr(snap, "embeds", None) or []:
            emb_text = " — ".join(
                piece for piece in ((emb.title or ""), (emb.description or "")) if piece
            ).strip()
            if emb_text:
                block_lines.append(f"[Embed] {emb_text}")
        attachments = getattr(snap, "attachments", None) or []
        if attachments:
            names = ", ".join(att.filename for att in attachments)
            block_lines.append(f"[مرفقات: {names}]")
        if block_lines:
            parts.append("\n".join(block_lines))
    return "\n---\n".join(parts).strip()


def _is_image_attachment(att) -> bool:
    ct = (att.content_type or "").lower()
    return ct.startswith("image/") or att.filename.lower().endswith(IMAGE_EXTS)




def _is_video_attachment(att) -> bool:
    ct = (att.content_type or "").lower()
    return ct.startswith("video/") or att.filename.lower().endswith(VIDEO_EXTS)


def _collect_attachments(message, pred):
    """كل المرفقات المطابقة من الرسالة نفسها + الريبلاي + الفورورد."""
    atts = [a for a in (message.attachments or []) if pred(a)]
    ref = message.reference.resolved if message.reference else None
    if isinstance(ref, discord.Message):
        atts += [a for a in (ref.attachments or []) if pred(a)]
    for snap in (getattr(message, "message_snapshots", None) or []):
        atts += [a for a in (getattr(snap, "attachments", None) or []) if pred(a)]
    return atts


def media_manifest(message) -> str:
    """قايمة نصية بكل ميديا الرسالة (صور وفيديوهات) عشان البرومبت."""
    rows = []
    for att in _collect_attachments(
        message, lambda a: _is_image_attachment(a) or _is_video_attachment(a)
    ):
        kind = "صورة" if _is_image_attachment(att) else "فيديو"
        size_mb = (att.size or 0) / (1024 * 1024)
        rows.append(f"- {kind}: {att.filename} ({size_mb:.1f}MB)")
    return "\n".join(rows)


def _extract_frames(video_path, out_prefix, count: int = 3) -> list:
    """يستخرج لغاية count فريم موزعين على مدة الفيديو (بيشتغل في thread)."""
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(video_path)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        duration = float((probe.stdout or "").strip() or 0)
    except (ValueError, subprocess.TimeoutExpired):
        duration = 0.0
    points = [duration * 0.1, duration * 0.5, duration * 0.9] if duration > 1 else [0.0]
    frames = []
    for j, ts in enumerate(points[:count]):
        out = Path(f"{out_prefix}_f{j}.jpg")
        try:
            proc = subprocess.run(
                ["ffmpeg", "-y", "-ss", f"{max(ts, 0):.2f}", "-i", str(video_path),
                 "-frames:v", "1", "-q:v", "3", str(out)],
                capture_output=True, timeout=60, check=False,
            )
        except subprocess.TimeoutExpired:
            continue
        if proc.returncode == 0 and out.exists() and out.stat().st_size > 0:
            frames.append(str(out))
    return frames


def _extract_audio(video_path, out_path) -> bool:
    """يطلّع المسار الصوتي 16kHz مونو WAV — الصيغة اللي whisper بيتوقعها.

    بيرجّع False لو الفيديو مافيهوش صوت أصلًا (حالة شائعة: تسجيل شاشة صامت)،
    وساعتها مافيش داعي نحمّل الموديل من أساسه.
    """
    try:
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path), "-vn",
             "-t", str(WHISPER_MAX_SECONDS),
             "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(out_path)],
            capture_output=True, timeout=180, check=False,
        )
    except subprocess.TimeoutExpired:
        return False
    out = Path(out_path)
    # هيدر الـ WAV لوحده 44 بايت — أي حاجة أصغر من ~1KB يبقى مافيش صوت فعلي
    return proc.returncode == 0 and out.exists() and out.stat().st_size > 1024


def _load_whisper():
    """يحمّل موديل faster-whisper مرة واحدة ويكاشه. None لو مش متاح.

    التحميل بياخد ثواني وبياكل رام، فبيتعمل مرة على أول فيديو فيه صوت —
    مش وقت الإقلاع، عشان بوت من غير فيديوهات مايدفعش التمن.
    """
    global _whisper_model, _whisper_load_failed
    if _whisper_model is not None or _whisper_load_failed:
        return _whisper_model
    try:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(
            WHISPER_MODEL_NAME, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
        print(f"WHISPER: اتحمّل موديل {WHISPER_MODEL_NAME} "
              f"({WHISPER_DEVICE}/{WHISPER_COMPUTE})")
    except Exception as error:
        _whisper_load_failed = True  # مانحاولش تاني كل رسالة
        print(f"WHISPER: مش متاح — {type(error).__name__}: {error}")
    return _whisper_model


def _transcribe(audio_path) -> tuple:
    """(نص, لغة) من ملف صوت. ("", "") لو فشل أو مفيش كلام. بيشتغل في thread.

    اللغة اكتشاف تلقائي (قرار آسر): الفيديوهات فيها عربي مصري وإنجليزي كامل،
    وتثبيت ar كان هيغلط في الفيديوهات الإنجليزي بالكامل.
    """
    model = _load_whisper()
    if model is None:
        return "", ""
    try:
        segments, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            vad_filter=True,       # بيشيل الصمت — أسرع ونضيف من الهلوسة
            vad_parameters={"min_silence_duration_ms": 500},
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text[:WHISPER_MAX_CHARS], (getattr(info, "language", "") or "")
    except Exception as error:
        print(f"WHISPER ERROR: {type(error).__name__}: {error}")
        return "", ""


async def _transcribe_video(video_path, tag) -> str:
    """يفرّغ صوت فيديو ويرجّع سطر ملاحظات للبرومبت ("" لو مفيش حاجة تتقال)."""
    if not WHISPER_ENABLED:
        return ""
    audio_path = Path(f"{video_path}.wav")
    try:
        got_audio = await asyncio.to_thread(_extract_audio, video_path, audio_path)
        if not got_audio:
            return ""
        # قفل عالمي: تفريغ واحد في المرة (شوف تعليق _whisper_lock)
        async with _get_whisper_lock():
            text, lang = await asyncio.to_thread(_transcribe, audio_path)
        if not text:
            return ""
        truncated = len(text) >= WHISPER_MAX_CHARS
        cut = f" (اتقص عند {WHISPER_MAX_SECONDS // 60} دقايق)" if truncated else ""
        lang_note = f" [لغة مكتشفة: {lang}]" if lang else ""
        return (f"- تفريغ صوت {tag}{lang_note}{cut}:\n"
                f"  «{text}»")
    except Exception as error:
        print(f"TRANSCRIBE ERROR: {type(error).__name__}: {error}")
        return ""
    finally:
        try:
            audio_path.unlink()
        except OSError:
            pass


async def save_video_frames(message: discord.Message, limit_videos: int = 2) -> tuple:
    """ينزّل الفيديوهات المرفقة مؤقتًا ويستخرج منها فريمات + تفريغ صوت.

    بيرجع (frame_paths, notes): الفريمات بتتضاف لقايمة الصور، والـ notes بتشرح
    حالة كل فيديو للبرومبت وبتشيل نص التفريغ. الفيديو نفسه بيتمسح فورًا بعد
    الاستخراج.

    الفريمات + الصوت مع بعض: أغلب الفيديوهات هنا حد بيشرح مشكلة بصوته وبيأشر
    على الشاشة، فالصورة لوحدها بتوصّل نص القصة بس."""
    vids = _collect_attachments(message, _is_video_attachment)
    frame_paths, notes = [], []
    if not vids:
        return frame_paths, notes
    IMAGES_DIR.mkdir(exist_ok=True)
    have_ffmpeg = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
    for i, att in enumerate(vids[:limit_videos]):
        size_mb = (att.size or 0) / (1024 * 1024)
        label = f"{att.filename} ({size_mb:.1f}MB)"
        if att.size and att.size > MAX_VIDEO_BYTES:
            notes.append(f"- الفيديو {label}: أكبر من 25MB فمشفتش محتواه — عند الإرفاق على ADO هيتحط لينكه تلقائيًا")
            continue
        if not have_ffmpeg:
            notes.append(f"- الفيديو {label}: مفيش أداة استخراج فريمات على السيرفر — متاح للإرفاق على ADO فقط")
            continue
        ext = Path(att.filename).suffix.lower() or ".mp4"
        video_path = IMAGES_DIR / f"{message.id}_vid{i}{ext}"
        try:
            await att.save(video_path)
            got = await asyncio.to_thread(
                _extract_frames, video_path, IMAGES_DIR / f"{message.id}_vid{i}"
            )
            frame_paths += got
            if got:
                notes.append(f"- الفيديو {label}: اتاخد منه {len(got)} فريمات — موجودة ضمن الصور اللي هتقراها")
            else:
                notes.append(f"- الفيديو {label}: معرفتش أستخرج فريمات (صيغة غير مدعومة غالبًا) — متاح للإرفاق على ADO")
            # التفريغ مستقل عن الفريمات: فيديو صيغته غريبة ممكن يفشل في
            # الفريمات وينجح في الصوت، والعكس. فشل أي واحد فيهم ماينفيش التاني.
            spoken = await _transcribe_video(video_path, label)
            if spoken:
                notes.append(spoken)
        except Exception as error:
            print(f"VIDEO FRAMES ERROR: {error}")
            notes.append(f"- الفيديو {label}: حصل خطأ في قراءته — متاح للإرفاق على ADO")
        finally:
            try:
                video_path.unlink()
            except OSError:
                pass
    for att in vids[limit_videos:]:
        notes.append(f"- فيديو إضافي: {att.filename} — موجود في الرسالة وبيترفق برضه مع --source-msg")
    return frame_paths, notes


REACTION_RULES = [
    (re.compile(r"شكر|متشكر|تسلم|thanks|thank\s*you|thx|جزاك|يعطيك العافية", re.IGNORECASE), "\U0001F64F"),
    (re.compile(r"مبروك|تهانينا|congrat", re.IGNORECASE), "\U0001F389"),
    (re.compile(r"خلصنا|اتقفل|اتحل|تم التسليم|اترفع|نجح|اشتغلت|fixed|done|deployed|released|passed", re.IGNORECASE), "\u2705"),
    (re.compile("\U0001F602|\U0001F923|ههه|هزار|لو+ل|lol", re.IGNORECASE), "\U0001F604"),
    (re.compile(r"مشكل|عطل|واقع|وقع|باج|بايظ|مش شغال|مش راضي|فشل|bug|error|crash|exception|fail|\bdown\b", re.IGNORECASE), "\U0001FAE1"),
    (re.compile(r"عاجل|ضروري|مستعجل|urgent|asap|فورًا|فورا|حالًا|حالا", re.IGNORECASE), "\u26A1"),
]


def pick_reaction(text: str) -> str:
    """رياكشن استلام متناسب مع مضمون الرسالة — والمحايد من غير رياكشن مبدئي
    (الموديل بيختار الرياكشن النهائي مع الرد)."""
    t = (text or "").strip()
    for rx, emoji in REACTION_RULES:
        if rx.search(t):
            return emoji
    return ""


ALLOWED_REACTIONS = {
    "\U0001F64F", "\U0001F389", "\u2705", "\U0001F604",
    "\U0001FAE1", "\u26A1", "\U0001F44B", "\U0001F914", "\U0001F4AA",
    "\U0001F525", "\u2764\uFE0F", "\U0001F622", "\U0001F44D",
}

REACT_RX = re.compile(r"^\s*REACT:\s*(\S{1,8})\s*(?:\n+|$)", re.IGNORECASE)


def split_react_directive(text):
    """يفصل سطر REACT: <إيموجي> من أول رد الموديل — بيرجع (emoji|None, باقي الرد)."""
    m = REACT_RX.match(text or "")
    if not m:
        return None, (text or "")
    emoji = m.group(1).strip()
    rest = (text[m.end():] or "").strip()
    if emoji not in ALLOWED_REACTIONS:
        emoji = None
    return emoji, rest


async def swap_ack_reaction(message, old_emoji, new_emoji):
    """يبدّل رياكشن الاستلام المبدئي بالرياكشن اللي اختاره الموديل من السياق الكامل."""
    if not new_emoji or new_emoji == old_emoji:
        return
    try:
        await message.add_reaction(new_emoji)
        me = message.guild.me if message.guild else client.user
        if old_emoji and me:
            await message.remove_reaction(old_emoji, me)
    except Exception as error:
        print(f"REACTION SWAP ERROR: {error}")




async def save_image_attachments(message: discord.Message, limit: int = 4) -> list:
    """ينزل الصور المرفقة (من الرسالة والريبلاي والفورورد) كملفات محلية عشان Claude يقراها بأداة Read."""
    atts = [a for a in (message.attachments or []) if _is_image_attachment(a)]
    ref = message.reference.resolved if message.reference else None
    if isinstance(ref, discord.Message):
        atts += [a for a in (ref.attachments or []) if _is_image_attachment(a)]
    for snap in (getattr(message, "message_snapshots", None) or []):
        atts += [a for a in (getattr(snap, "attachments", None) or []) if _is_image_attachment(a)]
    IMAGES_DIR.mkdir(exist_ok=True)
    paths = []
    for i, att in enumerate(atts[:limit]):
        if att.size and att.size > 8 * 1024 * 1024:
            continue
        ext = Path(att.filename).suffix.lower()
        if ext not in IMAGE_EXTS:
            ext = ".png"
        path = IMAGES_DIR / f"{message.id}_{i}{ext}"
        try:
            await att.save(path)
            paths.append(str(path))
        except Exception as error:
            print(f"IMAGE SAVE ERROR: {error}")
    return paths


async def build_channel_history(channel, before_message, limit: int = HISTORY_LIMIT) -> str:
    """يقرا آخر رسايل المحادثة (قناة أو DM) قبل الرسالة الحالية عشان هادي يفهم السياق.

    بيستبعد رسايل البوتات التانية، لكن بيدخّل رسايل هادي نفسه (معلّمة
    بـ "هادي (أنت)") — من غيرها هادي مش بيشوف ردوده."""
    lines = []
    try:
        async for prev in channel.history(limit=limit, before=before_message):
            if prev.author.bot and prev.author.id != client.user.id:
                continue
            text = prev.clean_content.strip()
            if not text:
                # ممكن تكون رسالة فورورد — محتواها في الـ snapshots مش في content
                fwd = extract_forwarded_text(prev)
                if fwd:
                    text = f"(فورورد) {fwd}"
            if not text and any(_is_image_attachment(a) or _is_video_attachment(a) for a in (prev.attachments or [])):
                text = "(بعت مرفق ميديا — صورة أو فيديو)"
            if not text:
                continue
            label = "هادي (أنت)" if prev.author.id == client.user.id else prev.author.display_name
            lines.append(f"[{label}] {text}")
    except discord.HTTPException:
        return ""

    lines.reverse()
    return "\n".join(lines)


async def build_channel_history_after(channel, before_message, after_id,
                                      cap: int = 40) -> str:
    """الرسايل اللي حصلت **بعد** رسالة معينة ولحد الرسالة الحالية (ب-1).

    نفس تنسيق build_channel_history بالظبط. الغرض: الجلسة المستأنفة شايلة
    أدوار هادي بس، فالكلام اللي حصل وهو ساكت لازم يوصله — بس من غير إعادة
    إرسال الـ 80 رسالة كل دور.
    """
    lines = []
    try:
        async for prev in channel.history(limit=cap, before=before_message,
                                          after=discord.Object(id=int(after_id)),
                                          oldest_first=True):
            if prev.author.bot and prev.author.id != client.user.id:
                continue
            text = prev.clean_content.strip()
            if not text:
                fwd = extract_forwarded_text(prev)
                if fwd:
                    text = f"(فورورد) {fwd}"
            if not text and any(_is_image_attachment(a) or _is_video_attachment(a)
                                for a in (prev.attachments or [])):
                text = "(بعت مرفق ميديا — صورة أو فيديو)"
            if not text:
                continue
            label = ("هادي (أنت)" if prev.author.id == client.user.id
                     else prev.author.display_name)
            lines.append(f"[{label}] {text}")
    except (discord.HTTPException, ValueError, TypeError):
        return ""
    if not lines:
        return ""
    head = ("الكلام اللي حصل في القناة من آخر مرة اتكلمت فيها (الأقدم فالأحدث) — "
            "الجلسة عندك شايلة ردودك بس، فده اللي فاتك:")
    if len(lines) >= cap:
        head += f"\n(معروض آخر {cap} رسالة — في كلام أقدم مش معروض)"
    return head + "\n" + "\n".join(lines)


async def build_reply_context(message: discord.Message) -> str:
    """لو الرسالة ريبلاي، هات الرسالة الأصلية عشان تتبعت لهادي كسياق أساسي."""
    ref = message.reference
    if not ref or not ref.message_id:
        return ""

    # الفورورد بيجي هو كمان في message.reference لكنه مش ريبلاي —
    # محتواه بيتقري من extract_forwarded_text فمنكرروش هنا.
    forward_type = getattr(getattr(discord, "MessageReferenceType", None), "forward", None)
    if forward_type is not None and getattr(ref, "type", None) == forward_type:
        return ""

    replied = ref.resolved
    if replied is None or isinstance(replied, discord.DeletedReferencedMessage):
        try:
            replied = await message.channel.fetch_message(ref.message_id)
        except discord.HTTPException:
            return ""

    if isinstance(replied, discord.DeletedReferencedMessage):
        return ""

    text = (replied.clean_content or "").strip()
    if not text:
        text = extract_forwarded_text(replied)
    if not text:
        return ""

    label = (
        "هادي (أنت)"
        if replied.author.id == client.user.id
        else replied.author.display_name
    )
    return f"[{label}] {text}"


def _split_message(text: str, limit: int = 1900) -> list:
    """F18: تقسيم على حدود الأسطر بدل القطع في نص لينك/كلمة — زي po_channel_cr."""
    chunks, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:  # سطر واحد أطول من الحد — قطع اضطراري
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    # 2026-07-26: فلترة الأجزاء الفاضية — Discord بيرفضها بـ 400 (50035) Invalid
    # Form Body. routines_common.split_for_discord كان بيفلتر والنسخة دي لأ.
    return [c for c in chunks if c.strip()] or [text[:limit]]


async def send_long_message(channel, text: str, reply_to: discord.Message = None):
    text = honorifics.enforce(text.strip()) or "لم يتم إرجاع رد."
    chunks = _split_message(text)

    first = None
    for i, chunk in enumerate(chunks):
        if i == 0 and reply_to is not None:
            try:
                sent = await reply_to.reply(chunk, mention_author=False)
            except discord.HTTPException as error:
                # 2026-07-26: الريبلاي بيفشل بـ 50035 لو الرسالة المرجعية اتمسحت
                # وسط التشغيل (بيحصل مع الترياج اللي بياخد دقايق). الشغل خلص
                # وكلّف فلوس — فمنرميهوش، نبعته رسالة عادية من غير reference.
                print(f"REPLY FAILED ({error}) — بيتبعت كرسالة عادية")
                sent = await channel.send(chunk)
        else:
            sent = await channel.send(chunk)
        if first is None:
            first = sent
    # نقطة 4 — سجّل إن هادي اتكلم في القناة دي دلوقتي (يفتح نافذة استمرار المحادثة).
    if first is not None and getattr(channel, "guild", None) is not None:
        _last_hadi_reply[channel.id] = time.time()
    return first  # بند 5.3: id الرد بيربط التقييم بالتفاعل


async def dm_allowed_users(text: str) -> None:
    """يبعت DM لآسر فقط (قرار آسر: كل التنبيهات الاستباقية والتذكيرات لآسر بس)."""
    text = honorifics.enforce(text)
    try:
        user = client.get_user(ASSER_USER_ID) or await client.fetch_user(ASSER_USER_ID)
        await user.send(text)
    except discord.HTTPException as error:
        print(f"DM FAIL {ASSER_USER_ID}: {type(error).__name__}: {error}")


def _current_pat() -> str:
    """يعيد قراءة .env قبل ما يرجّع الـ PAT — عشان التوكن المتجدد يتلقط من غير restart."""
    load_dotenv(BASE_DIR / ".env", override=True)
    return os.getenv("AZURE_DEVOPS_PAT", "").strip()


def check_ado_auth():
    """يختبر مصادقة ADO بالـ PAT الحالي ويرجّع (status, detail).

    status واحدة من:
    - "ok": المصادقة سليمة (رد JSON).
    - "auth": PAT منتهي/غلط (401/203 أو صفحة Sign-In بدل JSON).
    - "network": مشكلة اتصال مؤقتة.
    - "config": مفيش AZURE_DEVOPS_PAT في .env أصلاً.
    """
    pat = _current_pat()
    if not pat:
        return "config", "AZURE_DEVOPS_PAT مش موجود في .env"

    url = f"{ADO_ORG_URL}/_apis/projects?api-version=7.1&$top=1"
    token = base64.b64encode(f":{pat}".encode()).decode()
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if resp.status == 200 and "json" in ctype:
                return "ok", "المصادقة سليمة"
            return "auth", f"HTTP {resp.status} والرد مش JSON — غالبًا الـ PAT منتهي"
    except urllib.error.HTTPError as error:
        if error.code in (203, 401):
            return "auth", f"HTTP {error.code} — الـ PAT منتهي أو صلاحياته ناقصة"
        return "network", f"HTTP {error.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return "network", f"{type(error).__name__}: {error}"


def pat_expiry_days():
    """الأيام المتبقية على انتهاء الـ PAT لو AZURE_DEVOPS_PAT_EXPIRES متظبطة، وإلا None."""
    raw = os.getenv("AZURE_DEVOPS_PAT_EXPIRES", "").strip()
    if not raw:
        return None
    try:
        expires = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (expires - date.today()).days


_engine_down_last_alert = 0.0


async def _alert_engine_down(detail: str) -> None:
    """تبليغ آسر إن المحرك واقع — مرة واحدة كل ساعة مهما وصل رسايل كتير."""
    global _engine_down_last_alert
    if time.time() - _engine_down_last_alert < 3600:
        return
    _engine_down_last_alert = time.time()
    await dm_allowed_users(
        "🔴 **هادي مش قادر يشتغل** — سبب تشغيلي مش بق في الكود:\n"
        f"`{detail[:200]}`\n\n"
        "لو رصيد: بيرجع لوحده في الميعاد المكتوب فوق.\n"
        "لو `Not logged in`: محتاج `claude /login` على السيرفر.\n"
        "التشخيص: `journalctl -u hadi-discord -n 50 --no-pager`"
    )


def _pending_items_exist() -> bool:
    """هل في بنود معلقة فعلية في knowledge/pending_tickets.md؟"""
    try:
        txt = PENDING_TICKETS_FILE.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(line.strip().startswith("-") for line in txt.splitlines())


ADO_RENEW_HINT = (
    "التجديد: صفحة Personal Access Tokens في Azure DevOps ← New Token "
    "(Scopes: Work Items Read & Write) ← حدّثوا AZURE_DEVOPS_PAT (وتاريخ "
    "AZURE_DEVOPS_PAT_EXPIRES) في ملف .env على السيرفر — البوت بيقرا التوكن "
    "الجديد لوحده من غير restart، وأي طلبات معلقة هتتنفذ أوتوماتيك ويوصلكم بلاغ بيها."
)

PENDING_FLUSH_PROMPT = """
أنت هادي أمين (نفس وكيل الديسكورد) شغال في مهمة خلفية أوتوماتيكية من غير مستخدم قدامك.
ملف knowledge/pending_tickets.md فيه طلبات ADO اتأجلت بسبب مشكلة مصادقة، والمصادقة رجعت شغالة دلوقتي.
اقرأ CLAUDE.md (الأدوات والسياق) وبعدين:
1) نفّذ كل بند معلق بـ ado_cli.py (create-work-item / add-comment / add-child حسب البند) وهات لينك كل work item.
2) شيل البنود اللي نجحت من knowledge/pending_tickets.md — لو بند فشل لسبب غير المصادقة سيبه مكانه واكتب سبب الفشل جنبه.
3) رد بملخص قصير بالعربية المصرية: اللي اتنفذ (عنوان + لينك) واللي لسه معلق وليه — الملخص ده هيتبعت DM لآسر والفريق.
ممنوع أي update أو delete — تنفيذ البنود المعلقة فقط.
""".strip()


def _load_reminders():
    if REMINDERS_FILE.exists():
        try:
            return json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_reminders(items):
    tmp = REMINDERS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(REMINDERS_FILE)


async def _resolve_member_id(guild, name: str):
    """يدوّر على user id لعضو بالاسم (display name أو username). None لو مش لاقي أو ملتبس.

    F15: الـ Members privileged intent مش مفعّل، فـ guild.members غالبًا فاضية
    وquery_members بيفشل — والمنشن كان بيتحول bold text في صمت. الحل: fallback
    على REST search (routines_common.resolve_user_id) اللي شغال من غير الـ intent."""
    name_l = (name or "").strip().lstrip("@").lower()
    if not name_l or guild is None:
        return None
    for m in guild.members:
        if name_l in (m.display_name or "").lower() or name_l in (m.name or "").lower():
            return m.id
    try:
        found = await guild.query_members(query=name_l.split()[0], limit=10)
        matches = [
            m for m in found
            if name_l in (m.display_name or "").lower() or name_l in (m.name or "").lower()
        ]
        if len(matches) == 1:
            return matches[0].id
        if not matches and len(found) == 1:
            return found[0].id
    except Exception:
        pass
    try:  # F15: REST search — مثبت الفاعلية في الروتينات، ومش محتاج privileged intent
        import routines_common
        uid = await asyncio.to_thread(routines_common.resolve_user_id, name_l)
        if uid:
            return int(uid)
    except Exception as error:
        print(f"MENTION REST FALLBACK FAIL: {type(error).__name__}: {error}")
    return None


async def _fire_reminder(item):
    text = (item.get("text") or "").strip()
    target = item.get("target") or {}
    body = f"⏰ تذكير: {text}"
    if target.get("kind") == "dm":
        user = client.get_user(ASSER_USER_ID) or await client.fetch_user(ASSER_USER_ID)
        await user.send(body)
    elif target.get("kind") == "channel":
        cid = int(target["id"])
        ch = client.get_channel(cid) or await client.fetch_channel(cid)
        mention = str(target.get("mention") or "").strip()
        if mention:
            if mention.isdigit():
                body = f"<@{mention}> {body}"
            else:
                mid = await _resolve_member_id(getattr(ch, "guild", None), mention)
                body = f"<@{mid}> {body}" if mid else f"**{mention}** — {body}"
        await ch.send(body)
    else:
        raise ValueError(f"unknown target: {target}")


@tasks.loop(seconds=30)
async def reminder_loop():
    """يفحص التذكيرات المجدولة وينفّذ اللي حان ميعاده. آمن ضد الإضافة المتزامنة:
    بيجمع التحديثات بالـ id وبيعيد التحميل قبل الحفظ عشان ميمسحش تذكير جديد."""
    items = _load_reminders()
    if not items:
        return
    now = time.time()
    updates = {}
    give_up = []
    for item in items:
        if item.get("fired") or float(item.get("at_epoch", 0)) > now:
            continue
        # 2026-07-26: انتظار متزايد بين المحاولات. قبل كده 5 محاولات × 30 ثانية
        # = دقيقتين ونص وبعدها استسلام نهائي — أي انقطاع شبكة أطول من كده كان
        # بيضيّع التذكير.
        if float(item.get("next_attempt_at", 0)) > now:
            continue
        try:
            await _fire_reminder(item)
            updates[item["id"]] = {"fired": True}
            print(f"REMINDER FIRED: #{item.get('id')} {(item.get('text') or '')[:40]}")
        except Exception as error:
            att = int(item.get("attempts", 0)) + 1
            upd = {"attempts": att,
                   "next_attempt_at": now + min(30 * (2 ** (att - 1)), 900)}
            if att >= 10:
                # بيتعلّم fired عشان الحلقة تسيبه، بس **مع تبليغ** — قبل كده كان
                # بيتعلّم «اتنفذ» ويختفي من schedule.py list فمحدش يعرف إنه ضاع.
                upd.update(fired=True, failed=True,
                           last_error=f"{type(error).__name__}: {error}"[:200])
                give_up.append(item)
                print(f"REMINDER GIVEN UP: #{item.get('id')}")
            updates[item["id"]] = upd
            print(f"REMINDER FAIL #{item.get('id')} (محاولة {att}): "
                  f"{type(error).__name__}: {error}")
    if updates:

        def _apply_updates():
            # بند 3.3: نفس قفل الكتابة بتاع schedule.py/memory.py — علشان
            # «إضافة تذكير جديد» من محادثة متوازية متتكتبش فوق تعليم اللي اتنفذ.
            with state_lock.write_lock():
                current = _load_reminders()
                for it in current:
                    if it.get("id") in updates:
                        it.update(updates[it["id"]])
                _save_reminders(current)

        await asyncio.to_thread(_apply_updates)

    for item in give_up:
        await dm_allowed_users(
            f"⚠️ تذكير #{item.get('id')} فشل نهائيًا بعد 10 محاولات ومااتبعتش.\n"
            f"النص: {(item.get('text') or '')[:200]}\n"
            f"الوجهة: {item.get('target')}\n"
            f"آخر خطأ: {(item.get('last_error') or '?')[:150]}")


@tasks.loop(hours=24)
async def ado_health_loop():
    """فحص يومي لمصادقة ADO وقرب انتهاء الـ PAT — إنذار مبكر في الـ DM بدل مفاجأة وقت الشغل.

    أول فحص بيحصل فور تشغيل البوت، فأي مشكلة بتبان في نفس لحظة النشر مش بعد يوم."""
    status, detail = await asyncio.to_thread(check_ado_auth)

    if status == "auth":
        await dm_allowed_users(
            f"⚠️ فحص ADO اليومي: المصادقة واقعة ({detail}).\n{ADO_RENEW_HINT}"
        )
        return
    if status == "config":
        await dm_allowed_users(f"⚠️ فحص ADO اليومي: {detail}.\n{ADO_RENEW_HINT}")
        return
    if status == "network":
        # مشكلة شبكة مؤقتة مش بتستاهل إزعاج — بتتسجل في اللوج بس
        print(f"ADO HEALTH: مشكلة شبكة مؤقتة — {detail}")
        return

    days = pat_expiry_days()
    if days is None or days > ADO_WARN_DAYS:
        return
    if days < 0:
        await dm_allowed_users(
            "ℹ️ فحص ADO: المصادقة شغالة لكن تاريخ AZURE_DEVOPS_PAT_EXPIRES في .env عدّى — "
            "لو التوكن اتجدد حدّثوا التاريخ عشان الإنذار المبكر يفضل دقيق."
        )
        return
    await dm_allowed_users(
        f"⏰ تنبيه مبكر: الـ ADO PAT هينتهي خلال {days} يوم.\n{ADO_RENEW_HINT}"
    )


@tasks.loop(minutes=30)
async def pending_tickets_loop():
    """كل نص ساعة: لو في طلبات معلقة والمصادقة رجعت شغالة — ينفذها ويبلغ في الـ DM."""
    if not _pending_items_exist():
        return
    status, _ = await asyncio.to_thread(check_ado_auth)
    if status != "ok":
        return

    bg_lock = get_conv_lock("bg:pending")
    if bg_lock.locked():
        return

    async with bg_lock:
        try:
            summary = await hadi_engine.run_oneshot(PENDING_FLUSH_PROMPT, timeout=300)
        except RuntimeError as error:
            print(f"PENDING FLUSH FAIL: {type(error).__name__}: {error}")
            return

    if summary:
        await dm_allowed_users(f"📌 تحديث الطلبات المعلقة:\n{summary}")


@reminder_loop.before_loop
async def _before_reminder_loop():
    await client.wait_until_ready()


@ado_health_loop.before_loop
async def _before_ado_health_loop():
    await client.wait_until_ready()


@pending_tickets_loop.before_loop
async def _before_pending_tickets_loop():
    await client.wait_until_ready()


@client.event
async def on_ready():
    print(f"HADI ONLINE: {client.user} | ID: {client.user.id}")
    heartbeat.touch_alive()
    print(f"HADI ENGINE: {hadi_engine.describe()}")
    try:  # بند 4.2 (RAG): يعيد بناء فهرس /knowledge بس لو الملفات اتغيرت
        import knowledge_store
        print(f"HADI KNOWLEDGE: {knowledge_store.ensure_fresh()}")
    except Exception as error:
        print(f"HADI KNOWLEDGE: الفهرس مش شغال ({type(error).__name__}: {error})"
              " — هادي هيقرا ملفات المعرفة كاملة زي الأول")
    if not reminder_loop.is_running():
        reminder_loop.start()
    if not ado_health_loop.is_running():
        ado_health_loop.start()
    if not pending_tickets_loop.is_running():
        pending_tickets_loop.start()
    if heartbeat.ENABLED and not heartbeat_loop.is_running():  # بند 8.1
        heartbeat_loop.start()
    if not sprint_watch_loop.is_running():  # نقطة 2 — وعي السبرنت
        sprint_watch_loop.start()
    if not birthday_loop.is_running():  # نقطة 9 — عيد ميلاد هادي
        birthday_loop.start()
    try:  # F8: على سيرفر جديد knowledge/sprints.md مش موجود لحد ما التايمر يشتغل
        if not (BASE_DIR / "knowledge" / "sprints.md").exists():
            import sprints_sync
            await asyncio.to_thread(sprints_sync.write_default)
            print("HADI SPRINTS: knowledge/sprints.md اتولّد عند الإقلاع")
    except Exception as error:
        print(f"HADI SPRINTS: توليد sprints.md فشل ({type(error).__name__}: {error})")
    print(f"HADI HEARTBEAT: {'on' if heartbeat.ENABLED else 'off'}"
          f" (كل ساعة | هدوء {heartbeat.QUIET_START}:00-{heartbeat.QUIET_END}:00"
          f" | cooldown {heartbeat.COOLDOWN_H:g}س | حد أقصى {heartbeat.MAX_ALERTS} تنبيهات)")


STATUS_EDIT_INTERVAL = max(2.0, float(os.getenv("HADI_STATUS_EDIT_INTERVAL", "5") or "5"))
STATUS_TICK_SECONDS = 15.0


def _fmt_elapsed(seconds: float) -> str:
    minutes, secs = divmod(int(max(0.0, seconds)), 60)
    return f"{minutes}:{secs:02d}"


class StatusReporter:
    """بند 3.4 + نقطة 3 — رسالة الحالة الحية: «⏳ ماشي…» فورية بدل الصمت الطويل.

    (كانت معطلة بـ return مبكر — F1 في الأوديت — رجعت تشتغل بقرار آسر.)

    - بتتبعت فور استلام الطلب (أو «في الطابور» لو في طلب قبله في نفس المحادثة).
    - بتتحدث بالنشاط الحقيقي من المحرك عبر on_progress (بكلم Azure DevOps /
      ببحث على النت / بكتب الرد...) + الزمن المنقضي — مش نص ثابت.
    - احترام rate limits: أقصى تعديل كل HADI_STATUS_EDIT_INTERVAL ثانية (افتراضي 5 —
      أقل بكتير من حد Discord ~5 تعديلات/5 ثواني للقناة)، وticker كل 15 ثانية
      بيحدّث الزمن حتى من غير أحداث (مسار الـ CLI مثلًا).
    - بتتمسح دايمًا مع نهاية المعالجة (رد أو NO_REPLY أو خطأ) — الرد بيوصل كريبلاي
      عادي، فقرار الصمت بيفضل صامت ومفيش محتوى جزئي بيتسرب.
    - visible=False (الرسايل الـ ambient): مفيش رسالة حالة خالص — محدش نادى هادي
      فمفيش داعي يعلن إنه شغال؛ لو قرر يرد، الرد بيوصل لوحده.
    """

    def __init__(self, message: discord.Message, visible: bool = True):
        self._message = message
        self._visible = visible
        self._note = None
        self._t0 = time.time()
        self._activity = "بجهّز السياق وبفكر"
        self._dirty = False
        self._done = False
        self._last_edit = 0.0
        self._task = None

    async def start(self, first_line: str) -> None:
        if not self._visible:
            return
        try:
            self._note = await self._message.channel.send(f"⏳ {first_line}")
            self._last_edit = time.time()
        except Exception as error:
            print(f"STATUS START ERROR: {type(error).__name__}: {error}")
            self._note = None
        self._task = asyncio.create_task(self._ticker())

    def on_engine_event(self, label: str) -> None:
        """بيتنادى من hadi_engine مع كل نشاط — التسجيل هنا والتعديل في الـ ticker."""
        label = (label or "").strip()
        if label and label != self._activity:
            self._activity = label
            self._dirty = True

    async def _ticker(self) -> None:
        try:
            while not self._done:
                await asyncio.sleep(1.0)
                if self._done or self._note is None:
                    continue
                now = time.time()
                since = now - self._last_edit
                due_event = self._dirty and since >= STATUS_EDIT_INTERVAL
                due_tick = since >= STATUS_TICK_SECONDS
                if not (due_event or due_tick):
                    continue
                self._dirty = False
                self._last_edit = now
                text = f"⏳ شغال ({_fmt_elapsed(now - self._t0)}) — {self._activity}…"
                try:
                    await self._note.edit(content=text)
                except discord.NotFound:  # حد مسحها يدوي — كمّل من غير رسالة حالة
                    self._note = None
                except Exception as error:
                    print(f"STATUS EDIT ERROR: {type(error).__name__}: {error}")
        except asyncio.CancelledError:
            pass

    async def finish(self) -> None:
        """بتتنادى في الـ finally دايمًا — توقف التحديثات وتمسح رسالة الحالة."""
        self._done = True
        if self._task is not None:
            self._task.cancel()
        note, self._note = self._note, None
        if note is not None:
            try:
                await note.delete()
            except Exception:
                pass


@tasks.loop(hours=1)
async def heartbeat_loop():
    """بند 8.1/8.3 — نبضة الاستباقية: فحوصات مجدولة، والصمت لو مفيش حاجة.

    نفس فلسفة NO_REPLY: تنبيه من غير داعي أسوأ من مفيش تنبيه، لأنه بيخلي الفريق
    يتجاهل التنبيهات كلها. الضوابط (cooldown / ساعات الهدوء / حد أقصى للتنبيهات)
    كلها جوه heartbeat.py وقابلة للضبط من .env."""
    heartbeat.touch_alive()   # للـ watchdog — بيتحدث حتى في ساعات الهدوء
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


@tasks.loop(hours=4)
async def sprint_watch_loop():
    """نقطة 2 — وعي السبرنت: سبرنت جديد → DM لآسر بمواعيد الإيفنتات المتوقعة
    للتصحيح. نهاية السبرنت اتغيرت في ADO → تأكيد من آسر. مرة واحدة لكل حدث.

    نقطة 3 (كانبان): التنبيهات دي متوقفة طالما sprint_watch=false في
    process_state.json — عشان هادي مايفضلش يكرّر السؤال عن سبرنت احنا وقفناه."""
    if not process_state.sprint_watch_enabled():
        return
    try:
        s = await asyncio.to_thread(sprint_intake.check_status)
    except Exception as error:
        print(f"SPRINT WATCH FAIL: {type(error).__name__}: {error}")
        return
    if not s.get("sprint"):
        return
    try:
        if s.get("new_sprint"):
            msg = await asyncio.to_thread(
                sprint_intake.compose_dm, s["sprint"], s["start"], s["finish"]
            )
            await dm_allowed_users(msg)
            await asyncio.to_thread(sprint_intake.mark_seen, s["sprint"], s["finish"])
            print(f"SPRINT WATCH: سألت آسر عن إيفنتات {s['sprint']}")
        elif s.get("finish_changed"):
            await dm_allowed_users(
                f"📅 لاحظت إن تاريخ نهاية سبرنت {s['sprint']} اتغير في ADO: "
                f"{s['old_finish']} → {s['finish']}.\n"
                "ده تمديد للدورة ولا تعديل؟ وهل الريليز اتحرك؟ — رد عليا وأنا هحدّث "
                "المواعيد وأبقى فاكرها."
            )
            await asyncio.to_thread(sprint_intake.mark_seen, s["sprint"], s["finish"])
            print(f"SPRINT WATCH: نبهت آسر لتغيير نهاية {s['sprint']}")
    except Exception as error:
        print(f"SPRINT WATCH DM FAIL: {type(error).__name__}: {error}")


@sprint_watch_loop.before_loop
async def _before_sprint_watch_loop():
    await client.wait_until_ready()


@tasks.loop(minutes=30)
async def birthday_loop():
    """نقطة 9 — عيد ميلاد هادي (1 أغسطس): رسالة صباحية واحدة في قناة
    8orders-issues (اختيار آسر)، مرة واحدة في السنة (marker في logs/)."""
    try:
        if not identity.should_post_now():
            return
        ch = (client.get_channel(identity.BIRTHDAY_CHANNEL_ID)
              or await client.fetch_channel(identity.BIRTHDAY_CHANNEL_ID))
        await ch.send(identity.birthday_message())
        identity.mark_posted()
        print(f"BIRTHDAY: هادي بقى {identity.age()} سنة — الرسالة اتبعتت 🎂")
    except Exception as error:
        print(f"BIRTHDAY LOOP FAIL: {type(error).__name__}: {error}")


@birthday_loop.before_loop
async def _before_birthday_loop():
    await client.wait_until_ready()


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """بند 5.3: رياكشن على رد هادي = تقييم بشري مجاني (أرخص إشارة جودة متاحة).

    attach_feedback بيرجّع False لو الرسالة مش رد من ردود هادي المسجلة — فالرياكشنز
    على رسايل الناس العادية بتتجاهل لوحدها."""
    if client.user and payload.user_id == client.user.id:
        return
    if eval_store.attach_feedback(payload.message_id, str(payload.emoji), payload.user_id):
        print(f"EVAL FEEDBACK: {payload.emoji} على رد #{payload.message_id}")
        # نقطة 7 (قرار آسر): فيدباك سلبي من التيم → تنبيه فوري لآسر في الـ DM،
        # مش مستني تقرير الأسبوع.
        try:
            if str(payload.emoji) in eval_store.NEGATIVE:
                info = eval_store.interaction_for_reply(payload.message_id)
                if info:
                    _spawn(dm_allowed_users(
                        f"👎 فيدباك سلبي على رد ليا ({payload.emoji}) في "
                        f"{info.get('channel', '?')}\n"
                        f"السؤال: {(info.get('prompt_excerpt') or '')[:180]}\n"
                        f"ردّي: {(info.get('reply_excerpt') or '')[:300]}\n"
                        "هحطها في اعتباري — والتفاصيل في تقرير الـ evals الأسبوعي."
                    ))
        except Exception as _nf:
            print(f"NEGATIVE FEEDBACK ALERT ERROR: {type(_nf).__name__}: {_nf}")


@client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """شيل الرياكشن = سحب التقييم."""
    if client.user and payload.user_id == client.user.id:
        return
    eval_store.remove_feedback(payload.message_id, str(payload.emoji), payload.user_id)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # الرسائل الخاصة DM فقط حاليًا
    if message.guild is None:
        if message.author.id not in ALLOWED_USER_IDS:
            await message.channel.send("الحساب ده غير مصرح له باستخدام هادي.")
            return
        author_name = message.author.display_name
        content = message.content.strip()
    else:
        if (
            message.guild.id != HADAF_GUILD_ID
            or message.channel.id not in AUTHORIZED_CHANNEL_IDS
        ):
            return

        # أي رسالة في القناة المصرح بها تجدّد الـ TTL — هادي ممكن يكون مراقب
        # بصمت (ambient) ومحتاج جلسته تفضل حية حتى لو ما ردّش.
        _ch_key = f"ch:{message.channel.id}"
        hadi_engine.touch_session(_ch_key)

        mentioned = client.user in message.mentions
        named = NAME_TRIGGER and is_addressed_to_hadi(message.clean_content)
        replying_to_hadi = bool(
            message.reference
            and message.reference.resolved
            and getattr(message.reference.resolved, "author", None)
            and message.reference.resolved.author.id == client.user.id
        )

        # ريبلاي على رسالة هادي محتواه مجرد منشن/تاج لحد تاني ("@Amr Atef")
        # أو إيموجي بس → مش موجه لهادي، تجاهل تمامًا من غير أي رد.
        if replying_to_hadi and not (mentioned or named):
            residue = re.sub(
                r"<a?:\w+:\d+>|<@!?\d+>|<@&\d+>|<#\d+>",
                "",
                message.content or "",
            ).strip(" \t\r\n.,!?؟،~ـ-")
            if not residue:
                return

        author_name = message.author.display_name
        content = message.clean_content.strip()

    # الرسالة المحوّلة (Forward) بتوصل بـ content فاضي — محتواها الحقيقي في الـ snapshots.
    # من غير السطور دي هادي كان بيرد على أي فورورد بـ "ابعت رسالة نصية."
    ack_emoji = pick_reaction(content)
    try:
        if ack_emoji and (message.guild is None or mentioned or named or replying_to_hadi):
            await message.add_reaction(ack_emoji)
    except Exception:
        pass

    forwarded_text = extract_forwarded_text(message)
    if forwarded_text:
        forward_block = f"[رسالة محوّلة (Forward) — محتواها]:\n{forwarded_text}"
        content = f"{content}\n\n{forward_block}" if content else forward_block

    # بند 9: ترياج القناة — «اقرأ وحلل الرسايل والصور وارفع الإيشيوز تيكتات».
    # بيشتغل بس لما الرسالة موجّهة لهادي (منشن/نداء/ريبلاي) + فيها نية ترياج واضحة،
    # عشان ميفيرش على كل رسالة. مفيش تأكيد بشري (قرار آسر): هادي يجمّع → يراجع →
    # يقيّم نفسه → يرفع (Customer Issue/Change Request حسب المحتوى) → يرجّع لينكات.
    # أي خطأ بيتبلّغ صراحةً — مش بيسقط للمسار العام (اللي كان بيرفع تيكتات غلط).
    if message.guild is not None and (mentioned or named or replying_to_hadi):
        try:
            import channel_triage as _ct
            if _ct.is_trigger(content):
                # «من اول الرسالة ده» — لو ريبلاي، ابدأ من توقيت الرسالة المرجعية
                _anchor = None
                _ref = message.reference
                if _ref is not None:
                    _rep = _ref.resolved
                    if _rep is None or isinstance(_rep, discord.DeletedReferencedMessage):
                        try:
                            _rep = await message.channel.fetch_message(_ref.message_id)
                        except Exception:
                            _rep = None
                    if _rep is not None and not isinstance(_rep, discord.DeletedReferencedMessage):
                        _anchor = _rep.created_at
                async with message.channel.typing():
                    _msg = await _ct.run_triage(message.channel, client, hadi_engine, since_dt=_anchor)
                await send_long_message(message.channel, _msg, reply_to=message)
                return
        except Exception as _cte:
            print("channel_triage error:", _cte)
            await send_long_message(
                message.channel,
                f"حصل خطأ أثناء ترياج القناة: {type(_cte).__name__}. جرّب تاني أو بلّغ آسر.",
                reply_to=message,
            )
            return
    # ب-2 (2026-07-26): معالجة الميديا اتأخّرت لبعد بوابة الحضور.
    # الغلط القديم: تنزيل الصور واستخراج الفريمات والتفريغ كانوا بيحصلوا هنا
    # **قبل** البوابة، والشرط `and not image_paths` كان بيخلي أي رسالة فيها
    # مرفق **تتخطى البوابة بالكامل** وتروح للموديل الكامل — يعني أي سكرين شوت
    # في القناة (وقناة 8orders-issues طبيعتها كده) بيشغّل Sonnet + vision،
    # وسقف الردود الـ ambient (2/ساعة) ماكانش بيتفحص أصلًا.
    # الدليل: رسالتين ambient في logs وصلوا للموديل والبوابة سمحت بواحدة بس.
    #
    # الإشارة دي مجانية — قراءة metadata من كائن الرسالة، مفيش أي نداء شبكة.
    has_media = any(_is_image_attachment(a) or _is_video_attachment(a)
                    for a in (message.attachments or []))
    media_hint = "\n[الرسالة معاها مرفق ميديا]" if has_media else ""
    if not content and not has_media and not message.attachments:
        # رسالة فاضية تمامًا (ستيكر/نوع غير مدعوم): رد بس لو موجّهة لهادي، وإلا صمت تام
        # (منع سبام «ابعت رسالة نصية» على كل ستيكر في القناة).
        if message.guild is None or mentioned or named or replying_to_hadi:
            await message.channel.send("مفيش نص في رسالتك — ابعتلي التفاصيل بالكتابة.")
        return
    if content.lower() == "!ping":
        await message.channel.send("HADI_OK")
        return

    # السياق (آخر الرسايل + الريبلاي) بيتبني للـ DM والقنوات على حد سواء —
    # قبل كده كان بيتبني للقنوات بس، فهادي كان بيرد في الـ DM من غير أي سياق.
    # نقطة 1 — الحضور الذكي 24/7: بوابة ثلاثية (صامت/رياكشن/رد) للرسايل غير الموجهة
    # لهادي. Pre-filter محلي → قرار Haiku واحد بسياق → REPLY بس بيوصل للموديل الكامل.
    # الضوابط (سقف الردود/كولداون الرياكشن) والتسجيل جوه ambient_gate.py.
    ambient = (message.guild is not None
               and not (mentioned or named or replying_to_hadi))

    # نقطة 4 — استمرار المحادثة: لو هادي اتكلم في القناة من فترة قريبة والرسالة مش
    # موجّهة لحد تاني (مفيش منشن ولا ريبلاي لشخص غيره)، اعتبرها متابعة ليه — رد فوري
    # زي الإنسان من غير منشن ومن غير سقف الردّين/ساعة. المحرك نفسه بيقرر NO_REPLY لو
    # طلعت مش ليه، فمفيش اقتحام لكلام الناس مع بعضها.
    continuation = False
    if ambient and CONTINUATION_WINDOW_S > 0:
        _since = time.time() - _last_hadi_reply.get(message.channel.id, 0.0)
        _other_mention = any(u.id != client.user.id for u in (message.mentions or []))
        _ref = message.reference.resolved if message.reference else None
        _ref_other = bool(_ref and getattr(_ref, "author", None)
                          and _ref.author.id != client.user.id)
        continuation = (_since < CONTINUATION_WINDOW_S
                        and not _other_mention and not _ref_other)

    # نقطة 4 — بلاغ مشكلة: يوصل للمحرك يحلّل ويرفع تذكرة حتى من غير منشن، ومن غير ما
    # يتحسب على سقف الردّين/ساعة (البلاغات ماينفعش تتسكت بسبب السقف).
    force_issue = bool(ambient and _looks_like_issue(content))

    if ambient and not (continuation or force_issue):
        if not ambient_gate.enabled():
            return
        try:
            gate_history = await build_channel_history(
                message.channel, message, limit=ambient_gate.HISTORY_N
            )
            g_action, g_emoji = await ambient_gate.decide(
                hadi_engine, content + media_hint, author_name, str(message.author.id),
                message.channel.id, getattr(message.channel, "name", "?"),
                gate_history,
            )
        except Exception as _hg:
            print("ambient-gate error:", _hg)
            return
        if g_action == "react" and g_emoji:
            try:
                await message.add_reaction(g_emoji)
                print(f"HADI: ambient react {g_emoji} - {author_name}: {content[:60]}")
            except Exception as _re:
                print(f"AMBIENT REACT ERROR: {type(_re).__name__}: {_re}")
            return
        if g_action != "reply":
            print("HADI: ambient-gate silent -", author_name)
            return
    # الميديا بتتنزّل هنا — بعد ما اتأكدنا إن الرسالة مستحقة معالجة كاملة.
    image_paths = await save_image_attachments(message)
    frame_paths, video_notes = await save_video_frames(message)
    image_paths = image_paths + frame_paths
    manifest = media_manifest(message)
    media_notes = "\n".join(([manifest] if manifest else []) + video_notes)
    if not content and not image_paths and not media_notes:
        # رسالة فاضية تمامًا (ستيكر/نوع غير مدعوم): رد بس لو موجّهة لهادي، وإلا صمت
        if message.guild is None or mentioned or named or replying_to_hadi:
            await message.channel.send("مفيش نص في رسالتك — ابعتلي التفاصيل بالكتابة.")
        return
    if not content:
        content = "(بعت مرفقات من غير نص — بص على الصور وبيانات الميديا المرفقة ورد بناء عليها)"

    # سياق القناة: **الرسايل اللي حصلت من آخر مرة هادي اتكلم فيها** (ب-1).
    # (resume) شايلة المحادثة كلها، فإعادة إرسال آخر HISTORY_LIMIT رسالة مع كل
    # دور كانت بتضاعف نفس النص في السياق من غير أي فايدة.
    _conv_key_early = (f"dm:{message.author.id}" if message.guild is None
                       else f"ch:{message.channel.id}")
    _cursor = hadi_engine.session_cursor(_conv_key_early)
    if _cursor is None:
        # جلسة جديدة: دفعة السياق الكاملة زي الأول بالظبط
        history_text = await build_channel_history(message.channel, message)
    else:
        # جلسة شغالة: الرسايل اللي حصلت من آخر مرة هادي اتكلم فيها بس
        history_text = await build_channel_history_after(
            message.channel, message, after_id=_cursor)
    try:
        _docn = await file_extract.extract_attachment_texts(message)
        if _docn:
            media_notes = (media_notes + chr(10) + chr(10).join(_docn)) if media_notes else chr(10).join(_docn)
    except Exception as _fe:
        print("file-extract error:", _fe)
    reply_context = await build_reply_context(message)
    channel_label = (
        f"#{getattr(message.channel, 'name', '?')} (channel_id: {message.channel.id})"
        if message.guild is not None
        else "رسالة خاصة (DM)"
    )

    conv_key = (
        f"dm:{message.author.id}"
        if message.guild is None
        else f"ch:{message.channel.id}"
    )
    conv_lock = get_conv_lock(conv_key)
    # نقطة 3: رسالة الحالة الحية بتظهر بس لما حد فعلًا نادى هادي (منشن/اسم/ريبلاي/DM)
    # — الرسايل الـ ambient بتتعالج في صمت والرد بيوصل لوحده لو هادي قرر يتكلم.
    status = StatusReporter(message, visible=not ambient)
    eval_stats: dict = {}  # بند 5.3: المحرك بيملاها بالتوكنز والتكلفة
    _t0 = time.time()
    if conv_lock.locked():
        status.on_engine_event("مستني دوري — في طلب تاني شغال في نفس المحادثة")
        await status.start("في الطابور — قدّامي طلب تاني في نفس المحادثة، وهبدأ في طلبك أول ما يخلص.")
    else:
        await status.start("ماشي — مسكت طلبك وشغال عليه، وهوافيك بالرد أول ما يخلص.")
    async with conv_lock:
        status.on_engine_event("بجهّز السياق وبفكر")
        try:
            async with message.channel.typing():
                _t0 = time.time()
                response = await ask_claude(
                    content,
                    author_name,
                    history_text,
                    reply_context,
                    channel_label,
                    image_paths,
                    str(message.id),
                    media_notes,
                    author_id=str(message.author.id),
                    conv_key=conv_key,
                    on_progress=status.on_engine_event,
                    stats=eval_stats,
                )

            print(f"HADI: claude run {time.time()-_t0:.0f}s - {author_name}: {content[:60]}")
            resp_clean = (response or "").strip()
            react_emoji, resp_clean = split_react_directive(resp_clean)
            _spawn(swap_ack_reaction(message, ack_emoji, react_emoji))
            if not resp_clean or (
                resp_clean[:8].upper() == "NO_REPLY" and len(resp_clean) <= 40
            ):
                eval_store.record_interaction(
                conv_key=conv_key,
                channel=channel_label,
                author=author_name,
                user_message_id=message.id,
                prompt=content,
                latency_ms=int((time.time() - _t0) * 1000),
                stats=eval_stats,
                engine=hadi_engine.describe().split()[0],
                outcome="no_reply",
                )
                hadi_engine.mark_processed(conv_key, message.id)
                print(f"HADI: NO_REPLY skip — {author_name}: {content[:80]}")
                # F18: «الصمت قرار» يعني صمت كامل — رياكشن الاستلام المبدئي بيتشال
                # عشان مايفضلش أثر لتفاعل اتقرر إلغاؤه.
                if ack_emoji:
                    try:
                        me = message.guild.me if message.guild else client.user
                        if me:
                            await message.remove_reaction(ack_emoji, me)
                    except Exception:
                        pass
                return

            sent = await send_long_message(
                message.channel,
                resp_clean,
                reply_to=message if message.guild is not None else None,
            )
            hadi_engine.mark_processed(conv_key, message.id)
            # الرد اتبعت فعلًا → بيتحسب على سقف الـ ambient بتاع القناة. بس
            # الاستمرار وبلاغات المشاكل بيتخطّوا السقف عمدًا (مش بيتحسبوا).
            if ambient and not (continuation or force_issue):
                ambient_gate.note_reply(message.channel.id)
            eval_store.record_interaction(
                conv_key=conv_key,
                channel=channel_label,
                author=author_name,
                user_message_id=message.id,
                prompt=content,
                latency_ms=int((time.time() - _t0) * 1000),
                stats=eval_stats,
                engine=hadi_engine.describe().split()[0],
                reply_message_id=getattr(sent, "id", ""),
                reply=resp_clean,
                outcome="replied",
            )

        except hadi_engine.EngineUnavailable as error:
            # رصيد Claude خلص أو الـ CLI مسجّل خارج. حادثة 2026-07-23: هادي كان
            # واقع من 9ص لـ 1م اليوم اللي بعده والمستخدم شاف «EngineError» بس
            # ومحدش اتبلّغ. الفئة دي محتاجة تبليغ + رسالة مفهومة.
            eval_store.record_interaction(
                conv_key=conv_key, channel=channel_label, author=author_name,
                user_message_id=message.id, prompt=content,
                latency_ms=int((time.time() - _t0) * 1000), stats=eval_stats,
                engine=hadi_engine.describe().split()[0],
                outcome="error", error_type="EngineUnavailable",
                error_msg=str(error)[:300],
            )
            print(f"ENGINE UNAVAILABLE: {error}")
            _spawn(_alert_engine_down(str(error)))
            if (message.guild is None or mentioned or named or replying_to_hadi):
                await message.reply(
                    "مش قادر أشتغل دلوقتي — الرصيد بتاعي خلص أو الجلسة محتاجة "
                    "تسجيل دخول. بلّغت آسر، وهرجع أول ما يتصلح.",
                    mention_author=False,
                )

        except hadi_engine.EngineTimeout:
            eval_store.record_interaction(
                conv_key=conv_key,
                channel=channel_label,
                author=author_name,
                user_message_id=message.id,
                prompt=content,
                latency_ms=int((time.time() - _t0) * 1000),
                stats=eval_stats,
                engine=hadi_engine.describe().split()[0],
                outcome="timeout",
                error_type="EngineTimeout",
                error_msg=f"عدّى {900}s من غير رد",
            )
            print(f"HADI: TIMEOUT (900s) - {author_name}: {content[:60]}")
            if (message.guild is None or mentioned or named or replying_to_hadi): await message.reply(
                "الطلب خد وقت أطول من الحد المسموح (15 دقيقة) واتوقف. لو كان طلب تيكت، راجع البورد الأول قبل ما تكرر الطلب.",
                mention_author=False,
            )

        except Exception as error:
            eval_store.record_interaction(
                conv_key=conv_key,
                channel=channel_label,
                author=author_name,
                user_message_id=message.id,
                prompt=content,
                latency_ms=int((time.time() - _t0) * 1000),
                stats=eval_stats,
                engine=hadi_engine.describe().split()[0],
                outcome="error",
                error_type=type(error).__name__,
                error_msg=str(error)[:300],
            )
            print(f"ERROR: {type(error).__name__}: {error}")
            if (message.guild is None or mentioned or named or replying_to_hadi): await message.reply(
                f"حصل خطأ أثناء تشغيل هادي: {type(error).__name__}",
                mention_author=False,
            )


        finally:
            await status.finish()
            for _p in image_paths:
                try:
                    Path(_p).unlink()
                except OSError:
                    pass

if __name__ == "__main__":  # بند 5.3: الاستيراد من eval_runner مايشغلش البوت
    # حارس العملية الواحدة (2026-07-26). حادثة 2026-07-23: عمليتين اشتغلوا مع
    # بعض (واحدة من systemd وواحدة يدوية سايبة) → الاتنين استقبلوا كل رسالة →
    # رد مكرر، تذكرتين لنفس الطلب، وردود متناقضة (كل عملية بجلسة مختلفة).
    # asyncio.Lock و ambient_gate._Limiter بيحميوا جوّه العملية بس، فمفيش
    # حاجة كانت بتمنع ده.
    if not state_lock.acquire_singleton("hadi-discord"):
        raise SystemExit(1)
    client.run(TOKEN)
