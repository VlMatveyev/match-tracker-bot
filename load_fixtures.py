import datetime
import logging
from database import db, Match

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Полное расписание матчей Челси в АПЛ 2025/26
# Время указано МОСКОВСКОЕ (UTC+3) на основе данных championat.com и sport-express.ru
PREMIER_LEAGUE_FIXTURES = [
    # Август 2025
    {"date": "2025-08-17 16:00", "home": "Челси", "away": "Кристал Пэлас", "tournament": "АПЛ"},  # 1-й тур
    {"date": "2025-08-22 22:00", "home": "Вест Хэм", "away": "Челси", "tournament": "АПЛ"},  # 2-й тур
    {"date": "2025-08-30 14:30", "home": "Челси", "away": "Фулхэм", "tournament": "АПЛ"},  # 3-й тур

    # Сентябрь 2025
    {"date": "2025-09-13 22:00", "home": "Брентфорд", "away": "Челси", "tournament": "АПЛ"},  # 4-й тур
    {"date": "2025-09-20 19:30", "home": "Манчестер Юнайтед", "away": "Челси", "tournament": "АПЛ"},  # 5-й тур
    {"date": "2025-09-27 17:00", "home": "Челси", "away": "Брайтон", "tournament": "АПЛ"},  # 6-й тур

    # Октябрь 2025
    {"date": "2025-10-04 19:30", "home": "Челси", "away": "Ливерпуль", "tournament": "АПЛ"},  # 7-й тур
    {"date": "2025-10-18 14:30", "home": "Ноттингем Форест", "away": "Челси", "tournament": "АПЛ"},  # 8-й тур
    {"date": "2025-10-25 17:00", "home": "Челси", "away": "Сандерленд", "tournament": "АПЛ"},  # 9-й тур

    # Ноябрь 2025
    {"date": "2025-11-01 20:30", "home": "Тоттенхэм", "away": "Челси", "tournament": "АПЛ"},  # 10-й тур
    {"date": "2025-11-08 23:00", "home": "Челси", "away": "Вулверхэмптон", "tournament": "АПЛ"},  # 11-й тур
    {"date": "2025-11-22 15:30", "home": "Бернли", "away": "Челси", "tournament": "АПЛ"},  # 12-й тур
    {"date": "2025-11-30 19:30", "home": "Челси", "away": "Арсенал", "tournament": "АПЛ"},  # 13-й тур

    # Декабрь 2025
    {"date": "2025-12-03 23:15", "home": "Лидс Юнайтед", "away": "Челси", "tournament": "АПЛ"},  # 14-й тур
    {"date": "2025-12-06 18:00", "home": "Борнмут", "away": "Челси", "tournament": "АПЛ"},  # 15-й тур
    {"date": "2025-12-13 18:00", "home": "Челси", "away": "Эвертон", "tournament": "АПЛ"},  # 16-й тур
    {"date": "2025-12-20 15:30", "home": "Ньюкасл", "away": "Челси", "tournament": "АПЛ"},  # 17-й тур
    {"date": "2025-12-27 20:30", "home": "Челси", "away": "Астон Вилла", "tournament": "АПЛ"},  # 18-й тур
    {"date": "2025-12-30 22:30", "home": "Челси", "away": "Борнмут", "tournament": "АПЛ"},  # 19-й тур

    # Январь 2026
    {"date": "2026-01-04 20:30", "home": "Манчестер Сити", "away": "Челси", "tournament": "АПЛ"},  # 20-й тур
    {"date": "2026-01-07 22:30", "home": "Фулхэм", "away": "Челси", "tournament": "АПЛ"},  # 21-й тур
    {"date": "2026-01-17 18:00", "home": "Челси", "away": "Брентфорд", "tournament": "АПЛ"},  # 22-й тур
    {"date": "2026-01-25 17:00", "home": "Кристал Пэлас", "away": "Челси", "tournament": "АПЛ"},  # 23-й тур
    {"date": "2026-01-31 20:30", "home": "Челси", "away": "Вест Хэм", "tournament": "АПЛ"},  # 24-й тур

    # Февраль 2026
    {"date": "2026-02-07 18:00", "home": "Вулверхэмптон", "away": "Челси", "tournament": "АПЛ"},  # 25-й тур
    {"date": "2026-02-10 22:30", "home": "Челси", "away": "Лидс Юнайтед", "tournament": "АПЛ"},  # 26-й тур
    {"date": "2026-02-21 18:00", "home": "Челси", "away": "Бернли", "tournament": "АПЛ"},  # 27-й тур
    # 28 февраля матча НЕТ! Правильная дата матча с Арсеналом - 1 марта

    # Март 2026 (ОФИЦИАЛЬНЫЕ ДАТЫ)
    {"date": "2026-03-01 19:30", "home": "Арсенал", "away": "Челси", "tournament": "АПЛ"},  # 28-й тур ✓
    {"date": "2026-03-04 22:30", "home": "Астон Вилла", "away": "Челси", "tournament": "АПЛ"},  # 29-й тур ✓
    {"date": "2026-03-14 20:30", "home": "Челси", "away": "Ньюкасл", "tournament": "АПЛ"},  # 30-й тур ✓
    {"date": "2026-03-21 20:30", "home": "Эвертон", "away": "Челси", "tournament": "АПЛ"},  # 31-й тур ✓

    # Апрель 2026
    {"date": "2026-04-11 17:00", "home": "Челси", "away": "Манчестер Сити", "tournament": "АПЛ"},  # 32-й тур
    {"date": "2026-04-18 17:00", "home": "Челси", "away": "Манчестер Юнайтед", "tournament": "АПЛ"},  # 33-й тур
    {"date": "2026-04-25 17:00", "home": "Брайтон", "away": "Челси", "tournament": "АПЛ"},  # 34-й тур

    # Май 2026
    {"date": "2026-05-02 17:00", "home": "Челси", "away": "Ноттингем Форест", "tournament": "АПЛ"},  # 35-й тур
    {"date": "2026-05-09 17:00", "home": "Ливерпуль", "away": "Челси", "tournament": "АПЛ"},  # 36-й тур
    {"date": "2026-05-17 17:00", "home": "Челси", "away": "Тоттенхэм", "tournament": "АПЛ"},  # 37-й тур
    {"date": "2026-05-24 18:00", "home": "Сандерленд", "away": "Челси", "tournament": "АПЛ"},  # 38-й тур
]


