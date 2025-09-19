#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Дополнительные обработчики callback'ов
Содержит все недостающие обработчики для кнопок
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


class AdditionalCallbackHandlers:
    """Дополнительные обработчики callback'ов"""
    
    def __init__(self, bot_service: BotService):
        self.bot_service = bot_service
    
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
    
    # === МАГАЗИН И ПРОФИЛЬ ===
    
    async def _handle_show_balance_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик показа баланса"""
        user_id = UserId(query.from_user.id)
        
        try:
            balance = await self.bot_service.get_user_balance(user_id)
            display_name = await self.bot_service.get_user_display_name(
                user_id, query.from_user.username, query.from_user.first_name
            )
            
            keyboard = [
                [InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            balance_text = (
                f"🌲 **Баланс Лес и волки**\n\n"
                f"👤 **{display_name}:**\n"
                f"🌰 Орешки: {balance}\n\n"
                f"💡 Орешки можно заработать, играя в Лес и волки!"
            )
            
            await query.edit_message_text(balance_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка показа баланса: {e}")
            await query.edit_message_text("❌ Ошибка показа баланса")
    
    async def _handle_show_shop_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик показа магазина"""
        user_id = UserId(query.from_user.id)
        
        try:
            balance = await self.bot_service.get_user_balance(user_id)
            display_name = await self.bot_service.get_user_display_name(
                user_id, query.from_user.username, query.from_user.first_name
            )
            
            # Создаем клавиатуру магазина
            keyboard = [
                [InlineKeyboardButton("🍎 Яблоко (10 орехов)", callback_data="buy_item:apple:10")],
                [InlineKeyboardButton("🛡️ Защита (25 орехов)", callback_data="buy_item:protection:25")],
                [InlineKeyboardButton("❤️ Дополнительная жизнь (50 орехов)", callback_data="buy_item:extra_life:50")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            shop_text = (
                f"🌲 **Лесной магазин**\n\n"
                f"👤 **{display_name}:**\n"
                f"🌰 Орешки: {balance}\n\n"
                f"🛍️ **Что будем покупать?**\n\n"
                f"**🍎 Яблоко**\n"
                f"📝 Восстанавливает 1 орешек\n"
                f"💰 10 орешков\n\n"
                f"**🛡️ Защита**\n"
                f"📝 Защищает от одной атаки волка\n"
                f"💰 25 орешков\n\n"
                f"**❤️ Дополнительная жизнь**\n"
                f"📝 Дает дополнительную жизнь в игре\n"
                f"💰 50 орешков"
            )
            
            await query.edit_message_text(shop_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка показа магазина: {e}")
            await query.edit_message_text("❌ Ошибка показа магазина")
    
    async def _handle_show_stats_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик показа статистики"""
        user_id = UserId(query.from_user.id)
        
        try:
            display_name = await self.bot_service.get_user_display_name(
                user_id, query.from_user.username, query.from_user.first_name
            )
            
            # Получаем статистику пользователя
            stats = await self.bot_service.get_user_stats(user_id)
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            stats_text = (
                f"🌲 **Статистика Лес и волки**\n\n"
                f"👤 **{display_name}:**\n\n"
                f"🎮 Игр сыграно: {stats.get('games_played', 0)}\n"
                f"🏆 Побед: {stats.get('wins', 0)}\n"
                f"💀 Поражений: {stats.get('losses', 0)}\n"
                f"🌰 Орешков заработано: {stats.get('total_nuts', 0)}\n"
                f"🎭 Ролей сыграно: {stats.get('roles_played', 0)}\n"
                f"⏱️ Время в игре: {stats.get('time_played', 0)} минут"
            )
            
            await query.edit_message_text(stats_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка показа статистики: {e}")
            await query.edit_message_text("❌ Ошибка показа статистики")
    
    async def _handle_show_inventory_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик показа инвентаря"""
        user_id = UserId(query.from_user.id)
        
        try:
            display_name = await self.bot_service.get_user_display_name(
                user_id, query.from_user.username, query.from_user.first_name
            )
            
            # Получаем инвентарь пользователя
            inventory = await self.bot_service.get_user_inventory(user_id)
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Назад", callback_data="show_profile_pm")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            inventory_text = (
                f"🧺 **Корзинка**\n\n"
                f"👤 **{display_name}:**\n\n"
            )
            
            if inventory:
                for item, count in inventory.items():
                    inventory_text += f"• {item}: {count}\n"
            else:
                inventory_text += "📦 Инвентарь пуст\n"
                inventory_text += "🛍️ Посетите магазин, чтобы купить предметы!"
            
            await query.edit_message_text(inventory_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка показа инвентаря: {e}")
            await query.edit_message_text("❌ Ошибка показа инвентаря")
    
    async def _handle_show_chat_stats_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик показа статистики в чатах"""
        user_id = UserId(query.from_user.id)
        
        try:
            display_name = await self.bot_service.get_user_display_name(
                user_id, query.from_user.username, query.from_user.first_name
            )
            
            # Получаем статистику пользователя в чатах
            chat_stats = await self.bot_service.get_user_chat_stats(user_id)
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Назад", callback_data="show_profile_pm")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            stats_text = (
                f"📜 **Свиток чести**\n\n"
                f"👤 **{display_name}:**\n\n"
            )
            
            if chat_stats:
                for chat_name, stats in chat_stats.items():
                    stats_text += f"**{chat_name}:**\n"
                    stats_text += f"• Игр: {stats.get('games', 0)}\n"
                    stats_text += f"• Побед: {stats.get('wins', 0)}\n"
                    stats_text += f"• Поражений: {stats.get('losses', 0)}\n\n"
            else:
                stats_text += "📊 Статистика в чатах пока пуста\n"
                stats_text += "🎮 Сыграйте в игру в каком-либо чате, чтобы появилась статистика!"
            
            await query.edit_message_text(stats_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка показа статистики в чатах: {e}")
            await query.edit_message_text("❌ Ошибка показа статистики в чатах")
    
    # === НАСТРОЙКИ ===
    
    async def _handle_settings_back_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик возврата к настройкам"""
        # Проверяем права администратора
        if not await self._check_admin_permission(query, context):
            return
        
        chat_id = ChatId(query.message.chat_id)
        
        try:
            # Получаем настройки чата
            chat_settings = await self.bot_service.get_chat_settings(chat_id)
            
            keyboard = [
                [InlineKeyboardButton("⏱️ Изменить таймеры", callback_data="settings_timers")],
                [InlineKeyboardButton("🎭 Изменить распределение ролей", callback_data="settings_roles")],
                [InlineKeyboardButton("👥 Лимиты игроков", callback_data="settings_players")],
                [InlineKeyboardButton("🌲 Настройки лесной мафии", callback_data="forest_settings")],
                [InlineKeyboardButton("⚡ Быстрый режим: ВКЛ" if chat_settings.get('test_mode', False) else "⚡ Быстрый режим: ВЫКЛ", callback_data="settings_toggle_test")],
                [InlineKeyboardButton("🔄 Сбросить настройки", callback_data="settings_reset_chat")],
                [InlineKeyboardButton("❌ Закрыть", callback_data="settings_close")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            settings_text = (
                f"⚙️ **Настройки чата**\n\n"
                f"⚡ Быстрый режим: {'ВКЛ' if chat_settings.get('test_mode', False) else 'ВЫКЛ'}\n"
                f"👥 Игроков: {chat_settings.get('min_players', 6)}-{chat_settings.get('max_players', 12)}\n"
                f"⏱️ Таймеры: Ночь {chat_settings.get('night_duration', 60)}с, День {chat_settings.get('day_duration', 300)}с, Голосование {chat_settings.get('vote_duration', 120)}с\n"
                f"🎭 Роли: Лиса умрет через {chat_settings.get('fox_death_threshold', 2)} ночей, Крот раскроется через {chat_settings.get('mole_reveal_threshold', 3)} ночей\n"
                f"🛡️ Защита бобра: {'ВКЛ' if chat_settings.get('beaver_protection', True) else 'ВЫКЛ'}\n"
                f"🏁 Лимиты: {chat_settings.get('max_rounds', 25)} раундов, {chat_settings.get('max_time', 180)} мин, минимум {chat_settings.get('min_alive', 2)} живых\n\n"
                f"Выберите, что хотите изменить:"
            )
            
            await query.edit_message_text(settings_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка показа настроек: {e}")
            await query.edit_message_text("❌ Ошибка показа настроек")
    
    async def _handle_settings_timers_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик настроек таймеров"""
        # Проверяем права администратора
        if not await self._check_admin_permission(query, context):
            return
        
        chat_id = ChatId(query.message.chat_id)
        
        try:
            # Получаем настройки чата
            chat_settings = await self.bot_service.get_chat_settings(chat_id)
            
            keyboard = [
                [InlineKeyboardButton("🌙 Изменить длительность ночи", callback_data="timer_night")],
                [InlineKeyboardButton("☀️ Изменить длительность дня", callback_data="timer_day")],
                [InlineKeyboardButton("🗳️ Изменить длительность голосования", callback_data="timer_vote")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            night_min = chat_settings.get('night_duration', 60) // 60
            night_sec = chat_settings.get('night_duration', 60) % 60
            day_min = chat_settings.get('day_duration', 300) // 60
            day_sec = chat_settings.get('day_duration', 300) % 60
            vote_min = chat_settings.get('vote_duration', 120) // 60
            vote_sec = chat_settings.get('vote_duration', 120) % 60
            
            night_text = f"{night_min}м {night_sec}с" if night_min > 0 else f"{night_sec}с"
            day_text = f"{day_min}м {day_sec}с" if day_min > 0 else f"{day_sec}с"
            vote_text = f"{vote_min}м {vote_sec}с" if vote_min > 0 else f"{vote_sec}с"
            
            await query.edit_message_text(
                f"⏱️ **Настройки таймеров**\n\n"
                f"Текущие значения:\n"
                f"🌙 Ночь: {night_text}\n"
                f"☀️ День: {day_text}\n"
                f"🗳️ Голосование: {vote_text}\n\n"
                f"Выберите, что хотите изменить:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа настроек таймеров: {e}")
            await query.edit_message_text("❌ Ошибка показа настроек таймеров")
    
    async def _handle_settings_roles_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик настроек ролей"""
        # Проверяем права администратора
        if not await self._check_admin_permission(query, context):
            return
        
        keyboard = [
            [InlineKeyboardButton("🐺 Волки: 25%", callback_data="role_wolves_25")],
            [InlineKeyboardButton("🦊 Лиса: 15%", callback_data="role_fox_15")],
            [InlineKeyboardButton("🦫 Крот: 15%", callback_data="role_mole_15")],
            [InlineKeyboardButton("🦦 Бобёр: 10%", callback_data="role_beaver_10")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎭 **Настройки распределения ролей**\n\n"
            "Текущие значения:\n"
            "🐺 Волки: 25%\n"
            "🦊 Лиса: 15%\n"
            "🦫 Крот: 15%\n"
            "🦦 Бобёр: 10%\n"
            "🐰 Зайцы: 35% (автоматически)\n\n"
            "Выберите роль для изменения:",
            reply_markup=reply_markup
        )
    
    async def _handle_settings_players_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик настроек лимитов игроков"""
        # Проверяем права администратора
        if not await self._check_admin_permission(query, context):
            return
        
        chat_id = ChatId(query.message.chat_id)
        
        try:
            # Получаем настройки чата
            chat_settings = await self.bot_service.get_chat_settings(chat_id)
            
            keyboard = [
                [InlineKeyboardButton("👥 Минимум игроков", callback_data="players_min")],
                [InlineKeyboardButton("👥 Максимум игроков", callback_data="players_max")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"👥 **Настройки лимитов игроков**\n\n"
                f"Текущие значения:\n"
                f"👥 Минимум: {chat_settings.get('min_players', 6)} игроков\n"
                f"👥 Максимум: {chat_settings.get('max_players', 12)} игроков\n\n"
                f"Выберите, что хотите изменить:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа настроек игроков: {e}")
            await query.edit_message_text("❌ Ошибка показа настроек игроков")
    
    async def _handle_forest_settings_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик настроек лесной мафии"""
        # Проверяем права администратора
        if not await self._check_admin_permission(query, context):
            return
        
        keyboard = [
            [InlineKeyboardButton("🌙 Настройки ночи", callback_data="forest_night_settings")],
            [InlineKeyboardButton("🦊 Настройки лисы", callback_data="forest_fox_settings")],
            [InlineKeyboardButton("🦦 Настройки бобра", callback_data="forest_beaver_settings")],
            [InlineKeyboardButton("🦫 Настройки крота", callback_data="forest_mole_settings")],
            [InlineKeyboardButton("🏆 Настройки наград", callback_data="forest_rewards_settings")],
            [InlineKeyboardButton("💀 Настройки умерших", callback_data="forest_dead_settings")],
            [InlineKeyboardButton("⏰ Автозавершение", callback_data="forest_auto_end_settings")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🌲 **Настройки лесной мафии**\n\n"
            "Выберите категорию настроек:",
            reply_markup=reply_markup
        )
    
    async def _handle_toggle_test_mode_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик переключения быстрого режима"""
        # Проверяем права администратора
        if not await self._check_admin_permission(query, context):
            return
        
        chat_id = ChatId(query.message.chat_id)
        
        try:
            # Получаем текущие настройки
            chat_settings = await self.bot_service.get_chat_settings(chat_id)
            current_mode = chat_settings.get('test_mode', False)
            new_mode = not current_mode
            
            # Обновляем настройки
            await self.bot_service.update_chat_settings(chat_id, test_mode=new_mode)
            
            mode_text = "ВКЛ" if new_mode else "ВЫКЛ"
            min_players = 3 if new_mode else 6
            
            await query.answer(f"✅ Быстрый режим: {mode_text} (минимум: {min_players} игроков)", show_alert=True)
            
            # Обновляем сообщение
            await self._handle_settings_back_callback(query, params, context)
            
        except Exception as e:
            logger.error(f"Ошибка переключения быстрого режима: {e}")
            await query.edit_message_text("❌ Ошибка переключения быстрого режима")
    
    async def _handle_reset_chat_settings_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик сброса настроек чата"""
        # Проверяем права администратора
        if not await self._check_admin_permission(query, context):
            return
        
        chat_id = ChatId(query.message.chat_id)
        
        try:
            # Сбрасываем настройки к дефолтным
            await self.bot_service.reset_chat_settings(chat_id)
            
            await query.edit_message_text(
                "✅ **Настройки чата успешно сброшены к дефолтным значениям!**\n\n"
                "Все настройки восстановлены к стандартным значениям."
            )
            
        except Exception as e:
            logger.error(f"Ошибка сброса настроек чата: {e}")
            await query.edit_message_text("❌ Ошибка сброса настроек чата")
    
    async def _handle_close_settings_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик закрытия настроек"""
        await query.edit_message_text("⚙️ Настройки закрыты")
    
    # === ЯЗЫКОВЫЕ НАСТРОЙКИ ===
    
    async def _handle_language_settings_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик языковых настроек"""
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇺🇸 English (Coming Soon)", callback_data="lang_en_disabled")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🌍 **Язык / Language**\n\n"
            "Выберите язык интерфейса:",
            reply_markup=reply_markup
        )
    
    async def _handle_language_ru_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик выбора русского языка"""
        await query.answer("🇷🇺 Русский язык уже выбран!", show_alert=True)
    
    async def _handle_language_en_disabled_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик попытки выбрать английский язык (отключен)"""
        await query.answer("🇺🇸 Английский язык пока недоступен! Скоро будет добавлен.", show_alert=True)
    
    # === ПРОФИЛЬ В ЛС ===
    
    async def _handle_show_profile_pm_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик показа профиля в ЛС"""
        user_id = UserId(query.from_user.id)
        
        try:
            balance = await self.bot_service.get_user_balance(user_id)
            display_name = await self.bot_service.get_user_display_name(
                user_id, query.from_user.username, query.from_user.first_name
            )
            
            # Создаем клавиатуру профиля для ЛС
            keyboard = [
                [InlineKeyboardButton("🧺 Корзинка", callback_data="show_inventory")],
                [InlineKeyboardButton("📜 Свиток чести", callback_data="show_chat_stats")],
                [InlineKeyboardButton("🌰 Баланс", callback_data="show_balance")],
                [InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Формируем сообщение профиля
            profile_text = (
                f"👤 **Профиль игрока** 👤\n\n"
                f"🌲 **{display_name}**\n"
                f"🌰 Орешки: {balance}\n\n"
                f"🎮 Выберите действие:\n"
                f"🧺 **Корзинка** - ваш инвентарь\n"
                f"📜 **Свиток чести** - статистика в чатах\n"
                f"🌰 **Баланс** - подробная информация об орешках\n"
                f"🛍️ **Магазин** - покупка товаров"
            )
            
            await query.edit_message_text(profile_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка показа профиля в ЛС: {e}")
            await query.edit_message_text("❌ Ошибка показа профиля в ЛС")
    
    async def _handle_show_roles_pm_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик показа ролей в ЛС"""
        roles_text = (
            "🎭 **Роли в игре** 🎭\n\n"
            "🐺 **ХИЩНИКИ (Predators)**\n\n"
            "🐺 **Волк**\n"
            "• Убивает одного игрока каждую ночь\n"
            "• Цель: уничтожить всех травоядных\n"
            "• Может быть изгнан голосованием\n\n"
            "🦊 **Лиса**\n"
            "• Крадет орешки у игроков\n"
            "• Умирает после 2 краж\n"
            "• Помогает волкам\n\n"
            "🐰 **ТРАВОЯДНЫЕ (Herbivores)**\n\n"
            "🐰 **Зайец**\n"
            "• Обычный мирный житель\n"
            "• Может быть убит волком\n"
            "• Участвует в голосовании\n\n"
            "🦫 **Бобёр**\n"
            "• Защищает одного игрока за ночь\n"
            "• Может спасти от волка\n"
            "• Защита работает один раз\n\n"
            "🕳️ **Крот**\n"
            "• Проверяет роли игроков\n"
            "• Узнает, кто хищник, а кто нет\n"
            "• Помогает травоядным"
        )
        
        keyboard = [
            [InlineKeyboardButton("📖 Подробные правила", callback_data="show_rules_pm")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(roles_text, reply_markup=reply_markup)
    
    async def _handle_show_rules_pm_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик показа правил в ЛС"""
        rules_text = (
            "📖 **Подробные правила игры** 📖\n\n"
            "🌲 **Лес и Волки** - ролевая игра в стиле 'Мафия'\n\n"
            "🎯 **Цель игры:**\n"
            "• Хищники: уничтожить всех травоядных\n"
            "• Травоядные: найти и изгнать всех хищников\n\n"
            "🌙 **Ночная фаза:**\n"
            "• Волк выбирает жертву для убийства\n"
            "• Лиса крадет орешки у игрока\n"
            "• Бобёр защищает одного игрока\n"
            "• Крот проверяет роль игрока\n\n"
            "☀️ **Дневная фаза:**\n"
            "• Все игроки обсуждают события ночи\n"
            "• Голосование за изгнание подозреваемого\n"
            "• Изгнанный игрок покидает игру\n\n"
            "🎭 **Роли:**\n"
            "• **Волк** - убивает каждую ночь\n"
            "• **Лиса** - крадет орешки (умирает после 2 краж)\n"
            "• **Зайец** - обычный мирный житель\n"
            "• **Бобёр** - защищает игроков\n"
            "• **Крот** - проверяет роли\n\n"
            "🏆 **Победа:**\n"
            "• Хищники побеждают, если осталось равное количество\n"
            "• Травоядные побеждают, если изгнали всех хищников\n\n"
            "💡 **Советы:**\n"
            "• Внимательно слушайте других игроков\n"
            "• Анализируйте поведение и голосования\n"
            "• Не раскрывайте свою роль раньше времени"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎭 Роли", callback_data="show_roles_pm")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(rules_text, reply_markup=reply_markup)
    
    async def _handle_join_chat_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик входа в чат"""
        await query.edit_message_text(
            "🎮 **Войти в чат**\n\n"
            "Чтобы играть в Лес и волки, добавьте бота в групповой чат:\n\n"
            "1. Создайте групповой чат\n"
            "2. Добавьте бота в чат\n"
            "3. Дайте боту права администратора\n"
            "4. Напишите /start в чате\n\n"
            "🌲 Удачной игры!"
        )
    
    # === ОТМЕНА ДЕЙСТВИЙ ===
    
    async def _handle_cancel_action_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик отмены действия"""
        await query.edit_message_text("❌ Действие отменено")
    
    # === БЫСТРЫЙ РЕЖИМ ===
    
    async def _handle_toggle_quick_mode_game_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик переключения быстрого режима из игры"""
        # Проверяем права администратора
        if not await self._check_admin_permission(query, context):
            return
        
        chat_id = ChatId(query.message.chat_id)
        
        try:
            # Получаем текущие настройки
            chat_settings = await self.bot_service.get_chat_settings(chat_id)
            current_mode = chat_settings.get('test_mode', False)
            new_mode = not current_mode
            
            # Обновляем настройки
            await self.bot_service.update_chat_settings(chat_id, test_mode=new_mode)
            
            mode_text = "ВКЛ" if new_mode else "ВЫКЛ"
            min_players = 3 if new_mode else 6
            
            await query.answer(f"✅ Быстрый режим: {mode_text} (минимум: {min_players} игроков)", show_alert=True)
            
        except Exception as e:
            logger.error(f"Ошибка переключения быстрого режима из игры: {e}")
            await query.edit_message_text("❌ Ошибка переключения быстрого режима")
    
    # === ПРОЩАЛЬНЫЕ СООБЩЕНИЯ ===
    
    async def _handle_farewell_message_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик прощального сообщения"""
        if len(params) < 1:
            await query.edit_message_text("❌ Неверные параметры прощального сообщения")
            return
        
        user_id = int(params[0])
        
        keyboard = [
            [InlineKeyboardButton("💬 Кастомное сообщение", callback_data=f"farewell_custom_{user_id}")],
            [InlineKeyboardButton("🌲 Стандартное сообщение", callback_data=f"farewell_standard_{user_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data=f"farewell_back_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "💬 **Прощальное сообщение**\n\n"
            "Выберите тип прощального сообщения:",
            reply_markup=reply_markup
        )
    
    async def _handle_farewell_custom_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик кастомного прощального сообщения"""
        if len(params) < 1:
            await query.edit_message_text("❌ Неверные параметры кастомного прощального сообщения")
            return
        
        user_id = int(params[0])
        
        await query.edit_message_text(
            f"💬 **Кастомное прощальное сообщение**\n\n"
            f"Пользователь {user_id} покинул игру.\n"
            f"Можете написать свое прощальное сообщение в чат."
        )
    
    async def _handle_farewell_back_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик возврата от прощального сообщения"""
        if len(params) < 1:
            await query.edit_message_text("❌ Неверные параметры возврата от прощального сообщения")
            return
        
        user_id = int(params[0])
        
        await query.edit_message_text(
            f"👋 **Прощание с игроком**\n\n"
            f"Пользователь {user_id} покинул игру.\n"
            f"Выберите действие:"
        )
    
    async def _handle_leave_forest_callback(self, query: CallbackQuery, params: list, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик выхода из леса"""
        await query.edit_message_text(
            "🌲 **Выход из леса**\n\n"
            "Вы покинули игру Лес и волки.\n"
            "Спасибо за игру! 🌲"
        )
