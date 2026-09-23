import os
import requests
import base64
import threading
import asyncio
from flask import Flask, request
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from telegram import Update
import anthropic

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CHAT_ID = os.environ.get("CHAT_ID")
CHART_IMG_API_KEY = os.environ.get("CHART_IMG_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """
أنت مساعد ذكي متعدد التخصصات، مهمتك مساعدة المستخدمين في المجالات التالية بأسلوب واضح ومباشر:

1. التداول والعملات الرقمية:
- اشرح مفاهيم التحليل الفني والأساسي، إدارة رأس المال، إدارة المخاطر.
- لا تقدم توصيات استثمارية مباشرة، بل معلومات تعليمية.
- ذكّر أن الأسواق متقلبة وأنك لست مستشارًا ماليًا مرخصًا.

2. التغذية والعلاج بالأعشاب:
- معلومات