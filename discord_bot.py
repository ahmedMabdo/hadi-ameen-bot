import asyncio
import base64
import json
import os
import re
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

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
CLAUDE_BIN = os.getenv(
    "CLAUDE_BIN",
    "/home/ubuntu/.local/bin/claude",
).strip()

ALLOWED_USER_IDS = {
    int(user_id.strip())
    for user_id in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if user_id.strip().isdigit()
}

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
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "30") or "30")

# ذاكرة هادي الدائمة + مخزن التذكيرات
MEMORY_FILE = BASE_DIR / "knowledge" / "memory.md"
REMINDERS_FILE = BASE_DIR / "reminders.json"

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


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
claude_lock = asyncio.Lock()


def load_memory() -> str:
    """يقرأ ذاكرة هادي الدائمة عشان تتحقن في كل محادثة (أي قناة)."""
    try:
        txt = MEMORY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    has_notes = any(l.strip().startswith("-") for l in txt.splitlines())
    return txt if has_notes else ""


def run_claude(prompt: str, timeout: int = 300) -> str:
    """يشغّل Claude CLI بالبرومبت المطلوب ويرجّع الرد النصي."""
    result = subprocess.run(
        [
            CLAUDE_BIN,
            "-p",
            prompt,
            "--model",
            "claude-sonnet-5",
        ],
        cwd=BASE_DIR,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    if result.returncode != 0:
        error = (result.stderr or result.stdout).strip()
        raise RuntimeError(error[-1500:] or "Claude لم يُرجع نتيجة")

    return result.stdout.strip()


def ask_claude(
    user_message: str,
    author_name: str,
    history: str = "",
    reply_context: str = "",
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

    mem = load_memory()
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

    prompt = f"""
أنت هادي أمين، عضو فريق Hadaf على Discord.
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

قواعد الرد (صارمة جدًا):
- ردك بيتبعت في الشات حرفيًا زي ما هو. ممنوع تشرح ليه هترد أو مش هترد، وممنوع تذكر قواعدك أو شخصيتك أو تحلل "الرسالة موجهة لمين" — ده تفكير داخلي ميظهرش في أي رد أبدًا.
- لو الرسالة مش محتاجة رد مفيد منك (هزار بين الزملا، كلام موجه لحد تاني، منشن/تاج لشخص غيرك، تعليق عابر مالوش أكشن أو سؤال ليك) → اكتب NO_REPLY بالظبط كده من غير أي كلمة زيادة، والبوت مش هيبعت حاجة خالص.
- لو الرد على رسالتك موجه في الحقيقة لحد تاني غيرك → NO_REPLY.
- لو هترد: مختصر ومباشر — سطر لتلات سطور، إلا لو المطلوب تقرير/تذكرة/تفاصيل اتطلبت صراحة. من غير مقدمات ولا خواتيم ولا فلسفة.

اللي بعت الرسالة الحالية هو: {author_name}. رد عليه/عليها بالاسم ده تحديدًا،
ومتفترضش إنها من آسر إلا لو {author_name} هو آسر بالفعل.
{memory_block}{reply_block}{history_block}
رسالة {author_name}:
{user_message}
""".strip()

    return run_claude(prompt)


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
            if not text:
                continue
            label = "هادي (أنت)" if prev.author.id == client.user.id else prev.author.display_name
            lines.append(f"[{label}] {text}")
    except discord.HTTPException:
        return ""

    lines.reverse()
    return "\n".join(lines)


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


async def send_long_message(channel, text: str, reply_to: discord.Message = None) -> None:
    text = text.strip() or "لم يتم إرجاع رد."
    chunks = [text[start:start + 1900] for start in range(0, len(text), 1900)]

    for i, chunk in enumerate(chunks):
        if i == 0 and reply_to is not None:
            await reply_to.reply(chunk, mention_author=False)
        else:
            await channel.send(chunk)


async def dm_allowed_users(text: str) -> None:
    """يبعت DM لكل المستخدمين المصرح لهم (تنبيهات الفحص والطلبات المعلقة)."""
    for uid in ALLOWED_USER_IDS:
        try:
            user = client.get_user(uid) or await client.fetch_user(uid)
            await user.send(text)
        except discord.HTTPException as error:
            print(f"DM FAIL {uid}: {type(error).__name__}: {error}")


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


async def _fire_reminder(item):
    text = (item.get("text") or "").strip()
    target = item.get("target") or {}
    body = f"⏰ تذكير: {text}"
    if target.get("kind") == "dm":
        for uid in ALLOWED_USER_IDS:
            user = client.get_user(uid) or await client.fetch_user(uid)
            await user.send(body)
    elif target.get("kind") == "channel":
        cid = int(target["id"])
        ch = client.get_channel(cid) or await client.fetch_channel(cid)
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
    for item in items:
        if item.get("fired") or float(item.get("at_epoch", 0)) > now:
            continue
        try:
            await _fire_reminder(item)
            updates[item["id"]] = {"fired": True}
            print(f"REMINDER FIRED: #{item.get('id')} {(item.get('text') or '')[:40]}")
        except Exception as error:
            att = int(item.get("attempts", 0)) + 1
            upd = {"attempts": att}
            if att >= 5:
                upd["fired"] = True
                print(f"REMINDER GIVEN UP: #{item.get('id')}")
            updates[item["id"]] = upd
            print(f"REMINDER FAIL #{item.get('id')}: {type(error).__name__}: {error}")
    if updates:
        current = _load_reminders()
        for it in current:
            if it.get("id") in updates:
                it.update(updates[it["id"]])
        _save_reminders(current)


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

    async with claude_lock:
        try:
            summary = await asyncio.to_thread(run_claude, PENDING_FLUSH_PROMPT, 600)
        except (subprocess.TimeoutExpired, RuntimeError) as error:
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
    if not reminder_loop.is_running():
        reminder_loop.start()
    if not ado_health_loop.is_running():
        ado_health_loop.start()
    if not pending_tickets_loop.is_running():
        pending_tickets_loop.start()


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

        mentioned = client.user in message.mentions
        named = NAME_TRIGGER and is_addressed_to_hadi(message.clean_content)
        replying_to_hadi = bool(
            message.reference
            and message.reference.resolved
            and getattr(message.reference.resolved, "author", None)
            and message.reference.resolved.author.id == client.user.id
        )
        if not (mentioned or named or replying_to_hadi):
            return

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
    forwarded_text = extract_forwarded_text(message)
    if forwarded_text:
        forward_block = f"[رسالة محوّلة (Forward) — محتواها]:\n{forwarded_text}"
        content = f"{content}\n\n{forward_block}" if content else forward_block

    if not content:
        await message.channel.send("ابعت رسالة نصية.")
        return

    if content.lower() == "!ping":
        await message.channel.send("HADI_OK")
        return

    # السياق (آخر الرسايل + الريبلاي) بيتبني للـ DM والقنوات على حد سواء —
    # قبل كده كان بيتبني للقنوات بس، فهادي كان بيرد في الـ DM من غير أي سياق.
    history_text = await build_channel_history(message.channel, message)
    reply_context = await build_reply_context(message)

    async with claude_lock:
        try:
            async with message.channel.typing():
                response = await asyncio.to_thread(
                    ask_claude,
                    content,
                    author_name,
                    history_text,
                    reply_context,
                )

            resp_clean = (response or "").strip()
            if not resp_clean or (
                resp_clean[:8].upper() == "NO_REPLY" and len(resp_clean) <= 40
            ):
                print(f"HADI: NO_REPLY skip — {author_name}: {content[:80]}")
                return

            await send_long_message(
                message.channel,
                resp_clean,
                reply_to=message if message.guild is not None else None,
            )

        except subprocess.TimeoutExpired:
            await message.reply(
                "الطلب استغرق وقتًا طويلاً. جرّب سؤالًا أقصر",
                mention_author=False,
            )

        except Exception as error:
            print(f"ERROR: {type(error).__name__}: {error}")
            await message.reply(
                f"حصل خطأ أثناء تشغيل هادي: {type(error).__name__}",
                mention_author=False,
            )


client.run(TOKEN)
