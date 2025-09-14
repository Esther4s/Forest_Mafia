#!/usr/bin/env python36
# -*- coding: utf-8 -*-

import asyncio
import logging
import random
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from game_logic import Game, GamePhase, Role, Team, Player  # ваши реализации
from config import BOT_TOKEN  # ваши настройки
from night_actions import NightActions
from night_interface import NightInterface
from global_settings import GlobalSettings # Импортируем GlobalSettings
from forest_mafia_settings import ForestWolvesSettings
from database_adapter import DatabaseAdapter
from database_psycopg2 import (
    init_db, close_db,
    create_user, get_user_by_telegram_id, update_user_balance, get_user_balance,
    execute_query, fetch_one, fetch_query,
    get_chat_settings, update_chat_settings, reset_chat_settings,
    create_tables,
    save_player_action, save_vote, update_player_stats, update_user_stats,
    get_bot_setting, set_bot_setting,
    save_game_to_db, save_player_to_db, update_game_phase, finish_game_in_db,
    get_team_stats, get_top_players, get_best_predator, get_best_herbivore, get_player_detailed_stats,
    get_player_chat_stats, add_nuts_to_user, get_shop_items
)

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
        
        # Инициализация базы данных
        try:
            self.db = init_db()
            # Создаем таблицы если их нет
            tables_created = create_tables()
            if not tables_created:
                logger.warning("⚠️ Проблема с созданием таблиц, но база данных доступна")
            logger.info("✅ База данных инициализирована успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            self.db = None
        
        # Система случайных сообщений
        self.no_exile_messages = [
            "🌳 Вечер опустился на лес. Животные спорили и шептались, но так и не решились изгнать кого-то. Подозрения остались висеть в воздухе, как туман над поляной.",
            "🍂 Голоса разделились, и ни один зверь не оказался изгнан. Лес затаил дыхание — значит, завтра будет ещё тревожнее.",
            "🌲 Животные переглядывались с недоверием, но так и не нашли виновного. Лес проводил день в тишине, словно пряча чью-то тайну.",
            "🌙 Никого не изгнали. Лес уснул с нераскрытой загадкой, а тревога в сердцах животных лишь усилилась."
        ]
        
        self.no_kill_messages = [
            "🌌 Волки выли на луну, но так и не нашли добычи. Утром все проснулись целыми и невредимыми. Но сколько ещё продлится эта удача?",
            "🌲 Ночь прошла тихо. Волчьи лапы бродили по лесу, но никто не был тронут. Животные встречали рассвет с облегчением — пока.",
            "🍃 Волки кружили по поляне, но их пасти остались голодными. Утро настало без потерь, и лес зашептал: «Что это значит?..»",
            "🌙 Звёзды наблюдали, как волки искали жертву, но этой ночью зубы остались пустыми. Животные обняли рассвет с радостью и страхом."
        ]
        # Список разрешенных чатов и тем (chat_id, thread_id или None для всего чата)
        self.authorized_chats: set = set()  # Хранит кортежи (chat_id, thread_id)
        # Bot token
        self.bot_token = BOT_TOKEN
        # Инициализация базы данных
        try:
            self.db = init_db()
            # Создаем таблицы если их нет
            tables_created = create_tables()
            if not tables_created:
                logger.warning("⚠️ Проблема с созданием таблиц, но база данных доступна")
            logger.info("✅ База данных инициализирована успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            self.db = None
        
        # Загружаем активные игры из базы данных
        self.load_active_games()
        
        # Инициализируем автоматическое сохранение
        try:
            from auto_save_manager import AutoSaveManager
            self.auto_save_manager = AutoSaveManager(self)
            logger.info("✅ Автоматическое сохранение инициализировано")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации автоматического сохранения: {e}")
            self.auto_save_manager = None

    def load_active_games(self):
        """Загружает активные игры из базы данных при старте бота"""
        try:
            if not self.db:
                logger.warning("⚠️ База данных недоступна, активные игры не загружены")
                return
            
            from database_psycopg2 import load_all_active_games, load_players_state
            
            # Загружаем все активные игры
            active_games_data = load_all_active_games()
            
            for game_data in active_games_data:
                try:
                    # Восстанавливаем игру из данных
                    game = Game.from_dict(game_data)
                    
                    # Загружаем игроков
                    players_data = load_players_state(game_data['id'])
                    for player_data in players_data:
                        user_id = player_data['user_id']
                        role = Role(player_data['role']) if player_data.get('role') else None
                        team = Team(player_data['team']) if player_data.get('team') else None
                        
                        player = Player(
                            user_id=user_id,
                            username=player_data.get('username'),
                            first_name=player_data.get('first_name'),
                            role=role,
                            team=team
                        )
                        player.is_alive = player_data.get('is_alive', True)
                        game.players[user_id] = player
                    
                    # Добавляем игру в словарь
                    self.games[game.chat_id] = game
                    
                    # Восстанавливаем ночные действия и интерфейсы
                    self.night_actions[game.chat_id] = NightActions(game)
                    self.night_interfaces[game.chat_id] = NightInterface(game, self.night_actions[game.chat_id])
                    
                    logger.info(f"✅ Восстановлена игра в чате {game.chat_id} (фаза: {game.phase.value})")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка восстановления игры {game_data.get('id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"✅ Загружено {len(active_games_data)} активных игр из БД")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке активных игр: {e}")
    
    def start_auto_save(self):
        """Запускает автоматическое сохранение"""
        if hasattr(self, 'auto_save_manager') and self.auto_save_manager:
            self.auto_save_manager.start_auto_save()
            logger.info("✅ Автоматическое сохранение запущено")
    
    def stop_auto_save(self):
        """Останавливает автоматическое сохранение"""
        if hasattr(self, 'auto_save_manager') and self.auto_save_manager:
            self.auto_save_manager.stop_auto_save()
            logger.info("✅ Автоматическое сохранение остановлено")
    
    def force_save_state(self):
        """Принудительно сохраняет состояние"""
        if hasattr(self, 'auto_save_manager') and self.auto_save_manager:
            self.auto_save_manager.force_save()
            logger.info("✅ Состояние принудительно сохранено")
    
    def save_game_state(self, chat_id: int) -> bool:
        """
        Сохраняет состояние игры в базу данных
        
        Args:
            chat_id: ID чата с игрой
            
        Returns:
            bool: True если сохранение успешно, False иначе
        """
        try:
            if chat_id not in self.games:
                return False
            
            game = self.games[chat_id]
            from database_psycopg2 import save_game_state, save_players_state
            
            # Сериализуем игру
            game_data = game.to_dict()
            
            # Сохраняем состояние игры
            if not save_game_state(game_data):
                logger.error(f"❌ Ошибка сохранения состояния игры в чате {chat_id}")
                return False
            
            # Сохраняем игроков
            players_data = []
            for player in game.players.values():
                players_data.append({
                    'id': f"{chat_id}_{player.user_id}",
                    'user_id': player.user_id,
                    'username': player.username,
                    'first_name': player.first_name,
                    'role': player.role.value if player.role else None,
                    'is_alive': player.is_alive,
                    'team': player.team.value if player.team else None
                })
            
            if not save_players_state(game_data['id'], players_data):
                logger.error(f"❌ Ошибка сохранения игроков игры в чате {chat_id}")
                return False
            
            logger.debug(f"✅ Состояние игры в чате {chat_id} сохранено в БД")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения состояния игры в чате {chat_id}: {e}")
            return False
    
    def save_all_games_state(self) -> int:
        """
        Сохраняет состояние всех активных игр
        
        Returns:
            int: Количество успешно сохраненных игр
        """
        saved_count = 0
        for chat_id in self.games:
            if self.save_game_state(chat_id):
                saved_count += 1
        
        logger.info(f"✅ Сохранено состояние {saved_count} игр")
        return saved_count

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
    def get_display_name(self, user_id: int, username: str = None, first_name: str = None) -> str:
        """Получает отображаемое имя пользователя (приоритет: никнейм > username > first_name)"""
        try:
            from database_psycopg2 import get_user_nickname
            nickname = get_user_nickname(user_id)
            if nickname:
                return nickname
        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения никнейма для пользователя {user_id}: {e}")
        
        # Если никнейма нет, используем username или first_name
        if username and not username.isdigit():
            return username
        elif first_name:
            return first_name
        else:
            return f"ID:{user_id}"

    def format_player_tag(self, username: str, user_id: int, make_clickable: bool = True) -> str:
        """Форматирует тег игрока для отображения с учетом никнейма"""
        try:
            # Сначала пытаемся получить никнейм
            from database_psycopg2 import get_user_nickname
            nickname = get_user_nickname(user_id)
            
            if nickname:
                # Если есть никнейм, используем его
                if make_clickable:
                    return f'<a href="tg://user?id={user_id}">{nickname}</a>'
                else:
                    return nickname
            elif username and not username.isdigit():
                # Если username есть и это не просто ID
                if make_clickable:
                    return f'<a href="tg://user?id={user_id}">@{username}</a>'
                else:
                    return f"@{username}" if not username.startswith('@') else username
            else:
                # Если username нет или это ID, используем ID
                if make_clickable:
                    return f'<a href="tg://user?id={user_id}">ID:{user_id}</a>'
                else:
                    return f"ID:{user_id}"
        except Exception as e:
            # В случае ошибки используем старую логику
            logger.warning(f"⚠️ Ошибка получения никнейма для пользователя {user_id}: {e}")
            if username and not username.isdigit():
                if make_clickable:
                    return f'<a href="tg://user?id={user_id}">@{username}</a>'
                else:
                    return f"@{username}" if not username.startswith('@') else username
            else:
                if make_clickable:
                    return f'<a href="tg://user?id={user_id}">ID:{user_id}</a>'
                else:
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
            self.games[chat_id] = Game(chat_id, thread_id, is_test_mode=self.global_settings.is_test_mode())
            self.night_actions[chat_id] = NightActions(self.games[chat_id])
            self.night_interfaces[chat_id] = NightInterface(self.games[chat_id], self.night_actions[chat_id])
            
            # Создаем игру в базе данных
            import uuid
            db_game_id = str(uuid.uuid4())
            self.games[chat_id].db_game_id = db_game_id
            
            # Сохраняем игру в БД
            save_game_to_db(
                game_id=db_game_id,
                chat_id=chat_id,
                thread_id=thread_id,
                status='waiting',
                settings={}
            )

        game = self.games[chat_id]

        if game.phase != GamePhase.WAITING:
            return False, "❌ Игра уже идёт! Дождитесь её окончания.", None

        if game.add_player(user_id, username):
            self.player_games[user_id] = chat_id
            
            # Сохраняем игрока в базу данных
            if hasattr(game, 'db_game_id') and game.db_game_id:
                import uuid
                player_id = str(uuid.uuid4())
                save_player_to_db(
                    player_id=player_id,
                    game_id=game.db_game_id,
                    user_id=user_id,
                    username=username,
                    is_alive=True
                )
            
            max_players = getattr(game, "MAX_PLAYERS", 12)
            
            # Создаем улучшенную клавиатуру с новыми функциями
            keyboard = []
            
            # Кнопка "Присоединиться" - всегда первая
            keyboard.append([InlineKeyboardButton("✅ Присоединиться", callback_data="join_game")])
            
            # Кнопка "Выйти из регистрации"
            keyboard.append([InlineKeyboardButton("❌ Выйти из регистрации", callback_data="leave_registration")])
            
            # Кнопка "Посмотреть свою роль" (повторяет сообщения с кнопками действий)
            if game.phase != GamePhase.WAITING:
                keyboard.append([InlineKeyboardButton("👁️ Посмотреть свою роль", callback_data="repeat_role_actions")])
            
            # Кнопка "Магазин"
            keyboard.append([InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")])
            
            # Кнопка "Быстрый режим" (только для админов)
            if await self.is_user_admin(update, context):
                quick_mode_text = "⚡ Быстрый режим: ВКЛ" if self.global_settings.is_test_mode() else "⚡ Быстрый режим: ВЫКЛ"
                keyboard.append([InlineKeyboardButton(quick_mode_text, callback_data="toggle_quick_mode_game")])
            
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
                player_tag = self.format_player_tag(player.username, player.user_id, make_clickable=True)
                players_list += f"• {player_tag}\n"
            
            message = (
                f"✅ {self.format_player_tag(username, user_id, make_clickable=True)} присоединился к игре!\n\n"
                f"👥 Игроков: {len(game.players)}/{max_players}\n"
                f"📋 Минимум для старта: {self.global_settings.get_min_players()}\n\n"
                f"📝 Участники:\n{players_list}"
            )
            
            if game.can_start_game():
                message += "\n✅ Можно начинать игру! Используйте `/start_game`"
            else:
                message += f"\n⏳ Нужно ещё {max(0, self.global_settings.get_min_players() - len(game.players))} игроков"
            
            # Автосохранение состояния игры
            self.save_game_state(chat_id)
            
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
            [InlineKeyboardButton("🛑 Отменить игру", callback_data="welcome_cancel_game")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = (
            "🌲 <b>Лес и Волки</b> - ролевая игра в стиле 'Мафия'!\n\n"
            "🐺 <b>Хищники:</b> Волки + Лиса\n"
            "🐰 <b>Травоядные:</b> Зайцы + Крот + Бобёр\n\n"
            f"👥 Минимум: {self.global_settings.get_min_players()} игроков\n"
            f"{'⚡ БЫСТРЫЙ РЕЖИМ' if self.global_settings.is_test_mode() else ''}\n\n"
            "🚀 <b>Быстрый старт:</b> нажмите 'Начать игру' или используйте `/join`"
        )

        # Отправляем приветственное сообщение (без закрепления для быстрого доступа)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

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
            "🌲 <b>ПОЛНЫЕ ПРАВИЛА ИГРЫ 'Лес и Волки'</b> 🌲\n\n"
            "🎭 <b>Что это такое?</b>\n"
            "Ролевая игра в стиле 'Мафия' с лесными зверушками. Две команды сражаются за выживание в лесу!\n\n"
            "👥 <b>Команды:</b>\n\n"
            "🐺 <b>ХИЩНИКИ (меньшинство):</b>\n"
            "• <b>Волки</b> - стая хищников, съедают по зверю каждую ночь (кроме первой ночи)\n"
            "• <b>Лиса</b> - хитрая воровка, крадет запасы еды у травоядных\n\n"
            "🐰 <b>ТРАВОЯДНЫЕ (большинство):</b>\n"
            "• <b>Зайцы</b> - мирные зверушки, не имеют ночных способностей\n"
            "• <b>Крот</b> - роет норки, каждую ночь может проверить любого игрока и узнать его роль\n"
            "• <b>Бобёр</b> - помогает травоядным, может восстановить украденные запасы\n\n"
            "⏰ <b>ФАЗЫ ИГРЫ:</b>\n\n"
            "🌙 <b>НОЧЬ (60 секунд):</b>\n"
            "• Волки выбирают жертву для съедения\n"
            "• Лиса выбирает цель для кражи запасов\n"
            "• Бобёр может помочь пострадавшему от лисы\n"
            "• Крот проверяет любого игрока\n"
            "• Зайцы спят\n\n"
            "☀️ <b>ДЕНЬ (5 минут):</b>\n"
            "• Обсуждение событий ночи\n"
            "• Планирование стратегии\n"
            "• Обмен информацией\n"
            "• Подозрения и обвинения\n\n"
            "🗳️ <b>ГОЛОСОВАНИЕ (2 минуты):</b>\n"
            "• Голосование за изгнание подозрительного игрока\n"
            "• Игрок с наибольшим количеством голосов изгоняется\n"
            "• При ничьей никто не изгоняется\n\n"
            "🎯 <b>ЦЕЛИ КОМАНД:</b>\n\n"
            "🐺 <b>Хищники побеждают, если:</b>\n"
            "• Количество хищников становится равным или больше количества травоядных\n"
            "• Все травоядные уничтожены\n\n"
            "🐰 <b>Травоядные побеждают, если:</b>\n"
            "• Все хищники изгнаны или убиты\n"
            "• Волки полностью уничтожены\n\n"
            "🛡️ <b>СПЕЦИАЛЬНЫЕ МЕХАНИКИ:</b>\n\n"
            "🦊 <b>Лиса:</b>\n"
            "• Ворует запасы у травоядных (кроме бобра)\n"
            "• Игрок умирает после 2 краж подряд\n"
            "• Не может воровать у волков (союзники)\n\n"
            "🦦 <b>Бобёр:</b>\n"
            "• Может помочь любому, у кого украли запасы\n"
            "• Полностью восстанавливает украденные запасы\n"
            "• Защищает от смерти от кражи лисы\n\n"
            "🦫 <b>Крот:</b>\n"
            "• Может проверить любого игрока каждую ночь\n"
            "• Узнает точную роль игрока\n"
            "• Видит, действовал ли игрок этой ночью\n\n"
            "🐺 <b>Волки:</b>\n"
            "• Не действуют в первую ночь\n"
            "• Не могут есть лису (союзники)\n"
            "• Не могут есть друг друга\n\n"
            "⚡ <b>АВТОМАТИЧЕСКОЕ ЗАВЕРШЕНИЕ:</b>\n"
            "• Если остается менее 3 игроков\n"
            "• Если игра длится более 3 часов\n"
            "• Если сыграно более 25 раундов\n\n"
            "🎮 <b>КАК ИГРАТЬ:</b>\n"
            "1. Используйте `/start` для начала регистрации\n"
            "2. Нажмите 'Присоединиться к игре'\n"
            "3. Дождитесь начала игры (минимум 6 игроков)\n"
            "4. Получите роль в личных сообщениях\n"
            "5. Следуйте инструкциям бота\n\n"
            "💡 <b>СОВЕТЫ:</b>\n"
            "• Доверяйте, но проверяйте\n"
            "• Анализируйте поведение других игроков\n"
            "• Используйте информацию от крота\n"
            "• Защищайте важных игроков\n"
            "• Не раскрывайте свою роль без необходимости\n\n"
            "🔧 <b>КОМАНДЫ:</b>\n"
            "• `/start` - начать регистрацию\n"
            "• `/join` - присоединиться к игре\n"
            "• `/leave` - покинуть игру\n"
            "• `/status` - статус игры\n"
            "• `/rules` - эти правила\n"
            "• `/help` - помощь\n\n"
            "🎉 <b>Удачной игры!</b>"
        )
        await update.message.reply_text(rules_text, parse_mode='HTML')

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
            "🆘 <b>Быстрая справка по игре</b>\n\n"
            "🚀 <b>Быстрый старт:</b>\n"
            "• `/join` - присоединиться к игре\n"
            "• `/start_game` - начать игру\n"
            "• `/status` - статус игры\n\n"
            "🎭 <b>Роли:</b>\n"
            "🐺 Волки - едят по ночам\n"
            "🦊 Лиса - ворует запасы\n"
            "🐰 Зайцы - мирные жители\n"
            "🦫 Крот - проверяет команды\n"
            "🦦 Бобёр - защищает от лисы\n\n"
            "⏰ <b>Фазы игры:</b>\n"
            "🌙 Ночь (60 сек) - ночные действия\n"
            "☀️ День (5 мин) - обсуждение\n"
            "🗳️ Голосование (2 мин) - изгнание\n\n"
            "🏆 <b>Победа:</b> уничтожить команду противника\n\n"
            "💡 <b>Команды:</b> /rules, /help, /stats, /settings"
        )
        await update.message.reply_text(help_text, parse_mode='HTML')

    async def inventory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает инвентарь игрока"""
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
        
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or "Unknown"
        
        try:
            # Получаем подробную информацию об инвентаре
            from database_psycopg2 import get_user_inventory_detailed
            
            inventory_data = get_user_inventory_detailed(user_id)
            
            if not inventory_data['success']:
                await update.message.reply_text(f"❌ {inventory_data['error']}")
                return
            
            # Формируем сообщение
            message = f"🧺 <b>Инвентарь {username}</b>\n\n"
            message += f"🌰 Орешки: {inventory_data['balance']}\n"
            message += f"📊 Всего предметов: {inventory_data['total_items']}\n\n"
            
            if inventory_data['items']:
                message += "📦 <b>Предметы:</b>\n"
                for item in inventory_data['items']:
                    item_name = item['item_name']
                    count = item['count']
                    message += f"• {item_name} x{count}\n"
            else:
                message += "📦 <b>Инвентарь пуст</b>\n"
                message += "🛍️ Посетите магазин, чтобы купить предметы!"
            
            # Создаем клавиатуру
            keyboard = [
                [InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")],
                [InlineKeyboardButton("💰 Баланс", callback_data="show_balance")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения инвентаря для пользователя {user_id}: {e}")
            await update.message.reply_text("❌ Произошла ошибка при получении инвентаря!")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику игрока, топ игроков или общую статистику"""
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        # Проверяем права бота в чате
        if not await self.check_bot_permissions_decorator(update, context):
            return
        
        user_id = update.effective_user.id
        
        # Обрабатываем аргументы команды
        if context.args:
            if context.args[0] == "top":
                await self.show_top_players(update, context)
            elif context.args[0] == "teams":
                await self.show_team_stats(update, context)
            elif context.args[0] == "best":
                await self.show_best_players(update, context)
            else:
                await update.message.reply_text(
                    "📊 <b>Доступные команды статистики:</b>\n\n"
                    "`/stats` - ваша статистика\n"
                    "`/stats top` - топ игроков\n"
                    "`/stats teams` - статистика команд\n"
                    "`/stats best` - лучшие игроки по ролям",
                    parse_mode='HTML'
                )
        else:
            # Показываем статистику текущего игрока
            await self.show_player_stats(update, context, user_id)

    async def show_player_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Показывает статистику конкретного игрока"""
        try:
            stats = get_player_detailed_stats(user_id)
            
            if not stats or stats['games_played'] == 0:
                await update.message.reply_text("📊 У вас пока нет игр. Присоединяйтесь к игре командой /join!")
                return
            
            username = stats.get('username') or f"Игрок {user_id}"
            win_rate = stats.get('win_rate', 0)
            
            stats_text = f"📊 <b>Статистика игрока {username}:</b>\n\n"
            stats_text += f"🎮 Всего игр: {stats['games_played']}\n"
            stats_text += f"🏆 Побед: {stats['games_won']} ({win_rate}%)\n"
            stats_text += f"💀 Поражений: {stats['games_lost']}\n"
            
            if stats.get('last_played'):
                last_played = stats['last_played'].strftime('%d.%m.%Y %H:%M')
                stats_text += f"🕐 Последняя игра: {last_played}\n"
            
            await update.message.reply_text(stats_text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики игрока: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики. Попробуйте позже.")

    async def show_top_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает топ игроков"""
        try:
            top_players = get_top_players(10, "games_won")
            
            if not top_players:
                await update.message.reply_text("📊 Статистика пока пуста. Сыграйте несколько игр!")
                return
            
            stats_text = "🏆 <b>Топ-10 игроков по победам:</b>\n\n"
            for i, player in enumerate(top_players, 1):
                username = player.get('username') or f"Игрок {player['user_id']}"
                win_rate = player.get('win_rate', 0)
                
                stats_text += f"{i}. <b>{username}</b>\n"
                stats_text += f"   🎮 Игр: {player['games_played']} | 🏆 Побед: {player['games_won']} ({win_rate}%)\n\n"
            
            await update.message.reply_text(stats_text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения топ игроков: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики. Попробуйте позже.")

    async def show_team_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику команд"""
        try:
            team_stats = get_team_stats()
            
            stats_text = "📊 <b>Статистика команд:</b>\n\n"
            stats_text += f"🎮 Всего игр: {team_stats['total_games']}\n\n"
            
            # Статистика побед команд
            team_wins = team_stats.get('team_wins', {})
            predators_wins = team_wins.get('predators', 0)
            herbivores_wins = team_wins.get('herbivores', 0)
            
            stats_text += "🐺 <b>Хищники (Волки + Лиса):</b>\n"
            stats_text += f"   🏆 Побед: {predators_wins}\n\n"
            
            stats_text += "🐰 <b>Травоядные (Зайцы + Крот + Бобёр):</b>\n"
            stats_text += f"   🏆 Побед: {herbivores_wins}\n\n"
            
            # Процентное соотношение
            total_wins = predators_wins + herbivores_wins
            if total_wins > 0:
                predators_percent = (predators_wins / total_wins) * 100
                herbivores_percent = (herbivores_wins / total_wins) * 100
                
                stats_text += "📈 <b>Соотношение побед:</b>\n"
                stats_text += f"   🐺 Хищники: {predators_percent:.1f}%\n"
                stats_text += f"   🐰 Травоядные: {herbivores_percent:.1f}%\n"
            
            await update.message.reply_text(stats_text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики команд: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики. Попробуйте позже.")

    async def show_best_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает лучших игроков по ролям"""
        try:
            best_predator = get_best_predator()
            best_herbivore = get_best_herbivore()
            
            stats_text = "🌟 <b>Лучшие игроки:</b>\n\n"
            
            if best_predator:
                username = best_predator.get('username') or f"Игрок {best_predator['user_id']}"
                win_rate = best_predator.get('win_rate', 0)
                stats_text += f"🐺 <b>Лучший хищник:</b> {username}\n"
                stats_text += f"   🏆 Побед: {best_predator['games_won']} ({win_rate}%)\n"
                stats_text += f"   🎮 Игр: {best_predator['games_played']}\n\n"
            else:
                stats_text += "🐺 <b>Лучший хищник:</b> пока нет данных\n\n"
            
            if best_herbivore:
                username = best_herbivore.get('username') or f"Игрок {best_herbivore['user_id']}"
                win_rate = best_herbivore.get('win_rate', 0)
                stats_text += f"🐰 <b>Лучший травоядный:</b> {username}\n"
                stats_text += f"   🏆 Побед: {best_herbivore['games_won']} ({win_rate}%)\n"
                stats_text += f"   🎮 Игр: {best_herbivore['games_played']}\n"
            else:
                stats_text += "🐰 <b>Лучший травоядный:</b> пока нет данных\n"
            
            await update.message.reply_text(stats_text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения лучших игроков: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики. Попробуйте позже.")

    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает баланс пользователя"""
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
            
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or "Unknown"
        
        try:
            if not self.db:
                await update.message.reply_text("❌ База данных недоступна. Попробуйте позже.")
                return
            
            logger.info(f"💰 Запрос баланса для пользователя {username} (ID: {user_id})")
            
            # Используем новую систему баланса
            from database_balance_manager import balance_manager
            
            # Создаем пользователя, если его нет
            create_user(user_id, username)
            
            # Получаем актуальный баланс
            balance = balance_manager.get_user_balance(user_id)
            
            logger.info(f"✅ Баланс пользователя {username}: {balance}")
            await update.message.reply_text(
                f"🌰 <b>Баланс игрока {username}:</b>\n\n"
                f"💳 Текущий баланс: {int(balance)} орешков\n\n"
                f"💡 Используйте команду /join чтобы присоединиться к игре!",
                parse_mode='HTML'
            )
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения баланса: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            await update.message.reply_text("❌ Произошла ошибка при получении баланса. Попробуйте позже.")

    async def shop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает магазин товаров"""
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
            
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or "Unknown"
        
        try:
            if not self.db:
                await update.message.reply_text("❌ База данных недоступна. Попробуйте позже.")
                return
            
            logger.info(f"🛍️ Запрос магазина для пользователя {username} (ID: {user_id})")
            
            # Получаем баланс пользователя
            from database_balance_manager import balance_manager
            user_balance = balance_manager.get_user_balance(user_id)
            
            # Получаем товары из магазина
            from database_psycopg2 import get_shop_items
            shop_items = get_shop_items()
            
            if not shop_items:
                await update.message.reply_text("🛍️ <b>Магазин пуст</b>\n\nТовары появятся позже!", parse_mode='HTML')
                return
            
            # Создаем клавиатуру для магазина
            keyboard = []
            
            # Добавляем кнопки для каждого товара
            for item in shop_items:
                price = int(item['price'])
                button_text = f"{item['item_name']} - {price}🌰"
                callback_data = f"buy_item_{item['id']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            # Добавляем кнопки управления
            keyboard.append([
                InlineKeyboardButton("🎒 Инвентарь", callback_data="show_inventory"),
                InlineKeyboardButton("💰 Баланс", callback_data="show_balance")
            ])
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Получаем кликабельное имя с учетом никнейма
            clickable_name = self.format_player_tag(username, user_id, make_clickable=True)
            
            # Формируем сообщение с информацией о пользователе и товарах
            shop_text = f"🌲 <b>Лесной магазин</b>\n\n"
            shop_text += f"👤 <b>{clickable_name}:</b>\n"
            shop_text += f"🌰 Орешки: {user_balance}\n\n"
            shop_text += "🛍️ <b>Что будем покупать?</b>\n\n"
            
            # Добавляем описание товаров
            for item in shop_items:
                shop_text += f"<b>{item['item_name']}</b>\n"
                shop_text += f"📝 {item['description']}\n"
                shop_text += f"💰 {int(item['price'])} орешков\n\n"
            
            await update.message.reply_text(shop_text, reply_markup=reply_markup, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения магазина: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            await update.message.reply_text("❌ Произошла ошибка при получении магазина. Попробуйте позже.", parse_mode='HTML')

    async def game_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создает запись в таблице games для пользователя"""
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or "Unknown"
        
        try:
            if not self.db:
                await update.message.reply_text("❌ База данных недоступна. Попробуйте позже.")
                return
            
            # Убеждаемся, что пользователь существует в БД
            user = get_user_by_telegram_id(user_id)
            if not user:
                create_user(user_id, username)
                logger.info(f"✅ Пользователь {user_id} ({username}) создан в БД")
            
            # Создаем запись в таблице user_games
            game_query = """
                INSERT INTO user_games (user_id, game_type, status) 
                VALUES (%s, %s, %s)
                RETURNING id, created_at
            """
            
            result = fetch_one(game_query, (user_id, 'forest_mafia', 'created'))
            
            if result:
                game_id = result['id']
                created_at = result['created_at']
                
                await update.message.reply_text(
                    f"🎮 <b>Новая игра создана!</b>\n\n"
                    f"🆔 ID игры: {game_id}\n"
                    f"👤 Игрок: {username}\n"
                    f"🎯 Тип игры: Forest Mafia\n"
                    f"📅 Создана: {created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"💡 Используйте /start для начала регистрации в игру!",
                    parse_mode='HTML'
                )
                
                logger.info(f"✅ Игра {game_id} создана для пользователя {user_id}")
            else:
                await update.message.reply_text("❌ Не удалось создать игру. Попробуйте позже.")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания игры: {e}")
            await update.message.reply_text("❌ Произошла ошибка при создании игры. Попробуйте позже.")

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /cancel"""
        user_id = update.effective_user.id
        
        # Проверяем, ожидает ли пользователь ввода кастомного прощального сообщения
        if f'waiting_custom_farewell_{user_id}' in context.user_data:
            del context.user_data[f'waiting_custom_farewell_{user_id}']
            await update.message.reply_text("❌ Создание прощального сообщения отменено.")
        else:
            await update.message.reply_text("ℹ️ Нет активных операций для отмены.")

    async def update_player_stats_after_game(self, game: Game, winner: Optional[Team] = None):
        """Обновляет статистику игроков после окончания игры"""
        try:
            if not self.db:
                logger.warning("⚠️ База данных недоступна, статистика не обновлена")
                return
            
            for player in game.players.values():
                user_id = player.user_id
                username = player.username or f"Player_{user_id}"
                
                # Создаем пользователя в БД, если его нет
                create_user(user_id, username)
                
                # Получаем текущую статистику
                stats = fetch_one("SELECT * FROM stats WHERE user_id = %s", (user_id,))
                
                if stats:
                    # Обновляем существующую статистику
                    new_games_played = stats['games_played'] + 1
                    
                    # Определяем, выиграл ли игрок
                    player_won = False
                    if winner:
                        if winner == Team.HERBIVORES and player.team == Team.HERBIVORES:
                            player_won = True
                        elif winner == Team.PREDATORS and player.team == Team.PREDATORS:
                            player_won = True
                    
                    if player_won:
                        new_games_won = stats['games_won'] + 1
                        new_games_lost = stats['games_lost']
                    else:
                        new_games_won = stats['games_won']
                        new_games_lost = stats['games_lost'] + 1
                    
                    # Обновляем статистику используя функцию из database_psycopg2
                    success = update_user_stats(user_id, new_games_played, new_games_won, new_games_lost)
                    if not success:
                        logger.error(f"❌ Не удалось обновить статистику для пользователя {user_id}")
                    
                else:
                    # Создаем новую статистику
                    player_won = False
                    if winner:
                        if winner == Team.HERBIVORES and player.team == Team.HERBIVORES:
                            player_won = True
                        elif winner == Team.PREDATORS and player.team == Team.PREDATORS:
                            player_won = True
                    
                    # Создаем новую статистику используя функцию из database_psycopg2
                    success = update_user_stats(user_id, 1, 1 if player_won else 0, 0 if player_won else 1)
                    if not success:
                        logger.error(f"❌ Не удалось создать статистику для пользователя {user_id}")
                
                # Логируем результат
                if 'new_games_played' in locals():
                    logger.info(f"✅ Статистика обновлена для игрока {user_id}: игры={new_games_played}, победы={new_games_won if 'new_games_won' in locals() else (1 if player_won else 0)}")
                else:
                    logger.info(f"✅ Статистика создана для игрока {user_id}: игры=1, победы={1 if player_won else 0}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики: {e}")

    async def award_nuts_for_game(self, game: Game, winner: Optional[Team] = None):
        """Начисляет орешки игрокам за участие в игре"""
        nuts_info = ""
        try:
            if not self.db:
                logger.warning("⚠️ База данных недоступна, орешки не начислены")
                return nuts_info
            
            logger.info(f"🎮 Начинаем начисление орешков за игру. Игроков: {len(game.players)}, Победитель: {winner}")
            
            # Получаем настройки чата для проверки начисления наград
            chat_settings = get_chat_settings(game.chat_id)
            loser_rewards_enabled = chat_settings.get('loser_rewards_enabled', True)
            dead_rewards_enabled = chat_settings.get('dead_rewards_enabled', True)
            logger.info(f"🏆 Награды проигравшим: {'ВКЛ' if loser_rewards_enabled else 'ВЫКЛ'}")
            logger.info(f"💀 Награды умершим: {'ВКЛ' if dead_rewards_enabled else 'ВЫКЛ'}")
            
            nuts_awards = []  # Список для хранения информации о наградах
            
            for player in game.players.values():
                user_id = player.user_id
                username = player.username or f"Player_{user_id}"
                
                logger.info(f"👤 Обрабатываем игрока: {username} (ID: {user_id}), Жив: {player.is_alive}, Команда: {player.team}, Роль: {player.role}")
                
                # Создаем пользователя в БД, если его нет
                create_user(user_id, username)
                
                # Определяем количество орешков в зависимости от статуса игрока
                nuts_amount = 0
                
                if player.is_alive:
                    # Живой игрок
                    if winner:
                        # Определяем, выиграл ли игрок
                        player_won = False
                        if winner == Team.HERBIVORES and player.team == Team.HERBIVORES:
                            player_won = True
                        elif winner == Team.PREDATORS and player.team == Team.PREDATORS:
                            player_won = True
                        
                        if player_won:
                            nuts_amount = 100  # Победитель получает 100 орешков
                            logger.info(f"🏆 Игрок {username} - победитель, получает 100 орешков")
                        else:
                            nuts_amount = 50   # Проигравший получает 50 орешков
                            logger.info(f"😔 Игрок {username} - проигравший, получает 50 орешков")
                    else:
                        nuts_amount = 50  # Если нет победителя, все живые получают 50
                        logger.info(f"🤷 Игрок {username} - живой, но нет победителя, получает 50 орешков")
                else:
                    # Мертвый игрок получает 25 орешков (если награды умершим включены)
                    if dead_rewards_enabled:
                        nuts_amount = 25
                        logger.info(f"💀 Игрок {username} - мертвый, получает 25 орешков")
                    else:
                        nuts_amount = 0
                        logger.info(f"💀 Игрок {username} - мертвый, но награды умершим отключены")
                
                # Если награды проигравшим отключены, не начисляем орешки проигравшим
                if not loser_rewards_enabled and winner:
                    # Проверяем, проиграл ли игрок
                    player_lost = False
                    if winner == Team.HERBIVORES and player.team == Team.PREDATORS:
                        player_lost = True
                    elif winner == Team.PREDATORS and player.team == Team.HERBIVORES:
                        player_lost = True
                    
                    if player_lost:
                        nuts_amount = 0  # Проигравшие не получают орешки
                        logger.info(f"🏆 Игрок {username} проиграл, но награды проигравшим отключены")
                
                # Начисляем орешки через новую систему баланса
                if nuts_amount > 0:
                    logger.info(f"💰 Начисляем {nuts_amount} орешков игроку {username} (ID: {user_id})")
                    from database_balance_manager import balance_manager
                    success = balance_manager.add_to_balance(user_id, nuts_amount)
                    if success:
                        logger.info(f"✅ Начислено {nuts_amount} орешков игроку {username} (ID: {user_id})")
                        nuts_awards.append(f"🌰 {username}: +{nuts_amount} орешков")
                    else:
                        logger.error(f"❌ Не удалось начислить орешки игроку {username} (ID: {user_id})")
                else:
                    logger.warning(f"⚠️ Игрок {username} не получил орешки (amount=0)")
            
            # Формируем информацию об орешках для сообщения
            if nuts_awards:
                nuts_info = f"🌰 <b>Награды за игру:</b>\n" + "\n".join(nuts_awards)
                        
        except Exception as e:
            logger.error(f"❌ Ошибка начисления орешков: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        return nuts_info

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
        
        # Создаем или обновляем пользователя в базе данных
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or "Unknown"
        
        try:
            if self.db:
                # Создаем пользователя в БД (если его нет)
                create_user(user_id, username)
                logger.info(f"✅ Пользователь {user_id} ({username}) создан/обновлен в БД")
            else:
                logger.warning("⚠️ База данных недоступна, пользователь не создан в БД")
        except Exception as e:
            logger.error(f"❌ Ошибка создания пользователя в БД: {e}")
        
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
            # Создаем клавиатуру для личных сообщений
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
                "🌲 <b>Привет!</b>\n\n"
                "Я бот-ведущий для игры в 🌲 <b>Лес и Волки</b>.\n\n"
                "🎭 <b>Ролевая игра в стиле 'Мафия' с лесными зверушками</b>\n\n"
                "🐺 <b>Хищники:</b> Волки + Лиса\n"
                "🐰 <b>Травоядные:</b> Зайцы + Крот + Бобёр\n\n"
                "🌙 <b>Как играть:</b>\n"
                "• Ночью хищники охотятся, травоядные защищаются\n"
                "• Днем все обсуждают и голосуют за изгнание\n"
                "• Цель: уничтожить всех противников\n\n"
                "🚀 <b>Выберите действие:</b>"
            )
            
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return

        # Создаем игру, если её нет
        if chat_id not in self.games:
            self.games[chat_id] = Game(chat_id=chat_id, thread_id=update.effective_message.message_thread_id, is_test_mode=self.global_settings.is_test_mode())
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
            [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")]
        ]
        
        # Добавляем кнопку "Быстрый режим" (только для админов)
        if await self.is_user_admin(update, context):
            quick_mode_text = "⚡ Быстрый режим: ВКЛ" if self.global_settings.is_test_mode() else "⚡ Быстрый режим: ВЫКЛ"
            keyboard.append([InlineKeyboardButton(quick_mode_text, callback_data="toggle_quick_mode_game")])
        
        # Добавляем кнопку "Начать игру" если достаточно игроков
        if game.can_start_game():
            keyboard.append([InlineKeyboardButton("🚀 Начать игру", callback_data="start_game")])
        
        # Добавляем кнопку "Отменить игру" для администраторов
        if await self.is_user_admin(update, context):
            keyboard.append([InlineKeyboardButton("🛑 Отменить игру", callback_data="cancel_game")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Формируем сообщение о регистрации
        # Получаем настройки чата для правильного отображения минимума игроков
        chat_settings = get_chat_settings(chat_id)
        min_players = chat_settings.get('min_players', 6)
        current_players = len(game.players)
        
        registration_text = (
            "🌲 <b>Регистрация в игру 'Лес и Волки'</b> 🌲\n\n"
            "🎭 <b>Ролевая игра в стиле 'Мафия' с лесными зверушками</b>\n\n"
            "🐺 <b>Хищники:</b> Волки + Лиса\n"
            "🐰 <b>Травоядные:</b> Зайцы + Крот + Бобёр\n\n"
            f"👥 <b>Игроков зарегистрировано:</b> {current_players}\n"
            f"📋 <b>Минимум для начала:</b> {min_players}\n"
            f"{'⚡ <b>БЫСТРЫЙ РЕЖИМ</b>' if chat_settings.get('test_mode', False) else ''}\n\n"
            "🎯 <b>Цель:</b> Уничтожить команду противника!\n\n"
            "🚀 <b>Нажмите 'Присоединиться к игре' для участия!</b>"
        )

        await update.message.reply_text(
            registration_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
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
        """Показывает советы по игре для роли игрока в личных сообщениях"""
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
        
        # Сначала отправляем базовую информацию о роли
        role_info = self.get_role_info(player.role)
        team_name = "🦁 Хищники" if player.team.name == "PREDATORS" else "🌿 Травоядные"
        
        role_message = (
            f"🎭 Ваша роль в игре 'Лес и Волки':\n\n"
            f"👤 {role_info['name']}\n"
            f"🏴 Команда: {team_name}\n\n"
            f"📖 Описание:\n{role_info['description']}"
        )
        
        await update.message.reply_text(role_message)
        
        # Формируем советы по игре для роли
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
        
        # Детальные советы по игре для каждой роли
        role_game_tips = {
            Role.WOLF: {
                "title": "🐺 Советы для Волка",
                "description": "Вы - лидер хищников! Ваша цель - уничтожить всех травоядных.",
                "tips": [
                    "🎯 <b>Выбор жертвы:</b> Выбирайте активных игроков, которые могут быть кротом или бобром",
                    "🤝 <b>Работа в команде:</b> Найдите лису и координируйте действия",
                    "🎭 <b>Маскировка:</b> Не привлекайте к себе внимание в обсуждениях",
                    "📊 <b>Анализ:</b> Следите за голосованиями - кто голосует против кого",
                    "⏰ <b>Тайминг:</b> Не убивайте слишком рано, чтобы не выдать себя"
                ],
                "night_action": "🌙 <b>Ночное действие:</b> Выбирайте жертву для убийства",
                "win_condition": "🏆 <b>Цель:</b> Уничтожить всех травоядных"
            },
            Role.FOX: {
                "title": "🦊 Советы для Лисы",
                "description": "Вы - вор! Крадите орешки у травоядных, но не более 2 раз.",
                "tips": [
                    "💰 <b>Выбор цели:</b> Воруйте у игроков с большим количеством орешков",
                    "🎭 <b>Скрытность:</b> Не воруйте у одного игрока дважды подряд",
                    "🤝 <b>Координация:</b> Работайте с волками, но не раскрывайтесь",
                    "📈 <b>Стратегия:</b> Воруйте у подозрительных игроков",
                    "⚠️ <b>Осторожность:</b> После 2 краж вы умрете!"
                ],
                "night_action": "🌙 <b>Ночное действие:</b> Выбирайте игрока для кражи орешков",
                "win_condition": "🏆 <b>Цель:</b> Помочь хищникам победить"
            },
            Role.HARE: {
                "title": "🐰 Советы для Зайца",
                "description": "Вы - обычный мирный житель. Выживайте и помогайте команде найти хищников.",
                "tips": [
                    "👂 <b>Наблюдение:</b> Внимательно слушайте обсуждения и анализируйте поведение",
                    "🗣️ <b>Общение:</b> Задавайте вопросы, но не раскрывайте важную информацию",
                    "📊 <b>Анализ:</b> Следите за голосованиями и выявляйте подозрительных",
                    "🤝 <b>Команда:</b> Работайте с кротом и бобром",
                    "🎭 <b>Маскировка:</b> Не привлекайте к себе внимание хищников"
                ],
                "night_action": "🌙 <b>Ночное действие:</b> Отдыхайте и ждите утра",
                "win_condition": "🏆 <b>Цель:</b> Найти и изгнать всех хищников"
            },
            Role.MOLE: {
                "title": "🦫 Советы для Крота",
                "description": "Вы - детектив! Проверяйте роли игроков каждую ночь.",
                "tips": [
                    "🔍 <b>Выбор цели:</b> Проверяйте подозрительных игроков",
                    "📝 <b>Запись:</b> Записывайте результаты проверок",
                    "🤝 <b>Команда:</b> Делитесь информацией с травоядными",
                    "🎭 <b>Скрытность:</b> Не раскрывайте свою роль раньше времени",
                    "📊 <b>Анализ:</b> Используйте информацию для голосований"
                ],
                "night_action": "🌙 <b>Ночное действие:</b> Выбирайте игрока для проверки роли",
                "win_condition": "🏆 <b>Цель:</b> Помочь травоядным найти хищников"
            },
            Role.BEAVER: {
                "title": "🦦 Советы для Бобра",
                "description": "Вы - защитник! Защищайте травоядных от лисы, возвращая украденные орешки.",
                "tips": [
                    "🛡️ <b>Защита:</b> Защищайте игроков, у которых украли орешки",
                    "💰 <b>Восстановление:</b> Возвращайте украденные орешки",
                    "🤝 <b>Команда:</b> Работайте с кротом и зайцами",
                    "📊 <b>Анализ:</b> Следите за тем, у кого украли орешки",
                    "🎭 <b>Скрытность:</b> Не раскрывайте свою роль"
                ],
                "night_action": "🌙 <b>Ночное действие:</b> Выбирайте игрока для защиты",
                "win_condition": "🏆 <b>Цель:</b> Помочь травоядным победить"
            }
        }
        
        tips = role_game_tips[player.role]
        
        message = f"{tips['title']}\n\n"
        message += f"🏷️ <b>Команда:</b> {team_names[player.team]}\n"
        message += f"📝 <b>Описание:</b> {tips['description']}\n\n"
        
        message += "💡 <b>Советы по игре:</b>\n"
        for tip in tips['tips']:
            message += f"{tip}\n"
        
        message += f"\n{tips['night_action']}\n"
        message += f"{tips['win_condition']}\n\n"
        
        message += f"🎮 <b>Текущий раунд:</b> {game.current_round}\n"
        message += f"🌙 <b>Выжили ночей:</b> {player.consecutive_nights_survived}\n\n"
        
        message += "🎯 <b>Общие советы:</b>\n"
        message += "• Внимательно читайте сообщения бота\n"
        message += "• Анализируйте поведение других игроков\n"
        message += "• Не раскрывайте свою роль раньше времени\n"
        message += "• Работайте в команде с союзниками"
        
        await update.message.reply_text(message, parse_mode='HTML')

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
                # Любой пользователь может начинать игру
                pass
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
                        reply_markup=self._get_join_keyboard(game, context),
                        parse_mode='HTML'
                    )
        except Exception as e:
            logger.error(f"Error updating join message: {e}")

    def _get_join_message_text(self, game) -> str:
        """Формирует текст сообщения о присоединении"""
        max_players = getattr(game, "MAX_PLAYERS", 12)
        players_list = ""
        for player in game.players.values():
            player_tag = self.format_player_tag(player.username, player.user_id, make_clickable=True)
            players_list += f"• {player_tag}\n"
        
        # Получаем настройки чата для правильного отображения минимума игроков
        chat_settings = get_chat_settings(game.chat_id)
        min_players = chat_settings.get('min_players', 6)
        
        message = (
            "🌲 <b>Лес и Волки - Регистрация</b> 🌲\n\n"
            f"👥 Игроков: {len(game.players)}/{max_players}\n"
            f"📋 Минимум для старта: {min_players}\n\n"
            f"📝 Участники:\n{players_list}"
        )
        
        if game.can_start_game():
            message += "\n✅ Можно начинать игру!"
        else:
            message += f"\n⏳ Нужно ещё {max(0, min_players - len(game.players))} игроков"
        
        return message

    def _get_join_keyboard(self, game, context) -> InlineKeyboardMarkup:
        """Формирует клавиатуру для сообщения о присоединении"""
        keyboard = []
        
        # Кнопка "Посмотреть свою роль" (если игра идет)
        if game.phase != GamePhase.WAITING:
            keyboard.append([InlineKeyboardButton("👁️ Посмотреть свою роль", callback_data="repeat_role_actions")])
        
        # Основные кнопки управления игрой
        if game.phase == GamePhase.WAITING:
            # Кнопки для фазы ожидания
            keyboard.append([InlineKeyboardButton("✅ Присоединиться", callback_data="join_game")])
            keyboard.append([InlineKeyboardButton("❌ Покинуть игру", callback_data="leave_registration")])
            
            # Кнопка "Магазин"
            keyboard.append([InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")])
            
            # Кнопка "Быстрый режим" (только для админов)
            # Добавляем кнопку для всех - проверка прав будет в callback
            quick_mode_text = "⚡ Быстрый режим: ВКЛ" if self.global_settings.is_test_mode() else "⚡ Быстрый режим: ВЫКЛ"
            keyboard.append([InlineKeyboardButton(quick_mode_text, callback_data="toggle_quick_mode_game")])
            
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
        
        # Создаем пользователя в БД
        try:
            if self.db:
                create_user(user_id, username)
                logger.info(f"✅ Пользователь {user_id} ({username}) создан/обновлен в БД при join_from_callback")
        except Exception as e:
            logger.error(f"❌ Ошибка создания пользователя в БД: {e}")

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
                        join_message = await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
                        await context.bot.unpin_chat_message(chat_id, game.pinned_message_id)
                        await context.bot.pin_chat_message(chat_id, join_message.message_id)
                        game.pinned_message_id = join_message.message_id
                        logger.info(f"Создано и закреплено новое сообщение о присоединении: {join_message.message_id}")
                else:
                    # Если нет закрепленного сообщения, создаем новое
                    join_message = await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
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
                "📊 <b>Статус:</b> Ожидание игроков\n\n"
                f"👥 Игроков: {len(game.players)}/12\n"
                f"📋 Минимум: {min_players}\n\n"
                "<b>Участники:</b>\n"
            )
            for player in game.players.values():
                player_tag = self.format_player_tag(player.username, player.user_id, make_clickable=True)
                status_text += f"• {player_tag}\n"
            if game.can_start_game():
                status_text += "\n✅ <b>Можно начинать игру!</b>"
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
                f"📊 <b>Статус:</b> {phase_names.get(game.phase, 'Неизвестно')}\n\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых: {len(game.get_alive_players())}\n\n"
                "<b>Живые игроки:</b>\n"
            )
            for p in game.get_alive_players():
                player_tag = self.format_player_tag(p.username, p.user_id, make_clickable=True)
                status_text += f"• {player_tag}\n"

        await query.edit_message_text(status_text)


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
        
        # Создаем пользователя в БД
        try:
            if self.db:
                create_user(user_id, username)
                logger.info(f"✅ Пользователь {user_id} ({username}) создан/обновлен в БД при join")
        except Exception as e:
            logger.error(f"❌ Ошибка создания пользователя в БД: {e}")

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
                        join_message = await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
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
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

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
            
            player_tag = self.format_player_tag(username, user_id, make_clickable=True)
            # Показываем обновленный список игроков с тегами
            players_list = ""
            for player in game.players.values():
                tag = self.format_player_tag(player.username, player.user_id, make_clickable=True)
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
                
            await update.message.reply_text(message, parse_mode='HTML')
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
                "📊 <b>Статус:</b> Ожидание игроков\n\n"
                f"👥 Игроков: {len(game.players)}/12\n"
                f"📋 Минимум: {min_players}\n\n"
                "<b>Участники:</b>\n"
            )
            for player in game.players.values():
                player_tag = self.format_player_tag(player.username, player.user_id, make_clickable=True)
                status_text += f"• {player_tag}\n"
            if game.can_start_game():
                status_text += "\n✅ <b>Можно начинать игру!</b>"
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
                f"📊 <b>Статус:</b> {phase_names.get(game.phase, 'Неизвестно')}\n\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых: {len(game.get_alive_players())}\n\n"
                "<b>Живые игроки:</b>\n"
            )
            for p in game.get_alive_players():
                player_tag = self.format_player_tag(p.username, p.user_id, make_clickable=True)
                status_text += f"• {player_tag}\n"

        # Создаем кнопки для статуса
        keyboard = []
        
        # Добавляем кнопку "Повторить текущий этап" если игра не в фазе ожидания
        if game.phase != GamePhase.WAITING:
            keyboard.append([InlineKeyboardButton("🔄 Повторить текущий этап", callback_data="repeat_current_phase")])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        await update.message.reply_text(status_text, reply_markup=reply_markup)

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
        username = update.effective_user.username or update.effective_user.first_name or "Unknown"
        thread_id = self.get_thread_id(update)
        
        # Создаем пользователя в БД
        try:
            if self.db:
                create_user(user_id, username)
                logger.info(f"✅ Пользователь {user_id} ({username}) создан/обновлен в БД при start_game")
        except Exception as e:
            logger.error(f"❌ Ошибка создания пользователя в БД: {e}")

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
        import uuid
        db_game_id = str(uuid.uuid4())
        
        # Сохраняем игру в БД
        save_game_to_db(
            game_id=db_game_id,
            chat_id=chat_id,
            thread_id=thread_id,
            status='waiting',
            settings={
            "min_players": min_players,
            "max_players": self.global_settings.get("max_players", 12),
            "night_duration": self.global_settings.get("night_duration", 60),
            "day_duration": self.global_settings.get("day_duration", 300),
            "voting_duration": self.global_settings.get("voting_duration", 120)
            }
        )
        
        # Сохраняем ID игры в БД в объекте игры
        game.db_game_id = db_game_id

        if game.start_game():
            # Обновляем статус игры в БД
            update_game_phase(db_game_id, 'night', 1)
            
            # Добавляем всех игроков в БД
            for player in game.players.values():
                player_id = str(uuid.uuid4())
                save_player_to_db(
                    player_id=player_id,
                    game_id=db_game_id,
                    user_id=player.user_id,
                    username=player.username,
                    first_name=player.first_name,
                    last_name=player.last_name,
                    role=player.role.value if player.role else None,
                    team=player.team.value if player.team else None,
                    is_alive=True
                )
            
            # Тегируем всех участников игры
            await self.tag_game_participants(update, context, game)
            
            await self.start_night_phase(context, game)
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

        # Очищаем все игровые сессии в памяти
        self.games.clear()
        self.player_games.clear()
        self.night_actions.clear()
        self.night_interfaces.clear()
        
        # Очищаем сохраненное состояние
        if hasattr(self, 'auto_save_manager') and self.auto_save_manager:
            try:
                from state_persistence import state_persistence
                state_persistence.clear_all_state()
                logger.info("✅ Сохраненное состояние очищено")
            except Exception as e:
                logger.error(f"❌ Ошибка очистки сохраненного состояния: {e}")

        await update.message.reply_text(
            "🧹 Все игровые сессии очищены!\n\n"
            f"📊 Было завершено игр: {games_count}\n"
            f"👥 Было освобождено игроков: {players_count}\n"
            f"💾 Сохраненное состояние также очищено"
        )
    
    async def save_state_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для принудительного сохранения состояния"""
        # Проверяем права пользователя (только администраторы)
        has_permission, error_msg = await self.check_user_permissions(update, context, "admin")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        try:
            # Принудительно сохраняем состояние
            self.force_save_state()
            
            await update.message.reply_text(
                "💾 <b>Состояние сохранено!</b>\n\n"
                f"📊 Активных игр: {len(self.games)}\n"
                f"👥 Игроков в играх: {len(self.player_games)}\n"
                f"🔗 Авторизованных чатов: {len(self.authorized_chats)}\n\n"
                "✅ Все данные сохранены в базу данных"
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка принудительного сохранения: {e}")
            await update.message.reply_text(
                "❌ <b>Ошибка сохранения!</b>\n\n"
                f"Не удалось сохранить состояние: {str(e)}"
            )
    
    async def auto_save_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для проверки статуса автоматического сохранения"""
        # Проверяем права пользователя (только администраторы)
        has_permission, error_msg = await self.check_user_permissions(update, context, "admin")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        try:
            if hasattr(self, 'auto_save_manager') and self.auto_save_manager:
                status = self.auto_save_manager.get_save_status()
                
                status_text = (
                    "💾 <b>Статус автоматического сохранения</b>\n\n"
                    f"🔄 Работает: {'✅ Да' if status['is_running'] else '❌ Нет'}\n"
                    f"⏱️ Интервал: {status['save_interval']} секунд\n"
                    f"🕐 Последнее сохранение: {status['last_save_time']}\n"
                    f"⏰ Прошло времени: {status['time_since_last_save']:.1f} секунд\n\n"
                    f"📊 <b>Текущее состояние:</b>\n"
                    f"🎮 Активных игр: {len(self.games)}\n"
                    f"👥 Игроков в играх: {len(self.player_games)}\n"
                    f"🔗 Авторизованных чатов: {len(self.authorized_chats)}"
                )
                
                await update.message.reply_text(status_text, parse_mode='HTML')
            else:
                await update.message.reply_text(
                    "❌ <b>Автоматическое сохранение недоступно</b>\n\n"
                    "Менеджер автоматического сохранения не инициализирован."
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса сохранения: {e}")
            await update.message.reply_text(
                "❌ <b>Ошибка получения статуса!</b>\n\n"
                f"Не удалось получить статус: {str(e)}"
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
            self.games[chat_id] = Game(chat_id, thread_id, is_test_mode=self.global_settings.is_test_mode())
            self.night_actions[chat_id] = NightActions(self.games[chat_id])
            self.night_interfaces[chat_id] = NightInterface(self.games[chat_id], self.night_actions[chat_id])
            
            # Создаем клавиатуру с быстрыми действиями
            keyboard = [
                [InlineKeyboardButton("👥 Присоединиться к игре", callback_data="welcome_start_game")],
                [InlineKeyboardButton("📖 Правила игры", callback_data="welcome_rules")],
                [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")]
            ]
            
            # Добавляем кнопку "Быстрый режим" (только для админов)
            if await self.is_user_admin(update, context):
                quick_mode_text = "⚡ Быстрый режим: ВКЛ" if self.global_settings.is_test_mode() else "⚡ Быстрый режим: ВЫКЛ"
                keyboard.append([InlineKeyboardButton(quick_mode_text, callback_data="toggle_quick_mode_game")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение об успешной настройке
            setup_message = (
                f"✅ {location_short} успешно настроен для игры 'Лес и Волки'!\n\n"
                f"🎮 Тип чата: {chat_type}\n"
                f"📍 Область действия: {location_name}\n"
                f"📋 Минимум игроков: {self.global_settings.get_min_players()}\n"
                f"👥 Максимум игроков: {getattr(self.games[chat_id], 'MAX_PLAYERS', 12)}\n"
                f"⚡ Быстрый режим: {'Включен' if self.global_settings.is_test_mode() else 'Отключен'}\n\n"
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
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о завершении игры: {e}")
            # Fallback - попробуем отправить без форматирования
            try:
                await context.bot.send_message(
                    chat_id=game.chat_id,
                    text=message_text.replace('*', '').replace('_', ''),
                    message_thread_id=game.thread_id
                )
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
        
        # Сохраняем состояние после завершения игры
        if hasattr(self, 'auto_save_manager') and self.auto_save_manager:
            try:
                self.auto_save_manager.force_save()
                logger.info("✅ Состояние сохранено после завершения игры")
            except Exception as e:
                logger.error(f"❌ Ошибка сохранения состояния после завершения игры: {e}")

    # ---------------- night/day/vote flow ----------------
    async def start_night_phase(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        game.start_night()
        
        # Сохраняем смену фазы в базу данных
        if hasattr(game, 'db_game_id') and game.db_game_id:
            update_game_phase(game.db_game_id, "night", game.current_round)
        
        # Автосохранение состояния игры
        self.save_game_state(game.chat_id)
        
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
            "<b>И вот наступила ночь, зверушки мирно уснули сладким сном… 😴</b>"
        )
        
        # Отправляем сообщение о начале ночи
        await context.bot.send_message(
            chat_id=game.chat_id,
            text=forest_story,
            parse_mode='HTML',
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
                mole_text = "🦫 Вот ты где, дружок <b>Крот</b>! Не устал еще ночью рыть норки, попадая в домики других зверей? А хотя... Знаешь, это может быть очень полезно, ведь так можно узнать кто они на самом деле!"
                await context.bot.send_message(chat_id=mole.user_id, text=mole_text, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение кроту {mole.user_id}: {e}")

        # Beaver intro
        beavers = game.get_players_by_role(Role.BEAVER)
        for beaver in beavers:
            try:
                beaver_text = "🦦 Наш <b>Бобёр</b> весьма хитёр – всё добро несёт в шатёр. У <b>бобра</b> в шатре добра – бочка, кадка, два ведра!"
                await context.bot.send_message(chat_id=beaver.user_id, text=beaver_text, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение бобру {beaver.user_id}: {e}")

        # Fox intro
        foxes = game.get_players_by_role(Role.FOX)
        for fox in foxes:
            try:
                fox_text = "🦊 Жила-была <b>Лиса</b>-воровка, да не подвела ее сноровка! 🦊"
                await context.bot.send_message(chat_id=fox.user_id, text=fox_text, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение лисе {fox.user_id}: {e}")

        # Отправляем роли всем игрокам (только в первой ночи)
        if game.current_round == 1:
            await self.send_roles_to_players(context, game)
        
        # меню ночных действий
        await self.send_night_actions_to_players(context, game)

        # Отправляем кнопку просмотра роли игрокам без ночных действий
        await self.send_role_button_to_passive_players(context, game)

        # таймер ночи (запускаем как таск)
        asyncio.create_task(self.night_phase_timer(context, game))

    async def night_phase_timer(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
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
                    await self.process_night_phase(context, game)
                    await self.start_day_phase(context, game)
                    return
            
            # Если игра завершилась или фаза изменилась - выходим
            if game.phase != GamePhase.NIGHT:
                logger.info(f"Ночная фаза прервана: фаза изменилась на {game.phase}")
                return
        
        # Время вышло
        if game.phase == GamePhase.NIGHT:
            await self.process_night_phase(context, game)
            await self.start_day_phase(context, game)

    async def start_day_phase(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        # Проверяем условия автоматического завершения игры
        winner = game.check_game_end()
        if winner:
            await self.end_game_winner(context, game, winner)
            return
            
        game.start_day()
        
        # Сохраняем смену фазы в базу данных
        if hasattr(game, 'db_game_id') and game.db_game_id:
            update_game_phase(game.db_game_id, "day", game.current_round)
        
        # Автосохранение состояния игры
        self.save_game_state(game.chat_id)

        # Открепляем сообщение ночи
        await self._unpin_previous_stage_message(context, game, "day")

        # Создаем кнопки для дневной фазы
        keyboard = [
            [InlineKeyboardButton("🏁 Завершить обсуждение", callback_data="day_end_discussion")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        day_message = await context.bot.send_message(
            chat_id=game.chat_id,
            text="☀️ Наступило утро ☀️\n\n"
            "Начался очередной спокойный солнечный день в нашем дивном Лесу ☀️ Друзья зверята собрались вместе обсуждать новости последних дней 💬\n\n"
            "У вас есть 5 минут, чтобы обсудить ночные события и решить, кого изгнать.\n\n"
            "Используйте кнопки ниже для управления фазой:",
            reply_markup=reply_markup,
            message_thread_id=game.thread_id
        )
        
        # Закрепляем сообщение дня
        await self._pin_stage_message(context, game, "day", day_message.message_id)
        
        # Создаем и сохраняем задачу таймера дневной фазы
        day_timer_task = asyncio.create_task(self.day_phase_timer(context, game))
        game.set_day_timer_task(day_timer_task)

    async def day_phase_timer(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Таймер дневной фазы с диагностикой"""
        try:
            logger.info(f"Запущен таймер дневной фазы для игры {game.chat_id}")
            await asyncio.sleep(300)  # 5 минут
            
            # Проверяем, что игра все еще в дневной фазе
            if game.phase == GamePhase.DAY:
                logger.info(f"Таймер дневной фазы завершен, переходим к голосованию для игры {game.chat_id}")
                await self.start_voting_phase(context, game)
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

    async def start_voting_phase(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        game.start_voting()
        
        # Сохраняем смену фазы в базу данных
        if hasattr(game, 'db_game_id') and game.db_game_id:
            update_game_phase(game.db_game_id, "voting", game.current_round)
        
        # Автосохранение состояния игры
        self.save_game_state(game.chat_id)

        alive_players = game.get_alive_players()
        if len(alive_players) < 2:
            # Создаем фиктивный update для _end_game_internal
            from telegram import Update
            fake_update = Update(update_id=0)
            await self._end_game_internal(fake_update, context, game, "Недостаточно игроков для голосования")
            return

        # Открепляем сообщение дня
        await self._unpin_previous_stage_message(context, game, "voting")

        # Создаем клавиатуру для сообщения голосования
        voting_keyboard = [
            [InlineKeyboardButton("💬 Перейти в ЛС с ботом", url=f"https://t.me/{context.bot.username}")]
        ]
        voting_reply_markup = InlineKeyboardMarkup(voting_keyboard)
        
        # Отправляем уведомление в общий чат
        chat_message = (
            "🌲 \"Кого же мы изгоним из нашего Леса?\" - шепчут зверушки между собой.\n\n"
            "🦌 Зайцы переглядываются, 🐺 волки притворяются невинными, а 🦊 лиса уже готовит план...\n\n"
            "⏰ У вас есть 2 минуты, чтобы решить судьбу одного из обитателей леса!\n"
            "📱 Проверьте личные сообщения с ботом - там вас ждет важное решение."
        )
        
        voting_message = await context.bot.send_message(
            chat_id=game.chat_id, 
            text=chat_message, 
            message_thread_id=game.thread_id,
            reply_markup=voting_reply_markup
        )
        
        # Закрепляем сообщение голосования
        if voting_message:
            await self._pin_stage_message(context, game, "voting", voting_message.message_id)

        # Отправляем меню голосования каждому живому игроку в личку
        for voter in alive_players:
            # Исключаем самого голосующего из списка целей
            voting_targets = [p for p in alive_players if p.user_id != voter.user_id]
            keyboard = [[InlineKeyboardButton(f"🗳️ {self.get_display_name(p.user_id, p.username, p.first_name)}", callback_data=f"vote_{p.user_id}")] for p in voting_targets]
            # Добавляем кнопку "Пропустить голосование"
            keyboard.append([InlineKeyboardButton("⏭️ Пропустить голосование", callback_data="vote_skip")])
            # Добавляем кнопку "Перейти в ЛС с ботом" (если это не личные сообщения)
            if game.chat_id != voter.user_id:
                keyboard.append([InlineKeyboardButton("💬 Перейти в ЛС с ботом", url=f"https://t.me/{context.bot.username}")])
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
        
        asyncio.create_task(self.voting_timer(context, game))



    async def voting_timer(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
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
            # Проверяем, не были ли результаты уже обработаны досрочно
            if not (hasattr(game, 'voting_results_processed') and game.voting_results_processed):
                logger.info("Время голосования истекло. Обрабатываем результаты.")
                await self.process_voting_results(context, game)
            else:
                logger.info("Результаты голосования уже были обработаны досрочно.")
        else:
            logger.info(f"Голосование завершилось, но фаза уже {game.phase}")

    async def process_voting_results(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        logger.info(f"Обработка результатов голосования. Голосов: {len(game.votes)}")
        
        # Проверяем, не были ли результаты уже обработаны
        if hasattr(game, 'voting_results_processed') and game.voting_results_processed:
            logger.info("Результаты голосования уже были обработаны, пропускаем")
            return
        
        game.voting_results_processed = True  # Помечаем как обработанные
        
        exiled_player = game.process_voting()
        
        # Получаем детальную информацию о голосовании
        voting_details = game.get_voting_details()
        
        # Проверяем, было ли голосование завершено досрочно
        is_early_completion = hasattr(game, 'exile_voting_completed') and game.exile_voting_completed
        
        # Формируем сообщение с результатами
        if exiled_player:
            role_name = self.get_role_info(exiled_player.role)['name']
            if is_early_completion:
                result_text = f"⚡ Все игроки проголосовали! Голосование за изгнание завершено досрочно.\n\n🌲 {exiled_player.username} покидает лес навсегда...\n🦌 Оказалось, что это был {role_name}!"
            else:
                result_text = f"🌲 {exiled_player.username} покидает лес навсегда...\n🦌 Оказалось, что это был {role_name}!"
        else:
            # Если никто не изгнан, выбираем случайное сообщение
            random_message = random.choice(self.no_exile_messages)
            if is_early_completion:
                result_text = f"⚡ Все игроки проголосовали! Голосование за изгнание завершено досрочно.\n\n🌲 {voting_details['voting_summary']}\n\n{random_message}"
            else:
                result_text = f"🌲 {voting_details['voting_summary']}\n\n{random_message}"
        
        # Добавляем детальную информацию о голосовании
        result_text += "\n\n📊 <b>Результаты голосования:</b>\n"
        
        for voter_name, vote_info in voting_details['vote_breakdown'].items():
            result_text += f"• {voter_name}: {vote_info}\n"
        
        # Добавляем статистику
        result_text += "\n📈 <b>Статистика:</b>\n"
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

        # Отправляем сообщение белочки изгнанному игроку
        if exiled_player:
            await self.send_squirrel_message(context, exiled_player)

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
        alive_players = game.get_alive_players()
        wolves = game.get_players_by_role(Role.WOLF)
        logger.info(f"Проверка окончания игры: живых игроков={len(alive_players)}, волков={len(wolves)}")
        
        winner = game.check_game_end()
        if winner:
            logger.info(f"Игра завершена! Победила команда: {winner}")
            await self.end_game_winner(context, game, winner)
        else:
            logger.info("Игра продолжается. Начинаем новую ночь.")
            await self.start_new_night(context, game)


    async def start_new_night(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        # Открепляем сообщение голосования перед началом новой ночи
        await self._unpin_previous_stage_message(context, game, "night")
        await self.start_night_phase(context, game)

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
                "🌲 <b>Лес просыпается...</b> 🌲\n\n"
                "🦌 Все лесные зверушки собрались на поляне для игры в Лес и Волки!\n"
                "🍃 Шелест листьев, пение птиц, и тайные заговоры в тени деревьев...\n\n"
                f"🐾 <b>Участники лесного совета:</b> {', '.join(player_tags)}\n\n"
                "🎭 Роли уже распределены среди зверушек! Проверьте личные сообщения с ботом.\n"
                "🌙 Скоро наступит первая ночь в лесу, когда хищники выйдут на охоту..."
            )
            
            # Отправляем сообщение с тегами
            try:
                if hasattr(update, 'message') and update.message:
                    await update.message.reply_text(tag_message, parse_mode='HTML')
                else:
                    await context.bot.send_message(
                        chat_id=game.chat_id,
                        text=tag_message,
                        parse_mode='HTML',
                        message_thread_id=game.thread_id
                    )
            except Exception as send_error:
                logger.error(f"Ошибка при отправке сообщения с тегами: {send_error}")
                # Пробуем отправить без parse_mode
                try:
                    await context.bot.send_message(
                        chat_id=game.chat_id,
                        text=tag_message,
                        message_thread_id=game.thread_id
                    )
                except Exception as fallback_error:
                    logger.error(f"Ошибка при отправке сообщения с тегами (fallback): {fallback_error}")
            
            logger.info(f"Отправлено уведомление о начале игры с тегами участников для игры {game.chat_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при тегировании участников игры: {e}")

    async def end_game_winner(self, context: ContextTypes.DEFAULT_TYPE, game: Game, winner: Optional[Team] = None):
        if getattr(game, "game_over_sent", False):
            return
        game.game_over_sent = True

        game.phase = GamePhase.GAME_OVER
        
        # Сохраняем завершение игры в базу данных
        if hasattr(game, 'db_game_id') and game.db_game_id:
            winner_team = winner.value if winner else None
            finish_game_in_db(game.db_game_id, winner_team)
        
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
            
            # Начисляем орешки за участие в игре
            nuts_info = ""
            try:
                nuts_info = await self.award_nuts_for_game(game, winner)
            except Exception as e:
                logger.error(f"❌ Ошибка начисления орешков: {e}")
            
            # Получаем детальное сообщение о завершении игры
            message_text = game_end_logic.get_game_over_message(result, nuts_info)
            
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
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о завершении игры: {e}")
            # Fallback - попробуем отправить без форматирования
            try:
                await context.bot.send_message(
                    chat_id=game.chat_id,
                    text=message_text.replace('*', '').replace('_', ''),
                    message_thread_id=game.thread_id
                )
            except Exception as e2:
                    logger.error(f"Fallback тоже не сработал: {e2}")

        # Обновляем статистику игроков в базе данных
        try:
            if self.db and game.players:
                await self.update_player_stats_after_game(game, winner)
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики игроков: {e}")
        

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
            success = game.vote(user_id, None)  # None означает пропуск
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
        
        success = game.vote(user_id, target_id)
        
        if success:
            target_player = game.players[target_id]
            # Проверяем, голосовал ли игрок ранее
            already_voted = user_id in game.votes
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
                [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")]
            ]
            
            # Добавляем кнопку "Быстрый режим" (только для админов)
            if await self.is_user_admin(query, context):
                quick_mode_text = "⚡ Быстрый режим: ВКЛ" if self.global_settings.is_test_mode() else "⚡ Быстрый режим: ВЫКЛ"
                keyboard.append([InlineKeyboardButton(quick_mode_text, callback_data="toggle_quick_mode_game")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            welcome_text = (
                "🌲 <b>Добро пожаловать в Лес и Волки!</b> 🌲\n\n"
                "🎭 Это ролевая игра в стиле 'Мафия' с лесными зверушками!\n\n"
                "🐺 <b>Хищники:</b> Волки и Лиса\n"
                "🐰 <b>Травоядные:</b> Зайцы, Крот и Бобёр\n\n"
                "🎯 <b>Цель:</b> Уничтожить команду противника!\n\n"
                f"👥 Для игры нужно минимум {self.global_settings.get_min_players()} игроков\n"
                f"{'⚡ БЫСТРЫЙ РЕЖИМ АКТИВЕН' if self.global_settings.is_test_mode() else ''}\n"
                "⏰ Игра состоит из ночных и дневных фаз\n\n"
                "Нажмите кнопку ниже, чтобы начать!"
            )

            await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

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
            has_permission, error_msg = await self.check_game_permissions(update, context, "day_end_discussion")
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
                    'reply_text': lambda self, text, *kwargs: context.bot.send_message(
                        chat_id=game.chat_id, 
                        text=text, 
                        message_thread_id=game.thread_id
                    )
                })()
            })()
            await self.start_voting_phase(context, game)

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
                f"🔍 <b>Диагностика дневного таймера</b>\n\n"
                f"📊 {phase_info}\n"
                f"⏰ {timer_status}\n"
                f"🕐 {time_info}\n"
                f"🔧 {task_info}\n\n"
                "💡 Если таймер не работает, попробуйте завершить обсуждение вручную."
            )
            
            # Создаем кнопку "Закрыть"
            keyboard = [[InlineKeyboardButton("❌ Закрыть", callback_data="close_diagnostics")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(diagnostics_text, parse_mode='HTML', reply_markup=reply_markup)

        elif query.data == "close_diagnostics":
            await query.edit_message_text("🔍 Диагностика закрыта.")

        elif query.data == "repeat_current_phase":
            # Повторяем текущий этап - доступно всем участникам игры
            # Проверяем права пользователя (только участники игры)
            update_temp = Update(update_id=0, callback_query=query)
            has_permission, error_msg = await self.check_user_permissions(
                update_temp, context, "member"
            )
            if not has_permission:
                await query.answer(error_msg, show_alert=True)
                return
            
            if game.phase == GamePhase.WAITING:
                await query.answer("❌ Эта функция недоступна в фазе ожидания!", show_alert=True)
                return

            # Повторно отправляем сообщение в зависимости от текущей фазы
            if game.phase == GamePhase.DAY:
                # Дневная фаза
                phase_message = (
                    "☀️ Наступило утро ☀️\n\n"
                    "🌲 Все зверушки проснулись и собрались на лесной поляне для обсуждения.\n"
                    f"🔄 Раунд: {game.current_round}\n"
                    f"👥 Живых игроков: {len(game.get_alive_players())}\n\n"
                    "💬 Обсуждайте, кого подозреваете в хищничестве!\n"
                    "🕐 У вас есть время для размышлений..."
                )
                
                # Создаем кнопки для дневной фазы
                keyboard = [
                    [InlineKeyboardButton("🏁 Завершить обсуждение", callback_data="day_end_discussion")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
            elif game.phase == GamePhase.NIGHT:
                # Ночная фаза
                phase_message = (
                    "🌙 Наступила ночь 🌙\n\n"
                    "🌲 Все зверушки засыпают в своих укрытиях...\n"
                    f"🔄 Раунд: {game.current_round}\n"
                    f"👥 Живых игроков: {len(game.get_alive_players())}\n\n"
                    "🐺 Хищники выходят на охоту...\n"
                    "🦫 Травоядные спят беспокойно..."
                )
                reply_markup = None
                
            elif game.phase == GamePhase.VOTING:
                # Фаза голосования
                phase_message = (
                    "🗳️ Время голосования! 🗳️\n\n"
                    "🌲 Все зверушки собрались для принятия решения.\n"
                    f"🔄 Раунд: {game.current_round}\n"
                    f"👥 Живых игроков: {len(game.get_alive_players())}\n\n"
                    "🗳️ Голосуйте за изгнание подозрительного зверька!\n"
                    "⏰ У вас есть время на размышления...\n\n"
                    "📱 Проверьте личные сообщения с ботом - там вас ждет важное решение."
                )
                reply_markup = None
                
                # Отправляем кнопки голосования в личные сообщения
                alive_players = game.get_alive_players()
                for voter in alive_players:
                    # Исключаем самого голосующего из списка целей
                    voting_targets = [p for p in alive_players if p.user_id != voter.user_id]
                    keyboard = [[InlineKeyboardButton(f"🗳️ {self.get_display_name(p.user_id, p.username, p.first_name)}", callback_data=f"vote_{p.user_id}")] for p in voting_targets]
                    # Добавляем кнопку "Пропустить голосование"
                    keyboard.append([InlineKeyboardButton("⏭️ Пропустить голосование", callback_data="vote_skip")])
                    reply_markup_voting = InlineKeyboardMarkup(keyboard)

                    try:
                        await context.bot.send_message(
                            chat_id=voter.user_id,
                            text=(
                                "🌲 Время решать судьбу леса!\n\n"
                                "🦌 Кого из обитателей леса вы считаете опасным для остальных зверушек?\n"
                                "⏰ У вас есть время, чтобы сделать свой выбор:"
                            ),
                            reply_markup=reply_markup_voting
                        )
                    except Exception as e:
                        logger.error(f"Не удалось отправить меню голосования игроку {voter.user_id}: {e}")
                
            else:
                # Игра окончена
                phase_message = (
                    "🏁 Игра окончена! 🏁\n\n"
                    f"🔄 Раунд: {game.current_round}\n"
                    f"👥 Живых игроков: {len(game.get_alive_players())}\n\n"
                    "🌲 Игра завершена!"
                )
                reply_markup = None
            
            await context.bot.send_message(
                        chat_id=game.chat_id, 
                text=phase_message,
                reply_markup=reply_markup,
                        message_thread_id=game.thread_id
                    )
            
            phase_names = {
                GamePhase.DAY: "дня",
                GamePhase.NIGHT: "ночи", 
                GamePhase.VOTING: "голосования",
                GamePhase.GAME_OVER: "игры"
            }
            phase_name = phase_names.get(game.phase, "этапа")
            await query.edit_message_text(f"🔄 Сообщение {phase_name} повторно отправлено!")


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

        # Получаем настройки чата из базы данных
        chat_settings = get_chat_settings(chat_id)
        
        test_mode_text = "⚡ Быстрый режим: ВКЛ" if chat_settings['test_mode'] else "⚡ Быстрый режим: ВЫКЛ"

        keyboard = [
            [InlineKeyboardButton("⏱️ Изменить таймеры", callback_data="settings_timers")],
            [InlineKeyboardButton("🎭 Изменить распределение ролей", callback_data="settings_roles")],
            [InlineKeyboardButton("👥 Лимиты игроков", callback_data="settings_players")],
            [InlineKeyboardButton("🌲 Настройки лесной мафии", callback_data="forest_settings")],
            [InlineKeyboardButton(test_mode_text, callback_data="settings_toggle_test")],
            [InlineKeyboardButton("🔄 Сбросить настройки", callback_data="settings_reset_chat")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="settings_close")]
        ]

        # Если есть активная игра, добавляем кнопку сброса статистики
        if chat_id in self.games:
            keyboard.insert(-1, [InlineKeyboardButton("📊 Сбросить статистику", callback_data="settings_reset")])

        # Формируем текст с настройками чата
        settings_text = (
            "⚙️ Настройки чата\n\n"
            f"⚡ Быстрый режим: {'ВКЛ' if chat_settings['test_mode'] else 'ВЫКЛ'}\n"
            f"👥 Игроков: {chat_settings['min_players']}-{chat_settings['max_players']}\n"
            f"⏱️ Таймеры: Ночь {chat_settings['night_duration']}с, День {chat_settings['day_duration']}с, Голосование {chat_settings['vote_duration']}с\n"
            f"🎭 Роли: Лиса умрет через {chat_settings['fox_death_threshold']} ночей, Крот раскроется через {chat_settings['mole_reveal_threshold']} ночей\n"
            f"🛡️ Защита бобра: {'ВКЛ' if chat_settings['beaver_protection'] else 'ВЫКЛ'}\n"
            f"🏁 Лимиты: {chat_settings['max_rounds']} раундов, {chat_settings['max_time']//60} мин, минимум {chat_settings['min_alive']} живых\n\n"
            "Выберите, что хотите изменить:"
        )

        await update.message.reply_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update or not update.callback_query:
            return
        query = update.callback_query
        await query.answer()
        
        # Проверяем права пользователя
        update_temp = Update(update_id=0, callback_query=query)
        has_permission, error_msg = await self.check_user_permissions(
            update_temp, context, "member"
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
            await self.toggle_quick_mode(query, context, game)
        elif query.data == "toggle_quick_mode_game":
            await self.toggle_quick_mode_from_game(query, context, game)
        elif query.data == "settings_global":
            await self.show_global_settings(query, context)
        elif query.data == "settings_players":
            await self.show_player_settings(query, context)
        elif query.data == "settings_reset_chat":
            await self.reset_chat_settings(query, context)
        elif query.data == "confirm_reset_chat":
            await self.confirm_reset_chat_settings(query, context)
        elif query.data == "settings_reset":
            if game:
                await self.reset_game_stats(query, context, game)
            else:
                await query.edit_message_text("❌ Нет активной игры для сброса статистики!")
        elif query.data == "settings_close":
            await query.edit_message_text("⚙️ Настройки закрыты")
        elif query.data == "players_min":
            await self.show_min_players_options(query, context)
        elif query.data == "players_max":
            await self.show_max_players_options(query, context)
        elif query.data == "forest_settings":
            await self.show_forest_settings(query, context)
        elif query.data == "forest_rewards_settings":
            await self.show_rewards_settings(query, context)
        elif query.data == "forest_dead_settings":
            await self.show_dead_settings(query, context)
        elif query.data == "forest_settings_back":
            await self.show_forest_settings(query, context)
        elif query.data == "set_loser_rewards_true":
            await self.set_loser_rewards_setting(query, context, True)
        elif query.data == "set_loser_rewards_false":
            await self.set_loser_rewards_setting(query, context, False)
        elif query.data == "set_dead_rewards_true":
            await self.set_dead_rewards_setting(query, context, True)
        elif query.data == "set_dead_rewards_false":
            await self.set_dead_rewards_setting(query, context, False)
        # buy_item_ обрабатывается отдельным handler'ом
        elif query.data == "back_to_main":
            await self.show_main_menu(query, context)
        elif query.data == "show_balance":
            await self.show_balance_menu(query, context)
        elif query.data == "show_shop":
            await self.show_shop_menu(query, context)
        elif query.data == "show_stats":
            await self.show_stats_menu(query, context)
        elif query.data == "close_menu":
            await query.edit_message_text("🌲 Меню закрыто")
        elif query.data == "show_inventory":
            await self.show_inventory(query, context)
        elif query.data == "show_chat_stats":
            await self.show_chat_stats(query, context)
        elif query.data == "close_profile":
            await query.edit_message_text("👤 Профиль закрыт")
        elif query.data == "back_to_profile":
            await self.back_to_profile(query, context)
        elif query.data == "join_chat":
            await self.handle_join_chat(query, context)
        elif query.data == "language_settings":
            await self.handle_language_settings(query, context)
        elif query.data == "show_profile_pm":
            await self.show_profile_pm(query, context)
        elif query.data == "show_roles_pm":
            await self.show_roles_pm(query, context)
        elif query.data == "lang_ru":
            await self.handle_language_ru(query, context)
        elif query.data == "lang_en_disabled":
            await self.handle_language_en_disabled(query, context)
        elif query.data == "show_rules_pm":
            await self.show_rules_pm(query, context)
        elif query.data == "back_to_start":
            await self.back_to_start(query, context)
        elif query.data == "repeat_role_actions":
            await self.repeat_role_actions(query, context)
        elif query.data.startswith("farewell_message_"):
            user_id = int(query.data.split("_")[2])
            await self.handle_farewell_message(query, context, user_id)
        elif query.data == "leave_forest":
            await self.handle_leave_forest(query, context)
        elif query.data.startswith("farewell_"):
            parts = query.data.split("_")
            if len(parts) >= 3:
                farewell_type = parts[1]
                user_id = int(parts[2])
                if farewell_type == "custom":
                    await self.handle_custom_farewell(query, context, user_id)
                else:
                    await self.handle_farewell_type(query, context, farewell_type, user_id)
        elif query.data.startswith("farewell_back_"):
            user_id = int(query.data.split("_")[2])
            await self.handle_farewell_back(query, context, user_id)

    async def show_timer_settings(self, query, context):
        chat_id = query.message.chat.id
        chat_settings = get_chat_settings(chat_id)
        
        keyboard = [
            [InlineKeyboardButton("🌙 Изменить длительность ночи", callback_data="timer_night")],
            [InlineKeyboardButton("☀️ Изменить длительность дня", callback_data="timer_day")],
            [InlineKeyboardButton("🗳️ Изменить длительность голосования", callback_data="timer_vote")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")]
        ]
        
        night_min = chat_settings['night_duration'] // 60
        night_sec = chat_settings['night_duration'] % 60
        day_min = chat_settings['day_duration'] // 60
        day_sec = chat_settings['day_duration'] % 60
        vote_min = chat_settings['vote_duration'] // 60
        vote_sec = chat_settings['vote_duration'] % 60
        
        night_text = f"{night_min}м {night_sec}с" if night_min > 0 else f"{night_sec}с"
        day_text = f"{day_min}м {day_sec}с" if day_min > 0 else f"{day_sec}с"
        vote_text = f"{vote_min}м {vote_sec}с" if vote_min > 0 else f"{vote_sec}с"
        
        await query.edit_message_text(
            f"⏱️ Настройки таймеров\n\nТекущие значения:\n🌙 Ночь: {night_text}\n☀️ День: {day_text}\n🗳️ Голосование: {vote_text}\n\nВыберите, что хотите изменить:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_player_settings(self, query, context):
        """Показывает настройки лимитов игроков"""
        chat_id = query.message.chat.id
        chat_settings = get_chat_settings(chat_id)
        
        keyboard = [
            [InlineKeyboardButton("👥 Минимум игроков", callback_data="players_min")],
            [InlineKeyboardButton("👥 Максимум игроков", callback_data="players_max")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")]
        ]
        
        await query.edit_message_text(
            f"👥 Настройки лимитов игроков\n\nТекущие значения:\n👥 Минимум: {chat_settings['min_players']} игроков\n👥 Максимум: {chat_settings['max_players']} игроков\n\nВыберите, что хотите изменить:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_min_players_options(self, query, context):
        """Показывает опции для изменения минимального количества игроков"""
        keyboard = [
            [InlineKeyboardButton("3 игрока", callback_data="set_min_players_3")],
            [InlineKeyboardButton("4 игрока", callback_data="set_min_players_4")],
            [InlineKeyboardButton("5 игроков", callback_data="set_min_players_5")],
            [InlineKeyboardButton("6 игроков", callback_data="set_min_players_6")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="settings_players")]
        ]
        
        await query.edit_message_text(
            "👥 Выберите минимальное количество игроков:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_max_players_options(self, query, context):
        """Показывает опции для изменения максимального количества игроков"""
        keyboard = [
            [InlineKeyboardButton("8 игроков", callback_data="set_max_players_8")],
            [InlineKeyboardButton("10 игроков", callback_data="set_max_players_10")],
            [InlineKeyboardButton("12 игроков", callback_data="set_max_players_12")],
            [InlineKeyboardButton("15 игроков", callback_data="set_max_players_15")],
            [InlineKeyboardButton("20 игроков", callback_data="set_max_players_20")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="settings_players")]
        ]
        
        await query.edit_message_text(
            "👥 Выберите максимальное количество игроков:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def reset_chat_settings(self, query, context):
        """Сбрасывает настройки чата к дефолтным"""
        chat_id = query.message.chat.id
        
        # Подтверждение сброса
        keyboard = [
            [InlineKeyboardButton("✅ Да, сбросить", callback_data="confirm_reset_chat")],
            [InlineKeyboardButton("❌ Отмена", callback_data="settings_back")]
        ]
        
        await query.edit_message_text(
            "🔄 Сброс настроек чата\n\n⚠️ Это действие сбросит ВСЕ настройки чата к дефолтным значениям:\n\n"
            "• Быстрый режим: ВКЛ\n"
            "• Игроков: 4-12\n"
            "• Таймеры: Ночь 60с, День 300с, Голосование 120с\n"
            "• Роли: Лиса умрет через 2 ночи, Крот раскроется через 3 ночи\n"
            "• Защита бобра: ВКЛ\n"
            "• Лимиты: 20 раундов, 60 мин, минимум 2 живых\n\n"
            "Вы уверены, что хотите сбросить настройки?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def confirm_reset_chat_settings(self, query, context):
        """Подтверждает сброс настроек чата"""
        chat_id = query.message.chat.id
        
        # Сбрасываем настройки в базе данных
        success = reset_chat_settings(chat_id)
        
        if success:
            await query.edit_message_text(
                "✅ Настройки чата успешно сброшены к дефолтным значениям!\n\n"
                "Все настройки восстановлены к стандартным значениям."
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при сбросе настроек чата!\n\n"
                "Попробуйте еще раз или обратитесь к администратору."
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

    async def toggle_quick_mode(self, query, context, game: Optional[Game]):
        chat_id = query.message.chat.id
        
        # Проверяем, можно ли изменить быстрый режим
        if game and game.phase != GamePhase.WAITING:
            await query.edit_message_text("❌ Нельзя изменить быстрый режим во время игры! Дождитесь окончания игры.")
            return

        # Получаем текущие настройки чата
        chat_settings = get_chat_settings(chat_id)
        current_mode = chat_settings['test_mode']
        new_mode = not current_mode
        
        # Обновляем настройки в базе данных
        success = update_chat_settings(chat_id, test_mode=new_mode)
        
        if success:
            mode_text = "ВКЛ" if new_mode else "ВЫКЛ"
            
            # Обновляем игру, если она есть
            if game:
                game.is_test_mode = new_mode
            
            await query.answer("✅ Настройка сохранена!", show_alert=True)
            # Получаем правильное минимальное количество игроков
            min_players = 3 if new_mode else 6
            
            await query.edit_message_text(
                f"✅ Быстрый режим переключен: {mode_text}\n\n"
                f"Минимум игроков: {min_players}\n\n"
                "Настройка сохранена в базе данных и будет применена для следующих игр!"
            )
        else:
            await query.answer("❌ Ошибка сохранения настройки!", show_alert=True)
            await query.edit_message_text("❌ Ошибка при сохранении настройки в базе данных!")

    async def toggle_quick_mode_from_game(self, query, context, game: Optional[Game]):
        """Переключает быстрый режим из сообщения регистрации игры"""
        logger.info(f"🔄 Вызвана функция toggle_quick_mode_from_game для чата {query.message.chat.id}")
        chat_id = query.message.chat.id
        
        # Проверяем права администратора
        is_admin = await self.is_user_admin(query, context)
        logger.info(f"🔍 Проверка прав администратора для пользователя {query.from_user.id}: {is_admin}")
        
        if not is_admin:
            await query.answer("❌ Только администраторы могут изменять настройки!", show_alert=True)
            return
        
        # Проверяем, можно ли изменить быстрый режим
        if game and game.phase != GamePhase.WAITING:
            await query.answer("❌ Нельзя изменить быстрый режим во время игры!", show_alert=True)
            return

        # Получаем текущие настройки чата
        chat_settings = get_chat_settings(chat_id)
        current_mode = chat_settings['test_mode']
        new_mode = not current_mode
        
        # Обновляем настройки в базе данных
        # Устанавливаем min_players в зависимости от режима
        min_players = 3 if new_mode else 6
        success = update_chat_settings(chat_id, test_mode=new_mode, min_players=min_players)
        
        if success:
            mode_text = "ВКЛ" if new_mode else "ВЫКЛ"
            
            # Обновляем глобальные настройки
            self.global_settings.set_test_mode(new_mode)
            
            # Обновляем игру, если она есть
            if game:
                game.is_test_mode = new_mode
            
            # Получаем правильное минимальное количество игроков
            min_players = 3 if new_mode else 6
            
            await query.answer(f"✅ Быстрый режим: {mode_text} (минимум: {min_players} игроков)", show_alert=True)
            
            # Обновляем сообщение регистрации с новыми настройками
            await self.update_registration_message(query, context, game)
        else:
            await query.answer("❌ Ошибка сохранения настройки!", show_alert=True)

    async def update_registration_message(self, query, context, game: Optional[Game]):
        """Обновляет сообщение регистрации с актуальными настройками"""
        if not game:
            return
            
        chat_id = query.message.chat.id
        max_players = getattr(game, "MAX_PLAYERS", 12)
        
        # Формируем список игроков с кликабельными никнеймами
        players_list = ""
        for player in game.players.values():
            player_tag = self.format_player_tag(player.username, player.user_id, make_clickable=True)
            players_list += f"• {player_tag}\n"
        
        # Получаем настройки чата для правильного отображения минимума игроков
        chat_settings = get_chat_settings(chat_id)
        min_players = chat_settings.get('min_players', 6)
        
        # Создаем сообщение регистрации
        message = (
            f"🌲 <b>Лес и Волки - Регистрация</b> 🌲\n\n"
            f"👥 Игроков: {len(game.players)}/{max_players}\n"
            f"📋 Минимум для старта: {min_players}\n\n"
            f"📝 Участники:\n{players_list}"
        )
        
        if game.can_start_game():
            message += "\n✅ Можно начинать игру!"
        else:
            message += f"\n⏳ Нужно ещё {max(0, min_players - len(game.players))} игроков"
        
        # Создаем клавиатуру с обновленными настройками
        keyboard = []
        
        # Кнопка "Присоединиться" - всегда первая
        keyboard.append([InlineKeyboardButton("✅ Присоединиться", callback_data="join_game")])
        
        # Кнопка "Выйти из регистрации"
        keyboard.append([InlineKeyboardButton("❌ Выйти из регистрации", callback_data="leave_registration")])
        
        # Кнопка "Посмотреть свою роль" (повторяет сообщения с кнопками действий)
        if game.phase != GamePhase.WAITING:
            keyboard.append([InlineKeyboardButton("👁️ Посмотреть свою роль", callback_data="repeat_role_actions")])
        
        # Кнопка "Магазин"
        keyboard.append([InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")])
        
        # Кнопка "Быстрый режим" (только для админов)
        if await self.is_user_admin(query, context):
            quick_mode_text = "⚡ Быстрый режим: ВКЛ" if self.global_settings.is_test_mode() else "⚡ Быстрый режим: ВЫКЛ"
            keyboard.append([InlineKeyboardButton(quick_mode_text, callback_data="toggle_quick_mode_game")])
        
        # Кнопка "Начать игру" (если можно)
        if game.can_start_game():
            keyboard.append([InlineKeyboardButton("🚀 Начать игру", callback_data="start_game")])
        
        # Кнопка "Отменить игру" (только для админов)
        if await self.is_user_admin(query, context):
            keyboard.append([InlineKeyboardButton("🛑 Отменить игру", callback_data="cancel_game")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Обновляем сообщение
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

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
        update_temp = Update(update_id=0, callback_query=query)
        has_permission, error_msg = await self.check_user_permissions(
            update_temp, context, "member"
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
        update_temp = Update(update_id=0, callback_query=query)
        has_permission, error_msg = await self.check_user_permissions(
            update_temp, context, "member"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return
        
        chat_id = query.message.chat.id
        user_id = query.from_user.id

        # Обрабатываем конкретные настройки ролей
        if query.data.startswith("role_wolves_"):
            percentage = int(query.data.split("_")[2])
            current_distribution = self.global_settings.get("role_distribution", {})
            current_distribution["wolves"] = percentage / 100.0
            self.global_settings.set("role_distribution", current_distribution)
            await query.edit_message_text(f"🐺 Доля волков изменена на {percentage}%!\n\n✅ Настройка сохранена и будет применена для следующих игр.")
        elif query.data.startswith("role_fox_"):
            percentage = int(query.data.split("_")[2])
            current_distribution = self.global_settings.get("role_distribution", {})
            current_distribution["fox"] = percentage / 100.0
            self.global_settings.set("role_distribution", current_distribution)
            await query.edit_message_text(f"🦊 Доля лисы изменена на {percentage}%!\n\n✅ Настройка сохранена и будет применена для следующих игр.")
        elif query.data.startswith("role_mole_"):
            percentage = int(query.data.split("_")[2])
            current_distribution = self.global_settings.get("role_distribution", {})
            current_distribution["mole"] = percentage / 100.0
            self.global_settings.set("role_distribution", current_distribution)
            await query.edit_message_text(f"🦫 Доля крота изменена на {percentage}%!\n\n✅ Настройка сохранена и будет применена для следующих игр.")
        elif query.data.startswith("role_beaver_"):
            percentage = int(query.data.split("_")[2])
            current_distribution = self.global_settings.get("role_distribution", {})
            current_distribution["beaver"] = percentage / 100.0
            self.global_settings.set("role_distribution", current_distribution)
            await query.edit_message_text(f"🦦 Доля бобра изменена на {percentage}%!\n\n✅ Настройка сохранена и будет применена для следующих игр.")
        else:
            # Показываем настройки ролей
            await self.show_role_settings(query, context)

    async def handle_settings_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возвращает к главному меню настроек"""
        query = update.callback_query
        await query.answer()
        
        # Проверяем права пользователя
        update_temp = Update(update_id=0, callback_query=query)
        has_permission, error_msg = await self.check_user_permissions(
            update_temp, context, "member"
        )
        if not has_permission:
            await query.answer(error_msg, show_alert=True)
            return
        
        chat_id = query.message.chat.id
        user_id = query.from_user.id

        # Получаем настройки чата из базы данных
        chat_settings = get_chat_settings(chat_id)
        
        test_mode_text = "⚡ Быстрый режим: ВКЛ" if chat_settings['test_mode'] else "⚡ Быстрый режим: ВЫКЛ"

        keyboard = [
            [InlineKeyboardButton("⏱️ Изменить таймеры", callback_data="settings_timers")],
            [InlineKeyboardButton("🎭 Изменить распределение ролей", callback_data="settings_roles")],
            [InlineKeyboardButton("👥 Лимиты игроков", callback_data="settings_players")],
            [InlineKeyboardButton("🌲 Настройки лесной мафии", callback_data="forest_settings")],
            [InlineKeyboardButton(test_mode_text, callback_data="settings_toggle_test")],
            [InlineKeyboardButton("🔄 Сбросить настройки", callback_data="settings_reset_chat")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="settings_close")]
        ]

        # Если есть активная игра, добавляем кнопку сброса статистики
        if chat_id in self.games:
            keyboard.insert(-1, [InlineKeyboardButton("📊 Сбросить статистику", callback_data="settings_reset")])

        # Формируем текст с настройками чата
        settings_text = (
            "⚙️ Настройки чата\n\n"
            f"⚡ Быстрый режим: {'ВКЛ' if chat_settings['test_mode'] else 'ВЫКЛ'}\n"
            f"👥 Игроков: {chat_settings['min_players']}-{chat_settings['max_players']}\n"
            f"⏱️ Таймеры: Ночь {chat_settings['night_duration']}с, День {chat_settings['day_duration']}с, Голосование {chat_settings['vote_duration']}с\n"
            f"🎭 Роли: Лиса умрет через {chat_settings['fox_death_threshold']} ночей, Крот раскроется через {chat_settings['mole_reveal_threshold']} ночей\n"
            f"🛡️ Защита бобра: {'ВКЛ' if chat_settings['beaver_protection'] else 'ВЫКЛ'}\n"
            f"🏁 Лимиты: {chat_settings['max_rounds']} раундов, {chat_settings['max_time']//60} мин, минимум {chat_settings['min_alive']} живых\n\n"
            "Выберите, что хотите изменить:"
        )

        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def show_night_duration_options(self, query, context):
        """Показывает опции для изменения длительности ночи"""
        chat_id = query.message.chat.id
        chat_settings = get_chat_settings(chat_id)
        current_duration = chat_settings['night_duration']
        
        options = [30, 45, 60, 90, 120]
        keyboard = []
        
        for duration in options:
            button_text = f"{duration} секунд"
            if duration == current_duration:
                button_text += " ✅"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"set_night_{duration}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад к таймерам", callback_data="timer_back")])
        
        await query.edit_message_text(
            "🌙 Настройка длительности ночи\n\nВыберите новую длительность ночной фазы:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_day_duration_options(self, query, context):
        """Показывает опции для изменения длительности дня"""
        chat_id = query.message.chat.id
        chat_settings = get_chat_settings(chat_id)
        current_duration = chat_settings['day_duration']
        
        options = [120, 180, 300, 420, 600]  # 2, 3, 5, 7, 10 минут
        keyboard = []
        
        for duration in options:
            minutes = duration // 60
            button_text = f"{minutes} минут"
            if duration == current_duration:
                button_text += " ✅"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"set_day_{duration}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад к таймерам", callback_data="timer_back")])
        
        await query.edit_message_text(
            "☀️ Настройка длительности дня\n\nВыберите новую длительность дневной фазы:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_vote_duration_options(self, query, context):
        """Показывает опции для изменения длительности голосования"""
        chat_id = query.message.chat.id
        chat_settings = get_chat_settings(chat_id)
        current_duration = chat_settings['vote_duration']
        
        options = [60, 90, 120, 180, 300]  # 1, 1.5, 2, 3, 5 минут
        keyboard = []
        
        for duration in options:
            if duration == 60:
                button_text = "1 минута"
            elif duration == 90:
                button_text = "1.5 минуты"
            else:
                minutes = duration // 60
                button_text = f"{minutes} минуты"
            
            if duration == current_duration:
                button_text += " ✅"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"set_vote_{duration}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад к таймерам", callback_data="timer_back")])
        
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
        update_temp = Update(update_id=0, callback_query=query)
        has_permission, error_msg = await self.check_user_permissions(
            update_temp, context, "member"
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
            # Сохраняем настройку в базу данных
            success = update_chat_settings(chat_id, night_duration=seconds)
            if success:
                await query.answer("✅ Настройка сохранена!", show_alert=True)
                # Обновляем кнопки с галочкой
                await self.show_night_duration_options(query, context)
            else:
                await query.answer("❌ Ошибка сохранения настройки!", show_alert=True)
        elif query.data.startswith("set_day_"):
            seconds = int(query.data.split("_")[2])
            # Сохраняем настройку в базу данных
            success = update_chat_settings(chat_id, day_duration=seconds)
            if success:
                await query.answer("✅ Настройка сохранена!", show_alert=True)
                # Обновляем кнопки с галочкой
                await self.show_day_duration_options(query, context)
            else:
                await query.answer("❌ Ошибка сохранения настройки!", show_alert=True)
        elif query.data.startswith("set_vote_"):
            seconds = int(query.data.split("_")[2])
            # Сохраняем настройку в базу данных
            success = update_chat_settings(chat_id, vote_duration=seconds)
            if success:
                await query.answer("✅ Настройка сохранена!", show_alert=True)
                # Обновляем кнопки с галочкой
                await self.show_vote_duration_options(query, context)
            else:
                await query.answer("❌ Ошибка сохранения настройки!", show_alert=True)
        elif query.data.startswith("set_min_players_"):
            players = int(query.data.split("_")[3])
            # Сохраняем настройку в базу данных
            update_chat_settings(chat_id, min_players=players)
            await query.edit_message_text(f"👥 Минимальное количество игроков изменено на {players}!\n\n✅ Новая настройка сохранена и будет применена для следующих игр.")
        elif query.data.startswith("set_max_players_"):
            players = int(query.data.split("_")[3])
            # Сохраняем настройку в базу данных
            update_chat_settings(chat_id, max_players=players)
            await query.edit_message_text(f"👥 Максимальное количество игроков изменено на {players}!\n\n✅ Новая настройка сохранена и будет применена для следующих игр.")

    # ---------------- night actions processing ----------------
    async def send_night_actions_to_players(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        chat_id = game.chat_id
        if chat_id in self.night_interfaces:
            await self.night_interfaces[chat_id].send_role_reminders(context)

    async def send_squirrel_message(self, context: ContextTypes.DEFAULT_TYPE, player: Player):
        """Отправляет сообщение белочки изгнанному игроку (только при голосовании)"""
        try:
            # Получаем русское название роли
            from role_translator import get_role_name_russian
            role_name = get_role_name_russian(player.role)
            
            # Формируем имя игрока
            player_name = player.username or player.first_name or "Игрок"
            
            squirrel_message = (
                f"🍂 Осенний лист упал 🍂\n\n"
                f"🐿️ Маленькая белочка с печальными глазками подошла к тебе, {player_name}...\n\n"
                f"💭 \"Лес больше не нуждается в твоих услугах, {player_name},\" - говорит она.\n"
                f"🌅 \"Солнце заходит для тебя в этом мире.\"\n\n"
                f"🎭 Твоя роль: {role_name}\n"
                f"🚫 Твои действия в игре завершены.\n"
                f"🔇 Молчание - твоя новая обязанность.\n\n"
                f"🌌 Белочка бережно забирает твою душу, чтобы отнести её в звёздный лес...\n\n"
                f"⭐️ До свидания, {player_name} ⭐️"
            )
            
            # Создаем клавиатуру с кнопкой прощального сообщения
            keyboard = [
                [InlineKeyboardButton("💬 Сказать прощальное слово", callback_data=f"farewell_message_{player.user_id}")],
                [InlineKeyboardButton("🌲 Покинуть лес", callback_data="leave_forest")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение в личку
            await context.bot.send_message(
                chat_id=player.user_id,
                text=squirrel_message,
                reply_markup=reply_markup
            )
            
            logger.info(f"Отправлено сообщение белочки игроку {player_name} ({player.user_id})")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения белочки игроку {player.user_id}: {e}")

    async def send_wolf_victim_pm(self, context: ContextTypes.DEFAULT_TYPE, victim_info: Dict):
        """Отправляет ЛС игроку, которого съел волк"""
        try:
            user_id = victim_info['user_id']
            username = victim_info['username']
            role_name = victim_info['role_name']
            
            # Формируем сообщение
            message = (
                f"Не послушался, ты @{username} взрослых да других зверей, "
                f"открыл дверь злому волку. И остались от тебя ножки да орешков немножко. "
                f"покойся с миром!\n\n"
                f"🎭 Твоя роль: {role_name}\n"
                f"🚫 Твои действия в игре завершены.\n"
                f"🔇 Молчание - твоя новая обязанность."
            )
            
            # Создаем клавиатуру с кнопкой прощального сообщения
            keyboard = [
                [InlineKeyboardButton("💬 Сказать прощальное слово", callback_data=f"farewell_message_{user_id}")],
                [InlineKeyboardButton("🌲 Покинуть лес", callback_data="leave_forest")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем ЛС
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
            logger.info(f"✅ Отправлено ЛС жертве волка {username} (ID: {user_id})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке ЛС жертве волка: {e}")

    async def send_mole_check_pm(self, context: ContextTypes.DEFAULT_TYPE, check_info: Dict):
        """Отправляет ЛС кроту с результатом проверки"""
        try:
            mole_id = check_info['mole_id']
            mole_username = check_info['mole_username']
            target_username = check_info['target_username']
            target_role = check_info['target_role']
            check_result = check_info['check_result']
            
            # Получаем русское название роли
            from role_translator import get_role_name_russian
            role_name = get_role_name_russian(target_role)
            
            # Создаем специальное сообщение для крота с правильными обращениями
            pm_message = self._create_mole_pm_message(target_role, target_username, check_result)
            
            # Формируем сообщение для ЛС
            message = (
                f"🦫 <b>Результат твоей проверки:</b>\n\n"
                f"👤 Проверяемый: @{target_username}\n"
                f"🎭 Роль: {role_name}\n\n"
                f"{pm_message}"
            )
            
            # Отправляем ЛС
            await context.bot.send_message(
                chat_id=mole_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"✅ Отправлено ЛС кроту {mole_username} (ID: {mole_id}) с результатом проверки")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке ЛС кроту: {e}")

    def _create_mole_pm_message(self, target_role, target_username: str, check_result: str) -> str:
        """Создает сообщение для крота с правильными обращениями"""
        from game_logic import Role
        
        # Получаем правильные склонения для родительного падежа
        role_genitive = {
            Role.WOLF: "волка",
            Role.FOX: "лисы", 
            Role.HARE: "зайца",
            Role.MOLE: "крота",
            Role.BEAVER: "бобра"
        }
        role_genitive_name = role_genitive.get(target_role, "неизвестного")
        
        # Создаем сообщения специально для крота
        if target_role == Role.WOLF:
            if "отправился на охоту" in check_result:
                return f"🦡 Крот заглянул в норку, но она была пуста. Похоже, @{target_username} отправился на охоту..."
            else:
                return f"🦡 Крот посмотрел из-под тишка и заметил, что это @{target_username} - Волк!"
        
        elif target_role == Role.FOX:
            if "отправилась на дело" in check_result:
                return f"🦡 Крот заглянул в норку, но она была пуста. Похоже, @{target_username} отправилась на дело..."
            else:
                return f"🦡 Крот посмотрел из-под тишка и заметил, что это @{target_username} - Лиса!"
        
        elif target_role == Role.HARE:
            if "отправился по делам" in check_result:
                return f"🦡 Крот заглянул в норку, но она была пуста. Похоже, @{target_username} отправился по делам..."
            else:
                return f"🦡 Крот пришёл к норке @{target_username}, он открыл дверь. Всё спокойно, он мирный."
        
        elif target_role == Role.BEAVER:
            if "отправился помогать" in check_result:
                return f"🦡 Крот заглянул в норку, но она была пуста. Похоже, @{target_username} отправился помогать..."
            else:
                return f"🦡 Крот пришёл к норке @{target_username}, он открыл дверь. Всё спокойно, он мирный."
        
        elif target_role == Role.MOLE:
            if "отправился на разведку" in check_result:
                return f"🦡 Крот заглянул в норку, но она была пуста. Похоже, @{target_username} отправился на разведку..."
            else:
                return f"🦡 Крот посмотрел из-под тишка и заметил, что это @{target_username} - Крот!"
        
        else:
            return f"🦡 Крот заглянул в норку @{target_username}, но не смог понять, кто здесь живёт..."

    async def process_night_phase(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        chat_id = game.chat_id
        if chat_id in self.night_actions:
            night_actions = self.night_actions[chat_id]
            night_interface = self.night_interfaces[chat_id]
            results = night_actions.process_all_actions()
            await night_interface.send_night_results(context, results)
            night_actions.clear_actions()
            
            # Отправляем ЛС жертве волка, если есть
            if game.last_wolf_victim:
                await self.send_wolf_victim_pm(context, game.last_wolf_victim)
                game.last_wolf_victim = None  # Очищаем после отправки
            
            # Отправляем ЛС кроту с результатом проверки, если есть
            if game.last_mole_check:
                await self.send_mole_check_pm(context, game.last_mole_check)
                game.last_mole_check = None  # Очищаем после отправки
            
        # Проверяем условия автоматического завершения игры после ночных действий
        winner = game.check_game_end()
        if winner:
            await self.end_game_winner(context, game, winner)
            return


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
            # Вызываем process_voting_results напрямую (он сам отправит объединенное сообщение)
            await self.process_voting_results(context, game)
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
        
        # Формируем теги участников
        player_tags = []
        for player in game.players.values():
            if player.username:
                player_tags.append(f"@{player.username}")
            else:
                player_tags.append(f"[{player.first_name or 'Игрок'}](tg://user?id={player.user_id})")
        
        # Отправляем сообщение о начале игры в сказочном стиле
        start_message = (
            "🌲 <b>Лес просыпается...</b> 🌲\n\n"
            "🦌 Все лесные зверушки собрались на поляне для игры в Лес и Волки!\n"
            "🍃 Шелест листьев, пение птиц, и тайные заговоры в тени деревьев...\n\n"
            f"🐾 <b>Участники лесного совета:</b> {', '.join(player_tags)}\n\n"
            "🌙 Наступает первая ночь в нашем волшебном лесу...\n"
            "🎭 Роли уже распределены среди зверушек! Проверьте личные сообщения с ботом.\n"
            "🌅 Скоро наступит рассвет, когда хищники выйдут на охоту..."
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=start_message,
            parse_mode='HTML',
            message_thread_id=game.thread_id
        )
        
        # Запускаем первую ночь (роли будут отправлены в start_night_phase)
        await self.start_night_phase(context, game)
        
        # Автосохранение состояния игры
        self.save_game_state(chat_id)

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
            f"🌙 Напоминание о вашей роли:\n\n"
            f"🎭{role_info['name']}\n"
            f"📝 {role_info['description']}"
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
            BotCommand("balance", "💰 Показать баланс"),
            BotCommand("shop", "🛍️ Магазин товаров"),
            BotCommand("profile", "👤 Профиль игрока"),
            BotCommand("global_stats", "🌍 Общая статистика"),
            BotCommand("nickname", "🎭 Установить никнейм"),
            BotCommand("reset_nickname", "🗑️ Сбросить никнейм"),
            
            # 🎯 Команды для управления игрой
            BotCommand("start_game", "🚀 Начать игру"),
            BotCommand("end_game", "🏁 Завершить игру"),
            BotCommand("end", "🏁 Завершить игру (краткая)"),
            BotCommand("leave", "👋 Покинуть игру"),
            
            # ⚙️ Административные команды
            BotCommand("settings", "⚙️ Настройки игры"),
            BotCommand("quick_mode", "⚡ Быстрый режим"),
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
        application.add_handler(CommandHandler("inventory", self.inventory_command))
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
        application.add_handler(CommandHandler("quick_mode", self.handle_quick_mode_command)) # Обработчик команды quick_mode
        application.add_handler(CommandHandler("setup_channel", self.setup_channel)) # Обработчик команды setup_channel
        application.add_handler(CommandHandler("remove_channel", self.remove_channel)) # Обработчик команды remove_channel
        application.add_handler(CommandHandler("save_state", self.save_state_command)) # Команда для принудительного сохранения
        application.add_handler(CommandHandler("auto_save_status", self.auto_save_status_command)) # Статус автоматического сохранения
        
        # Новые команды для работы с базой данных
        application.add_handler(CommandHandler("balance", self.balance_command)) # Команда /balance
        application.add_handler(CommandHandler("shop", self.shop_command)) # Команда /shop
        application.add_handler(CommandHandler("profile", self.profile_command)) # Команда /profile
        application.add_handler(CommandHandler("global_stats", self.global_stats_command)) # Команда /global_stats
        application.add_handler(CommandHandler("nickname", self.nickname_command)) # Команда /nickname
        application.add_handler(CommandHandler("reset_nickname", self.reset_nickname_command)) # Команда /reset_nickname
        application.add_handler(CommandHandler("game", self.game_command)) # Команда /game
        application.add_handler(CommandHandler("cancel", self.cancel_command)) # Команда /cancel
        

        # Обработчик присоединения бота к чату
        application.add_handler(ChatMemberHandler(self.handle_bot_join, ChatMemberHandler.MY_CHAT_MEMBER))
        
        # Обработчик личных сообщений (для регистрации пользователей)
        application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, self.handle_private_message))

        # callbacks
        application.add_handler(CallbackQueryHandler(self.handle_vote, pattern=r"^vote_"))
        application.add_handler(CallbackQueryHandler(self.handle_night_action, pattern=r"^night_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^settings_"))
        application.add_handler(CallbackQueryHandler(self.handle_welcome_buttons, pattern=r"^welcome_"))
        application.add_handler(CallbackQueryHandler(self.handle_day_actions, pattern=r"^day_"))
        
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
        application.add_handler(CallbackQueryHandler(self.handle_view_my_role, pattern=r"^night_view_role_"))
        
        # shop and profile handlers
        application.add_handler(CallbackQueryHandler(self.handle_buy_item_callback, pattern=r"^buy_item_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^show_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^back_to_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^close_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^farewell_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^leave_forest"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^join_chat"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^language_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^show_profile_pm"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^show_roles_pm"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^lang_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^show_rules_pm"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^back_to_start"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^repeat_role_actions"))

        # Установка команд после старта бота
        async def post_init(application):
            await self.setup_bot_commands(application)

        application.post_init = post_init

        # Запуск бота (blocking call)
        try:
            application.run_polling()
        except KeyboardInterrupt:
            logger.info("⏹️ Остановка бота...")
        except Exception as e:
            if "Conflict" in str(e):
                logger.error("❌ Ошибка Conflict: Запущено несколько экземпляров бота!")
                logger.error("❌ Убедитесь, что только один экземпляр бота работает одновременно")
                logger.error(f"❌ Детали ошибки: {e}")
            else:
                logger.error(f"❌ Неожиданная ошибка: {e}")
                raise
        finally:
            # Закрываем подключение к базе данных
            if self.db:
                close_db()
                logger.info("✅ Подключение к базе данных закрыто")

    async def handle_private_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает личные сообщения боту"""
        if not update.message:
            return
            
        # Проверяем, что это личное сообщение (не группа)
        if update.effective_chat.type != 'private':
            return
            
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or "Unknown"
        
        # Проверяем, ожидает ли пользователь ввода кастомного прощального сообщения
        if f'waiting_custom_farewell_{user_id}' in context.user_data:
            await self.handle_custom_farewell_text(update, context, user_id, username)
            return
        
        # Создаем пользователя в БД с начальным балансом 100 орешков
        try:
            if self.db:
                # Проверяем, есть ли уже пользователь в БД
                existing_user = get_user_by_telegram_id(user_id)
                if not existing_user:
                    # Создаем пользователя с балансом 100 орешков
                    create_user(user_id, username)
                    logger.info(f"✅ Новый пользователь {user_id} ({username}) создан в БД с балансом 100 орешков")
                    
                    # Отправляем приветственное сообщение
                    welcome_text = (
                        f"👋 Привет, {username}!\n\n"
                        f"🌰 Добро пожаловать в Лесную Мафию!\n"
                        f"💰 Ваш начальный баланс: 100 орешков\n\n"
                        f"🎮 Для игры присоединяйтесь к группе и используйте команду /join\n"
                        f"📊 Проверить баланс: /balance\n"
                        f"📖 Правила игры: /rules\n"
                        f"❓ Помощь: /help"
                    )
                    await update.message.reply_text(welcome_text)
                else:
                    # Пользователь уже существует, просто отвечаем
                    await update.message.reply_text(
                        f"👋 Привет, {username}!\n\n"
                        f"🎮 Для игры присоединяйтесь к группе и используйте команду /join\n"
                        f"📊 Проверить баланс: /balance\n"
                        f"📖 Правила игры: /rules\n"
                        f"❓ Помощь: /help"
                    )
        except Exception as e:
            logger.error(f"❌ Ошибка обработки личного сообщения: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

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
            "🌲 <b>Добро пожаловать в 'Лес и Волки'!</b> 🌲\n\n"
            "🎭 <b>Ролевая игра в стиле 'Мафия' с лесными зверушками</b>\n\n"
            "🐺 <b>Хищники:</b> Волки + Лиса\n"
            "🐰 <b>Травоядные:</b> Зайцы + Крот + Бобёр\n\n"
            "🌙 <b>Как играть:</b>\n"
            "• Ночью хищники охотятся, травоядные защищаются\n"
            "• Днем все обсуждают и голосуют за изгнание\n"
            "• Цель: уничтожить всех противников\n\n"
            f"👥 Минимум: {self.global_settings.get_min_players()} игроков\n"
            f"{'⚡ БЫСТРЫЙ РЕЖИМ' if self.global_settings.is_test_mode() else ''}\n\n"
            "🚀 <b>Нажмите кнопку ниже, чтобы начать игру!</b>"
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
                parse_mode='HTML'
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

    async def handle_quick_mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /quick_mode для включения/выключения быстрого режима."""
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
            await update.message.reply_text("❌ Управление быстрым режимом доступно только в группах!")
            return

        # Проверяем права администратора
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут изменять быстрый режим!")
            return

        game = self.games.get(chat_id)  # Игра может отсутствовать

        # Проверяем, можно ли изменить быстрый режим
        if game and game.phase != GamePhase.WAITING:
            await update.message.reply_text("❌ Нельзя изменить быстрый режим во время игры! Дождитесь окончания игры.")
            return

        self.global_settings.toggle_test_mode() # Используем метод для переключения
        mode_text = "включен" if self.global_settings.is_test_mode() else "выключен"
        min_players = self.global_settings.get_min_players()

        result_text = (
            f"⚡ Быстрый режим {mode_text}!\n\n"
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

    async def show_forest_settings(self, query, context):
        """Показывает настройки лесной мафии"""
        from forest_mafia_settings import ForestWolvesSettings
        forest_settings = ForestWolvesSettings(self.global_settings)
        
        keyboard = forest_settings.get_forest_wolves_settings_keyboard()
        summary = forest_settings.get_settings_summary()
        
        await query.edit_message_text(
            summary,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    async def show_rewards_settings(self, query, context):
        """Показывает настройки наград"""
        from forest_mafia_settings import ForestWolvesSettings
        forest_settings = ForestWolvesSettings(self.global_settings)
        
        keyboard = forest_settings.get_rewards_settings_keyboard()
        
        current_enabled = self.global_settings.get("forest_wolves_features", {}).get("loser_rewards_enabled", True)
        status_text = "ВКЛ" if current_enabled else "ВЫКЛ"
        
        await query.edit_message_text(
            f"🏆 <b>Настройки наград</b>\n\n"
            f"🌰 Награды проигравшим игрокам: {status_text}\n\n"
            f"Выберите действие:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    async def set_loser_rewards_setting(self, query, context, enabled: bool):
        """Устанавливает настройку награждения проигравших"""
        from forest_mafia_settings import ForestWolvesSettings
        forest_settings = ForestWolvesSettings(self.global_settings)
        
        success = forest_settings.apply_setting("loser_rewards", enabled)
        
        if success:
            status_text = "включены" if enabled else "отключены"
            await query.edit_message_text(
                f"🏆 Награды проигравшим {status_text}!\n\n"
                f"✅ Настройка сохранена и будет применена для следующих игр.",
                reply_markup=forest_settings.get_forest_settings_back_keyboard()
            )
        else:
            await query.answer("❌ Ошибка при сохранении настройки!", show_alert=True)

    async def show_dead_settings(self, query, context):
        """Показывает настройки умерших игроков"""
        try:
            forest_settings = ForestWolvesSettings()
            keyboard = forest_settings.get_dead_settings_keyboard()
            
            settings_text = (
                "💀 <b>Настройки умерших игроков</b> 💀\n\n"
                "🌲 Здесь можно настроить, получают ли умершие игроки орешки за участие в игре.\n\n"
                "💡 <b>Награды умершим</b> - получают ли орешки игроки, которые умерли во время игры."
            )
            
            await query.edit_message_text(settings_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа настроек умерших: {e}")
            await query.answer("❌ Ошибка при загрузке настроек!", show_alert=True)

    async def set_dead_rewards_setting(self, query, context, value: bool):
        """Устанавливает настройку наград умершим игрокам"""
        try:
            chat_id = query.message.chat.id
            
            # Обновляем настройку в базе данных
            success = update_chat_settings(chat_id, dead_rewards_enabled=value)
            
            if success:
                # Обновляем настройку в глобальных настройках
                forest_settings = ForestWolvesSettings()
                forest_settings.global_settings.update_forest_feature("dead_rewards_enabled", value)
                
                status_text = "включены" if value else "отключены"
                await query.edit_message_text(
                    f"💀 Награды умершим {status_text}!\n\n"
                    f"✅ Настройка сохранена и будет применена для следующих игр.",
                    reply_markup=forest_settings.get_forest_settings_back_keyboard()
                )
            else:
                await query.answer("❌ Ошибка при сохранении настройки!", show_alert=True)
                
        except Exception as e:
            logger.error(f"❌ Ошибка установки настройки умерших: {e}")
            await query.answer("❌ Ошибка при сохранении настройки!", show_alert=True)

    async def handle_buy_item_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает callback покупки товара"""
        query = update.callback_query
        if not query:
            return
        
        try:
            # Извлекаем ID товара из callback_data
            item_id = int(query.data.split("_")[2])
            await self.handle_buy_item(query, context, item_id)
        except Exception as e:
            logger.error(f"❌ Ошибка обработки callback покупки: {e}")
            await query.answer("❌ Ошибка покупки!", show_alert=True)

    async def update_shop_message(self, query, context):
        """Обновляет существующее сообщение магазина"""
        try:
            user_id = query.from_user.id
            username = query.from_user.username or query.from_user.first_name or "Unknown"
            
            # Получаем баланс пользователя
            from database_balance_manager import balance_manager
            user_balance = balance_manager.get_user_balance(user_id)
            
            # Получаем товары из магазина
            from database_psycopg2 import get_shop_items
            shop_items = get_shop_items()
            
            if not shop_items:
                await query.edit_message_text("🛍️ <b>Магазин пуст</b>\n\nТовары появятся позже!", parse_mode='HTML')
                return
            
            # Создаем клавиатуру для магазина
            keyboard = []
            
            # Добавляем кнопки для каждого товара
            for item in shop_items:
                price = int(item['price'])
                button_text = f"{item['item_name']} - {price}🌰"
                callback_data = f"buy_item_{item['id']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            # Добавляем кнопку "Назад"
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Формируем сообщение с информацией о пользователе и товарах
            shop_text = f"🌲 <b>Лесной магазин</b>\n\n"
            # Получаем кликабельное имя с учетом никнейма
            clickable_name = self.format_player_tag(username, user_id, make_clickable=True)
            shop_text += f"👤 <b>{clickable_name}:</b>\n"
            shop_text += f"🌰 Орешки: {user_balance}\n\n"
            shop_text += "🛍️ <b>Что будем покупать?</b>\n\n"
            
            # Добавляем описание товаров
            for item in shop_items:
                shop_text += f"<b>{item['item_name']}</b>\n"
                shop_text += f"📝 {item['description']}\n"
                shop_text += f"💰 {int(item['price'])} орешков\n\n"
            
            await query.edit_message_text(shop_text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления магазина: {e}")
            await query.answer("❌ Ошибка обновления магазина!", show_alert=True)

    async def handle_buy_item(self, query, context, item_id: int):
        """Обрабатывает покупку товара"""
        try:
            user_id = query.from_user.id
            username = query.from_user.username or query.from_user.first_name or "Unknown"
            
            # Получаем информацию о товаре
            from database_psycopg2 import get_shop_items
            shop_items = get_shop_items()
            item = None
            for shop_item in shop_items:
                if shop_item['id'] == item_id:
                    item = shop_item
                    break
            
            if not item:
                await query.answer("❌ Товар не найден!", show_alert=True)
                return
            
            # Используем новую атомарную систему покупок
            from database_psycopg2 import buy_item
            # Конвертируем DECIMAL в int (цена может быть float из БД)
            item_price = int(float(item['price']))
            result = buy_item(user_id, item['item_name'], item_price)
            
            if result['success']:
                # Формируем сообщение об успешной покупке
                success_message = (
                    f"✅ Ты купил: {result['item_name']}\n"
                    f"🌰 Баланс: {result['balance']}\n"
                    f"🎒 Инвентарь обновлён!"
                )
                
                await query.answer(success_message, show_alert=True)
                logger.info(f"✅ Пользователь {username} (ID: {user_id}) купил {result['item_name']} за {item_price} орешков. Новый баланс: {result['balance']}")
                
                # Обновляем сообщение магазина
                await self.update_shop_message(query, context)
            else:
                # Показываем краткую ошибку (Telegram ограничение на длину)
                error_message = f"❌ {result['error']}"
                if 'balance' in result:
                    error_message += f"\n🌰 Баланс: {result['balance']}"
                
                await query.answer(error_message, show_alert=True)
                logger.warning(f"❌ Покупка не удалась для пользователя {username} (ID: {user_id}): {result['error']}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при покупке товара: {e}")
            error_message = f"❌ Ошибка покупки!\n💡 Попробуйте позже"
            await query.answer(error_message, show_alert=True)

    async def show_main_menu(self, query, context):
        """Показывает главное меню"""
        try:
            keyboard = [
                [InlineKeyboardButton("🌰 Баланс", callback_data="show_balance")],
                [InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")],
                [InlineKeyboardButton("📊 Статистика", callback_data="show_stats")],
                [InlineKeyboardButton("❌ Закрыть", callback_data="close_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🌲 <b>Главное меню Лес и волки</b>\n\nВыберите действие:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"❌ Ошибка показа главного меню: {e}")

    async def show_balance_menu(self, query, context):
        """Показывает меню баланса"""
        try:
            user_id = query.from_user.id
            username = query.from_user.username or query.from_user.first_name or "Unknown"
            
            # Получаем баланс пользователя
            from database_balance_manager import balance_manager
            user_balance = balance_manager.get_user_balance(user_id)
            
            keyboard = [
                [InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Получаем кликабельное имя с учетом никнейма
            clickable_name = self.format_player_tag(username, user_id, make_clickable=True)
            
            balance_text = f"🌲 <b>Баланс Лес и волки</b>\n\n"
            balance_text += f"👤 <b>{clickable_name}:</b>\n"
            balance_text += f"🌰 Орешки: {user_balance}\n\n"
            balance_text += "💡 Орешки можно заработать, играя в Лес и волки!"
            
            await query.edit_message_text(balance_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e:
            logger.error(f"❌ Ошибка показа баланса: {e}")

    async def show_shop_menu(self, query, context):
        """Показывает меню магазина"""
        try:
            user_id = query.from_user.id
            username = query.from_user.username or query.from_user.first_name or "Unknown"
            
            # Получаем баланс пользователя
            from database_balance_manager import balance_manager
            user_balance = balance_manager.get_user_balance(user_id)
            
            # Получаем товары из магазина
            shop_items = get_shop_items()
            
            if not shop_items:
                await query.edit_message_text("🛍️ <b>Магазин пуст</b>\n\nТовары появятся позже!", parse_mode='HTML')
                return
            
            # Создаем клавиатуру для магазина
            keyboard = []
            
            # Добавляем кнопки для каждого товара
            for item in shop_items:
                price = int(item['price'])
                button_text = f"{item['item_name']} - {price}🌰"
                callback_data = f"buy_item_{item['id']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            # Добавляем кнопку "Назад"
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Формируем сообщение с информацией о пользователе и товарах
            shop_text = f"🌲 <b>Лесной магазин</b>\n\n"
            # Получаем кликабельное имя с учетом никнейма
            clickable_name = self.format_player_tag(username, user_id, make_clickable=True)
            shop_text += f"👤 <b>{clickable_name}:</b>\n"
            shop_text += f"🌰 Орешки: {user_balance}\n\n"
            shop_text += "🛍️ <b>Что будем покупать?</b>\n\n"
            
            # Добавляем описание товаров
            for item in shop_items:
                shop_text += f"<b>{item['item_name']}</b>\n"
                shop_text += f"📝 {item['description']}\n"
                shop_text += f"💰 {int(item['price'])} орешков\n\n"
            
            await query.edit_message_text(shop_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e:
            logger.error(f"❌ Ошибка показа магазина: {e}")

    async def show_stats_menu(self, query, context):
        """Показывает меню статистики"""
        try:
            user_id = query.from_user.id
            username = query.from_user.username or query.from_user.first_name or "Unknown"
            
            # Получаем статистику пользователя
            from database_psycopg2 import get_player_detailed_stats
            stats = get_player_detailed_stats(user_id)
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            stats_text = f"🌲 <b>Статистика Лес и волки</b>\n\n"
            stats_text += f"👤 <b>{username}:</b>\n\n"
            
            if stats:
                stats_text += f"🎮 Игр сыграно: {stats.get('games_played', 0)}\n"
                stats_text += f"🏆 Побед: {stats.get('wins', 0)}\n"
                stats_text += f"💀 Поражений: {stats.get('losses', 0)}\n"
                stats_text += f"🌰 Орешков заработано: {stats.get('total_nuts', 0)}\n"
            else:
                stats_text += "📊 Статистика пока пуста\n"
                stats_text += "🎮 Сыграйте в игру, чтобы появилась статистика!"
            
            await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e:
            logger.error(f"❌ Ошибка показа статистики: {e}")

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает профиль игрока"""
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name or "Unknown"
            
            if not self.db:
                await update.message.reply_text("❌ База данных недоступна. Попробуйте позже.")
                return
            
            logger.info(f"👤 Запрос профиля для пользователя {username} (ID: {user_id})")
            
            # Получаем баланс пользователя
            from database_balance_manager import balance_manager
            user_balance = balance_manager.get_user_balance(user_id)
            
            # Получаем кликабельное имя с учетом никнейма
            clickable_name = self.format_player_tag(username, user_id, make_clickable=True)
            
            # Создаем клавиатуру профиля
            keyboard = [
                [InlineKeyboardButton("🧺 Корзинка", callback_data="show_inventory")],
                [InlineKeyboardButton("📜 Свиток чести", callback_data="show_chat_stats")],
                [InlineKeyboardButton("🌰 Баланс", callback_data="show_balance")],
                [InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")],
                [InlineKeyboardButton("❌ Закрыть", callback_data="close_profile")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Формируем сообщение профиля
            profile_text = f"👤 <b>Профиль игрока</b> 👤\n\n"
            profile_text += f"🌲 <b>{clickable_name}</b>\n"
            profile_text += f"🌰 Орешки: {user_balance}\n\n"
            profile_text += "🎮 Выберите действие:\n"
            profile_text += "🧺 <b>Корзинка</b> - ваш инвентарь\n"
            profile_text += "📜 <b>Свиток чести</b> - статистика в этом чате\n"
            profile_text += "🌰 <b>Баланс</b> - подробная информация об орешках\n"
            profile_text += "🛍️ <b>Магазин</b> - покупка товаров"
            
            await update.message.reply_text(profile_text, reply_markup=reply_markup, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения профиля: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            await update.message.reply_text("❌ Произошла ошибка при получении профиля. Попробуйте позже.")

    async def global_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает общую статистику игрока"""
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name or "Unknown"
            
            if not self.db:
                await update.message.reply_text("❌ База данных недоступна. Попробуйте позже.")
                return
            
            logger.info(f"🌍 Запрос общей статистики для пользователя {username} (ID: {user_id})")
            
            # Получаем общую статистику пользователя
            from database_psycopg2 import get_player_detailed_stats
            stats = get_player_detailed_stats(user_id)
            
            # Формируем сообщение статистики
            stats_text = f"🌍 <b>Общая статистика</b> 🌍\n\n"
            stats_text += f"👤 <b>{username}</b>\n\n"
            
            if stats:
                games_played = stats.get('games_played', 0)
                games_won = stats.get('games_won', 0)
                games_lost = stats.get('games_lost', 0)
                win_rate = stats.get('win_rate', 0)
                
                # Получаем баланс пользователя
                from database_balance_manager import balance_manager
                total_nuts = balance_manager.get_user_balance(user_id)
                
                stats_text += f"🎮 <b>Игровая статистика:</b>\n"
                stats_text += f"• Игр сыграно: {games_played}\n"
                stats_text += f"• Побед: {games_won}\n"
                stats_text += f"• Поражений: {games_lost}\n"
                stats_text += f"• Процент побед: {win_rate:.1f}%\n\n"
                
                stats_text += f"🌰 <b>Орешки:</b>\n"
                stats_text += f"• Всего заработано: {total_nuts}\n"
                stats_text += f"• Среднее за игру: {total_nuts // games_played if games_played > 0 else 0}\n\n"
                
                # Дополнительная статистика по ролям
                if 'role_stats' in stats:
                    role_stats = stats['role_stats']
                    stats_text += f"🎭 <b>Статистика по ролям:</b>\n"
                    for role, count in role_stats.items():
                        stats_text += f"• {role}: {count} раз\n"
            else:
                stats_text += "📊 Статистика пока пуста\n"
                stats_text += "🎮 Сыграйте в игру, чтобы появилась статистика!\n\n"
                stats_text += "💡 Используйте /profile для просмотра статистики в конкретном чате"
            
            await update.message.reply_text(stats_text)
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения общей статистики: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            await update.message.reply_text("❌ Произошла ошибка при получении статистики. Попробуйте позже.")

    async def nickname_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для установки никнейма игрока"""
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name or "Unknown"
            
            if not self.db:
                await update.message.reply_text("❌ База данных недоступна. Попробуйте позже.")
                return
            
            # Получаем аргументы команды
            if not context.args:
                # Показываем текущий никнейм и инструкции
                from database_psycopg2 import get_user_nickname, get_display_name
                
                current_nickname = get_user_nickname(user_id)
                display_name = get_display_name(user_id, username, update.effective_user.first_name)
                
                help_text = f"🎭 <b>Управление никнеймом</b>\n\n"
                help_text += f"👤 <b>Текущее имя:</b> {display_name}\n"
                
                if current_nickname:
                    help_text += f"🎭 <b>Никнейм:</b> {current_nickname}\n\n"
                    help_text += f"💡 <b>Команды:</b>\n"
                    help_text += f"• <code>/nickname НовыйНик</code> - изменить никнейм\n"
                    help_text += f"• <code>/nickname clear</code> - удалить никнейм\n"
                    help_text += f"• <code>/reset_nickname</code> - быстро сбросить никнейм\n"
                else:
                    help_text += f"🎭 <b>Никнейм:</b> не установлен\n\n"
                    help_text += f"💡 <b>Команды:</b>\n"
                    help_text += f"• <code>/nickname НовыйНик</code> - установить никнейм\n"
                
                help_text += f"\n📝 <b>Правила:</b>\n"
                help_text += f"• Максимум 50 символов\n"
                help_text += f"• Должен содержать буквы или цифры\n"
                help_text += f"• Должен быть уникальным\n"
                help_text += f"• Никнейм будет использоваться во всех играх"
                
                await update.message.reply_text(help_text, parse_mode='HTML')
                return
            
            # Обрабатываем команду
            nickname_arg = " ".join(context.args).strip()
            
            if nickname_arg.lower() == "clear":
                # Удаляем никнейм
                from database_psycopg2 import clear_user_nickname, get_display_name
                
                if clear_user_nickname(user_id):
                    display_name = get_display_name(user_id, username, update.effective_user.first_name)
                    await update.message.reply_text(
                        f"✅ <b>Никнейм удален!</b>\n\n"
                        f"👤 <b>Теперь вас будут называть:</b> {display_name}",
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text("❌ Ошибка при удалении никнейма. Попробуйте позже.")
            else:
                # Устанавливаем новый никнейм
                from database_psycopg2 import set_user_nickname, is_nickname_available, get_display_name
                
                # Проверяем доступность никнейма
                if not is_nickname_available(nickname_arg, user_id):
                    await update.message.reply_text(
                        f"❌ <b>Никнейм занят!</b>\n\n"
                        f"🎭 Никнейм '{nickname_arg}' уже используется другим игроком.\n"
                        f"💡 Попробуйте другой никнейм.",
                        parse_mode='HTML'
                    )
                    return
                
                # Устанавливаем никнейм
                if set_user_nickname(user_id, nickname_arg):
                    display_name = get_display_name(user_id, username, update.effective_user.first_name)
                    await update.message.reply_text(
                        f"✅ <b>Никнейм установлен!</b>\n\n"
                        f"🎭 <b>Ваш никнейм:</b> {nickname_arg}\n"
                        f"👤 <b>Вас будут называть:</b> {display_name}\n\n"
                        f"💡 Никнейм будет использоваться во всех играх и упоминаниях!",
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(
                        f"❌ <b>Ошибка установки никнейма!</b>\n\n"
                        f"💡 Проверьте, что никнейм:\n"
                        f"• Не пустой\n"
                        f"• Не длиннее 50 символов\n"
                        f"• Содержит буквы или цифры",
                        parse_mode='HTML'
                    )
                
        except Exception as e:
            logger.error(f"❌ Ошибка команды nickname: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            await update.message.reply_text("❌ Произошла ошибка при работе с никнеймом. Попробуйте позже.")

    async def reset_nickname_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для сброса никнейма игрока"""
        # Проверяем права пользователя
        has_permission, error_msg = await self.check_user_permissions(update, context, "member")
        if not has_permission:
            await self.send_permission_error(update, context, error_msg)
            return
        
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name or "Unknown"
            
            if not self.db:
                await update.message.reply_text("❌ База данных недоступна. Попробуйте позже.")
                return
            
            # Проверяем, есть ли у пользователя никнейм
            from database_psycopg2 import get_user_nickname, clear_user_nickname, get_display_name
            
            current_nickname = get_user_nickname(user_id)
            
            if not current_nickname:
                await update.message.reply_text(
                    "ℹ️ <b>У вас нет никнейма!</b>\n\n"
                    "💡 Используйте <code>/nickname НовыйНик</code> для установки никнейма.",
                    parse_mode='HTML'
                )
                return
            
            # Удаляем никнейм
            if clear_user_nickname(user_id):
                display_name = get_display_name(user_id, username, update.effective_user.first_name)
                await update.message.reply_text(
                    f"✅ <b>Никнейм сброшен!</b>\n\n"
                    f"🎭 <b>Удален никнейм:</b> {current_nickname}\n"
                    f"👤 <b>Теперь вас будут называть:</b> {display_name}\n\n"
                    f"💡 Используйте <code>/nickname НовыйНик</code> для установки нового никнейма.",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text("❌ Ошибка при сбросе никнейма. Попробуйте позже.")
                
        except Exception as e:
            logger.error(f"❌ Ошибка команды reset_nickname: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            await update.message.reply_text("❌ Произошла ошибка при сбросе никнейма. Попробуйте позже.")

    async def handle_farewell_message(self, query, context, user_id: int):
        """Обрабатывает запрос на прощальное сообщение"""
        try:
            # Проверяем, что запрос от правильного пользователя
            if query.from_user.id != user_id:
                await query.answer("❌ Это не ваше прощальное сообщение!", show_alert=True)
                return
            
            # Проверяем, можно ли отправить прощальное сообщение
            can_send, error_message, game_data = await self.can_send_farewell_message(user_id)
            
            logger.info(f"Прощальное сообщение для пользователя {user_id}: can_send={can_send}, error={error_message}")
            
            if not can_send:
                # Показываем ошибку вместо меню
                error_text = (
                    f"❌ <b>Прощальное сообщение недоступно</b>\n\n"
                    f"{error_message}\n\n"
                    f"💡 Прощальное сообщение можно отправить только:\n"
                    f"• После участия в игре\n"
                    f"• В течение суток после окончания игры\n"
                    f"• Если в чате не началась новая игра"
                )
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"farewell_back_{user_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')
                return
            
            # Создаем клавиатуру с вариантами прощальных сообщений
            keyboard = [
                [InlineKeyboardButton("🌲 Лесное прощание", callback_data=f"farewell_forest_{user_id}")],
                [InlineKeyboardButton("🐺 Прощание волка", callback_data=f"farewell_wolf_{user_id}")],
                [InlineKeyboardButton("🦊 Прощание лисы", callback_data=f"farewell_fox_{user_id}")],
                [InlineKeyboardButton("🐰 Прощание зайца", callback_data=f"farewell_hare_{user_id}")],
                [InlineKeyboardButton("🦫 Прощание бобра", callback_data=f"farewell_beaver_{user_id}")],
                [InlineKeyboardButton("🕳️ Прощание крота", callback_data=f"farewell_mole_{user_id}")],
                [InlineKeyboardButton("✍️ Написать свое сообщение", callback_data=f"farewell_custom_{user_id}")],
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"farewell_back_{user_id}")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            farewell_text = (
                "🍂 <b>Прощальные слова</b> 🍂\n\n"
                "🌲 Лес прощается с тобой...\n"
                "💭 Выбери, как ты хочешь попрощаться с остальными обитателями леса:\n\n"
                "🌿 Каждое прощание имеет свой особый лесной стиль!\n\n"
                f"⏰ Время на прощание: в течение суток после окончания игры"
            )
            
            await query.edit_message_text(farewell_text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки прощального сообщения: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def handle_leave_forest(self, query, context):
        """Обрабатывает покидание леса"""
        try:
            farewell_text = (
                "🌲 <b>Покидание леса</b> 🌲\n\n"
                "🍂 Ты тихо покидаешь лес...\n"
                "🌙 Твоя душа уходит в звёздный лес навсегда.\n\n"
                "⭐️ До свидания, путник! ⭐️"
            )
            
            await query.edit_message_text(farewell_text)
            
        except Exception as e:
            logger.error(f"❌ Ошибка покидания леса: {e}")

    async def can_send_farewell_message(self, user_id: int) -> tuple[bool, str, dict]:
        """
        Проверяет, можно ли отправить прощальное сообщение
        
        Returns:
            tuple[bool, str, dict]: (можно_отправить, сообщение_об_ошибке, данные_игры)
        """
        try:
            from datetime import datetime, timedelta
            
            # Находим последнюю игру для этого пользователя (активную или завершенную)
            last_game = None
            last_game_chat_id = None
            
            # Сначала проверяем активные игры
            for chat_id, game in self.games.items():
                if user_id in [player.user_id for player in game.players.values()]:
                    last_game = game
                    last_game_chat_id = chat_id
                    logger.info(f"Найдена активная игра для пользователя {user_id} в чате {chat_id}, фаза: {game.phase}")
                    break
            
            # Если нет активной игры, ищем в базе данных последнюю завершенную игру
            if not last_game:
                try:
                    from database_psycopg2 import fetch_query
                    
                    # Ищем последнюю игру пользователя в базе данных
                    query = """
                        SELECT chat_id, thread_id, game_data, created_at, updated_at
                        FROM active_games_state 
                        WHERE game_data->>'phase' = 'finished'
                        AND game_data->'players' ? %s
                        ORDER BY updated_at DESC 
                        LIMIT 1
                    """
                    
                    result = fetch_query(query, (str(user_id),))
                    if result:
                        game_data = result[0]
                        last_game_chat_id = game_data['chat_id']
                        last_game = {
                            'chat_id': game_data['chat_id'],
                            'thread_id': game_data['thread_id'],
                            'updated_at': game_data['updated_at']
                        }
                        logger.info(f"Найдена завершенная игра в БД для пользователя {user_id} в чате {last_game_chat_id}")
                    else:
                        logger.info(f"Завершенная игра в БД не найдена для пользователя {user_id}")
                except Exception as db_error:
                    logger.warning(f"Ошибка поиска в БД: {db_error}")
                    # Если БД недоступна, разрешаем прощальное сообщение для активных игр
                    if last_game_chat_id:
                        last_game = {
                            'chat_id': last_game_chat_id,
                            'thread_id': None,
                            'updated_at': datetime.now()
                        }
            
            if not last_game:
                logger.warning(f"Прощальное сообщение: игра не найдена для пользователя {user_id}")
                return False, "❌ Игра не найдена! Прощальное сообщение можно отправить только после участия в игре.", {}
            
            # Проверяем, не началась ли уже новая игра в том же чате
            if last_game_chat_id in self.games:
                current_game = self.games[last_game_chat_id]
                if current_game.phase != 'finished' and user_id not in [player.user_id for player in current_game.players.values()]:
                    return False, "❌ В чате уже началась новая игра! Прощальное сообщение можно отправить только после окончания игры.", {}
            
            # Проверяем время (не позже чем через час после окончания)
            game_end_time = None
            if hasattr(last_game, 'updated_at'):
                game_end_time = last_game.updated_at
            elif isinstance(last_game, dict):
                game_end_time = last_game.get('updated_at')
            
            if game_end_time:
                if isinstance(game_end_time, str):
                    try:
                        game_end_time = datetime.fromisoformat(game_end_time.replace('Z', '+00:00'))
                    except:
                        game_end_time = datetime.now()
                
                current_time = datetime.now(game_end_time.tzinfo) if game_end_time.tzinfo else datetime.now()
                time_diff = current_time - game_end_time
                
                if time_diff > timedelta(hours=24):  # Увеличиваем время до 24 часов
                    return False, f"❌ Прошло слишком много времени! Прощальное сообщение можно отправить только в течение суток после окончания игры. (Прошло: {time_diff.total_seconds()/3600:.1f} часов)", {}
            
            return True, "", last_game
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки возможности прощального сообщения: {e}")
            return False, f"❌ Ошибка проверки: {str(e)}", {}

    async def send_farewell_to_chat(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, farewell_type: str, username: str):
        """Отправляет прощальное сообщение в чат"""
        try:
            # Проверяем, можно ли отправить прощальное сообщение
            can_send, error_message, game_data = await self.can_send_farewell_message(user_id)
            
            if not can_send:
                logger.warning(f"Нельзя отправить прощальное сообщение для пользователя {user_id}: {error_message}")
                return False, error_message
            
            # Используем данные игры
            chat_id = game_data.get('chat_id')
            thread_id = game_data.get('thread_id')
            
            logger.info(f"Прощальное сообщение: chat_id={chat_id}, thread_id={thread_id}, game_data={game_data}")
            
            if not chat_id:
                return False, "❌ Не удалось определить чат для отправки прощального сообщения"
            
            # Получаем отображаемое имя пользователя
            display_name = self.get_display_name(user_id, username, None)
            
            # Получаем прощальное сообщение по типу
            farewell_messages = {
                "forest": f"🌲 {display_name} прощается с лесом: \"Спасибо за игру, друзья! Лес навсегда останется в моём сердце... 🌿\"",
                "wolf": f"🐺 {display_name} воет на прощание: \"Аууу! Было круто охотиться с вами! Увидимся в звёздном лесу! 🌙\"",
                "fox": f"🦊 {display_name} машет хвостом: \"Хи-хи! Какая интересная игра! Надеюсь, вы не забудете мои хитрости! 🍇\"",
                "hare": f"🐰 {display_name} подпрыгивает: \"Прыг-скок! Спасибо за веселье! Лес полон чудес! 🥕\"",
                "beaver": f"🦫 {display_name} стучит хвостом: \"Тук-тук! Отличная работа, команда! Строим мосты дружбы! 🌉\"",
                "mole": f"🕳️ {display_name} выглядывает из норки: \"Копаю-копаю! Было интересно рыть туннели! До встречи! 🕳️\""
            }
            
            message = farewell_messages.get(farewell_type, farewell_messages["forest"])
            
            # Отправляем в чат игры
            if thread_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    message_thread_id=thread_id
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message
                )
            
            logger.info(f"✅ Отправлено прощальное сообщение от {username} в чат {chat_id}")
            return True, "✅ Прощальное сообщение отправлено!"
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки прощального сообщения в чат: {e}")
            return False, f"❌ Ошибка отправки: {str(e)}"

    async def handle_farewell_type(self, query, context, farewell_type: str, user_id: int):
        """Обрабатывает выбор типа прощания"""
        try:
            # Проверяем, что запрос от правильного пользователя
            if query.from_user.id != user_id:
                await query.answer("❌ Это не ваше прощальное сообщение!", show_alert=True)
                return
            
            username = query.from_user.username or query.from_user.first_name or "Игрок"
            
            # Отправляем прощальное сообщение в чат
            success, message = await self.send_farewell_to_chat(context, user_id, farewell_type, username)
            
            if success:
                # Показываем подтверждение
                confirmation_text = (
                    f"✅ <b>Прощальное сообщение отправлено!</b>\n\n"
                    f"🌲 Твоё прощание в стиле {farewell_type} было отправлено в чат игры.\n\n"
                    f"🍂 Лес будет помнить твои слова...\n"
                    f"⭐️ До свидания, {username}!"
                )
                
                await query.edit_message_text(confirmation_text)
            else:
                # Показываем ошибку
                error_text = (
                    f"❌ <b>Не удалось отправить прощальное сообщение</b>\n\n"
                    f"{message}\n\n"
                    f"💡 Попробуйте позже или обратитесь к администратору."
                )
                
                await query.edit_message_text(error_text)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки типа прощания: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def handle_custom_farewell(self, query, context, user_id: int):
        """Обрабатывает запрос на написание своего прощального сообщения"""
        try:
            # Проверяем, что запрос от правильного пользователя
            if query.from_user.id != user_id:
                await query.answer("❌ Это не ваше прощальное сообщение!", show_alert=True)
                return
            
            # Проверяем, можно ли отправить прощальное сообщение
            can_send, error_message, game_data = await self.can_send_farewell_message(user_id)
            
            if not can_send:
                error_text = (
                    f"❌ <b>Прощальное сообщение недоступно</b>\n\n"
                    f"{error_message}\n\n"
                    f"💡 Прощальное сообщение можно отправить только:\n"
                    f"• После участия в игре\n"
                    f"• В течение суток после окончания игры\n"
                    f"• Если в чате не началась новая игра"
                )
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"farewell_back_{user_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')
                return
            
            # Показываем инструкции для написания своего сообщения
            custom_text = (
                "✍️ <b>Написать свое прощальное сообщение</b> ✍️\n\n"
                "🌲 Напишите свое личное прощальное сообщение в следующем сообщении.\n\n"
                "💭 <b>Советы:</b>\n"
                "• Сообщение должно быть в духе игры\n"
                "• Не используйте оскорбления или нецензурную лексику\n"
                "• Максимум 200 символов\n"
                "• Можете использовать эмодзи\n\n"
                "📝 <b>Примеры:</b>\n"
                "• \"Спасибо за игру, друзья! Было весело! 🌿\"\n"
                "• \"До свидания, лес! Увидимся в следующей игре! 🐺\"\n\n"
                "⏰ У вас есть 5 минут на написание сообщения.\n"
                "❌ Отправьте /cancel для отмены."
            )
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Назад к выбору", callback_data=f"farewell_back_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(custom_text, reply_markup=reply_markup, parse_mode='HTML')
            
            # Сохраняем состояние ожидания пользовательского ввода
            from datetime import datetime
            context.user_data[f'waiting_custom_farewell_{user_id}'] = {
                'game_data': game_data,
                'start_time': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки кастомного прощания: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def handle_custom_farewell_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, username: str):
        """Обрабатывает текстовое сообщение для кастомного прощания"""
        try:
            from datetime import datetime, timedelta
            
            # Получаем данные ожидания
            waiting_data = context.user_data.get(f'waiting_custom_farewell_{user_id}')
            if not waiting_data:
                await update.message.reply_text("❌ Время ожидания истекло. Попробуйте снова.")
                return
            
            # Проверяем время ожидания (5 минут)
            start_time = waiting_data['start_time']
            current_time = datetime.now()
            if current_time - start_time > timedelta(minutes=5):
                del context.user_data[f'waiting_custom_farewell_{user_id}']
                await update.message.reply_text("⏰ Время ожидания истекло. Попробуйте снова.")
                return
            
            # Получаем текст сообщения
            message_text = update.message.text.strip()
            
            # Проверяем команду отмены
            if message_text.lower() in ['/cancel', 'отмена', 'cancel']:
                del context.user_data[f'waiting_custom_farewell_{user_id}']
                await update.message.reply_text("❌ Создание прощального сообщения отменено.")
                return
            
            # Проверяем длину сообщения
            if len(message_text) > 200:
                await update.message.reply_text(
                    "❌ Сообщение слишком длинное! Максимум 200 символов.\n"
                    f"Ваше сообщение: {len(message_text)} символов\n\n"
                    "Попробуйте сократить сообщение."
                )
                return
            
            if len(message_text) < 5:
                await update.message.reply_text(
                    "❌ Сообщение слишком короткое! Минимум 5 символов.\n\n"
                    "Попробуйте написать более развернутое сообщение."
                )
                return
            
            # Проверяем на нецензурную лексику (базовая проверка)
            bad_words = ['дурак', 'идиот', 'тупой', 'глупый', 'лох', 'придурок']
            if any(word in message_text.lower() for word in bad_words):
                await update.message.reply_text(
                    "❌ Сообщение содержит недопустимые слова!\n\n"
                    "Пожалуйста, напишите сообщение в духе игры без оскорблений."
                )
                return
            
            # Отправляем кастомное прощальное сообщение
            game_data = waiting_data['game_data']
            chat_id = game_data.get('chat_id')
            thread_id = game_data.get('thread_id')
            
            if not chat_id:
                await update.message.reply_text("❌ Не удалось определить чат для отправки прощального сообщения.")
                return
            
            # Получаем отображаемое имя пользователя
            display_name = self.get_display_name(user_id, username, None)
            
            # Формируем сообщение
            farewell_message = f"💬 {display_name} прощается: \"{message_text}\""
            
            # Отправляем в чат игры
            try:
                if thread_id:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=farewell_message,
                        message_thread_id=thread_id
                    )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=farewell_message
                    )
                
                # Удаляем состояние ожидания
                del context.user_data[f'waiting_custom_farewell_{user_id}']
                
                # Показываем подтверждение
                confirmation_text = (
                    f"✅ <b>Ваше прощальное сообщение отправлено!</b>\n\n"
                    f"💬 <b>Сообщение:</b> \"{message_text}\"\n\n"
                    f"🌲 Ваше прощание было отправлено в чат игры.\n"
                    f"🍂 Лес будет помнить ваши слова...\n"
                    f"⭐️ До свидания, {username}!"
                )
                
                await update.message.reply_text(confirmation_text, parse_mode='HTML')
                
                logger.info(f"✅ Отправлено кастомное прощальное сообщение от {username} в чат {chat_id}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка отправки кастомного прощального сообщения: {e}")
                await update.message.reply_text(
                    "❌ Не удалось отправить прощальное сообщение в чат.\n"
                    "Попробуйте позже или обратитесь к администратору."
                )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки кастомного прощального текста: {e}")
            await update.message.reply_text("❌ Произошла ошибка при обработке сообщения.")

    async def handle_farewell_back(self, query, context, user_id: int):
        """Обрабатывает возврат к предыдущему меню прощания"""
        try:
            # Проверяем, что запрос от правильного пользователя
            if query.from_user.id != user_id:
                await query.answer("❌ Это не ваше прощальное сообщение!", show_alert=True)
                return
            
            # Возвращаемся к основному меню прощания
            await self.handle_farewell_message(query, context, user_id)
            
        except Exception as e:
            logger.error(f"❌ Ошибка возврата к меню прощания: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def show_inventory(self, query, context):
        """Показывает инвентарь игрока (корзинка)"""
        try:
            user_id = query.from_user.id
            username = query.from_user.username or query.from_user.first_name or "Unknown"
            
            # Получаем подробную информацию об инвентаре
            from database_psycopg2 import get_user_inventory_detailed
            
            inventory_data = get_user_inventory_detailed(user_id)
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Назад к профилю", callback_data="back_to_profile")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Получаем кликабельное имя с учетом никнейма
            clickable_name = self.format_player_tag(username, user_id, make_clickable=True)
            
            inventory_text = f"🧺 <b>Корзинка</b> 🧺\n\n"
            inventory_text += f"👤 <b>{clickable_name}</b>\n\n"
            
            if not inventory_data['success']:
                inventory_text += f"❌ {inventory_data['error']}"
            elif inventory_data['items']:
                inventory_text += "🛍️ <b>Ваши товары:</b>\n\n"
                
                for item in inventory_data['items']:
                    item_name = item['item_name']
                    count = item['count']
                    inventory_text += f"• {item_name} x{count}\n"
                
                inventory_text += f"\n📦 Всего товаров: {inventory_data['total_items']} видов\n"
                inventory_text += f"🌰 Орешки: {inventory_data['balance']}"
            else:
                inventory_text += "📦 Корзинка пуста\n\n"
                inventory_text += "🛍️ Посетите магазин, чтобы купить товары!\n"
                inventory_text += "💡 Используйте кнопку 'Магазин' в профиле"
            
            await query.edit_message_text(inventory_text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа инвентаря: {e}")
            await query.answer("❌ Произошла ошибка при загрузке инвентаря!", show_alert=True)

    async def show_chat_stats(self, query, context):
        """Показывает статистику игрока в этом чате (свиток чести)"""
        try:
            user_id = query.from_user.id
            username = query.from_user.username or query.from_user.first_name or "Unknown"
            chat_id = query.message.chat.id
            
            # Получаем статистику игрока в этом чате
            stats = get_player_chat_stats(user_id, chat_id)
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Назад к профилю", callback_data="back_to_profile")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Получаем кликабельное имя с учетом никнейма
            clickable_name = self.format_player_tag(username, user_id, make_clickable=True)
            
            stats_text = f"📜 <b>Свиток чести</b> 📜\n\n"
            stats_text += f"👤 <b>{clickable_name}</b>\n"
            stats_text += f"🌲 <b>В этом чате</b>\n\n"
            
            if stats:
                games_played = stats.get('games_played', 0)
                games_won = stats.get('games_won', 0)
                games_lost = stats.get('games_lost', 0)
                total_nuts = stats.get('total_nuts', 0)
                win_rate = (games_won / games_played * 100) if games_played > 0 else 0
                
                stats_text += f"🎮 <b>Игровая статистика:</b>\n"
                stats_text += f"• Игр сыграно: {games_played}\n"
                stats_text += f"• Побед: {games_won}\n"
                stats_text += f"• Поражений: {games_lost}\n"
                stats_text += f"• Процент побед: {win_rate:.1f}%\n\n"
                
                stats_text += f"🌰 <b>Орешки в этом чате:</b>\n"
                stats_text += f"• Заработано: {total_nuts}\n"
                stats_text += f"• Среднее за игру: {total_nuts // games_played if games_played > 0 else 0}\n\n"
                
                # Статистика по ролям в этом чате
                if 'role_stats' in stats:
                    role_stats = stats['role_stats']
                    stats_text += f"🎭 <b>Роли в этом чате:</b>\n"
                    for role, count in role_stats.items():
                        stats_text += f"• {role}: {count} раз\n"
                
                # Рейтинг в чате
                if 'chat_rank' in stats:
                    rank = stats['chat_rank']
                    stats_text += f"\n🏆 <b>Рейтинг в чате:</b> #{rank}"
            else:
                stats_text += "📊 Статистика в этом чате пуста\n\n"
                stats_text += "🎮 Сыграйте в игру в этом чате, чтобы появилась статистика!\n\n"
                stats_text += "💡 Используйте /global_stats для просмотра общей статистики"
            
            await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа статистики чата: {e}")
            await query.answer("❌ Произошла ошибка при загрузке статистики!", show_alert=True)

    async def back_to_profile(self, query, context):
        """Возвращает к профилю игрока"""
        try:
            user_id = query.from_user.id
            username = query.from_user.username or query.from_user.first_name or "Unknown"
            
            # Получаем баланс пользователя
            from database_balance_manager import balance_manager
            user_balance = balance_manager.get_user_balance(user_id)
            
            # Создаем клавиатуру профиля
            keyboard = [
                [InlineKeyboardButton("🧺 Корзинка", callback_data="show_inventory")],
                [InlineKeyboardButton("📜 Свиток чести", callback_data="show_chat_stats")],
                [InlineKeyboardButton("🌰 Баланс", callback_data="show_balance")],
                [InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")],
                [InlineKeyboardButton("❌ Закрыть", callback_data="close_profile")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Получаем кликабельное имя с учетом никнейма
            clickable_name = self.format_player_tag(username, user_id, make_clickable=True)
            
            # Формируем сообщение профиля
            profile_text = f"👤 <b>Профиль игрока</b> 👤\n\n"
            profile_text += f"🌲 <b>{clickable_name}</b>\n"
            profile_text += f"🌰 Орешки: {user_balance}\n\n"
            profile_text += "🎮 Выберите действие:\n"
            profile_text += "🧺 <b>Корзинка</b> - ваш инвентарь\n"
            profile_text += "📜 <b>Свиток чести</b> - статистика в этом чате\n"
            profile_text += "🌰 <b>Баланс</b> - подробная информация об орешках\n"
            profile_text += "🛍️ <b>Магазин</b> - покупка товаров"
            
            await query.edit_message_text(profile_text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка возврата к профилю: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def handle_join_chat(self, query, context):
        """Обрабатывает кнопку 'Войти в чат'"""
        try:
            join_text = (
                "🎮 <b>Войти в чат</b> 🎮\n\n"
                "🌲 Чтобы присоединиться к игре:\n\n"
                "1️⃣ <b>Найдите чат с игрой</b>\n"
                "• Ищите чаты, где уже запущена игра 'Лес и Волки'\n"
                "• Или создайте новый чат и добавьте бота\n\n"
                "2️⃣ <b>Присоединитесь к игре</b>\n"
                "• Используйте команду `/join` в чате с игрой\n"
                "• Или нажмите кнопку 'Присоединиться' в сообщении игры\n\n"
                "3️⃣ <b>Начните играть!</b>\n"
                "• Дождитесь начала игры\n"
                "• Следуйте инструкциям бота\n\n"
                "💡 <b>Совет:</b> Добавьте бота в свой чат, чтобы создать игру!"
            )
            
            keyboard = [
                [InlineKeyboardButton("🌲 Добавить игру в свой чат", url=f"https://t.me/{context.bot.username}?startgroup=true")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(join_text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки 'Войти в чат': {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def handle_language_settings(self, query, context):
        """Обрабатывает кнопку 'Язык / Language'"""
        try:
            language_text = (
                "🌍 <b>Язык / Language</b> 🌍\n\n"
                "🌲 <b>Русский (Russian)</b>\n"
                "• Основной язык бота\n"
                "• Все сообщения на русском\n"
                "• Роли и описания на русском\n\n"
                "🇺🇸 <b>English</b>\n"
                "• Английский язык (в разработке)\n"
                "• English language (coming soon)\n\n"
                "💡 <b>Сейчас доступен только русский язык</b>"
            )
            
            keyboard = [
                [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
                [InlineKeyboardButton("🇺🇸 English (скоро)", callback_data="lang_en_disabled")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(language_text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки настроек языка: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def show_profile_pm(self, query, context):
        """Показывает профиль в личных сообщениях"""
        try:
            user_id = query.from_user.id
            username = query.from_user.username or query.from_user.first_name or "Unknown"
            
            # Получаем баланс пользователя
            from database_balance_manager import balance_manager
            user_balance = balance_manager.get_user_balance(user_id)
            
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
            profile_text = f"👤 <b>Профиль игрока</b> 👤\n\n"
            profile_text += f"🌲 <b>{username}</b>\n"
            profile_text += f"🌰 Орешки: {user_balance}\n\n"
            profile_text += "🎮 Выберите действие:\n"
            profile_text += "🧺 <b>Корзинка</b> - ваш инвентарь\n"
            profile_text += "📜 <b>Свиток чести</b> - статистика в чатах\n"
            profile_text += "🌰 <b>Баланс</b> - подробная информация об орешках\n"
            profile_text += "🛍️ <b>Магазин</b> - покупка товаров"
            
            await query.edit_message_text(profile_text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа профиля в ЛС: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def show_roles_pm(self, query, context):
        """Показывает роли в личных сообщениях"""
        try:
            roles_text = (
                "🎭 <b>Роли в игре</b> 🎭\n\n"
                "🐺 <b>ХИЩНИКИ (Predators)</b>\n\n"
                "🐺 <b>Волк</b>\n"
                "• Убивает одного игрока каждую ночь\n"
                "• Цель: уничтожить всех травоядных\n"
                "• Может быть изгнан голосованием\n\n"
                "🦊 <b>Лиса</b>\n"
                "• Крадет орешки у игроков\n"
                "• Умирает после 2 краж\n"
                "• Помогает волкам\n\n"
                "🐰 <b>ТРАВОЯДНЫЕ (Herbivores)</b>\n\n"
                "🐰 <b>Зайец</b>\n"
                "• Обычный мирный житель\n"
                "• Может быть убит волком\n"
                "• Участвует в голосовании\n\n"
                "🦫 <b>Бобёр</b>\n"
                "• Защищает одного игрока за ночь\n"
                "• Может спасти от волка\n"
                "• Защита работает один раз\n\n"
                "🕳️ <b>Крот</b>\n"
                "• Проверяет роли игроков\n"
                "• Узнает, кто хищник, а кто нет\n"
                "• Помогает травоядным"
            )
            
            keyboard = [
                [InlineKeyboardButton("📖 Подробные правила", callback_data="show_rules_pm")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(roles_text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа ролей в ЛС: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)


    async def repeat_role_actions(self, query, context):
        """Повторяет сообщения с кнопками действий для роли игрока"""
        try:
            user_id = query.from_user.id
            chat_id = query.message.chat.id
            
            # Проверяем, что игра существует
            if chat_id not in self.games:
                await query.answer("❌ Игра не найдена!", show_alert=True)
                return
            
            game = self.games[chat_id]
            
            # Проверяем, что игра идет
            if game.phase == GamePhase.WAITING:
                await query.answer("⏳ Игра еще не началась!", show_alert=True)
                return
            
            # Проверяем, что игрок участвует в игре
            if user_id not in game.players:
                await query.answer("❌ Вы не участвуете в игре!", show_alert=True)
                return
            
            player = game.players[user_id]
            
            # Отправляем сообщения с кнопками действий в зависимости от роли и фазы
            if game.phase == GamePhase.NIGHT:
                await self._send_night_role_actions(query, context, game, player)
            elif game.phase == GamePhase.DAY:
                await self._send_day_role_actions(query, context, game, player)
            elif game.phase == GamePhase.VOTING:
                await self._send_voting_role_actions(query, context, game, player)
            else:
                await query.answer("❌ Неизвестная фаза игры!", show_alert=True)
                
        except Exception as e:
            logger.error(f"❌ Ошибка повторения действий роли: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def _send_night_role_actions(self, query, context, game, player):
        """Отправляет ночные действия для роли"""
        try:
            if player.role == Role.WOLF:
                # Действия для волка
                message = (
                    "🐺 <b>Ваша роль: Волк</b>\n\n"
                    "🌙 <b>Ночная фаза</b>\n\n"
                    "Выберите жертву для убийства:"
                )
                
                # Создаем клавиатуру с живыми игроками
                keyboard = []
                for player_id, p in game.players.items():
                    if p.is_alive and p.role != Role.WOLF:
                        display_name = self.get_display_name(p.user_id, p.username, p.first_name)
                        keyboard.append([InlineKeyboardButton(f"🎯 {display_name}", callback_data=f"wolf_kill_{player_id}")])
                
                if keyboard:
                    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    await query.answer("❌ Нет доступных целей!", show_alert=True)
                    
            elif player.role == Role.FOX:
                # Действия для лисы
                message = (
                    "🦊 <b>Ваша роль: Лиса</b>\n\n"
                    "🌙 <b>Ночная фаза</b>\n\n"
                    "Выберите жертву для кражи орешков:"
                )
                
                # Создаем клавиатуру с живыми травоядными
                keyboard = []
                for player_id, p in game.players.items():
                    if p.is_alive and p.team == Team.HERBIVORES:
                        display_name = self.get_display_name(p.user_id, p.username, p.first_name)
                        keyboard.append([InlineKeyboardButton(f"💰 {display_name}", callback_data=f"fox_steal_{player_id}")])
                
                if keyboard:
                    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    await query.answer("❌ Нет доступных целей!", show_alert=True)
                    
            elif player.role == Role.MOLE:
                # Действия для крота
                message = (
                    "🦫 <b>Ваша роль: Крот</b>\n\n"
                    "🌙 <b>Ночная фаза</b>\n\n"
                    "Выберите игрока для проверки роли:"
                )
                
                # Создаем клавиатуру с живыми игроками
                keyboard = []
                for player_id, p in game.players.items():
                    if p.is_alive and p.role != Role.MOLE:
                        display_name = self.get_display_name(p.user_id, p.username, p.first_name)
                        keyboard.append([InlineKeyboardButton(f"🔍 {display_name}", callback_data=f"mole_check_{player_id}")])
                
                if keyboard:
                    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    await query.answer("❌ Нет доступных целей!", show_alert=True)
                    
            elif player.role == Role.BEAVER:
                # Действия для бобра
                message = (
                    "🦦 <b>Ваша роль: Бобёр</b>\n\n"
                    "🌙 <b>Ночная фаза</b>\n\n"
                    "Выберите игрока для защиты:"
                )
                
                # Создаем клавиатуру с живыми травоядными
                keyboard = []
                for player_id, p in game.players.items():
                    if p.is_alive and p.team == Team.HERBIVORES and p.role != Role.BEAVER:
                        display_name = self.get_display_name(p.user_id, p.username, p.first_name)
                        keyboard.append([InlineKeyboardButton(f"🛡️ {display_name}", callback_data=f"beaver_protect_{player_id}")])
                
                if keyboard:
                    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    await query.answer("❌ Нет доступных целей!", show_alert=True)
                    
            else:
                # Заяц - нет ночных действий
                message = (
                    "🐰 <b>Ваша роль: Заяц</b>\n\n"
                    "🌙 <b>Ночная фаза</b>\n\n"
                    "У вас нет ночных действий. Отдыхайте и ждите утра!"
                )
                await query.message.reply_text(message, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки ночных действий: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def _send_day_role_actions(self, query, context, game, player):
        """Отправляет дневные действия для роли"""
        try:
            message = (
                f"☀️ <b>Дневная фаза</b>\n\n"
                f"🎭 <b>Ваша роль:</b> {self.get_role_name_russian(player.role)}\n"
                f"🏷️ <b>Команда:</b> {'Хищники' if player.team == Team.PREDATORS else 'Травоядные'}\n\n"
                f"💬 <b>Обсуждайте события ночи и выдвигайте подозрения!</b>\n\n"
                f"🎯 <b>Ваша цель:</b> {'Уничтожить всех травоядных' if player.team == Team.PREDATORS else 'Найти и изгнать всех хищников'}"
            )
            
            await query.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки дневных действий: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def _send_voting_role_actions(self, query, context, game, player):
        """Отправляет действия голосования для роли"""
        try:
            message = (
                f"🗳️ <b>Фаза голосования</b>\n\n"
                f"🎭 <b>Ваша роль:</b> {self.get_role_name_russian(player.role)}\n"
                f"🏷️ <b>Команда:</b> {'Хищники' if player.team == Team.PREDATORS else 'Травоядные'}\n\n"
                f"🗳️ <b>Голосуйте за изгнание подозреваемого!</b>\n\n"
                f"🎯 <b>Ваша цель:</b> {'Уничтожить всех травоядных' if player.team == Team.PREDATORS else 'Найти и изгнать всех хищников'}"
            )
            
            # Создаем клавиатуру с живыми игроками для голосования
            keyboard = []
            for player_id, p in game.players.items():
                if p.is_alive and p.user_id != player.user_id:
                    display_name = self.get_display_name(p.user_id, p.username, p.first_name)
                    keyboard.append([InlineKeyboardButton(f"🗳️ {display_name}", callback_data=f"vote_{player_id}")])
            
            if keyboard:
                keyboard.append([InlineKeyboardButton("❌ Пропустить", callback_data="vote_skip")])
                # Добавляем кнопку "Перейти в ЛС с ботом" (если это не личные сообщения)
                if game.chat_id != player.user_id:
                    keyboard.append([InlineKeyboardButton("💬 Перейти в ЛС с ботом", url=f"https://t.me/{context.bot.username}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await query.message.reply_text(message, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки действий голосования: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def back_to_start(self, query, context):
        """Возвращает к начальному меню"""
        try:
            # Создаем клавиатуру для личных сообщений
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
                "🌲 <b>Привет!</b>\n\n"
                "Я бот-ведущий для игры в 🌲 <b>Лес и Волки</b>.\n\n"
                "🎭 <b>Ролевая игра в стиле 'Мафия' с лесными зверушками</b>\n\n"
                "🐺 <b>Хищники:</b> Волки + Лиса\n"
                "🐰 <b>Травоядные:</b> Зайцы + Крот + Бобёр\n\n"
                "🌙 <b>Как играть:</b>\n"
                "• Ночью хищники охотятся, травоядные защищаются\n"
                "• Днем все обсуждают и голосуют за изгнание\n"
                "• Цель: уничтожить всех противников\n\n"
                "🚀 <b>Выберите действие:</b>"
            )
            
            await query.edit_message_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка возврата к начальному меню: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def handle_language_ru(self, query, context):
        """Обрабатывает выбор русского языка"""
        try:
            await query.answer("🇷🇺 Русский язык уже выбран!", show_alert=True)
        except Exception as e:
            logger.error(f"❌ Ошибка обработки выбора русского языка: {e}")

    async def handle_language_en_disabled(self, query, context):
        """Обрабатывает попытку выбрать английский язык (отключен)"""
        try:
            await query.answer("🇺🇸 Английский язык пока недоступен! Скоро будет добавлен.", show_alert=True)
        except Exception as e:
            logger.error(f"❌ Ошибка обработки выбора английского языка: {e}")

    async def show_rules_pm(self, query, context):
        """Показывает подробные правила в личных сообщениях"""
        try:
            rules_text = (
                "📖 <b>Подробные правила игры</b> 📖\n\n"
                "🌲 <b>Лес и Волки</b> - ролевая игра в стиле 'Мафия'\n\n"
                "🎯 <b>Цель игры:</b>\n"
                "• Хищники: уничтожить всех травоядных\n"
                "• Травоядные: найти и изгнать всех хищников\n\n"
                "🌙 <b>Ночная фаза:</b>\n"
                "• Волк выбирает жертву для убийства\n"
                "• Лиса крадет орешки у игрока\n"
                "• Бобёр защищает одного игрока\n"
                "• Крот проверяет роль игрока\n\n"
                "☀️ <b>Дневная фаза:</b>\n"
                "• Все игроки обсуждают события ночи\n"
                "• Голосование за изгнание подозреваемого\n"
                "• Изгнанный игрок покидает игру\n\n"
                "🎭 <b>Роли:</b>\n"
                "• <b>Волк</b> - убивает каждую ночь\n"
                "• <b>Лиса</b> - крадет орешки (умирает после 2 краж)\n"
                "• <b>Зайец</b> - обычный мирный житель\n"
                "• <b>Бобёр</b> - защищает игроков\n"
                "• <b>Крот</b> - проверяет роли\n\n"
                "🏆 <b>Победа:</b>\n"
                "• Хищники побеждают, если осталось равное количество\n"
                "• Травоядные побеждают, если изгнали всех хищников\n\n"
                "💡 <b>Советы:</b>\n"
                "• Внимательно слушайте других игроков\n"
                "• Анализируйте поведение и голосования\n"
                "• Не раскрывайте свою роль раньше времени"
            )
            
            keyboard = [
                [InlineKeyboardButton("🎭 Роли", callback_data="show_roles_pm")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(rules_text, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа правил в ЛС: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)


if __name__ == "__main__":
    bot = ForestWolvesBot()
    bot.run()