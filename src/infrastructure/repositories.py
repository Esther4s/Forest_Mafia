#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Реализации репозиториев
Конкретные реализации интерфейсов репозиториев для работы с БД
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..domain.entities import Game, Player, GameStatistics
from ..domain.value_objects import GameId, ChatId, UserId, Username, GamePhase, Team, Role
from ..domain.repositories import (
    GameRepository, PlayerRepository, UserRepository,
    GameEventRepository, ChatSettingsRepository, StatisticsRepository
)

logger = logging.getLogger(__name__)


class GameRepositoryImpl(GameRepository):
    """Реализация репозитория игр"""
    
    def __init__(self):
        self.games: Dict[str, Game] = {}
    
    async def save(self, game: Game) -> None:
        """Сохраняет игру"""
        try:
            # В реальной реализации здесь будет сохранение в БД
            self.games[game.game_id.value] = game
            logger.debug(f"Игра {game.game_id.value} сохранена")
        except Exception as e:
            logger.error(f"Ошибка сохранения игры {game.game_id.value}: {e}")
            raise
    
    async def get_by_id(self, game_id: GameId) -> Optional[Game]:
        """Получает игру по ID"""
        try:
            return self.games.get(game_id.value)
        except Exception as e:
            logger.error(f"Ошибка получения игры {game_id.value}: {e}")
            return None
    
    async def get_by_chat(self, chat_id: ChatId, thread_id: Optional[int] = None) -> Optional[Game]:
        """Получает активную игру в чате"""
        try:
            for game in self.games.values():
                if (game.chat_id.value == chat_id.value and 
                    game.thread_id == thread_id and 
                    game.phase != GamePhase.GAME_OVER):
                    return game
            return None
        except Exception as e:
            logger.error(f"Ошибка получения игры для чата {chat_id.value}: {e}")
            return None
    
    async def get_all_active(self) -> List[Game]:
        """Получает все активные игры"""
        try:
            return [
                game for game in self.games.values()
                if game.phase != GamePhase.GAME_OVER
            ]
        except Exception as e:
            logger.error(f"Ошибка получения активных игр: {e}")
            return []
    
    async def delete(self, game_id: GameId) -> None:
        """Удаляет игру"""
        try:
            if game_id.value in self.games:
                del self.games[game_id.value]
                logger.debug(f"Игра {game_id.value} удалена")
        except Exception as e:
            logger.error(f"Ошибка удаления игры {game_id.value}: {e}")
            raise
    
    async def update_phase(self, game_id: GameId, phase: str) -> None:
        """Обновляет фазу игры"""
        try:
            game = self.games.get(game_id.value)
            if game:
                game.phase = GamePhase(phase)
                await self.save(game)
        except Exception as e:
            logger.error(f"Ошибка обновления фазы игры {game_id.value}: {e}")
            raise


class PlayerRepositoryImpl(PlayerRepository):
    """Реализация репозитория игроков"""
    
    def __init__(self):
        self.players: Dict[str, Dict[str, Player]] = {}  # game_id -> {user_id: Player}
    
    async def save(self, player: Player, game_id: GameId) -> None:
        """Сохраняет игрока"""
        try:
            if game_id.value not in self.players:
                self.players[game_id.value] = {}
            self.players[game_id.value][str(player.user_id.value)] = player
            logger.debug(f"Игрок {player.user_id.value} сохранен в игре {game_id.value}")
        except Exception as e:
            logger.error(f"Ошибка сохранения игрока {player.user_id.value}: {e}")
            raise
    
    async def get_by_user_id(self, user_id: UserId, game_id: GameId) -> Optional[Player]:
        """Получает игрока по ID пользователя в игре"""
        try:
            game_players = self.players.get(game_id.value, {})
            return game_players.get(str(user_id.value))
        except Exception as e:
            logger.error(f"Ошибка получения игрока {user_id.value}: {e}")
            return None
    
    async def get_all_in_game(self, game_id: GameId) -> List[Player]:
        """Получает всех игроков в игре"""
        try:
            game_players = self.players.get(game_id.value, {})
            return list(game_players.values())
        except Exception as e:
            logger.error(f"Ошибка получения игроков игры {game_id.value}: {e}")
            return []
    
    async def update_stats(self, user_id: UserId, stats: Dict[str, Any]) -> None:
        """Обновляет статистику игрока"""
        try:
            # В реальной реализации здесь будет обновление в БД
            logger.debug(f"Статистика игрока {user_id.value} обновлена: {stats}")
        except Exception as e:
            logger.error(f"Ошибка обновления статистики игрока {user_id.value}: {e}")
            raise


