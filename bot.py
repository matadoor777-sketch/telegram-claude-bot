import os
import json
import logging
import asyncio
import threading

from flask import Flask, request
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from telegram import Update
import anthropic
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CMC_API_KEY = os.environ.get("CMC_API_KEY")
CHAT_ID = os.environ.get("CHAT_ID")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

MAX_HISTORY = 20
conversation_history = {}

SYSTEM_PROMPT = """
أنت مساعد ذكي متعدد التخصصات، مهمتك مساعدة المستخدمين في المجالات التالية بأسلوب واضح ومباشر:

1. التداول والعملات الرقمية:
- اشرح مفاهيم التحليل الفني والأساسي، إدارة رأس المال، إدارة المخاطر.
- لا تقدم توصيات استثمارية مباشرة، بل معلومات تعليمية.
- ذكر أن الأسواق متقلبة وأنك لست مستشارا ماليا مرخصا.

2. التغذية والعلاج بالأعشاب:
- معلومات عامة، ونبه لاستشارة طبيب عند الحاجة.

3. التدريب الرياضي واللياقة البدنية:
- برامج عامة حسب مستوى المستخدم وأهدافه.

4. الترجمة:
- ترجم بدقة بين جميع اللغات.

5. طب الأسنان:
- معلومات عامة، وأحل الحالات الجدية لطبيب مختص.

قواعد عامة:
- كن مباشرا وواضحا، وأضف تنويها عند المواضيع الحساسة.
"""


def get_history(chat_id):
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    return conversation_history[chat_id]


def add_to_history(chat_id, role, content):
    history = get_history(chat_id)
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY:
        conversation_history[chat_id] = history[-MAX_HISTORY:]


def ask_claude(chat_id, prompt):
    add_to_history(chat_id, "user", prompt)
    messages = get_history(chat_id)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=messages
    )
    reply = response.content[0].text
    add_to_history(chat_id, "assistant", reply)
    return reply


def check_crypto_query(text):
    keywords = ["سعر", "price", "بيتكوين", "بتكوين", "btc", "eth", "ايثيريوم"]
    text_lower = text.lower()
    return any(k in text_lower for k in keywords)


def get_crypto_data(symbol):
    if not CMC_API_KEY:
        return "لم يتم إعداد مفتاح CoinMarketCap (CMC_API_KEY) بعد."

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"symbol": symbol.upper()}

    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()

        if "data" not in data or symbol.upper() not in data["data"]:
            return f"لم أجد بيانات للعملة {symbol}. تأكد من الرمز (مثل BTC أو ETH)."

        quote = data["data"][symbol.upper()]["quote"]["USD"]
        price = quote["price"]
        change_24h = quote["percent_change_24h"]

        return (
            f"💰 سعر {symbol.upper()}: ${price:,.2f}\n"
            f"📊 التغير خلال 24 ساعة: {change_24h:.2f}%"
        )
    except Exception as e:
        logger.error(f"CoinMarketCap error: {e}")
        return "حدث خطأ أثناء جلب سعر العملة. حاول مرة أخرى بعد قليل."


async def price_command(update: Update, context):
    if not context.args:
        await update.message.reply_text("استخدم: /price BTC")
        return
    symbol = context.args[0]
    reply = get_crypto_data(symbol)
    await update.message.reply_text(reply)


async def reset_command(update: Update, context):
    chat_id = update.message.chat_id
    conversation_history[chat_id] = []
    await update.message.reply_text("تم مسح الذاكرة، نبدأ محادثة جديدة.")


async def myid_command(update: Update, context):
    await update.message.reply_text(f"Chat ID: {update.message.chat_id}")


async def translate(update: Update, context):
    if not context.args:
        await update.message.reply_text("استخدم: /translate <اللغة> <النص>")
        return
    target_lang = context.args[0]
    text = " ".join(context.args[1:])
    prompt = f"Translate the following text to {target_lang}. Only return the translation:\n\n{text}"
    reply = ask_claude(update.message.chat_id, prompt)
    await update.message.reply_text(reply)


async def summarize(update: Update, context):
    if not context.args:
        await update.message.reply_text("استخدم: /summarize <النص>")
        return
    text = " ".join(context.args)
    prompt = f"لخص النص التالي في نقاط مختصرة وواضحة:\n\n{text}"
    reply = ask_claude(update.message.chat_id, prompt)
    await update.message.reply_text(reply)


async def handle_message(update: Update, context):
    chat_id = update.message.chat_id
    user_text = update.message.text

    if check_crypto_query(user_text):
        reply = "لتفاصيل سعر عملة معينة استخدم: /price BTC (أو أي رمز عملة آخر)"
    else:
        reply = ask_claude(chat_id, user_text)

    await update.message.reply_text(reply)


def build_telegram_app():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("translate", translate))
    app.add_handler(CommandHandler("summarize", summarize))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app


telegram_app = build_telegram_app()

flask_app = Flask(__name__)


@flask_app.route("/webhook", methods=["POST"])
def tradingview_webhook():
    data = request.get_data(as_text=True)
    asyncio.run(send_alert(data))
    return "OK", 200


async def send_alert(message):
    if CHAT_ID:
        await telegram_app.bot.send_message(chat_id=CHAT_ID, text=f"📈 تنبيه من TradingView:\n{message}")


def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is missing!")
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY is missing!")

    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("Bot is starting...")
    telegram_app.run_polling(drop_pending_updates=True)