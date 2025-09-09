#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с базой данных в ForestMafia Bot
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime

from game_logic import Game, Player, Role, Team
from database_psycopg2 import (
    init_db, close_db, create_tables,
    save_game_to_db, save_player_to_db, update_game_phase, finish_game_in_db,
    get_team_stats, get_top_players, get_player_detailed_stats
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер базы данных для бота"""
    
    def __init__(self):
        self.db = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Инициализирует базу данных"""
        try:
            self.db = init_db()
            create_tables()
            logger.info("✅ База данных инициализирована успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            self.db = None
    
    def is_available(self) -> bool:
        """Проверяет, доступна ли база данных"""
        return self.db is not None
    
    def save_game_state(self, game: Game):
        """Сохраняет состояние игры в базу данных"""
        if not self.is_available():
            return
        
        try:
            # Сохраняем игру
            game_id = save_game_to_db(
                chat_id=game.chat_id,
                thread_id=game.thread_id,
                phase=game.phase.value,
                round_number=game.current_round,
                is_test_mode=game.is_test_mode
            )
            
            # Сохраняем игроков
            for player in game.players.values():
                save_player_to_db(
                    game_id=game_id,
                    user_id=player.user_id,
                    username=player.username,
                    role=player.role.value,
                    team=player.team.value,
                    is_alive=player.is_alive,
                    supplies=player.supplies,
                    max_supplies=player.max_supplies,
                    is_fox_stolen=player.is_fox_stolen,
                    stolen_supplies=player.stolen_supplies,
                    is_beaver_protected=player.is_beaver_protected,
                    consecutive_nights_survived=player.consecutive_nights_survived,
                    last_action_round=player.last_action_round
                )
            
            logger.info(f"✅ Состояние игры сохранено в БД (ID: {game_id})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения состояния игры: {e}")
    
    def update_game_phase(self, game: Game):
        """Обновляет фазу игры в базе данных"""
        if not self.is_available():
            return
        
        try:
            update_game_phase(
                chat_id=game.chat_id,
                thread_id=game.thread_id,
                phase=game.phase.value,
                round_number=game.current_round
            )
            logger.info(f"✅ Фаза игры обновлена: {game.phase.value}")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления фазы игры: {e}")
    
    def finish_game(self, game: Game, winner_team: Optional[Team]):
        """Завершает игру в базе данных"""
        if not self.is_available():
            return
        
        try:
            winner = winner_team.value if winner_team else None
            finish_game_in_db(
                chat_id=game.chat_id,
                thread_id=game.thread_id,
                winner_team=winner,
                final_round=game.current_round
            )
            logger.info(f"✅ Игра завершена в БД (победитель: {winner})")
        except Exception as e:
            logger.error(f"❌ Ошибка завершения игры в БД: {e}")
    
    def get_player_stats(self, user_id: int) -> Dict:
        """Получает статистику игрока"""
        if not self.is_available():
            return {}
        
        try:
            stats = get_player_detailed_stats(user_id)
            return stats if stats else {}
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики игрока {user_id}: {e}")
            return {}
    
    def get_top_players(self, limit: int = 10) -> List[Dict]:
        """Получает топ игроков"""
        if not self.is_available():
            return []
        
        try:
            return get_top_players(limit)
        except Exception as e:
            logger.error(f"❌ Ошибка получения топа игроков: {e}")
            return []
    
    def get_team_stats(self) -> Dict:
        """Получает статистику команд"""
        if not self.is_available():
            return {}
        
        try:
            return get_team_stats()
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики команд: {e}")
            return {}
    
    def close(self):
        """Закрывает соединение с базой данных"""
        if self.db:
            try:
                close_db()
                logger.info("✅ Соединение с базой данных закрыто")
            except Exception as e:
                logger.error(f"❌ Ошибка закрытия БД: {e}")
            finally:
                self.db = None


class GameStateManager:
    """Менеджер состояния игр"""
    
    def __init__(self, database_manager: DatabaseManager):
        self.db_manager = database_manager
        self.games: Dict[int, Game] = {}
        self.player_games: Dict[int, int] = {}  # user_id -> chat_id
    
    def get_or_create_game(self, chat_id: int, thread_id: Optional[int] = None, is_test_mode: bool = True) -> Game:
        """Получает или создает игру"""
        if chat_id not in self.games:
            self.games[chat_id] = Game(chat_id, thread_id, is_test_mode)
            logger.info(f"✅ Создана новая игра для чата {chat_id}")
        
        return self.games[chat_id]
    
    def get_game(self, chat_id: int) -> Optional[Game]:
        """Получает игру по ID чата"""
        return self.games.get(chat_id)
    
    def remove_game(self, chat_id: int):
        """Удаляет игру"""
        if chat_id in self.games:
            # Удаляем игроков из индекса
            game = self.games[chat_id]
            for player_id in game.players.keys():
                if player_id in self.player_games:
                    del self.player_games[player_id]
            
            del self.games[chat_id]
            logger.info(f"✅ Игра для чата {chat_id} удалена")
    
    def add_player_to_game(self, user_id: int, chat_id: int):
        """Добавляет игрока в индекс игр"""
        self.player_games[user_id] = chat_id
    
    def remove_player_from_game(self, user_id: int):
        """Удаляет игрока из индекса игр"""
        if user_id in self.player_games:
            del self.player_games[user_id]
    
    def get_player_game(self, user_id: int) -> Optional[Game]:
        """Получает игру игрока"""
        chat_id = self.player_games.get(user_id)
        if chat_id:
            return self.games.get(chat_id)
        return None
    
    def save_all_games(self):
        """Сохраняет все активные игры"""
        for game in self.games.values():
            self.db_manager.save_game_state(game)
    
    def load_active_games(self):
        """Загружает активные игры из базы данных"""
        # TODO: Реализовать загрузку игр из БД
        logger.info("📋 Загрузка активных игр из БД (пока не реализовано)")
    
    def cleanup_finished_games(self):
        """Очищает завершенные игры"""
        finished_chats = []
        for chat_id, game in self.games.items():
            if game.phase == GamePhase.GAME_OVER:
                finished_chats.append(chat_id)
        
        for chat_id in finished_chats:
            self.remove_game(chat_id)
        
        if finished_chats:
            logger.info(f"🧹 Очищено {len(finished_chats)} завершенных игр")
