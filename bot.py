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

# Список доступных команд
AVAILABLE_TEAMS = ["Челси", "Манчестер Юнайтед"]


# Функция для создания главной клавиатуры (только одна кнопка)
def get_main_keyboard():
    """Возвращает клавиатуру с одной кнопкой для вызова команд"""
    keyboard = [
        [InlineKeyboardButton("📋 Меню команд", callback_data="show_commands")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Функция для создания клавиатуры с командами
def get_commands_keyboard():
    """Возвращает клавиатуру со всеми командами"""
    keyboard = [
        [InlineKeyboardButton("⏭ Следующий матч", callback_data="next"),
         InlineKeyboardButton("📅 На сегодня", callback_data="today")],
        [InlineKeyboardButton("📆 Ближайшие 5", callback_data="upcoming"),
         InlineKeyboardButton("🔔 Подписаться", callback_data="subscribe")],
        [InlineKeyboardButton("❌ Отписаться", callback_data="unsubscribe")],
        [InlineKeyboardButton("🔄 Сменить команду", callback_data="change_team")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Функция для создания клавиатуры выбора команды
def get_team_selection_keyboard():
    """Возвращает клавиатуру для выбора команды"""
    keyboard = []
    for team in AVAILABLE_TEAMS:
        keyboard.append([InlineKeyboardButton(f"⚽ {team}", callback_data=f"select_team_{team}")])
    return InlineKeyboardMarkup(keyboard)


# Функция для создания кнопки "Назад к меню"
def get_back_keyboard():
    """Возвращает клавиатуру с кнопкой возврата в меню"""
    keyboard = [
        [InlineKeyboardButton("◀️ Назад к меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение с выбором команды"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /start от пользователя {update.effective_user.id}")

    chat_id = update.effective_chat.id

    # Проверяем, выбрана ли уже команда
    selected_team = db.get_user_selected_team(chat_id)

    if selected_team:
        welcome_text = f"""
🔵 <b>Добро пожаловать! Я бот для отслеживания матчей.</b>

Ваша команда: <b>{selected_team}</b>

Нажмите кнопку ниже, чтобы увидеть список доступных команд.

⚽ <b>Вперед, {selected_team}!</b>
        """
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    else:
        # Если команда не выбрана, предлагаем выбрать
        welcome_text = """
🔵 <b>Добро пожаловать! Я бот для отслеживания матчей.</b>

Выберите вашу любимую команду, чтобы начать:
        """
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_team_selection_keyboard(),
            parse_mode='HTML'
        )


async def select_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора команды"""
    query = update.callback_query
    await query.answer()

    team = query.data.replace("select_team_", "")
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"

    # Сохраняем выбранную команду
    db.set_user_selected_team(chat_id, user_id, username, team)

    text = f"""
✅ Вы выбрали команду: <b>{team}</b>

Теперь я буду показывать матчи только этой команды.
    """

    await query.message.reply_text(
        text,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


async def change_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Смена команды"""
    query = update.callback_query
    await query.answer()

    text = "🔄 Выберите новую команду:"

    await query.message.reply_text(
        text,
        reply_markup=get_team_selection_keyboard(),
        parse_mode='HTML'
    )


async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список команд"""
    query = update.callback_query

    chat_id = update.effective_chat.id
    selected_team = db.get_user_selected_team(chat_id)

    text = f"""
📋 <b>Доступные команды для {selected_team}:</b>

⏭ <b>Следующий матч</b> - показать ближайший матч
📅 <b>На сегодня</b> - матчи на сегодня
📆 <b>Ближайшие</b> - ближайшие матчи
🔔 <b>Подписаться</b> - на уведомления о матчах
❌ <b>Отписаться</b> - отписаться от уведомлений
🔄 <b>Сменить команду</b> - выбрать другую команду

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

    chat_id = update.effective_chat.id
    selected_team = db.get_user_selected_team(chat_id)

    text = f"""
🔵 <b>Главное меню</b>

Ваша команда: <b>{selected_team}</b>

Нажмите кнопку ниже, чтобы увидеть список доступных команд.
    """

    await query.message.reply_text(
        text,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


async def next_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать следующий матч для выбранной команды"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /next от пользователя {update.effective_user.id}")

    chat_id = update.effective_chat.id
    selected_team = db.get_user_selected_team(chat_id)

    if not selected_team:
        text = "⚠️ Сначала выберите команду через /start"
        if update.callback_query:
            await update.callback_query.message.reply_text(text, reply_markup=get_team_selection_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=get_team_selection_keyboard())
        return

    match = db.get_next_match(team=selected_team)

    if not match:
        text = f"😕 Нет запланированных матчей для {selected_team}"
    else:
        date_str = match.match_date.strftime("%d.%m.%Y в %H:%M")
        text = f"""
⚽ <b>Следующий матч {selected_team}:</b>

🏆 Турнир: {match.tournament}
🏟 Матч: {match.home_team} vs {match.away_team}
📅 Дата: {date_str}

⚽ <b>Вперед, {selected_team}!</b>
        """

    if update.callback_query:
        query = update.callback_query
        await query.message.reply_text(text, reply_markup=get_back_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=get_main_keyboard(), parse_mode='HTML')


async def today_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Матчи на сегодня для выбранной команды"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /today от пользователя {update.effective_user.id}")

    chat_id = update.effective_chat.id
    selected_team = db.get_user_selected_team(chat_id)

    if not selected_team:
        text = "⚠️ Сначала выберите команду через /start"
        if update.callback_query:
            await update.callback_query.message.reply_text(text, reply_markup=get_team_selection_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=get_team_selection_keyboard())
        return

    matches = db.get_today_matches(team=selected_team)

    if not matches:
        text = f"😴 Сегодня матчей {selected_team} нет"
    else:
        text = f"📅 <b>Матчи {selected_team} на сегодня:</b>\n\n"
        for match in matches:
            time_str = match.match_date.strftime("%H:%M")
            text += f"⏰ {time_str} - {match.home_team} vs {match.away_team} ({match.tournament})\n"

    if update.callback_query:
        query = update.callback_query
        await query.message.reply_text(text, reply_markup=get_back_keyboard(), parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=get_main_keyboard(), parse_mode='HTML')


async def upcoming_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Следующие матчи для выбранной команды"""
    logger.info(f"🔵 ПОЛУЧЕНА КОМАНДА /upcoming от пользователя {update.effective_user.id}")

    chat_id = update.effective_chat.id
    selected_team = db.get_user_selected_team(chat_id)

    if not selected_team:
        text = "⚠️ Сначала выберите команду через /start"
        if update.callback_query:
            await update.callback_query.message.reply_text(text, reply_markup=get_team_selection_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=get_team_selection_keyboard())
        return

    matches = db.get_upcoming_matches(limit=5, team=selected_team)

    if not matches:
        text = f"📆 Нет ближайших матчей для {selected_team}"
    else:
        text = f"📆 <b>Ближайшие матчи {selected_team}:</b>\n\n"
        for i, match in enumerate(matches, 1):
            date_str = match.match_date.strftime("%d.%m.%Y в %H:%M")
            text += f"{i}. ⚽ {match.home_team} vs {match.away_team}\n"
            text += f"   📅 {date_str}\n"
            text += f"   🏆 {match.tournament}\n\n"

    if update.callback_query:
        query = update.callback_query
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
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, reply_markup=get_back_keyboard())
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
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, reply_markup=get_back_keyboard())
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
    elif query.data == "change_team":
        await change_team(update, context)
    elif query.data.startswith("select_team_"):
        await select_team(update, context)


async def check_and_notify():
    pass

def main():
    """Запуск бота"""
    # Проверяем, есть ли матчи в базе
    session = db.Session()
    count = session.query(Match).count()
    session.close()

    if count == 0:
        logger.info("⚠️ База данных пуста. Загружаем матчи...")
        try:
            from load_fixtures import load_fixtures
            load_fixtures()
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

    # Сначала запускаем планировщик
    scheduler.start()

    # Потом запускаем приложение
    application.run_polling()

if __name__ == '__main__':
    main()