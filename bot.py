import os
import asyncio
import logging
from datetime import datetime

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
CHANNEL_ID = os.getenv("CHANNEL_ID", "@Athar_Dz_Islamic").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
).strip()

# النشر كل ساعتين بالضبط
POST_INTERVAL_SECONDS = 2 * 60 * 60

# الذاكرة القصيرة للمحادثات
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "8"))

# رابط القناة
CHANNEL_LINK = "https://t.me/Athar_Dz_Islamic"

# التوقيع الذي سيظهر في نهاية كل منشور
CHANNEL_FOOTER = (
    "🔗 https://t.me/Athar_Dz_Islamic\n"
    "«صدقة جارية للأخت الأندلسية غ ـفر الله لها "
    "وجعلها صابرة ومحتسبة» ☝🏻⚔️🖤"
)


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("RihannaBot")


# ============================================================
# التحقق من المتغيرات
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في المتغيرات")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY غير موجود في المتغيرات")


# ============================================================
# Groq
# ============================================================

groq = AsyncGroq(api_key=GROQ_API_KEY)


# ============================================================
# الذاكرة المؤقتة
# ============================================================

conversation_history = {}


# ============================================================
# شخصية المساعد
# ============================================================

SYSTEM_PROMPT = """
أنت مساعد إسلامي تربوي لقناة تيليجرام موجهة خصوصًا إلى
شباب وفتيات الجزائر والمغرب العربي.

أسلوبك:
- عربي واضح مع لمسة جزائرية "دزيرية" خفيفة وطبيعية.
- لا تكثر من اللهجة حتى يبقى الكلام مفهومًا لجميع أهل المغرب العربي.
- أسلوب أخوي، رحيم، حكيم، جاد عند الحاجة.
- هدفك تقوية الإيمان والتوبة والصلاة والقرآن والذكر وحسن الخلق
  وبر الوالدين والعفة والصبر وطلب العلم وتزكية النفس.
- شجع الشباب والفتيات على الاستقامة والابتعاد عن الفتن والمعاصي
  والشهوات بأسلوب تربوي وإيماني وسلمي.
- لا تستخدم التكفير أو التحريض أو التهديد.
- لا تدعو إلى العنف أو العمليات المسلحة أو التجنيد أو الانضمام
  إلى جماعات مسلحة.

في المسائل الشرعية:
- لا تخترع آيات أو أحاديث.
- لا تنسب حديثًا للنبي ﷺ إلا إذا كنت واثقًا من صحته.
- إذا ذكرت حديثًا، اذكر مصدره قدر الإمكان.
- لا تغيّر نص القرآن.
- إذا لم تكن متأكدًا من معلومة شرعية، لا تخترع جوابًا.
- المسائل الفقهية الدقيقة أو النوازل تُحال إلى عالم موثوق ومتخصص.

عند الإجابة:
- افهم السؤال أولًا ثم أجب مباشرة.
- لا تجعل كل إجابة طويلة.
- إذا كان السائل حزينًا أو ضعيفًا، اجعل جوابك رحيمًا ومشجعًا.
- لا تحكم على نيات الناس.
- لا تدّعي أنك عالم أو مفتي حقيقي.

عند إنشاء منشور للقناة:
- أنشئ منشورًا إسلاميًا أصليًا ومفيدًا.
- نوّع المواضيع ولا تكرر نفس الفكرة باستمرار.
- اهتم بالإيمان والصلاة والقرآن والذكر والتوبة والأخلاق والعفة
  والأسرة والشباب والفتيات والصبر وطلب العلم.
- يمكن استخدام اللهجة الجزائرية الخفيفة عندما تكون مناسبة.
- لا تضع رابط القناة أو التوقيع في المنشور؛
  البرنامج سيضيفهما تلقائيًا.
- لا تقل "منشور اليوم".
- لا تخترع أحاديث أو أقوالًا وتنسبها لأصحابها.

أنت مساعد رقمي ولست عالمًا بشريًا، فلا تدّعي لنفسك منزلة العلماء.
"""


# ============================================================
# الاتصال بالذكاء الاصطناعي
# ============================================================

async def ask_ai(prompt: str, chat_key: str | None = None) -> str:
    try:
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

        if chat_key:
            history = conversation_history.get(chat_key, [])
            messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        response = await groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.65,
            max_tokens=1200,
        )

        answer = response.choices[0].message.content.strip()

        if chat_key:
            history = conversation_history.setdefault(
                chat_key,
                []
            )

            history.append(
                {
                    "role": "user",
                    "content": prompt,
                }
            )

            history.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )

            if len(history) > MAX_HISTORY * 2:
                del history[:-MAX_HISTORY * 2]

        return answer

    except Exception:
        logger.exception("حدث خطأ أثناء الاتصال بـ Groq")

        return (
            "عذرًا خويا، صراتلي مشكلة تقنية صغيرة 😅\n"
            "عاود سؤالك من بعد إن شاء الله."
        )


# ============================================================
# إنشاء منشور جديد
# ============================================================

