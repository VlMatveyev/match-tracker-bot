import datetime
import logging
from database import db, Match

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ТОЛЬКО ПРЕДСТОЯЩИЕ матчи Челси (АПЛ + Кубки + ЛЧ)
# Время указано МОСКОВСКОЕ (UTC+3) на основе championat.com
UPCOMING_FIXTURES = [
    # Лига чемпионов - Март 2026 (1/8 финала)
    {"date": "2026-03-11 23:00", "home": "ПСЖ", "away": "Челси", "tournament": "Лига чемпионов"},
    # 1/8 финала, 1-й матч

    # АПЛ - Март 2026
    {"date": "2026-03-14 20:30", "home": "Челси", "away": "Ньюкасл", "tournament": "АПЛ"},
    {"date": "2026-03-21 20:30", "home": "Эвертон", "away": "Челси", "tournament": "АПЛ"},

    # Лига чемпионов - Март 2026 (1/8 финала ответный)
    {"date": "2026-03-17 23:00", "home": "Челси", "away": "ПСЖ", "tournament": "Лига чемпионов"},  # 1/8 финала ответный

    # Кубок Англии - Апрель 2026
    {"date": "2026-04-04 17:00", "home": "Челси", "away": "Порт Вейл", "tournament": "Кубок Англии"},  # Четвертьфинал

    # АПЛ - Апрель 2026
    {"date": "2026-04-11 17:00", "home": "Челси", "away": "Манчестер Сити", "tournament": "АПЛ"},
    {"date": "2026-04-18 17:00", "home": "Челси", "away": "Манчестер Юнайтед", "tournament": "АПЛ"},
    {"date": "2026-04-25 17:00", "home": "Брайтон", "away": "Челси", "tournament": "АПЛ"},

    # АПЛ - Май 2026
    {"date": "2026-05-02 17:00", "home": "Челси", "away": "Ноттингем Форест", "tournament": "АПЛ"},
    {"date": "2026-05-09 17:00", "home": "Ливерпуль", "away": "Челси", "tournament": "АПЛ"},
    {"date": "2026-05-17 17:00", "home": "Челси", "away": "Тоттенхэм", "tournament": "АПЛ"},
    {"date": "2026-05-24 18:00", "home": "Сандерленд", "away": "Челси", "tournament": "АПЛ"},
]

# Если Челси выйдет в четвертьфинал Лиги чемпионов
CHAMPIONS_LEAGUE_QF = {
    "first_leg": {"date": "2026-04-07 22:00", "home": "TBD", "away": "Челси", "tournament": "Лига чемпионов"},
    "second_leg": {"date": "2026-04-14 22:00", "home": "Челси", "away": "TBD", "tournament": "Лига чемпионов"}
}

# Если Челси выйдет в полуфинал Кубка Англии
FA_CUP_SF = {
    "date": "2026-05-02 19:00",  # Ориентировочная дата полуфинала
    "home": "Челси",  # Может быть жеребьёвка
    "away": "TBD",
    "tournament": "Кубок Англии"
}


def parse_fixture_date(date_str):
    """Преобразование строки с датой в объект datetime"""
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except ValueError as e:
        logger.error(f"Ошибка парсинга даты {date_str}: {e}")
        return None


def clear_finished_matches():
    """Удаляем завершённые матчи (старше сегодняшнего дня)"""
    session = db.Session()
    try:
        now = datetime.datetime.now()
        deleted = session.query(Match).filter(Match.match_date < now).delete()
        session.commit()
        if deleted > 0:
            logger.info(f"🗑 Удалено {deleted} завершённых матчей")
    except Exception as e:
        logger.error(f"Ошибка при удалении завершённых матчей: {e}")
        session.rollback()
    finally:
        session.close()


def load_fixtures(clear_finished=True):
    """Загрузка предстоящих матчей в базу данных"""
    if clear_finished:
        clear_finished_matches()

    session = db.Session()
    added_count = 0
    skipped_count = 0

    for fixture in UPCOMING_FIXTURES:
        match_date = parse_fixture_date(fixture["date"])
        if not match_date:
            skipped_count += 1
            continue

        # Проверяем, не существует ли уже такой матч
        existing = session.query(Match).filter_by(
            tournament=fixture["tournament"],
            home_team=fixture["home"],
            away_team=fixture["away"],
            match_date=match_date
        ).first()

        if existing:
            logger.info(f"⏭ Матч уже существует: {fixture['home']} vs {fixture['away']}")
            skipped_count += 1
            continue

        # Создаем новый матч
        match = Match(
            tournament=fixture["tournament"],
            home_team=fixture["home"],
            away_team=fixture["away"],
            match_date=match_date,
            is_notified=False,
            match_status="scheduled"
        )
        session.add(match)
        added_count += 1
        date_formatted = match_date.strftime("%d.%m.%Y %H:%M")
        logger.info(f"✅ Добавлен матч: {fixture['home']} vs {fixture['away']} ({date_formatted} МСК)")

    try:
        session.commit()
        logger.info(f"📊 Итог: добавлено {added_count} предстоящих матчей, пропущено {skipped_count}")
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении: {e}")
        session.rollback()
    finally:
        session.close()

    return added_count


def show_upcoming_matches(limit=10):
    """Показать предстоящие матчи для проверки"""
    session = db.Session()
    now = datetime.datetime.now()

    matches = session.query(Match).filter(
        Match.match_date > now,
        Match.match_status == 'scheduled'
    ).order_by(Match.match_date).limit(limit).all()

    if not matches:
        logger.info("📭 Нет предстоящих матчей")
    else:
        logger.info(f"📅 Предстоящие матчи (Московское время):")
        for i, match in enumerate(matches, 1):
            date_str = match.match_date.strftime("%d.%m.%Y %H:%M")
            logger.info(f"  {i}. {match.home_team} vs {match.away_team} - {date_str} МСК ({match.tournament})")

    session.close()
    return matches


if __name__ == "__main__":
    logger.info("🚀 Загрузка предстоящих матчей Челси (АПЛ + Кубок Англии + Лига чемпионов)...")
    logger.info("🕒 Все даты указаны в московском времени (UTC+3) на основе championat.com")

    # Загружаем только предстоящие матчи
    count = load_fixtures(clear_finished=True)

    # Показываем предстоящие матчи
    show_upcoming_matches()

    logger.info("✨ Загрузка завершена!")