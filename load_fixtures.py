import datetime
import logging
from database import db, Match

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# ПРЕДСТОЯЩИЕ МАТЧИ ЧЕЛСИ (исправленное расписание)
# ============================================
CHELSEA_FIXTURES = [
    # АПЛ - Март 2026
    {"date": "2026-03-21 20:30", "home": "Эвертон", "away": "Челси", "tournament": "АПЛ", "team": "Челси"},

    # Кубок Англии - Апрель 2026
    {"date": "2026-04-04 19:15", "home": "Челси", "away": "Порт Вейл", "tournament": "Кубок Англии", "team": "Челси"},

    # АПЛ - Апрель 2026
    {"date": "2026-04-12 18:30", "home": "Челси", "away": "Манчестер Сити", "tournament": "АПЛ", "team": "Челси"},
    {"date": "2026-04-18 22:00", "home": "Челси", "away": "Манчестер Юнайтед", "tournament": "АПЛ", "team": "Челси"},
    {"date": "2026-04-26 18:30", "home": "Брайтон", "away": "Челси", "tournament": "АПЛ", "team": "Челси"},

    # АПЛ - Май 2026
    {"date": "2026-05-02 17:00", "home": "Челси", "away": "Ноттингем Форест", "tournament": "АПЛ", "team": "Челси"},
    {"date": "2026-05-09 17:00", "home": "Ливерпуль", "away": "Челси", "tournament": "АПЛ", "team": "Челси"},
    {"date": "2026-05-17 17:00", "home": "Челси", "away": "Тоттенхэм", "tournament": "АПЛ", "team": "Челси"},
    {"date": "2026-05-24 18:00", "home": "Сандерленд", "away": "Челси", "tournament": "АПЛ", "team": "Челси"},
]

# ============================================
# ПРЕДСТОЯЩИЕ МАТЧИ МАНЧЕСТЕР ЮНАЙТЕД (исправленное расписание)
# ============================================
MANCHESTER_UNITED_FIXTURES = [
    # Март 2026
    {"date": "2026-03-20 23:00", "home": "Борнмут", "away": "Манчестер Юнайтед", "tournament": "АПЛ", "team": "Манчестер Юнайтед"},

    # Апрель 2026
    {"date": "2026-04-13 22:00", "home": "Манчестер Юнайтед", "away": "Лидс", "tournament": "АПЛ", "team": "Манчестер Юнайтед"},
    {"date": "2026-04-18 22:00", "home": "Челси", "away": "Манчестер Юнайтед", "tournament": "АПЛ", "team": "Манчестер Юнайтед"},
    {"date": "2026-04-27 22:00", "home": "Манчестер Юнайтед", "away": "Брентфорд", "tournament": "АПЛ", "team": "Манчестер Юнайтед"},

    # Май 2026
    {"date": "2026-05-02 17:00", "home": "Манчестер Юнайтед", "away": "Ливерпуль", "tournament": "АПЛ", "team": "Манчестер Юнайтед"},
    {"date": "2026-05-09 17:00", "home": "Сандерленд", "away": "Манчестер Юнайтед", "tournament": "АПЛ", "team": "Манчестер Юнайтед"},
    {"date": "2026-05-17 17:00", "home": "Манчестер Юнайтед", "away": "Ноттингем Форест", "tournament": "АПЛ", "team": "Манчестер Юнайтед"},
    {"date": "2026-05-24 18:00", "home": "Брайтон", "away": "Манчестер Юнайтед", "tournament": "АПЛ", "team": "Манчестер Юнайтед"},
]

# ============================================
# ВСЕ МАТЧИ ВМЕСТЕ
# ============================================
ALL_FIXTURES = CHELSEA_FIXTURES + MANCHESTER_UNITED_FIXTURES


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

    for fixture in ALL_FIXTURES:
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


def show_upcoming_matches(limit=10, team=None):
    """Показать предстоящие матчи для проверки (опционально для конкретной команды)"""
    session = db.Session()
    now = datetime.datetime.now()

    query = session.query(Match).filter(
        Match.match_date > now,
        Match.match_status == 'scheduled'
    )

    if team:
        query = query.filter(
            (Match.home_team == team) | (Match.away_team == team)
        )

    matches = query.order_by(Match.match_date).limit(limit).all()

    if not matches:
        logger.info("📭 Нет предстоящих матчей")
    else:
        team_str = f" для {team}" if team else ""
        logger.info(f"📅 Предстоящие матчи{team_str} (Московское время):")
        for i, match in enumerate(matches, 1):
            date_str = match.match_date.strftime("%d.%m.%Y %H:%M")
            logger.info(f"  {i}. {match.home_team} vs {match.away_team} - {date_str} МСК ({match.tournament})")

    session.close()
    return matches


def get_matches_by_team(team_name):
    """Получить все матчи для конкретной команды"""
    session = db.Session()
    now = datetime.datetime.now()

    matches = session.query(Match).filter(
        ((Match.home_team == team_name) | (Match.away_team == team_name)) &
        (Match.match_date > now) &
        (Match.match_status == 'scheduled')
    ).order_by(Match.match_date).all()

    session.close()
    return matches


if __name__ == "__main__":
    logger.info("🚀 Загрузка предстоящих матчей Челси и Манчестер Юнайтед...")
    logger.info("🕒 Все даты указаны в московском времени (UTC+3) на основе championat.com")

    # Загружаем все матчи
    count = load_fixtures(clear_finished=True)

    # Показываем статистику по командам
    chelsea_matches = get_matches_by_team("Челси")
    united_matches = get_matches_by_team("Манчестер Юнайтед")

    logger.info(f"📊 Челси: {len(chelsea_matches)} предстоящих матчей")
    logger.info(f"📊 Манчестер Юнайтед: {len(united_matches)} предстоящих матчей")

    # Показываем ближайшие матчи
    show_upcoming_matches(5)

    logger.info("✨ Загрузка завершена!")