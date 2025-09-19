#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Расширенная интеграция системы лесов с профилями
Включает все функции профилей, аналитики и статистики
"""

import logging
from typing import Optional

from telegram import Update, Bot
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from forest_system import init_forest_manager, get_forest_manager, ForestManager
from forest_profiles import init_forest_profile_manager, get_forest_profile_manager, ForestProfileManager
from forest_analytics import init_forest_analytics_manager, get_forest_analytics_manager, ForestAnalyticsManager
from user_forest_profile import init_user_forest_profile_manager, get_user_forest_profile_manager, UserForestProfileManager
from forest_profile_handlers import init_extended_forest_profile_handlers, get_extended_forest_profile_handlers, ExtendedForestProfileHandlers
from database import init_database

logger = logging.getLogger(__name__)


class EnhancedForestIntegration:
    """Расширенная интеграция системы лесов с профилями"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.forest_manager: Optional[ForestManager] = None
        self.forest_profile_manager: Optional[ForestProfileManager] = None
        self.forest_analytics_manager: Optional[ForestAnalyticsManager] = None
        self.user_forest_profile_manager: Optional[UserForestProfileManager] = None
        self.extended_handlers: Optional[ExtendedForestProfileHandlers] = None
    
    def initialize(self):
        """Инициализирует расширенную систему лесов"""
        try:
            # Инициализируем базу данных
            init_database()
            
            # Инициализируем основные компоненты
            self.forest_manager = init_forest_manager(self.bot)
            self.forest_profile_manager = init_forest_profile_manager(self.forest_manager)
            self.forest_analytics_manager = init_forest_analytics_manager(self.forest_manager)
            self.user_forest_profile_manager = init_user_forest_profile_manager(
                self.forest_manager, 
                self.forest_profile_manager, 
                self.forest_analytics_manager
            )
            
            # Инициализируем расширенные обработчики
            self.extended_handlers = init_extended_forest_profile_handlers()
            
            logger.info("✅ Расширенная система лесов инициализирована успешно")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации расширенной системы лесов: {e}")
            return False
    
    def get_command_handlers(self):
        """Возвращает все обработчики команд"""
        if not self.extended_handlers:
            raise RuntimeError("Расширенная система лесов не инициализирована")
        
        return self.extended_handlers.get_command_handlers()
    
    def get_callback_handlers(self):
        """Возвращает все обработчики callback-ов"""
        if not self.extended_handlers:
            raise RuntimeError("Расширенная система лесов не инициализирована")
        
        return self.extended_handlers.get_callback_handlers()
    
    def get_help_text(self) -> str:
        """Возвращает расширенную справку по командам"""
        return (
            "🌲 **Расширенная система лесов** 🌲\n\n"
            "**🏗️ Создание и управление лесами:**\n"
            "• /create_forest <название> <описание> - создать лес\n"
            "• /forests - список всех лесов\n"
            "• /my_forests_profile - мои леса с детальной информацией\n\n"
            "**👤 Профили пользователей:**\n"
            "• /profile - полный профиль с лесами\n"
            "• /profile_compact - компактный профиль\n"
            "• /user_forest_stats - лесная статистика пользователя\n\n"
            "**🌲 Профили лесов:**\n"
            "• /forest_profile <ID> - профиль леса\n"
            "• /forest_stats <ID> - статистика леса\n"
            "• /forest_analytics <ID> - аналитика леса\n"
            "• /forest_ranking <ID> - рейтинг участников леса\n\n"
            "**📊 Аналитика и рейтинги:**\n"
            "• /top_forests - топ лесов по вовлеченности\n"
            "• /forest_comparison <ID1> <ID2> - сравнение лесов\n"
            "• /forest_members_ranking <ID> - рейтинг участников\n\n"
            "**🎮 Участие в лесах:**\n"
            "• /join_forest_<id> - присоединиться к лесу\n"
            "• /leave_forest_<id> - покинуть лес\n"
            "• /summon_forest_<id> - созвать участников\n"
            "• /list_forest_<id> - список участников\n"
            "• /invite_forest_<id> @username - пригласить в лес\n\n"
            "**💡 Примеры:**\n"
            "• /create_forest Лес Волков Еженедельные игры --max 20\n"
            "• /forest_profile les_i_volki\n"
            "• /profile\n"
            "• /top_forests"
        )
    
    def get_forest_commands_summary(self) -> str:
        """Возвращает краткую сводку команд лесов"""
        return (
            "🌲 **Команды лесов:**\n"
            "• /create_forest - создать лес\n"
            "• /forests - список лесов\n"
            "• /profile - мой профиль\n"
            "• /forest_profile <ID> - профиль леса\n"
            "• /top_forests - топ лесов\n"
            "• /help_forests - полная справка"
        )


# Глобальный экземпляр расширенной интеграции
enhanced_forest_integration: Optional[EnhancedForestIntegration] = None

def init_enhanced_forest_integration(bot: Bot) -> EnhancedForestIntegration:
    """Инициализирует расширенную интеграцию системы лесов"""
    global enhanced_forest_integration
    enhanced_forest_integration = EnhancedForestIntegration(bot)
    enhanced_forest_integration.initialize()
    return enhanced_forest_integration

def get_enhanced_forest_integration() -> EnhancedForestIntegration:
    """Получает экземпляр расширенной интеграции системы лесов"""
    if enhanced_forest_integration is None:
        raise RuntimeError("Расширенная интеграция системы лесов не инициализирована")
    return enhanced_forest_integration
