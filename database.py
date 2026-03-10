import sqlite3
import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()


class Match(Base):
    __tablename__ = 'matches'

    id = Column(Integer, primary_key=True)
    tournament = Column(String)
    home_team = Column(String)
    away_team = Column(String)
    match_date = Column(DateTime)
    is_notified = Column(Boolean, default=False)
    match_status = Column(String, default='scheduled')

    def __repr__(self):
        return f"<Match(id={self.id}, {self.home_team} vs {self.away_team})>"


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String, nullable=True)
    subscribed_at = Column(DateTime, default=datetime.datetime.now)

    def __repr__(self):
        return f"<Chat(chat_id={self.chat_id}, user_id={self.user_id})>"


class Database:
    def __init__(self, db_name='chelsea_matches.db'):
        self.engine = create_engine(f'sqlite:///{db_name}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_next_match(self):
        """Получить следующий матч"""
        session = self.Session()
        try:
            now = datetime.now()
            match = session.query(Match) \
                .filter(Match.match_date > now) \
                .order_by(Match.match_date) \
                .first()
            return match
        finally:
            session.close()

    def get_today_matches(self):
        """Получить матчи на сегодня"""
        session = self.Session()
        try:
            now = datetime.now()
            today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
            today_end = datetime(now.year, now.month, now.day, 23, 59, 59)

            matches = session.query(Match) \
                .filter(Match.match_date.between(today_start, today_end)) \
                .order_by(Match.match_date) \
                .all()
            return matches
        finally:
            session.close()

    def get_upcoming_matches(self, days=30, limit=5):
        """Получить ближайшие матчи (по умолчанию следующие 5)"""
        session = self.Session()
        try:
            now = datetime.now()
            from datetime import timedelta
            future = now + timedelta(days=days)

            matches = session.query(Match) \
                .filter(Match.match_date.between(now, future)) \
                .order_by(Match.match_date) \
                .limit(limit) \
                .all()
            return matches
        finally:
            session.close()

    def add_match(self, tournament, home_team, away_team, match_date):
        """Добавить матч в базу"""
        session = self.Session()
        try:
            # Проверяем, есть ли уже такой матч
            existing = session.query(Match) \
                .filter_by(
                tournament=tournament,
                home_team=home_team,
                away_team=away_team,
                match_date=match_date
            ).first()

            if not existing:
                match = Match(
                    tournament=tournament,
                    home_team=home_team,
                    away_team=away_team,
                    match_date=match_date
                )
                session.add(match)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Ошибка при добавлении матча: {e}")
            return False
        finally:
            session.close()

    def clear_matches(self):
        """Очистить таблицу матчей"""
        session = self.Session()
        try:
            session.query(Match).delete()
            session.commit()
            print("✅ Таблица матчей очищена")
        except Exception as e:
            session.rollback()
            print(f"❌ Ошибка при очистке: {e}")
        finally:
            session.close()


# Создаем глобальный экземпляр базы данных
db = Database()