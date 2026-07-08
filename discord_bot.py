import asyncio
import os
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


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
claude_lock = asyncio.Lock()


def ask_claude(user_message: str) -> str:
    prompt = f"""
أنت هادي أمين، مساعد فريق Hadaf داخل Discord.

التزم بتعليمات ملف CLAUDE.md الموجود داخل المشروع.
رد بالعربية المصرية الواضحة إلا لو المستخدم طلب لغة أخرى.
لا تعرض أي tokens أو passwords أو بيانات من ملف .env.
لا تنفذ حذفًا أو تعديلات خطرة دون تأكيد واضح من المستخدم.

رسالة آسر:
{user_message}
""".strip()

    result = subprocess.run(
        [
            CLAUDE_BIN,
            "-p",
                      prompt,
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


async def send_long_message(channel, text: str) -> None:
    text = text.strip() or "لم يتم إرجاع رد."

    for start in range(0, len(text), 1900):
        await channel.send(text[start:start + 1900])


@client.event
async def on_ready():
    print(f"HADI ONLINE: {client.user} | ID: {client.user.id}")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # الرسائل الخاصة DM فقط حاليًا
    if message.guild is not None:
        return

    if message.author.id not in ALLOWED_USER_IDS:
        await message.channel.send("الحساب ده غير مصرح له باستخدام هادي.")
        return

    content = message.content.strip()

    if not content:
        await message.channel.send("ابعت رسالة نصية.")
        return

    if content.lower() == "!ping":
        await message.channel.send("HADI_OK")
        return

    async with claude_lock:
        try:
            async with message.channel.typing():
                response = await asyncio.to_thread(
                    ask_claude,
                    content,
                )

            await send_long_message(message.channel, response)

        except subprocess.TimeoutExpired:
            await message.channel.send(
                "الطلب استغرق وقتًا طويلًا. جرّب طلبًا أقصر."
            )

        except Exception as error:
            print(f"ERROR: {type(error).__name__}: {error}")
            await message.channel.send(
                f"حصل خطأ أثناء تشغيل هادي: {type(error).__name__}"
            )


client.run(TOKEN)
