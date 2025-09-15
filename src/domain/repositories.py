#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Интерфейсы репозиториев
Определяют контракты для работы с данными
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime

from .entities import Game, Player, GameStatistics
from .value_objects import GameId, ChatId, UserId


class GameRepository(ABC):
    """Репозиторий для работы с играми"""
    
    @abstractmethod
    async def save(self, game: Game) -> None:
        """Сохраняет игру"""
        pass
    
    @abstractmethod
    async def get_by_id(self, game_id: GameId) -> Optional[Game]:
        """Получает игру по ID"""
        pass
    
    @abstractmethod
    async def get_by_chat(self, chat_id: ChatId, thread_id: Optional[int] = None) -> Optional[Game]:
        """Получает активную игру в чате"""
        pass
    
    @abstractmethod
    async def get_all_active(self) -> List[Game]:
        """Получает все активные игры"""
        pass
    
    @abstractmethod
    async def delete(self, game_id: GameId) -> None:
        """Удаляет игру"""
        pass
    
    @abstractmethod
    async def update_phase(self, game_id: GameId, phase: str) -> None:
        """Обновляет фазу игры"""
        pass


class PlayerRepository(ABC):
    """Репозиторий для работы с игроками"""
    
    @abstractmethod
    async def save(self, player: Player, game_id: GameId) -> None:
        """Сохраняет игрока"""
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: UserId, game_id: GameId) -> Optional[Player]:
        """Получает игрока по ID пользователя в игре"""
        pass
    
    @abstractmethod
    async def get_all_in_game(self, game_id: GameId) -> List[Player]:
        """Получает всех игроков в игре"""
        pass
    
    @abstractmethod
    async def update_stats(self, user_id: UserId, stats: Dict[str, Any]) -> None:
        """Обновляет статистику игрока"""
        pass


class UserRepository(ABC):
    """Репозиторий для работы с пользователями"""
    
    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> Optional[Dict[str, Any]]:
        """Получает пользователя по ID"""
        pass
    
    @abstractmethod
    async def create(self, user_id: UserId, username: str, first_name: str = None) -> None:
        """Создает нового пользователя"""
        pass
    
    @abstractmethod
    async def update_balance(self, user_id: UserId, amount: int) -> None:
        """Обновляет баланс пользователя"""
        pass
    
    @abstractmethod
    async def get_balance(self, user_id: UserId) -> int:
        """Получает баланс пользователя"""
        pass
    
    @abstractmethod
    async def get_nickname(self, user_id: UserId) -> Optional[str]:
        """Получает никнейм пользователя"""
        pass
    
    @abstractmethod
    async def set_nickname(self, user_id: UserId, nickname: str) -> None:
        """Устанавливает никнейм пользователя"""
        pass


class GameEventRepository(ABC):
    """Репозиторий для работы с событиями игры"""
    
    @abstractmethod
    async def log_event(self, game_id: GameId, event_type: str, data: Dict[str, Any]) -> None:
        """Логирует событие игры"""
        pass
    
    @abstractmethod
    async def get_game_events(self, game_id: GameId) -> List[Dict[str, Any]]:
        """Получает события игры"""
        pass
    
    @abstractmethod
    async def log_action(self, user_id: UserId, game_id: GameId, action_type: str, target_id: Optional[UserId] = None) -> None:
        """Логирует действие игрока"""
        pass


class ChatSettingsRepository(ABC):
    """Репозиторий для работы с настройками чата"""
    
    @abstractmethod
    async def get_settings(self, chat_id: ChatId) -> Dict[str, Any]:
        """Получает настройки чата"""
        pass
    
    @abstractmethod
    async def update_settings(self, chat_id: ChatId, settings: Dict[str, Any]) -> None:
        """Обновляет настройки чата"""
        pass
    
    @abstractmethod
    async def reset_settings(self, chat_id: ChatId) -> None:
        """Сбрасывает настройки чата"""
        pass


class StatisticsRepository(ABC):
    """Репозиторий для работы со статистикой"""
    
    @abstractmethod
    async def get_player_stats(self, user_id: UserId) -> Dict[str, Any]:
        """Получает статистику игрока"""
        pass
    
    @abstractmethod
    async def get_team_stats(self, team: str) -> Dict[str, Any]:
        """Получает статистику команды"""
        pass
    
    @abstractmethod
    async def get_top_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает топ игроков"""
        pass
    
    @abstractmethod
    async def update_player_stats(self, user_id: UserId, stats: Dict[str, Any]) -> None:
        """Обновляет статистику игрока"""
        pass
