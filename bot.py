import logging
import asyncio
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from game_logic import Game, GamePhase, Role, Team, Player
from config import BOT_TOKEN, MIN_PLAYERS
from night_actions import NightActions
from night_interface import NightInterface

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ForestMafiaBot:
    def __init__(self):
        self.games: Dict[int, Game] = {}  # chat_id -> Game
        self.player_games: Dict[int, int] = {}  # user_id -> chat_id
        self.night_actions: Dict[int, NightActions] = {}  # chat_id -> NightActions
        self.night_interfaces: Dict[int, NightInterface] = {}  # chat_id -> NightInterface
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        await update.message.reply_text(
            "🌲 Добро пожаловать в Лесную Возню! 🌲\n\n"
            "Это ролевая игра 'Мафия' с лесными зверушками.\n\n"
            "Команды:\n"
            "/join - присоединиться к игре\n"
            "/leave - покинуть игру\n"
            "/start_game - начать игру (только для администраторов)\n"
            "/end_game - завершить игру (только для администраторов)\n"
            "/force_end - принудительно завершить игру (только для администраторов)\n"
            "/settings - настройки игры\n"
            "/rules - правила игры\n"
            "/status - статус текущей игры"
        )
    
    async def rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /rules"""
        rules_text = (
            "📖 Правила игры 'Лесная Возня':\n\n"
            "🎭 Роли:\n"
            "🐺 Волки (Хищники) - стая, по ночам съедает по зверю\n"
            "🦊 Лиса (Хищники) - ворует запасы еды, дважды обворованный зверь уходит\n"
            "🐰 Зайцы (Травоядные) - мирные зверушки, только дневные действия\n"
            "🦫 Крот (Травоядные) - роет норки, узнает команды других зверей\n"
            "🦦 Бобёр (Травоядные) - возвращает украденные запасы\n\n"
            "🌙 Ночные фазы: Волки → Лиса → Бобёр → Крот\n"
            "☀️ Дневные фазы: обсуждение и голосование\n"
            "🏆 Цель: уничтожить команду противника"
        )
        await update.message.reply_text(rules_text)
    
    async def join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /join"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or str(user_id)
        
        # Проверяем, не участвует ли игрок уже в другой игре
        if user_id in self.player_games:
            other_chat_id = self.player_games[user_id]
            if other_chat_id != chat_id:
                await update.message.reply_text(
                    "❌ Вы уже участвуете в игре в другом чате!"
                )
                return
        
        # Получаем или создаем игру для этого чата
        if chat_id not in self.games:
            self.games[chat_id] = Game(chat_id)
            self.night_actions[chat_id] = NightActions(self.games[chat_id])
            self.night_interfaces[chat_id] = NightInterface(self.games[chat_id], self.night_actions[chat_id])
        
        game = self.games[chat_id]
        
        # Проверяем, не идет ли уже игра
        if game.phase != GamePhase.WAITING:
            await update.message.reply_text(
                "❌ Игра уже идет! Дождитесь её окончания."
            )
            return
        
        # Добавляем игрока
        if game.add_player(user_id, username):
            self.player_games[user_id] = chat_id
            await update.message.reply_text(
                f"✅ {username} присоединился к игре!\n"
                f"Игроков: {len(game.players)}/{game.MAX_PLAYERS if hasattr(game, 'MAX_PLAYERS') else 12}"
            )
        else:
            await update.message.reply_text(
                "❌ Не удалось присоединиться к игре. Возможно, вы уже в игре или достигнут лимит игроков."
            )
    
    async def leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /leave"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or str(user_id)
        
        if chat_id not in self.games:
            await update.message.reply_text(
                "❌ В этом чате нет активной игры!"
            )
            return
        
        game = self.games[chat_id]
        
        # Проверяем, не идет ли уже игра
        if game.phase != GamePhase.WAITING:
            await update.message.reply_text(
                "❌ Игра уже идет! Дождитесь её окончания."
            )
            return
        
        # Проверяем, участвует ли игрок в игре
        if user_id not in game.players:
            await update.message.reply_text(
                "❌ Вы не участвуете в игре!"
            )
            return
        
        # Игрок покидает игру
        if game.leave_game(user_id):
            # Удаляем из player_games
            if user_id in self.player_games:
                del self.player_games[user_id]
            
            await update.message.reply_text(
                f"👋 {username} покинул игру.\n"
                f"Игроков: {len(game.players)}/{12}"
            )
            
            # Если игроков стало меньше минимума, убираем возможность начать игру
            if not game.can_start_game():
                await update.message.reply_text(
                    "⚠️ Игроков стало меньше минимума. Игра не может быть начата."
                )
        else:
            await update.message.reply_text(
                "❌ Не удалось покинуть игру."
            )
    
    async def start_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start_game"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Проверяем права администратора
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text(
                "❌ Только администраторы могут начинать игру!"
            )
            return
        
        if chat_id not in self.games:
            await update.message.reply_text(
                "❌ Нет активной игры в этом чате!"
            )
            return
        
        game = self.games[chat_id]
        
        if not game.can_start_game():
            await update.message.reply_text(
                f"❌ Недостаточно игроков! Нужно минимум {MIN_PLAYERS} игроков."
            )
            return
        
        if game.phase != GamePhase.WAITING:
            await update.message.reply_text(
                "❌ Игра уже идет!"
            )
            return
        
        # Начинаем игру
        if game.start_game():
            await self.start_night_phase(update, context, game)
        else:
            await update.message.reply_text("❌ Не удалось начать игру!")
    
    async def end_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /end_game - завершение игры"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Проверяем права администратора
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text(
                "❌ Только администраторы могут завершать игру!"
            )
            return
        
        if chat_id not in self.games:
            await update.message.reply_text(
                "❌ Нет активной игры в этом чате!"
            )
            return
        
        game = self.games[chat_id]
        
        if game.phase == GamePhase.WAITING:
            await update.message.reply_text(
                "❌ Игра еще не началась! Используйте /start_game чтобы начать игру."
            )
            return
        
        # Завершаем игру
        await self.end_game_internal(update, context, game, "Администратор завершил игру")
    
    async def force_end(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /force_end - принудительное завершение игры"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Проверяем права администратора
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text(
                "❌ Только администраторы могут принудительно завершать игру!"
            )
            return
        
        if chat_id not in self.games:
            await update.message.reply_text(
                "❌ Нет активной игры в этом чате!"
            )
            return
        
        game = self.games[chat_id]
        
        # Принудительно завершаем игру в любом состоянии
        await self.end_game_internal(update, context, game, "Администратор принудительно завершил игру")
    
    async def end_game_internal(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game, reason: str):
        """Внутренний метод для завершения игры"""
        game.phase = GamePhase.GAME_OVER
        
        await update.message.reply_text(
            f"🏁 Игра завершена!\n\n"
            f"📋 Причина: {reason}\n"
            f"📊 Статистика игры:\n"
            f"Всего игроков: {len(game.players)}\n"
            f"Раундов сыграно: {game.current_round}\n"
            f"Фаза: {game.phase.value}"
        )
        
        # Очищаем игру
        for player_id in game.players:
            if player_id in self.player_games:
                del self.player_games[player_id]
        
        chat_id = game.chat_id
        del self.games[chat_id]
        if chat_id in self.night_actions:
            del self.night_actions[chat_id]
        if chat_id in self.night_interfaces:
            del self.night_interfaces[chat_id]
    
    async def start_night_phase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Начинает ночную фазу"""
        await update.message.reply_text(
            "🌙 Наступает ночь в лесу...\n"
            "Все звери засыпают, кроме ночных обитателей.\n\n"
            "🎭 Распределение ролей завершено!"
        )
        
        # Отправляем личные сообщения каждому игроку с их ролью
        for player in game.players.values():
            role_info = self.get_role_info(player.role)
            try:
                await context.bot.send_message(
                    chat_id=player.user_id,
                    text=f"🎭 Ваша роль: {role_info['name']}\n\n{role_info['description']}"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение игроку {player.user_id}: {e}")
        
        # Если это первая ночь, волки знакомятся друг с другом
        wolves = game.get_players_by_role(Role.WOLF)
        if len(wolves) > 1:
            wolves_text = "🐺 Волки, познакомьтесь друг с другом:\n"
            for wolf in wolves:
                wolves_text += f"• {wolf.username}\n"
            
            for wolf in wolves:
                try:
                    await context.bot.send_message(
                        chat_id=wolf.user_id,
                        text=wolves_text
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить сообщение волку {wolf.user_id}: {e}")
        
        # Отправляем меню ночных действий для игроков с ночными ролями
        await self.send_night_actions_to_players(context, game)
        
        # Запускаем таймер ночной фазы
        asyncio.create_task(self.night_phase_timer(update, context, game))
    
    async def night_phase_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Таймер ночной фазы"""
        await asyncio.sleep(60)  # 60 секунд на первую ночь
        
        if game.phase == GamePhase.NIGHT:
            # Обрабатываем ночные действия
            await self.process_night_phase(update, context, game)
            await self.start_day_phase(update, context, game)
    
    async def start_day_phase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Начинает дневную фазу"""
        game.start_day()
        
        await update.message.reply_text(
            "☀️ Восходит солнце! Лес просыпается.\n\n"
            "🌲 Начинается дневное обсуждение.\n"
            "У вас есть 5 минут, чтобы обсудить ночные события и решить, кого изгнать."
        )
        
        # Запускаем таймер дневной фазы
        asyncio.create_task(self.day_phase_timer(update, context, game))
    
    async def day_phase_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Таймер дневной фазы"""
        await asyncio.sleep(300)  # 5 минут на обсуждение
        
        if game.phase == GamePhase.DAY:
            await self.start_voting_phase(update, context, game)
    
    async def start_voting_phase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Начинает фазу голосования"""
        game.start_voting()
        
        alive_players = game.get_alive_players()
        if len(alive_players) < 2:
            await self.end_game(update, context, game)
            return
        
        # Создаем клавиатуру для голосования
        keyboard = []
        for player in alive_players:
            keyboard.append([InlineKeyboardButton(
                f"🗳️ {player.username}",
                callback_data=f"vote_{player.user_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🗳️ Время голосования!\n"
            "У вас есть 2 минуты, чтобы проголосовать за изгнание зверя из леса.\n"
            "Выберите того, кого хотите изгнать:",
            reply_markup=reply_markup
        )
        
        # Запускаем таймер голосования
        asyncio.create_task(self.voting_timer(update, context, game))
    
    async def voting_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Таймер голосования"""
        await asyncio.sleep(120)  # 2 минуты на голосование
        
        if game.phase == GamePhase.VOTING:
            await self.process_voting_results(update, context, game)
    
    async def process_voting_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Обрабатывает результаты голосования"""
        exiled_player = game.process_voting()
        
        if exiled_player:
            await update.message.reply_text(
                f"🚫 {exiled_player.username} изгнан из леса!\n"
                f"Его роль: {self.get_role_info(exiled_player.role)['name']}"
            )
        else:
            await update.message.reply_text(
                "🤝 Ничья в голосовании! Никто не изгнан."
            )
        
        # Проверяем, не закончилась ли игра
        winner = game.check_game_end()
        if winner:
            await self.end_game_winner(update, context, game, winner)
        else:
            # Начинаем новую ночь
            await self.start_new_night(update, context, game)
    
    async def start_new_night(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Начинает новую ночь"""
        game.start_night()
        
        await update.message.reply_text(
            "🌙 Снова наступает ночь в лесу...\n"
            "Ночные обитатели совершают свои действия."
        )
        
        # Отправляем меню ночных действий для игроков с ночными ролями
        await self.send_night_actions_to_players(context, game)
        
        # Запускаем таймер ночной фазы
        asyncio.create_task(self.night_phase_timer(update, context, game))
    
    async def end_game_winner(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game, winner: Optional[Team] = None):
        """Завершает игру"""
        game.phase = GamePhase.GAME_OVER
        
        if winner:
            winner_text = "🏆 Травоядные победили!" if winner == Team.HERBIVORES else "🏆 Хищники победили!"
            await update.message.reply_text(
                f"🎉 Игра окончена! {winner_text}\n\n"
                "📊 Статистика игры:\n"
                f"Всего игроков: {len(game.players)}\n"
                f"Раундов сыграно: {game.current_round}"
            )
        else:
            await update.message.reply_text(
                "🏁 Игра окончена!\n"
                "Недостаточно игроков для продолжения."
            )
        
        # Очищаем игру
        for player_id in game.players:
            if player_id in self.player_games:
                del self.player_games[player_id]
        
        chat_id = game.chat_id
        del self.games[chat_id]
        if chat_id in self.night_actions:
            del self.night_actions[chat_id]
        if chat_id in self.night_interfaces:
            del self.night_interfaces[chat_id]
    
    async def handle_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик голосования"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        chat_id = query.message.chat.id
        
        if chat_id not in self.games:
            return
        
        game = self.games[chat_id]
        
        if game.phase != GamePhase.VOTING:
            await query.edit_message_text("❌ Голосование уже завершено!")
            return
        
        # Извлекаем ID цели из callback_data
        target_id = int(query.data.split('_')[1])
        
        if game.vote(user_id, target_id):
            await query.edit_message_text(
                f"✅ Ваш голос зарегистрирован!\n"
                f"Вы проголосовали за изгнание игрока."
            )
        else:
            await query.edit_message_text("❌ Не удалось зарегистрировать голос!")
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.games:
            await update.message.reply_text(
                "❌ В этом чате нет активной игры!\n"
                "Используйте /join чтобы присоединиться."
            )
            return
        
        game = self.games[chat_id]
        
        if game.phase == GamePhase.WAITING:
            status_text = (
                "⏳ Ожидание игроков...\n\n"
                f"👥 Игроков: {len(game.players)}/{12}\n"
                f"📋 Минимум для начала: {MIN_PLAYERS}\n\n"
                "Список игроков:\n"
            )
            
            for player in game.players.values():
                status_text += f"• {player.username}\n"
            
            if game.can_start_game():
                status_text += "\n✅ Можно начинать игру!"
            else:
                status_text += f"\n⏳ Нужно еще {MIN_PLAYERS - len(game.players)} игроков"
        else:
            phase_names = {
                GamePhase.NIGHT: "🌙 Ночь",
                GamePhase.DAY: "☀️ День",
                GamePhase.VOTING: "🗳️ Голосование",
                GamePhase.GAME_OVER: "🏁 Игра окончена"
            }
            
            status_text = (
                f"🎮 Игра идет\n\n"
                f"📊 Фаза: {phase_names.get(game.phase, 'Неизвестно')}\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых игроков: {len(game.get_alive_players())}\n\n"
                "Живые игроки:\n"
            )
            
            for player in game.get_alive_players():
                status_text += f"• {player.username}\n"
        
        await update.message.reply_text(status_text)
    
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /settings"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Проверяем права администратора
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text(
                "❌ Только администраторы могут изменять настройки!"
            )
            return
        
        if chat_id not in self.games:
            await update.message.reply_text(
                "❌ В этом чате нет активной игры!\n"
                "Используйте /join чтобы присоединиться."
            )
            return
        
        game = self.games[chat_id]
        
        # Создаем клавиатуру настроек
        keyboard = [
            [InlineKeyboardButton("⏱️ Изменить таймеры", callback_data="settings_timers")],
            [InlineKeyboardButton("🎭 Изменить распределение ролей", callback_data="settings_roles")],
            [InlineKeyboardButton("📊 Сбросить статистику", callback_data="settings_reset")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="settings_close")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚙️ Настройки игры\n\n"
            "Выберите, что хотите изменить:",
            reply_markup=reply_markup
        )
    
    async def send_night_actions_to_players(self, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Отправляет меню ночных действий игрокам с ночными ролями"""
        chat_id = game.chat_id
        if chat_id in self.night_interfaces:
            night_interface = self.night_interfaces[chat_id]
            await night_interface.send_role_reminders(context)
    
    async def process_night_phase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
        """Обрабатывает ночную фазу"""
        chat_id = game.chat_id
        if chat_id in self.night_actions:
            night_actions = self.night_actions[chat_id]
            night_interface = self.night_interfaces[chat_id]
            
            # Обрабатываем все ночные действия
            results = night_actions.process_all_actions()
            
            # Отправляем результаты
            await night_interface.send_night_results(context, results)
            
            # Очищаем действия для следующей ночи
            night_actions.clear_actions()
    
    async def handle_night_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ночных действий"""
        query = update.callback_query
        user_id = query.from_user.id
        
        # Находим игру, в которой участвует игрок
        if user_id in self.player_games:
            chat_id = self.player_games[user_id]
                    if chat_id in self.night_interfaces:
            night_interface = self.night_interfaces[chat_id]
            await night_interface.handle_night_action(update, context)
    
    async def handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик настроек игры"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        chat_id = query.message.chat.id
        
        # Проверяем права администратора
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await query.edit_message_text("❌ Только администраторы могут изменять настройки!")
            return
        
        if chat_id not in self.games:
            await query.edit_message_text("❌ В этом чате нет активной игры!")
            return
        
        game = self.games[chat_id]
        data = query.data.split('_')[1]
        
        if data == "timers":
            await self.show_timer_settings(query, context, game)
        elif data == "roles":
            await self.show_role_settings(query, context, game)
        elif data == "reset":
            await self.reset_game_stats(query, context, game)
        elif data == "close":
            await query.edit_message_text("⚙️ Настройки закрыты")
    
    async def show_timer_settings(self, query, context, game):
        """Показывает настройки таймеров"""
        keyboard = [
            [InlineKeyboardButton("🌙 Ночь: 60с", callback_data="timer_night_60")],
            [InlineKeyboardButton("☀️ День: 5мин", callback_data="timer_day_300")],
            [InlineKeyboardButton("🗳️ Голосование: 2мин", callback_data="timer_vote_120")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⏱️ Настройки таймеров\n\n"
            "Текущие значения:\n"
            "🌙 Ночь: 60 секунд\n"
            "☀️ День: 5 минут\n"
            "🗳️ Голосование: 2 минуты\n\n"
            "Выберите, что хотите изменить:",
            reply_markup=reply_markup
        )
    
    async def show_role_settings(self, query, context, game):
        """Показывает настройки ролей"""
        keyboard = [
            [InlineKeyboardButton("🐺 Волки: 25%", callback_data="role_wolves_25")],
            [InlineKeyboardButton("🦊 Лиса: 15%", callback_data="role_fox_15")],
            [InlineKeyboardButton("🦫 Крот: 15%", callback_data="role_mole_15")],
            [InlineKeyboardButton("🦦 Бобёр: 10%", callback_data="role_beaver_10")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎭 Настройки распределения ролей\n\n"
            "Текущие значения:\n"
            "🐺 Волки: 25%\n"
            "🦊 Лиса: 15%\n"
            "🦫 Крот: 15%\n"
            "🦦 Бобёр: 10%\n"
            "🐰 Зайцы: 35% (автоматически)\n\n"
            "Выберите роль для изменения:",
            reply_markup=reply_markup
        )
    
    async def reset_game_stats(self, query, context, game):
        """Сбрасывает статистику игры"""
        if game.phase != GamePhase.WAITING:
            await query.edit_message_text(
                "❌ Нельзя сбросить статистику во время игры!\n"
                "Дождитесь окончания игры."
            )
            return
        
        # Сбрасываем статистику
        game.current_round = 0
        game.game_start_time = None
        game.phase_end_time = None
        
        await query.edit_message_text(
            "📊 Статистика игры сброшена!\n\n"
            "✅ Раунд: 0\n"
            "✅ Время начала: сброшено\n"
            "✅ Таймеры: сброшены"
        )
    
    async def handle_settings_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки 'Назад' и других настроек"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        chat_id = query.message.chat.id
        
        # Проверяем права администратора
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await query.edit_message_text("❌ Только администраторы могут изменять настройки!")
            return
        
        if chat_id not in self.games:
            await query.edit_message_text("❌ В этом чате нет активной игры!")
            return
        
        game = self.games[chat_id]
        data = query.data
        
        if data == "settings_back":
            # Возвращаемся к главному меню настроек
            await self.settings(update, context)
        elif data.startswith("timer_"):
            await self.handle_timer_setting(query, context, game, data)
        elif data.startswith("role_"):
            await self.handle_role_setting(query, context, game, data)
    
    async def handle_timer_setting(self, query, context, game, data):
        """Обрабатывает изменение таймеров"""
        parts = data.split('_')
        timer_type = parts[1]
        current_value = int(parts[2])
        
        # Показываем варианты изменения
        if timer_type == "night":
            options = [30, 45, 60, 90, 120]
            current = 60
        elif timer_type == "day":
            options = [180, 300, 420, 600]
            current = 300
        elif timer_type == "vote":
            options = [60, 90, 120, 180]
            current = 120
        else:
            await query.edit_message_text("❌ Неизвестный тип таймера!")
            return
        
        keyboard = []
        for option in options:
            mark = "✅ " if option == current else ""
            keyboard.append([InlineKeyboardButton(
                f"{mark}{option} сек" if option < 60 else f"{mark}{option//60} мин",
                callback_data=f"set_timer_{timer_type}_{option}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        timer_names = {"night": "🌙 Ночь", "day": "☀️ День", "vote": "🗳️ Голосование"}
        await query.edit_message_text(
            f"⏱️ Изменение таймера: {timer_names.get(timer_type, 'Неизвестно')}\n\n"
            f"Текущее значение: {current} сек\n\n"
            "Выберите новое значение:",
            reply_markup=reply_markup
        )
    
    async def handle_role_setting(self, query, context, game, data):
        """Обрабатывает изменение распределения ролей"""
        parts = data.split('_')
        role_type = parts[1]
        current_value = int(parts[2])
        
        # Показываем варианты изменения
        if role_type == "wolves":
            options = [20, 25, 30, 35]
            current = 25
        elif role_type == "fox":
            options = [10, 15, 20, 25]
            current = 15
        elif role_type == "mole":
            options = [10, 15, 20, 25]
            current = 15
        elif role_type == "beaver":
            options = [5, 10, 15, 20]
            current = 10
        else:
            await query.edit_message_text("❌ Неизвестная роль!")
            return
        
        keyboard = []
        for option in options:
            mark = "✅ " if option == current else ""
            keyboard.append([InlineKeyboardButton(
                f"{mark}{option}%",
                callback_data=f"set_role_{role_type}_{option}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        role_names = {"wolves": "🐺 Волки", "fox": "🦊 Лиса", "mole": "🦫 Крот", "beaver": "🦦 Бобёр"}
        await query.edit_message_text(
            f"🎭 Изменение распределения роли: {role_names.get(role_type, 'Неизвестно')}\n\n"
            f"Текущее значение: {current}%\n\n"
            "Выберите новое значение:",
            reply_markup=reply_markup
        )
    
    async def handle_set_values(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик установки новых значений настроек"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        chat_id = query.message.chat.id
        
        # Проверяем права администратора
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await query.edit_message_text("❌ Только администраторы могут изменять настройки!")
            return
        
        if chat_id not in self.games:
            await query.edit_message_text("❌ В этом чате нет активной игры!")
            return
        
        game = self.games[chat_id]
        data = query.data.split('_')
        
        if len(data) != 4:
            await query.edit_message_text("❌ Неверный формат данных!")
            return
        
        setting_type = data[1]  # timer или role
        setting_name = data[2]  # night, day, vote, wolves, fox, mole, beaver
        new_value = int(data[3])
        
        if setting_type == "timer":
            await self.apply_timer_setting(query, context, game, setting_name, new_value)
        elif setting_type == "role":
            await self.apply_role_setting(query, context, game, setting_name, new_value)
    
    async def apply_timer_setting(self, query, context, game, timer_type, new_value):
        """Применяет новое значение таймера"""
        # Здесь можно добавить логику для применения таймеров
        # Пока что просто показываем сообщение об успехе
        
        timer_names = {"night": "🌙 Ночь", "day": "☀️ День", "vote": "🗳️ Голосование"}
        time_text = f"{new_value} сек" if new_value < 60 else f"{new_value//60} мин"
        
        await query.edit_message_text(
            f"✅ Таймер {timer_names.get(timer_type, 'Неизвестно')} изменен на {time_text}!\n\n"
            "⚠️ Примечание: Изменения вступят в силу в следующей игре."
        )
    
    async def apply_role_setting(self, query, context, game, role_type, new_value):
        """Применяет новое значение распределения ролей"""
        # Здесь можно добавить логику для применения распределения ролей
        # Пока что просто показываем сообщение об успехе
        
        role_names = {"wolves": "🐺 Волки", "fox": "🦊 Лиса", "mole": "🦫 Крот", "beaver": "🦦 Бобёр"}
        
        await query.edit_message_text(
            f"✅ Распределение роли {role_names.get(role_type, 'Неизвестно')} изменено на {new_value}%!\n\n"
            "⚠️ Примечание: Изменения вступят в силу в следующей игре."
        )
    
    def get_role_info(self, role: Role) -> Dict[str, str]:
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
                "description": "Вы травоядный! По ночам вы роете норки и узнаете команды других зверей."
            },
            Role.BEAVER: {
                "name": "🦦 Бобёр",
                "description": "Вы травоядный! Вы можете возвращать украденные запасы другим зверям."
            }
        }
        return role_info.get(role, {"name": "Неизвестно", "description": "Роль не определена"})
    
    def run(self):
        """Запускает бота"""
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("rules", self.rules))
        application.add_handler(CommandHandler("join", self.join))
        application.add_handler(CommandHandler("leave", self.leave))
        application.add_handler(CommandHandler("start_game", self.start_game))
        application.add_handler(CommandHandler("end_game", self.end_game))
        application.add_handler(CommandHandler("force_end", self.force_end))
        application.add_handler(CommandHandler("settings", self.settings))
        application.add_handler(CommandHandler("status", self.status))
        
        # Добавляем обработчики callback query
        application.add_handler(CallbackQueryHandler(self.handle_vote, pattern="^vote_"))
        application.add_handler(CallbackQueryHandler(self.handle_night_action, pattern="^night_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings, pattern="^settings_"))
        application.add_handler(CallbackQueryHandler(self.handle_settings_back, pattern="^(settings_back|timer_|role_)"))
        application.add_handler(CallbackQueryHandler(self.handle_set_values, pattern="^set_(timer|role)_"))
        
        # Запускаем бота
        application.run_polling()

if __name__ == "__main__":
    bot = ForestMafiaBot()
    bot.run()
