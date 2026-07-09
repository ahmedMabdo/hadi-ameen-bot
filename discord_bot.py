import asyncio
import os
from pathlib import Path

import discord
from anthropic import Anthropic, APITimeoutError
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5").strip() or "claude-sonnet-5"
CLAUDE_TIMEOUT_SECONDS = float(os.getenv("CLAUDE_TIMEOUT_SECONDS", "300") or 300)

ALLOWED_USER_IDS = {
    int(user_id.strip())
    for user_id in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if user_id.strip().isdigit()
}

if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN غير موجود في ملف .env")

if not ALLOWED_USER_IDS:
    raise RuntimeError("ALLOWED_USER_IDS غير موجود في ملف .env")

if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY غير موجود في ملف .env")

HADAF_GUILD_ID = 1016740895544049724
AUTHORIZED_CHANNEL_IDS = {
    1136668686044909761,  # mars-team
    1179369466279235584,  # 8orders-issues
    1358833733699899704,  # 8orders-po
}

# عدد رسايل السياق اللي بتتقرا من القناة قبل الرد (تستبعد رسايل البوتات)
HISTORY_LIMIT = 30

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
claude_client = Anthropic(api_key=ANTHROPIC_API_KEY, timeout=CLAUDE_TIMEOUT_SECONDS)
claude_lock = asyncio.Lock()


def load_hadi_instructions() -> str:
    instructions_path = BASE_DIR / "CLAUDE.md"
    try:
        return instructions_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def ask_claude(user_message: str, author_name: str, history: str = "") -> str:
    history_block = (
        f"""
آخر رسايل القناة دي (الأقدم فالأحدث) — سياق فقط، دوّر فيها قبل ما تقول "مش لاقي معلومة":
{history}
"""
        if history
        else ""
    )

    system_prompt = f"""
أنت هادي أمين، مساعد فريق Hadaf داخل Discord.
رد بالعربية المصرية الواضحة إلا لو المستخدم طلب لغة أخرى.
لا تعرض أي tokens أو passwords أو بيانات من ملف .env.
لا تنفذ حذفًا أو تعديلات خطرة دون تأكيد واضح من المستخدم.

التزم بتعليمات هادي التالية:
{load_hadi_instructions()}
""".strip()

    user_prompt = f"""
اللي بعت الرسالة الحالية هو: {author_name}. رد عليه/عليها بالاسم ده تحديدًا،
ومتفترضش إنها من آسر إلا لو {author_name} هو آسر بالفعل.
{history_block}
رسالة {author_name}:
{user_message}
""".strip()

    response = claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
    )

    answer = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()
    if not answer:
        raise RuntimeError("Claude لم يُرجع نتيجة")

    return answer


async def build_channel_history(channel, before_message, limit: int = HISTORY_LIMIT) -> str:
    """يقرا آخر رسايل القناة (غير رسايل البوتات) قبل الرسالة الحالية، عشان
    هادي يقدر يرجع لمحتوى المحادثة نفسها لو اتسأل عن حاجة اتقالت قبل كده،
    بدل ما يقول إنه مش لاقي معلومة من غير ما يدور."""
    lines = []
    try:
        async for prev in channel.history(limit=limit, before=before_message):
            if prev.author.bot:
                continue
            text = prev.clean_content.strip()
            if not text:
                continue
            lines.append(f"[{prev.author.display_name}] {text}")
    except discord.HTTPException:
        return ""

    lines.reverse()
    return "\n".join(lines)


async def send_long_message(channel, text: str, reply_to: discord.Message = None) -> None:
    text = text.strip() or "لم يتم إرجاع رد."
    chunks = [text[start:start + 1900] for start in range(0, len(text), 1900)]

    for i, chunk in enumerate(chunks):
        if i == 0 and reply_to is not None:
            # رد مباشر (Discord reply) على رسالة الشخص اللي عمل المينشن تحديدًا
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
            or client.user not in message.mentions
        ):
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

    async with claude_lock:
        try:
            async with message.channel.typing():
                response = await asyncio.to_thread(
                    ask_claude,
                    content,
                    author_name,
                    history_text,
                )

            await send_long_message(
                message.channel,
                response,
                reply_to=message if message.guild is not None else None,
            )

        except APITimeoutError:
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
