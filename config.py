#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Конфигурация бота Лес и волки
Централизованное управление настройками приложения
"""

import os
from typing import Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    """Конфигурация базы данных"""
    url: str = os.environ.get('DATABASE_URL', 'sqlite:///forest_mafia.db')


@dataclass(frozen=True)
class GameConfig:
    """Конфигурация игровых параметров"""
    min_players_normal: int = 3  # Изменено с 6 на 3
    min_players_test: int = 3
    max_players: int = 12
    
    # Длительность фаз (в секундах)
    night_duration: int = 60
    day_duration: int = 300  # 5 минут на обсуждение
    voting_duration: int = 120  # 2 минуты на голосование
    
    # Распределение ролей (проценты)
    role_distribution: Dict[str, float] = None
    
    def __post_init__(self):
        if self.role_distribution is None:
            object.__setattr__(self, 'role_distribution', {
                'wolves': 0.25,    # 25% - Волки
                'fox': 0.15,       # 15% - Лиса
                'hares': 0.35,     # 35% - Зайцы
                'mole': 0.15,      # 15% - Крот
                'beaver': 0.10     # 10% - Бобёр
            })


@dataclass(frozen=True)
class BotConfig:
    """Конфигурация бота"""
    token: str
    test_mode: bool = False
    
    def __post_init__(self):
        if not self.token or self.token == 'your_bot_token_here':
            raise ValueError(
                "BOT_TOKEN не установлен! Создайте файл .env и добавьте BOT_TOKEN=your_actual_token"
            )


class Config:
    """Главный класс конфигурации"""
    
    def __init__(self):
        self._bot_token = self._get_bot_token()
        self._database = DatabaseConfig()
        self._game = GameConfig()
        self._bot = BotConfig(token=self._bot_token)
    
    @staticmethod
    def _get_bot_token() -> str:
        """Получает токен бота из переменных окружения"""
        token = os.environ.get('BOT_TOKEN', '').strip("'\"")
        return token
    
    @property
    def bot_token(self) -> str:
        """Токен бота"""
        return self._bot.token
    
    @property
    def database_url(self) -> str:
        """URL базы данных"""
        return self._database.url
    
    @property
    def min_players(self) -> int:
        """Минимальное количество игроков в зависимости от режима"""
        if self._bot.test_mode:
            return self._game.min_players_test
        return self._game.min_players_normal
    
    @property
    def max_players(self) -> int:
        """Максимальное количество игроков"""
        return self._game.max_players
    
    @property
    def night_duration(self) -> int:
        """Длительность ночной фазы в секундах"""
        return self._game.night_duration
    
    @property
    def day_duration(self) -> int:
        """Длительность дневной фазы в секундах"""
        return self._game.day_duration
    
    @property
    def voting_duration(self) -> int:
        """Длительность фазы голосования в секундах"""
        return self._game.voting_duration
    
    @property
    def role_distribution(self) -> Dict[str, float]:
        """Распределение ролей"""
        return self._game.role_distribution.copy()
    
    @property
    def is_test_mode(self) -> bool:
        """Включен ли тестовый режим"""
        return self._bot.test_mode
    
    def get_game_settings(self) -> Dict[str, Any]:
        """Возвращает все игровые настройки"""
        return {
            'min_players': self.min_players,
            'max_players': self.max_players,
            'night_duration': self.night_duration,
            'day_duration': self.day_duration,
            'voting_duration': self.voting_duration,
            'role_distribution': self.role_distribution,
            'test_mode': self.is_test_mode
        }


# Глобальный экземпляр конфигурации
config = Config()

# Обратная совместимость (для существующего кода)
BOT_TOKEN = config.bot_token
DATABASE_URL = config.database_url
MIN_PLAYERS = config.min_players
MAX_PLAYERS = config.max_players
TEST_MODE = config.is_test_mode
TEST_MIN_PLAYERS = config._game.min_players_test
ROLE_DISTRIBUTION = config.role_distribution
NIGHT_PHASE_DURATION = config.night_duration
DAY_PHASE_DURATION = config.day_duration
VOTING_DURATION = config.voting_duration