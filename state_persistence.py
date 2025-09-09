#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для сохранения состояния бота в базе данных
Предотвращает потерю данных при перезапуске
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from database_psycopg2 import (
    execute_query, fetch_one, fetch_query,
    init_db, close_db
)

logger = logging.getLogger(__name__)


class StatePersistence:
    """Класс для сохранения состояния бота"""
    
    def __init__(self):
        self.logger = logger
        self.db = None
        self._init_database()
    
    def _init_database(self):
        """Инициализирует подключение к БД"""
        try:
            self.db = init_db()
            self._create_state_tables()
            self.logger.info("✅ StatePersistence: База данных инициализирована")
        except Exception as e:
            self.logger.error(f"❌ StatePersistence: Ошибка инициализации БД: {e}")
            self.db = None
    
    def _create_state_tables(self):
        """Создает таблицы для сохранения состояния"""
        try:
            # Таблица для сохранения состояния бота
            create_bot_state_table = """
                CREATE TABLE IF NOT EXISTS bot_state (
                    id SERIAL PRIMARY KEY,
                    state_type VARCHAR(50) NOT NULL,
                    state_data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(state_type)
                )
            """
            
            # Таблица для сохранения активных игр
            create_active_games_table = """
                CREATE TABLE IF NOT EXISTS active_games_state (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    thread_id BIGINT,
                    game_data JSONB NOT NULL,
                    players_data JSONB NOT NULL,
                    night_actions_data JSONB,
                    night_interface_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chat_id, thread_id)
                )
            """
            
            # Таблица для сохранения маппинга игроков
            create_player_games_table = """
                CREATE TABLE IF NOT EXISTS player_games_state (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    thread_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id)
                )
            """
            
            # Таблица для сохранения авторизованных чатов
            create_authorized_chats_table = """
                CREATE TABLE IF NOT EXISTS authorized_chats_state (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    thread_id BIGINT,
                    chat_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chat_id, thread_id)
                )
            """
            
            # Создаем таблицы
            execute_query(create_bot_state_table)
            execute_query(create_active_games_table)
            execute_query(create_player_games_table)
            execute_query(create_authorized_chats_table)
            
            # Создаем индексы
            execute_query("CREATE INDEX IF NOT EXISTS idx_active_games_chat_id ON active_games_state(chat_id)")
            execute_query("CREATE INDEX IF NOT EXISTS idx_player_games_user_id ON player_games_state(user_id)")
            execute_query("CREATE INDEX IF NOT EXISTS idx_authorized_chats_chat_id ON authorized_chats_state(chat_id)")
            
            self.logger.info("✅ StatePersistence: Таблицы состояния созданы")
            
        except Exception as e:
            self.logger.error(f"❌ StatePersistence: Ошибка создания таблиц: {e}")
    
    def save_bot_state(self, state_type: str, state_data: Dict[str, Any]) -> bool:
        """
        Сохраняет состояние бота
        
        Args:
            state_type: Тип состояния (games, player_games, authorized_chats, etc.)
            state_data: Данные состояния
            
        Returns:
            bool: True если сохранение успешно
        """
        try:
            if not self.db:
                self.logger.error("❌ StatePersistence: База данных недоступна")
                return False
            
            # Конвертируем данные в JSON
            json_data = json.dumps(state_data, ensure_ascii=False, default=str)
            
            # Сохраняем или обновляем состояние
            query = """
                INSERT INTO bot_state (state_type, state_data, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (state_type)
                DO UPDATE SET 
                    state_data = EXCLUDED.state_data,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            affected = execute_query(query, (state_type, json_data))
            
            if affected > 0:
                self.logger.info(f"✅ StatePersistence: Состояние {state_type} сохранено")
                return True
            else:
                self.logger.error(f"❌ StatePersistence: Не удалось сохранить состояние {state_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ StatePersistence: Ошибка сохранения состояния {state_type}: {e}")
            return False
    
    def load_bot_state(self, state_type: str) -> Optional[Dict[str, Any]]:
        """
        Загружает состояние бота
        
        Args:
            state_type: Тип состояния
            
        Returns:
            Dict или None: Данные состояния
        """
        try:
            if not self.db:
                self.logger.error("❌ StatePersistence: База данных недоступна")
                return None
            
            query = "SELECT state_data FROM bot_state WHERE state_type = %s"
            result = fetch_one(query, (state_type,))
            
            if result:
                state_data = json.loads(result['state_data'])
                self.logger.info(f"✅ StatePersistence: Состояние {state_type} загружено")
                return state_data
            else:
                self.logger.info(f"ℹ️ StatePersistence: Состояние {state_type} не найдено")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ StatePersistence: Ошибка загрузки состояния {state_type}: {e}")
            return None
    
    def save_active_games(self, games: Dict[int, Any], player_games: Dict[int, int], 
                         night_actions: Dict[int, Any], night_interfaces: Dict[int, Any]) -> bool:
        """
        Сохраняет активные игры
        
        Args:
            games: Словарь игр
            player_games: Маппинг игроков
            night_actions: Ночные действия
            night_interfaces: Ночные интерфейсы
            
        Returns:
            bool: True если сохранение успешно
        """
        try:
            if not self.db:
                return False
            
            # Очищаем старые данные
            execute_query("DELETE FROM active_games_state")
            execute_query("DELETE FROM player_games_state")
            
            # Сохраняем каждую игру
            for chat_id, game in games.items():
                if hasattr(game, 'thread_id'):
                    thread_id = game.thread_id
                else:
                    thread_id = None
                
                # Подготавливаем данные игры
                game_data = {
                    'chat_id': game.chat_id,
                    'thread_id': thread_id,
                    'phase': game.phase.value if hasattr(game, 'phase') else 'waiting',
                    'current_round': game.current_round if hasattr(game, 'current_round') else 1,
                    'status': getattr(game, 'status', 'active'),
                    'db_game_id': getattr(game, 'db_game_id', None),
                    'phase_end_time': game.phase_end_time.isoformat() if hasattr(game, 'phase_end_time') and game.phase_end_time else None,
                    'game_stats': getattr(game, 'game_stats', {}).__dict__ if hasattr(game, 'game_stats') else {}
                }
                
                # Подготавливаем данные игроков
                players_data = {}
                for user_id, player in game.players.items():
                    players_data[user_id] = {
                        'user_id': player.user_id,
                        'username': player.username,
                        'first_name': player.first_name,
                        'last_name': player.last_name,
                        'role': player.role.value if hasattr(player, 'role') else None,
                        'team': player.team.value if hasattr(player, 'team') else None,
                        'is_alive': player.is_alive,
                        'supplies': player.supplies,
                        'max_supplies': player.max_supplies,
                        'is_fox_stolen': getattr(player, 'is_fox_stolen', False),
                        'is_beaver_protected': getattr(player, 'is_beaver_protected', False),
                        'consecutive_nights_survived': getattr(player, 'consecutive_nights_survived', 0),
                        'last_action_round': getattr(player, 'last_action_round', 0)
                    }
                
                # Сохраняем игру
                query = """
                    INSERT INTO active_games_state 
                    (chat_id, thread_id, game_data, players_data, night_actions_data, night_interface_data)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                night_actions_data = json.dumps(night_actions.get(chat_id, {}), default=str)
                night_interface_data = json.dumps(night_interfaces.get(chat_id, {}), default=str)
                
                execute_query(query, (
                    chat_id, thread_id,
                    json.dumps(game_data, default=str),
                    json.dumps(players_data, default=str),
                    night_actions_data,
                    night_interface_data
                ))
            
            # Сохраняем маппинг игроков
            for user_id, game_chat_id in player_games.items():
                query = """
                    INSERT INTO player_games_state (user_id, chat_id, thread_id)
                    VALUES (%s, %s, %s)
                """
                
                # Получаем thread_id из игры
                thread_id = None
                if game_chat_id in games:
                    thread_id = getattr(games[game_chat_id], 'thread_id', None)
                
                execute_query(query, (user_id, game_chat_id, thread_id))
            
            self.logger.info(f"✅ StatePersistence: Сохранено {len(games)} активных игр")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ StatePersistence: Ошибка сохранения активных игр: {e}")
            return False
    
    def load_active_games(self) -> Dict[str, Any]:
        """
        Загружает активные игры
        
        Returns:
            Dict: Данные активных игр
        """
        try:
            if not self.db:
                return {}
            
            # Загружаем игры
            query = """
                SELECT chat_id, thread_id, game_data, players_data, 
                       night_actions_data, night_interface_data
                FROM active_games_state
            """
            
            games_data = fetch_query(query)
            
            # Загружаем маппинг игроков
            player_games_query = """
                SELECT user_id, chat_id, thread_id
                FROM player_games_state
            """
            
            player_games_data = fetch_query(player_games_query)
            
            # Загружаем авторизованные чаты
            authorized_chats_query = """
                SELECT chat_id, thread_id, chat_name
                FROM authorized_chats_state
            """
            
            authorized_chats_data = fetch_query(authorized_chats_query)
            
            result = {
                'games': games_data,
                'player_games': player_games_data,
                'authorized_chats': authorized_chats_data
            }
            
            self.logger.info(f"✅ StatePersistence: Загружено {len(games_data)} активных игр")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ StatePersistence: Ошибка загрузки активных игр: {e}")
            return {}
    
    def save_authorized_chats(self, authorized_chats: set) -> bool:
        """
        Сохраняет авторизованные чаты
        
        Args:
            authorized_chats: Множество авторизованных чатов
            
        Returns:
            bool: True если сохранение успешно
        """
        try:
            if not self.db:
                return False
            
            # Очищаем старые данные
            execute_query("DELETE FROM authorized_chats_state")
            
            # Сохраняем каждый чат
            for chat_id, thread_id in authorized_chats:
                query = """
                    INSERT INTO authorized_chats_state (chat_id, thread_id, chat_name)
                    VALUES (%s, %s, %s)
                """
                
                execute_query(query, (chat_id, thread_id, f"Chat {chat_id}"))
            
            self.logger.info(f"✅ StatePersistence: Сохранено {len(authorized_chats)} авторизованных чатов")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ StatePersistence: Ошибка сохранения авторизованных чатов: {e}")
            return False
    
    def load_authorized_chats(self) -> set:
        """
        Загружает авторизованные чаты
        
        Returns:
            set: Множество авторизованных чатов
        """
        try:
            if not self.db:
                return set()
            
            query = "SELECT chat_id, thread_id FROM authorized_chats_state"
            result = fetch_query(query)
            
            authorized_chats = set()
            for row in result:
                authorized_chats.add((row['chat_id'], row['thread_id']))
            
            self.logger.info(f"✅ StatePersistence: Загружено {len(authorized_chats)} авторизованных чатов")
            return authorized_chats
            
        except Exception as e:
            self.logger.error(f"❌ StatePersistence: Ошибка загрузки авторизованных чатов: {e}")
            return set()
    
    def clear_all_state(self) -> bool:
        """
        Очищает все сохраненное состояние
        
        Returns:
            bool: True если очистка успешна
        """
        try:
            if not self.db:
                return False
            
            # Очищаем все таблицы состояния
            execute_query("DELETE FROM bot_state")
            execute_query("DELETE FROM active_games_state")
            execute_query("DELETE FROM player_games_state")
            execute_query("DELETE FROM authorized_chats_state")
            
            self.logger.info("✅ StatePersistence: Все состояние очищено")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ StatePersistence: Ошибка очистки состояния: {e}")
            return False
    
    def cleanup_old_state(self, days_old: int = 7) -> bool:
        """
        Очищает старое состояние
        
        Args:
            days_old: Количество дней для очистки
            
        Returns:
            bool: True если очистка успешна
        """
        try:
            if not self.db:
                return False
            
            # Очищаем состояние старше указанного количества дней
            query = """
                DELETE FROM bot_state 
                WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            """
            
            execute_query(query, (days_old,))
            
            self.logger.info(f"✅ StatePersistence: Очищено состояние старше {days_old} дней")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ StatePersistence: Ошибка очистки старого состояния: {e}")
            return False


# Глобальный экземпляр для сохранения состояния
state_persistence = StatePersistence()
