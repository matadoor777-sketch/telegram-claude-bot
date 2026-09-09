import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# =========================================================
# الإعدادات والمفاتيح
# =========================================================
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
CMC_API_KEY = "YOUR_CMC_API_KEY_HERE"

# قاموس الربط بين الكلمات المفتاحية ورموز العملات
COMMON_COINS = {
    "bitcoin": "BTC", "btc": "BTC", "بيتكوين": "BTC", "البيتكوين": "BTC",
    "ethereum": "ETH", "eth": "ETH", "ايثريوم": "ETH", "الأيثريوم": "ETH",
    "solana": "SOL", "sol": "SOL", "سولانا": "SOL",
    "sui": "SUI",
    "fet": "FET", "fetch": "FET",
    "rndr": "RNDR", "render": "RNDR",
    "hype": "HYPE",
    "hyve": "HYVE",
    "somnia": "SOMI", "somi": "SOMI"
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# =========================================================
# الدوال البرمجية
# =========================================================
def extract_symbol_from_text(user_message: str):
    """استخراج رمز العملة من نص المستخدم"""
    text_lower = user_message.lower()
    for keyword, symbol in COMMON_COINS.items():
        if keyword in text_lower:
            return symbol
    return None

def get_crypto_data(symbol: str):
    """جلب بيانات العملة من CoinMarketCap"""
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"symbol": symbol.upper(), "convert": "USD"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        if "data" not in data or symbol.upper() not in data["data"]:
            return None

        coin_info = data["data"][symbol.upper()]
        quote = coin_info["quote"]["USD"]

        return {
            "name": coin_info["name"],
            "symbol": coin_info["symbol"],
            "price": quote["price"],
            "percent_change_24h": quote["percent_change_24h"],
            "market_cap": quote["market_cap"]
        }
    except Exception as e:
        logging.error(f"خطأ أثناء جلب البيانات للرمز {symbol}: {e}")
        return None

# =========================================================
# أوامر ومعالجة رسائل البوت
# =========================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك! 🤖\nأرسل اسم أو رمز أي عملة رقمية (مثل: BTC أو سولانا) للحصول على السعر الحالي والتفاصيل."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    symbol = extract_symbol_from_text(user_text)

    if not symbol:
        symbol = user_text.strip().upper()

    crypto_data = get_crypto_data(symbol)

    if not crypto_data:
        await update.message.reply_text("❌ لم يتم العثور على بيانات لهذه العملة. تأكد من الرمز وحاول مجدداً.")
        return

    change_emoji = "📈" if crypto_data["percent_change_24h"] >= 0 else "📉"
    
    response_msg = (
        f"🪙 **{crypto_data['name']} ({crypto_data['symbol']})**\n\n"
        f"💵 السعر: **${crypto_data['price']:,.4f}**\n"
        f"{change_emoji} التغير (24h): **{crypto_data['percent_change_24h']:.2f}%**\n"
        f"📊 القيمة السوقية: **${crypto_data['market_cap']:,.0f}**"
    )

    await update.message.reply_text(response_msg, parse_mode="Markdown")

# =========================================================
# تشغيل التطبيق
# =========================================================
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("البوت يعمل الآن...")
    app.run_polling()
