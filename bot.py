import os
import asyncio
import logging

from groq import AsyncGroq

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# ============================================================
# الإعدادات
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

CHANNEL_ID = os.getenv(
    "CHANNEL_ID",
    "@Athar_Dz_Islamic"
).strip()

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    ""
).strip()

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
).strip()

POST_INTERVAL_SECONDS = 2 * 60 * 60


# ============================================================
# رابط القناة والتوقيع
# ============================================================

CHANNEL_LINK = "https://t.me/Athar_Dz_Islamic"

CHANNEL_FOOTER = (
    f"{CHANNEL_LINK}\n"
    "«هذي القناة صدقة جارية لأم عقيدة وحمزة "
    "غ ـفر الله لها وجعلها صابرة ومحتسبة»☝🏻⚔️🖤"
)


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("RihannaBot")


# ============================================================
# التحقق
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY غير موجود")


# ============================================================
# Groq
# ============================================================

groq = AsyncGroq(
    api_key=GROQ_API_KEY
)


# ============================================================
# البرومبت
# ============================================================

SYSTEM_PROMPT = """
أنت مسلم موحد من بلاد المغرب الإسلامي.

مهمتك نشر المنشورات في القناة والرد والتعليق على
منشورات القناة داخل المجموعة التابعة لها.

عند النشر في القناة:

اكتب منشورًا موجهًا للفتيات والشباب في المغرب الإسلامي.

كن ناصحًا ومحبًا ورحيمًا.

تحدث عن غض البصر والعفة لدى النساء،
وتحدث خصوصًا عن مخاطر المخدرات على الشباب.

اجعل الكلام واضحًا ومباشرًا ومؤثرًا.

لا يزيد المنشور عن 1500 حرف.

لا تضف رابط القناة.

لا تضف التوقيع.

اكتب المنشور مباشرة دون مقدمة أو شرح إضافي.

عند الرد في المجموعة:

أجب على كلام العضو مباشرة وبأسلوب ناصح ومحب ورحيم.

لا تضف رابط القناة ولا التوقيع.
"""


# ============================================================
# طلب Groq
# ============================================================

async def ask_ai(prompt: str) -> str:

    try:

        response = await groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.6,
            max_tokens=1200,
        )

        answer = (
            response.choices[0]
            .message
            .content
            .strip()
        )

        return answer

    except Exception:

        logger.exception(
            "❌ خطأ أثناء الاتصال بـ Groq"
        )

        return ""


# ============================================================
# إنشاء منشور القناة
# ============================================================

async def generate_channel_post() -> str:

    return await ask_ai(
        "اكتب الآن المنشور المطلوب للنشر في القناة."
    )


# ============================================================
# نشر القناة
# ============================================================

async def publish_to_channel(
    application: Application,
):

    try:

        post = await generate_channel_post()

        if not post:
            logger.warning(
                "⚠️ لم يتم إنشاء منشور."
            )
            return

        # الرابط أولاً ثم التوقيع
        final_post = (
            f"{post}\n\n"
            f"{CHANNEL_FOOTER}"
        )

        await application.bot.send_message(
            chat_id=CHANNEL_ID,
            text=final_post,
            disable_web_page_preview=True,
        )

        logger.info(
            "✅ تم نشر المنشور في القناة."
        )

    except Exception:

        logger.exception(
            "❌ فشل نشر المنشور."
        )


# ============================================================
# النشر كل ساعتين
# ============================================================

async def scheduled_publisher(
    application: Application,
):

    while True:

        await asyncio.sleep(
            POST_INTERVAL_SECONDS
        )

        await publish_to_channel(
            application
        )


# ============================================================
# الرد على المجموعة
# ============================================================

async def handle_group_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    message = update.message

    if message.chat.type not in (
        ChatType.GROUP,
        ChatType.SUPERGROUP,
    ):
        return

    text = (
        message.text
        or message.caption
        or ""
    ).strip()

    if not text:
        return

    bot = await context.bot.get_me()

    mentioned = False

    if bot.username:

        mentioned = (
            f"@{bot.username.lower()}"
            in text.lower()
        )

    replied_to_bot = False

    if message.reply_to_message:

        if message.reply_to_message.from_user:

            replied_to_bot = (
                message.reply_to_message
                .from_user
                .id
                == bot.id
            )

    if not (
        mentioned
        or replied_to_bot
        or "؟" in text
        or "?" in text
    ):
        return

    if bot.username:

        text = text.replace(
            f"@{bot.username}",
            ""
        ).strip()

    if not text:
        return

    answer = await ask_ai(text)

    if not answer:
        return

    try:

        await message.reply_text(
            answer,
            disable_web_page_preview=True,
        )

    except Exception:

        logger.exception(
            "❌ فشل إرسال الرد."
        )


# ============================================================
# /start
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.message:

        await update.message.reply_text(
            "السلام عليكم ورحمة الله وبركاته."
        )


# ============================================================
# تشغيل جدولة النشر
# ============================================================

async def post_init(
    application: Application,
):

    asyncio.create_task(
        scheduled_publisher(
            application
        )
    )


# ============================================================
# Main
# ============================================================

def main():

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )

    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.TEXT
            & ~filters.COMMAND,
            handle_group_message,
        )
    )

    logger.info(
        "🟢 البوت يعمل..."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
