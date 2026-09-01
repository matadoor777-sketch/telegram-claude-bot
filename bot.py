import os
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from telegram import Update
import anthropic

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def ask_claude(prompt):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

async def translate(update: Update, context):
    if not context.args:
        await update.message.reply_text("استخدم: /translate <اللغة> <النص>")
        return
    target_lang = context.args[0]
    text = " ".join(context.args[1:])
    prompt = f"Translate the following text to {target_lang}. Only return the translation, nothing else:\n\n{text}"
    reply = ask_claude(prompt)
    await update.message.reply_text(reply)

async def summarize(update: Update, context):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("استخدم: /summarize <النص>")
        return
    prompt = f"لخّص النص التالي في نقاط مختصرة وواضحة:\n\n{text}"
    reply = ask_claude(prompt)
    await update.message.reply_text(reply)

async def handle_message(update: Update, context):
    user_text = update.message.text
    reply = ask_claude(user_text)
    await update.message.reply_text(reply)

app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("translate", translate))
app.add_handler(CommandHandler("summarize", summarize))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
