#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис бота
Основная логика для управления ботом и играми
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ..domain.entities import Game, Player
from ..domain.value_objects import GameId, ChatId, UserId, Username, GamePhase, Team
from ..domain.repositories import (
    GameRepository, PlayerRepository, UserRepository, 
    GameEventRepository, ChatSettingsRepository
)
from .services import GameService, UserService, VotingService
from .factories import GameFactory, PlayerFactory, ValueObjectFactory

logger = logging.getLogger(__name__)


class BotService:
    """Основной сервис бота"""
    
    def __init__(
        self,
        game_repo: GameRepository,
        player_repo: PlayerRepository,
        user_repo: UserRepository,
        event_repo: GameEventRepository,
        chat_settings_repo: ChatSettingsRepository
    ):
        self.game_repo = game_repo
        self.player_repo = player_repo
        self.user_repo = user_repo
        self.event_repo = event_repo
        self.chat_settings_repo = chat_settings_repo
        
        # Инициализируем сервисы
        self.game_service = GameService(game_repo, player_repo, event_repo)
        self.user_service = UserService(user_repo)
        self.voting_service = VotingService()
        
        # Инициализируем фабрики
        self.game_factory = GameFactory(None)  # RoleAssignmentService будет добавлен позже
        self.player_factory = PlayerFactory()
        
        # Кэш активных игр
        self.active_games: Dict[int, Game] = {}
        
        # Авторизованные чаты
        self.authorized_chats: set = set()
    
    async def initialize(self) -> None:
        """Инициализация сервиса"""
        try:
            # Загружаем активные игры из БД
            active_games = await self.game_repo.get_all_active()
            for game in active_games:
                self.active_games[game.chat_id.value] = game
            
            logger.info(f"✅ Загружено {len(active_games)} активных игр")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации BotService: {e}")
    
    def is_chat_authorized(self, chat_id: ChatId, thread_id: Optional[int] = None) -> bool:
        """Проверяет, авторизован ли чат"""
        return (chat_id.value, thread_id) in self.authorized_chats
    
    def authorize_chat(self, chat_id: ChatId, thread_id: Optional[int] = None) -> None:
        """Авторизует чат"""
        self.authorized_chats.add((chat_id.value, thread_id))
    
    def deauthorize_chat(self, chat_id: ChatId, thread_id: Optional[int] = None) -> None:
        """Деавторизует чат"""
        self.authorized_chats.discard((chat_id.value, thread_id))
    
    async def get_or_create_game(self, chat_id: ChatId, thread_id: Optional[int] = None, is_test_mode: bool = False) -> Game:
        """Получает или создает игру"""
        # Проверяем кэш
        if chat_id.value in self.active_games:
            return self.active_games[chat_id.value]
        
        # Проверяем БД
        game = await self.game_service.get_active_game(chat_id, thread_id)
        if game:
            self.active_games[chat_id.value] = game
            return game
        
        # Создаем новую игру
        game = self.game_factory.create_game(chat_id, thread_id, is_test_mode)
        await self.game_repo.save(game)
        self.active_games[chat_id.value] = game
        
        return game
    
    async def join_game(self, chat_id: ChatId, user_id: UserId, username: str, first_name: str = None, thread_id: Optional[int] = None) -> Dict[str, Any]:
        """Присоединяет игрока к игре"""
        # Проверяем авторизацию
        if not self.is_chat_authorized(chat_id, thread_id):
            return {"success": False, "message": "❌ Этот чат не авторизован для игры."}
        
        # Получаем или создаем пользователя
        await self.user_service.get_or_create_user(user_id, username, first_name)
        
        # Получаем или создаем игру
        game = await self.get_or_create_game(chat_id, thread_id)
        
        # Проверяем, можно ли присоединиться
        if game.phase != GamePhase.WAITING:
            return {"success": False, "message": "❌ Игра уже началась. Дождитесь следующей игры."}
        
        # Добавляем игрока
        username_obj = ValueObjectFactory.create_username(username)
        success = await self.game_service.add_player_to_game(game, user_id, username_obj)
        
        if success:
            player_count = len(game.players)
            min_players = 3 if game.is_test_mode else 6
            
            if player_count >= min_players:
                message = (
                    f"✅ {first_name or username} присоединился к игре!\n\n"
                    f"👥 Игроков: {player_count}/12\n"
                    f"🎮 Игра готова к началу! Администратор может использовать /start_game"
                )
            else:
                message = (
                    f"✅ {first_name or username} присоединился к игре!\n\n"
                    f"👥 Игроков: {player_count}/12\n"
                    f"⏳ Нужно еще {min_players - player_count} игроков для начала"
                )
            
            return {"success": True, "message": message, "game": game}
        else:
            if user_id.value in game.players:
                return {"success": False, "message": "❌ Вы уже в игре!"}
            else:
                return {"success": False, "message": "❌ Не удалось присоединиться к игре."}
    
    async def leave_game(self, chat_id: ChatId, user_id: UserId) -> Dict[str, Any]:
        """Игрок покидает игру"""
        game = self.active_games.get(chat_id.value)
        if not game:
            return {"success": False, "message": "❌ В этом чате нет активной игры."}
        
        success = await self.game_service.remove_player_from_game(game, user_id)
        
        if success:
            player_count = len(game.players)
            return {
                "success": True, 
                "message": f"👋 Игрок покинул игру.\n\n👥 Игроков: {player_count}/12",
                "game": game
            }
        else:
            return {"success": False, "message": "❌ Вы не можете покинуть игру сейчас."}
    
    async def start_game(self, chat_id: ChatId) -> Dict[str, Any]:
        """Начинает игру"""
        game = self.active_games.get(chat_id.value)
        if not game:
            return {"success": False, "message": "❌ В этом чате нет активной игры."}
        
        if not game.can_start_game():
            player_count = len(game.players)
            min_players = 3 if game.is_test_mode else 6
            return {
                "success": False, 
                "message": f"❌ Недостаточно игроков для начала игры.\n👥 Игроков: {player_count}/12\n⏳ Нужно минимум {min_players} игроков"
            }
        
        # Начинаем игру
        success = await self.game_service.start_game(game)
        if success:
            return {
                "success": True, 
                "message": f"🌲 **ИГРА НАЧАЛАСЬ!** 🌲\n\n👥 Игроков: {len(game.players)}\n🎭 Роли распределены!\n🌙 Начинается первая ночь...",
                "game": game
            }
        else:
            return {"success": False, "message": "❌ Не удалось начать игру."}
    
    async def end_game(self, chat_id: ChatId, reason: str = "Администратор завершил игру") -> Dict[str, Any]:
        """Завершает игру"""
        game = self.active_games.get(chat_id.value)
        if not game:
            return {"success": False, "message": "❌ В этом чате нет активной игры."}
        
        # Определяем победителя
        winner = game.check_game_end()
        
        # Завершаем игру
        await self.game_service.end_game(game, winner, reason)
        
        # Удаляем из кэша
        if chat_id.value in self.active_games:
            del self.active_games[chat_id.value]
        
        winner_text = f"🏆 Победили: {winner.value if winner else 'Ничья'}"
        
        return {
            "success": True,
            "message": f"🌲 **ИГРА ЗАВЕРШЕНА** 🌲\n\n📋 Причина: {reason}\n{winner_text}\n👥 Участников: {len(game.players)}\n🎮 Раундов: {game.current_round}",
            "game": game,
            "winner": winner
        }
    
    async def get_game_status(self, chat_id: ChatId) -> Dict[str, Any]:
        """Получает статус игры"""
        game = self.active_games.get(chat_id.value)
        if not game:
            return {"success": False, "message": "❌ В этом чате нет активной игры."}
        
        status_text = self._format_game_status(game)
        return {"success": True, "message": status_text, "game": game}
    
    def _format_game_status(self, game: Game) -> str:
        """Форматирует статус игры"""
        if game.phase == GamePhase.WAITING:
            player_count = len(game.players)
            min_players = 3 if game.is_test_mode else 6
            
            status = (
                f"🌲 **Статус игры** 🌲\n\n"
                f"📋 Фаза: Ожидание игроков\n"
                f"👥 Игроков: {player_count}/12\n"
                f"⏳ Нужно еще {min_players - player_count} игроков для начала\n\n"
                f"**Участники:**\n"
            )
            
            for player in game.players.values():
                status += f"• {player.username.value}\n"
            
            return status
        
        elif game.phase == GamePhase.NIGHT:
            alive_count = len(game.get_alive_players())
            return (
                f"🌲 **Статус игры** 🌲\n\n"
                f"📋 Фаза: Ночь (Раунд {game.current_round})\n"
                f"👥 Живых игроков: {alive_count}\n"
                f"🌙 Ночные действия в процессе..."
            )
        
        elif game.phase == GamePhase.DAY:
            alive_count = len(game.get_alive_players())
            return (
                f"🌲 **Статус игры** 🌲\n\n"
                f"📋 Фаза: День (Раунд {game.current_round})\n"
                f"👥 Живых игроков: {alive_count}\n"
                f"☀️ Обсуждение событий ночи..."
            )
        
        elif game.phase == GamePhase.VOTING:
            alive_count = len(game.get_alive_players())
            return (
                f"🌲 **Статус игры** 🌲\n\n"
                f"📋 Фаза: Голосование (Раунд {game.current_round})\n"
                f"👥 Живых игроков: {alive_count}\n"
                f"🗳️ Голосование за изгнание..."
            )
        
        else:
            return "🌲 Игра завершена 🌲"
    
    async def vote(self, chat_id: ChatId, voter_id: UserId, target_id: Optional[UserId] = None) -> Dict[str, Any]:
        """Обрабатывает голосование"""
        game = self.active_games.get(chat_id.value)
        if not game:
            return {"success": False, "message": "❌ В этом чате нет активной игры."}
        
        if game.phase != GamePhase.VOTING:
            return {"success": False, "message": "❌ Сейчас не время голосования."}
        
        success = game.vote(voter_id, target_id)
        if success:
            await self.game_repo.save(game)
            return {"success": True, "message": "✅ Голос засчитан", "game": game}
        else:
            return {"success": False, "message": "❌ Неверный голос"}
    
    async def process_voting(self, chat_id: ChatId) -> Dict[str, Any]:
        """Обрабатывает результаты голосования"""
        game = self.active_games.get(chat_id.value)
        if not game:
            return {"success": False, "message": "❌ В этом чате нет активной игры."}
        
        exiled_player = self.voting_service.process_voting(game)
        await self.game_repo.save(game)
        
        if exiled_player:
            return {
                "success": True, 
                "message": f"🗳️ Изгнан: {exiled_player.username.value}",
                "exiled_player": exiled_player,
                "game": game
            }
        else:
            return {
                "success": True, 
                "message": "🗳️ Никто не изгнан",
                "game": game
            }
    
    async def get_user_display_name(self, user_id: UserId, username: str = None, first_name: str = None) -> str:
        """Получает отображаемое имя пользователя"""
        return await self.user_service.get_display_name(user_id, username, first_name)
    
    async def get_user_balance(self, user_id: UserId) -> int:
        """Получает баланс пользователя"""
        return await self.user_service.get_balance(user_id)
    
    async def update_user_balance(self, user_id: UserId, amount: int) -> None:
        """Обновляет баланс пользователя"""
        await self.user_service.update_balance(user_id, amount)
