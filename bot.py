import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from config import BOT_TOKEN
from database import db, Match
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ID чатов, где бот должен отправлять уведомления
NOTIFICATION_CHATS = []


# Функция для создания клавиатуры
def get_main_keyboard():
    """Возвращает основную клавиатуру с кнопками"""
    keyboard = [
        [InlineKeyboardButton("⏭ Следующий матч", callback_data="next"),
         InlineKeyboardButton("📅 Матчи на сегодня", callback_data="today")],
        [InlineKeyboardButton("📆 Ближайшие матчи", callback_data="upcoming"),
         InlineKeyboardButton("🔔 Подписаться", callback_data="subscribe")],
        [InlineKeyboardButton("❌ Отписаться", callback_data="unsubscribe")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение"""
    logger.info(
        f"🔵 ПОЛУЧЕНА КОМАНДА /start от пользователя {update.effective_user.id} в чате {update.effective_chat.id}")

    welcome_text = """
🔵 <b>Добро пожаловать! Я бот матчей Челси.</b>

Доступные команды:
/next - следующий матч
/today - матчи на сегодня
/upcoming - ближайшие матчи (7 дней)
/subscribe - подписаться на уведомления
/unsubscribe - отписаться от уведомлений

⚽ <b>Вперед, Челси!</b>
    """

    try:
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        logger.info(f"✅ Ответ на /start отправлен пользователю {update.effective_user.id}")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке ответа на /start: {e}")


async def next_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать следующий матч"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /next от пользователя {update.effective_user.id}")

    match = db.get_next_match()

    if not match:
        await update.message.reply_text(
            "😕 Нет запланированных матчей",
            reply_markup=get_main_keyboard()
        )
        return

    date_str = match.match_date.strftime("%d.%m.%Y в %H:%M")

    message = f"""
⚽ <b>Следующий матч Челси:</b>

🏆 Турнир: {match.tournament}
🏟 Матч: {match.home_team} vs {match.away_team}
📅 Дата: {date_str}

🔵 Вперед, Челси! 🔵
    """

    await update.message.reply_text(
        message,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


async def today_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Матчи на сегодня"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /today от пользователя {update.effective_user.id}")

    matches = db.get_today_matches()

    if not matches:
        await update.message.reply_text(
            "😴 Сегодня матчей нет",
            reply_markup=get_main_keyboard()
        )
        return

    message = "📅 <b>Матчи Челси на сегодня:</b>\n\n"

    for match in matches:
        time_str = match.match_date.strftime("%H:%M")
        message += f"⏰ {time_str} - {match.home_team} vs {match.away_team} ({match.tournament})\n"

    await update.message.reply_text(
        message,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


async def upcoming_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ближайшие матчи"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /upcoming от пользователя {update.effective_user.id}")

    matches = db.get_upcoming_matches()

    if not matches:
        await update.message.reply_text(
            "📆 Нет ближайших матчей",
            reply_markup=get_main_keyboard()
        )
        return

    message = "📆 <b>Ближайшие матчи Челси (7 дней):</b>\n\n"

    for match in matches:
        date_str = match.match_date.strftime("%d.%m %H:%M")
        message += f"📌 {date_str} - {match.home_team} vs {match.away_team}\n"
        message += f"   🏆 {match.tournament}\n\n"

    await update.message.reply_text(
        message,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подписка на уведомления"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /subscribe от пользователя {update.effective_user.id}")

    chat_id = update.effective_chat.id

    if chat_id not in NOTIFICATION_CHATS:
        NOTIFICATION_CHATS.append(chat_id)
        text = "✅ Вы подписались на уведомления о матчах!"
        logger.info(
            f"✅ Пользователь {update.effective_user.id} подписался на уведомления. Всего подписок: {len(NOTIFICATION_CHATS)}")
    else:
        text = "⚠️ Вы уже подписаны на уведомления"

    await update.message.reply_text(
        text,
        reply_markup=get_main_keyboard()
    )


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отписка от уведомлений"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /unsubscribe от пользователя {update.effective_user.id}")

    chat_id = update.effective_chat.id

    if chat_id in NOTIFICATION_CHATS:
        NOTIFICATION_CHATS.remove(chat_id)
        text = "❌ Вы отписались от уведомлений"
        logger.info(
            f"✅ Пользователь {update.effective_user.id} отписался от уведомлений. Осталось подписок: {len(NOTIFICATION_CHATS)}")
    else:
        text = "⚠️ Вы не были подписаны"

    await update.message.reply_text(
        text,
        reply_markup=get_main_keyboard()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    logger.info(f"🔵 ПОЛУЧЕНО НАЖАТИЕ КНОПКИ '{query.data}' от пользователя {update.effective_user.id}")

    if query.data == "next":
        match = db.get_next_match()
        if match:
            date_str = match.match_date.strftime("%d.%m.%Y в %H:%M")
            text = f"⚽ {match.home_team} vs {match.away_team}\n📅 {date_str}\n🏆 {match.tournament}"
        else:
            text = "Нет запланированных матчей"
        await query.message.reply_text(text, reply_markup=get_main_keyboard())

    elif query.data == "today":
        matches = db.get_today_matches()
        if matches:
            text = "📅 Матчи на сегодня:\n"
            for m in matches:
                text += f"\n⏰ {m.match_date.strftime('%H:%M')} - {m.home_team} vs {m.away_team}"
        else:
            text = "Сегодня матчей нет"
        await query.message.reply_text(text, reply_markup=get_main_keyboard())

    elif query.data == "upcoming":
        matches = db.get_upcoming_matches()
        if matches:
            text = "📆 Ближайшие матчи:\n"
            for m in matches:
                text += f"\n📌 {m.match_date.strftime('%d.%m %H:%M')} - {m.home_team} vs {m.away_team}"
        else:
            text = "Нет ближайших матчей"
        await query.message.reply_text(text, reply_markup=get_main_keyboard())

    elif query.data == "subscribe":
        chat_id = update.effective_chat.id
        if chat_id not in NOTIFICATION_CHATS:
            NOTIFICATION_CHATS.append(chat_id)
            text = "✅ Вы подписались на уведомления!"
            logger.info(f"✅ Пользователь {update.effective_user.id} подписался через кнопку")
        else:
            text = "⚠️ Вы уже подписаны"
        await query.message.reply_text(text, reply_markup=get_main_keyboard())

    elif query.data == "unsubscribe":
        chat_id = update.effective_chat.id
        if chat_id in NOTIFICATION_CHATS:
            NOTIFICATION_CHATS.remove(chat_id)
            text = "❌ Вы отписались от уведомлений"
            logger.info(f"✅ Пользователь {update.effective_user.id} отписался через кнопку")
        else:
            text = "⚠️ Вы не были подписаны"
        await query.message.reply_text(text, reply_markup=get_main_keyboard())


async def check_and_notify(context: ContextTypes.DEFAULT_TYPE):
    """Проверка матчей и отправка уведомлений"""
    now = datetime.datetime.now()
    check_time = now + datetime.timedelta(hours=1)

    session = db.Session()
    result = session.execute(
        "SELECT * FROM matches WHERE match_date <= ? AND match_date > ? AND is_notified = 0 AND match_status = 'scheduled'",
        (check_time.isoformat(), now.isoformat())
    )
    rows = result.fetchall()

    for row in rows:
        match_id, tournament, home_team, away_team, match_date_str, is_notified, match_status = row

        try:
            match_date = datetime.datetime.fromisoformat(match_date_str)
        except ValueError:
            match_date = datetime.datetime.fromisoformat(match_date_str.split('.')[0])

        time_until = match_date - now
        minutes = int(time_until.total_seconds() / 60)

        message = f"""
⚠️ <b>Скоро начнется матч!</b>

🏆 {tournament}
⚽ {home_team} vs {away_team}
⏱ Начало через {minutes} минут

🔵 Вперед, Челси! 🔵
        """

        for chat_id in NOTIFICATION_CHATS:
            try:
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                logger.info(f"✅ Уведомление отправлено в чат {chat_id}")
            except Exception as e:
                logger.error(f"❌ Не удалось отправить уведомление в чат {chat_id}: {e}")

        session.execute("UPDATE matches SET is_notified = 1 WHERE id = ?", (match_id,))
        session.commit()

    session.close()


async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все матчи в базе"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /show от пользователя {update.effective_user.id}")

    try:
        session = db.Session()
        result = session.execute(
            "SELECT id, tournament, home_team, away_team, match_date, is_notified, match_status FROM matches ORDER BY match_date LIMIT 10")
        rows = result.fetchall()

        count = session.execute("SELECT COUNT(*) FROM matches").scalar()
        session.close()

        if not rows:
            await update.message.reply_text(
                "📭 База данных пуста",
                reply_markup=get_main_keyboard()
            )
            return

        message = f"📋 <b>Всего матчей: {count}</b>\n\n"
        message += "<b>Первые 10 матчей:</b>\n\n"
        for row in rows:
            date_obj = datetime.datetime.fromisoformat(row[4])
            date_str = date_obj.strftime("%d.%m.%Y %H:%M")
            message += f"🆔 ID: {row[0]}\n"
            message += f"🏆 {row[1]}\n"
            message += f"⚽ {row[2]} vs {row[3]}\n"
            message += f"📅 {date_str}\n"
            message += f"📊 Статус: {row[6]}\n"
            message += "─" * 20 + "\n"

        await update.message.reply_text(
            message,
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_main_keyboard()
        )
        logger.error(f"Ошибка в show_matches: {e}")


def main():
    """Запуск бота"""
    # Проверяем, есть ли матчи в базе
    session = db.Session()
    count = session.query(Match).count()
    session.close()

    if count == 0:
        logger.info("⚠️ База данных пуста. Загружаем матчи АПЛ...")
        try:
            from load_fixtures import load_fixtures
            load_fixtures(clear_first=False)
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке матчей: {e}")
    else:
        logger.info(f"✅ В базе уже есть {count} матчей")

    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("next", next_match))
    application.add_handler(CommandHandler("today", today_matches))
    application.add_handler(CommandHandler("upcoming", upcoming_matches))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("show", show_matches))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Настраиваем планировщик для уведомлений
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_and_notify,
        'interval',
        minutes=5,
        args=[application]
    )
    scheduler.start()

    logger.info("🚀 Бот запущен и ожидает команды...")
    application.run_polling()


if __name__ == '__main__':
    main()