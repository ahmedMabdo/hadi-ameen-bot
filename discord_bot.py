import asyncio
import os
import re
import subprocess
from pathlib import Path

import discord
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

# الرد على النداء بالاسم من غير مينشن (هادي / يا هادي / Hadi) — on افتراضيًا.
# للتعطيل: NAME_TRIGGER=off في .env
NAME_TRIGGER = os.getenv("NAME_TRIGGER", "on").strip().lower() not in {
    "0", "off", "false", "no",
}

# نداء صريح فقط — عشان كلمة "هادي" كصفة ("الوضع هادي") متشغلش البوت:
#   - "هادي..." أو "يا هادي..." أو "هادي أمين..." في أول الرسالة
#   - "يا هادي" في أي مكان في الرسالة (صيغة نداء صريحة)
#   - "Hadi" / "ya hadi" بنفس المنطق
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


def ask_claude(
    user_message: str,
    author_name: str,
    history: str = "",
    reply_context: str = "",
) -> str:
    history_block = (
        f"""
آخر رسايل القناة دي (الأقدم فالأحدث) — سياق فقط، دوّر فيها قبل ما تقول "مش لاقي معلومة".
رسايلك انت معلّمة بـ [هادي (أنت)] — استخدمها عشان تفهم لو الطلب الحالي متابعة لحاجة انت عملتها:
{history}
"""
        if history
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

اللي بعت الرسالة الحالية هو: {author_name}. رد عليه/عليها بالاسم ده تحديدًا،
ومتفترضش إنها من آسر إلا لو {author_name} هو آسر بالفعل.
{reply_block}{history_block}
رسالة {author_name}:
{user_message}
""".strip()

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
        timeout=300,
        check=False,
    )

    if result.returncode != 0:
        error = (result.stderr or result.stdout).strip()
        raise RuntimeError(error[-1500:] or "Claude لم يُرجع نتيجة")

    return result.stdout.strip()


async def build_channel_history(channel, before_message, limit: int = HISTORY_LIMIT) -> str:
    """يقرا آخر رسايل القناة قبل الرسالة الحالية عشان هادي يفهم سياق المحادثة.

    بيستبعد رسايل البوتات التانية، لكن بيدخّل رسايل هادي نفسه (معلّمة
    بـ "هادي (أنت)") — من غيرها هادي مش بيشوف ردوده، وأي متابعة زي
    "اعملها 48 ساعة" بتوصله من غير التقرير اللي المفروض يتعدل."""
    lines = []
    try:
        async for prev in channel.history(limit=limit, before=before_message):
            if prev.author.bot and prev.author.id != client.user.id:
                continue
            text = prev.clean_content.strip()
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
            # رد مباشر (Discord reply) على رسالة الشخص اللي نادى هادي تحديدًا
            await reply_to.reply(chunk, mention_author=False)
        else:
            await channel.send(chunk)


@client.event
async def on_ready():
    print(f"HADI ONLINE: {client.user} | ID: {client.user.id}")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    history_text = ""
    reply_context = ""

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
        # ريبلاي مباشر على رسالة هادي = استكمال محادثة، حتى من غير مينشن ولا اسم
        replying_to_hadi = bool(
            message.reference
            and message.reference.resolved
            and getattr(message.reference.resolved, "author", None)
            and message.reference.resolved.author.id == client.user.id
        )
        if not (mentioned or named or replying_to_hadi):
            return

        author_name = message.author.display_name
        content = message.clean_content.strip()

    if not content:
        await message.channel.send("ابعت رسالة نصية.")
        return

    if content.lower() == "!ping":
        await message.channel.send("HADI_OK")
        return

    if message.guild is not None:
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

            await send_long_message(
                message.channel,
                response,
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
