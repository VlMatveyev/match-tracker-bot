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


# Функция для получения подписанных чатов из БД
async def get_subscribed_chats():
    """Получает список ID чатов, подписанных на уведомления"""
    session = db.Session()
    try:
        chats = session.execute(select(Chat.chat_id)).scalars().all()
        return list(chats)
    finally:
        session.close()


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
    user_id = update.effective_user.id
    username = update.effective_user.username

    session = db.Session()
    try:
        # Проверяем, есть ли уже такая подписка
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

    await update.message.reply_text(
        text,
        reply_markup=get_main_keyboard()
    )


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
                text = "✅ Вы подписались на уведомления!"
                logger.info(f"✅ Пользователь {user_id} подписался через кнопку")
            else:
                text = "⚠️ Вы уже подписаны"
        except Exception as e:
            session.rollback()
            text = "❌ Ошибка при подписке"
            logger.error(f"Ошибка при подписке через кнопку: {e}")
        finally:
            session.close()

        await query.message.reply_text(text, reply_markup=get_main_keyboard())

    elif query.data == "unsubscribe":
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
                logger.info(f"✅ Пользователь {update.effective_user.id} отписался через кнопку")
            else:
                text = "⚠️ Вы не были подписаны"
        except Exception as e:
            session.rollback()
            text = "❌ Ошибка при отписке"
            logger.error(f"Ошибка при отписке через кнопку: {e}")
        finally:
            session.close()

        await query.message.reply_text(text, reply_markup=get_main_keyboard())


async def check_and_notify(context: ContextTypes.DEFAULT_TYPE):
    """Проверка матчей и отправка уведомлений"""
    now = datetime.datetime.now()
    check_time = now + datetime.timedelta(hours=1)

    logger.info(f"🔍 Проверка матчей для уведомлений...")

    session = db.Session()
    try:
        # Ищем матчи, которые начнутся через час и еще не уведомили
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

        # Получаем список подписанных чатов
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

            # Отправляем уведомления всем подписчикам
            for chat_id in subscribed_chats:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                    logger.info(f"✅ Уведомление отправлено в чат {chat_id}")
                except Exception as e:
                    logger.error(f"❌ Не удалось отправить уведомление в чат {chat_id}: {e}")

                    # Если бот заблокирован или чат не найден, удаляем подписку
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

            # Отмечаем матч как уведомленный
            match.is_notified = True
            session.commit()
            logger.info(f"✅ Матч {match.id} отмечен как уведомленный")

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Ошибка в check_and_notify: {e}")
    finally:
        session.close()


async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все матчи в базе"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /show от пользователя {update.effective_user.id}")

    session = db.Session()
    try:
        # Получаем общее количество
        total_count = session.query(Match).count()

        # Получаем первые 10 матчей
        matches = session.query(Match).order_by(Match.match_date).limit(10).all()

        if not matches:
            await update.message.reply_text(
                "📭 База данных пуста",
                reply_markup=get_main_keyboard()
            )
            return

        message = f"📋 <b>Всего матчей: {total_count}</b>\n\n"
        message += "<b>Первые 10 матчей:</b>\n\n"

        for match in matches:
            date_str = match.match_date.strftime("%d.%m.%Y %H:%M")
            message += f"🆔 ID: {match.id}\n"
            message += f"🏆 {match.tournament}\n"
            message += f"⚽ {match.home_team} vs {match.away_team}\n"
            message += f"📅 {date_str}\n"
            message += f"📊 Статус: {match.match_status}\n"
            message += f"🔔 Уведомлен: {'Да' if match.is_notified else 'Нет'}\n"
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
    finally:
        session.close()


async def show_subscribers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список подписчиков (только для админа)"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /subscribers от пользователя {update.effective_user.id}")

    # Здесь можно добавить проверку на админа
    # if update.effective_user.id not in ADMIN_IDS:
    #     await update.message.reply_text("⛔ У вас нет прав для этой команды")
    #     return

    session = db.Session()
    try:
        subscribers = session.query(Chat).order_by(Chat.subscribed_at.desc()).all()

        if not subscribers:
            await update.message.reply_text("📭 Нет подписчиков")
            return

        message = "📋 <b>Список подписчиков:</b>\n\n"
        for sub in subscribers:
            date_str = sub.subscribed_at.strftime("%d.%m.%Y %H:%M")
            message += f"👤 ID: {sub.user_id}\n"
            message += f"💬 Chat: {sub.chat_id}\n"
            message += f"📝 Username: @{sub.username if sub.username else 'Нет'}\n"
            message += f"📅 Подписался: {date_str}\n"
            message += "─" * 20 + "\n"

        await update.message.reply_text(
            message,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Ошибка при показе подписчиков: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    finally:
        session.close()


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
    application.add_handler(CommandHandler("subscribers", show_subscribers))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Настраиваем планировщик для уведомлений
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_and_notify,
        'interval',
        minutes=5,
        args=[application]  # Передаем application, он будет преобразован в context
    )
    scheduler.start()

    logger.info("🚀 Бот запущен и ожидает команды...")
    application.run_polling()


if __name__ == '__main__':
    main()