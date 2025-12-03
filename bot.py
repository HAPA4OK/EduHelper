import json
import logging
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# 👉 ВСТАВЬ СВОЙ ТОКЕН
BOT_TOKEN = "8451520044:AAE6gcQsi42ccLeHsSNizMTEiXyziouo-NA"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Загружаем вопросы из файла questions.json
BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_FILE = BASE_DIR / "questions.json"

with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# Человеческие названия сфер
SPHERE_LABELS = {
    "it": "IT / Программирование",
    "science": "Наука / Аналитика",
    "design": "Дизайн / UX / UI",
    "art": "Творчество / Искусство",
    "marketing": "Маркетинг / Коммуникации",
    "social": "Социальная / Психология",
    "business": "Бизнес / Предпринимательство",
    "sport": "Спорт / Активность",
}


# -----------------------------------------------------------
# ФУНКЦИЯ НАЧИСЛЕНИЯ БАЛЛОВ
# -----------------------------------------------------------
def apply_answer(score: dict, question_index: int, answer_index: int):
    """Начисляет баллы по ответу пользователя."""
    answer = QUESTIONS[question_index]["answers"][answer_index]
    for sphere in answer["scores"]:
        score[sphere] += 1


# -----------------------------------------------------------
# СТАРТ — ПОКАЗЫВАЕМ КНОПКУ «НАЧАТЬ ТЕСТ»
# -----------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("Начать тест")]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Привет! 👋\nНажми кнопку ниже, чтобы начать тест:",
        reply_markup=markup
    )

    # Обнуляем результаты заранее
    context.user_data["score"] = {k: 0 for k in SPHERE_LABELS}


# -----------------------------------------------------------
# ПО НАЖАТИЮ КНОПКИ «НАЧАТЬ ТЕСТ»
# -----------------------------------------------------------
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Начать тест":
        context.user_data["score"] = {k: 0 for k in SPHERE_LABELS}
        await send_question(update, context, question_index=0, new_message=True)


# -----------------------------------------------------------
# ПОКАЗ ВОПРОСОВ (С ПРОГРЕССОМ)
# -----------------------------------------------------------
async def send_question(
    update_or_query: Update,
    context: ContextTypes.DEFAULT_TYPE,
    question_index: int,
    new_message: bool,
):
    """Отправляет вопрос пользователю с прогрессом."""
    total = len(QUESTIONS)
    if question_index >= total:
        await show_result(update_or_query, context)
        return

    q = QUESTIONS[question_index]

    # --- прогресс ---
    current = question_index + 1
    bar_len = 10
    filled = int(bar_len * current / total)
    bar = "█" * filled + "░" * (bar_len - filled)

    header = f"Вопрос {current} из {total}  [{bar}]\n\n"
    text = header + q["text"]

    keyboard = []
    for i, answer in enumerate(q["answers"]):
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=answer["label"],
                    callback_data=f"{question_index}:{i}",
                )
            ]
        )

    markup = InlineKeyboardMarkup(keyboard)

    # Если первый вопрос — шлём новое сообщение
    if new_message:
        await update_or_query.message.reply_text(text, reply_markup=markup)
    else:
        # Иначе обновляем сообщение вопроса
        await update_or_query.callback_query.message.edit_text(
            text, reply_markup=markup
        )


# -----------------------------------------------------------
# ПРИ НАЖАТИИ INLINE-КНОПКИ
# -----------------------------------------------------------
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    q_idx, a_idx = map(int, query.data.split(":"))

    score = context.user_data.get("score")
    if score is None:
        score = {k: 0 for k in SPHERE_LABELS}
        context.user_data["score"] = score

    apply_answer(score, q_idx, a_idx)

    await send_question(update, context, question_index=q_idx + 1, new_message=False)


# -----------------------------------------------------------
# ФИНАЛЬНЫЙ РЕЗУЛЬТАТ
# -----------------------------------------------------------
async def show_result(update_or_query: Update, context: ContextTypes.DEFAULT_TYPE):
    score = context.user_data.get("score") or {}
    if not score:
        # На всякий случай, если что-то пошло не так
        if update_or_query.callback_query:
            await update_or_query.callback_query.message.edit_text(
                "Похоже, тест не был пройден. Попробуй ещё раз: /start"
            )
        else:
            await update_or_query.message.reply_text(
                "Похоже, тест не был пройден. Попробуй ещё раз: /start"
            )
        return

    max_score = max(score.values())
    best = [k for k, v in score.items() if v == max_score]

    text = "🎉 *Тест завершён!*\n\nТвои сильные направления развития:\n\n"
    for sphere in best:
        text += f"• *{SPHERE_LABELS[sphere]}* — {score[sphere]} баллов\n"

    text += "\nХочешь пройти ещё раз? /start"

    # Тут show_result вызывается из callback, так что используем callback_query.message
    if update_or_query.callback_query:
        await update_or_query.callback_query.message.edit_text(
            text, parse_mode="Markdown"
        )
    else:
        await update_or_query.message.reply_text(text, parse_mode="Markdown")


# -----------------------------------------------------------
# ЗАПУСК БОТА
# -----------------------------------------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    app.add_handler(CallbackQueryHandler(handle_answer))

    logger.info("Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    main()
