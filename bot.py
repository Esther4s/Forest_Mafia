#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ContextTypes
)

from game_logic import Game, GamePhase, Role, Team  # ваши реализации
from config import BOT_TOKEN  # ваши настройки
from night_actions import NightActions
from night_interface import NightInterface
from global_settings import GlobalSettings # Импортируем GlobalSettings
from database_adapter import DatabaseAdapter

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ForestWolvesBot:
    def __init__(self):
        # chat_id -> Game
        self.games: Dict[int, Game] = {}
        # user_id -> chat_id
        self.player_games: Dict[int, int] = {}
        # chat_id -> NightActions
        self.night_actions: Dict[int, NightActions] = {}
        # chat_id -> NightInterface
        self.night_interfaces: Dict[int, NightInterface] = {}
        # Global settings instance
        self.global_settings = GlobalSettings()
        # Список разрешенных чатов и тем (chat_id, thread_id или None для всего чата)
        self.authorized_chats: set = set()  # Хранит кортежи (chat_id, thread_id)
        # Bot token
        self.bot_token = BOT_TOKEN
        # Database adapter
        self.db = DatabaseAdapter()
        
        # Загружаем активные игры из базы данных
        self.load_active_games()

    def load_active_games(self):
        """Загружает активные игры из базы данных при старте бота"""
        try:
            # Получаем все активные игры из БД
            active_games = self.db.get_all_active_games()
            
            for game_data in active_games:
                chat_id = game_data['chat_id']
                thread_id = game_data.get('thread_id')
                
                # Создаем объект игры
                game = Game()
                game.chat_id = chat_id
                game.thread_id = thread_id
                game.db_game_id = game_data['id']
                game.phase = GamePhase(game_data['phase'])
                game.current_round = game_data.get('round_number', 0)
                game.status = game_data.get('status', 'active')
                
                # Загружаем игроков
                players_data = self.db.get_game_players(game_data['id'])
                for player_data in players_data:
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
                    
                    game.players[player.user_id] = player
                    self.player_games[player.user_id] = chat_id
                
                # Сохраняем игру в памяти
                self.games[chat_id] = game
                
                logger.info(f"Загружена активная игра {game_data['id']} для чата {chat_id}")
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке активных игр: {e}")

    # ---------------- helper functions ----------------
    async def can_bot_write_in_chat(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> bool:
        """Проверяет, может ли бот писать в данном чате"""
        try:
            # Получаем информацию о боте в чате
            if not context.bot or not context.bot.id:
                return False
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            
            # Проверяем статус бота
            if bot_member.status in ['administrator', 'creator']:
                return True
            elif bot_member.status == 'member':
                # Для обычных групп проверяем права на отправку сообщений
                chat = await context.bot.get_chat(chat_id)
                if chat.type == 'private':
                    return True
                # В группах обычно члены могут писать, если не ограничено
                return True
            else:
                # kicked, left, restricted
                return False
        except Exception as e:
            logger.warning(f"Не удалось проверить права бота в чате {chat_id}: {e}")
            return False

    def get_thread_id(self, update: Update) -> Optional[int]:
        """Получает thread_id из сообщения или callback query"""
        if hasattr(update, 'message') and update.message:
            return getattr(update.message, 'message_thread_id', None)
        elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
            return getattr(update.callback_query.message, 'message_thread_id', None)
        return None

    def is_chat_authorized(self, chat_id: int, thread_id: Optional[int] = None) -> bool:
        """Проверяет, авторизован ли чат/тема для игры"""
        # Проверяем точное совпадение (chat_id, thread_id)
        if (chat_id, thread_id) in self.authorized_chats:
            return True
        # Проверяем авторизацию всего чата (для обратной совместимости)
        if (chat_id, None) in self.authorized_chats and thread_id is None:
            return True
        return False

    def authorize_chat(self, chat_id: int, thread_id: Optional[int] = None):
        """Авторизует чат/тему для игры"""
        self.authorized_chats.add((chat_id, thread_id))
        if thread_id:
            logger.info(f"Автоматически авторизован чат {chat_id}, тема {thread_id} для игры")
        else:
            logger.info(f"Автоматически авторизован чат {chat_id} для игры")

    async def check_bot_permissions_decorator(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверяет права бота и авторизацию чата перед выполнением команды"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        thread_id = self.get_thread_id(update)
        
        # ВСЕГДА разрешаем личные сообщения (необходимо для игры!)
        if chat_id == user_id:
            return True
        
        # Проверяем права бота на запись
        if not await self.can_bot_write_in_chat(context, chat_id):
            logger.info(f"Бот не может писать в чате {chat_id}, игнорируем команду")
            return False
        
        # Разрешаем команды /setup_channel и /remove_channel для настройки чатов
        if hasattr(update, 'message') and update.message and update.message.text:
            if update.message.text.startswith('/setup_channel') or update.message.text.startswith('/remove_channel'):
                return True
        
        # Автоматически авторизуем чат/тему при первой игровой команде
        game_commands = ['/join', '/start_game', '/status', '/rules', '/settings', '/end_game', '/end',
                        '/force_end', '/help', '/version', '/test_mode', '/min_players']
        
        if hasattr(update, 'message') and update.message and update.message.text:
            for cmd in game_commands:
                if update.message.text.startswith(cmd):
                    # Автоматически добавляем чат/тему в авторизованные если еще не добавлен
                    if not self.is_chat_authorized(chat_id, thread_id):
                        self.authorize_chat(chat_id, thread_id)
                    return True
        
        # Для callback query (нажатия кнопок) тоже разрешаем и авторизуем
        if hasattr(update, 'callback_query') and update.callback_query:
            if not self.is_chat_authorized(chat_id, thread_id):
                self.authorize_chat(chat_id, thread_id)
                if thread_id:
                    logger.info(f"Тема {thread_id} в чате {chat_id} автоматически авторизована для callback")
                else:
                    logger.info(f"Групповой чат {chat_id} автоматически авторизован для callback")
            return True
        
        # Проверяем, авторизован ли чат/тема
        if not self.is_chat_authorized(chat_id, thread_id):
            # Автоматически авторизуем чат при первом обращении
            self.authorize_chat(chat_id, thread_id)
            if thread_id:
                logger.info(f"Тема {thread_id} в чате {chat_id} автоматически авторизована для игры")
            else:
                logger.info(f"Групповой чат {chat_id} автоматически авторизован для игры")
        
        return True

    # ---------------- helper functions for game logic ----------------
    def format_player_tag(self, username: str, user_id: int) -> str:
        """Форматирует тег игрока для отображения"""
        if username and not username.isdigit():
            # Если username есть и это не просто ID
            return f"@{username}" if not username.startswith('@') else username
        else:
            # Если username нет или это ID, используем ID
            return f"ID:{user_id}"

    async def _join_game_common(self, chat_id: int, user_id: int, username: str, context: ContextTypes.DEFAULT_TYPE, 
                               is_callback: bool = False, update: Update = None) -> tuple[bool, str, any]:
        """
        Общая логика присоединения к игре
        Возвращает: (success, message, reply_markup)
        """
        # Проверяем, что это группа, а не личные сообщения
        if chat_id == user_id:
            return False, "❌ Игра доступна только в группах! Добавьте бота в группу и попробуйте там.", None

        # already in another game?
        if user_id in self.player_games:
            other_chat = self.player_games[user_id]
            if other_chat != chat_id:
                try:
                    other_chat_info = await context.bot.get_chat(other_chat)
                    chat_name = other_chat_info.title or f"Чат {other_chat}"
                except:
                    chat_name = f"Чат {other_chat}"
                return False, f"❌ Вы уже участвуете в игре в другом чате!\nЧат: {chat_name}", None
            else:
                # Игрок уже в этой игре - показываем статус
                game = self.games[chat_id]
                max_players = getattr(game, "MAX_PLAYERS", 12)
                
                keyboard = [[InlineKeyboardButton("🎮 Присоединиться", callback_data="join_game")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                message = f"ℹ️ Вы уже участвуете в этой игре!\nИгроков: {len(game.players)}/{max_players}"
                return False, message, reply_markup

        # create game if needed
        if chat_id not in self.games:
            thread_id = self.get_thread_id(update)
            self.games[chat_id] = Game(chat_id, thread_id)
            self.games[chat_id].is_test_mode = self.global_settings.is_test_mode()
            self.night_actions[chat_id] = NightActions(self.games[chat_id])
            self.night_interfaces[chat_id] = NightInterface(self.games[chat_id], self.night_actions[chat_id])

        game = self.games[chat_id]

        if game.phase != GamePhase.WAITING:
            return False, "❌ Игра уже идёт! Дождитесь её окончания.", None

        if game.add_player(user_id, username):
            self.player_games[user_id] = chat_id
            max_players = getattr(game, "MAX_PLAYERS", 12)
            
            # Создаем улучшенную клавиатуру с новыми функциями
            keyboard = []
            
            # Кнопка "Присоединиться" - всегда первая
            keyboard.append([InlineKeyboardButton("✅ Присоединиться", callback_data="join_game")])
            
            # Кнопка "Выйти из регистрации"
            keyboard.append([InlineKeyboardButton("❌ Выйти из регистрации", callback_data="leave_registration")])
            
            # Кнопка "Посмотреть свою роль" (скрывает ссылку на ЛС с ботом)
            if game.phase != GamePhase.WAITING:
                bot_username = context.bot.username
                keyboard.append([InlineKeyboardButton("👁️ Посмотреть свою роль", url=f"https://t.me/{bot_username}?start=role")])
            
            # Кнопка "Начать игру" (если можно)
            if game.can_start_game():
                keyboard.append([InlineKeyboardButton("🚀 Начать игру", callback_data="start_game")])
            
            # Кнопка "Отменить игру" (только для админов)
            if await self.is_user_admin(update, context):
                keyboard.append([InlineKeyboardButton("🛑 Отменить игру", callback_data="cancel_game")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Форматируем список игроков с тегами
            players_list = ""
            for player in game.players.values():
                player_tag = self.format_player_tag(player.username, player.user_id)
                players_list += f"• {player_tag}\n"
            
            message = (
                f"✅ {self.format_player_tag(username, user_id)} присоединился к игре!\n\n"
                f"👥 Игроков: {len(game.players)}/{max_players}\n"
                f"📋 Минимум для старта: {self.global_settings.get_min_players()}\n\n"
                f"📝 Участники:\n{players_list}"
            )
            
            if game.can_start_game():
                message += "\n✅ Можно начинать игру! Используйте `/start_game`"
            else:
                message += f"\n⏳ Нужно ещё {max(0, self.global_settings.get_min_players() - len(game.players))} игроков"
            
            return True, message, reply_markup
        else:
            return False, "❌ Не удалось присоединиться к игре!", None

    # ---------------- basic commands ----------------
    async def welcome_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        keyboard = [
            [InlineKeyboardButton("🚀 Начать игру", callback_data="welcome_start_game")],
            [InlineKeyboardButton("📖 Правила", callback_data="welcome_rules")],
            [InlineKeyboardButton("📊 Статус", callback_data="welcome_status")],
            [InlineKeyboardButton("🔍 Проверить этап", callback_data="check_stage")],
            [InlineKeyboardButton("🛑 Отменить игру", callback_data="welcome_cancel_game")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = (
            "🌲 *Лес и Волки* - ролевая игра в стиле 'Мафия'!\n\n"
            "🐺 *Хищники:* Волки + Лиса\n"
            "🐰 *Травоядные:* Зайцы + Крот + Бобёр\n\n"
            f"👥 Минимум: {self.global_settings.get_min_players()} игроков\n"
            f"{'🧪 ТЕСТОВЫЙ РЕЖИМ' if self.global_settings.is_test_mode() else ''}\n\n"
            "🚀 *Быстрый старт:* нажмите 'Начать игру' или используйте `/join`"
        )

        # Отправляем приветственное сообщение (без закрепления для быстрого доступа)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        rules_text = (
            "🌲 *ПОЛНЫЕ ПРАВИЛА ИГРЫ 'Лес и Волки'* 🌲\n\n"
            "🎭 *Что это такое?*\n"
            "Ролевая игра в стиле 'Мафия' с лесными зверушками. Две команды сражаются за выживание в лесу!\n\n"
            "👥 *Команды:*\n\n"
            "🐺 *ХИЩНИКИ (меньшинство):*\n"
            "• **Волки** - стая хищников, съедают по зверю каждую ночь (кроме первой ночи)\n"
            "• **Лиса** - хитрая воровка, крадет запасы еды у травоядных\n\n"
            "🐰 *ТРАВОЯДНЫЕ (большинство):*\n"
            "• **Зайцы** - мирные зверушки, не имеют ночных способностей\n"
            "• **Крот** - роет норки, каждую ночь может проверить любого игрока и узнать его роль\n"
            "• **Бобёр** - помогает травоядным, может восстановить украденные запасы\n\n"
            "⏰ *ФАЗЫ ИГРЫ:*\n\n"
            "🌙 *НОЧЬ (60 секунд):*\n"
            "• Волки выбирают жертву для съедения\n"
            "• Лиса выбирает цель для кражи запасов\n"
            "• Бобёр может помочь пострадавшему от лисы\n"
            "• Крот проверяет любого игрока\n"
            "• Зайцы спят\n\n"
            "☀️ *ДЕНЬ (5 минут):*\n"
            "• Обсуждение событий ночи\n"
            "• Планирование стратегии\n"
            "• Обмен информацией\n"
            "• Подозрения и обвинения\n\n"
            "🗳️ *ГОЛОСОВАНИЕ (2 минуты):*\n"
            "• Голосование за изгнание подозрительного игрока\n"
            "• Игрок с наибольшим количеством голосов изгоняется\n"
            "• При ничьей никто не изгоняется\n\n"
            "🎯 *ЦЕЛИ КОМАНД:*\n\n"
            "🐺 *Хищники побеждают, если:*\n"
            "• Количество хищников становится равным или больше количества травоядных\n"
            "• Все травоядные уничтожены\n\n"
            "🐰 *Травоядные побеждают, если:*\n"
            "• Все хищники изгнаны или убиты\n"
            "• Волки полностью уничтожены\n\n"
            "🛡️ *СПЕЦИАЛЬНЫЕ МЕХАНИКИ:*\n\n"
            "🦊 *Лиса:*\n"
            "• Ворует запасы у травоядных (кроме бобра)\n"
            "• Игрок умирает после 2 краж подряд\n"
            "• Не может воровать у волков (союзники)\n\n"
            "🦦 *Бобёр:*\n"
            "• Может помочь любому, у кого украли запасы\n"
            "• Полностью восстанавливает украденные запасы\n"
            "• Защищает от смерти от кражи лисы\n\n"
            "🦫 *Крот:*\n"
            "• Может проверить любого игрока каждую ночь\n"
            "• Узнает точную роль игрока\n"
            "• Видит, действовал ли игрок этой ночью\n\n"
            "🐺 *Волки:*\n"
            "• Не действуют в первую ночь\n"
            "• Не могут есть лису (союзники)\n"
            "• Не могут есть друг друга\n\n"
            "⚡ *АВТОМАТИЧЕСКОЕ ЗАВЕРШЕНИЕ:*\n"
            "• Если остается менее 3 игроков\n"
            "• Если игра длится более 3 часов\n"
            "• Если сыграно более 25 раундов\n\n"
            "🎮 *КАК ИГРАТЬ:*\n"
            "1. Используйте `/start` для начала регистрации\n"
            "2. Нажмите 'Присоединиться к игре'\n"
            "3. Дождитесь начала игры (минимум 6 игроков)\n"
            "4. Получите роль в личных сообщениях\n"
            "5. Следуйте инструкциям бота\n\n"
            "💡 *СОВЕТЫ:*\n"
            "• Доверяйте, но проверяйте\n"
            "• Анализируйте поведение других игроков\n"
            "• Используйте информацию от крота\n"
            "• Защищайте важных игроков\n"
            "• Не раскрывайте свою роль без необходимости\n\n"
            "🔧 *КОМАНДЫ:*\n"
            "• `/start` - начать регистрацию\n"
            "• `/join` - присоединиться к игре\n"
            "• `/leave` - покинуть игру\n"
            "• `/status` - статус игры\n"
            "• `/rules` - эти правила\n"
            "• `/help` - помощь\n\n"
            "🎉 *Удачной игры!*"
        )
        await update.message.reply_text(rules_text, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        help_text = (
            "🆘 *Быстрая справка по игре*\n\n"
            "🚀 *Быстрый старт:*\n"
            "• `/join` - присоединиться к игре\n"
            "• `/start_game` - начать игру\n"
            "• `/status` - статус игры\n\n"
            "🎭 *Роли:*\n"
            "🐺 Волки - едят по ночам\n"
            "🦊 Лиса - ворует запасы\n"
            "🐰 Зайцы - мирные жители\n"
            "🦫 Крот - проверяет команды\n"
            "🦦 Бобёр - защищает от лисы\n\n"
            "⏰ *Фазы игры:*\n"
            "🌙 Ночь (60 сек) - ночные действия\n"
            "☀️ День (5 мин) - обсуждение\n"
            "🗳️ Голосование (2 мин) - изгнание\n\n"
            "🏆 *Победа:* уничтожить команду противника\n\n"
            "💡 *Команды:* /rules, /help, /stats, /settings"
        )
        await update.message.reply_text(help_text)

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику игрока или топ игроков"""
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
        
        user_id = update.effective_user.id
        
        # Если есть аргументы, показываем топ игроков
        if context.args and context.args[0] == "top":
            top_players = self.db.get_top_players(10, "games_won")
            
            if not top_players:
                await update.message.reply_text("📊 Статистика пока пуста. Сыграйте несколько игр!")
                return
            
            stats_text = "🏆 *Топ игроков по победам:*\n\n"
            for i, player in enumerate(top_players, 1):
                username = player["username"] or f"Игрок {player['user_id']}"
                win_rate = (player["games_won"] / max(player["total_games"], 1)) * 100
                stats_text += f"{i}. {username}\n"
                stats_text += f"   🎮 Игр: {player['total_games']} | 🏆 Побед: {player['games_won']} ({win_rate:.1f}%)\n"
                stats_text += f"   🐺 Волк: {player['times_wolf']} | 🦊 Лиса: {player['times_fox']} | 🐰 Заяц: {player['times_hare']}\n\n"
            
            await update.message.reply_text(stats_text)
        else:
            # Показываем статистику текущего игрока
            stats = self.db.get_player_stats(user_id)
            
            if stats["total_games"] == 0:
                await update.message.reply_text("📊 У вас пока нет игр. Присоединяйтесь к игре командой /join!")
                return
            
            win_rate = (stats["games_won"] / stats["total_games"]) * 100
            
            stats_text = f"📊 *Ваша статистика:*\n\n"
            stats_text += f"🎮 Всего игр: {stats['total_games']}\n"
            stats_text += f"🏆 Побед: {stats['games_won']} ({win_rate:.1f}%)\n"
            stats_text += f"💀 Поражений: {stats['games_lost']}\n\n"
            stats_text += f"🎭 *Роли:*\n"
            stats_text += f"🐺 Волк: {stats['times_wolf']}\n"
            stats_text += f"🦊 Лиса: {stats['times_fox']}\n"
            stats_text += f"🐰 Заяц: {stats['times_hare']}\n"
            stats_text += f"🦫 Крот: {stats['times_mole']}\n"
            stats_text += f"🦦 Бобёр: {stats['times_beaver']}\n\n"
            stats_text += f"⚔️ Убийств: {stats['kills_made']}\n"
            stats_text += f"🗳️ Голосов против: {stats['votes_received']}\n\n"
            
            if stats["last_played"]:
                stats_text += f"🕐 Последняя игра: {stats['last_played'].strftime('%d.%m.%Y %H:%M')}"
            
            await update.message.reply_text(stats_text)

    # ---------------- новые улучшенные методы ----------------
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /start с различными параметрами"""
        if not update or not update.message:
            return
        
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем параметры команды
        if context.args and context.args[0] == "role":
            # Показываем роль игрока
            await self.show_role_in_private(update, context)
        else:
            # Начинаем регистрацию в игру
            await self.start_registration(update, context)

    async def start_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начинает регистрацию игроков в игру"""
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        # Для личных сообщений отправляем информацию о том, как начать игру
        if chat_id == user_id:
            await update.message.reply_text(
                "🌲 *Добро пожаловать в 'Лес и Волки'!* 🌲\n\n"
                "🎭 *Ролевая игра в стиле 'Мафия' с лесными зверушками*\n\n"
                "🐺 *Хищники:* Волки + Лиса\n"
                "🐰 *Травоядные:* Зайцы + Крот + Бобёр\n\n"
                "🌙 *Как играть:*\n"
                "• Ночью хищники охотятся, травоядные защищаются\n"
                "• Днем все обсуждают и голосуют за изгнание\n"
                "• Цель: уничтожить всех противников\n\n"
                "🚀 *Чтобы начать игру:*\n"
                "1. Добавьте бота в группу\n"
                "2. Используйте команду /start в группе\n"
                "3. Или нажмите кнопку 'Начать игру' в приветственном сообщении\n\n"
                "💡 *Команды:* `/rules`, `/help`, `/settings`"
            )
            return

        # Создаем игру, если её нет
        if chat_id not in self.games:
            self.games[chat_id] = Game(chat_id=chat_id, thread_id=update.effective_message.message_thread_id)
            self.night_actions[chat_id] = NightActions(self.games[chat_id])
            self.night_interfaces[chat_id] = NightInterface(self.games[chat_id], self.night_actions[chat_id])

        game = self.games[chat_id]

        # Проверяем, что игра в режиме ожидания
        if game.phase != GamePhase.WAITING:
            await update.message.reply_text("❌ Игра уже идет! Дождитесь окончания текущей игры.")
            return

        # Создаем клавиатуру для регистрации
        keyboard = [
            [InlineKeyboardButton("✅ Присоединиться к игре", callback_data="welcome_start_game")],
            [InlineKeyboardButton("📖 Правила игры", callback_data="welcome_rules")],
            [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")],
            [InlineKeyboardButton("🔍 Проверить этап", callback_data="check_stage")]
        ]
        
        # Добавляем кнопку "Начать игру" если достаточно игроков
        if game.can_start_game():
            keyboard.append([InlineKeyboardButton("🚀 Начать игру", callback_data="start_game")])
        
        # Добавляем кнопку "Отменить игру" для администраторов
        if await self.is_user_admin(update, context):
            keyboard.append([InlineKeyboardButton("🛑 Отменить игру", callback_data="cancel_game")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Формируем сообщение о регистрации
        min_players = self.global_settings.get_min_players()
        current_players = len(game.players)
        
        registration_text = (
            "🌲 *Регистрация в игру 'Лес и Волки'* 🌲\n\n"
            "🎭 *Ролевая игра в стиле 'Мафия' с лесными зверушками*\n\n"
            "🐺 *Хищники:* Волки + Лиса\n"
            "🐰 *Травоядные:* Зайцы + Крот + Бобёр\n\n"
            f"👥 *Игроков зарегистрировано:* {current_players}\n"
            f"📋 *Минимум для начала:* {min_players}\n"
            f"{'🧪 *ТЕСТОВЫЙ РЕЖИМ*' if self.global_settings.is_test_mode() else ''}\n\n"
            "🎯 *Цель:* Уничтожить команду противника!\n\n"
            "🚀 *Нажмите 'Присоединиться к игре' для участия!*"
        )

        await update.message.reply_text(
            registration_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def is_user_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Проверяет, является ли пользователь администратором чата"""
        try:
            # Получаем chat_id в зависимости от типа update
            if hasattr(update, 'effective_chat') and update.effective_chat:
                chat_id = update.effective_chat.id
            elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                chat_id = update.callback_query.message.chat.id
            else:
                return False
                
            user_id = update.effective_user.id
            
            # В личных сообщениях считаем пользователя админом
            if chat_id == user_id:
                return True
            
            # Проверяем права в группе
            member = await context.bot.get_chat_member(chat_id, user_id)
            return member.status in ['creator', 'administrator']
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False

    async def show_role_in_private(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает роль игрока в личных сообщениях"""
        user_id = update.effective_user.id
        
        if user_id not in self.player_games:
            await update.message.reply_text("❌ Вы не участвуете в игре!")
            return
        
        chat_id = self.player_games[user_id]
        if chat_id not in self.games:
            await update.message.reply_text("❌ Игра не найдена!")
            return
        
        game = self.games[chat_id]
        if game.phase == GamePhase.WAITING:
            await update.message.reply_text("⏳ Игра еще не началась! Роли будут назначены при старте.")
            return
        
        player = game.players.get(user_id)
        if not player:
            await update.message.reply_text("❌ Вы не найдены в игре!")
            return
        
        # Формируем красивое сообщение о роли
        role_emojis = {
            Role.WOLF: "🐺",
            Role.FOX: "🦊", 
            Role.HARE: "🐰",
            Role.MOLE: "🦫",
            Role.BEAVER: "🦦"
        }
        
        role_names_russian = {
            Role.WOLF: "Волк",
            Role.FOX: "Лиса", 
            Role.HARE: "Заяц",
            Role.MOLE: "Крот",
            Role.BEAVER: "Бобёр"
        }
        
        team_names = {
            Team.PREDATORS: "Хищники",
            Team.HERBIVORES: "Травоядные"
        }
        
        role_descriptions = {
            Role.WOLF: "Вы - Волк! Выбирайте жертву каждую ночь. Работайте с другими хищниками.",
            Role.FOX: "Вы - Лиса! Воруйте запасы у травоядных. После 2 краж жертва уходит.",
            Role.HARE: "Вы - Заяц! Выживайте и помогайте команде найти хищников.",
            Role.MOLE: "Вы - Крот! Проверяйте команды других игроков каждую ночь.",
            Role.BEAVER: "Вы - Бобёр! Защищайте травоядных от лисы, возвращая украденные запасы."
        }
        
        message = (
            f"{role_emojis[player.role]} *Ваша роль: {role_names_russian[player.role]}*\n\n"
            f"🏷️ Команда: {team_names[player.team]}\n"
            f"📝 Описание: {role_descriptions[player.role]}\n\n"
            f"🎮 Раунд: {game.current_round}\n"
            f"🌙 Выжили ночей: {player.consecutive_nights_survived}\n\n"
            f"💡 *Совет:* {self._get_role_tip(player.role)}"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')

    def get_role_name_russian(self, role: Role) -> str:
        """Возвращает русское название роли"""
        from role_translator import get_role_name_russian
        return get_role_name_russian(role)

    def _get_role_tip(self, role: Role) -> str:
        """Возвращает совет для конкретной роли"""
        tips = {
            Role.WOLF: "Скрывайте свою роль! Работайте с другими хищниками.",
            Role.FOX: "Воруйте у разных игроков, чтобы не привлекать внимание.",
            Role.HARE: "Будьте осторожны в общении, не раскрывайте важную информацию.",
            Role.MOLE: "Делитесь информацией с командой, но осторожно.",
            Role.BEAVER: "Защищайте тех, у кого украли запасы. Вы ключ к победе!"
        }
        return tips.get(role, "Играйте по роли и помогайте команде!")

    # ---------------- permission checking functions ----------------
    async def check_user_permissions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   required_permission: str = "member") -> tuple[bool, str]:
        """
        Проверяет права пользователя в чате
        Возвращает: (has_permission, error_message)
        """
        user_id = None
        chat_id = None
        try:
            # Получаем user_id в зависимости от типа update
            if update.effective_user:
                user_id = update.effective_user.id
            elif update.callback_query and update.callback_query.from_user:
                user_id = update.callback_query.from_user.id
            else:
                return False, "❌ Не удалось определить пользователя!"
            
            # Получаем chat_id в зависимости от типа update
            if update.effective_chat:
                chat_id = update.effective_chat.id
            elif update.callback_query and update.callback_query.message:
                chat_id = update.callback_query.message.chat_id
            else:
                return False, "❌ Не удалось определить чат!"
            
            # Получаем информацию о пользователе в чате
            member = await context.bot.get_chat_member(chat_id, user_id)
            
            # Проверяем статус пользователя
            if required_permission == "admin":
                if member.status not in ['administrator', 'creator']:
                    return False, "❌ Эта команда доступна только администраторам чата!"
            elif required_permission == "member":
                if member.status in ['kicked', 'left']:
                    return False, "❌ Вы не являетесь участником этого чата!"
                elif member.status == 'restricted':
                    # Проверяем, может ли пользователь писать сообщения
                    if not getattr(member, 'can_send_messages', True):
                        return False, "❌ У вас нет прав на отправку сообщений в этом чате!"
            
            return True, ""
            
        except Exception as e:
            user_info = f"пользователя {user_id}" if user_id else "пользователя"
            chat_info = f"чате {chat_id}" if chat_id else "чате"
            logger.error(f"Ошибка при проверке прав {user_info} в {chat_info}: {e}")
            return False, "❌ Не удалось проверить ваши права в чате!"

    async def check_game_permissions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   action: str = "join") -> tuple[bool, str]:
        """
        Проверяет права пользователя для игровых действий
        Возвращает: (has_permission, error_message)
        """
        user_id = None
        try:
            # Получаем user_id в зависимости от типа update
            if update.effective_user:
                user_id = update.effective_user.id
            elif update.callback_query and update.callback_query.from_user:
                user_id = update.callback_query.from_user.id
            else:
                return False, "❌ Не удалось определить пользователя!"
            
            # Получаем chat_id в зависимости от типа update
            if update.effective_chat:
                chat_id = update.effective_chat.id
            elif update.callback_query and update.callback_query.message:
                chat_id = update.callback_query.message.chat_id
            else:
                return False, "❌ Не удалось определить чат!"
            
            # Проверяем базовые права
            has_permission, error_msg = await self.check_user_permissions(update, context, "member")
            if not has_permission:
                return False, error_msg
            
            # Дополнительные проверки для игровых действий
            if action == "start_game":
                # Только участники игры могут начинать игру
                if user_id not in self.player_games or self.player_games[user_id] != chat_id:
                    return False, "❌ Только участники игры могут её начинать!"
            elif action == "end_game":
                # Только участники игры или администраторы могут завершать игру
                if user_id not in self.player_games or self.player_games[user_id] != chat_id:
                    # Проверяем, является ли пользователь администратором
                    has_admin_permission, admin_error = await self.check_user_permissions(update, context, "admin")
                    if not has_admin_permission:
                        return False, "❌ Только участники игры или администраторы могут завершать игру!"
            elif action == "settings":
                # Только администраторы могут изменять настройки
                return await self.check_user_permissions(update, context, "admin")
            
            return True, ""
            
        except Exception as e:
            user_info = f"пользователя {user_id}" if user_id else "пользователя"
            logger.error(f"Ошибка при проверке игровых прав {user_info}: {e}")
            return False, "❌ Не удалось проверить ваши права для этого действия!"

    async def send_permission_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  error_message: str, original_message: str = None):
        """
        Отправляет сообщение об ошибке прав доступа, не изменяя оригинальное сообщение
        """
        try:
            if update.callback_query:
                # Для callback query отвечаем отдельным сообщением
                await update.callback_query.answer(error_message, show_alert=True)
            else:
                # Для обычных команд отправляем отдельное сообщение
                await update.message.reply_text(error_message)
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения об ошибке прав: {e}")


    async def leave_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Позволяет игроку выйти из регистрации"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if user_id not in self.player_games:
            await update.message.reply_text("❌ Вы не зарегистрированы в игре!")
            return
        
        if self.player_games[user_id] != chat_id:
            await update.message.reply_text("❌ Вы зарегистрированы в другом чате!")
            return
        
        game = self.games[chat_id]
        if game.phase != GamePhase.WAITING:
            await update.message.reply_text("❌ Нельзя выйти из игры, которая уже началась!")
            return
        
        # Удаляем игрока
        if game.remove_player(user_id):
            del self.player_games[user_id]
            
            # Обновляем сообщение в чате
            await self._update_join_message(chat_id, context)
            
            await update.message.reply_text("✅ Вы вышли из регистрации на игру!")
        else:
            await update.message.reply_text("❌ Не удалось выйти из регистрации!")

    async def cancel_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отменяет игру (только для админов)"""
        if not await self.is_user_admin(update, context):
            await update.message.reply_text("❌ Только администраторы могут отменить игру!")
            return
        
        chat_id = update.effective_chat.id
        if chat_id not in self.games:
            await update.message.reply_text("❌ В этом чате нет активной игры!")
            return
        
        game = self.games[chat_id]
        if game.phase != GamePhase.WAITING:
            await update.message.reply_text("❌ Нельзя отменить игру, которая уже началась!")
            return
        
        # Отменяем игру
        game.phase = GamePhase.GAME_OVER
        del self.games[chat_id]
        
        # Очищаем данные игроков
        for user_id in list(self.player_games.keys()):
            if self.player_games[user_id] == chat_id:
                del self.player_games[user_id]
        
        await update.message.reply_text("🛑 Игра отменена администратором!")

    async def _update_join_message(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Обновляет сообщение о присоединении в чате"""
        try:
            if chat_id in self.games:
                game = self.games[chat_id]
                if hasattr(game, 'pinned_message_id') and game.pinned_message_id:
                    # Обновляем закрепленное сообщение
                    await context.bot.edit_message_text(
                        self._get_join_message_text(game),
                        chat_id=chat_id,
                        message_id=game.pinned_message_id,
                        reply_markup=self._get_join_keyboard(game, context)
                    )
        except Exception as e:
            logger.error(f"Error updating join message: {e}")

    def _get_join_message_text(self, game) -> str:
        """Формирует текст сообщения о присоединении"""
        max_players = getattr(game, "MAX_PLAYERS", 12)
        players_list = ""
        for player in game.players.values():
            player_tag = self.format_player_tag(player.username, player.user_id)
            players_list += f"• {player_tag}\n"
        
        message = (
            "🌲 *Лес и Волки - Регистрация* 🌲\n\n"
            f"👥 Игроков: {len(game.players)}/{max_players}\n"
            f"📋 Минимум для старта: {self.global_settings.get_min_players()}\n\n"
            f"📝 Участники:\n{players_list}"
        )
        
        if game.can_start_game():
            message += "\n✅ Можно начинать игру!"
        else:
            message += f"\n⏳ Нужно ещё {max(0, self.global_settings.get_min_players() - len(game.players))} игроков"
        
        return message

    def _get_join_keyboard(self, game, context) -> InlineKeyboardMarkup:
        """Формирует клавиатуру для сообщения о присоединении"""
        keyboard = []
        
        # Кнопка "Посмотреть свою роль" (если игра идет)
        if game.phase != GamePhase.WAITING:
            bot_username = context.bot.username
            keyboard.append([InlineKeyboardButton("👁️ Посмотреть свою роль", url=f"https://t.me/{bot_username}?start=role")])
        
        # Основные кнопки управления игрой
        if game.phase == GamePhase.WAITING:
            # Кнопки для фазы ожидания
            keyboard.append([InlineKeyboardButton("✅ Присоединиться", callback_data="join_game")])
            keyboard.append([InlineKeyboardButton("❌ Покинуть игру", callback_data="leave_registration")])
            
            # Кнопка "Начать игру" (если можно)
            if game.can_start_game():
                keyboard.append([InlineKeyboardButton("🚀 Начать игру", callback_data="start_game")])
        else:
            # Кнопки для активной игры
            keyboard.append([InlineKeyboardButton("🏁 Завершить игру", callback_data="end_game")])
        
        return InlineKeyboardMarkup(keyboard)

    # ---------------- callback helpers ----------------
    async def join_from_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем, что message существует
        if not query.message:
            logger.error("CallbackQuery message is None")
            return
            
        chat_id = query.message.chat.id
        user_id = query.from_user.id
        username = query.from_user.username or query.from_user.full_name or str(user_id)

        success, message, reply_markup = await self._join_game_common(chat_id, user_id, username, context, is_callback=True, update=query)
        
        if success:
            try:
                game = self.games[chat_id]
                
                # Если есть закрепленное сообщение, редактируем его
                if hasattr(game, 'pinned_message_id') and game.pinned_message_id:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=game.pinned_message_id,
                            text=message,
                            reply_markup=reply_markup
                        )
                        logger.info(f"Отредактировано сообщение о присоединении: {game.pinned_message_id}")
                    except Exception as e:
                        logger.warning(f"Не удалось отредактировать сообщение: {e}")
                        # Если не удалось отредактировать, создаем новое
                        join_message = await query.message.reply_text(message, reply_markup=reply_markup)
                        await context.bot.unpin_chat_message(chat_id, game.pinned_message_id)
                        await context.bot.pin_chat_message(chat_id, join_message.message_id)
                        game.pinned_message_id = join_message.message_id
                        logger.info(f"Создано и закреплено новое сообщение о присоединении: {join_message.message_id}")
                else:
                    # Если нет закрепленного сообщения, создаем новое
                    join_message = await query.message.reply_text(message, reply_markup=reply_markup)
                    await context.bot.pin_chat_message(chat_id, join_message.message_id)
                    game.pinned_message_id = join_message.message_id
                    logger.info(f"Создано и закреплено новое сообщение о присоединении: {join_message.message_id}")
                
                # Отвечаем на callback
                await query.answer("✅ Вы присоединились к игре!")
                logger.info("✅ Игрок присоединился к игре через callback")
                
            except Exception:
                logger.error("Error in join_from_callback")
                await query.answer("❌ Произошла ошибка при присоединении к игре!")
        else:
            await query.answer(message)

    async def status_from_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        chat_id = query.message.chat.id

        if chat_id not in self.games:
            await query.edit_message_text("❌ В этом чате нет активной игры!\nИспользуйте `/join` чтобы присоединиться.")
            return

        game = self.games[chat_id]

        if game.phase == GamePhase.WAITING:
            min_players = self.global_settings.get_min_players()
            status_text = (
                "📊 *Статус:* Ожидание игроков\n\n"
                f"👥 Игроков: {len(game.players)}/12\n"
                f"📋 Минимум: {min_players}\n\n"
                "**Участники:**\n"
            )
            for player in game.players.values():
                player_tag = self.format_player_tag(player.username, player.user_id)
                status_text += f"• {player_tag}\n"
            if game.can_start_game():
                status_text += "\n✅ **Можно начинать игру!**"
            else:
                status_text += f"\n⏳ Нужно ещё {max(0, min_players - len(game.players))} игроков"
        else:
            phase_names = {
                GamePhase.NIGHT: "🌙 Ночь",
                GamePhase.DAY: "☀️ День",
                GamePhase.VOTING: "🗳️ Голосование",
                GamePhase.GAME_OVER: "🏁 Игра окончена"
            }
            status_text = (
                f"📊 *Статус:* {phase_names.get(game.phase, 'Неизвестно')}\n\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых: {len(game.get_alive_players())}\n\n"
                "**Живые игроки:**\n"
            )
            for p in game.get_alive_players():
                player_tag = self.format_player_tag(p.username, p.user_id)
                status_text += f"• {player_tag}\n"

        await query.edit_message_text(status_text)

    async def check_stage_from_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Проверяет текущий этап игры и отправляет соответствующее сообщение с кнопками"""
        chat_id = query.message.chat.id
        thread_id = getattr(query.message, 'message_thread_id', None)

        if chat_id not in self.games:
            await query.edit_message_text("❌ В этом чате нет активной игры!\nИспользуйте `/join` чтобы присоединиться.")
            return

        game = self.games[chat_id]

        # Отправляем сообщение в зависимости от этапа игры
        if game.phase == GamePhase.WAITING:
            # Этап регистрации
            min_players = self.global_settings.get_min_players()
            stage_text = (
                "🎮 **Этап: Регистрация игроков**\n\n"
                f"👥 Игроков: {len(game.players)}/12\n"
                f"📋 Минимум: {min_players}\n\n"
                "**Участники:**\n"
            )
            for player in game.players.values():
                player_tag = self.format_player_tag(player.username, player.user_id)
                stage_text += f"• {player_tag}\n"
            
            if game.can_start_game():
                stage_text += "\n✅ **Можно начинать игру!**"
            else:
                stage_text += f"\n⏳ Нужно ещё {max(0, min_players - len(game.players))} игроков"
            
            # Кнопки для этапа регистрации
            keyboard = [
                [InlineKeyboardButton("✅ Присоединиться к игре", callback_data="welcome_start_game")],
                [InlineKeyboardButton("📖 Правила игры", callback_data="welcome_rules")],
                [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")],
                [InlineKeyboardButton("🔍 Проверить этап", callback_data="check_stage")]
            ]
            
            if game.can_start_game():
                keyboard.insert(0, [InlineKeyboardButton("🚀 Начать игру", callback_data="welcome_start_game")])
            
        elif game.phase == GamePhase.NIGHT:
            # Ночной этап
            stage_text = (
                "🌙 **Этап: Ночь**\n\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых: {len(game.get_alive_players())}\n\n"
                "🌲 Все зверушки спят в лесу...\n"
                "🐺 Хищники планируют свои действия\n"
                "🦫 Травоядные отдыхают"
            )
            
            # Кнопки для ночного этапа
            keyboard = [
                [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")],
                [InlineKeyboardButton("🔍 Проверить этап", callback_data="check_stage")]
            ]
            
        elif game.phase == GamePhase.DAY:
            # Дневной этап
            stage_text = (
                "☀️ **Этап: День**\n\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых: {len(game.get_alive_players())}\n\n"
                "🌲 Все зверушки проснулись!\n"
                "💬 Время для обсуждения и поиска хищников\n"
                "🗳️ Скоро начнется голосование"
            )
            
            # Кнопки для дневного этапа
            keyboard = [
                [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")],
                [InlineKeyboardButton("🔍 Проверить этап", callback_data="check_stage")]
            ]
            
        elif game.phase == GamePhase.VOTING:
            # Этап голосования
            stage_text = (
                "🗳️ **Этап: Голосование**\n\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых: {len(game.get_alive_players())}\n\n"
                "🌲 Время решать судьбу подозрительных зверушек!\n"
                "🗳️ Каждый голосует за изгнание"
            )
            
            # Кнопки для этапа голосования
            keyboard = [
                [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")],
                [InlineKeyboardButton("🔍 Проверить этап", callback_data="check_stage")]
            ]
            
        else:
            # Игра окончена
            stage_text = (
                "🏁 **Игра окончена!**\n\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых: {len(game.get_alive_players())}\n\n"
                "🌲 Игра завершена!"
            )
            
            # Кнопки для завершенной игры
            keyboard = [
                [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")],
                [InlineKeyboardButton("🔍 Проверить этап", callback_data="check_stage")]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(stage_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_check_stage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки 'Проверить этап' без проверки прав администратора"""
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()
        
        # Вызываем функцию проверки этапа без проверки прав
        await self.check_stage_from_callback(query, context)

    # ---------------- join / leave / status ----------------
    async def join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
        
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.full_name or str(user_id)

        success, message, reply_markup = await self._join_game_common(
            chat_id, user_id, username, context, is_callback=False, update=update
        )
        
        if success:
            try:
                game = self.games[chat_id]
                
                join_message = None  # чтобы всегда было определено

                # Если есть закрепленное сообщение, редактируем его
                if hasattr(game, 'pinned_message_id') and game.pinned_message_id:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=game.pinned_message_id,
                            text=message,
                            reply_markup=reply_markup
                        )
                        logger.info(f"Отредактировано сообщение о присоединении: {game.pinned_message_id}")
                    except Exception as e:
                        logger.warning(f"Не удалось отредактировать сообщение: {e}")
                        # Если не удалось отредактировать, создаем новое
                        join_message = await update.message.reply_text(message, reply_markup=reply_markup)
                        await context.bot.unpin_chat_message(chat_id, game.pinned_message_id)

                if join_message is None:
                    # Если редактирование прошло успешно — закрепляем старое сообщение
                    await context.bot.pin_chat_message(chat_id, game.pinned_message_id)
                else:
                    # Если создавали новое — закрепляем его
                    await context.bot.pin_chat_message(chat_id, join_message.message_id)
                    game.pinned_message_id = join_message.message_id
                    logger.info(f"Создано и закреплено новое сообщение о присоединении: {join_message.message_id}")
                
                # Отправляем подтверждение пользователю
                await update.message.reply_text("✅ Вы присоединились к игре!")
                
            except Exception as e:
                logger.error(f"Error in join: {e}")
                await update.message.reply_text("❌ Произошла ошибка при присоединении к игре!")
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)

    async def leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.full_name or str(user_id)

        # Проверяем, что это группа, а не личные сообщения
        if chat_id == user_id:
            await update.message.reply_text("❌ Игра доступна только в группах!")
            return

        if chat_id not in self.games:
            await update.message.reply_text("❌ В этом чате нет активной игры!")
            return

        game = self.games[chat_id]

        if game.phase != GamePhase.WAITING:
            await update.message.reply_text("❌ Игра уже идёт! Нельзя покинуть сейчас.")
            return

        if user_id not in game.players:
            await update.message.reply_text("❌ Вы не участвуете в игре!")
            return

        if game.leave_game(user_id):
            if user_id in self.player_games:
                del self.player_games[user_id]
            
            player_tag = self.format_player_tag(username, user_id)
            # Показываем обновленный список игроков с тегами
            players_list = ""
            for player in game.players.values():
                tag = self.format_player_tag(player.username, player.user_id)
                players_list += f"• {tag}\n"
            
            message = (
                f"👋 {player_tag} покинул игру.\n\n"
                f"👥 Игроков: {len(game.players)}/{getattr(game, 'MAX_PLAYERS', 12)}\n"
                f"📋 Минимум для начала: {self.global_settings.get_min_players()}\n\n"
                f"📝 Участники:\n{players_list}" if players_list else "📝 Участников нет\n"
            )
            
            if not game.can_start_game() and len(game.players) > 0:
                message += f"\n⚠️ Нужно ещё {max(0, self.global_settings.get_min_players() - len(game.players))} игроков"
            elif game.can_start_game():
                message += "\n✅ Можно начинать игру!"
                
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ Не удалось покинуть игру.")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        chat_id = update.effective_chat.id

        # Проверяем, что это группа, а не личные сообщения
        if chat_id == update.effective_user.id:
            await update.message.reply_text("❌ Игра доступна только в группах!")
            return

        if chat_id not in self.games:
            await update.message.reply_text("❌ В этом чате нет активной игры!\nИспользуйте `/join` чтобы присоединиться.")
            return

        game = self.games[chat_id]

        if game.phase == GamePhase.WAITING:
            min_players = self.global_settings.get_min_players()
            status_text = (
                "📊 *Статус:* Ожидание игроков\n\n"
                f"👥 Игроков: {len(game.players)}/12\n"
                f"📋 Минимум: {min_players}\n\n"
                "**Участники:**\n"
            )
            for player in game.players.values():
                player_tag = self.format_player_tag(player.username, player.user_id)
                status_text += f"• {player_tag}\n"
            if game.can_start_game():
                status_text += "\n✅ **Можно начинать игру!**"
            else:
                status_text += f"\n⏳ Нужно ещё {max(0, min_players - len(game.players))} игроков"
        else:
            phase_names = {
                GamePhase.NIGHT: "🌙 Ночь",
                GamePhase.DAY: "☀️ День",
                GamePhase.VOTING: "🗳️ Голосование",
                GamePhase.GAME_OVER: "🏁 Игра окончена"
            }
            status_text = (
                f"📊 *Статус:* {phase_names.get(game.phase, 'Неизвестно')}\n\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых: {len(game.get_alive_players())}\n\n"
                "**Живые игроки:**\n"
            )
            for p in game.get_alive_players():
                player_tag = self.format_player_tag(p.username, p.user_id)
                status_text += f"• {player_tag}\n"

        await update.message.reply_text(status_text)

    # ---------------- starting / ending game ----------------
    async def start_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_game_permissions(update, context, "start_game")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        thread_id = self.get_thread_id(update)

        # Проверяем, что это группа, а не личные сообщения
        if chat_id == user_id:
            await update.message.reply_text("❌ Игра доступна только в группах!")
            return

        # Убираем проверку прав администратора - теперь любой пользователь может начать игру

        if chat_id not in self.games:
            await update.message.reply_text("❌ Нет активной игры в этом чате!")
            return

        game = self.games[chat_id]

        min_players = self.global_settings.get_min_players()
        if not game.can_start_game():
            await update.message.reply_text(f"❌ Недостаточно игроков! Нужно минимум {min_players} игроков.")
            return

        if game.phase != GamePhase.WAITING:
            await update.message.reply_text("❌ Игра уже идёт!")
            return

        # Создаем игру в базе данных
        db_game_id = self.db.create_game(chat_id, thread_id, {
            "min_players": min_players,
            "max_players": self.global_settings.get("max_players", 12),
            "night_duration": self.global_settings.get("night_duration", 60),
            "day_duration": self.global_settings.get("day_duration", 300),
            "voting_duration": self.global_settings.get("voting_duration", 120)
        })
        
        # Сохраняем ID игры в БД в объекте игры
        game.db_game_id = db_game_id

        if game.start_game():
            # Записываем начало игры в БД
            self.db.start_game(db_game_id)
            
            # Добавляем всех игроков в БД
            for player in game.players:
                self.db.add_player(
                    db_game_id, 
                    player.user_id, 
                    player.username, 
                    player.first_name, 
                    player.last_name
                )
            
            # Назначаем роли в БД
            role_assignments = {}
            for player in game.players:
                role_assignments[player.user_id] = {
                    "role": player.role.value if player.role else None,
                    "team": player.team.value if player.team else None
                }
            self.db.assign_roles(db_game_id, role_assignments)
            
            # Тегируем всех участников игры
            await self.tag_game_participants(update, context, game)
            
            await self.start_night_phase(update, context, game)
        else:
            await update.message.reply_text("❌ Не удалось начать игру!")

    async def end_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_game_permissions(update, context, "end_game")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        if chat_id not in self.games:
            await update.message.reply_text("❌ Нет активной игры в этом чате!")
            return

        game = self.games[chat_id]

        if game.phase == GamePhase.WAITING:
            await update.message.reply_text("❌ Игра ещё не началась! Используйте `/start_game` чтобы начать игру.")
            return
        
        # Проверяем, что пользователь участвует в игре
        if user_id not in self.player_games or self.player_games[user_id] != chat_id:
            await update.message.reply_text("❌ Только участники игры могут её завершить!")
            return

        await self._end_game_internal(update, context, game, "Участник завершил игру")

    async def force_end(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем права пользователя (только администраторы)
        has_permission, error_msg = await self.check_user_permissions(update, context, "admin")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        # Проверяем, что это группа, а не личные сообщения
        if chat_id == user_id:
            await update.message.reply_text("❌ Игра доступна только в группах!")
            return

        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут принудительно завершать игру!")
            return

        if chat_id not in self.games:
            await update.message.reply_text("❌ Нет активной игры в этом чате!")
            return

        game = self.games[chat_id]
        await self._end_game_internal(update, context, game, "Администратор принудительно завершил игру")

    async def clear_all_games(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем права пользователя (только администраторы)
        has_permission, error_msg = await self.check_user_permissions(update, context, "admin")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        user_id = update.effective_user.id

        games_count = len(self.games)
        players_count = len(self.player_games)

        # Очищаем все игровые сессии
        self.games.clear()
        self.player_games.clear()
        self.night_actions.clear()
        self.night_interfaces.clear()

        await update.message.reply_text(
            "🧹 Все игровые сессии очищены!\n\n"
            f"📊 Было завершено игр: {games_count}\n"
            f"👥 Было освобождено игроков: {players_count}"
        )

    async def setup_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для настройки канала/темы для игры"""
        # Проверяем права пользователя (только администраторы)
        has_permission, error_msg = await self.check_user_permissions(update, context, "admin")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        thread_id = self.get_thread_id(update)
        
        # Проверяем, что это группа или канал, а не личные сообщения
        if chat_id == user_id:
            await update.message.reply_text(
                "❌ Эта команда доступна только в группах и каналах!\n"
                "Добавьте бота в группу и используйте команду там."
            )
            return
        
        # Проверяем права администратора
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            if chat_member.status not in ['creator', 'administrator']:
                await update.message.reply_text(
                    "❌ Только администраторы могут настраивать канал для игры!"
                )
                return
        except Exception as e:
            await update.message.reply_text(
                "❌ Ошибка при проверке прав администратора. "
                "Убедитесь, что бот имеет права для проверки участников."
            )
            return
        
        # Получаем информацию о чате
        try:
            chat_info = await context.bot.get_chat(chat_id)
            chat_name = chat_info.title or f"Чат {chat_id}"
            chat_type = chat_info.type
        except Exception:
            chat_name = f"Чат {chat_id}"
            chat_type = "unknown"
        
        # Формируем название места для сообщений (чат или тема)
        if thread_id:
            location_name = f"тема {thread_id} в чате '{chat_name}'"
            location_short = f"Тема {thread_id}"
        else:
            location_name = f"чат '{chat_name}'"
            location_short = f"Чат '{chat_name}'"
        
        # Проверяем, есть ли уже активная игра
        if chat_id in self.games:
            game = self.games[chat_id]
            if game.phase != GamePhase.WAITING:
                await update.message.reply_text(
                    f"⚠️ В канале '{chat_name}' уже идёт игра!\n"
                    f"Текущая фаза: {game.phase.value}\n"
                    f"Участников: {len(game.players)}\n\n"
                    "Дождитесь окончания текущей игры или используйте /force_end для принудительного завершения."
                )
                return
            else:
                # Есть игра в ожидании - добавляем в авторизованные чаты/темы если не добавлен
                if not self.is_chat_authorized(chat_id, thread_id):
                    self.authorize_chat(chat_id, thread_id)
                # показываем статус
                await update.message.reply_text(
                    f"✅ {location_short} уже настроен для игры!\n\n"
                    "📊 Статус: Ожидание игроков\n"
                    f"👥 Участников: {len(game.players)}/{getattr(game, 'MAX_PLAYERS', 12)}\n"
                    f"📋 Минимум для старта: {self.global_settings.get_min_players()}\n\n"
                    "Используйте `/join` для присоединения к игре."
                )
                return
        
        # Настраиваем канал/тему для игры
        try:
            # Добавляем чат/тему в авторизованные
            self.authorize_chat(chat_id, thread_id)
            
            # Создаем новую игру
            self.games[chat_id] = Game(chat_id, thread_id)
            self.games[chat_id].is_test_mode = self.global_settings.is_test_mode()
            self.night_actions[chat_id] = NightActions(self.games[chat_id])
            self.night_interfaces[chat_id] = NightInterface(self.games[chat_id], self.night_actions[chat_id])
            
            # Создаем клавиатуру с быстрыми действиями
            keyboard = [
                [InlineKeyboardButton("👥 Присоединиться к игре", callback_data="welcome_start_game")],
                [InlineKeyboardButton("📖 Правила игры", callback_data="welcome_rules")],
                [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")],
            [InlineKeyboardButton("🔍 Проверить этап", callback_data="check_stage")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение об успешной настройке
            setup_message = (
                f"✅ {location_short} успешно настроен для игры 'Лес и Волки'!\n\n"
                f"🎮 Тип чата: {chat_type}\n"
                f"📍 Область действия: {location_name}\n"
                f"📋 Минимум игроков: {self.global_settings.get_min_players()}\n"
                f"👥 Максимум игроков: {getattr(self.games[chat_id], 'MAX_PLAYERS', 12)}\n"
                f"🧪 Тестовый режим: {'Включен' if self.global_settings.is_test_mode() else 'Отключен'}\n\n"
                "🚀 Готово к игре! Участники могут использовать:\n"
                "• `/join` - присоединиться к игре\n"
                "• `/status` - посмотреть статус\n"
                "• `/rules` - изучить правила\n\n"
                "🎯 Все пользователи могут использовать:\n"
                "• `/start_game` - начать игру\n"
                "• `/settings` - настройки игры\n"
                "• `/end_game` - завершить игру\n\n"
                f"ℹ️ Бот будет работать только в {location_name}\n\n"
                "Удачной игры! 🌲"
            )
            
            await update.message.reply_text(setup_message, reply_markup=reply_markup)
            
            # Логируем успешную настройку
            logger.info(f"Channel {chat_id} ({chat_name}) successfully set up for Forest Mafia by user {user_id}")
            
        except Exception as e:
            logger.error(f"Error setting up channel {chat_id}: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при настройке канала!\n"
                "Попробуйте еще раз или обратитесь к администратору бота."
            )

    async def remove_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для удаления канала/темы из авторизованных для игры"""
        # Проверяем права пользователя (только администраторы)
        has_permission, error_msg = await self.check_user_permissions(update, context, "admin")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        thread_id = self.get_thread_id(update)
        
        # Проверяем, что это группа или канал, а не личные сообщения
        if chat_id == user_id:
            await update.message.reply_text(
                "❌ Эта команда доступна только в группах и каналах!"
            )
            return
        
        # Проверяем права администратора
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            if chat_member.status not in ['creator', 'administrator']:
                await update.message.reply_text(
                    "❌ Только администраторы могут удалять канал из игры!"
                )
                return
        except Exception as e:
            await update.message.reply_text(
                "❌ Ошибка при проверке прав администратора."
            )
            return
        
        # Получаем информацию о чате
        try:
            chat_info = await context.bot.get_chat(chat_id)
            chat_name = chat_info.title or f"Чат {chat_id}"
        except Exception:
            chat_name = f"Чат {chat_id}"
        
        # Формируем название места для сообщений (чат или тема)
        if thread_id:
            location_name = f"тема {thread_id} в чате '{chat_name}'"
            location_short = f"Тема {thread_id}"
        else:
            location_name = f"чат '{chat_name}'"
            location_short = f"Чат '{chat_name}'"
        
        # Проверяем, есть ли активная игра
        if chat_id in self.games:
            game = self.games[chat_id]
            if game.phase != GamePhase.WAITING:
                await update.message.reply_text(
                    f"❌ В канале '{chat_name}' идёт игра!\n"
                    "Завершите игру перед удалением канала из авторизованных."
                )
                return
            else:
                # Завершаем игру в ожидании и удаляем все связанные данные
                for pid in list(game.players.keys()):
                    if pid in self.player_games:
                        del self.player_games[pid]
                del self.games[chat_id]
                if chat_id in self.night_actions:
                    del self.night_actions[chat_id]
                if chat_id in self.night_interfaces:
                    del self.night_interfaces[chat_id]
        
        # Удаляем чат/тему из авторизованных
        if self.is_chat_authorized(chat_id, thread_id):
            self.authorized_chats.discard((chat_id, thread_id))
            await update.message.reply_text(
                f"✅ {location_short} удален из авторизованных для игры!\n\n"
                f"🚫 Бот больше не будет отвечать на команды в {location_name}.\n"
                "Используйте /setup_channel для повторной настройки."
            )
            if thread_id:
                logger.info(f"Thread {thread_id} in channel {chat_id} ({chat_name}) removed from authorized chats by user {user_id}")
            else:
                logger.info(f"Channel {chat_id} ({chat_name}) removed from authorized chats by user {user_id}")
        else:
            await update.message.reply_text(
                f"❌ {location_short} не был настроен для игры.\n"
                "Используйте /setup_channel для настройки."
            )

    async def _end_game_internal(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game, reason: str):
        if getattr(game, "game_over_sent", False):
            return
        game.game_over_sent = True

        game.phase = GamePhase.GAME_OVER

        # Открепляем все закрепленные сообщения бота при завершении игры
        await self._unpin_all_bot_messages(context, game)

        # Используем улучшенную логику завершения игры
        try:
            from game_end_logic import GameEndLogic
            game_end_logic = GameEndLogic(game)
            
            # Определяем победителя по количеству живых игроков
            alive_players = game.get_alive_players()
            predators = [p for p in alive_players if p.team == Team.PREDATORS]
            herbivores = [p for p in alive_players if p.team == Team.HERBIVORES]
            
            if len(predators) > len(herbivores):
                winner = Team.PREDATORS
            elif len(herbivores) > len(predators):
                winner = Team.HERBIVORES
            else:
                winner = Team.HERBIVORES  # По умолчанию травоядные
            
            result = {
                "winner": winner,
                "reason": "🏁 Игра окончена!",
                "details": f"📋 Причина: {reason}"
            }
            
            message_text = game_end_logic.get_game_over_message(result)
            
        except ImportError:
            # Fallback на старую логику
            message_text = f"🏁 Игра завершена!\n\n📋 Причина: {reason}\n📊 Статистика игры:\nВсего игроков: {len(game.players)}\nРаундов сыграно: {game.current_round}\nФаза: {game.phase.value}"

        # Отправляем сообщение
        try:
            await context.bot.send_message(
                chat_id=game.chat_id,
                text=message_text,
                message_thread_id=game.thread_id,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о завершении игры: {e}")
            # Fallback - если update есть, попробуем через reply
            if update and hasattr(update, 'message') and update.message:
                try:
                    await update.message.reply_text(message_text, parse_mode='Markdown')
                except Exception as e2:
                    logger.error(f"Fallback тоже не сработал: {e2}")

        # очищаем маппинги
        for pid in list(game.players.keys()):
            if pid in self.player_games:
                del self.player_games[pid]

        chat_id = game.chat_id
        if chat_id in self.games:
            del self.games[chat_id]
        if chat_id in self.night_actions:
            del self.night_actions[chat_id]
        if chat_id in self.night_interfaces:
            del self.night_interfaces[chat_id]
        
        # Дополнительная очистка - удаляем все записи игроков из этого чата
        players_to_remove = []
        for user_id, game_chat_id in self.player_games.items():
            if game_chat_id == chat_id:
                players_to_remove.append(user_id)
        
        for user_id in players_to_remove:
            del self.player_games[user_id]

    # ---------------- night/day/vote flow ----------------
    async def start_night_phase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        game.start_night()
        
        # Открепляем сообщение о присоединении, так как игра началась
        if hasattr(game, 'pinned_message_id') and game.pinned_message_id:
            try:
                await context.bot.unpin_chat_message(
                    chat_id=game.chat_id,
                    message_id=game.pinned_message_id
                )
                logger.info(f"Откреплено сообщение о присоединении при начале игры: {game.pinned_message_id}")
                game.pinned_message_id = None
            except Exception as e:
                logger.warning(f"Не удалось открепить сообщение о присоединении: {e}")
        
        # Создаем кнопку для просмотра роли
        keyboard = [
            [InlineKeyboardButton("🎭 Посмотреть свою роль", callback_data="view_my_role")], 
            [InlineKeyboardButton("💌 Написать боту", url="https://t.me/Forest_fuss_bot")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем лесную сказку
        forest_story = (
            "🌲 Жили-были в тёмном Сосновом Лесу всевозможные звери. Каждый сидел в своей норке, берлоге или пещере, кто-то по ночам охотился, кто-то запасал на зиму зерно. Были тут и зайцы, были и волки, были лисы и бобры, и каждый занимался чем-то своим, пытаясь помочь как себе, так и своим близким.\n"
            "Однажды, одной тёмной ночью некоторые зверушки стали исчезать… Лесные жители решили дружно разобраться почему так происходит и кто же в этом виноват.\n\n"
            "**И вот наступила ночь, зверушки мирно уснули сладким сном… 😴**"
        )
        
        # Проверяем, является ли update фиктивным (для досрочного завершения голосования)
        # или это callback query
        if (hasattr(update, 'message') and hasattr(update.message, 'message_id') and update.message.message_id == 0) or hasattr(update, 'callback_query'):
            # Используем context.bot.send_message для фиктивного update или callback query
            await context.bot.send_message(
                chat_id=game.chat_id,
                text=forest_story,
                parse_mode='Markdown',
                message_thread_id=game.thread_id
            )
            
            # Небольшая пауза для атмосферы
            await asyncio.sleep(2)
            
            night_message = await context.bot.send_message(
                chat_id=game.chat_id,
                text="🌙 Наступает ночь 🌙 Зверята разбежались по норкам и сладко заснули 😴 А вот ночные звери выходят на охоту…\n\n🎭 Распределение ролей завершено!",
                reply_markup=reply_markup,
                message_thread_id=game.thread_id
            )
            
            # Закрепляем сообщение ночи
            await self._pin_stage_message(context, game, "night", night_message.message_id)
        else:
            # Обычный update - используем reply_text
            await update.message.reply_text(forest_story, parse_mode='Markdown')
            
            # Небольшая пауза для атмосферы
            await asyncio.sleep(2)
            
            night_message = await update.message.reply_text(
                "🌙 Наступает ночь 🌙 Зверята разбежались по норкам и сладко заснули 😴 А вот ночные звери выходят на охоту…\n\n🎭 Распределение ролей завершено!",
                reply_markup=reply_markup
            )
            
            # Закрепляем сообщение ночи
            await self._pin_stage_message(context, game, "night", night_message.message_id)

        # ЛС с ролями
        for player in game.players.values():
            role_info = self.get_role_info(player.role)
            try:
                await context.bot.send_message(chat_id=player.user_id, text=f"🎭 Ваша роль: {role_info['name']}\n\n{role_info['description']}")
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение игроку {player.user_id}: {e}")

        # Wolves intro
        wolves = game.get_players_by_role(Role.WOLF)
        if len(wolves) > 1:
            wolves_text = f"🐺 {', '.join([w.username for w in wolves])}, так-так-так, а вот и наши голодные волки. 🐺 Знакомьтесь, точите зубки (да хоть друг-другу), следующей ночью вы выходите на охоту 😈"
            for wolf in wolves:
                try:
                    await context.bot.send_message(chat_id=wolf.user_id, text=wolves_text)
                except Exception as e:
                    logger.error(f"Не удалось отправить сообщение волку {wolf.user_id}: {e}")

        # Mole intro
        moles = game.get_players_by_role(Role.MOLE)
        for mole in moles:
            try:
                mole_text = "🦫 Вот ты где, дружок **Крот**! Не устал еще ночью рыть норки, попадая в домики других зверей? А хотя... Знаешь, это может быть очень полезно, ведь так можно узнать кто они на самом деле!"
                await context.bot.send_message(chat_id=mole.user_id, text=mole_text, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение кроту {mole.user_id}: {e}")

        # Beaver intro
        beavers = game.get_players_by_role(Role.BEAVER)
        for beaver in beavers:
            try:
                beaver_text = "🦦 Наш **Бобёр** весьма хитёр – всё добро несёт в шатёр. У **бобра** в шатре добра – бочка, кадка, два ведра!"
                await context.bot.send_message(chat_id=beaver.user_id, text=beaver_text, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение бобру {beaver.user_id}: {e}")

        # Fox intro
        foxes = game.get_players_by_role(Role.FOX)
        for fox in foxes:
            try:
                fox_text = "🦊 Жила-была **Лиса**-воровка, да не подвела ее сноровка! 🦊"
                await context.bot.send_message(chat_id=fox.user_id, text=fox_text, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение лисе {fox.user_id}: {e}")

        # меню ночных действий
        await self.send_night_actions_to_players(context, game)

        # Отправляем кнопку просмотра роли игрокам без ночных действий
        await self.send_role_button_to_passive_players(context, game)

        # таймер ночи (запускаем как таск)
        asyncio.create_task(self.night_phase_timer(update, context, game))

    async def night_phase_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Таймер для ночной фазы с проверкой досрочного завершения"""
        logger.info(f"Ночная фаза начата. Игроков: {len(game.get_alive_players())}")
        
        for i in range(60):  # Проверяем каждую секунду в течение 60 секунд
            await asyncio.sleep(1)
            
            # Проверяем, все ли игроки выполнили ночные действия
            if game.phase == GamePhase.NIGHT and game.chat_id in self.night_actions:
                night_actions = self.night_actions[game.chat_id]
                if night_actions.are_all_actions_completed():
                    logger.info("Все игроки выполнили ночные действия! Завершаем ночь досрочно.")
                    await context.bot.send_message(
                        chat_id=game.chat_id, 
                        text="⚡ Все игроки выполнили ночные действия! Ночь завершена досрочно.",
                        message_thread_id=game.thread_id
                    )
                    await self.process_night_phase(update, context, game)
                    await self.start_day_phase(update, context, game)
                    return
            
            # Если игра завершилась или фаза изменилась - выходим
            if game.phase != GamePhase.NIGHT:
                logger.info(f"Ночная фаза прервана: фаза изменилась на {game.phase}")
                return
        
        # Время вышло
        if game.phase == GamePhase.NIGHT:
            await self.process_night_phase(update, context, game)
            await self.start_day_phase(update, context, game)

    async def start_day_phase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        # Проверяем условия автоматического завершения игры
        winner = game.check_game_end()
        if winner:
            await self.end_game_winner(update, context, game, winner)
            return
            
        game.start_day()

        # Открепляем сообщение ночи
        await self._unpin_previous_stage_message(context, game, "day")

        # Создаем кнопки для дневной фазы
        keyboard = [
            [InlineKeyboardButton("🏁 Завершить обсуждение", callback_data="day_end_discussion")],
            [InlineKeyboardButton("🐺 Выбрать волка", callback_data="day_choose_wolf")],
            [InlineKeyboardButton("🔍 Диагностика таймера", callback_data="day_timer_diagnostics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        day_message = await update.message.reply_text(
            "☀️ Наступило утро ☀️\n\n"
            "Начался очередной спокойный солнечный день в нашем дивном Лесу ☀️ Друзья зверята собрались вместе обсуждать новости последних дней 💬\n\n"
            "У вас есть 5 минут, чтобы обсудить ночные события и решить, кого изгнать.\n\n"
            "Используйте кнопки ниже для управления фазой:",
            reply_markup=reply_markup
        )
        
        # Закрепляем сообщение дня
        await self._pin_stage_message(context, game, "day", day_message.message_id)
        
        # Создаем и сохраняем задачу таймера дневной фазы
        day_timer_task = asyncio.create_task(self.day_phase_timer(update, context, game))
        game.set_day_timer_task(day_timer_task)

    async def day_phase_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Таймер дневной фазы с диагностикой"""
        try:
            logger.info(f"Запущен таймер дневной фазы для игры {game.chat_id}")
            await asyncio.sleep(300)  # 5 минут
            
            # Проверяем, что игра все еще в дневной фазе
            if game.phase == GamePhase.DAY:
                logger.info(f"Таймер дневной фазы завершен, переходим к голосованию для игры {game.chat_id}")
                await self.start_voting_phase(update, context, game)
            else:
                logger.info(f"Таймер дневной фазы завершен, но фаза изменилась на {game.phase} для игры {game.chat_id}")
                
        except asyncio.CancelledError:
            logger.info(f"Таймер дневной фазы отменен для игры {game.chat_id}")
            raise
        except Exception as e:
            logger.error(f"Ошибка в таймере дневной фазы для игры {game.chat_id}: {e}")
        finally:
            # Очищаем ссылку на задачу
            game.day_timer_task = None

    async def start_voting_phase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        game.start_voting()

        alive_players = game.get_alive_players()
        if len(alive_players) < 2:
            await self._end_game_internal(update, context, game, "Недостаточно игроков для голосования")
            return

        # Открепляем сообщение дня
        await self._unpin_previous_stage_message(context, game, "voting")

        # Отправляем уведомление в общий чат
        chat_message = (
            "🌲 \"Кого же мы изгоним из нашего Леса?\" - шепчут зверушки между собой.\n\n"
            "🦌 Зайцы переглядываются, 🐺 волки притворяются невинными, а 🦊 лиса уже готовит план...\n\n"
            "⏰ У вас есть 2 минуты, чтобы решить судьбу одного из обитателей леса!\n"
            "📱 Проверьте личные сообщения с ботом - там вас ждет важное решение."
        )
        
        voting_message = None
        if hasattr(update, 'message') and update.message:
            voting_message = await update.message.reply_text(chat_message)
        elif hasattr(update, 'callback_query') and update.callback_query:
            voting_message = await context.bot.send_message(chat_id=game.chat_id, text=chat_message, message_thread_id=game.thread_id)
        
        # Закрепляем сообщение голосования
        if voting_message:
            await self._pin_stage_message(context, game, "voting", voting_message.message_id)

        # Отправляем меню голосования каждому живому игроку в личку
        for voter in alive_players:
            # Исключаем самого голосующего из списка целей
            voting_targets = [p for p in alive_players if p.user_id != voter.user_id]
            keyboard = [[InlineKeyboardButton(f"🗳️ {p.username}", callback_data=f"vote_{p.user_id}")] for p in voting_targets]
            # Добавляем кнопку "Пропустить голосование"
            keyboard.append([InlineKeyboardButton("⏭️ Пропустить голосование", callback_data="vote_skip")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await context.bot.send_message(
                    chat_id=voter.user_id,
                    text=(
                        "🌲 Время решать судьбу леса!\n\n"
                        "🦌 Кого из обитателей леса вы считаете опасным для остальных зверушек?\n"
                        "⏰ У вас есть 2 минуты, чтобы сделать свой выбор:"
                    ),
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Не удалось отправить меню голосования игроку {voter.user_id}: {e}")

        # Сохраняем информацию о количестве игроков для проверки досрочного завершения
        game.total_voters = len(alive_players)
        game.voting_type = "exile"  # Помечаем тип голосования
        
        asyncio.create_task(self.voting_timer(context, game, update))

    async def start_wolf_voting_phase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Начинает специальное голосование за волка"""
        game.start_voting()

        alive_players = game.get_alive_players()
        if len(alive_players) < 2:
            if hasattr(update, 'message') and update.message:
                await update.message.reply_text("❌ Недостаточно игроков для голосования!")
            elif hasattr(update, 'callback_query') and update.callback_query:
                await context.bot.send_message(chat_id=game.chat_id, text="❌ Недостаточно игроков для голосования!", message_thread_id=game.thread_id)
            return

        # Отправляем уведомление в общий чат
        chat_message = (
            "🐺 \"А кто же среди нас волк?\" - шепчут зверушки.\n\n"
            "🦌 Зайцы оглядываются по сторонам, 🦊 лиса притворяется невинной...\n"
            "🌲 Кого вы подозреваете в том, что он хищник?\n\n"
            "⚠️ Это голосование НЕ изгонит игрока - просто попытка выявить волка!\n"
            "📱 Проверьте личные сообщения с ботом для голосования."
        )
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(chat_message)
        elif hasattr(update, 'callback_query') and update.callback_query:
            await context.bot.send_message(chat_id=game.chat_id, text=chat_message, message_thread_id=game.thread_id)

        # Отправляем меню голосования каждому живому игроку в личку
        for voter in alive_players:
            # Исключаем самого голосующего из списка целей
            voting_targets = [p for p in alive_players if p.user_id != voter.user_id]
            keyboard = [[InlineKeyboardButton(f"🐺 {p.username}", callback_data=f"wolf_vote_{p.user_id}")] for p in voting_targets]
            # Добавляем кнопку "Пропустить голосование"
            keyboard.append([InlineKeyboardButton("⏭️ Пропустить голосование", callback_data="wolf_vote_skip")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await context.bot.send_message(
                    chat_id=voter.user_id,
                    text=(
                        "🐺 \"Кто же среди нас волк?\" - думаете вы.\n\n"
                        "🦌 Кого из обитателей леса вы подозреваете в том, что он хищник?\n"
                        "⚠️ Этот зверек НЕ будет изгнан - просто попытка выявить волка!\n\n"
                        f"⏰ У вас есть 2 минуты на размышления (Ваша роль: {self.get_role_info(voter.role)['name']}):"
                    ),
                    reply_markup=reply_markup
                )
                logger.info(f"Меню голосования за волка отправлено игроку {voter.username} (роль: {self.get_role_name_russian(voter.role)})")
            except Exception as e:
                logger.error(f"Не удалось отправить меню голосования игроку {voter.user_id} ({voter.username}): {e}")
                # Если не удалось отправить в личку, попробуем уведомить в общем чате
                try:
                    await context.bot.send_message(
                        chat_id=game.chat_id,
                        text=f"❌ @{voter.username}, не удалось отправить меню голосования в личные сообщения. Откройте диалог с ботом и попробуйте снова.",
                        message_thread_id=game.thread_id
                    )
                except Exception:
                    pass

        # Сохраняем информацию о количестве игроков для проверки досрочного завершения
        game.total_voters = len(alive_players)
        game.voting_type = "wolf"  # Помечаем тип голосования
        
        # Отправляем дублирующие кнопки голосования в группу для тех, кто не получил личное сообщение
        await asyncio.sleep(2)  # Даём время на отправку личных сообщений
        
        group_keyboard = []
        for p in alive_players:
            group_keyboard.append([InlineKeyboardButton(f"🐺 Подозреваю {p.username}", callback_data=f"wolf_vote_{p.user_id}")])
        # Добавляем кнопку "Пропустить голосование" в группе
        group_keyboard.append([InlineKeyboardButton("⏭️ Пропустить голосование", callback_data="wolf_vote_skip")])
        
        group_reply_markup = InlineKeyboardMarkup(group_keyboard)
        
        await context.bot.send_message(
            chat_id=game.chat_id,
            text=(
                "🐺 Резервное голосование в группе!\n\n"
                "Если вы не получили личное сообщение для голосования, можете проголосовать здесь:\n"
                "(Каждый игрок может проголосовать только один раз)"
            ),
            reply_markup=group_reply_markup,
            message_thread_id=game.thread_id
        )
        
        asyncio.create_task(self.wolf_voting_timer(context, game))

    async def wolf_voting_timer(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Таймер для голосования за волка с проверкой досрочного завершения"""
        for _ in range(120):  # Проверяем каждую секунду в течение 2 минут
            await asyncio.sleep(1)
            
            # Проверяем, все ли проголосовали
            if game.phase == GamePhase.VOTING and hasattr(game, 'total_voters'):
                if len(game.votes) >= game.total_voters:
                    # Все проголосовали - завершаем досрочно
                    await context.bot.send_message(
                        chat_id=game.chat_id, 
                        text="⚡ Все игроки проголосовали! Голосование завершено досрочно.",
                        message_thread_id=game.thread_id
                    )
                    await self.process_wolf_voting_results(context, game)
                    return
            
            # Если игра завершилась или фаза изменилась - выходим
            if game.phase != GamePhase.VOTING:
                return
        
        # Время вышло
        if game.phase == GamePhase.VOTING:
            await self.process_wolf_voting_results(context, game)

    async def voting_timer(self, context: ContextTypes.DEFAULT_TYPE, game: Game, update: Update):
        """Таймер для голосования с проверкой досрочного завершения"""
        logger.info(f"Голосование начато. Игроков: {len(game.get_alive_players())}, total_voters: {getattr(game, 'total_voters', 'НЕ УСТАНОВЛЕНО')}")
        
        for i in range(120):  # Проверяем каждую секунду в течение 2 минут
            await asyncio.sleep(1)
            
            # Проверяем, все ли проголосовали
            if game.phase == GamePhase.VOTING and hasattr(game, 'total_voters') and hasattr(game, 'voting_type'):
                current_votes = len(game.votes)
                expected_voters = game.total_voters
                
                logger.info(f"Голосование ({game.voting_type}): {current_votes}/{expected_voters} проголосовали")
                
                # Проверяем досрочное завершение только для голосования за изгнание
                if game.voting_type == "exile" and current_votes >= expected_voters:
                    # Проверяем, не завершается ли уже голосование
                    if not (hasattr(game, 'exile_voting_completed') and game.exile_voting_completed):
                        logger.info("Все игроки проголосовали! Завершаем голосование досрочно.")
                        # Создаем задачу для досрочного завершения (она сама обработает результаты)
                        asyncio.create_task(self.complete_exile_voting_early(context, game))
                    return
            
            # Если игра завершилась или фаза изменилась - выходим
            if game.phase != GamePhase.VOTING:
                logger.info(f"Голосование прервано: фаза изменилась на {game.phase}")
                return
        
        # Время вышло
        if game.phase == GamePhase.VOTING:
            logger.info("Время голосования истекло. Обрабатываем результаты.")
            await self.process_voting_results(update, context, game)
        else:
            logger.info(f"Голосование завершилось, но фаза уже {game.phase}")

    async def process_voting_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        logger.info(f"Обработка результатов голосования. Голосов: {len(game.votes)}")
        
        # Проверяем, не были ли результаты уже обработаны
        if hasattr(game, 'voting_results_processed') and game.voting_results_processed:
            logger.info("Результаты голосования уже были обработаны, пропускаем")
            return
        
        game.voting_results_processed = True  # Помечаем как обработанные
        
        exiled_player = game.process_voting()
        
        # Получаем детальную информацию о голосовании
        voting_details = game.get_voting_details()
        
        # Формируем сообщение с результатами
        if exiled_player:
            role_name = self.get_role_info(exiled_player.role)['name']
            result_text = f"🌲 {exiled_player.username} покидает лес навсегда...\n🦌 Оказалось, что это был {role_name}!"
        else:
            result_text = f"🌲 {voting_details['voting_summary']}"
        
        # Добавляем детальную информацию о голосовании
        result_text += "\n\n📊 **Результаты голосования:**\n"
        
        for voter_name, vote_info in voting_details['vote_breakdown'].items():
            result_text += f"• {voter_name}: {vote_info}\n"
        
        # Добавляем статистику
        result_text += "\n📈 **Статистика:**\n"
        result_text += f"• Всего голосов: {voting_details['total_votes']}\n"
        result_text += f"• За изгнание: {voting_details['votes_for_exile']}\n"
        result_text += f"• Пропустили: {voting_details['skip_votes']}\n"
        
        logger.info(f"Результат голосования: {voting_details['voting_summary']}")
        
        # Всегда отправляем результат в правильную тему чата
        try:
            await context.bot.send_message(
                chat_id=game.chat_id, 
                text=result_text, 
                message_thread_id=game.thread_id
            )
        except Exception as e:
            logger.error(f"Ошибка отправки результатов голосования: {e}")
            # Fallback без темы
            await context.bot.send_message(chat_id=game.chat_id, text=result_text)

        # Очищаем атрибуты голосования
        if hasattr(game, 'total_voters'):
            delattr(game, 'total_voters')
        if hasattr(game, 'voting_type'):
            delattr(game, 'voting_type')
        if hasattr(game, 'voting_results_processed'):
            delattr(game, 'voting_results_processed')
        if hasattr(game, 'exile_voting_completed'):
            delattr(game, 'exile_voting_completed')

        # Проверяем условия окончания игры
        winner = game.check_game_end()
        if winner:
            logger.info(f"Игра завершена! Победила команда: {winner}")
            await self.end_game_winner(update, context, game, winner)
        else:
            logger.info("Игра продолжается. Начинаем новую ночь.")
            await self.start_new_night(update, context, game)

    async def process_wolf_voting_results(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Обрабатывает результаты голосования за волка"""
        if not game.votes:
            await context.bot.send_message(
                chat_id=game.chat_id,
                text="🤷‍♂️ Никто не проголосовал в голосовании 'Кто волк?'!",
                message_thread_id=game.thread_id
            )
            game.start_day()  # Возвращаемся к дневной фазе
            return

        # Подсчет голосов
        vote_counts = {}
        for target_id in game.votes.values():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

        # Находим игрока с максимальным количеством голосов
        max_votes = max(vote_counts.values())
        max_vote_players = [pid for pid, votes in vote_counts.items() if votes == max_votes]

        # Формируем результат
        if len(max_vote_players) > 1:
            # Ничья
            suspects = [game.players[pid].username for pid in max_vote_players]
            result_text = f"🤔 Ничья в голосовании 'Кто волк?'!\n\nПодозреваемые: {', '.join(suspects)}"
        else:
            # Есть лидер
            suspect_id = max_vote_players[0]
            suspect = game.players[suspect_id]
            votes = vote_counts[suspect_id]
            
            # Проверяем, действительно ли это волк
            is_actually_wolf = suspect.role == Role.WOLF
            
            if is_actually_wolf:
                result_text = (f"🎯 Результат голосования 'Кто волк?':\n\n"
                              f"🐺 {suspect.username} получил больше всего голосов ({votes}) и действительно оказался волком!\n"
                              "👏 Жители угадали!")
            else:
                result_text = (f"🎯 Результат голосования 'Кто волк?':\n\n"
                              f"🐰 {suspect.username} получил больше всего голосов ({votes}), но оказался {self.get_role_info(suspect.role)['name']}!\n"
                              "😅 Жители ошиблись!")

        await context.bot.send_message(chat_id=game.chat_id, text=result_text, message_thread_id=game.thread_id)
        
        # Очищаем голоса и возвращаемся к дневной фазе
        game.votes.clear()
        if hasattr(game, 'total_voters'):
            delattr(game, 'total_voters')
        if hasattr(game, 'voting_type'):
            delattr(game, 'voting_type')
        game.start_day()
        
        # Возвращаем кнопки дневной фазы
        keyboard = [
            [InlineKeyboardButton("🏁 Завершить обсуждение", callback_data="day_end_discussion")],
            [InlineKeyboardButton("🐺 Выбрать волка", callback_data="day_choose_wolf")],
            [InlineKeyboardButton("🔍 Диагностика таймера", callback_data="day_timer_diagnostics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=game.chat_id,
            text="☀️ Продолжается дневное обсуждение.\nИспользуйте кнопки ниже для управления фазой:",
            reply_markup=reply_markup
        )

    async def start_new_night(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        # Открепляем сообщение голосования перед началом новой ночи
        await self._unpin_previous_stage_message(context, game, "night")
        await self.start_night_phase(update, context, game)

    async def _unpin_all_bot_messages(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Открепляет все закрепленные сообщения бота в чате"""
        try:
            # Открепляем сообщение о присоединении
            if hasattr(game, 'pinned_message_id') and game.pinned_message_id:
                try:
                    await context.bot.unpin_chat_message(
                        chat_id=game.chat_id,
                        message_id=game.pinned_message_id
                    )
                    logger.info(f"Откреплено сообщение о присоединении: {game.pinned_message_id}")
                    game.pinned_message_id = None
                except Exception as e:
                    logger.warning(f"Не удалось открепить сообщение о присоединении: {e}")
            
            # Открепляем все сообщения этапов
            for stage, message_id in game.stage_pinned_messages.items():
                try:
                    await context.bot.unpin_chat_message(
                        chat_id=game.chat_id,
                        message_id=message_id
                    )
                    logger.info(f"Откреплено сообщение этапа {stage}: {message_id}")
                except Exception as e:
                    logger.warning(f"Не удалось открепить сообщение этапа {stage}: {e}")
            
            # Очищаем все ID закрепленных сообщений этапов
            game.clear_all_stage_pinned_messages()
            
            # Открепляем все закрепленные сообщения бота в этом чате
            try:
                chat = await context.bot.get_chat(game.chat_id)
                if chat.pinned_message:
                    # Проверяем, является ли закрепленное сообщение нашим
                    if hasattr(chat.pinned_message, 'from_user') and chat.pinned_message.from_user.id == context.bot.id:
                        await context.bot.unpin_chat_message(
                            chat_id=game.chat_id,
                            message_id=chat.pinned_message.message_id
                        )
                        logger.info(f"Откреплено закрепленное сообщение бота: {chat.pinned_message.message_id}")
            except Exception as e:
                logger.warning(f"Не удалось проверить/открепить закрепленные сообщения: {e}")
                
        except Exception as e:
            logger.error(f"Ошибка при откреплении сообщений: {e}")

    async def _unpin_previous_stage_message(self, context: ContextTypes.DEFAULT_TYPE, game: Game, current_stage: str):
        """Открепляет сообщение предыдущего этапа"""
        try:
            # Определяем предыдущий этап
            stage_order = ["night", "day", "voting"]
            current_index = stage_order.index(current_stage) if current_stage in stage_order else -1
            
            if current_index > 0:
                previous_stage = stage_order[current_index - 1]
                previous_message_id = game.get_stage_pinned_message(previous_stage)
                
                if previous_message_id:
                    try:
                        await context.bot.unpin_chat_message(
                            chat_id=game.chat_id,
                            message_id=previous_message_id
                        )
                        logger.info(f"Откреплено сообщение этапа {previous_stage}: {previous_message_id}")
                        game.clear_stage_pinned_message(previous_stage)
                    except Exception as e:
                        logger.warning(f"Не удалось открепить сообщение этапа {previous_stage}: {e}")
        except Exception as e:
            logger.error(f"Ошибка при откреплении сообщения предыдущего этапа: {e}")

    async def _pin_stage_message(self, context: ContextTypes.DEFAULT_TYPE, game: Game, stage: str, message_id: int):
        """Закрепляет сообщение этапа"""
        try:
            await context.bot.pin_chat_message(
                chat_id=game.chat_id,
                message_id=message_id,
                disable_notification=True
            )
            game.set_stage_pinned_message(stage, message_id)
            logger.info(f"Закреплено сообщение этапа {stage}: {message_id}")
        except Exception as e:
            logger.error(f"Ошибка при закреплении сообщения этапа {stage}: {e}")

    async def tag_game_participants(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Тегирует всех участников игры с оповещением о начале"""
        try:
            # Формируем список тегов участников
            player_tags = []
            for player in game.players.values():
                if player.username:
                    player_tags.append(f"@{player.username}")
                else:
                    player_tags.append(f"[{player.first_name or 'Игрок'}](tg://user?id={player.user_id})")
            
            # Создаем сообщение с тегами в лесном стиле
            tag_message = (
                "🌲 **Лес просыпается...** 🌲\n\n"
                "🦌 Все лесные зверушки собрались на поляне для игры в Лес и Волки!\n"
                "🍃 Шелест листьев, пение птиц, и тайные заговоры в тени деревьев...\n\n"
                f"🐾 **Участники лесного совета:** {', '.join(player_tags)}\n\n"
                "🎭 Роли уже распределены среди зверушек! Проверьте личные сообщения с ботом.\n"
                "🌙 Скоро наступит первая ночь в лесу, когда хищники выйдут на охоту..."
            )
            
            # Отправляем сообщение с тегами
            if hasattr(update, 'message') and update.message:
                await update.message.reply_text(tag_message, parse_mode='Markdown')
            else:
                await context.bot.send_message(
                    chat_id=game.chat_id,
                    text=tag_message,
                    parse_mode='Markdown',
                    message_thread_id=game.thread_id
                )
            
            logger.info(f"Отправлено уведомление о начале игры с тегами участников для игры {game.chat_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при тегировании участников игры: {e}")

    async def end_game_winner(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game, winner: Optional[Team] = None):
        if getattr(game, "game_over_sent", False):
            return
        game.game_over_sent = True

        game.phase = GamePhase.GAME_OVER
        
        # Отменяем таймер дневной фазы при завершении игры
        game.cancel_day_timer()
        
        # Открепляем все закрепленные сообщения бота при завершении игры
        await self._unpin_all_bot_messages(context, game)
        
        # Используем новую логику завершения игры
        try:
            from game_end_logic import GameEndLogic
            game_end_logic = GameEndLogic(game)
            
            # Создаем результат для отображения
            if winner:
                result = {
                    "winner": winner,
                    "reason": "🏆 Игра завершена победой одной из команд!",
                    "details": f"Победители: {'Травоядные' if winner == Team.HERBIVORES else 'Хищники'}"
                }
            else:
                result = {
                    "winner": Team.HERBIVORES,  # По умолчанию
                    "reason": "🏁 Игра окончена!",
                    "details": "Недостаточно игроков для продолжения."
                }
            
            # Получаем детальное сообщение о завершении игры
            message_text = game_end_logic.get_game_over_message(result)
            
        except ImportError:
            # Fallback на старую логику
            if winner:
                winner_text = "🏆 Травоядные победили!" if winner == Team.HERBIVORES else "🏆 Хищники победили!"
                message_text = f"🎉 Игра окончена! {winner_text}\n\n📊 Статистика игры:\nВсего игроков: {len(game.players)}\nРаундов сыграно: {game.current_round}"
            else:
                message_text = "🏁 Игра окончена!\nНедостаточно игроков для продолжения."
        
        # Отправляем в чат с правильной темой
        try:
            await context.bot.send_message(
                chat_id=game.chat_id,
                text=message_text,
                message_thread_id=game.thread_id,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о завершении игры: {e}")
            # Fallback - если update есть, попробуем через reply
            if update and hasattr(update, 'message') and update.message:
                try:
                    await update.message.reply_text(message_text, parse_mode='Markdown')
                except Exception as e2:
                    logger.error(f"Fallback тоже не сработал: {e2}")

        for pid in list(game.players.keys()):
            if pid in self.player_games:
                del self.player_games[pid]

        chat_id = game.chat_id
        if chat_id in self.games:
            del self.games[chat_id]
        if chat_id in self.night_actions:
            del self.night_actions[chat_id]
        if chat_id in self.night_interfaces:
            del self.night_interfaces[chat_id]
        
        # Дополнительная очистка - удаляем все записи игроков из этого чата
        players_to_remove = []
        for user_id, game_chat_id in self.player_games.items():
            if game_chat_id == chat_id:
                players_to_remove.append(user_id)
        
        for user_id in players_to_remove:
            del self.player_games[user_id]

    # ---------------- callbacks: voting, night actions, welcome buttons ----------------
    async def handle_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()

        # Проверяем права пользователя
        update = Update(update_id=0, callback_query=query)
        has_permission, error_msg = await self.check_user_permissions(
            update, context, "member"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return

        user_id = query.from_user.id
        
        # Находим игру по игроку
        if user_id not in self.player_games:
            await query.answer("❌ Вы не участвуете в игре!", show_alert=True)
            return

        chat_id = self.player_games[user_id]
        if chat_id not in self.games:
            await query.edit_message_text("❌ Игра не найдена!")
            return

        game = self.games[chat_id]
        if game.phase != GamePhase.VOTING:
            await query.answer("❌ Голосование уже завершено!", show_alert=True)
            return

        # Проверяем пропуск голосования
        if query.data == "vote_skip":
            # Добавляем голос "пропустить" в игру
            success, already_voted = game.vote(user_id, None)  # None означает пропуск
            if success:
                await query.edit_message_text("⏭️ Вы пропустили голосование!\n\n🕐 Ожидайте результатов голосования...")
                
                # Проверяем, все ли проголосовали (включая пропуски)
                if hasattr(game, 'total_voters') and hasattr(game, 'voting_type') and game.voting_type == "exile":
                    if len(game.votes) >= game.total_voters:
                        # Проверяем, не завершается ли уже голосование
                        if not (hasattr(game, 'exile_voting_completed') and game.exile_voting_completed):
                            # Все проголосовали - завершаем досрочно
                            asyncio.create_task(self.complete_exile_voting_early(context, game))
            else:
                await query.edit_message_text("❌ Не удалось зарегистрировать пропуск голосования!")
            return
        
        target_id = int(query.data.split('_', 1)[1])
        
        # Дополнительная проверка на голосование за себя
        if target_id == user_id:
            await query.answer("❌ Вы не можете голосовать за себя!\n\n🔄 Выберите другого игрока для голосования.", show_alert=True)
            return
        
        success, already_voted = game.vote(user_id, target_id)
        
        if success:
            target_player = game.players[target_id]
            if already_voted:
                await query.edit_message_text(f"🔄 Ваш голос изменен!\nТеперь вы голосуете за изгнание: {target_player.username}\n\n🕐 Ожидайте результатов голосования...")
            else:
                await query.edit_message_text(f"✅ Ваш голос зарегистрирован!\nВы проголосовали за изгнание: {target_player.username}\n\n🕐 Ожидайте результатов голосования...")
            
            # Проверяем, все ли проголосовали (только для обычного голосования)
            if hasattr(game, 'total_voters') and hasattr(game, 'voting_type') and game.voting_type == "exile":
                if len(game.votes) >= game.total_voters:
                    # Проверяем, не завершается ли уже голосование
                    if not (hasattr(game, 'exile_voting_completed') and game.exile_voting_completed):
                        # Все проголосовали - завершаем досрочно
                        asyncio.create_task(self.complete_exile_voting_early(context, game))
        else:
            await query.edit_message_text("❌ Не удалось зарегистрировать голос!")

    async def handle_night_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()
        
        # Проверяем права пользователя
        update = Update(update_id=0, callback_query=query)
        has_permission, error_msg = await self.check_user_permissions(
            update, context, "member"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return
        
        user_id = query.from_user.id

        if user_id in self.player_games:
            chat_id = self.player_games[user_id]
            if chat_id in self.night_interfaces:
                await self.night_interfaces[chat_id].handle_night_action(update, context)
            else:
                await query.edit_message_text("❌ Игра не найдена!")
        else:
            await query.answer("❌ Вы не участвуете в игре!", show_alert=True)

    async def handle_welcome_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()

        # Проверяем права пользователя
        update = Update(update_id=0, callback_query=query)
        has_permission, error_msg = await self.check_user_permissions(
            update, context, "member"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return

        if query.data == "welcome_start_game":
            # welcome_start_game может означать как присоединение, так и начало игры
            # Проверяем контекст - если игра уже есть и можно начать, то начинаем
            chat_id = query.message.chat.id
            if chat_id in self.games:
                game = self.games[chat_id]
                if game.phase == GamePhase.WAITING and game.can_start_game():
                    # Начинаем игру
                    await self.handle_start_game_callback(query, context)
                else:
                    # Присоединяемся к игре
                    await self.join_from_callback(query, context)
            else:
                # Присоединяемся к игре (создаем новую)
                await self.join_from_callback(query, context)
        elif query.data == "welcome_rules":
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="welcome_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📖 Правила игры 'Лес и Волки':\n\n"
                "🎭 Роли:\n"
                "🐺 Волки (Хищники) - стая, по ночам съедает по зверю\n"
                "🦊 Лиса (Хищники) - ворует запасы еды\n"
                "🐰 Зайцы (Травоядные) - мирные зверушки\n"
                "🦫 Крот (Травоядные) - роет норки, узнаёт команды других зверей\n"
                "🦦 Бобёр (Травоядные) - возвращает украденные запасы\n\n"
                "🌙 Ночные фазы: Волки → Лиса → Бобёр → Крот\n"
                "☀️ Дневные фазы: обсуждение и голосование\n"
                "🏆 Цель: уничтожить команду противника",
                reply_markup=reply_markup
            )
        elif query.data == "welcome_status":
            await self.status_from_callback(query, context)
        elif query.data == "welcome_cancel_game":
            await self.cancel_game_from_welcome(query, context)
        elif query.data == "welcome_back":
            # Возвращаемся к приветственному сообщению
            keyboard = [
                [InlineKeyboardButton("🎮 Начать игру", callback_data="welcome_start_game")],
                [InlineKeyboardButton("📖 Правила игры", callback_data="welcome_rules")],
                [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")],
            [InlineKeyboardButton("🔍 Проверить этап", callback_data="check_stage")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            welcome_text = (
                "🌲 *Добро пожаловать в Лес и Волки!* 🌲\n\n"
                "🎭 Это ролевая игра в стиле 'Мафия' с лесными зверушками!\n\n"
                "🐺 *Хищники:* Волки и Лиса\n"
                "🐰 *Травоядные:* Зайцы, Крот и Бобёр\n\n"
                "🎯 *Цель:* Уничтожить команду противника!\n\n"
                f"👥 Для игры нужно минимум {self.global_settings.get_min_players()} игроков\n"
                f"{'🧪 ТЕСТОВЫЙ РЕЖИМ АКТИВЕН' if self.global_settings.is_test_mode() else ''}\n"
                "⏰ Игра состоит из ночных и дневных фаз\n\n"
                "Нажмите кнопку ниже, чтобы начать!"
            )

            await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def cancel_game_from_welcome(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Отменяет игру из приветственного сообщения"""
        chat_id = query.message.chat.id
        user_id = query.from_user.id

        # Проверяем права администратора
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            if chat_member.status not in ['creator', 'administrator']:
                await query.edit_message_text("❌ Только администраторы могут отменять игру!")
                return
        except Exception:
            await query.edit_message_text("❌ Ошибка проверки прав!")
            return

        if chat_id not in self.games:
            await query.edit_message_text("❌ В этом чате нет активной игры!")
            return

        game = self.games[chat_id]

        if game.phase != GamePhase.WAITING:
            await query.edit_message_text("❌ Можно отменить только игру в ожидании игроков!")
            return

        # Удаляем игру
        del self.games[chat_id]
        
        # Открепляем сообщение о присоединении, если оно есть
        if hasattr(game, 'pinned_message_id') and game.pinned_message_id:
            try:
                await context.bot.unpin_chat_message(chat_id, game.pinned_message_id)
            except Exception:
                logger.warning("Не удалось открепить сообщение")

        await query.edit_message_text("🛑 Игра отменена администратором!")

    async def handle_day_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает действия дневной фазы"""
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()

        # Проверяем права пользователя (только администраторы)
        update = Update(update_id=0, callback_query=query)
        has_permission, error_msg = await self.check_user_permissions(
            update, context, "admin"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return

        chat_id = query.message.chat.id
        user_id = query.from_user.id

        if chat_id not in self.games:
            await query.edit_message_text("❌ В этом чате нет активной игры!")
            return

        game = self.games[chat_id]

        if query.data == "day_end_discussion":
            # Проверяем права пользователя
            has_permission, error_msg = await self.check_game_permissions(query, context, "day_end_discussion")
            if not has_permission:
                await query.answer(error_msg, show_alert=True)
                return
            
            if game.phase != GamePhase.DAY:
                await query.edit_message_text("❌ Сейчас не время обсуждения!")
                return

            # Отменяем таймер дневной фазы
            game.cancel_day_timer()
            logger.info(f"Дневная фаза завершена досрочно администратором для игры {game.chat_id}")

            await query.edit_message_text("🏁 Администратор завершил обсуждение досрочно!")
            # Создаем mock update для start_voting_phase
            mock_update = type('MockUpdate', (), {
                'message': type('MockMessage', (), {
                    'reply_text': lambda self, text, **kwargs: context.bot.send_message(
                        chat_id=game.chat_id, 
                        text=text, 
                        message_thread_id=game.thread_id
                    )
                })()
            })()
            await self.start_voting_phase(mock_update, context, game)

        elif query.data == "day_timer_diagnostics":
            # Проверяем права пользователя
            has_permission, error_msg = await self.check_game_permissions(query, context, "day_timer_diagnostics")
            if not has_permission:
                await query.answer(error_msg, show_alert=True)
                return
            
            if game.phase != GamePhase.DAY:
                await query.edit_message_text("❌ Диагностика таймера доступна только в дневной фазе!")
                return
            
            # Получаем диагностическую информацию
            timer_status = game.get_day_timer_status()
            phase_info = f"Текущая фаза: {game.phase.value}"
            
            # Дополнительная информация
            from datetime import datetime
            if game.day_start_time:
                elapsed = (datetime.now() - game.day_start_time).total_seconds()
                elapsed_minutes = int(elapsed // 60)
                elapsed_seconds = int(elapsed % 60)
                time_info = f"Время с начала дня: {elapsed_minutes}м {elapsed_seconds}с"
            else:
                time_info = "Время начала дня не записано"
            
            # Информация о задаче таймера
            if game.day_timer_task:
                if game.day_timer_task.done():
                    task_info = "Задача таймера: завершена"
                else:
                    task_info = "Задача таймера: активна"
            else:
                task_info = "Задача таймера: не найдена"
            
            diagnostics_text = (
                f"🔍 **Диагностика дневного таймера**\n\n"
                f"📊 {phase_info}\n"
                f"⏰ {timer_status}\n"
                f"🕐 {time_info}\n"
                f"🔧 {task_info}\n\n"
                "💡 Если таймер не работает, попробуйте завершить обсуждение вручную."
            )
            
            # Создаем кнопку "Закрыть"
            keyboard = [[InlineKeyboardButton("❌ Закрыть", callback_data="close_diagnostics")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(diagnostics_text, parse_mode='Markdown', reply_markup=reply_markup)

        elif query.data == "close_diagnostics":
            await query.edit_message_text("🔍 Диагностика закрыта.")

        elif query.data == "day_choose_wolf":
            # Проверяем права пользователя
            has_permission, error_msg = await self.check_game_permissions(query, context, "day_choose_wolf")
            if not has_permission:
                await query.answer(error_msg, show_alert=True)
                return
            
            if game.phase != GamePhase.DAY:
                await query.edit_message_text("❌ Голосование за волка доступно только в дневной фазе!")
                return

            await query.edit_message_text("🐺 Администратор инициировал голосование 'Кто волк?'!")
            # Создаем mock update для start_wolf_voting_phase
            mock_update = type('MockUpdate', (), {
                'message': type('MockMessage', (), {
                    'reply_text': lambda self, text, **kwargs: context.bot.send_message(
                        chat_id=game.chat_id, 
                        text=text, 
                        message_thread_id=game.thread_id
                    )
                })()
            })()
            await self.start_wolf_voting_phase(mock_update, context, game)

    # ---------------- settings UI (basic, non-persistent) ----------------
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_game_permissions(update, context, "settings")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        # Проверяем, что это группа, а не личные сообщения
        if chat_id == user_id:
            await update.message.reply_text("❌ Настройки доступны только в группах!")
            return

        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут изменять настройки!")
            return

        test_mode_text = "🧪 Тестовый режим: ВКЛ" if self.global_settings.is_test_mode() else "🧪 Тестовый режим: ВЫКЛ"

        keyboard = [
            [InlineKeyboardButton("⏱️ Изменить таймеры", callback_data="settings_timers")],
            [InlineKeyboardButton("🎭 Изменить распределение ролей", callback_data="settings_roles")],
            [InlineKeyboardButton(test_mode_text, callback_data="settings_toggle_test")],
            [InlineKeyboardButton("📈 Глобальные настройки", callback_data="settings_global")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="settings_close")]
        ]

        # Если есть активная игра, добавляем кнопку сброса статистики
        if chat_id in self.games:
            keyboard.insert(-1, [InlineKeyboardButton("📊 Сбросить статистику", callback_data="settings_reset")])

        settings_text = (
            "⚙️ Настройки бота\n\n"
            f"{self.global_settings.get_settings_summary()}\n\n"
            "Выберите, что хотите изменить:"
        )

        await update.message.reply_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()
        
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_game_permissions(
            query, context, "settings"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return
        
        user_id = query.from_user.id
        chat_id = query.message.chat.id

        game = self.games.get(chat_id)  # Игра может отсутствовать
        
        if query.data == "settings_timers":
            await self.show_timer_settings(query, context)
        elif query.data == "settings_roles":
            await self.show_role_settings(query, context)
        elif query.data == "settings_toggle_test":
            await self.toggle_test_mode(query, context, game)
        elif query.data == "settings_global":
            await self.show_global_settings(query, context)
        elif query.data == "settings_reset":
            if game:
                await self.reset_game_stats(query, context, game)
            else:
                await query.edit_message_text("❌ Нет активной игры для сброса статистики!")
        elif query.data == "settings_close":
            await query.edit_message_text("⚙️ Настройки закрыты")

    async def show_timer_settings(self, query, context):
        keyboard = [
            [InlineKeyboardButton("🌙 Изменить длительность ночи", callback_data="timer_night")],
            [InlineKeyboardButton("☀️ Изменить длительность дня", callback_data="timer_day")],
            [InlineKeyboardButton("🗳️ Изменить длительность голосования", callback_data="timer_vote")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")]
        ]
        await query.edit_message_text(
            "⏱️ Настройки таймеров\n\nТекущие значения:\n🌙 Ночь: 60 секунд\n☀️ День: 5 минут\n🗳️ Голосование: 2 минуты\n\nВыберите, что хотите изменить:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_role_settings(self, query, context):
        keyboard = [
            [InlineKeyboardButton("🐺 Волки: 25%", callback_data="role_wolves_25")],
            [InlineKeyboardButton("🦊 Лиса: 15%", callback_data="role_fox_15")],
            [InlineKeyboardButton("🦫 Крот: 15%", callback_data="role_mole_15")],
            [InlineKeyboardButton("🦦 Бобёр: 10%", callback_data="role_beaver_10")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")]
        ]
        await query.edit_message_text(
            "🎭 Настройки распределения ролей\n\nТекущие значения:\n🐺 Волки: 25%\n🦊 Лиса: 15%\n🦫 Крот: 15%\n🦦 Бобёр: 10%\n🐰 Зайцы: 35% (автоматически)\n\nВыберите роль для изменения:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def toggle_test_mode(self, query, context, game: Optional[Game]):
        # Проверяем, можно ли изменить тестовый режим
        if game and game.phase != GamePhase.WAITING:
            await query.edit_message_text("❌ Нельзя изменить тестовый режим во время игры! Дождитесь окончания игры.")
            return

        # Переключаем тестовый режим
        new_mode = self.global_settings.toggle_test_mode()
        mode_text = "ВКЛ" if new_mode else "ВЫКЛ"
        
        # Обновляем игру, если она есть
        if game:
            game.is_test_mode = new_mode
        
        await query.edit_message_text(
            f"✅ Тестовый режим переключен: {mode_text}\n\n"
            f"Минимум игроков: {self.global_settings.get_min_players()}\n\n"
            "Настройка сохранена и будет применена для следующих игр!"
        )

    async def show_global_settings(self, query, context):
        """Показывает глобальные настройки бота"""
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к настройкам", callback_data="settings_back")]
        ]
        
        await query.edit_message_text(
            self.global_settings.get_settings_summary(),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_timer_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает настройки таймеров"""
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()
        
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_game_permissions(
            query, context, "settings"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return
        
        chat_id = query.message.chat.id
        user_id = query.from_user.id

        # Обрабатываем конкретные настройки таймеров
        if query.data == "timer_night":
            await self.show_night_duration_options(query, context)
        elif query.data == "timer_day":
            await self.show_day_duration_options(query, context)
        elif query.data == "timer_vote":
            await self.show_vote_duration_options(query, context)
        else:
            # Показываем общее меню настроек таймеров
            await self.show_timer_settings(query, context)

    async def handle_role_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает настройки ролей"""
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()
        
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_game_permissions(
            query, context, "settings"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return
        
        chat_id = query.message.chat.id
        user_id = query.from_user.id

        # Обрабатываем конкретные настройки ролей
        if query.data.startswith("role_wolves_"):
            percentage = int(query.data.split("_")[2])
            self.global_settings.set("role_distribution", {
                **self.global_settings.get("role_distribution", {}),
                "wolves": percentage / 100.0
            })
            await query.edit_message_text(f"🐺 Доля волков изменена на {percentage}%!\n\n✅ Настройка сохранена и будет применена для следующих игр.")
        elif query.data.startswith("role_fox_"):
            percentage = int(query.data.split("_")[2])
            self.global_settings.set("role_distribution", {
                **self.global_settings.get("role_distribution", {}),
                "fox": percentage / 100.0
            })
            await query.edit_message_text(f"🦊 Доля лисы изменена на {percentage}%!\n\n✅ Настройка сохранена и будет применена для следующих игр.")
        elif query.data.startswith("role_mole_"):
            percentage = int(query.data.split("_")[2])
            self.global_settings.set("role_distribution", {
                **self.global_settings.get("role_distribution", {}),
                "mole": percentage / 100.0
            })
            await query.edit_message_text(f"🦫 Доля крота изменена на {percentage}%!\n\n✅ Настройка сохранена и будет применена для следующих игр.")
        elif query.data.startswith("role_beaver_"):
            percentage = int(query.data.split("_")[2])
            self.global_settings.set("role_distribution", {
                **self.global_settings.get("role_distribution", {}),
                "beaver": percentage / 100.0
            })
            await query.edit_message_text(f"🦦 Доля бобра изменена на {percentage}%!\n\n✅ Настройка сохранена и будет применена для следующих игр.")
        else:
            # Показываем настройки ролей
            await self.show_role_settings(query, context)

    async def handle_settings_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возвращает к главному меню настроек"""
        query = update.callback_query
        await query.answer()
        
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_game_permissions(
            query, context, "settings"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return
        
        chat_id = query.message.chat.id
        user_id = query.from_user.id

        test_mode_text = "🧪 Тестовый режим: ВКЛ" if self.global_settings.is_test_mode() else "🧪 Тестовый режим: ВЫКЛ"

        keyboard = [
            [InlineKeyboardButton("⏱️ Изменить таймеры", callback_data="settings_timers")],
            [InlineKeyboardButton("🎭 Изменить распределение ролей", callback_data="settings_roles")],
            [InlineKeyboardButton(test_mode_text, callback_data="settings_toggle_test")],
            [InlineKeyboardButton("📈 Глобальные настройки", callback_data="settings_global")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="settings_close")]
        ]

        # Если есть активная игра, добавляем кнопку сброса статистики
        if chat_id in self.games:
            keyboard.insert(-1, [InlineKeyboardButton("📊 Сбросить статистику", callback_data="settings_reset")])

        settings_text = (
            "⚙️ Настройки бота\n\n"
            f"{self.global_settings.get_settings_summary()}\n\n"
            "Выберите, что хотите изменить:"
        )

        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def show_night_duration_options(self, query, context):
        """Показывает опции для изменения длительности ночи"""
        keyboard = [
            [InlineKeyboardButton("30 секунд", callback_data="set_night_30")],
            [InlineKeyboardButton("45 секунд", callback_data="set_night_45")],
            [InlineKeyboardButton("60 секунд ✅", callback_data="set_night_60")],
            [InlineKeyboardButton("90 секунд", callback_data="set_night_90")],
            [InlineKeyboardButton("120 секунд", callback_data="set_night_120")],
            [InlineKeyboardButton("⬅️ Назад к таймерам", callback_data="timer_back")]
        ]
        await query.edit_message_text(
            "🌙 Настройка длительности ночи\n\nВыберите новую длительность ночной фазы:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_day_duration_options(self, query, context):
        """Показывает опции для изменения длительности дня"""
        keyboard = [
            [InlineKeyboardButton("2 минуты", callback_data="set_day_120")],
            [InlineKeyboardButton("3 минуты", callback_data="set_day_180")],
            [InlineKeyboardButton("5 минут ✅", callback_data="set_day_300")],
            [InlineKeyboardButton("7 минут", callback_data="set_day_420")],
            [InlineKeyboardButton("10 минут", callback_data="set_day_600")],
            [InlineKeyboardButton("⬅️ Назад к таймерам", callback_data="timer_back")]
        ]
        await query.edit_message_text(
            "☀️ Настройка длительности дня\n\nВыберите новую длительность дневной фазы:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_vote_duration_options(self, query, context):
        """Показывает опции для изменения длительности голосования"""
        keyboard = [
            [InlineKeyboardButton("1 минута", callback_data="set_vote_60")],
            [InlineKeyboardButton("1.5 минуты", callback_data="set_vote_90")],
            [InlineKeyboardButton("2 минуты ✅", callback_data="set_vote_120")],
            [InlineKeyboardButton("3 минуты", callback_data="set_vote_180")],
            [InlineKeyboardButton("5 минут", callback_data="set_vote_300")],
            [InlineKeyboardButton("⬅️ Назад к таймерам", callback_data="timer_back")]
        ]
        await query.edit_message_text(
            "🗳️ Настройка длительности голосования\n\nВыберите новую длительность голосования:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def reset_game_stats(self, query, context, game: Game):
        if game.phase != GamePhase.WAITING:
            await query.edit_message_text("❌ Нельзя сбросить статистику во время игры! Дождитесь окончания игры.")
            return
        game.current_round = 0
        game.game_start_time = None
        game.phase_end_time = None
        await query.edit_message_text("📊 Статистика игры сброшена!\n\n✅ Раунд: 0\n✅ Время начала: сброшено\n✅ Таймеры: сброшены")

    async def handle_timer_values(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает установку конкретных значений таймеров"""
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()
        
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_game_permissions(
            query, context, "settings"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return
        
        chat_id = query.message.chat.id
        user_id = query.from_user.id

        if query.data == "timer_back":
            await self.show_timer_settings(query, context)
            return

        # Обрабатываем установку конкретных значений
        if query.data.startswith("set_night_"):
            seconds = int(query.data.split("_")[2])
            # Сохраняем настройку
            self.global_settings.set("night_duration", seconds)
            await query.edit_message_text(f"🌙 Длительность ночи изменена на {seconds} секунд!\n\n✅ Новая настройка сохранена и будет применена для следующих игр.")
        elif query.data.startswith("set_day_"):
            seconds = int(query.data.split("_")[2])
            minutes = seconds // 60
            # Сохраняем настройку
            self.global_settings.set("day_duration", seconds)
            await query.edit_message_text(f"☀️ Длительность дня изменена на {minutes} минут!\n\n✅ Новая настройка сохранена и будет применена для следующих игр.")
        elif query.data.startswith("set_vote_"):
            seconds = int(query.data.split("_")[2])
            # Сохраняем настройку
            self.global_settings.set("voting_duration", seconds)
            if seconds >= 60:
                minutes = seconds // 60
                if seconds % 60 == 0:
                    time_text = f"{minutes} минут"
                else:
                    time_text = f"{minutes}.{(seconds % 60)//6} минуты"
            else:
                time_text = f"{seconds} секунд"
            await query.edit_message_text(f"🗳️ Длительность голосования изменена на {time_text}!\n\n✅ Новая настройка сохранена и будет применена для следующих игр.")

    # ---------------- night actions processing ----------------
    async def send_night_actions_to_players(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        chat_id = game.chat_id
        if chat_id in self.night_interfaces:
            await self.night_interfaces[chat_id].send_role_reminders(context)

    async def process_night_phase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        chat_id = game.chat_id
        if chat_id in self.night_actions:
            night_actions = self.night_actions[chat_id]
            night_interface = self.night_interfaces[chat_id]
            results = night_actions.process_all_actions()
            await night_interface.send_night_results(context, results)
            night_actions.clear_actions()
            
        # Проверяем условия автоматического завершения игры после ночных действий
        winner = game.check_game_end()
        if winner:
            await self.end_game_winner(update, context, game, winner)
            return

    async def handle_wolf_voting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает голосование за волка"""
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()

        # Проверяем права пользователя
        update = Update(update_id=0, callback_query=query)
        has_permission, error_msg = await self.check_user_permissions(
            update, context, "member"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return

        user_id = query.from_user.id
        
        # Находим игру по игроку
        if user_id not in self.player_games:
            await query.answer("❌ Вы не участвуете в игре!", show_alert=True)
            return

        chat_id = self.player_games[user_id]
        if chat_id not in self.games:
            await query.edit_message_text("❌ Игра не найдена!")
            return

        game = self.games[chat_id]
        if game.phase != GamePhase.VOTING:
            await query.answer("❌ Голосование уже завершено!", show_alert=True)
            return

        # Проверяем пропуск голосования
        if query.data == "wolf_vote_skip":
            # Добавляем голос "пропустить" в игру
            success, already_voted = game.vote(user_id, None)  # None означает пропуск
            if success:
                await query.edit_message_text("⏭️ Вы пропустили голосование за волка!\n\n🕐 Ожидайте результатов голосования...")
                
                # Проверяем, все ли проголосовали (включая пропуски)
                if hasattr(game, 'total_voters') and len(game.votes) >= game.total_voters:
                    # Все проголосовали - завершаем досрочно в отдельной задаче
                    asyncio.create_task(self.complete_wolf_voting_early(context, game))
            else:
                await query.edit_message_text("❌ Не удалось зарегистрировать пропуск голосования!")
            return

        data = query.data.split('_')
        if len(data) != 3:
            await query.edit_message_text("❌ Ошибка данных!")
            return

        target_id = int(data[2])
        
        # Дополнительная проверка на голосование за себя
        if target_id == user_id:
            await query.answer("❌ Вы не можете голосовать за себя!\n\n🔄 Выберите другого игрока для голосования.", show_alert=True)
            return
        
        # Проверяем, что голосующий жив и в игре
        voter = game.players.get(user_id)
        if not voter or not voter.is_alive:
            await query.answer("❌ Вы не можете голосовать!", show_alert=True)
            return

        success, already_voted = game.vote(user_id, target_id)
        if success:
            target_player = game.players[target_id]
            if already_voted:
                await query.edit_message_text(f"🔄 Ваш голос изменен!\nТеперь вы голосуете за волка: {target_player.username}\n\n🕐 Ожидайте результатов голосования...")
            else:
                await query.edit_message_text(f"✅ Вы проголосовали за {target_player.username} как за волка!\n\n🕐 Ожидайте результатов голосования...")
            
            # Проверяем, все ли проголосовали
            if hasattr(game, 'total_voters') and len(game.votes) >= game.total_voters:
                # Все проголосовали - завершаем досрочно в отдельной задаче
                asyncio.create_task(self.complete_wolf_voting_early(context, game))
        else:
            await query.edit_message_text("❌ Не удалось зарегистрировать голос!")

    async def complete_wolf_voting_early(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Завершает голосование за волка досрочно"""
        await asyncio.sleep(0.5)  # Небольшая задержка чтобы все голоса успели обработаться
        if game.phase == GamePhase.VOTING and hasattr(game, 'voting_type') and game.voting_type == "wolf":
            await context.bot.send_message(
                chat_id=game.chat_id, 
                text="⚡ Все игроки проголосовали! Голосование 'Кто волк?' завершено досрочно."
            )
            await self.process_wolf_voting_results(context, game)

    async def complete_exile_voting_early(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Завершает голосование за изгнание досрочно"""
        # Проверяем, не был ли уже вызван этот метод
        if hasattr(game, 'exile_voting_completed') and game.exile_voting_completed:
            logger.info("Голосование за изгнание уже завершено, пропускаем")
            return
        
        # Дополнительная проверка состояния игры
        if game.phase != GamePhase.VOTING or not hasattr(game, 'voting_type') or game.voting_type != "exile":
            logger.info(f"Игра не в фазе голосования за изгнание: phase={game.phase}, voting_type={getattr(game, 'voting_type', 'None')}")
            return
            
        game.exile_voting_completed = True  # Помечаем как завершенное
        
        await asyncio.sleep(0.5)  # Небольшая задержка чтобы все голоса успели обработаться
        
        try:
            await context.bot.send_message(
                chat_id=game.chat_id, 
                text="⚡ Все игроки проголосовали! Голосование за изгнание завершено досрочно.",
                message_thread_id=game.thread_id,
                read_timeout=10,  # Увеличиваем таймаут
                write_timeout=10,
                connect_timeout=10
            )
            
            # Создаем фиктивный update для process_voting_results
            from telegram import Update, Message
            fake_message = Message(
                message_id=0,
                date=None,
                chat=None,
                from_user=None,
                text=""
            )
            fake_update = Update(update_id=0, message=fake_message)
            await self.process_voting_results(fake_update, context, game)
        except Exception as e:
            logger.error(f"Ошибка в complete_exile_voting_early: {e}")
            # Сбрасываем флаг в случае ошибки
            game.exile_voting_completed = False

    # ---------------- новые callback обработчики ----------------
    async def handle_join_game_callback(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает callback для присоединения к игре"""
        try:
            query = update.callback_query
            logger.info(f"Обработка callback join_game от пользователя {query.from_user.id}")
            
            # Проверяем права пользователя
            has_permission, error_msg = await self.check_user_permissions(
                update, context, "member"
            )
            if not has_permission:
                await query.answer(error_msg, show_alert=True)
                return
            
            await self.join_from_callback(query, context)
        except Exception as e:
            logger.error(f"Ошибка в handle_join_game_callback: {e}")
            if update.callback_query:
                await update.callback_query.answer("❌ Произошла ошибка при присоединении к игре!")
    
    async def handle_start_game_callback(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает callback для начала игры"""
        try:
            query = update.callback_query
            logger.info(f"Обработка callback start_game от пользователя {query.from_user.id}")
            await query.answer()
            
            # Проверяем права пользователя
            has_permission, error_msg = await self.check_game_permissions(
                update, context, "start_game"
            )
            if not has_permission:
                await query.answer(error_msg, show_alert=True)
                return
            
            chat_id = query.message.chat.id
            
            # Проверяем, есть ли игра
            if chat_id not in self.games:
                await query.edit_message_text("❌ Игра не найдена!")
                return
            
            game = self.games[chat_id]
            if game.phase != GamePhase.WAITING:
                await query.edit_message_text("❌ Игра уже идет!")
                return
            
            if not game.can_start_game():
                await query.edit_message_text("❌ Недостаточно игроков для начала игры!")
                return
            
            # Начинаем игру
            if game.start_game():
                await self.start_game_common(query, context, game)
            else:
                await query.edit_message_text("❌ Не удалось начать игру!")
        except Exception as e:
            logger.error(f"Ошибка в handle_start_game_callback: {e}")
            if update.callback_query:
                await update.callback_query.answer("❌ Произошла ошибка при начале игры!")

    async def handle_leave_registration_callback(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает callback для выхода из регистрации"""
        try:
            query = update.callback_query
            logger.info(f"Обработка callback leave_registration от пользователя {query.from_user.id}")
            await query.answer()
            
            # Проверяем права пользователя
            has_permission, error_msg = await self.check_user_permissions(
                update, context, "member"
            )
            if not has_permission:
                await query.answer(error_msg, show_alert=True)
                return
            
            user_id = query.from_user.id
            chat_id = query.message.chat.id
            
            if user_id not in self.player_games:
                await query.answer("❌ Вы не зарегистрированы в игре!", show_alert=True)
                return
            
            if self.player_games[user_id] != chat_id:
                await query.answer("❌ Вы зарегистрированы в другом чате!", show_alert=True)
                return
            
            game = self.games[chat_id]
            if game.phase != GamePhase.WAITING:
                await query.answer("❌ Нельзя выйти из игры, которая уже началась!", show_alert=True)
                return
            
            # Удаляем игрока
            if game.remove_player(user_id):
                del self.player_games[user_id]
                
                # Обновляем сообщение в чате
                await self._update_join_message(chat_id, context)
                
                await query.answer("✅ Вы вышли из регистрации на игру!", show_alert=True)
            else:
                await query.answer("❌ Не удалось выйти из регистрации!", show_alert=True)
        except Exception as e:
            logger.error(f"Ошибка в handle_leave_registration_callback: {e}")
            if update.callback_query:
                await update.callback_query.answer("❌ Произошла ошибка при выходе из регистрации!")

    async def handle_cancel_game_callback(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает callback для отмены игры"""
        try:
            query = update.callback_query
            logger.info(f"Обработка callback cancel_game от пользователя {query.from_user.id}")
            await query.answer()
            
            # Проверяем права пользователя (только администраторы)
            has_permission, error_msg = await self.check_user_permissions(
                update, context, "admin"
            )
            if not has_permission:
                await query.answer(error_msg, show_alert=True)
                return
            
            chat_id = query.message.chat.id
            user_id = query.from_user.id
            
            if chat_id not in self.games:
                await query.edit_message_text("❌ В этом чате нет активной игры!")
                return
            
            game = self.games[chat_id]
            if game.phase != GamePhase.WAITING:
                await query.edit_message_text("❌ Нельзя отменить игру, которая уже началась!")
                return
            
            # Отменяем игру
            game.phase = GamePhase.GAME_OVER
            del self.games[chat_id]
            
            # Очищаем данные игроков
            for user_id in list(self.player_games.keys()):
                if self.player_games[user_id] == chat_id:
                    del self.player_games[user_id]
            
            await query.edit_message_text("🛑 Игра отменена администратором!")
        except Exception as e:
            logger.error(f"Ошибка в handle_cancel_game_callback: {e}")
            if update.callback_query:
                await update.callback_query.answer("❌ Произошла ошибка при отмене игры!")

    async def handle_end_game_callback(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает callback для завершения игры"""
        query = update.callback_query
        await query.answer()
        
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_game_permissions(
            update, context, "end_game"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return
        
        chat_id = query.message.chat.id
        user_id = query.from_user.id
        
        if chat_id not in self.games:
            await query.answer("❌ В этом чате нет активной игры!")
            return
        
        game = self.games[chat_id]
        if game.phase == GamePhase.WAITING:
            await query.answer("❌ Игра ещё не началась!")
            return
        
        # Проверяем, что пользователь участвует в игре
        if user_id not in self.player_games or self.player_games[user_id] != chat_id:
            await query.answer("❌ Только участники игры могут её завершить!")
            return

        await self._end_game_internal(query, context, game, "Участник завершил игру")

    async def start_game_common(self, update_or_query, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Общая логика начала игры"""
        chat_id = game.chat_id
        
        # Отправляем сообщение о начале игры
        start_message = (
            "🚀 *Игра началась!* 🚀\n\n"
            "🌙 Наступает первая ночь...\n"
            "🎭 Роли распределены и отправлены в личные сообщения\n\n"
            "📱 Проверьте свои личные сообщения с ботом!"
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=start_message,
            parse_mode='Markdown',
            message_thread_id=game.thread_id
        )
        
        # Отправляем роли всем игрокам
        await self.send_roles_to_players(context, game)
        
        # Запускаем первую ночь
        await self.start_night_phase(update_or_query, context, game)

    async def send_roles_to_players(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Отправляет роли всем игрокам в личные сообщения"""
        for player in game.players.values():
            role_info = self.get_role_info(player.role)
            team_name = "🦁 Хищники" if player.team.name == "PREDATORS" else "🌿 Травоядные"
            
            role_message = (
                f"🎭 Ваша роль в игре 'Лес и Волки':\n\n"
                f"👤 {role_info['name']}\n"
                f"🏴 Команда: {team_name}\n\n"
                f"📖 Описание:\n{role_info['description']}"
            )
            
            try:
                await context.bot.send_message(chat_id=player.user_id, text=role_message)
            except Exception as e:
                logger.error(f"Не удалось отправить роль игроку {player.user_id}: {e}")

    # ---------------- helper ----------------
    async def send_role_button_to_passive_players(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Отправляет кнопку просмотра роли игрокам без ночных действий"""
        passive_roles = [Role.HARE]  # Зайцы не имеют ночных действий

        for player in game.players.values():
            if player.is_alive and player.role in passive_roles:
                keyboard = [[InlineKeyboardButton(
                    "🎭 Посмотреть мою роль",
                    callback_data=f"night_view_role_{player.user_id}"
                )]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                try:
                    await context.bot.send_message(
                        chat_id=player.user_id,
                        text="🌙 Ночь в лесу...\n\nВы спите, но можете посмотреть свою роль:",
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить кнопку роли игроку {player.user_id}: {e}")

    async def handle_view_my_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает нажатие кнопки 'Посмотреть свою роль' и отправляет информацию в личку"""
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()
        
        # Проверяем права пользователя
        update = Update(update_id=0, callback_query=query)
        has_permission, error_msg = await self.check_user_permissions(
            update, context, "member"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return
        
        user_id = query.from_user.id
        
        # Проверяем, участвует ли игрок в игре
        if user_id not in self.player_games:
            await query.answer("❌ Вы не участвуете в игре!", show_alert=True)
            return
        
        chat_id = self.player_games[user_id]
        if chat_id not in self.games:
            await query.edit_message_text("❌ Игра не найдена!")
            return
        
        game = self.games[chat_id]
        if user_id not in game.players:
            await query.edit_message_text("❌ Вы не являетесь участником этой игры!")
            return
        
        player = game.players[user_id]
        role_info = self.get_role_info(player.role)
        team_name = "🦁 Хищники" if player.team.name == "PREDATORS" else "🌿 Травоядные"
        
        role_message = (
            f"🎭 Ваша роль в игре 'Лес и Волки':\n\n"
            f"👤 {role_info['name']}\n"
            f"🏴 Команда: {team_name}\n\n"
            f"📝 Описание:\n{role_info['description']}\n\n"
            f"🌙 Раунд: {game.current_round}\n"
            f"💚 Статус: {'Живой' if player.is_alive else 'Мертвый'}"
        )
        
        try:
            # Отправляем роль в личные сообщения
            await context.bot.send_message(chat_id=user_id, text=role_message)
            # Не изменяем исходное сообщение, просто показываем уведомление
            await query.answer("✅ Информация о вашей роли отправлена в личные сообщения!", show_alert=True)
        except Exception as e:
            logger.error(f"Не удалось отправить роль игроку {user_id}: {e}")
            # Показываем ошибку как alert, не изменяя сообщение
            await query.answer(
                "❌ Не удалось отправить сообщение в личку!\n"
                "Убедитесь, что вы написали боту в личных сообщениях (/start в личке с ботом).", 
                show_alert=True
            )

    def get_role_info(self, role: Role) -> Dict[str, str]:
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
                "name": "🦦 Бобер",
                "description": "Вы травоядный! Вы можете возвращать украденные запасы другим зверям."
            }
        }
        return role_info.get(role, {"name": "Неизвестно", "description": "Роль не определена"})

    # ---------------- bot lifecycle: setup and run ----------------
    async def setup_bot_commands(self, application: Application):
        commands = [
            # 🎮 Основные команды для игроков
            BotCommand("start", "🌲 Приветствие и быстрый старт"),
            BotCommand("join", "✅ Присоединиться к игре"),
            BotCommand("status", "📊 Статус игры"),
            BotCommand("help", "🆘 Подробная инструкция"),
            BotCommand("rules", "📖 Правила игры"),
            
            # 🎯 Команды для управления игрой
            BotCommand("start_game", "🚀 Начать игру"),
            BotCommand("end_game", "🏁 Завершить игру"),
            BotCommand("end", "🏁 Завершить игру (краткая)"),
            BotCommand("leave", "👋 Покинуть игру"),
            
            # ⚙️ Административные команды
            BotCommand("settings", "⚙️ Настройки игры"),
            BotCommand("test_mode", "🧪 Тестовый режим"),
            BotCommand("force_end", "⛔ Принудительное завершение"),
            BotCommand("clear_all_games", "🧹 Очистить все игры"),
            BotCommand("setup_channel", "🔧 Настройка канала"),
        ]
        try:
            await application.bot.set_my_commands(commands)
            logger.info("Bot commands set.")
        except Exception as ex:
            logger.error(f"Failed to set bot commands: {ex}")

    def run(self):
        application = Application.builder().token(BOT_TOKEN).build()

        # зарегистрируем обработчики
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("rules", self.rules))
        application.add_handler(CommandHandler("join", self.join))
        application.add_handler(CommandHandler("leave", self.leave))
        application.add_handler(CommandHandler("start_game", self.start_game))
        application.add_handler(CommandHandler("end_game", self.end_game))
        application.add_handler(CommandHandler("end", self.end_game))  # Алиас для end_game
        application.add_handler(CommandHandler("force_end", self.force_end))
        application.add_handler(CommandHandler("clear_all_games", self.clear_all_games))
        application.add_handler(CommandHandler("settings", self.settings))
        application.add_handler(CommandHandler("status", self.status))
        application.add_handler(CommandHandler("test_mode", self.handle_test_mode_command)) # Обработчик команды test_mode
        application.add_handler(CommandHandler("setup_channel", self.setup_channel)) # Обработчик команды setup_channel
        application.add_handler(CommandHandler("remove_channel", self.remove_channel)) # Обработчик команды remove_channel
        

        # Обработчик присоединения бота к чату
        application.add_handler(ChatMemberHandler(self.handle_bot_join, ChatMemberHandler.MY_CHAT_MEMBER))

        # callbacks
        application.add_handler(CallbackQueryHandler(self.handle_vote, pattern=r"^vote_"))
        application.add_handler(CallbackQueryHandler(self.handle_night_action, pattern=r"^night_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^settings_"))
        application.add_handler(CallbackQueryHandler(self.handle_welcome_buttons, pattern=r"^welcome_"))
        application.add_handler(CallbackQueryHandler(self.handle_day_actions, pattern=r"^day_"))
        application.add_handler(CallbackQueryHandler(self.handle_wolf_voting, pattern=r"^wolf_vote_"))
        
        # Новые callback обработчики
        application.add_handler(CallbackQueryHandler(self.handle_join_game_callback, pattern=r"^join_game$"))
        application.add_handler(CallbackQueryHandler(self.handle_start_game_callback, pattern=r"^start_game$"))
        application.add_handler(CallbackQueryHandler(self.handle_leave_registration_callback, pattern=r"^leave_registration$"))
        application.add_handler(CallbackQueryHandler(self.handle_cancel_game_callback, pattern=r"^cancel_game$"))
        application.add_handler(CallbackQueryHandler(self.handle_end_game_callback, pattern=r"^end_game$"))
        
        # settings submenu/back handlers
        application.add_handler(CallbackQueryHandler(self.handle_timer_settings, pattern=r"^timer_"))
        application.add_handler(CallbackQueryHandler(self.handle_role_settings, pattern=r"^role_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings_back, pattern=r"^settings_back$"))
        application.add_handler(CallbackQueryHandler(self.handle_timer_values, pattern=r"^set_"))
        application.add_handler(CallbackQueryHandler(self.handle_timer_values, pattern=r"^timer_back"))
        application.add_handler(CallbackQueryHandler(self.handle_view_my_role, pattern=r"^view_my_role$"))
        application.add_handler(CallbackQueryHandler(self.handle_check_stage, pattern=r"^check_stage$"))

        # Установка команд после старта бота
        async def post_init(application):
            await self.setup_bot_commands(application)

        application.post_init = post_init

        # Запуск бота (blocking call)
        application.run_polling()

    async def handle_bot_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает присоединение бота к чату"""
        chat_member_updated = update.my_chat_member
        
        # Проверяем, что бот был добавлен в чат
        if (chat_member_updated.new_chat_member.status == 'member' and 
            chat_member_updated.old_chat_member.status in ['left', 'kicked']):
            
            chat_id = update.effective_chat.id
            
            # Проверяем, что это первое появление бота в чате
            # (не отправляем приветствие, если игра уже существует)
            if chat_id not in self.games:
                # Отправляем приветственное сообщение только при первом появлении
                await self.send_welcome_message(chat_id, context)
    
    
    async def send_welcome_message(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет приветственное сообщение при первом появлении бота в чате"""
        welcome_text = (
            "🌲 *Добро пожаловать в 'Лес и Волки'!* 🌲\n\n"
            "🎭 *Ролевая игра в стиле 'Мафия' с лесными зверушками*\n\n"
            "🐺 *Хищники:* Волки + Лиса\n"
            "🐰 *Травоядные:* Зайцы + Крот + Бобёр\n\n"
            "🌙 *Как играть:*\n"
            "• Ночью хищники охотятся, травоядные защищаются\n"
            "• Днем все обсуждают и голосуют за изгнание\n"
            "• Цель: уничтожить всех противников\n\n"
            f"👥 Минимум: {self.global_settings.get_min_players()} игроков\n"
            f"{'🧪 ТЕСТОВЫЙ РЕЖИМ' if self.global_settings.is_test_mode() else ''}\n\n"
            "🚀 *Нажмите кнопку ниже, чтобы начать игру!*"
        )
        
        # Создаем кнопку "Начать игру"
        keyboard = [
            [InlineKeyboardButton("🎮 Начать игру", callback_data="welcome_start_game")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            # Отправляем приветственное сообщение
            welcome_message = await context.bot.send_message(
                chat_id=chat_id,
                text=welcome_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Закрепляем сообщение только в группах (не в личных сообщениях)
            try:
                await context.bot.pin_chat_message(chat_id, welcome_message.message_id)
                logger.info(f"Отправлено и закреплено приветственное сообщение в чат {chat_id}")
            except Exception:
                # В личных сообщениях закрепление невозможно, это нормально
                logger.info(f"Приветственное сообщение отправлено в чат {chat_id} (закрепление недоступно)")
            
        except Exception as e:
            logger.error(f"Не удалось отправить приветственное сообщение в чат {chat_id}: {e}")

    async def handle_test_mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /test_mode для включения/выключения тестового режима."""
        # Проверяем права пользователя (только администраторы)
        has_permission, error_msg = await self.check_user_permissions(update, context, "admin")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
            
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        # Проверяем, что это группа, а не личные сообщения
        if chat_id == user_id:
            await update.message.reply_text("❌ Управление тестовым режимом доступно только в группах!")
            return

        # Проверяем права администратора
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут изменять тестовый режим!")
            return

        game = self.games.get(chat_id)  # Игра может отсутствовать

        # Проверяем, можно ли изменить тестовый режим
        if game and game.phase != GamePhase.WAITING:
            await update.message.reply_text("❌ Нельзя изменить тестовый режим во время игры! Дождитесь окончания игры.")
            return

        self.global_settings.toggle_test_mode() # Используем метод для переключения
        mode_text = "включен" if self.global_settings.is_test_mode() else "выключен"
        min_players = self.global_settings.get_min_players()

        result_text = (
            f"🧪 Тестовый режим {mode_text}!\n\n"
            f"📋 Минимум игроков: {min_players}\n"
        )

        if game:
            result_text += (
                f"🎮 Можно начать игру: {'✅' if game.can_start_game() else '❌'}\n"
                f"👥 Текущих игроков: {len(game.players)}"
            )
        else:
            result_text += "ℹ️ Создайте игру командой `/join` для применения настроек"

        await update.message.reply_text(result_text)


if __name__ == "__main__":
    bot = ForestWolvesBot()
    bot.run()