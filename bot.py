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
    ContextTypes
)

from game_logic import Game, GamePhase, Role, Team, Player  # ваши реализации
from config import BOT_TOKEN, MIN_PLAYERS, TEST_MODE, TEST_MIN_PLAYERS  # ваши настройки
from night_actions import NightActions
from night_interface import NightInterface
from global_settings import GlobalSettings # Импортируем GlobalSettings

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ForestMafiaBot:
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

    # ---------------- basic commands ----------------
    async def welcome_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🎮 Начать игру", callback_data="welcome_start_game")],
            [InlineKeyboardButton("📖 Правила игры", callback_data="welcome_rules")],
            [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = (
            "🌲 *Добро пожаловать в Лесную Возню!* 🌲\n\n"
            "🎭 Это ролевая игра в стиле 'Мафия' с лесными зверушками!\n\n"
            "🐺 *Хищники:* Волки и Лиса\n"
            "🐰 *Травоядные:* Зайцы, Крот и Бобёр\n\n"
            "🎯 *Цель:* Уничтожить команду противника!\n\n"
            f"👥 Для игры нужно минимум {self.global_settings.get_min_players()} игроков\n"
            f"{'🧪 ТЕСТОВЫЙ РЕЖИМ АКТИВЕН' if self.global_settings.is_test_mode() else ''}\n"
            "⏰ Игра состоит из ночных и дневных фаз\n\n"
            "Нажмите кнопку ниже, чтобы начать!"
        )

        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        rules_text = (
            "📖 Правила игры 'Лесная Возня':\n\n"
            "🎭 Роли:\n"
            "🐺 Волки (Хищники) - стая, по ночам съедает по зверю\n"
            "🦊 Лиса (Хищники) - ворует запасы еды\n"
            "🐰 Зайцы (Травоядные) - мирные зверушки\n"
            "🦫 Крот (Травоядные) - роет норки, узнаёт команды других зверей\n"
            "🦦 Бобёр (Травоядные) - возвращает украденные запасы\n\n"
            "🌙 Ночные фазы: Волки → Лиса → Бобёр → Крот\n"
            "☀️ Дневные фазы: обсуждение и голосование\n"
            "🏆 Цель: уничтожить команду противника"
        )
        await update.message.reply_text(rules_text)

    # ---------------- callback helpers ----------------
    async def join_from_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        chat_id = query.message.chat.id
        user_id = query.from_user.id
        username = query.from_user.username or query.from_user.full_name or str(user_id)

        # Проверяем, что это группа, а не личные сообщения
        if chat_id == user_id:  # Это личные сообщения
            await query.edit_message_text("❌ Игра доступна только в группах! Добавьте бота в группу и попробуйте там.")
            return

        # already in another game?
        if user_id in self.player_games:
            other_chat = self.player_games[user_id]
            if other_chat != chat_id:
                try:
                    other_chat_info = await context.bot.get_chat(other_chat)
                    chat_name = other_chat_info.title or f"Чат {other_chat}"
                except:
                    chat_name = f"Чат {other_chat}"
                await query.edit_message_text(f"❌ Вы уже участвуете в игре в другом чате!\nЧат: {chat_name}")
                return
            else:
                # Игрок уже в этой игре - показываем статус
                game = self.games[chat_id]
                max_players = getattr(game, "MAX_PLAYERS", 12)
                
                keyboard = [[InlineKeyboardButton("🎮 Присоединиться", callback_data="welcome_start_game")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"ℹ️ Вы уже участвуете в этой игре!\nИгроков: {len(game.players)}/{max_players}",
                    reply_markup=reply_markup
                )
                return

        # create game if needed
        if chat_id not in self.games:
            self.games[chat_id] = Game(chat_id)
            self.games[chat_id].is_test_mode = self.global_settings.is_test_mode()
            self.night_actions[chat_id] = NightActions(self.games[chat_id])
            self.night_interfaces[chat_id] = NightInterface(self.games[chat_id], self.night_actions[chat_id])

        game = self.games[chat_id]

        if game.phase != GamePhase.WAITING:
            await query.edit_message_text("❌ Игра уже идёт! Дождитесь её окончания.")
            return

        if game.add_player(user_id, username):
            self.player_games[user_id] = chat_id
            max_players = getattr(game, "MAX_PLAYERS", 12)
            
            # Добавляем инлайн кнопку для присоединения других игроков
            keyboard = [[InlineKeyboardButton("🎮 Присоединиться", callback_data="welcome_start_game")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            join_text = f"✅ {username} присоединился к игре!\nИгроков: {len(game.players)}/{max_players}"
            
            # Если это первый игрок, отправляем и закрепляем сообщение
            if len(game.players) == 1:
                message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=join_text,
                    reply_markup=reply_markup
                )
                # Сохраняем ID закрепленного сообщения в игре
                game.pinned_message_id = message.message_id
                
                try:
                    await context.bot.pin_chat_message(
                        chat_id=chat_id,
                        message_id=message.message_id,
                        disable_notification=True
                    )
                except Exception as e:
                    logger.warning(f"Не удалось закрепить сообщение: {e}")
                
                await query.edit_message_text("✅ Вы присоединились к игре! Сообщение о присоединении закреплено в чате.")
            else:
                # Обновляем закрепленное сообщение, если оно существует
                if hasattr(game, 'pinned_message_id') and game.pinned_message_id:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=game.pinned_message_id,
                            text=join_text,
                            reply_markup=reply_markup
                        )
                        await query.edit_message_text("✅ Вы присоединились к игре! Закрепленное сообщение обновлено.")
                    except Exception as e:
                        logger.warning(f"Не удалось обновить закрепленное сообщение: {e}")
                        await query.edit_message_text(join_text, reply_markup=reply_markup)
                else:
                    await query.edit_message_text(join_text, reply_markup=reply_markup)
        else:
            await query.edit_message_text("❌ Не удалось присоединиться к игре. Возможно, вы уже в игре или достигнут лимит игроков.")

    async def status_from_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        chat_id = query.message.chat.id

        if chat_id not in self.games:
            await query.edit_message_text("❌ В этом чате нет активной игры!\nИспользуйте /join чтобы присоединиться.")
            return

        game = self.games[chat_id]

        if game.phase == GamePhase.WAITING:
            min_players = self.global_settings.get_min_players()
            status_text = (
                "⏳ Ожидание игроков...\n\n"
                f"👥 Игроков: {len(game.players)}/{getattr(game, 'MAX_PLAYERS', 12)}\n"
                f"📋 Минимум для начала: {min_players}\n\n"
                "Список игроков:\n"
            )
            for player in game.players.values():
                status_text += f"• {player.username}\n"
            if game.can_start_game():
                status_text += "\n✅ Можно начинать игру!"
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
                f"🎮 Игра идёт\n\n"
                f"📊 Фаза: {phase_names.get(game.phase, 'Неизвестно')}\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых игроков: {len(game.get_alive_players())}\n\n"
                "Живые игроки:\n"
            )
            for p in game.get_alive_players():
                status_text += f"• {p.username}\n"

        await query.edit_message_text(status_text)

    # ---------------- join / leave / status ----------------
    async def join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.full_name or str(user_id)

        # Проверяем, что это группа, а не личные сообщения
        if chat_id == user_id:  # Это личные сообщения
            await update.message.reply_text("❌ Игра доступна только в группах! Добавьте бота в группу и попробуйте там.")
            return

        # already in another game?
        if user_id in self.player_games:
            other_chat = self.player_games[user_id]
            if other_chat != chat_id:
                try:
                    other_chat_info = await context.bot.get_chat(other_chat)
                    chat_name = other_chat_info.title or f"Чат {other_chat}"
                except:
                    chat_name = f"Чат {other_chat}"
                await update.message.reply_text(f"❌ Вы уже участвуете в игре в другом чате!\nЧат: {chat_name}")
                return
            else:
                # Игрок уже в этой игре - показываем статус
                game = self.games[chat_id]
                max_players = getattr(game, "MAX_PLAYERS", 12)
                
                keyboard = [[InlineKeyboardButton("🎮 Присоединиться", callback_data="welcome_start_game")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"ℹ️ Вы уже участвуете в этой игре!\nИгроков: {len(game.players)}/{max_players}",
                    reply_markup=reply_markup
                )
                return

        # create game if needed
        if chat_id not in self.games:
            self.games[chat_id] = Game(chat_id)
            self.games[chat_id].is_test_mode = self.global_settings.is_test_mode()
            self.night_actions[chat_id] = NightActions(self.games[chat_id])
            self.night_interfaces[chat_id] = NightInterface(self.games[chat_id], self.night_actions[chat_id])

        game = self.games[chat_id]

        if game.phase != GamePhase.WAITING:
            await update.message.reply_text("❌ Игра уже идёт! Дождитесь её окончания.")
            return

        if game.add_player(user_id, username):
            self.player_games[user_id] = chat_id
            max_players = getattr(game, "MAX_PLAYERS", 12)
            
            # Добавляем инлайн кнопку для присоединения других игроков
            keyboard = [[InlineKeyboardButton("🎮 Присоединиться", callback_data="welcome_start_game")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            join_text = f"✅ {username} присоединился к игре!\nИгроков: {len(game.players)}/{max_players}"
            
            # Если это первый игрок, отправляем и закрепляем сообщение
            if len(game.players) == 1:
                message = await update.message.reply_text(join_text, reply_markup=reply_markup)
                # Сохраняем ID закрепленного сообщения в игре
                game.pinned_message_id = message.message_id
                
                try:
                    await context.bot.pin_chat_message(
                        chat_id=chat_id,
                        message_id=message.message_id,
                        disable_notification=True
                    )
                except Exception as e:
                    logger.warning(f"Не удалось закрепить сообщение: {e}")
            else:
                # Обновляем закрепленное сообщение, если оно существует
                if hasattr(game, 'pinned_message_id') and game.pinned_message_id:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=game.pinned_message_id,
                            text=join_text,
                            reply_markup=reply_markup
                        )
                        await update.message.reply_text("✅ Вы присоединились к игре! Закрепленное сообщение обновлено.")
                    except Exception as e:
                        logger.warning(f"Не удалось обновить закрепленное сообщение: {e}")
                        await update.message.reply_text(join_text, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(join_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text("❌ Не удалось присоединиться к игре. Возможно, вы уже в игре или достигнут лимит игроков.")

    async def leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            await update.message.reply_text(f"👋 {username} покинул игру.\nИгроков: {len(game.players)}/{getattr(game, 'MAX_PLAYERS', 12)}")
            if not game.can_start_game():
                await update.message.reply_text("⚠️ Игроков стало меньше минимума. Игра не может быть начата.")
        else:
            await update.message.reply_text("❌ Не удалось покинуть игру.")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id

        # Проверяем, что это группа, а не личные сообщения
        if chat_id == update.effective_user.id:
            await update.message.reply_text("❌ Игра доступна только в группах!")
            return

        if chat_id not in self.games:
            await update.message.reply_text("❌ В этом чате нет активной игры!\nИспользуйте /join чтобы присоединиться.")
            return

        game = self.games[chat_id]

        if game.phase == GamePhase.WAITING:
            min_players = self.global_settings.get_min_players()
            status_text = (
                "⏳ Ожидание игроков...\n\n"
                f"👥 Игроков: {len(game.players)}/{getattr(game, 'MAX_PLAYERS', 12)}\n"
                f"📋 Минимум для начала: {min_players}\n\n"
                "Список игроков:\n"
            )
            for player in game.players.values():
                status_text += f"• {player.username}\n"
            if game.can_start_game():
                status_text += "\n✅ Можно начинать игру!"
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
                f"🎮 Игра идёт\n\n"
                f"📊 Фаза: {phase_names.get(game.phase, 'Неизвестно')}\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых игроков: {len(game.get_alive_players())}\n\n"
                "Живые игроки:\n"
            )
            for p in game.get_alive_players():
                status_text += f"• {p.username}\n"

        await update.message.reply_text(status_text)

    # ---------------- starting / ending game ----------------
    async def start_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        # Проверяем, что это группа, а не личные сообщения
        if chat_id == user_id:
            await update.message.reply_text("❌ Игра доступна только в группах!")
            return

        # Проверяем права администратора
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут начинать игру!")
            return

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

        if game.start_game():
            await self.start_night_phase(update, context, game)
        else:
            await update.message.reply_text("❌ Не удалось начать игру!")

    async def end_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут завершать игру!")
            return

        if chat_id not in self.games:
            await update.message.reply_text("❌ Нет активной игры в этом чате!")
            return

        game = self.games[chat_id]

        if game.phase == GamePhase.WAITING:
            await update.message.reply_text("❌ Игра ещё не началась! Используйте /start_game чтобы начать игру.")
            return

        await self._end_game_internal(update, context, game, "Администратор завершил игру")

    async def force_end(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        user_id = update.effective_user.id

        # Проверяем, что команда от создателя бота (можете изменить это условие)
        if user_id != 123456789:  # Замените на ваш user_id
            await update.message.reply_text("❌ Недостаточно прав для выполнения команды!")
            return

        games_count = len(self.games)
        players_count = len(self.player_games)

        # Очищаем все игровые сессии
        self.games.clear()
        self.player_games.clear()
        self.night_actions.clear()
        self.night_interfaces.clear()

        await update.message.reply_text(
            f"🧹 Все игровые сессии очищены!\n\n"
            f"📊 Было завершено игр: {games_count}\n"
            f"👥 Было освобождено игроков: {players_count}"
        )

    async def _end_game_internal(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game, reason: str):
        game.phase = GamePhase.GAME_OVER

        # Открепляем сообщение о присоединении при завершении игры
        if hasattr(game, 'pinned_message_id') and game.pinned_message_id:
            try:
                await context.bot.unpin_chat_message(
                    chat_id=game.chat_id,
                    message_id=game.pinned_message_id
                )
            except Exception as e:
                logger.warning(f"Не удалось открепить сообщение: {e}")

        await update.message.reply_text(
            f"🏁 Игра завершена!\n\n📋 Причина: {reason}\n📊 Статистика игры:\n"
            f"Всего игроков: {len(game.players)}\nРаундов сыграно: {game.current_round}\nФаза: {game.phase.value}"
        )

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
                game.pinned_message_id = None
            except Exception as e:
                logger.warning(f"Не удалось открепить сообщение: {e}")
        
        await update.message.reply_text("🌙 Наступает ночь в лесу...\nВсе звери засыпают, кроме ночных обитателей.\n\n🎭 Распределение ролей завершено!")

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
            wolves_text = "🐺 Волки, познакомьтесь друг с другом:\n" + "\n".join(f"• {w.username}" for w in wolves)
            for wolf in wolves:
                try:
                    await context.bot.send_message(chat_id=wolf.user_id, text=wolves_text)
                except Exception as e:
                    logger.error(f"Не удалось отправить сообщение волку {wolf.user_id}: {e}")

        # меню ночных действий
        await self.send_night_actions_to_players(context, game)

        # Отправляем кнопку просмотра роли игрокам без ночных действий
        await self.send_role_button_to_passive_players(context, game)

        # таймер ночи (запускаем как таск)
        asyncio.create_task(self.night_phase_timer(update, context, game))

    async def night_phase_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        await asyncio.sleep(60)  # первая ночь 60 сек
        if game.phase == GamePhase.NIGHT:
            await self.process_night_phase(update, context, game)
            await self.start_day_phase(update, context, game)

    async def start_day_phase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        game.start_day()

        # Создаем кнопки для дневной фазы
        keyboard = [
            [InlineKeyboardButton("🏁 Завершить обсуждение", callback_data="day_end_discussion")],
            [InlineKeyboardButton("🐺 Выбрать волка", callback_data="day_choose_wolf")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "☀️ Восходит солнце! Лес просыпается.\n\n"
            "🌲 Начинается дневное обсуждение.\n"
            "У вас есть 5 минут, чтобы обсудить ночные события и решить, кого изгнать.\n\n"
            "Используйте кнопки ниже для управления фазой:",
            reply_markup=reply_markup
        )
        asyncio.create_task(self.day_phase_timer(update, context, game))

    async def day_phase_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        await asyncio.sleep(300)
        if game.phase == GamePhase.DAY:
            await self.start_voting_phase(update, context, game)

    async def start_voting_phase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        game.start_voting()

        alive_players = game.get_alive_players()
        if len(alive_players) < 2:
            await self._end_game_internal(update, context, game, "Недостаточно игроков для голосования")
            return

        # Отправляем уведомление в общий чат
        chat_message = (
            "🗳️ Время голосования за изгнание!\n\n"
            "У вас есть 2 минуты, чтобы проголосовать в личных сообщениях за изгнание зверя из леса.\n\n"
            "📱 Проверьте личные сообщения с ботом для голосования."
        )
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(chat_message)
        elif hasattr(update, 'callback_query') and update.callback_query:
            await context.bot.send_message(chat_id=game.chat_id, text=chat_message)

        # Отправляем меню голосования каждому живому игроку в личку
        for voter in alive_players:
            keyboard = [[InlineKeyboardButton(f"🗳️ {p.username}", callback_data=f"vote_{p.user_id}")] for p in alive_players]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await context.bot.send_message(
                    chat_id=voter.user_id,
                    text=(
                        "🗳️ Время голосования за изгнание!\n\n"
                        "Выберите игрока, которого вы хотите изгнать из леса.\n"
                        "У вас есть 2 минуты на голосование:"
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
                await context.bot.send_message(chat_id=game.chat_id, text="❌ Недостаточно игроков для голосования!")
            return

        # Отправляем уведомление в общий чат
        chat_message = (
            "🐺 Голосование 'Кто волк?' началось!\n\n"
            "У вас есть 2 минуты, чтобы проголосовать в личных сообщениях за того, кого вы подозреваете в том, что он волк.\n"
            "Этот игрок НЕ будет изгнан, это просто попытка выявить волка!\n\n"
            "📱 Проверьте личные сообщения с ботом для голосования."
        )
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(chat_message)
        elif hasattr(update, 'callback_query') and update.callback_query:
            await context.bot.send_message(chat_id=game.chat_id, text=chat_message)

        # Отправляем меню голосования каждому живому игроку в личку
        for voter in alive_players:
            keyboard = [[InlineKeyboardButton(f"🐺 {p.username}", callback_data=f"wolf_vote_{p.user_id}")] for p in alive_players]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await context.bot.send_message(
                    chat_id=voter.user_id,
                    text=(
                        "🐺 Голосование 'Кто волк?'!\n\n"
                        "Выберите игрока, которого вы подозреваете в том, что он волк.\n"
                        "Этот игрок НЕ будет изгнан - это просто попытка выявить волка!\n\n"
                        "У вас есть 2 минуты на голосование:"
                    ),
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Не удалось отправить меню голосования игроку {voter.user_id}: {e}")

        # Сохраняем информацию о количестве игроков для проверки досрочного завершения
        game.total_voters = len(alive_players)
        game.voting_type = "wolf"  # Помечаем тип голосования
        
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
                        text="⚡ Все игроки проголосовали! Голосование завершено досрочно."
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
        for _ in range(120):  # Проверяем каждую секунду в течение 2 минут
            await asyncio.sleep(1)
            
            # Проверяем, все ли проголосовали
            if game.phase == GamePhase.VOTING and hasattr(game, 'total_voters'):
                if len(game.votes) >= game.total_voters:
                    # Все проголосовали - завершаем досрочно
                    await context.bot.send_message(
                        chat_id=game.chat_id, 
                        text="⚡ Все игроки проголосовали! Голосование завершено досрочно."
                    )
                    await self.process_voting_results(update, context, game)
                    return
            
            # Если игра завершилась или фаза изменилась - выходим
            if game.phase != GamePhase.VOTING:
                return
        
        # Время вышло
        if game.phase == GamePhase.VOTING:
            await self.process_voting_results(update, context, game)

    async def process_voting_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        exiled_player = game.process_voting()
        if exiled_player:
            await update.message.reply_text(f"🚫 {exiled_player.username} изгнан из леса!\nЕго роль: {self.get_role_info(exiled_player.role)['name']}")
        else:
            await update.message.reply_text("🤝 Ничья в голосовании! Никто не изгнан.")

        # Очищаем атрибуты голосования
        if hasattr(game, 'total_voters'):
            delattr(game, 'total_voters')
        if hasattr(game, 'voting_type'):
            delattr(game, 'voting_type')

        winner = game.check_game_end()
        if winner:
            await self.end_game_winner(update, context, game, winner)
        else:
            await self.start_new_night(update, context, game)

    async def process_wolf_voting_results(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Обрабатывает результаты голосования за волка"""
        if not game.votes:
            await context.bot.send_message(
                chat_id=game.chat_id,
                text="🤷‍♂️ Никто не проголосовал в голосовании 'Кто волк?'!"
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
                              f"🐺 {suspect.username} получил больше всего голосов ({votes}) и действительно оказался ВОЛКОМ!\n"
                              f"👏 Жители угадали!")
            else:
                result_text = (f"🎯 Результат голосования 'Кто волк?':\n\n"
                              f"🐰 {suspect.username} получил больше всего голосов ({votes}), но оказался {self.get_role_info(suspect.role)['name']}!\n"
                              f"😅 Жители ошиблись!")

        await context.bot.send_message(chat_id=game.chat_id, text=result_text)
        
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
            [InlineKeyboardButton("🐺 Выбрать волка", callback_data="day_choose_wolf")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=game.chat_id,
            text="☀️ Продолжается дневное обсуждение.\nИспользуйте кнопки ниже для управления фазой:",
            reply_markup=reply_markup
        )

    async def start_new_night(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        await self.start_night_phase(update, context, game)

    async def end_game_winner(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game, winner: Optional[Team] = None):
        game.phase = GamePhase.GAME_OVER
        
        # Открепляем сообщение о присоединении при завершении игры
        if hasattr(game, 'pinned_message_id') and game.pinned_message_id:
            try:
                await context.bot.unpin_chat_message(
                    chat_id=game.chat_id,
                    message_id=game.pinned_message_id
                )
            except Exception as e:
                logger.warning(f"Не удалось открепить сообщение: {e}")
        
        if winner:
            winner_text = "🏆 Травоядные победили!" if winner == Team.HERBIVORES else "🏆 Хищники победили!"
            await update.message.reply_text(f"🎉 Игра окончена! {winner_text}\n\n📊 Статистика игры:\nВсего игроков: {len(game.players)}\nРаундов сыграно: {game.current_round}")
        else:
            await update.message.reply_text("🏁 Игра окончена!\nНедостаточно игроков для продолжения.")

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

    # ---------------- callbacks: voting, night actions, welcome buttons ----------------
    async def handle_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        
        # Находим игру по игроку
        if user_id not in self.player_games:
            await query.edit_message_text("❌ Вы не участвуете в игре!")
            return

        chat_id = self.player_games[user_id]
        if chat_id not in self.games:
            await query.edit_message_text("❌ Игра не найдена!")
            return

        game = self.games[chat_id]
        if game.phase != GamePhase.VOTING:
            await query.edit_message_text("❌ Голосование уже завершено!")
            return

        target_id = int(query.data.split('_', 1)[1])
        if game.vote(user_id, target_id):
            target_player = game.players[target_id]
            await query.edit_message_text(f"✅ Ваш голос зарегистрирован!\nВы проголосовали за изгнание: {target_player.username}\n\n🕐 Ожидайте результатов голосования...")
            
            # Проверяем, все ли проголосовали (только для обычного голосования)
            if hasattr(game, 'total_voters') and hasattr(game, 'voting_type') and game.voting_type == "exile":
                if len(game.votes) >= game.total_voters:
                    # Все проголосовали - завершаем досрочно
                    asyncio.create_task(self.complete_exile_voting_early(context, game, update))
        else:
            await query.edit_message_text("❌ Не удалось зарегистрировать голос!")

    async def handle_night_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if user_id in self.player_games:
            chat_id = self.player_games[user_id]
            if chat_id in self.night_interfaces:
                await self.night_interfaces[chat_id].handle_night_action(update, context)

    async def handle_welcome_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == "welcome_start_game":
            await self.join_from_callback(query, context)
        elif query.data == "welcome_rules":
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="welcome_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📖 Правила игры 'Лесная Возня':\n\n"
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
        elif query.data == "welcome_back":
            # Возвращаемся к приветственному сообщению
            keyboard = [
                [InlineKeyboardButton("🎮 Начать игру", callback_data="welcome_start_game")],
                [InlineKeyboardButton("📖 Правила игры", callback_data="welcome_rules")],
                [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            welcome_text = (
                "🌲 *Добро пожаловать в Лесную Возню!* 🌲\n\n"
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

    async def handle_day_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает действия дневной фазы"""
        query = update.callback_query
        await query.answer()

        chat_id = query.message.chat.id
        user_id = query.from_user.id

        # Проверяем права администратора
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            if chat_member.status not in ['creator', 'administrator']:
                await query.edit_message_text("❌ Только администраторы могут управлять игрой!")
                return
        except Exception:
            await query.edit_message_text("❌ Ошибка проверки прав!")
            return

        if chat_id not in self.games:
            await query.edit_message_text("❌ В этом чате нет активной игры!")
            return

        game = self.games[chat_id]

        if query.data == "day_end_discussion":
            if game.phase != GamePhase.DAY:
                await query.edit_message_text("❌ Сейчас не время обсуждения!")
                return

            await query.edit_message_text("🏁 Администратор завершил обсуждение досрочно!")
            await self.start_voting_phase(update, context, game)

        elif query.data == "day_choose_wolf":
            if game.phase != GamePhase.DAY:
                await query.edit_message_text("❌ Голосование за волка доступно только в дневной фазе!")
                return

            await query.edit_message_text("🐺 Администратор инициировал голосование 'Кто волк?'!")
            await self.start_wolf_voting_phase(update, context, game)

    # ---------------- settings UI (basic, non-persistent) ----------------
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        chat_id = query.message.chat.id

        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await query.edit_message_text("❌ Только администраторы могут изменять настройки!")
            return

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
            [InlineKeyboardButton("🌙 Ночь: 60с", callback_data="timer_night_60")],
            [InlineKeyboardButton("☀️ День: 5мин", callback_data="timer_day_300")],
            [InlineKeyboardButton("🗳️ Голосование: 2мин", callback_data="timer_vote_120")],
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
            result_text += "ℹ️ Создайте игру командой /join для применения настроек"

        await query.edit_message_text(result_text)

    async def show_global_settings(self, query, context):
        """Показывает глобальные настройки бота"""
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к настройкам", callback_data="settings_back")]
        ]
        
        await query.edit_message_text(
            self.global_settings.get_settings_summary(),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_settings_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возвращает к главному меню настроек"""
        query = update.callback_query
        await query.answer()
        
        chat_id = query.message.chat.id
        user_id = query.from_user.id

        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await query.edit_message_text("❌ Только администраторы могут изменять настройки!")
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

        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def reset_game_stats(self, query, context, game: Game):
        if game.phase != GamePhase.WAITING:
            await query.edit_message_text("❌ Нельзя сбросить статистику во время игры! Дождитесь окончания игры.")
            return
        game.current_round = 0
        game.game_start_time = None
        game.phase_end_time = None
        await query.edit_message_text("📊 Статистика игры сброшена!\n\n✅ Раунд: 0\n✅ Время начала: сброшено\n✅ Таймеры: сброшены")

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

    async def handle_wolf_voting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает голосование за волка"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        
        # Находим игру по игроку
        if user_id not in self.player_games:
            await query.edit_message_text("❌ Вы не участвуете в игре!")
            return

        chat_id = self.player_games[user_id]
        if chat_id not in self.games:
            await query.edit_message_text("❌ Игра не найдена!")
            return

        game = self.games[chat_id]
        if game.phase != GamePhase.VOTING:
            await query.edit_message_text("❌ Голосование уже завершено!")
            return

        data = query.data.split('_')
        if len(data) != 3:
            await query.edit_message_text("❌ Ошибка данных!")
            return

        target_id = int(data[2])
        
        # Проверяем, что голосующий жив и в игре
        voter = game.players.get(user_id)
        if not voter or not voter.is_alive:
            await query.edit_message_text("❌ Вы не можете голосовать!")
            return

        if game.vote(user_id, target_id):
            target_player = game.players[target_id]
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

    async def complete_exile_voting_early(self, context: ContextTypes.DEFAULT_TYPE, game: Game, update: Update):
        """Завершает голосование за изгнание досрочно"""
        await asyncio.sleep(0.5)  # Небольшая задержка чтобы все голоса успели обработаться
        if game.phase == GamePhase.VOTING and hasattr(game, 'voting_type') and game.voting_type == "exile":
            await context.bot.send_message(
                chat_id=game.chat_id, 
                text="⚡ Все игроки проголосовали! Голосование за изгнание завершено досрочно."
            )
            await self.process_voting_results(update, context, game)

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
                "name": "🦦 Бобёр",
                "description": "Вы травоядный! Вы можете возвращать украденные запасы другим зверям."
            }
        }
        return role_info.get(role, {"name": "Неизвестно", "description": "Роль не определена"})

    # ---------------- bot lifecycle: setup and run ----------------
    async def setup_bot_commands(self, application: Application):
        commands = [
            BotCommand("start", "🌲 Приветствие и начало работы"),
            BotCommand("rules", "📖 Правила игры"),
            BotCommand("join", "✅ Присоединиться к игре (только группы)"),
            BotCommand("leave", "👋 Покинуть игру"),
            BotCommand("start_game", "🎮 Начать игру (админы)"),
            BotCommand("end_game", "🏁 Завершить игру (админы)"),
            BotCommand("force_end", "⛔ Принудительно завершить (админы)"),
            BotCommand("clear_all_games", "🧹 Очистить все игры (супер-админ)"),
            BotCommand("settings", "⚙️ Настройки игры (админы)"),
            BotCommand("status", "📊 Статус текущей игры"),
            BotCommand("test_mode", "🧪 Включить/выключить тестовый режим (админы)"), # Добавлена команда для тестового режима
        ]
        try:
            await application.bot.set_my_commands(commands)
            logger.info("Bot commands set.")
        except Exception as ex:
            logger.error(f"Failed to set bot commands: {ex}")

    def run(self):
        application = Application.builder().token(BOT_TOKEN).build()

        # зарегистрируем обработчики
        application.add_handler(CommandHandler("start", self.welcome_message))
        application.add_handler(CommandHandler("rules", self.rules))
        application.add_handler(CommandHandler("join", self.join))
        application.add_handler(CommandHandler("leave", self.leave))
        application.add_handler(CommandHandler("start_game", self.start_game))
        application.add_handler(CommandHandler("end_game", self.end_game))
        application.add_handler(CommandHandler("force_end", self.force_end))
        application.add_handler(CommandHandler("clear_all_games", self.clear_all_games))
        application.add_handler(CommandHandler("settings", self.settings))
        application.add_handler(CommandHandler("status", self.status))
        application.add_handler(CommandHandler("test_mode", self.handle_test_mode_command)) # Обработчик команды test_mode

        # callbacks
        application.add_handler(CallbackQueryHandler(self.handle_vote, pattern=r"^vote_"))
        application.add_handler(CallbackQueryHandler(self.handle_night_action, pattern=r"^night_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^settings_"))
        application.add_handler(CallbackQueryHandler(self.handle_welcome_buttons, pattern=r"^welcome_"))
        application.add_handler(CallbackQueryHandler(self.handle_day_actions, pattern=r"^day_"))
        application.add_handler(CallbackQueryHandler(self.handle_wolf_voting, pattern=r"^wolf_vote_"))
        # settings submenu/back handlers
        application.add_handler(CallbackQueryHandler(self.show_timer_settings, pattern=r"^timer_"))
        application.add_handler(CallbackQueryHandler(self.show_role_settings, pattern=r"^role_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings_back, pattern=r"^settings_back$"))
        application.add_handler(CallbackQueryHandler(self.handle_welcome_buttons, pattern=r"^welcome_"))

        # Установка команд после старта бота
        async def post_init(application):
            await self.setup_bot_commands(application)

        application.post_init = post_init

        # Запуск бота (blocking call)
        application.run_polling()

    async def handle_test_mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /test_mode для включения/выключения тестового режима."""
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
            result_text += "ℹ️ Создайте игру командой /join для применения настроек"

        await update.message.reply_text(result_text)


if __name__ == "__main__":
    bot = ForestMafiaBot()
    bot.run()