#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчики команд и сообщений для Лес и волки Bot
"""

import logging
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from game_logic import Game, GamePhase, Role, Team, Player
from config import config

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Обработчики команд бота"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def handle_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def handle_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /join"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        thread_id = update.effective_message.message_thread_id if update.effective_chat.is_forum else None
        
        # Проверяем авторизацию чата
        if not self.bot.is_chat_authorized(chat_id, thread_id):
            await update.message.reply_text("❌ Этот чат не авторизован для игры.")
            return
        
        # Получаем или создаем игру
        game = self.bot.get_or_create_game(chat_id, thread_id)
        
        # Проверяем, можно ли присоединиться
        if game.phase != GamePhase.WAITING:
            await update.message.reply_text("❌ Игра уже началась. Дождитесь следующей игры.")
            return
        
        # Добавляем игрока
        success = game.add_player(user.id, user.username or user.first_name)
        
        if success:
            player_count = len(game.players)
            min_players = config.min_players
            
            if player_count >= min_players:
                message = (
                    f"✅ {user.first_name} присоединился к игре!\n\n"
                    f"👥 Игроков: {player_count}/{config.max_players}\n"
                    f"🎮 Игра готова к началу! Администратор может использовать /start_game"
                )
            else:
                message = (
                    f"✅ {user.first_name} присоединился к игре!\n\n"
                    f"👥 Игроков: {player_count}/{config.max_players}\n"
                    f"⏳ Нужно еще {min_players - player_count} игроков для начала"
                )
            
            await update.message.reply_text(message)
        else:
            if user.id in game.players:
                await update.message.reply_text("❌ Вы уже в игре!")
            else:
                await update.message.reply_text("❌ Не удалось присоединиться к игре.")
    
    async def handle_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /leave"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        thread_id = update.effective_message.message_thread_id if update.effective_chat.is_forum else None
        
        game = self.bot.games.get(chat_id)
        if not game:
            await update.message.reply_text("❌ В этом чате нет активной игры.")
            return
        
        success = game.leave_game(user.id)
        
        if success:
            player_count = len(game.players)
            await update.message.reply_text(
                f"👋 {user.first_name} покинул игру.\n\n"
                f"👥 Игроков: {player_count}/{config.max_players}"
            )
        else:
            await update.message.reply_text("❌ Вы не можете покинуть игру сейчас.")
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        chat_id = update.effective_chat.id
        game = self.bot.games.get(chat_id)
        
        if not game:
            await update.message.reply_text("❌ В этом чате нет активной игры.")
            return
        
        status_text = self._format_game_status(game)
        await update.message.reply_text(status_text)
    
    def _format_game_status(self, game: Game) -> str:
        """Форматирует статус игры"""
        if game.phase == GamePhase.WAITING:
            player_count = len(game.players)
            min_players = config.min_players
            
            status = (
                f"🌲 **Статус игры** 🌲\n\n"
                f"📋 Фаза: Ожидание игроков\n"
                f"👥 Игроков: {player_count}/{config.max_players}\n"
                f"⏳ Нужно еще {min_players - player_count} игроков для начала\n\n"
                f"**Участники:**\n"
            )
            
            for player in game.players.values():
                status += f"• {player.username}\n"
            
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


class AdminHandlers:
    """Обработчики административных команд"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    async def handle_start_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start_game"""
        if not self._is_admin(update):
            await update.message.reply_text("❌ Только администраторы могут начинать игру.")
            return
        
        chat_id = update.effective_chat.id
        thread_id = update.effective_message.message_thread_id if update.effective_chat.is_forum else None
        
        game = self.bot.games.get(chat_id)
        if not game:
            await update.message.reply_text("❌ В этом чате нет активной игры.")
            return
        
        if not game.can_start_game():
            player_count = len(game.players)
            min_players = config.min_players
            await update.message.reply_text(
                f"❌ Недостаточно игроков для начала игры.\n"
                f"👥 Игроков: {player_count}/{config.max_players}\n"
                f"⏳ Нужно минимум {min_players} игроков"
            )
            return
        
        # Начинаем игру
        success = game.start_game()
        if success:
            await self._announce_game_start(update, game)
        else:
            await update.message.reply_text("❌ Не удалось начать игру.")
    
    async def handle_end_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /end_game"""
        if not self._is_admin(update):
            await update.message.reply_text("❌ Только администраторы могут завершать игру.")
            return
        
        chat_id = update.effective_chat.id
        game = self.bot.games.get(chat_id)
        
        if not game:
            await update.message.reply_text("❌ В этом чате нет активной игры.")
            return
        
        # Завершаем игру
        await self._end_game(update, game, "Администратор завершил игру")
    
    async def _announce_game_start(self, update: Update, game: Game):
        """Объявляет о начале игры"""
        start_message = (
            f"🌲 **ИГРА НАЧАЛАСЬ!** 🌲\n\n"
            f"👥 Игроков: {len(game.players)}\n"
            f"🎭 Роли распределены!\n"
            f"🌙 Начинается первая ночь...\n\n"
            f"Проверьте личные сообщения для информации о вашей роли!"
        )
        
        await update.message.reply_text(start_message)
        
        # Отправляем роли игрокам
        await self._send_roles_to_players(update, game)
    
    async def _send_roles_to_players(self, update: Update, game: Game):
        """Отправляет роли игрокам в личные сообщения"""
        for player in game.players.values():
            try:
                role_info = self._get_role_info(player.role)
                team_name = "🦁 Хищники" if player.team == Team.PREDATORS else "🌿 Травоядные"
                
                role_message = (
                    f"🎭 **Ваша роль в игре:**\n\n"
                    f"👤 {role_info['name']}\n"
                    f"🏴 Команда: {team_name}\n\n"
                    f"📝 **Описание:**\n{role_info['description']}\n\n"
                    f"🌲 Удачной игры! 🌲"
                )
                
                await update.effective_chat.bot.send_message(
                    chat_id=player.user_id,
                    text=role_message
                )
            except Exception as e:
                logger.error(f"Не удалось отправить роль игроку {player.user_id}: {e}")
    
    def _get_role_info(self, role: Role) -> Dict[str, str]:
        """Возвращает информацию о роли"""
        role_info = {
            Role.WOLF: {
                "name": "🐺 Волк",
                "description": "Вы хищник! Вместе с другими волками вы охотитесь по ночам."
            },
            Role.FOX: {
                "name": "🦊 Лиса",
                "description": "Вы хищник! Каждую ночь вы воруете запасы еды у других зверей."
            },
            Role.HARE: {
                "name": "🐰 Заяц",
                "description": "Вы травоядный! Вы спите всю ночь и участвуете только в дневных обсуждениях."
            },
            Role.MOLE: {
                "name": "🦫 Крот",
                "description": "Вы травоядный! По ночам вы роете норки и узнаёте команды других зверей."
            },
            Role.BEAVER: {
                "name": "🦦 Бобёр",
                "description": "Вы травоядный! Вы можете возвращать украденные запасы другим зверям."
            }
        }
        return role_info.get(role, {"name": "Неизвестно", "description": "Роль не определена"})
    
    async def _end_game(self, update: Update, game: Game, reason: str):
        """Завершает игру"""
        game.phase = GamePhase.GAME_OVER
        
        end_message = (
            f"🌲 **ИГРА ЗАВЕРШЕНА** 🌲\n\n"
            f"📋 Причина: {reason}\n"
            f"👥 Участников: {len(game.players)}\n"
            f"🎮 Раундов: {game.current_round}\n\n"
            f"Спасибо за игру! 🌲"
        )
        
        await update.message.reply_text(end_message)
        
        # Очищаем игру
        del self.bot.games[update.effective_chat.id]
    
    def _is_admin(self, update: Update) -> bool:
        """Проверяет, является ли пользователь администратором"""
        user = update.effective_user
        chat = update.effective_chat
        
        # Проверяем права администратора
        if chat.type in ['group', 'supergroup']:
            member = chat.get_member(user.id)
            return member.status in ['creator', 'administrator']
        
        return True  # В личных сообщениях считаем админом
