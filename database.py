import datetime
import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

Base = declarative_base()


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String, nullable=True)
    subscribed_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Chat(chat_id={self.chat_id}, user_id={self.user_id})>"

class Match(Base):
    __tablename__ = 'matches'

    id = Column(Integer, primary_key=True)
    tournament = Column(String)  # Название турнира
    home_team = Column(String)  # Хозяева
    away_team = Column(String)  # Гости
    match_date = Column(DateTime)  # Дата и время матча
    is_notified = Column(Boolean, default=False)  # Было ли отправлено уведомление
    match_status = Column(String, default='scheduled')  # scheduled, finished, postponed


class Database:
    def __init__(self, db_path='sqlite:///chelsea_matches.db'):
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def parse_date(self, date_value):
        """Безопасный парсинг даты из разных форматов"""
        if isinstance(date_value, datetime.datetime):
            return date_value

        if isinstance(date_value, str):
            try:
                # Пробуем стандартный ISO формат
                return datetime.datetime.fromisoformat(date_value)
            except ValueError:
                try:
                    # Пробуем без миллисекунд
                    if '.' in date_value:
                        date_value = date_value.split('.')[0]
                    return datetime.datetime.fromisoformat(date_value)
                except ValueError:
                    # Пробуем формат SQLite
                    return datetime.datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S.%f')
        return None

    def add_match(self, tournament, home_team, away_team, match_date):
        """Добавление матча в БД"""
        session = self.Session()
        # Убеждаемся, что дата в правильном формате
        if isinstance(match_date, str):
            match_date = self.parse_date(match_date)

        match = Match(
            tournament=tournament,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date
        )
        session.add(match)
        session.commit()
        session.close()

    def get_next_match(self):
        """Получение следующего матча"""
        session = self.Session()
        now = datetime.datetime.now()
        try:
            # Сначала проверим количество записей
            count = session.query(Match).count()
            logger.info(f"Всего записей в БД: {count}")

            # Найдем следующий матч
            match = session.query(Match).filter(
                Match.match_date > now,
                Match.match_status == 'scheduled'
            ).order_by(Match.match_date).first()

            # Если нашли матч, выводим отладочную информацию
            if match:
                logger.info(f"✅ Найден матч: {match.home_team} vs {match.away_team}, дата: {match.match_date}")
            else:
                logger.warning(f"❌ Матчи не найдены. Текущее время: {now}")

                # Для отладки покажем все матчи
                all_matches = session.query(Match).all()
                logger.info(f"Всего матчей в БД: {len(all_matches)}")
                for m in all_matches:
                    logger.info(f"  - {m.home_team} vs {m.away_team}, дата: {m.match_date}, статус: {m.match_status}")

        except Exception as e:
            logger.error(f"Ошибка в get_next_match: {e}")
            match = None
        finally:
            session.close()
        return match

    def get_today_matches(self):
        """Матчи на сегодня"""
        session = self.Session()
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + datetime.timedelta(days=1)

        try:
            matches = session.query(Match).filter(
                Match.match_date >= today_start,
                Match.match_date < today_end
            ).all()

            logger.info(f"Найдено матчей на сегодня: {len(matches)}")

        except Exception as e:
            logger.error(f"Ошибка в get_today_matches: {e}")
            matches = []
        finally:
            session.close()
        return matches

    def get_upcoming_matches(self, days=7):
        """Ближайшие матчи на N дней"""
        session = self.Session()
        now = datetime.datetime.now()
        future = now + datetime.timedelta(days=days)

        try:
            matches = session.query(Match).filter(
                Match.match_date >= now,
                Match.match_date <= future,
                Match.match_status == 'scheduled'
            ).order_by(Match.match_date).all()

            logger.info(f"Найдено ближайших матчей: {len(matches)}")

        except Exception as e:
            logger.error(f"Ошибка в get_upcoming_matches: {e}")
            matches = []
        finally:
            session.close()
        return matches

    def mark_notified(self, match_id):
        """Отметить матч как уведомленный"""
        session = self.Session()
        try:
            match = session.query(Match).filter_by(id=match_id).first()
            if match:
                match.is_notified = True
                session.commit()
                logger.info(f"Матч {match_id} отмечен как уведомленный")
        except Exception as e:
            logger.error(f"Ошибка в mark_notified: {e}")
        finally:
            session.close()


# Создаем экземпляр БД (ЭТО ВАЖНО - ОН ДОЛЖЕН БЫТЬ ЗДЕСЬ)
db = Database()