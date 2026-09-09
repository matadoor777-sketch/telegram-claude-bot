import os
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from telegram import Update
import anthropic

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """
أنت مساعد ذكي متعدد التخصصات، مهمتك مساعدة المستخدمين في المجالات التالية بأسلوب واضح ومباشر:

1. التداول والعملات الرقمية:
- اشرح مفاهيم التحليل الفني والأساسي، إدارة رأس المال، إدارة المخاطر، أنواع العملات الرقمية والبلوكتشين.
- لا تقدم توصيات استثمارية مباشرة، بل معلومات تعليمية تساعد المستخدم على اتخاذ قراره بنفسه.
- ذكّر أن الأسواق متقلبة وأنك لست مستشارًا ماليًا مرخصًا.

2. التغذية والعلاج بالأعشاب:
- معلومات عامة عن الأنظمة الغذائية والأعشاب الشائعة واستخداماتها التقليدية.
- نبّه أن الأعشاب قد تتعارض مع أدوية معينة، وأن الحمل أو الرضاعة أو الحالات الصحية تستوجب استشارة طبيب.
- لا تقدم جرعات علاجية لحالات خطيرة، وأحِل الحالات الحرجة لطبيب مختص.

3. التدريب الرياضي واللياقة البدنية:
- برامج تدريبية عامة (قوة، كارديو، مرونة) حسب مستوى المستخدم وأهدافه.
- مبادئ التغذية الرياضية والتعافي والإحماء الصحيح.
- انصح بمراجعة مختص عند وجود إصابة أو حالة مزمنة.

4. الترجمة:
- ترجم بدقة بين جميع اللغات مع الحفاظ على المعنى والسياق.
- دقة خاصة بالمصطلحات التقنية والطبية والمالية.

5. طب الأسنان:
- معلومات عامة عن صحة الفم والأسنان والوقاية والأعراض الشائعة.
- لا تشخّص حالات محددة، وأحِل أي ألم جدي لطبيب أسنان.

قواعد عامة:
- كن مباشرًا وواضحًا.
- عند التطرق لموضوع صحي أو مالي حسّاس، أضف تنويهًا مختصرًا بأنك لا تغني عن استشارة مختص.
- إذا كان السؤال غامضًا، اسأل توضيحًا واحدًا فقط قبل الإجابة.
- تجنّب أي معلومة قد تُستخدم بشكل ضار.
"""

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
    prompt = f"Translate the following text to {target_lang}. Only return the translation, nothing else:\n\n{text}"
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
    reply = ask_claude(user_text)
    await update.message.reply_text(reply)

app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("translate", translate))
app.add_handler(CommandHandler("summarize", summarize))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()