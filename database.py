#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid

# База данных
Base = declarative_base()

class Game(Base):
    """Модель игры"""
    __tablename__ = 'games'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(Integer, nullable=False, index=True)
    thread_id = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default='waiting')  # waiting, active, finished
    phase = Column(String, nullable=False, default='registration')  # registration, night, day, voting, finished
    round_number = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    winner_team = Column(String, nullable=True)  # predators, herbivores
    settings = Column(JSON, default=dict)  # Настройки игры
    
    # Связи
    players = relationship("Player", back_populates="game", cascade="all, delete-orphan", foreign_keys="Player.game_id")
    game_events = relationship("GameEvent", back_populates="game", cascade="all, delete-orphan", foreign_keys="GameEvent.game_id")

class Player(Base):
    """Модель игрока"""
    __tablename__ = 'players'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    game_id = Column(String, ForeignKey('games.id'), nullable=False)
    role = Column(String, nullable=True)  # wolf, fox, hare, mole, beaver
    team = Column(String, nullable=True)  # predators, herbivores
    is_alive = Column(Boolean, default=True)
    is_online = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    died_at = Column(DateTime, nullable=True)
    death_reason = Column(String, nullable=True)  # killed, voted_out, left
    
    # Связи
    game = relationship("Game", back_populates="players", foreign_keys=[game_id])
    actions = relationship("PlayerAction", back_populates="player", cascade="all, delete-orphan", foreign_keys="PlayerAction.player_id")
    votes = relationship("Vote", back_populates="voter", cascade="all, delete-orphan", foreign_keys="Vote.voter_id")
    received_votes = relationship("Vote", back_populates="target", foreign_keys="Vote.target_id")

class GameEvent(Base):
    """Модель событий игры"""
    __tablename__ = 'game_events'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id = Column(String, ForeignKey('games.id'), nullable=False)
    event_type = Column(String, nullable=False)  # phase_change, player_joined, player_left, player_died, vote, action
    event_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    game = relationship("Game", back_populates="game_events", foreign_keys=[game_id])

class PlayerAction(Base):
    """Модель действий игроков"""
    __tablename__ = 'player_actions'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id = Column(String, ForeignKey('players.id'), nullable=False)
    game_id = Column(String, ForeignKey('games.id'), nullable=False)
    action_type = Column(String, nullable=False)  # kill, steal, investigate, protect, vote
    target_id = Column(String, nullable=True)  # ID целевого игрока
    action_data = Column(JSON, default=dict)
    round_number = Column(Integer, nullable=False)
    phase = Column(String, nullable=False)  # night, day, voting
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    player = relationship("Player", back_populates="actions", foreign_keys=[player_id])

class Vote(Base):
    """Модель голосований"""
    __tablename__ = 'votes'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id = Column(String, ForeignKey('games.id'), nullable=False)
    voter_id = Column(String, ForeignKey('players.id'), nullable=False)
    target_id = Column(String, ForeignKey('players.id'), nullable=True)
    round_number = Column(Integer, nullable=False)
    phase = Column(String, nullable=False)  # voting, lynch
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    voter = relationship("Player", back_populates="votes", foreign_keys=[voter_id])
    target = relationship("Player", back_populates="received_votes", foreign_keys=[target_id])

class PlayerStats(Base):
    """Модель статистики игроков"""
    __tablename__ = 'player_stats'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String, nullable=True)
    total_games = Column(Integer, default=0)
    games_won = Column(Integer, default=0)
    games_lost = Column(Integer, default=0)
    times_wolf = Column(Integer, default=0)
    times_fox = Column(Integer, default=0)
    times_hare = Column(Integer, default=0)
    times_mole = Column(Integer, default=0)
    times_beaver = Column(Integer, default=0)
    kills_made = Column(Integer, default=0)
    votes_received = Column(Integer, default=0)
    last_played = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BotSettings(Base):
    """Модель настроек бота"""
    __tablename__ = 'bot_settings'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(Integer, nullable=False, index=True)
    thread_id = Column(Integer, nullable=True)
    setting_key = Column(String, nullable=False)
    setting_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            # Используем SQLite по умолчанию
            database_url = os.environ.get('DATABASE_URL', 'sqlite:///forest_mafia.db')
        
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Создаем таблицы
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Получить сессию базы данных"""
        return self.SessionLocal()
    
    def close(self):
        """Закрыть соединение с базой данных"""
        self.engine.dispose()

# Глобальный экземпляр менеджера БД
db_manager: Optional[DatabaseManager] = None

def init_database(database_url: Optional[str] = None) -> DatabaseManager:
    """Инициализировать базу данных"""
    global db_manager
    db_manager = DatabaseManager(database_url)
    return db_manager

def get_db() -> Session:
    """Получить сессию базы данных (для dependency injection)"""
    if db_manager is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_database() сначала.")
    
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

def get_db_session() -> Session:
    """Получить сессию базы данных напрямую"""
    if db_manager is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_database() сначала.")
    
    return db_manager.get_session()
