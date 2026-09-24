import os
import requests
import base64
import threading
import asyncio
from flask import Flask, request
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from telegram import Update
import anthropic
import secretary

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CHAT_ID = os.environ.get("CHAT_ID")
CHART_IMG_API_KEY = os.environ.get("CHART_IMG_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = "أنت مساعد ذكي متعدد التخصصات، مهمتك مساعدة المستخدمين في المجالات التالية بأسلوب واضح ومباشر: 1) التداول والعملات الرقمية: اشرح مفاهيم التحليل الفني والأساسي وإدارة رأس المال وإدارة المخاطر، ولا تقدم توصيات استثمارية مباشرة بل معلومات تعليمية، وذكّر أن الأسواق متقلبة وأنك لست مستشارًا ماليًا مرخصًا. 2) التغذية والعلاج بالأعشاب: معلومات عامة، ونبّه لاستشارة طبيب عند الحاجة. 3) التدريب الرياضي واللياقة البدنية: برامج عامة حسب مستوى المستخدم وأهدافه. 4) الترجمة: ترجم بدقة بين جميع اللغات. 5) طب الأسنان: معلومات عامة، وأحِل الحالات الجدية لطبيب مختص. كن مباشرًا وواضحًا، وأضف تنويهًا عند المواضيع الحسّاسة."

def ask_claude(prompt):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

async def translate(update: Update, context):
    if not context.args:
        await update.message.reply_text("استخدم: /translate <اللغة> <النص>")
        return
    target_lang = context.args[0]
    text = " ".join(context.args[1:])
    prompt = "Translate the following text to " + target_lang + ". Only return the translation:\n\n" + text
    reply = ask_claude(prompt)
    await update.message.reply_text(reply)

async def summarize(update: Update, context):
    if not context.args:
        await update.message.reply_text("استخدم: /summarize <النص>")
        return
    text = " ".join(context.args)
    prompt = "لخّص النص التالي في نقاط مختصرة وواضحة:\n\n" + text
    reply = ask_claude(prompt)
    await update.message.reply_text(reply)

async def handle_message(update: Update, context):
    user_text = update.message.text
    reply = ask_claude(user_text)
    await update.message.reply_text(reply)

async def handle_photo(update: Update, context):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    image_b64 = base64.b64encode(photo_bytes).decode("utf-8")

    caption = update.message.caption or "صف لي هذه الصورة بالتفصيل"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                {"type": "text", "text": caption}
            ]
        }]
    )
    reply = response.content[0].text
    await update.message.reply_text(reply)

async def chart_command(update: Update, context):
    if not context.args:
        await update.message.reply_text("اكتب الرمز، مثال:\n/chart BTCUSDT")
        return

    symbol = context.args[0].upper()
    interval = context.args[1] if len(context.args) > 1 else "1D"

    url = "https://api.chart-img.com/v2/tradingview/advanced-chart"
    headers = {"x-api-key": CHART_IMG_API_KEY}
    payload = {
        "symbol": "BINANCE:" + symbol,
        "interval": interval,
        "theme": "dark"
    }

    try:
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=resp.content,
            caption="📊 " + symbol + " - " + interval
        )
    except Exception as e:
        await update.message.reply_text("صار خطأ بجلب الشارت: " + str(e))

telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
secretary.register(telegram_app)
telegram_app.add_handler(CommandHandler("translate", translate))
telegram_app.add_handler(CommandHandler("summarize", summarize))
telegram_app.add_handler(CommandHandler("chart", chart_command))
telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

flask_app = Flask(__name__)

@flask_app.route("/webhook", methods=["POST"])
def tradingview_webhook():
    data = request.get_data(as_text=True)
    asyncio.run(send_alert(data))
    return "OK", 200

async def send_alert(message):
    await telegram_app.bot.send_message(chat_id=CHAT_ID, text="📈 تنبيه من TradingView:\n" + message)

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    telegram_app.run_polling()
import feedparser

def get_crypto_news():
    feed = feedparser.parse("https://www.coindesk.com/arc/outboundfeeds/rss/")
    items = feed.entries[:5]
    news_text = "📰 آخر أخبار السوق:\n\n"
    for item in items:
        news_text += f"• {item.title}\n{item.link}\n\n"
    return news_text
async def news_command(update, context):
    news = get_crypto_news()
    await update.message.reply_text(news)

app.add_handler(CommandHandler("news", news_command))