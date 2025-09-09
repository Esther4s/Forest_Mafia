#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Менеджер автоматического сохранения состояния бота
Сохраняет данные при изменениях и загружает при старте
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from state_persistence import state_persistence

logger = logging.getLogger(__name__)


class AutoSaveManager:
    """Менеджер автоматического сохранения"""
    
    def __init__(self, bot_instance):
        self.logger = logger
        self.bot = bot_instance
        self.save_interval = 30  # Сохраняем каждые 30 секунд
        self.last_save_time = datetime.now()
        self.auto_save_task = None
        self.is_running = False
    
    def start_auto_save(self):
        """Запускает автоматическое сохранение"""
        if self.is_running:
            return
        
        self.is_running = True
        self.auto_save_task = asyncio.create_task(self._auto_save_loop())
        self.logger.info("✅ AutoSaveManager: Автоматическое сохранение запущено")
    
    def stop_auto_save(self):
        """Останавливает автоматическое сохранение"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.auto_save_task:
            self.auto_save_task.cancel()
        self.logger.info("✅ AutoSaveManager: Автоматическое сохранение остановлено")
    
    async def _auto_save_loop(self):
        """Цикл автоматического сохранения"""
        while self.is_running:
            try:
                await asyncio.sleep(self.save_interval)
                
                if self.is_running:
                    await self.save_current_state()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ AutoSaveManager: Ошибка в цикле сохранения: {e}")
    
    async def save_current_state(self):
        """Сохраняет текущее состояние бота"""
        try:
            # Сохраняем активные игры
            await self._save_active_games()
            
            # Сохраняем авторизованные чаты
            await self._save_authorized_chats()
            
            # Сохраняем общее состояние
            await self._save_general_state()
            
            self.last_save_time = datetime.now()
            self.logger.debug("✅ AutoSaveManager: Состояние сохранено")
            
        except Exception as e:
            self.logger.error(f"❌ AutoSaveManager: Ошибка сохранения состояния: {e}")
    
    async def _save_active_games(self):
        """Сохраняет активные игры"""
        try:
            if hasattr(self.bot, 'games') and hasattr(self.bot, 'player_games'):
                success = state_persistence.save_active_games(
                    self.bot.games,
                    self.bot.player_games,
                    getattr(self.bot, 'night_actions', {}),
                    getattr(self.bot, 'night_interfaces', {})
                )
                
                if success:
                    self.logger.debug("✅ AutoSaveManager: Активные игры сохранены")
                else:
                    self.logger.warning("⚠️ AutoSaveManager: Не удалось сохранить активные игры")
                    
        except Exception as e:
            self.logger.error(f"❌ AutoSaveManager: Ошибка сохранения активных игр: {e}")
    
    async def _save_authorized_chats(self):
        """Сохраняет авторизованные чаты"""
        try:
            if hasattr(self.bot, 'authorized_chats'):
                success = state_persistence.save_authorized_chats(self.bot.authorized_chats)
                
                if success:
                    self.logger.debug("✅ AutoSaveManager: Авторизованные чаты сохранены")
                else:
                    self.logger.warning("⚠️ AutoSaveManager: Не удалось сохранить авторизованные чаты")
                    
        except Exception as e:
            self.logger.error(f"❌ AutoSaveManager: Ошибка сохранения авторизованных чатов: {e}")
    
    async def _save_general_state(self):
        """Сохраняет общее состояние бота"""
        try:
            general_state = {
                'last_save_time': self.last_save_time.isoformat(),
                'bot_token': getattr(self.bot, 'bot_token', None),
                'global_settings': getattr(self.bot, 'global_settings', {}).__dict__ if hasattr(self.bot, 'global_settings') else {},
                'no_exile_messages': getattr(self.bot, 'no_exile_messages', []),
                'no_kill_messages': getattr(self.bot, 'no_kill_messages', [])
            }
            
            success = state_persistence.save_bot_state('general', general_state)
            
            if success:
                self.logger.debug("✅ AutoSaveManager: Общее состояние сохранено")
            else:
                self.logger.warning("⚠️ AutoSaveManager: Не удалось сохранить общее состояние")
                
        except Exception as e:
            self.logger.error(f"❌ AutoSaveManager: Ошибка сохранения общего состояния: {e}")
    
    async def load_saved_state(self):
        """Загружает сохраненное состояние"""
        try:
            # Загружаем активные игры
            await self._load_active_games()
            
            # Загружаем авторизованные чаты
            await self._load_authorized_chats()
            
            # Загружаем общее состояние
            await self._load_general_state()
            
            self.logger.info("✅ AutoSaveManager: Сохраненное состояние загружено")
            
        except Exception as e:
            self.logger.error(f"❌ AutoSaveManager: Ошибка загрузки состояния: {e}")
    
    async def _load_active_games(self):
        """Загружает активные игры"""
        try:
            saved_data = state_persistence.load_active_games()
            
            if not saved_data:
                self.logger.info("ℹ️ AutoSaveManager: Нет сохраненных активных игр")
                return
            
            # Восстанавливаем игры
            games_data = saved_data.get('games', [])
            player_games_data = saved_data.get('player_games', [])
            
            # Очищаем текущие данные
            if hasattr(self.bot, 'games'):
                self.bot.games.clear()
            if hasattr(self.bot, 'player_games'):
                self.bot.player_games.clear()
            if hasattr(self.bot, 'night_actions'):
                self.bot.night_actions.clear()
            if hasattr(self.bot, 'night_interfaces'):
                self.bot.night_interfaces.clear()
            
            # Восстанавливаем игры
            for game_data in games_data:
                await self._restore_game(game_data)
            
            # Восстанавливаем маппинг игроков
            for player_data in player_games_data:
                self.bot.player_games[player_data['user_id']] = player_data['chat_id']
            
            self.logger.info(f"✅ AutoSaveManager: Восстановлено {len(games_data)} активных игр")
            
        except Exception as e:
            self.logger.error(f"❌ AutoSaveManager: Ошибка загрузки активных игр: {e}")
    
    async def _restore_game(self, game_data):
        """Восстанавливает игру из сохраненных данных"""
        try:
            from game_logic import Game, GamePhase, Role, Team, Player
            
            # Создаем объект игры
            game = Game()
            game.chat_id = game_data['chat_id']
            game.thread_id = game_data.get('thread_id')
            
            # Восстанавливаем данные игры
            game_data_dict = game_data['game_data']
            game.phase = GamePhase(game_data_dict['phase'])
            game.current_round = game_data_dict['current_round']
            game.status = game_data_dict['status']
            game.db_game_id = game_data_dict.get('db_game_id')
            
            if game_data_dict.get('phase_end_time'):
                from datetime import datetime
                game.phase_end_time = datetime.fromisoformat(game_data_dict['phase_end_time'])
            
            # Восстанавливаем игроков
            players_data = game_data['players_data']
            for user_id, player_data in players_data.items():
                player = Player(
                    user_id=player_data['user_id'],
                    username=player_data.get('username'),
                    first_name=player_data.get('first_name'),
                    last_name=player_data.get('last_name')
                )
                
                if player_data.get('role'):
                    player.role = Role(player_data['role'])
                if player_data.get('team'):
                    player.team = Team(player_data['team'])
                
                player.is_alive = player_data.get('is_alive', True)
                player.supplies = player_data.get('supplies', 3)
                player.max_supplies = player_data.get('max_supplies', 3)
                player.is_fox_stolen = player_data.get('is_fox_stolen', False)
                player.is_beaver_protected = player_data.get('is_beaver_protected', False)
                player.consecutive_nights_survived = player_data.get('consecutive_nights_survived', 0)
                player.last_action_round = player_data.get('last_action_round', 0)
                
                game.players[player.user_id] = player
            
            # Восстанавливаем ночные действия и интерфейсы
            from night_actions import NightActions
            from night_interface import NightInterface
            
            self.bot.night_actions[game.chat_id] = NightActions(game)
            self.bot.night_interfaces[game.chat_id] = NightInterface(game, self.bot.night_actions[game.chat_id])
            
            # Сохраняем игру
            self.bot.games[game.chat_id] = game
            
            self.logger.info(f"✅ AutoSaveManager: Игра {game.chat_id} восстановлена")
            
        except Exception as e:
            self.logger.error(f"❌ AutoSaveManager: Ошибка восстановления игры: {e}")
    
    async def _load_authorized_chats(self):
        """Загружает авторизованные чаты"""
        try:
            authorized_chats = state_persistence.load_authorized_chats()
            
            if hasattr(self.bot, 'authorized_chats'):
                self.bot.authorized_chats = authorized_chats
            
            self.logger.info(f"✅ AutoSaveManager: Восстановлено {len(authorized_chats)} авторизованных чатов")
            
        except Exception as e:
            self.logger.error(f"❌ AutoSaveManager: Ошибка загрузки авторизованных чатов: {e}")
    
    async def _load_general_state(self):
        """Загружает общее состояние"""
        try:
            general_state = state_persistence.load_bot_state('general')
            
            if general_state:
                # Восстанавливаем общие настройки
                if hasattr(self.bot, 'global_settings') and general_state.get('global_settings'):
                    for key, value in general_state['global_settings'].items():
                        setattr(self.bot.global_settings, key, value)
                
                # Восстанавливаем сообщения
                if general_state.get('no_exile_messages'):
                    self.bot.no_exile_messages = general_state['no_exile_messages']
                if general_state.get('no_kill_messages'):
                    self.bot.no_kill_messages = general_state['no_kill_messages']
                
                self.logger.info("✅ AutoSaveManager: Общее состояние восстановлено")
            
        except Exception as e:
            self.logger.error(f"❌ AutoSaveManager: Ошибка загрузки общего состояния: {e}")
    
    def force_save(self):
        """Принудительно сохраняет состояние"""
        asyncio.create_task(self.save_current_state())
    
    def get_save_status(self) -> Dict[str, Any]:
        """Получает статус сохранения"""
        return {
            'is_running': self.is_running,
            'last_save_time': self.last_save_time.isoformat(),
            'save_interval': self.save_interval,
            'time_since_last_save': (datetime.now() - self.last_save_time).total_seconds()
        }
