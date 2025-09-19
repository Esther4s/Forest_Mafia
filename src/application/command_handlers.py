#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчики команд
Содержит логику обработки команд бота
"""

import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..domain.value_objects import ChatId, UserId, Username
from .bot_service import BotService

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Обработчики команд бота"""
    
    def __init__(self, bot_service: BotService):
        self.bot_service = bot_service
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        welcome_text = (
            "🌲 Добро пожаловать в Лес и волки Bot! 🌲\n\n"
            "Это бот для игры 'Лес и Волки' - увлекательной ролевой игры с лесной тематикой.\n\n"
            "🎮 **Как играть:**\n"
            "• Используйте /join для присоединения к игре\n"
            "• Администратор использует /start_game для начала\n"
            "• Играйте ролями: Волки, Лиса, Зайцы, Крот, Бобёр\n\n"
            "📋 **Доступные команды:**\n"
            "• /rules - правила игры\n"
            "• /join - присоединиться к игре\n"
            "• /leave - покинуть игру\n"
            "• /status - статус текущей игры\n"
            "• /stats - ваша статистика\n\n"
            "🌲 Удачной игры в лесу! 🌲"
        )
        
        await update.message.reply_text(welcome_text)
    
    async def handle_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /rules"""
        rules_text = (
            "🌲 **Правила игры 'Лес и Волки'** 🌲\n\n"
            "**🎭 Роли:**\n"
            "🐺 **Волки** - хищники, охотятся по ночам\n"
            "🦊 **Лиса** - хищник, ворует припасы\n"
            "🐰 **Зайцы** - травоядные, только дневные действия\n"
            "🦫 **Крот** - травоядный, проверяет роли\n"
            "🦦 **Бобёр** - травоядный, защищает и восстанавливает\n\n"
            "**🏆 Победа:**\n"
            "• Травоядные побеждают, если все хищники уничтожены\n"
            "• Хищники побеждают, если их количество >= травоядных\n\n"
            "**🌙 Ночные действия:**\n"
            "• Волки выбирают жертву для охоты\n"
            "• Лиса ворует припасы (2 кражи = смерть)\n"
            "• Крот проверяет роли других игроков\n"
            "• Бобёр защищает и восстанавливает припасы\n\n"
            "**☀️ Дневные действия:**\n"
            "• Обсуждение событий ночи (5 минут)\n"
            "• Голосование за изгнание (2 минуты)\n"
            "• Требуется большинство голосов для изгнания\n\n"
            "🌲 Удачной игры! 🌲"
        )
        
        await update.message.reply_text(rules_text)
    
    async def handle_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /join"""
        user = update.effective_user
        chat_id = ChatId(update.effective_chat.id)
        thread_id = update.effective_message.message_thread_id if update.effective_chat.is_forum else None
        
        user_id = UserId(user.id)
        username = Username(user.username or user.first_name or f"User_{user.id}")
        
        result = await self.bot_service.join_game(
            chat_id=chat_id,
            user_id=user_id,
            username=username.value,
            first_name=user.first_name,
            thread_id=thread_id
        )
        
        await update.message.reply_text(result["message"])
    
    async def handle_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /leave"""
        user = update.effective_user
        chat_id = ChatId(update.effective_chat.id)
        user_id = UserId(user.id)
        
        result = await self.bot_service.leave_game(chat_id, user_id)
        await update.message.reply_text(result["message"])
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /status"""
        chat_id = ChatId(update.effective_chat.id)
        result = await self.bot_service.get_game_status(chat_id)
        await update.message.reply_text(result["message"])
    
    async def handle_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /stats"""
        user = update.effective_user
        user_id = UserId(user.id)
        
        try:
            balance = await self.bot_service.get_user_balance(user_id)
            display_name = await self.bot_service.get_user_display_name(
                user_id, user.username, user.first_name
            )
            
            stats_text = (
                f"📊 **Статистика игрока** 📊\n\n"
                f"👤 Игрок: {display_name}\n"
                f"💰 Баланс: {balance} орехов\n\n"
                f"🌲 Удачной игры! 🌲"
            )
            
            await update.message.reply_text(stats_text)
        except Exception as e:
            logger.error(f"Ошибка получения статистики для пользователя {user.id}: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики.")


class AdminCommandHandlers:
    """Обработчики административных команд"""
    
    def __init__(self, bot_service: BotService):
        self.bot_service = bot_service
    
    async def handle_start_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start_game"""
        if not self._is_admin(update):
            await update.message.reply_text("❌ Только администраторы могут начинать игру.")
            return
        
        chat_id = ChatId(update.effective_chat.id)
        result = await self.bot_service.start_game(chat_id)
        await update.message.reply_text(result["message"])
        
        # Если игра успешно началась, отправляем роли игрокам
        if result["success"] and "game" in result:
            await self._send_roles_to_players(update, result["game"])
    
    async def handle_end_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /end_game"""
        if not self._is_admin(update):
            await update.message.reply_text("❌ Только администраторы могут завершать игру.")
            return
        
        chat_id = ChatId(update.effective_chat.id)
        result = await self.bot_service.end_game(chat_id)
        await update.message.reply_text(result["message"])
    
    async def _send_roles_to_players(self, update: Update, game) -> None:
        """Отправляет роли игрокам в личные сообщения"""
        for player in game.players.values():
            try:
                role_info = self._get_role_info(player.role)
                team_name = "🦁 Хищники" if player.team.value == "predators" else "🌿 Травоядные"
                
                role_message = (
                    f"🎭 **Ваша роль в игре:**\n\n"
                    f"👤 {role_info['name']}\n"
                    f"🏴 Команда: {team_name}\n\n"
                    f"📝 **Описание:**\n{role_info['description']}\n\n"
                    f"🌲 Удачной игры! 🌲"
                )
                
                await update.effective_chat.bot.send_message(
                    chat_id=player.user_id.value,
                    text=role_message
                )
            except Exception as e:
                logger.error(f"Не удалось отправить роль игроку {player.user_id.value}: {e}")
    
    def _get_role_info(self, role) -> Dict[str, str]:
        """Возвращает информацию о роли"""
        role_info = {
            "wolf": {
                "name": "🐺 Волк",
                "description": "Вы хищник! Вместе с другими волками вы охотитесь по ночам."
            },
            "fox": {
                "name": "🦊 Лиса",
                "description": "Вы хищник! Каждую ночь вы воруете запасы еды у других зверей."
            },
            "hare": {
                "name": "🐰 Заяц",
                "description": "Вы травоядный! Вы спите всю ночь и участвуете только в дневных обсуждениях."
            },
            "mole": {
                "name": "🦫 Крот",
                "description": "Вы травоядный! По ночам вы роете норки и узнаёте команды других зверей."
            },
            "beaver": {
                "name": "🦦 Бобёр",
                "description": "Вы травоядный! Вы можете возвращать украденные запасы другим зверям."
            }
        }
        return role_info.get(role.value, {"name": "Неизвестно", "description": "Роль не определена"})
    
    def _is_admin(self, update: Update) -> bool:
        """Проверяет, является ли пользователь администратором"""
        user = update.effective_user
        chat = update.effective_chat
        
        # Проверяем права администратора
        if chat.type in ['group', 'supergroup']:
            member = chat.get_member(user.id)
            return member.status in ['creator', 'administrator']
        
        return True  # В личных сообщениях считаем админом


class VotingHandlers:
    """Обработчики голосования"""
    
    def __init__(self, bot_service: BotService):
        self.bot_service = bot_service
    
    async def handle_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE, target_id: int = None) -> None:
        """Обработчик голосования"""
        user = update.effective_user
        chat_id = ChatId(update.effective_chat.id)
        user_id = UserId(user.id)
        target_user_id = UserId(target_id) if target_id else None
        
        result = await self.bot_service.vote(chat_id, user_id, target_user_id)
        await update.message.reply_text(result["message"])
    
    async def process_voting_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает результаты голосования"""
        chat_id = ChatId(update.effective_chat.id)
        result = await self.bot_service.process_voting(chat_id)
        await update.message.reply_text(result["message"])
