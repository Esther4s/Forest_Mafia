#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Менеджер ночных действий для Лес и волки Bot
"""

import logging
from typing import Dict, Optional
from telegram import Update
from telegram.ext import ContextTypes

from game_logic import Game, GamePhase, Role
from night_actions import NightActions
from night_interface import NightInterface

logger = logging.getLogger(__name__)


class NightManager:
    """Менеджер ночных действий"""
    
    def __init__(self):
        self.night_actions: Dict[int, NightActions] = {}
        self.night_interfaces: Dict[int, NightInterface] = {}
    
    def get_or_create_night_actions(self, game: Game) -> NightActions:
        """Получает или создает объект ночных действий для игры"""
        if game.chat_id not in self.night_actions:
            self.night_actions[game.chat_id] = NightActions(game)
            logger.info(f"✅ Созданы ночные действия для игры {game.chat_id}")
        
        return self.night_actions[game.chat_id]
    
    def get_or_create_night_interface(self, game: Game) -> NightInterface:
        """Получает или создает интерфейс ночных действий для игры"""
        if game.chat_id not in self.night_interfaces:
            night_actions = self.get_or_create_night_actions(game)
            self.night_interfaces[game.chat_id] = NightInterface(game, night_actions)
            logger.info(f"✅ Создан интерфейс ночных действий для игры {game.chat_id}")
        
        return self.night_interfaces[game.chat_id]
    
    async def start_night_phase(self, game: Game, context: ContextTypes.DEFAULT_TYPE):
        """Начинает ночную фазу"""
        game.start_night()
        
        # Получаем интерфейс ночных действий
        night_interface = self.get_or_create_night_interface(game)
        
        # Отправляем меню действий игрокам с ночными ролями
        await night_interface.send_role_reminders(context)
        
        logger.info(f"🌙 Началась ночная фаза для игры {game.chat_id} (раунд {game.current_round})")
    
    async def process_night_actions(self, game: Game, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает ночные действия"""
        night_actions = self.get_or_create_night_actions(game)
        
        # Обрабатываем все действия
        results = night_actions.process_all_actions()
        
        # Отправляем результаты
        night_interface = self.get_or_create_night_interface(game)
        await night_interface.send_night_results(context, results)
        
        # Очищаем действия
        night_actions.clear_actions()
        
        logger.info(f"🌙 Ночные действия обработаны для игры {game.chat_id}")
    
    async def handle_night_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает callback от ночных действий"""
        query = update.callback_query
        user_id = query.from_user.id
        
        # Находим игру игрока
        game = self._find_player_game(user_id)
        if not game:
            await query.answer("❌ Вы не участвуете в игре!", show_alert=True)
            return
        
        if game.phase != GamePhase.NIGHT:
            await query.answer("❌ Сейчас не ночная фаза!", show_alert=True)
            return
        
        # Получаем интерфейс ночных действий
        night_interface = self.get_or_create_night_interface(game)
        
        # Обрабатываем действие
        await night_interface.handle_night_action(update, context)
    
    def _find_player_game(self, user_id: int) -> Optional[Game]:
        """Находит игру игрока"""
        # Это упрощенная версия - в реальном боте нужно использовать GameStateManager
        # Пока что ищем по всем играм
        for game in self.night_actions.values():
            if user_id in game.game.players:
                return game.game
        return None
    
    def cleanup_game(self, chat_id: int):
        """Очищает данные игры"""
        if chat_id in self.night_actions:
            del self.night_actions[chat_id]
        if chat_id in self.night_interfaces:
            del self.night_interfaces[chat_id]
        logger.info(f"🧹 Очищены ночные действия для игры {chat_id}")
    
    def get_night_actions_summary(self, game: Game) -> str:
        """Возвращает сводку ночных действий"""
        if game.chat_id not in self.night_actions:
            return "🌙 Ночные действия не инициализированы"
        
        night_actions = self.night_actions[game.chat_id]
        return night_actions.get_action_summary()
    
    def are_all_night_actions_completed(self, game: Game) -> bool:
        """Проверяет, все ли ночные действия выполнены"""
        if game.chat_id not in self.night_actions:
            return False
        
        night_actions = self.night_actions[game.chat_id]
        return night_actions.are_all_actions_completed()
    
    def get_player_night_actions(self, game: Game, player_id: int) -> Dict:
        """Получает доступные ночные действия игрока"""
        if game.chat_id not in self.night_actions:
            return {}
        
        night_actions = self.night_actions[game.chat_id]
        return night_actions.get_player_actions(player_id)
