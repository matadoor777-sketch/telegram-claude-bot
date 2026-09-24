import asyncio
import json
import os
import re
from datetime import time as dtime
from zoneinfo import ZoneInfo

import feedparser
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TZ = ZoneInfo("Asia/Kuwait")
NOTES_FILE = "notes.json"
MORNING_HOUR = 8  # وقت التقرير الصباحي بتوقيت الكويت

# مصادر الأخبار. الروابط قابلة للتعديل، واستخدم /feeds لاختبارها
FEEDS = {
    "BBC عربي": "https://feeds.bbci.co.uk/arabic/rss.xml",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "العربية - أسواق": "https://www.alarabiya.net/feed/rss2/ar/aswaq.xml",
}

# ---------- الملاحظات ----------
def load_notes():
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_notes(data):
    try:
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


async def note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("اكتب هكذا: /note نص الملاحظة")
        return
    data = load_notes()
    key = str(update.effective_chat.id)
    data.setdefault(key, []).append(text)
    save_notes(data)
    await update.message.reply_text("تم حفظ الملاحظة رقم " + str(len(data[key])))


async def notes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_notes()
    items = data.get(str(update.effective_chat.id), [])
    if not items:
        await update.message.reply_text("لا توجد ملاحظات.")
        return
    lines = [str(i + 1) + ". " + t for i, t in enumerate(items)]
    await update.message.reply_text("\n".join(lines))


async def delnote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_notes()
    key = str(update.effective_chat.id)
    items = data.get(key, [])
    try:
        idx = int(context.args[0]) - 1
        removed = items.pop(idx)
    except Exception:
        await update.message.reply_text("اكتب هكذا: /delnote رقم")
        return
    data[key] = items
    save_notes(data)
    await update.message.reply_text("تم حذف: " + removed)


# ---------- التذكيرات ----------
async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=context.job.chat_id, text="تذكير: " + context.job.data
    )


async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usage = "اكتب هكذا: /remind 30m اشتري خبز\n(m دقائق، h ساعات، d أيام)"
    if len(context.args) < 2:
        await update.message.reply_text(usage)
        return
    m = re.fullmatch(r"(\d+)([mhd]?)", context.args[0].lower())
    if not m:
        await update.message.reply_text(usage)
        return
    n = int(m.group(1))
    unit = m.group(2) or "m"
    seconds = n * {"m": 60, "h": 3600, "d": 86400}[unit]
    text = " ".join(context.args[1:])
    context.job_queue.run_once(
        reminder_job, when=seconds, chat_id=update.effective_chat.id, data=text
    )
    await update.message.reply_text("تم ضبط التذكير بعد " + context.args[0])


# ---------- الأخبار ----------
def fetch_news(per_feed=3):
    parts = []
    for name, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            entries = feed.entries[:per_feed]
            if not entries:
                continue
            lines = ["- " + e.get("title", "").strip() for e in entries]
            parts.append(name + ":\n" + "\n".join(lines))
        except Exception:
            continue
    return "\n\n".join(parts) if parts else "تعذر جلب الأخبار الآن."


async def news_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("جاري جلب الأخبار...")
    text = await asyncio.to_thread(fetch_news)
    await update.message.reply_text(text[:4000])


def test_feeds():
    lines = []
    for name, url in FEEDS.items():
        try:
            n = len(feedparser.parse(url).entries)
            lines.append(("يعمل " if n else "لا يعمل ") + name + " (" + str(n) + ")")
        except Exception:
            lines.append("لا يعمل " + name)
    return "\n".join(lines)


async def feeds_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await asyncio.to_thread(test_feeds)
    await update.message.reply_text(text)


# ---------- التقرير الصباحي ----------
async def send_morning(bot, chat_id):
    news = await asyncio.to_thread(fetch_news)
    items = load_notes().get(str(chat_id), [])
    notes = "\n".join("- " + t for t in items) if items else "لا توجد ملاحظات."
    msg = "صباح الخير\n\nملاحظاتك:\n" + notes + "\n\nأخبار اليوم:\n" + news
    await bot.send_message(chat_id=chat_id, text=msg[:4000])


async def morning_job(context: ContextTypes.DEFAULT_TYPE):
    await send_morning(context.bot, context.job.chat_id)


async def morning_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_morning(context.bot, update.effective_chat.id)


# ---------- التسجيل ----------
def register(app: Application):
    app.add_handler(CommandHandler("note", note_cmd))
    app.add_handler(CommandHandler("notes", notes_cmd))
    app.add_handler(CommandHandler("delnote", delnote_cmd))
    app.add_handler(CommandHandler("remind", remind_cmd))
    app.add_handler(CommandHandler("news", news_cmd))
    app.add_handler(CommandHandler("feeds", feeds_cmd))
    app.add_handler(CommandHandler("morning", morning_cmd))

    chat_id = os.environ.get("CHAT_ID")
    if chat_id and app.job_queue:
        app.job_queue.run_daily(
            morning_job,
            time=dtime(MORNING_HOUR, 0, tzinfo=TZ),
            chat_id=int(chat_id),
        )