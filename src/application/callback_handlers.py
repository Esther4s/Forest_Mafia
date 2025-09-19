#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчики callback'ов
Содержит логику обработки callback запросов от inline кнопок
"""

import logging
from typing import Dict, Optional, Any
from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..domain.value_objects import ChatId, UserId
from ..domain.entities import Game, Player
from ..domain.value_objects import GamePhase, Role, Team
from .bot_service import BotService

logger = logging.getLogger(__name__)


class CallbackHandlers:
    """Обработчики callback'ов"""
    
    def __init__(self, bot_service: BotService):
        self.bot_service = bot_service
        self.callback_handlers: Dict[str, callable] = {
            # Голосование
            'vote': self._handle_vote_callback,
            'skip_vote': self._handle_skip_vote_callback,
            'vote_skip': self._handle_skip_vote_callback,
            
            # Ночные действия
            'wolf_kill': self._handle_wolf_kill_callback,
            'fox_steal': self._handle_fox_steal_callback,
            'mole_check': self._handle_mole_check_callback,
            'beaver_protect': self._handle_beaver_protect_callback,
            'wolf_skip': self._handle_skip_night_action_callback,
            'fox_skip': self._handle_skip_night_action_callback,
            'mole_skip': self._handle_skip_night_action_callback,
            'beaver_skip': self._handle_skip_night_action_callback,
            
            # Магазин и профиль
            'shop': self._handle_shop_callback,
            'buy_item': self._handle_buy_item_callback,
            'profile': self._handle_profile_callback,
            'show_balance': self._handle_show_balance_callback,
            'show_shop': self._handle_show_shop_callback,
            'show_stats': self._handle_show_stats_callback,
            'show_inventory': self._handle_show_inventory_callback,
            'show_chat_stats': self._handle_show_chat_stats_callback,
            
            # Настройки
            'settings': self._handle_settings_callback,
            'settings_back': self._handle_settings_back_callback,
            'settings_timers': self._handle_settings_timers_callback,
            'settings_roles': self._handle_settings_roles_callback,
            'settings_players': self._handle_settings_players_callback,
            'forest_settings': self._handle_forest_settings_callback,
            'settings_toggle_test': self._handle_toggle_test_mode_callback,
            'settings_reset_chat': self._handle_reset_chat_settings_callback,
            'settings_close': self._handle_close_settings_callback,
            
            # Игровые действия
            'join_game': self._handle_join_game_callback,
            'start_game': self._handle_start_game_callback,
            'leave_registration': self._handle_leave_registration_callback,
            'cancel_game': self._handle_cancel_game_callback,
            'end_game': self._handle_end_game_callback,
            'repeat_role_actions': self._handle_repeat_role_actions_callback,
            'view_my_role': self._handle_view_my_role_callback,
            
            # Навигация
            'back_to_main': self._handle_back_to_main_callback,
            'back_to_start': self._handle_back_to_start_callback,
            'back_to_profile': self._handle_back_to_profile_callback,
            'close_menu': self._handle_close_menu_callback,
            
            # Языковые настройки
            'language_settings': self._handle_language_settings_callback,
            'lang_ru': self._handle_language_ru_callback,
            'lang_en_disabled': self._handle_language_en_disabled_callback,
            
            # Профиль в ЛС
            'show_profile_pm': self._handle_show_profile_pm_callback,
            'show_roles_pm': self._handle_show_roles_pm_callback,
            'show_rules_pm': self._handle_show_rules_pm_callback,
            'join_chat': self._handle_join_chat_callback,
            
            # Таймеры
            'timer_night': self._handle_timer_night_callback,
            'timer_day': self._handle_timer_day_callback,
            'timer_vote': self._handle_timer_vote_callback,
            'timer_back': self._handle_timer_back_callback,
            
            # Установка значений
            'set_night': self._handle_set_night_callback,
            'set_day': self._handle_set_day_callback,
            'set_vote': self._handle_set_vote_callback,
            'set_min_players': self._handle_set_min_players_callback,
            'set_max_players': self._handle_set_max_players_callback,
            
            # Роли
            'role_wolves': self._handle_role_wolves_callback,
            'role_fox': self._handle_role_fox_callback,
            'role_mole': self._handle_role_mole_callback,
            'role_beaver': self._handle_role_beaver_callback,
            
            # Лесные настройки
            'forest_night_settings': self._handle_forest_night_settings_callback,
            'forest_fox_settings': self._handle_forest_fox_settings_callback,
            'forest_beaver_settings': self._handle_forest_beaver_settings_callback,
            'forest_mole_settings': self._handle_forest_mole_settings_callback,
            'forest_rewards_settings': self._handle_forest_rewards_settings_callback,
            'forest_dead_settings': self._handle_forest_dead_settings_callback,
            'forest_auto_end_settings': self._handle_forest_auto_end_settings_callback,
            'forest_settings_back': self._handle_forest_settings_back_callback,
            
            # Дневные действия
            'day_end_discussion': self._handle_day_end_discussion_callback,
            
            # Приветственные кнопки
            'welcome_start_game': self._handle_welcome_start_game_callback,
            'welcome_rules': self._handle_welcome_rules_callback,
            'welcome_status': self._handle_welcome_status_callback,
            
            # Отмена действий
            'cancel_action': self._handle_cancel_action_callback,
            
            # Быстрый режим
            'toggle_quick_mode_game': self._handle_toggle_quick_mode_game_callback,
            
            # Прощальные сообщения
            'farewell_message': self._handle_farewell_message_callback,
            'farewell_custom': self._handle_farewell_custom_callback,
            'farewell_back': self._handle_farewell_back_callback,
            'leave_forest': self._handle_leave_forest_callback
        }
    
    async def _is_admin(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Проверяет, является ли пользователь администратором чата"""
        try:
            user_id = query.from_user.id
            chat_id = query.message.chat_id
            
            # В личных сообщениях считаем пользователя админом
            if chat_id == user_id:
                return True
            
            # Проверяем права в группе
            member = await context.bot.get_chat_member(chat_id, user_id)
            return member.status in ['creator', 'administrator']
        except Exception as e:
            logger.error(f"Ошибка проверки прав администратора: {e}")
            return False
    
    async def _check_admin_permission(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Проверяет права администратора и показывает alert если нет прав"""
        if not await self._is_admin(query, context):
            await query.answer("❌ Это действие могут совершать только администраторы.", show_alert=True)
            return False
        return True
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Основной обработчик callback'ов"""
        query = update.callback_query
        await query.answer()
        
        try:
            # Парсим callback data
            callback_data = query.data
            if not callback_data:
                await query.edit_message_text("❌ Неверные данные callback'а")
                return
            
            # Разбираем callback data (формат: action_param1_param2 или action:param1:param2)
            if ':' in callback_data:
                parts = callback_data.split(':')
                action = parts[0]
                params = parts[1:] if len(parts) > 1 else []
            else:
                # Формат: action_param1_param2
                parts = callback_data.split('_')
                action = parts[0]
                params = parts[1:] if len(parts) > 1 else []
            
            # Находим обработчик
            handler = self.callback_handlers.get(action)
            if not handler:
                # Пробуем найти обработчик для составного действия
                if len(parts) >= 2:
                    compound_action = f"{parts[0]}_{parts[1]}"
                    handler = self.callback_handlers.get(compound_action)
                    if handler:
                        params = parts[2:] if len(parts) > 2 else []
                    else:
                        # Пробуем найти обработчик для полного callback_data
                        handler = self.callback_handlers.get(callback_data)
                        if not handler:
                            await query.edit_message_text(f"❌ Неизвестное действие: {callback_data}")
                            return
                        params = []
                else:
                    await query.edit_message_text(f"❌ Неизвестное действие: {action}")
                    return
            
            # Выполняем обработчик
            await handler(query, params, context)
            
        except Exception as e:
            logger.error(f"Ошибка обработки callback'а: {e}")
            await query.edit_message_text("❌ Произошла ошибка при обработке запроса")
    
    async def _handle_vote_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик голосования"""
        if len(params) < 1:
            await query.edit_message_text("❌ Неверные параметры голосования")
            return
        
        target_id = int(params[0])
        user_id = UserId(query.from_user.id)
        chat_id = ChatId(query.message.chat_id)
        target_user_id = UserId(target_id)
        
        result = await self.bot_service.vote(chat_id, user_id, target_user_id)
        await query.edit_message_text(result["message"])
    
    async def _handle_skip_vote_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик пропуска голосования"""
        user_id = UserId(query.from_user.id)
        chat_id = ChatId(query.message.chat_id)
        
        result = await self.bot_service.vote(chat_id, user_id, None)
        await query.edit_message_text(result["message"])
    
    async def _handle_wolf_kill_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик убийства волка"""
        if len(params) < 1:
            await query.edit_message_text("❌ Неверные параметры действия волка")
            return
        
        target_id = int(params[0])
        user_id = UserId(query.from_user.id)
        chat_id = ChatId(query.message.chat_id)
        
        # Получаем игру
        game = self.bot_service.active_games.get(chat_id.value)
        if not game:
            await query.edit_message_text("❌ Игра не найдена")
            return
        
        # Проверяем, что это ночная фаза
        if game.phase != GamePhase.NIGHT:
            await query.edit_message_text("❌ Сейчас не ночная фаза")
            return
        
        # Проверяем, что игрок - волк
        player = game.players.get(user_id.value)
        if not player or player.role != Role.WOLF:
            await query.edit_message_text("❌ Вы не волк")
            return
        
        # Проверяем, что цель жива
        target = game.players.get(target_id)
        if not target or not target.is_alive:
            await query.edit_message_text("❌ Цель недоступна")
            return
        
        # Устанавливаем действие
        game.night_actions[user_id.value] = {
            'action': 'kill',
            'target': target_id
        }
        
        await query.edit_message_text(f"✅ Выбрана цель: {target.username.value}")
    
    async def _handle_fox_steal_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик кражи лисы"""
        if len(params) < 1:
            await query.edit_message_text("❌ Неверные параметры действия лисы")
            return
        
        target_id = int(params[0])
        user_id = UserId(query.from_user.id)
        chat_id = ChatId(query.message.chat_id)
        
        # Получаем игру
        game = self.bot_service.active_games.get(chat_id.value)
        if not game:
            await query.edit_message_text("❌ Игра не найдена")
            return
        
        # Проверяем, что это ночная фаза
        if game.phase != GamePhase.NIGHT:
            await query.edit_message_text("❌ Сейчас не ночная фаза")
            return
        
        # Проверяем, что игрок - лиса
        player = game.players.get(user_id.value)
        if not player or player.role != Role.FOX:
            await query.edit_message_text("❌ Вы не лиса")
            return
        
        # Проверяем, что цель жива и травоядная
        target = game.players.get(target_id)
        if not target or not target.is_alive or target.team != Team.HERBIVORES:
            await query.edit_message_text("❌ Цель недоступна")
            return
        
        # Устанавливаем действие
        game.night_actions[user_id.value] = {
            'action': 'steal',
            'target': target_id
        }
        
        await query.edit_message_text(f"✅ Выбрана цель для кражи: {target.username.value}")
    
    async def _handle_mole_check_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик проверки крота"""
        if len(params) < 1:
            await query.edit_message_text("❌ Неверные параметры действия крота")
            return
        
        target_id = int(params[0])
        user_id = UserId(query.from_user.id)
        chat_id = ChatId(query.message.chat_id)
        
        # Получаем игру
        game = self.bot_service.active_games.get(chat_id.value)
        if not game:
            await query.edit_message_text("❌ Игра не найдена")
            return
        
        # Проверяем, что это ночная фаза
        if game.phase != GamePhase.NIGHT:
            await query.edit_message_text("❌ Сейчас не ночная фаза")
            return
        
        # Проверяем, что игрок - крот
        player = game.players.get(user_id.value)
        if not player or player.role != Role.MOLE:
            await query.edit_message_text("❌ Вы не крот")
            return
        
        # Проверяем, что цель жива и не сам крот
        target = game.players.get(target_id)
        if not target or not target.is_alive or target_id == user_id.value:
            await query.edit_message_text("❌ Цель недоступна")
            return
        
        # Устанавливаем действие
        game.night_actions[user_id.value] = {
            'action': 'check',
            'target': target_id
        }
        
        await query.edit_message_text(f"✅ Выбрана цель для проверки: {target.username.value}")
    
    async def _handle_beaver_protect_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик защиты бобра"""
        if len(params) < 1:
            await query.edit_message_text("❌ Неверные параметры действия бобра")
            return
        
        target_id = int(params[0])
        user_id = UserId(query.from_user.id)
        chat_id = ChatId(query.message.chat_id)
        
        # Получаем игру
        game = self.bot_service.active_games.get(chat_id.value)
        if not game:
            await query.edit_message_text("❌ Игра не найдена")
            return
        
        # Проверяем, что это ночная фаза
        if game.phase != GamePhase.NIGHT:
            await query.edit_message_text("❌ Сейчас не ночная фаза")
            return
        
        # Проверяем, что игрок - бобер
        player = game.players.get(user_id.value)
        if not player or player.role != Role.BEAVER:
            await query.edit_message_text("❌ Вы не бобер")
            return
        
        # Проверяем, что цель жива и травоядная
        target = game.players.get(target_id)
        if not target or not target.is_alive or target.team != Team.HERBIVORES:
            await query.edit_message_text("❌ Цель недоступна")
            return
        
        # Устанавливаем действие
        game.night_actions[user_id.value] = {
            'action': 'protect',
            'target': target_id
        }
        
        await query.edit_message_text(f"✅ Выбрана цель для защиты: {target.username.value}")
    
    async def _handle_skip_night_action_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик пропуска ночного действия"""
        user_id = UserId(query.from_user.id)
        chat_id = ChatId(query.message.chat_id)
        
        # Получаем игру
        game = self.bot_service.active_games.get(chat_id.value)
        if not game:
            await query.edit_message_text("❌ Игра не найдена")
            return
        
        # Проверяем, что это ночная фаза
        if game.phase != GamePhase.NIGHT:
            await query.edit_message_text("❌ Сейчас не ночная фаза")
            return
        
        # Устанавливаем пропуск действия
        game.night_actions[user_id.value] = {
            'action': 'skip',
            'target': None
        }
        
        await query.edit_message_text("✅ Ночное действие пропущено")
    
    async def _handle_shop_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик магазина"""
        user_id = UserId(query.from_user.id)
        
        try:
            balance = await self.bot_service.get_user_balance(user_id)
            
            # Создаем клавиатуру магазина
            keyboard = [
                [InlineKeyboardButton("🍎 Яблоко (10 орехов)", callback_data="buy_item:apple:10")],
                [InlineKeyboardButton("🛡️ Защита (25 орехов)", callback_data="buy_item:protection:25")],
                [InlineKeyboardButton("❤️ Дополнительная жизнь (50 орехов)", callback_data="buy_item:extra_life:50")],
                [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            shop_text = (
                f"🛒 **Лесной магазин** 🛒\n\n"
                f"💰 Ваш баланс: {balance} орехов\n\n"
                f"Выберите товар для покупки:"
            )
            
            await query.edit_message_text(shop_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка открытия магазина: {e}")
            await query.edit_message_text("❌ Ошибка открытия магазина")
    
    async def _handle_buy_item_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик покупки предмета"""
        if len(params) < 2:
            await query.edit_message_text("❌ Неверные параметры покупки")
            return
        
        item_type = params[0]
        price = int(params[1])
        user_id = UserId(query.from_user.id)
        
        try:
            balance = await self.bot_service.get_user_balance(user_id)
            
            if balance < price:
                await query.edit_message_text(f"❌ Недостаточно орехов! Нужно: {price}, у вас: {balance}")
                return
            
            # Покупаем предмет
            await self.bot_service.update_user_balance(user_id, -price)
            
            # Здесь должна быть логика добавления предмета в инвентарь
            item_names = {
                'apple': '🍎 Яблоко',
                'protection': '🛡️ Защита',
                'extra_life': '❤️ Дополнительная жизнь'
            }
            
            item_name = item_names.get(item_type, item_type)
            
            await query.edit_message_text(
                f"✅ Покупка успешна!\n\n"
                f"🛒 Куплено: {item_name}\n"
                f"💰 Потрачено: {price} орехов\n"
                f"💳 Остаток: {balance - price} орехов"
            )
            
        except Exception as e:
            logger.error(f"Ошибка покупки предмета: {e}")
            await query.edit_message_text("❌ Ошибка покупки предмета")
    
    async def _handle_profile_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик профиля"""
        user_id = UserId(query.from_user.id)
        
        try:
            balance = await self.bot_service.get_user_balance(user_id)
            display_name = await self.bot_service.get_user_display_name(
                user_id, query.from_user.username, query.from_user.first_name
            )
            
            # Создаем клавиатуру профиля
            keyboard = [
                [InlineKeyboardButton("🛒 Магазин", callback_data="shop")],
                [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
                [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            profile_text = (
                f"👤 **Профиль игрока** 👤\n\n"
                f"🆔 Имя: {display_name}\n"
                f"💰 Баланс: {balance} орехов\n"
                f"🎮 Игр сыграно: 0\n"
                f"🏆 Побед: 0\n\n"
                f"Выберите действие:"
            )
            
            await query.edit_message_text(profile_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка открытия профиля: {e}")
            await query.edit_message_text("❌ Ошибка открытия профиля")
    
    async def _handle_settings_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик настроек"""
        # Создаем клавиатуру настроек
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        settings_text = (
            f"⚙️ **Настройки** ⚙️\n\n"
            f"🔔 Уведомления: Включены\n"
            f"🌙 Ночной режим: Выключен\n"
            f"🎵 Звуки: Включены\n\n"
            f"Настройки будут доступны в следующих версиях."
        )
        
        await query.edit_message_text(settings_text, reply_markup=reply_markup)
    
    # === ИГРОВЫЕ ДЕЙСТВИЯ ===
    
    async def _handle_join_game_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик присоединения к игре"""
        user_id = UserId(query.from_user.id)
        chat_id = ChatId(query.message.chat_id)
        username = query.from_user.username or query.from_user.first_name or f"User_{user_id.value}"
        
        result = await self.bot_service.join_game(
            chat_id=chat_id,
            user_id=user_id,
            username=username,
            first_name=query.from_user.first_name
        )
        
        await query.edit_message_text(result["message"])
    
    async def _handle_start_game_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик начала игры"""
        # Проверяем права администратора
        if not await self._check_admin_permission(query, context):
            return
        
        chat_id = ChatId(query.message.chat_id)
        result = await self.bot_service.start_game(chat_id)
        await query.edit_message_text(result["message"])
    
    async def _handle_leave_registration_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик выхода из регистрации"""
        user_id = UserId(query.from_user.id)
        chat_id = ChatId(query.message.chat_id)
        result = await self.bot_service.leave_game(chat_id, user_id)
        await query.edit_message_text(result["message"])
    
    async def _handle_cancel_game_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик отмены игры"""
        # Проверяем права администратора
        if not await self._check_admin_permission(query, context):
            return
        
        # Получаем информацию о пользователе для сообщения
        user_info = query.from_user
        admin_name = user_info.first_name or user_info.username or f"ID{user_info.id}"
        
        chat_id = ChatId(query.message.chat_id)
        result = await self.bot_service.cancel_game(chat_id, f"Игра отменена участником {admin_name}")
        await query.edit_message_text(result["message"])
    
    async def _handle_end_game_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик завершения игры"""
        # Проверяем права администратора
        if not await self._check_admin_permission(query, context):
            return
        
        chat_id = ChatId(query.message.chat_id)
        result = await self.bot_service.end_game(chat_id, "Игра завершена администратором")
        await query.edit_message_text(result["message"])
    
    async def _handle_repeat_role_actions_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик повторения действий роли"""
        user_id = UserId(query.from_user.id)
        chat_id = ChatId(query.message.chat_id)
        
        # Получаем игру
        game = self.bot_service.active_games.get(chat_id.value)
        if not game:
            await query.edit_message_text("❌ Игра не найдена")
            return
        
        # Проверяем, что игрок участвует в игре
        player = game.players.get(user_id.value)
        if not player:
            await query.edit_message_text("❌ Вы не участвуете в игре")
            return
        
        # Отправляем информацию о роли в зависимости от фазы
        if game.phase == GamePhase.NIGHT:
            await self._send_night_role_info(query, game, player)
        elif game.phase == GamePhase.DAY:
            await self._send_day_role_info(query, game, player)
        elif game.phase == GamePhase.VOTING:
            await self._send_voting_role_info(query, game, player)
        else:
            await query.edit_message_text("❌ Неизвестная фаза игры")
    
    async def _handle_view_my_role_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик просмотра своей роли"""
        await self._handle_repeat_role_actions_callback(query, params, context)
    
    # === НАВИГАЦИЯ ===
    
    async def _handle_back_to_main_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик возврата к главному меню"""
        keyboard = [
            [InlineKeyboardButton("🌰 Баланс", callback_data="show_balance")],
            [InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")],
            [InlineKeyboardButton("📊 Статистика", callback_data="show_stats")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="close_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🌲 **Главное меню Лес и волки**\n\nВыберите действие:",
            reply_markup=reply_markup
        )
    
    async def _handle_back_to_start_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик возврата к начальному меню"""
        keyboard = [
            [InlineKeyboardButton("🌲 Добавить игру в свой чат", url=f"https://t.me/{context.bot.username}?startgroup=true")],
            [InlineKeyboardButton("🎮 Войти в чат", callback_data="join_chat")],
            [InlineKeyboardButton("🌍 Язык / Language", callback_data="language_settings")],
            [InlineKeyboardButton("👤 Профиль", callback_data="show_profile_pm")],
            [InlineKeyboardButton("🎭 Роли", callback_data="show_roles_pm")],
            [InlineKeyboardButton("💡 Советы по игре (Роль)", url=f"https://t.me/{context.bot.username}?start=role")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "🌲 **Привет!**\n\n"
            "Я бот-ведущий для игры в 🌲 **Лес и Волки**.\n\n"
            "🎭 **Ролевая игра в стиле 'Мафия' с лесными зверушками**\n\n"
            "🐺 **Хищники:** Волки + Лиса\n"
            "🐰 **Травоядные:** Зайцы + Крот + Бобёр\n\n"
            "🌙 **Как играть:**\n"
            "• Ночью хищники охотятся, травоядные защищаются\n"
            "• Днем все обсуждают и голосуют за изгнание\n"
            "• Цель: уничтожить всех противников\n\n"
            "🚀 **Выберите действие:**"
        )
        
        await query.edit_message_text(welcome_text, reply_markup=reply_markup)
    
    async def _handle_back_to_profile_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик возврата к профилю"""
        await self._handle_profile_callback(query, params, context)
    
    async def _handle_close_menu_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик закрытия меню"""
        await query.edit_message_text("👤 Меню закрыто")
    
    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===
    
    async def _send_night_role_info(self, query: CallbackQuery, game: Game, player: Player) -> None:
        """Отправляет информацию о ночной роли"""
        role_info = {
            Role.WOLF: "🐺 **Ваша роль: Волк**\n\n🌙 **Ночная фаза**\n\nВыберите жертву для убийства:",
            Role.FOX: "🦊 **Ваша роль: Лиса**\n\n🌙 **Ночная фаза**\n\nВыберите жертву для кражи орешков:",
            Role.MOLE: "🦫 **Ваша роль: Крот**\n\n🌙 **Ночная фаза**\n\nВыберите игрока для проверки роли:",
            Role.BEAVER: "🦦 **Ваша роль: Бобёр**\n\n🌙 **Ночная фаза**\n\nВыберите игрока для защиты:",
            Role.HARE: "🐰 **Ваша роль: Заяц**\n\n🌙 **Ночная фаза**\n\nУ вас нет ночных действий. Отдыхайте и ждите утра!"
        }
        
        message = role_info.get(player.role, "❌ Неизвестная роль")
        await query.edit_message_text(message)
    
    async def _send_day_role_info(self, query: CallbackQuery, game: Game, player: Player) -> None:
        """Отправляет информацию о дневной роли"""
        team_name = "Хищники" if player.team == Team.PREDATORS else "Травоядные"
        goal = "Уничтожить всех травоядных" if player.team == Team.PREDATORS else "Найти и изгнать всех хищников"
        
        message = (
            f"☀️ **Дневная фаза**\n\n"
            f"🎭 **Ваша роль:** {self._get_role_name_russian(player.role)}\n"
            f"🏷️ **Команда:** {team_name}\n\n"
            f"💬 **Обсуждайте события ночи и выдвигайте подозрения!**\n\n"
            f"🎯 **Ваша цель:** {goal}"
        )
        
        await query.edit_message_text(message)
    
    async def _send_voting_role_info(self, query: CallbackQuery, game: Game, player: Player) -> None:
        """Отправляет информацию о роли в голосовании"""
        team_name = "Хищники" if player.team == Team.PREDATORS else "Травоядные"
        goal = "Уничтожить всех травоядных" if player.team == Team.PREDATORS else "Найти и изгнать всех хищников"
        
        message = (
            f"🗳️ **Фаза голосования**\n\n"
            f"🎭 **Ваша роль:** {self._get_role_name_russian(player.role)}\n"
            f"🏷️ **Команда:** {team_name}\n\n"
            f"🗳️ **Голосуйте за изгнание подозреваемого!**\n\n"
            f"🎯 **Ваша цель:** {goal}"
        )
        
        await query.edit_message_text(message)
    
    def _get_role_name_russian(self, role: Role) -> str:
        """Возвращает русское название роли"""
        role_names = {
            Role.WOLF: "Волк",
            Role.FOX: "Лиса",
            Role.HARE: "Зайец",
            Role.MOLE: "Крот",
            Role.BEAVER: "Бобёр"
        }
        return role_names.get(role, "Неизвестно")