async def generate_channel_post() -> str:
    prompt = """
اكتب الآن منشورًا إسلاميًا جديدًا وجاهزًا للنشر.

اختَر موضوعًا مناسبًا من:
- تقوية الإيمان
- الصلاة
- القرآن
- الذكر
- التوبة
- الصبر
- حسن الخلق
- بر الوالدين
- العفة
- غض البصر
- الأسرة
- تربية الشباب
- تربية الفتيات
- طلب العلم
- مجاهدة النفس
- الثبات أمام الفتن والشهوات
- الأمل وحسن الظن بالله

اجعل المنشور مؤثرًا وواقعيًا ومناسبًا لشباب وفتيات الجزائر
والمغرب العربي.

استخدم العربية الفصحى مع لمسة دزيرية خفيفة إذا كانت مناسبة.

لا تخترع حديثًا أو آية.

إذا استشهدت بحديث، فاذكر مصدره.
إذا لم تكن بحاجة إلى حديث أو آية فلا تستخدم واحدًا.

اجعل المنشور متوسط الطول، مرتبًا، ومناسبًا للنشر مباشرة.

لا تضف رابط القناة.
لا تضف التوقيع.
لا تضف هاشتاغات كثيرة.
"""

    return await ask_ai(prompt)


# ============================================================
# نشر المنشور
# ============================================================

async def publish_to_channel(application: Application):
    try:
        logger.info("جاري إنشاء منشور جديد...")

        post = await generate_channel_post()

        final_post = (
            f"{post}\n\n"
            f"{CHANNEL_FOOTER}"
        )

        await application.bot.send_message(
            chat_id=CHANNEL_ID,
            text=final_post,
            disable_web_page_preview=True,
        )

        logger.info("تم نشر منشور جديد في القناة.")

    except Exception:
        logger.exception("فشل نشر المنشور.")


# ============================================================
# جدولة النشر
# ============================================================

async def scheduled_publisher(application: Application):
    """
    نشر تلقائي كل ساعتين بالضبط.
    """

    while True:
        logger.info(
            "⏳ المنشور القادم بعد ساعتين بالضبط."
        )

        await asyncio.sleep(POST_INTERVAL_SECONDS)

        await publish_to_channel(application)


# ============================================================
# التحقق من كون الرسالة سؤالًا
# ============================================================

def looks_like_question(text: str) -> bool:
    if not text:
        return False

    text = text.strip().lower()

    if "?" in text or "؟" in text:
        return True

    question_words = [
        "هل ",
        "كيف ",
        "ما حكم",
        "ماهو",
        "ما هو",
        "ماذا ",
        "لماذا ",
        "حكم ",
        "يجوز",
        "حرام",
        "حلال",
        "أريد أن أعرف",
        "واش ",
        "علاش ",
        "كيفاش ",
        "وش ",
        "نقدر ",
    ]

    return any(
        text.startswith(word)
        for word in question_words
    )


# ============================================================
# التعامل مع أسئلة المجموعة
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

    text = message.text or message.caption or ""

    if not text.strip():
        return

    bot = await context.bot.get_me()

    mentioned = (
        bot.username
        and f"@{bot.username.lower()}" in text.lower()
    )

    replied_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot.id
    )

    question = looks_like_question(text)

    # لا يتدخل في كل محادثات المجموعة
    if not (question or mentioned or replied_to_bot):
        return

    if bot.username:
        text = text.replace(
            f"@{bot.username}",
            ""
        ).strip()

    user = message.from_user

    if user:
        chat_key = f"{message.chat.id}:{user.id}"
    else:
        chat_key = str(message.chat.id)

    logger.info(
        "سؤال جديد من المجموعة: %s",
        text[:200],
    )

    answer = await ask_ai(
        text,
        chat_key=chat_key,
    )

    try:
        await message.reply_text(
            answer,
            disable_web_page_preview=True,
        )

    except Exception:
        logger.exception(
            "فشل إرسال الرد إلى المجموعة."
        )


# ============================================================
# /start
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        "مرحبا بيك خويا/أختي.\n"
        "تقدر تطرح سؤالك في أمور الدين والتربية والإيمان، "
        "ونحاول نعاونك بما نعرف، وإذا كانت المسألة تحتاج "
        "لعالم مختص نوجّهك لذلك إن شاء الله."
    )


# ============================================================
# /status
# ============================================================

async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "🟢 البوت يعمل بشكل طبيعي.\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


# ============================================================
# تشغيل جدولة النشر
# ============================================================

async def post_scheduler(
    application: Application
):
    await asyncio.sleep(30)

    await scheduled_publisher(
        application
    )


async def post_init(
    application: Application
):
    asyncio.create_task(
        post_scheduler(application)
    )


# ============================================================
# Main
# ============================================================

def main():
    logger.info(
        "Starting Rihanna Islamic Bot..."
    )

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
        CommandHandler(
            "status",
            status_command
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_group_message,
        )
    )

    logger.info(
        "Bot is running..."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
