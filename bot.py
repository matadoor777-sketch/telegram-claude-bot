import os
import re
import threading
import asyncio
import requests
from flask import Flask, request
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from telegram import Update
import anthropic

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CHAT_ID = os.environ.get("CHAT_ID")
CMC_API_KEY = os.environ.get("CMC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """
أنت مساعد ذكي متعدد التخصصات، مهمتك مساعدة المستخدمين في المجالات التالية بأسلوب واضح ومباشر:

1. التداول والعملات الرقمية:
- اشرح مفاهيم التحليل الفني والأساسي، إدارة رأس المال، إدارة المخاطر.
- لا تقدم توصيات استثمارية مباشرة، بل معلومات تعليمية.
- ذكّر أن الأسواق متقلبة وأنك لست مستشارًا ماليًا مرخصًا.

2. التغذية والعلاج بالأعشاب:
- معلومات عامة، ونبّه لاستشارة طبيب عند الحاجة.

3. التدريب الرياضي واللياقة البدنية:
- برامج عامة حسب مستوى المستخدم وأهدافه.

4. الترجمة:
- ترجم بدقة بين جميع اللغات.

5. طب الأسنان:
- معلومات عامة، وأحِل الحالات الجدية لطبيب مختص.

قواعد عامة:
- كن مباشرًا وواضحًا، وأضف تنويهًا عند المواضيع الحسّاسة.
"""

# ---------- CoinMarketCap ----------

COMMON_COINS = {
    "بيتكوين": "BTC", "بتكوين": "BTC", "btc": "BTC",
    "ايثيريوم": "ETH", "إيثريوم": "ETH", "eth": "ETH",
    "سولانا": "SOL", "sol": "SOL",
    "usdt": "USDT", "تيثر": "USDT",
    "بينانس": "BNB", "bnb": "BNB",
    "ريبل": "XRP", "xrp": "XRP",
    "دوجكوين": "DOGE", "doge": "DOGE",
}

def check_crypto_query(user_message):
    """يدور على اسم عملة في رسالة المستخدم"""
    text_lower = user_message.lower()
    for keyword, symbol in COMMON_COINS.items():
        if keyword in text_lower:
            return symbol
    return None

def get_crypto_data(symbol):
    """يجيب بيانات العملة من CoinMarketCap"""
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"symbol": symbol.upper(), "convert": "USD"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        if "data" not in data or symbol.upper() not in data["data"]:
            return None

        coin = data["data"][symbol.upper()]["quote"]["USD"]
        return {
            "price": coin["price"],
            "market_cap": coin["market_cap"],
            "change_24h": coin["percent_change_24h"]
        }
    except Exception as e:
        print(f"CMC API error: {e}")
        return None

# ---------- Claude ----------

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
    prompt = f"Translate the following text to {target_lang}. Only return the translation:\n\n{text}"
    reply = ask_claude(prompt)
    await update.message.reply_text(reply)

async def summarize(update: Update, context):
    if not context.args:
        await update.message.reply_text("استخدم: /summarize <النص>")
        return
    text = " ".join(context.args)
    prompt = f"لخّص النص التالي في نقاط مختصرة وواضحة:\n\n{text}"
    reply = ask_claude(prompt)
    await update.message.reply_text(reply)

async def handle_message(update: Update, context):
    user_text = update.message.text

    symbol = check_crypto_query(user_text)
    crypto_context = ""

    if symbol:
        data = get_crypto_data(symbol)
        if data:
            crypto_context = (
                f"\n\n[بيانات سعرية حالية لـ {symbol}]: "
                f"السعر: ${data['price']:.2f}, "
                f"القيمة السوقية: ${data['market_cap']:,.0f}, "
                f"التغير خلال 24 ساعة: {data['change_24h']:.2f}%"
            )

    final_message = user_text + crypto_context
    reply = ask_claude(final_message)
    await update.message.reply_text(reply)

telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
telegram_app.add_handler(CommandHandler("translate", translate))
telegram_app.add_handler(CommandHandler("summarize", summarize))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

flask_app = Flask(__name__)

@flask_app.route("/webhook", methods=["POST"])
def tradingview_webhook():
    data = request.get_data(as_text=True)
    asyncio.run(send_alert(data))
    return "OK", 200

async def send_alert(message):
    await telegram_app.bot.send_message(chat_id=CHAT_ID, text=f"📈 تنبيه من TradingView:\n{message}")

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    telegram_app.run_polling()