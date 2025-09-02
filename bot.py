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
            "/start_game - начать игру (только для администраторов)\n"
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
            await self.end_game(update, context, game, winner)
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
    
    async def end_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game, winner: Optional[Team] = None):
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
        application.add_handler(CommandHandler("start_game", self.start_game))
        application.add_handler(CommandHandler("status", self.status))
        
        # Добавляем обработчики callback query
        application.add_handler(CallbackQueryHandler(self.handle_vote, pattern="^vote_"))
        application.add_handler(CallbackQueryHandler(self.handle_night_action, pattern="^night_"))
        
        # Запускаем бота
        application.run_polling()

if __name__ == "__main__":
    bot = ForestMafiaBot()
    bot.run()
