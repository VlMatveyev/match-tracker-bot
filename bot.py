import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from config import BOT_TOKEN
from database import db, Match, Chat
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, and_

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Функция для создания главной клавиатуры (только одна кнопка)
def get_main_keyboard():
    """Возвращает клавиатуру с одной кнопкой для вызова команд"""
    keyboard = [
        [InlineKeyboardButton("⚽ Вперед!", callback_data="show_commands")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Функция для создания клавиатуры с командами
def get_commands_keyboard():
    """Возвращает клавиатуру со всеми командами"""
    keyboard = [
        [InlineKeyboardButton("⏭ Следующий матч", callback_data="next"),
         InlineKeyboardButton("📅 Матчи сегодня", callback_data="today")],
        [InlineKeyboardButton("📆 Ближайшие матчи", callback_data="upcoming"),
         InlineKeyboardButton("🔔 Подписаться", callback_data="subscribe")],
        [InlineKeyboardButton("❌ Отписаться", callback_data="unsubscribe")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Функция для создания кнопки "Назад к меню"
def get_back_keyboard():
    """Возвращает клавиатуру с кнопкой возврата в меню"""
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение"""
    logger.info(
        f"🔵 ПОЛУЧЕНА КОМАНДА /start от пользователя {update.effective_user.id} в чате {update.effective_chat.id}")

    welcome_text = """
🔵 <b>Добро пожаловать! Я бот матчей АПЛ.</b>

Нажмите кнопку ниже, чтобы увидеть список доступных команд.

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


async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список команд"""
    query = update.callback_query
    await query.answer()

    text = """
📋 <b>Доступные команды:</b>

⏭ <b>Следующий матч</b> - показать ближайший матч
📅 <b>На сегодня</b> - матчи на сегодня
📆 <b>Ближайшие матчи</b> - следующие 5 матчей
🔔 <b>Подписаться</b> - на уведомления о матчах
❌ <b>Отписаться</b> - отписаться от уведомлений

Выберите нужную команду:
    """

    await query.message.reply_text(
        text,
        reply_markup=get_commands_keyboard(),
        parse_mode='HTML'
    )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться к главному меню"""
    query = update.callback_query
    await query.answer()

    text = """
🔵 <b>Главное меню</b>

Нажмите кнопку ниже, чтобы увидеть список доступных команд.
    """

    await query.message.reply_text(
        text,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


async def next_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать следующий матч"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /next от пользователя {update.effective_user.id}")

    match = db.get_next_match()

    if not match:
        text = "😕 Нет запланированных матчей"
    else:
        date_str = match.match_date.strftime("%d.%m.%Y в %H:%M")
        text = f"""
⚽ <b>Следующий матч Челси:</b>

🏆 Турнир: {match.tournament}
🏟 Матч: {match.home_team} vs {match.away_team}
📅 Дата: {date_str}

🔵 Вперед, Челси! 🔵
        """

    # Определяем, откуда пришел вызов (кнопка или команда)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(text, reply_markup=get_back_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=get_main_keyboard(), parse_mode='HTML')


async def today_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Матчи на сегодня"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /today от пользователя {update.effective_user.id}")

    matches = db.get_today_matches()

    if not matches:
        text = "😴 Сегодня матчей нет"
    else:
        text = "📅 <b>Матчи Челси на сегодня:</b>\n\n"
        for match in matches:
            time_str = match.match_date.strftime("%H:%M")
            text += f"⏰ {time_str} - {match.home_team} vs {match.away_team} ({match.tournament})\n"

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(text, reply_markup=get_back_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=get_main_keyboard(), parse_mode='HTML')


async def upcoming_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Следующие 5 матчей"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /upcoming от пользователя {update.effective_user.id}")

    matches = db.get_upcoming_matches(limit=5)

    if not matches:
        text = "📆 Нет ближайших матчей"
    else:
        text = "📆 <b>Следующие 5 матчей Челси:</b>\n\n"
        for i, match in enumerate(matches, 1):
            date_str = match.match_date.strftime("%d.%m.%Y в %H:%M")
            text += f"{i}. ⚽ {match.home_team} vs {match.away_team}\n"
            text += f"   📅 {date_str}\n"
            text += f"   🏆 {match.tournament}\n\n"

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(text, reply_markup=get_back_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=get_main_keyboard(), parse_mode='HTML')


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подписка на уведомления"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /subscribe от пользователя {update.effective_user.id}")

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username

    session = db.Session()
    try:
        existing = session.execute(
            select(Chat).where(Chat.chat_id == chat_id)
        ).scalar_one_or_none()

        if not existing:
            new_chat = Chat(
                chat_id=chat_id,
                user_id=user_id,
                username=username,
                subscribed_at=datetime.datetime.now()
            )
            session.add(new_chat)
            session.commit()
            text = "✅ Вы подписались на уведомления о матчах!"
            logger.info(f"✅ Пользователь {user_id} подписался на уведомления")
        else:
            text = "⚠️ Вы уже подписаны на уведомления"
    except Exception as e:
        session.rollback()
        text = "❌ Ошибка при подписке"
        logger.error(f"Ошибка при подписке: {e}")
    finally:
        session.close()

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(text, reply_markup=get_back_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=get_main_keyboard())


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отписка от уведомлений"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /unsubscribe от пользователя {update.effective_user.id}")

    chat_id = update.effective_chat.id

    session = db.Session()
    try:
        chat = session.execute(
            select(Chat).where(Chat.chat_id == chat_id)
        ).scalar_one_or_none()

        if chat:
            session.delete(chat)
            session.commit()
            text = "❌ Вы отписались от уведомлений"
            logger.info(f"✅ Пользователь {update.effective_user.id} отписался от уведомлений")
        else:
            text = "⚠️ Вы не были подписаны"
    except Exception as e:
        session.rollback()
        text = "❌ Ошибка при отписке"
        logger.error(f"Ошибка при отписке: {e}")
    finally:
        session.close()

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(text, reply_markup=get_back_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=get_main_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    logger.info(f"🔵 ПОЛУЧЕНО НАЖАТИЕ КНОПКИ '{query.data}' от пользователя {update.effective_user.id}")

    if query.data == "show_commands":
        await show_commands(update, context)
    elif query.data == "back_to_main":
        await back_to_main(update, context)
    elif query.data == "next":
        await next_match(update, context)
    elif query.data == "today":
        await today_matches(update, context)
    elif query.data == "upcoming":
        await upcoming_matches(update, context)
    elif query.data == "subscribe":
        await subscribe(update, context)
    elif query.data == "unsubscribe":
        await unsubscribe(update, context)


async def check_and_notify(context: ContextTypes.DEFAULT_TYPE):
    """Проверка матчей и отправка уведомлений"""
    now = datetime.datetime.now()
    check_time = now + datetime.timedelta(hours=1)

    logger.info(f"🔍 Проверка матчей для уведомлений...")

    session = db.Session()
    try:
        matches = session.execute(
            select(Match).where(
                and_(
                    Match.match_date <= check_time,
                    Match.match_date > now,
                    Match.is_notified == False,
                    Match.match_status == 'scheduled'
                )
            )
        ).scalars().all()

        if not matches:
            logger.info("📭 Нет матчей для уведомления")
            return

        subscribed_chats = session.execute(select(Chat.chat_id)).scalars().all()

        if not subscribed_chats:
            logger.info("📭 Нет подписчиков для уведомлений")
            return

        for match in matches:
            time_until = match.match_date - now
            minutes = int(time_until.total_seconds() / 60)

            message = f"""
⚠️ <b>Скоро начнется матч!</b>

🏆 {match.tournament}
⚽ {match.home_team} vs {match.away_team}
⏱ Начало через {minutes} минут

🔵 Вперед, Челси! 🔵
            """

            for chat_id in subscribed_chats:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                    logger.info(f"✅ Уведомление отправлено в чат {chat_id}")
                except Exception as e:
                    logger.error(f"❌ Не удалось отправить уведомление в чат {chat_id}: {e}")

                    if "Forbidden" in str(e) or "chat not found" in str(e):
                        try:
                            chat_to_delete = session.execute(
                                select(Chat).where(Chat.chat_id == chat_id)
                            ).scalar_one_or_none()
                            if chat_to_delete:
                                session.delete(chat_to_delete)
                                session.commit()
                                logger.info(f"🗑 Удалена недействительная подписка для чата {chat_id}")
                        except Exception as delete_error:
                            logger.error(f"Ошибка при удалении подписки: {delete_error}")

            match.is_notified = True
            session.commit()
            logger.info(f"✅ Матч {match.id} отмечен как уведомленный")

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Ошибка в check_and_notify: {e}")
    finally:
        session.close()


def main():
    """Запуск бота"""
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