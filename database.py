import sqlite3
import datetime
import logging
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
    # Добавляем поле для фильтрации по команде
    team = Column(String, nullable=True)  # Челси или Манчестер Юнайтед

    def __repr__(self):
        return f"<Match(id={self.id}, {self.home_team} vs {self.away_team})>"


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String, nullable=True)
    subscribed_at = Column(DateTime, default=datetime.datetime.now)
    # Добавляем выбранную команду для пользователя
    selected_team = Column(String, nullable=True)  # Челси или Манчестер Юнайтед

    def __repr__(self):
        return f"<Chat(chat_id={self.chat_id}, user_id={self.user_id})>"


class Database:
    def __init__(self, db_name='chelsea_matches.db'):
        self.engine = create_engine(f'sqlite:///{db_name}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_next_match(self, team=None):
        """Получить следующий матч для указанной команды"""
        session = self.Session()
        try:
            now = datetime.datetime.now()
            query = session.query(Match).filter(Match.match_date > now)

            if team:
                query = query.filter((Match.home_team == team) | (Match.away_team == team))

            match = query.order_by(Match.match_date).first()
            return match
        finally:
            session.close()

    def get_today_matches(self, team=None):
        """Получить матчи на сегодня для указанной команды"""
        session = self.Session()
        try:
            now = datetime.datetime.now()
            today_start = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
            today_end = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)

            query = session.query(Match).filter(Match.match_date.between(today_start, today_end))

            if team:
                query = query.filter((Match.home_team == team) | (Match.away_team == team))

            matches = query.order_by(Match.match_date).all()
            return matches
        finally:
            session.close()

    def get_upcoming_matches(self, days=30, limit=5, team=None):
        """Получить ближайшие матчи для указанной команды"""
        session = self.Session()
        try:
            now = datetime.datetime.now()
            from datetime import timedelta
            future = now + timedelta(days=days)

            query = session.query(Match).filter(Match.match_date.between(now, future))

            if team:
                query = query.filter((Match.home_team == team) | (Match.away_team == team))

            matches = query.order_by(Match.match_date).limit(limit).all()
            return matches
        finally:
            session.close()

    def add_match(self, tournament, home_team, away_team, match_date, team=None):
        """Добавить матч в базу"""
        session = self.Session()
        try:
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
                    match_date=match_date,
                    team=team
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

    def get_user_selected_team(self, chat_id):
        """Получить выбранную команду для пользователя"""
        session = self.Session()
        try:
            chat = session.query(Chat).filter(Chat.chat_id == chat_id).first()
            return chat.selected_team if chat else None
        finally:
            session.close()

    def set_user_selected_team(self, chat_id, user_id, username, team):
        """Установить выбранную команду для пользователя"""
        session = self.Session()
        try:
            chat = session.query(Chat).filter(Chat.chat_id == chat_id).first()
            if chat:
                chat.selected_team = team
            else:
                chat = Chat(
                    chat_id=chat_id,
                    user_id=user_id,
                    username=username,
                    selected_team=team,
                    subscribed_at=datetime.datetime.now()
                )
                session.add(chat)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Ошибка при установке команды: {e}")
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