def parse_fixture_date(date_str):
    """Преобразование строки с датой в объект datetime"""
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except ValueError as e:
        logger.error(f"Ошибка парсинга даты {date_str}: {e}")
        return None


def clear_existing_matches():
    """Очистка существующих матчей"""
    session = db.Session()
    try:
        count = session.query(Match).delete()
        session.commit()
        logger.info(f"🗑 Удалено {count} существующих матчей")
    except Exception as e:
        logger.error(f"Ошибка при очистке: {e}")
        session.rollback()
    finally:
        session.close()


def load_fixtures(clear_first=True):
    """Загрузка всех матчей в базу данных"""
    if clear_first:
        clear_existing_matches()

    session = db.Session()
    added_count = 0
    skipped_count = 0

    for fixture in PREMIER_LEAGUE_FIXTURES:
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
        logger.info(f"📊 Итог: добавлено {added_count} матчей, пропущено {skipped_count}")
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении: {e}")
        session.rollback()
    finally:
        session.close()

    return added_count


def show_upcoming_matches(limit=5):
    """Показать ближайшие матчи для проверки"""
    session = db.Session()
    now = datetime.datetime.now()

    matches = session.query(Match).filter(
        Match.match_date > now,
        Match.match_status == 'scheduled'
    ).order_by(Match.match_date).limit(limit).all()

    if not matches:
        logger.info("📭 Нет предстоящих матчей")
    else:
        logger.info(f"📅 Ближайшие {len(matches)} матчей (Московское время):")
        for i, match in enumerate(matches, 1):
            date_str = match.match_date.strftime("%d.%m.%Y %H:%M")
            logger.info(f"  {i}. {match.home_team} vs {match.away_team} - {date_str} МСК")

    session.close()
    return matches


if __name__ == "__main__":
    logger.info("🚀 Начинаем загрузку расписания АПЛ 2025/26...")
    logger.info("🕒 Все даты указаны в московском времени (UTC+3) на основе championat.com")

    # Загружаем матчи (очищаем старые)
    count = load_fixtures(clear_first=True)

    # Показываем ближайшие матчи для проверки
    show_upcoming_matches(5)

    logger.info("✨ Загрузка завершена!")