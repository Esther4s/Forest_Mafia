#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Интеграция системы лесов с основным ботом
Добавляет команды и обработчики для управления лесами
"""

import logging
from typing import Optional

from telegram import Update, Bot
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from forest_system import init_forest_manager, get_forest_manager, ForestManager
from forest_handlers import ForestCommandHandlers, ForestCallbackHandlers
from summon_system import init_summon_system, get_summon_system, SummonSystem
from database import init_database

logger = logging.getLogger(__name__)


class ForestIntegration:
    """Интеграция системы лесов с ботом"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.forest_manager: Optional[ForestManager] = None
        self.summon_system: Optional[SummonSystem] = None
        self.command_handlers: Optional[ForestCommandHandlers] = None
        self.callback_handlers: Optional[ForestCallbackHandlers] = None
    
    def initialize(self):
        """Инициализирует систему лесов"""
        try:
            # Инициализируем базу данных
            init_database()
            
            # Инициализируем менеджер лесов
            self.forest_manager = init_forest_manager(self.bot)
            
            # Инициализируем систему созыва
            self.summon_system = init_summon_system(self.bot)
            
            # Создаем обработчики
            self.command_handlers = ForestCommandHandlers(self.forest_manager)
            self.callback_handlers = ForestCallbackHandlers(self.forest_manager)
            
            logger.info("✅ Система лесов инициализирована успешно")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации системы лесов: {e}")
            return False
    
    def get_command_handlers(self):
        """Возвращает обработчики команд для системы лесов"""
        if not self.command_handlers:
            raise RuntimeError("Система лесов не инициализирована")
        
        return [
            # Команды создания и управления лесами
            CommandHandler("create_forest", self.command_handlers.handle_create_forest),
            CommandHandler("forests", self._handle_list_forests),
            CommandHandler("my_forests", self._handle_my_forests),
            
            # Динамические команды лесов (будут добавлены через regex)
            # /join_forest_*, /leave_forest_*, /summon_forest_*, /list_forest_*, /invite_forest_*
        ]
    
    def get_callback_handlers(self):
        """Возвращает обработчики callback-ов для системы лесов"""
        if not self.callback_handlers:
            raise RuntimeError("Система лесов не инициализирована")
        
        return [
            # Callback-ы для лесов
            CallbackQueryHandler(self.callback_handlers.handle_join_forest_callback, pattern="^join_forest_"),
            CallbackQueryHandler(self.callback_handlers.handle_forest_info_callback, pattern="^forest_info_"),
            CallbackQueryHandler(self.callback_handlers.handle_accept_invite_callback, pattern="^accept_invite_"),
            CallbackQueryHandler(self.callback_handlers.handle_decline_invite_callback, pattern="^decline_invite_"),
            CallbackQueryHandler(self.callback_handlers.handle_ask_info_callback, pattern="^ask_info_"),
        ]
    
    def get_dynamic_command_handlers(self):
        """Возвращает обработчики для динамических команд лесов"""
        if not self.command_handlers:
            raise RuntimeError("Система лесов не инициализирована")
        
        return [
            # Обработчики для команд с ID леса
            CommandHandler("join_forest", self._handle_dynamic_join_forest),
            CommandHandler("leave_forest", self._handle_dynamic_leave_forest),
            CommandHandler("summon_forest", self._handle_dynamic_summon_forest),
            CommandHandler("list_forest", self._handle_dynamic_list_forest),
            CommandHandler("invite_forest", self._handle_dynamic_invite_forest),
        ]
    
    async def _handle_list_forests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /forests - список всех лесов"""
        try:
            # Получаем список всех лесов из БД
            from database import get_db_session, Forest
            session = get_db_session()
            
            try:
                forests = session.query(Forest).all()
                
                if not forests:
                    await update.message.reply_text("🌲 Пока нет созданных лесов.")
                    return
                
                message = "🌲 **Доступные леса:** 🌲\n\n"
                
                for i, forest in enumerate(forests, 1):
                    # Получаем количество участников
                    member_count = len(forest.members)
                    max_count = forest.max_size or "∞"
                    
                    message += (
                        f"{i}. **{forest.name}**\n"
                        f"   📝 {forest.description}\n"
                        f"   👥 {member_count}/{max_count} участников\n"
                        f"   🔒 {'Приватный' if forest.privacy == 'private' else 'Публичный'}\n"
                        f"   🆔 ID: `{forest.id}`\n\n"
                    )
                
                message += "**Команды:**\n"
                message += "• /join_forest_<id> - присоединиться к лесу\n"
                message += "• /create_forest <название> <описание> - создать лес\n"
                message += "• /my_forests - мои леса"
                
                await update.message.reply_text(message, parse_mode='Markdown')
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Ошибка при получении списка лесов: {e}")
            await update.message.reply_text("❌ Ошибка при получении списка лесов.")
    
    async def _handle_my_forests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /my_forests - мои леса"""
        user = update.effective_user
        
        try:
            from database import get_db_session, Forest, ForestMember
            session = get_db_session()
            
            try:
                # Леса, созданные пользователем
                created_forests = session.query(Forest).filter(Forest.creator_id == user.id).all()
                
                # Леса, в которых состоит пользователь
                member_forests = session.query(Forest).join(ForestMember).filter(
                    ForestMember.user_id == user.id
                ).all()
                
                message = f"🌲 **Ваши леса, {user.first_name}:** 🌲\n\n"
                
                if created_forests:
                    message += "**🏗️ Созданные вами леса:**\n"
                    for forest in created_forests:
                        member_count = len(forest.members)
                        max_count = forest.max_size or "∞"
                        
                        message += (
                            f"• **{forest.name}** (ID: `{forest.id}`)\n"
                            f"  👥 {member_count}/{max_count} участников\n"
                            f"  📝 {forest.description}\n\n"
                        )
                
                if member_forests:
                    message += "**🌿 Леса, в которых вы состоите:**\n"
                    for forest in member_forests:
                        if forest.creator_id != user.id:  # Не дублируем созданные леса
                            member_count = len(forest.members)
                            max_count = forest.max_size or "∞"
                            
                            message += (
                                f"• **{forest.name}** (ID: `{forest.id}`)\n"
                                f"  👥 {member_count}/{max_count} участников\n"
                                f"  📝 {forest.description}\n\n"
                            )
                
                if not created_forests and not member_forests:
                    message += "Вы пока не создали лесов и не состоите ни в одном лесу.\n\n"
                    message += "**Создайте лес:**\n"
                    message += "• /create_forest <название> <описание>\n\n"
                    message += "**Или присоединитесь к существующему:**\n"
                    message += "• /forests - список всех лесов"
                
                await update.message.reply_text(message, parse_mode='Markdown')
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Ошибка при получении моих лесов: {e}")
            await update.message.reply_text("❌ Ошибка при получении ваших лесов.")
    
    async def _handle_dynamic_join_forest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик динамических команд присоединения к лесу"""
        # Извлекаем ID леса из команды
        command = update.message.text
        if not command.startswith('/join_forest_'):
            return
        
        forest_id_str = command.replace('/join_forest_', '')
        
        # Создаем временный контекст с forest_id
        temp_context = context
        temp_context.args = [forest_id_str]
        
        await self.command_handlers.handle_join_forest(update, temp_context)
    
    async def _handle_dynamic_leave_forest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик динамических команд покидания леса"""
        command = update.message.text
        if not command.startswith('/leave_forest_'):
            return
        
        forest_id_str = command.replace('/leave_forest_', '')
        temp_context = context
        temp_context.args = [forest_id_str]
        
        await self.command_handlers.handle_leave_forest(update, temp_context)
    
    async def _handle_dynamic_summon_forest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик динамических команд созыва леса"""
        command = update.message.text
        if not command.startswith('/summon_forest_'):
            return
        
        forest_id_str = command.replace('/summon_forest_', '')
        temp_context = context
        temp_context.args = [forest_id_str]
        
        await self.command_handlers.handle_summon_forest(update, temp_context)
    
    async def _handle_dynamic_list_forest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик динамических команд списка участников леса"""
        command = update.message.text
        if not command.startswith('/list_forest_'):
            return
        
        forest_id_str = command.replace('/list_forest_', '')
        temp_context = context
        temp_context.args = [forest_id_str]
        
        await self.command_handlers.handle_list_forest(update, temp_context)
    
    async def _handle_dynamic_invite_forest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик динамических команд приглашения в лес"""
        command = update.message.text
        if not command.startswith('/invite_forest_'):
            return
        
        forest_id_str = command.replace('/invite_forest_', '')
        temp_context = context
        temp_context.args = [forest_id_str] + (context.args or [])  # Добавляем ID леса к аргументам
        
        await self.command_handlers.handle_invite_forest(update, temp_context)
    
    def get_help_text(self) -> str:
        """Возвращает текст справки по командам лесов"""
        return (
            "🌲 **Команды системы лесов:** 🌲\n\n"
            "**Создание и управление:**\n"
            "• /create_forest <название> <описание> - создать лес\n"
            "• /forests - список всех лесов\n"
            "• /my_forests - мои леса\n\n"
            "**Участие в лесах:**\n"
            "• /join_forest_<id> - присоединиться к лесу\n"
            "• /leave_forest_<id> - покинуть лес\n"
            "• /list_forest_<id> - список участников леса\n"
            "• /summon_forest_<id> - созвать участников леса\n"
            "• /invite_forest_<id> @username - пригласить в лес\n\n"
            "**Примеры:**\n"
            "• /create_forest Лес Волков Еженедельные игры\n"
            "• /join_forest_les_volkov\n"
            "• /summon_forest_les_volkov\n\n"
            "**Примечание:** ID леса можно найти в списке лесов (/forests)"
        )


# Глобальный экземпляр интеграции
forest_integration: Optional[ForestIntegration] = None

def init_forest_integration(bot: Bot) -> ForestIntegration:
    """Инициализирует интеграцию системы лесов"""
    global forest_integration
    forest_integration = ForestIntegration(bot)
    forest_integration.initialize()
    return forest_integration

def get_forest_integration() -> ForestIntegration:
    """Получает экземпляр интеграции системы лесов"""
    if forest_integration is None:
        raise RuntimeError("Интеграция системы лесов не инициализирована")
    return forest_integration
