from questions import PROGRAMMING_QUESTIONS
from news import fetch_random_article, format_article

from dotenv import load_dotenv
import logging
import random
import json
import os
from datetime import datetime, time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# ─────────────────────────────────────────────
# НАСТРОЙКИ
# ─────────────────────────────────────────────
load_dotenv()
os.getenv('BOT_TOKEN')

# Расписание напоминаний (часы UTC, поправь под свой часовой пояс)
SCHEDULED_HOURS = [15, 19]  # 09:00, 13:00, 18:00, 21:00

# Случайные напоминания: каждые N минут (случайно в диапазоне)
RANDOM_REMINDER_MIN = 180  # минимум минут
RANDOM_REMINDER_MAX = 300  # максимум минут

DATA_FILE = "bot_data.json"

# ─────────────────────────────────────────────
# ВОПРОСЫ ДЛЯ КОНТРОЛЯ ДОМИНАНТЫ
# ─────────────────────────────────────────────
DAILY_QUESTIONS = [
    "💻 Что пишешь сегодня?",
    "🎯 Какая задача открыта прямо сейчас?",
    "⚡ Над чем работаешь в данный момент?",
    "🔥 Какую проблему решаешь сегодня?",
    "📌 Что запланировал сделать сегодня по коду?",
]
 
CHECKIN_QUESTIONS = [
    "✅ Сделал то, что планировал? Что удалось?",
    "📊 Как прошёл день по программированию?",
    "🏁 Закрыл задачу или ещё в процессе?",
    "💬 Что застряло или мешает?",
]
 
RANDOM_NUDGES = [
    "👀 Эй, ты сейчас кодишь или залип в YouTube?",
    "🚀 Напоминаю: есть открытая задача. Как прогресс?",
    "⏰ Прошло время — что успел сделать?",
    "💡 Маленький вопрос: ты сейчас в потоке или отвлёкся?",
    "🎯 Фокус! Что сейчас на экране?",
    "🔁 Пора чекнуться — пишешь что-то полезное?",
    "Эй, а сколько можно ебланить — иди делом займись!",
    "Я надеюсь ты не читаешь это в уведомлении?",
    "РАБОТАЙ БЛЯТЬ",
]
 
# ─────────────────────────────────────────────
# ХРАНЕНИЕ ДАННЫХ
# ─────────────────────────────────────────────
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}}
 
def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
 
def get_user(data: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "active": True,
            "current_task": None,
            "log": [],
            "streak": 0,
            "last_checkin": None,
        }
    return data["users"][uid]
 
# ─────────────────────────────────────────────
# НАПОМИНАНИЯ
# ─────────────────────────────────────────────
def schedule_random_reminder(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    # удаляем старую job чтобы не дублировались
    for job in context.job_queue.get_jobs_by_name(f"random_{chat_id}"):
        job.schedule_removal()
 
    delay = random.randint(RANDOM_REMINDER_MIN, RANDOM_REMINDER_MAX) * 60
    context.job_queue.run_once(
        random_reminder,
        when=delay,
        chat_id=chat_id,
        name=f"random_{chat_id}",
    )
 
async def random_reminder(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    data = load_data()
 
    user = data["users"].get(str(chat_id))
    if not user or not user.get("active", True):
        return
 
    nudge = random.choice(RANDOM_NUDGES)
    try:
        await context.bot.send_message(chat_id=chat_id, text=nudge)
    except Exception as e:
        logging.warning(f"Ошибка случайного напоминания: {e}")
 
    schedule_random_reminder(context, chat_id)
 
async def quiz_reminder(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    data = load_data()
 
    user = data["users"].get(str(chat_id))
    if not user or not user.get("active", True):
        return
 
    question = random.choice(PROGRAMMING_QUESTIONS)
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🧠 *Вопрос дня:*\n\n{question}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logging.warning(f"Ошибка quiz_reminder: {e}")
 
    delay = random.randint(300, 540) * 60
    context.job_queue.run_once(quiz_reminder, when=delay, chat_id=chat_id)
 
async def news_reminder(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    data = load_data()
 
    user = data["users"].get(str(chat_id))
    if not user or not user.get("active", True):
        return
 
    article = fetch_random_article()
    if article:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=format_article(article),
                parse_mode="Markdown",
                disable_web_page_preview=False,
            )
        except Exception as e:
            logging.warning(f"Ошибка news_reminder: {e}")
 
    delay = random.randint(180, 360) * 60
    context.job_queue.run_once(news_reminder, when=delay, chat_id=chat_id)
 
# ─────────────────────────────────────────────
# КОМАНДЫ
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()
    get_user(data, user.id)
    save_data(data)
 
    keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton("📌 Задача"), KeyboardButton("✅ Чекин")],
            [KeyboardButton("📋 Лог"), KeyboardButton("🔥 Стрик")],
            [KeyboardButton("📰 Новость"), KeyboardButton("⏸ Пауза")],
            [KeyboardButton("▶️ Возобновить")],
        ],
        resize_keyboard=True,
    )
 
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я твой бот-контролёр доминанты в программировании.\n"
        "Буду спрашивать, что пишешь, и не давать расслабляться 😏\n\n"
        "📌 *Задача* — поставить текущую задачу\n"
        "✅ *Чекин* — отчитаться о прогрессе\n"
        "📋 *Лог* — посмотреть свои записи\n"
        "🔥 *Стрик* — сколько дней подряд активен\n"
        "📰 *Новость* — случайная статья\n"
        "⏸ *Пауза* — отключить напоминания\n\n"
        "Поехали! Что пишешь сегодня?",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
 
    chat_id = update.effective_chat.id
    schedule_random_reminder(context, chat_id)
 
    # удаляем старые jobs перед созданием новых (защита от дублей при повторном /start)
    for job_name in [f"quiz_{chat_id}", f"news_{chat_id}"]:
        for job in context.job_queue.get_jobs_by_name(job_name):
            job.schedule_removal()
 
    context.job_queue.run_once(
        quiz_reminder,
        when=random.randint(60, 180) * 60,
        chat_id=chat_id,
        name=f"quiz_{chat_id}",
    )
    context.job_queue.run_once(
        news_reminder,
        when=random.randint(30, 90) * 60,
        chat_id=chat_id,
        name=f"news_{chat_id}",
    )
 
