import os
import logging
import threading
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from groq import AsyncGroq

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============================================================
# الإعدادات وقراءة المتغيرات
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "@Athar_Dz_Islamic").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

try:
    MAX_HISTORY = int(os.getenv("MAX_HISTORY", "8").strip())
except ValueError:
    MAX_HISTORY = 8

POST_INTERVAL_SECONDS = 2 * 60 * 60  # كل ساعتين
FIRST_POST_DELAY = 5  # ثواني الانتظار قبل أول منشور بعد الإقلاع

# ============================================================
# رابط القناة والتوقيع
# ============================================================
CHANNEL_LINK = "https://t.me/Athar_Dz_Islamic"
CHANNEL_FOOTER = (
    f"\n\n🔗 {CHANNEL_LINK}\n"
    "«هذي القناة صدقة جارية لأم عقيدة وحمزة "
    "غ ـفر الله لها وجعلها صابرة ومحتسبة»☝🏻⚔️🖤"
)

# ============================================================
# الذاكرة المؤقتة للدردشة (Chat History)
# ============================================================
chat_histories = defaultdict(list)

# ============================================================
# الـ Logging
# ============================================================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("RihannaBot")

# ============================================================
# التحقق من المتغيرات الأساسية
# ============================================================
if not BOT_TOKEN:
    raise RuntimeError("خطأ: BOT_TOKEN غير موجود في المتغيرات البيئية!")

if not GROQ_API_KEY:
    raise RuntimeError("خطأ: GROQ_API_KEY غير موجود في المتغيرات البيئية!")

groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# ============================================================
# التعليمات البرمجية للذكاء الاصطناعي (System Prompts)
# ============================================================
SYSTEM_PROMPT = """
أنت مسلم موحد من بلاد المغرب الإسلامي.
مهمتك نشر المنشورات في القناة والرد والتعليق على منشورات القناة داخل المجموعة التابعة لها.

عند النشر في القناة:
اكتب منشورًا موجهًا للفتيات والشباب في المغرب الإسلامي.
كن ناصحًا ومحبًا ورحيمًا.
تحدث عن غض البصر والعفة لدى النساء، وتحدث خصوصًا عن مخاطر المخدرات على الشباب وتحذيرهم بأن الغرب الصليبي هم من أرادوا لشباب الإسلام بأن يتاعطون المخدرات لكي لا ينشئ جيل ينصرون الإسلام.
اجعل الكلام واضحًا ومباشرًا ومؤثرًا.
اكتب منشوراً مفصلاً ومطولاً وشاملاً، على أن يتراوح طوله بين 1024 إلى 1100 حرف ولا يقل عن ذلك.
لا تضف رابط القناة.
لا تضف التوقيع.
اكتب المنشور مباشرة دون مقدمة أو شرح إضافي.

عند الرد في المجموعة:
أجب على كلام العضو مباشرة وبأسلوب ناصح ومحب ورحيم وتكلم باللهجة الجزائرية أو المغاربية الخفيفة والمفهومة للجميع لتقريب النصح لقلوبهم.
لا تضف رابط القناة ولا التوقيع.
"""

# ============================================================
# خادم فحص الصحة (Health Check) لمنع Railway من إيقاف الحاوية
# ============================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, fmt, *args):
        pass


def start_health_server():
    port = int(os.getenv("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.info(f"خادم فحص الصحة يعمل على المنفذ {port}")


# ============================================================
# الوظائف التلقائية (Tasks)
# ============================================================

async def auto_post_job(context: ContextTypes.DEFAULT_TYPE):
    """وظيفة النشر التلقائي في القناة التي يتم استدعاؤها عبر الـ JobQueue"""
    logger.info("جاري إعداد وإنشاء منشور تلقائي للقناة عبر Groq...")
    try:
        response = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "أنشئ منشورًا دعويًا جديدًا ومؤثرًا الآن للشباب والفتيات."},
            ],
            model=GROQ_MODEL,
            timeout=60,
        )
        post_content = response.choices[0].message.content.strip()

        final_post = f"{post_content}{CHANNEL_FOOTER}"

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=final_post,
            disable_web_page_preview=True,
        )
        logger.info("تم نشر المنشور بنجاح في القناة.")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء النشر التلقائي: {e}")


# ============================================================
# معالجة الأوامر والرسائل (Handlers)
# ============================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد على أمر /start"""
    await update.message.reply_text(
        "مرحباً بك، أنا بوت رَيْحَانَةُ المَغْرِبِ الأَوْسَطِ المساعد الرقمي الإسلامي."
    )


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رسائل المجموعة والتفاعل مع الأعضاء بالاعتماد على الذاكرة"""
    if not update.message or not update.message.text:
        return

    message_text = update.message.text.strip()
    bot_username = context.bot.username
    user_id = update.message.from_user.id

    is_mentioned = f"@{bot_username}" in message_text
    is_reply_to_bot = (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user
        and update.message.reply_to_message.from_user.id == context.bot.id
    )

    if is_mentioned or is_reply_to_bot:
        clean_text = message_text.replace(f"@{bot_username}", "").strip()

        if not clean_text:
            return

        logger.info(f"سؤال جديد من المستخدم {user_id} في المجموعة: {clean_text}")

        user_history = chat_histories[user_id]
        user_history.append({"role": "user", "content": clean_text})

        if len(user_history) > MAX_HISTORY:
            user_history = user_history[-MAX_HISTORY:]
            chat_histories[user_id] = user_history

        messages_to_send = [{"role": "system", "content": SYSTEM_PROMPT}] + user_history

        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )

            response = await groq_client.chat.completions.create(
                messages=messages_to_send,
                model=GROQ_MODEL,
                timeout=60,
            )
            bot_reply = response.choices[0].message.content.strip()

            user_history.append({"role": "assistant", "content": bot_reply})
            chat_histories[user_id] = user_history

            await update.message.reply_text(text=bot_reply)
        except Exception as e:
            logger.error(f"حدث خطأ أثناء معالجة رد الذكاء الاصطناعي في المجموعة: {e}")
            await update.message.reply_text(
                "عذراً، حدث خطأ مؤقت في معالجة طلبك، أعد المحاولة لاحقاً."
            )


# ============================================================
# تشغيل التطبيق الرئيسي
# ============================================================
def main():
    logger.info("جاري بدء تشغيل بوت رَيْحَانَةُ المَغْرِبِ الأَوْسَطِ...")

    # تشغيل خادم فحص الصحة لمنع Railway من إيقاف الحاوية
    start_health_server()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(
        MessageHandler(filters.ChatType.GROUPS & filters.TEXT, handle_group_message)
    )

    # جدولة النشر التلقائي: أول منشور بعد 5 ثواني، ثم كل ساعتين
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(
            auto_post_job,
            interval=POST_INTERVAL_SECONDS,
            first=FIRST_POST_DELAY,
        )
        logger.info(
            f"تم ضبط جدولة النشر التلقائي: أول منشور بعد {FIRST_POST_DELAY} ثوانٍ، ثم كل {POST_INTERVAL_SECONDS // 3600} ساعات."
        )
    else:
        logger.warning("تحذير: الـ JobQueue غير مفعلة، تأكد من تثبيت python-telegram-bot[ext]")

    logger.info("البوت يعمل ومستقر الآن ومستعد لاستقبال التحديثات...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
        