class UserRepositoryImpl(UserRepository):
    """Реализация репозитория пользователей"""
    
    def __init__(self):
        self.users: Dict[int, Dict[str, Any]] = {}
    
    async def get_by_id(self, user_id: UserId) -> Optional[Dict[str, Any]]:
        """Получает пользователя по ID"""
        try:
            return self.users.get(user_id.value)
        except Exception as e:
            logger.error(f"Ошибка получения пользователя {user_id.value}: {e}")
            return None
    
    async def create(self, user_id: UserId, username: str, first_name: str = None) -> None:
        """Создает нового пользователя"""
        try:
            self.users[user_id.value] = {
                'user_id': user_id.value,
                'username': username,
                'first_name': first_name,
                'balance': 0,
                'nickname': None,
                'created_at': datetime.now().isoformat()
            }
            logger.debug(f"Пользователь {user_id.value} создан")
        except Exception as e:
            logger.error(f"Ошибка создания пользователя {user_id.value}: {e}")
            raise
    
    async def update_balance(self, user_id: UserId, amount: int) -> None:
        """Обновляет баланс пользователя"""
        try:
            if user_id.value in self.users:
                self.users[user_id.value]['balance'] += amount
                logger.debug(f"Баланс пользователя {user_id.value} обновлен на {amount}")
        except Exception as e:
            logger.error(f"Ошибка обновления баланса пользователя {user_id.value}: {e}")
            raise
    
    async def get_balance(self, user_id: UserId) -> int:
        """Получает баланс пользователя"""
        try:
            user = self.users.get(user_id.value)
            return user.get('balance', 0) if user else 0
        except Exception as e:
            logger.error(f"Ошибка получения баланса пользователя {user_id.value}: {e}")
            return 0
    
    async def get_nickname(self, user_id: UserId) -> Optional[str]:
        """Получает никнейм пользователя"""
        try:
            user = self.users.get(user_id.value)
            return user.get('nickname') if user else None
        except Exception as e:
            logger.error(f"Ошибка получения никнейма пользователя {user_id.value}: {e}")
            return None
    
    async def set_nickname(self, user_id: UserId, nickname: str) -> None:
        """Устанавливает никнейм пользователя"""
        try:
            if user_id.value in self.users:
                self.users[user_id.value]['nickname'] = nickname
                logger.debug(f"Никнейм пользователя {user_id.value} установлен: {nickname}")
        except Exception as e:
            logger.error(f"Ошибка установки никнейма пользователя {user_id.value}: {e}")
            raise


class GameEventRepositoryImpl(GameEventRepository):
    """Реализация репозитория событий игры"""
    
    def __init__(self):
        self.events: Dict[str, List[Dict[str, Any]]] = {}  # game_id -> [events]
    
    async def log_event(self, game_id: GameId, event_type: str, data: Dict[str, Any]) -> None:
        """Логирует событие игры"""
        try:
            if game_id.value not in self.events:
                self.events[game_id.value] = []
            
            event = {
                'game_id': game_id.value,
                'event_type': event_type,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
            
            self.events[game_id.value].append(event)
            logger.debug(f"Событие {event_type} залогировано для игры {game_id.value}")
        except Exception as e:
            logger.error(f"Ошибка логирования события {event_type}: {e}")
            raise
    
    async def get_game_events(self, game_id: GameId) -> List[Dict[str, Any]]:
        """Получает события игры"""
        try:
            return self.events.get(game_id.value, [])
        except Exception as e:
            logger.error(f"Ошибка получения событий игры {game_id.value}: {e}")
            return []
    
    async def log_action(self, user_id: UserId, game_id: GameId, action_type: str, target_id: Optional[UserId] = None) -> None:
        """Логирует действие игрока"""
        try:
            data = {
                'user_id': user_id.value,
                'action_type': action_type
            }
            if target_id:
                data['target_id'] = target_id.value
            
            await self.log_event(game_id, 'player_action', data)
        except Exception as e:
            logger.error(f"Ошибка логирования действия игрока {user_id.value}: {e}")
            raise


class ChatSettingsRepositoryImpl(ChatSettingsRepository):
    """Реализация репозитория настроек чата"""
    
    def __init__(self):
        self.settings: Dict[int, Dict[str, Any]] = {}  # chat_id -> settings
    
    async def get_settings(self, chat_id: ChatId) -> Dict[str, Any]:
        """Получает настройки чата"""
        try:
            return self.settings.get(chat_id.value, {})
        except Exception as e:
            logger.error(f"Ошибка получения настроек чата {chat_id.value}: {e}")
            return {}
    
    async def update_settings(self, chat_id: ChatId, settings: Dict[str, Any]) -> None:
        """Обновляет настройки чата"""
        try:
            self.settings[chat_id.value] = settings
            logger.debug(f"Настройки чата {chat_id.value} обновлены")
        except Exception as e:
            logger.error(f"Ошибка обновления настроек чата {chat_id.value}: {e}")
            raise
    
    async def reset_settings(self, chat_id: ChatId) -> None:
        """Сбрасывает настройки чата"""
        try:
            if chat_id.value in self.settings:
                del self.settings[chat_id.value]
                logger.debug(f"Настройки чата {chat_id.value} сброшены")
        except Exception as e:
            logger.error(f"Ошибка сброса настроек чата {chat_id.value}: {e}")
            raise


class StatisticsRepositoryImpl(StatisticsRepository):
    """Реализация репозитория статистики"""
    
    def __init__(self):
        self.player_stats: Dict[int, Dict[str, Any]] = {}  # user_id -> stats
        self.team_stats: Dict[str, Dict[str, Any]] = {}  # team -> stats
    
    async def get_player_stats(self, user_id: UserId) -> Dict[str, Any]:
        """Получает статистику игрока"""
        try:
            return self.player_stats.get(user_id.value, {})
        except Exception as e:
            logger.error(f"Ошибка получения статистики игрока {user_id.value}: {e}")
            return {}
    
    async def get_team_stats(self, team: str) -> Dict[str, Any]:
        """Получает статистику команды"""
        try:
            return self.team_stats.get(team, {})
        except Exception as e:
            logger.error(f"Ошибка получения статистики команды {team}: {e}")
            return {}
    
    async def get_top_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает топ игроков"""
        try:
            # В реальной реализации здесь будет запрос к БД
            return []
        except Exception as e:
            logger.error(f"Ошибка получения топ игроков: {e}")
            return []
    
    async def update_player_stats(self, user_id: UserId, stats: Dict[str, Any]) -> None:
        """Обновляет статистику игрока"""
        try:
            if user_id.value not in self.player_stats:
                self.player_stats[user_id.value] = {}
            
            self.player_stats[user_id.value].update(stats)
            logger.debug(f"Статистика игрока {user_id.value} обновлена")
        except Exception as e:
            logger.error(f"Ошибка обновления статистики игрока {user_id.value}: {e}")
            raise