async def cmd_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = random.choice(DAILY_QUESTIONS)
    context.user_data["awaiting"] = "task"
    await update.message.reply_text(question)
 
async def cmd_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = random.choice(CHECKIN_QUESTIONS)
    context.user_data["awaiting"] = "checkin"
    await update.message.reply_text(question)
 
async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user = get_user(data, update.effective_user.id)
    log = user.get("log", [])
 
    if not log:
        await update.message.reply_text("📋 Лог пустой. Начни с команды 📌 Задача!")
        return
 
    recent = log[-10:]
    text = "📋 *Твои последние записи:*\n\n"
    for entry in reversed(recent):
        text += f"🕐 `{entry['time']}` — {entry['text']}\n"
 
    await update.message.reply_text(text, parse_mode="Markdown")
 
async def cmd_streak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user = get_user(data, update.effective_user.id)
    streak = user.get("streak", 0)
    task = user.get("current_task") or "не задана"
 
    emoji = "🔥" if streak >= 3 else "✨" if streak >= 1 else "💤"
    await update.message.reply_text(
        f"{emoji} *Стрик:* {streak} дн. подряд\n"
        f"📌 *Текущая задача:* {task}",
        parse_mode="Markdown",
    )
 
async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user = get_user(data, update.effective_user.id)
    user["active"] = False
    save_data(data)
    await update.message.reply_text(
        "⏸ Напоминания отключены.\n"
        "Когда будешь готов — нажми ▶️ *Возобновить*.",
        parse_mode="Markdown",
    )
 
async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user = get_user(data, update.effective_user.id)
    user["active"] = True
    save_data(data)
    schedule_random_reminder(context, update.effective_chat.id)
    await update.message.reply_text(
        "▶️ Напоминания включены! Погнали 🚀\n"
        "Что сейчас на очереди?"
    )
 
async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Ищу что-нибудь интересное...")
    article = fetch_random_article()
    if article:
        await update.message.reply_text(
            format_article(article),
            parse_mode="Markdown",
            disable_web_page_preview=False,
        )
    else:
        await update.message.reply_text("😕 Не удалось загрузить статью, попробуй позже.")
 
# ─────────────────────────────────────────────
# ОБРАБОТКА ТЕКСТА
# ─────────────────────────────────────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
 
    if text == "📌 Задача":
        return await cmd_task(update, context)
    elif text == "✅ Чекин":
        return await cmd_checkin(update, context)
    elif text == "📋 Лог":
        return await cmd_log(update, context)
    elif text == "🔥 Стрик":
        return await cmd_streak(update, context)
    elif text == "⏸ Пауза":
        return await cmd_pause(update, context)
    elif text == "▶️ Возобновить":
        return await cmd_resume(update, context)
    elif text == "📰 Новость":
        return await cmd_news(update, context)
 
    awaiting = context.user_data.get("awaiting")
    if awaiting:
        data = load_data()
        user = get_user(data, update.effective_user.id)
 
        now = datetime.now().strftime("%d.%m %H:%M")
        entry = {"time": now, "text": text, "type": awaiting}
        user["log"].append(entry)
 
        if awaiting == "task":
            user["current_task"] = text
            responses = [
                f"🎯 Записал! Задача: *{text}*\nДавай, не сворачивай — пиши код!",
                f"💪 Понял, задача: *{text}*\nЖду отчёта по прогрессу!",
                f"🔥 Отлично! *{text}* — хорошая цель.\nДержу тебя под контролем 😏",
            ]
        else:
            today = datetime.now().strftime("%d.%m.%Y")
            if user.get("last_checkin") != today:
                user["streak"] = user.get("streak", 0) + 1
                user["last_checkin"] = today
            responses = [
                "✅ Записал! Продолжай в том же духе.",
                "📊 Принято. Каждый чекин — шаг вперёд!",
                f"💾 Сохранено. Стрик уже {user['streak']} дн. 🔥",
            ]
 
        save_data(data)
        context.user_data.pop("awaiting", None)
        await update.message.reply_text(random.choice(responses), parse_mode="Markdown")
    else:
        await update.message.reply_text("Используй кнопки или напиши /start 😊")
 
# ─────────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────────
def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
 
    app = Application.builder().token(BOT_TOKEN).build()
 
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("task", cmd_task))
    app.add_handler(CommandHandler("checkin", cmd_checkin))
    app.add_handler(CommandHandler("log", cmd_log))
    app.add_handler(CommandHandler("streak", cmd_streak))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
 
    print("🤖 Бот запущен! Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
 
if __name__ == "__main__":
    main()