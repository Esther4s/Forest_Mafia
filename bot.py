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
from config import BOT_TOKEN, MIN_PLAYERS  # ваши настройки
from night_actions import NightActions
from night_interface import NightInterface

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
            f"👥 Для игры нужно минимум {MIN_PLAYERS} игроков\n"
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

    # ---------------- join / leave / status ----------------
    async def join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.full_name or str(user_id)

        # already in another game?
        if user_id in self.player_games:
            other_chat = self.player_games[user_id]
            if other_chat != chat_id:
                await update.message.reply_text("❌ Вы уже участвуете в игре в другом чате!")
                return

        # create game if needed
        if chat_id not in self.games:
            self.games[chat_id] = Game(chat_id)
            self.night_actions[chat_id] = NightActions(self.games[chat_id])
            self.night_interfaces[chat_id] = NightInterface(self.games[chat_id], self.night_actions[chat_id])

        game = self.games[chat_id]

        if game.phase != GamePhase.WAITING:
            await update.message.reply_text("❌ Игра уже идёт! Дождитесь её окончания.")
            return

        if game.add_player(user_id, username):
            self.player_games[user_id] = chat_id
            max_players = getattr(game, "MAX_PLAYERS", 12)
            await update.message.reply_text(f"✅ {username} присоединился к игре!\nИгроков: {len(game.players)}/{max_players}")
        else:
            await update.message.reply_text("❌ Не удалось присоединиться к игре. Возможно, вы уже в игре или достигнут лимит игроков.")

    async def leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.full_name or str(user_id)

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

        if chat_id not in self.games:
            await update.message.reply_text("❌ В этом чате нет активной игры!\nИспользуйте /join чтобы присоединиться.")
            return

        game = self.games[chat_id]

        if game.phase == GamePhase.WAITING:
            status_text = (
                "⏳ Ожидание игроков...\n\n"
                f"👥 Игроков: {len(game.players)}/{getattr(game, 'MAX_PLAYERS', 12)}\n"
                f"📋 Минимум для начала: {MIN_PLAYERS}\n\n"
                "Список игроков:\n"
            )
            for player in game.players.values():
                status_text += f"• {player.username}\n"
            if game.can_start_game():
                status_text += "\n✅ Можно начинать игру!"
            else:
                status_text += f"\n⏳ Нужно ещё {max(0, MIN_PLAYERS - len(game.players))} игроков"
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

        # Проверяем права администратора
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут начинать игру!")
            return

        if chat_id not in self.games:
            await update.message.reply_text("❌ Нет активной игры в этом чате!")
            return

        game = self.games[chat_id]

        if not game.can_start_game():
            await update.message.reply_text(f"❌ Недостаточно игроков! Нужно минимум {MIN_PLAYERS} игроков.")
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

        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут принудительно завершать игру!")
            return

        if chat_id not in self.games:
            await update.message.reply_text("❌ Нет активной игры в этом чате!")
            return

        game = self.games[chat_id]
        await self._end_game_internal(update, context, game, "Администратор принудительно завершил игру")

    async def _end_game_internal(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game, reason: str):
        game.phase = GamePhase.GAME_OVER

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

        # таймер ночи (запускаем как таск)
        asyncio.create_task(self.night_phase_timer(update, context, game))

    async def night_phase_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        await asyncio.sleep(60)  # первая ночь 60 сек
        if game.phase == GamePhase.NIGHT:
            await self.process_night_phase(update, context, game)
            await self.start_day_phase(update, context, game)

    async def start_day_phase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        game.start_day()
        await update.message.reply_text("☀️ Восходит солнце! Лес просыпается.\n\n🌲 Начинается дневное обсуждение.\nУ вас есть 5 минут, чтобы обсудить ночные события и решить, кого изгнать.")
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

        keyboard = [[InlineKeyboardButton(f"🗳️ {p.username}", callback_data=f"vote_{p.user_id}")] for p in alive_players]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🗳️ Время голосования!\nУ вас есть 2 минуты, чтобы проголосовать за изгнание зверя из леса.\nВыберите того, кого хотите изгнать:",
            reply_markup=reply_markup
        )

        asyncio.create_task(self.voting_timer(update, context, game))

    async def voting_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        await asyncio.sleep(120)
        if game.phase == GamePhase.VOTING:
            await self.process_voting_results(update, context, game)

    async def process_voting_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        exiled_player = game.process_voting()
        if exiled_player:
            await update.message.reply_text(f"🚫 {exiled_player.username} изгнан из леса!\nЕго роль: {self.get_role_info(exiled_player.role)['name']}")
        else:
            await update.message.reply_text("🤝 Ничья в голосовании! Никто не изгнан.")

        winner = game.check_game_end()
        if winner:
            await self.end_game_winner(update, context, game, winner)
        else:
            await self.start_new_night(update, context, game)

    async def start_new_night(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        await self.start_night_phase(update, context, game)

    async def end_game_winner(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game, winner: Optional[Team] = None):
        game.phase = GamePhase.GAME_OVER
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
        chat_id = query.message.chat.id

        if chat_id not in self.games:
            await query.edit_message_text("❌ В чате нет активной игры.")
            return

        game = self.games[chat_id]
        if game.phase != GamePhase.VOTING:
            await query.edit_message_text("❌ Голосование уже завершено!")
            return

        target_id = int(query.data.split('_', 1)[1])
        if game.vote(user_id, target_id):
            await query.edit_message_text("✅ Ваш голос зарегистрирован!")
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
            # simulate a /join for the user in this chat
            await self.join(update, context)
        elif query.data == "welcome_rules":
            await self.rules(update, context)
        elif query.data == "welcome_status":
            await self.status(update, context)

    # ---------------- settings UI (basic, non-persistent) ----------------
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Только администраторы могут изменять настройки!")
            return

        if chat_id not in self.games:
            await update.message.reply_text("❌ В этом чате нет активной игры!\nИспользуйте /join чтобы присоединиться.")
            return

        keyboard = [
            [InlineKeyboardButton("⏱️ Изменить таймеры", callback_data="settings_timers")],
            [InlineKeyboardButton("🎭 Изменить распределение ролей", callback_data="settings_roles")],
            [InlineKeyboardButton("📊 Сбросить статистику", callback_data="settings_reset")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="settings_close")]
        ]
        await update.message.reply_text("⚙️ Настройки игры\n\nВыберите, что хотите изменить:", reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        chat_id = query.message.chat.id

        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await query.edit_message_text("❌ Только администраторы могут изменять настройки!")
            return

        if chat_id not in self.games:
            await query.edit_message_text("❌ В этом чате нет активной игре!")
            return

        game = self.games[chat_id]
        if query.data == "settings_timers":
            await self.show_timer_settings(query, context, game)
        elif query.data == "settings_roles":
            await self.show_role_settings(query, context, game)
        elif query.data == "settings_reset":
            await self.reset_game_stats(query, context, game)
        elif query.data == "settings_close":
            await query.edit_message_text("⚙️ Настройки закрыты")

    async def show_timer_settings(self, query, context, game: Game):
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

    async def show_role_settings(self, query, context, game: Game):
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

    # ---------------- helper ----------------
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
            BotCommand("join", "✅ Присоединиться к игре"),
            BotCommand("leave", "👋 Покинуть игру"),
            BotCommand("start_game", "🎮 Начать игру (админы)"),
            BotCommand("end_game", "🏁 Завершить игру (админы)"),
            BotCommand("force_end", "⛔ Принудительно завершить (админы)"),
            BotCommand("settings", "⚙️ Настройки игры (админы)"),
            BotCommand("status", "📊 Статус текущей игры"),
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
        application.add_handler(CommandHandler("settings", self.settings))
        application.add_handler(CommandHandler("status", self.status))

        # callbacks
        application.add_handler(CallbackQueryHandler(self.handle_vote, pattern=r"^vote_"))
        application.add_handler(CallbackQueryHandler(self.handle_night_action, pattern=r"^night_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern=r"^settings_"))
        application.add_handler(CallbackQueryHandler(self.handle_welcome_buttons, pattern=r"^welcome_"))
        # settings submenu/back handlers
        application.add_handler(CallbackQueryHandler(self.show_timer_settings, pattern=r"^timer_"))
        application.add_handler(CallbackQueryHandler(self.show_role_settings, pattern=r"^role_"))
        application.add_handler(CallbackQueryHandler(self.reset_game_stats, pattern=r"^settings_reset$"))
        application.add_handler(CallbackQueryHandler(self.handle_welcome_buttons, pattern=r"^welcome_"))

        # отложенная установка команд через JobQueue (будет выполнено после старта)
        def schedule_set_commands(context):
            # контекст — JobQueueContext, внутри него запускаем coro
            asyncio.create_task(self.setup_bot_commands(application))

        try:
            application.job_queue.run_once(schedule_set_commands, when=1)
        except Exception as e:
            logger.warning(f"Не удалось запланировать установку команд через JobQueue: {e}")
            # попробуем вызвать сразу (без loop) — безопасно, если бот ещё не стартовал, будет поймано
            asyncio.create_task(self.setup_bot_commands(application))

        # Запуск бота (blocking call)
        application.run_polling()


if __name__ == "__main__":
    bot = ForestMafiaBot()
    bot.run()
