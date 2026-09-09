import os
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

        if "data" not in data or symbol.upper() no