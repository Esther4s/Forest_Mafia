#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ForestMafia Bot - Рефакторенная версия
Telegram бот для игры "Лес и Волки"
"""

import asyncio
import logging
from typing import Dict, Optional

from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from config import config
from bot_handlers import CommandHandlers, AdminHandlers
from bot_database import DatabaseManager, GameStateManager
from bot_night_manager import NightManager
from game_logic import Game, GamePhase

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ForestMafiaBot:
    """Основной класс бота ForestMafia"""
    
    def __init__(self):
        # Инициализация компонентов
        self.database_manager = DatabaseManager()
        self.game_state_manager = GameStateManager(self.database_manager)
        self.night_manager = NightManager()
        
        # Обработчики команд
        self.command_handlers = CommandHandlers(self)
        self.admin_handlers = AdminHandlers(self)
        
        # Авторизованные чаты
        self.authorized_chats: set = set()
        
        # Система случайных сообщений
        self._init_message_templates()
        
        # Загружаем активные игры
        self.game_state_manager.load_active_games()
    
    def _init_message_templates(self):
        """Инициализирует шаблоны сообщений"""
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
    
    # Публичные методы для доступа к играм
    @property
    def games(self) -> Dict[int, Game]:
        """Возвращает словарь игр"""
        return self.game_state_manager.games
    
    def get_or_create_game(self, chat_id: int, thread_id: Optional[int] = None) -> Game:
        """Получает или создает игру"""
        return self.game_state_manager.get_or_create_game(chat_id, thread_id, config.is_test_mode)
    
    def is_chat_authorized(self, chat_id: int, thread_id: Optional[int] = None) -> bool:
        """Проверяет, авторизован ли чат"""
        chat_key = (chat_id, thread_id)
        return chat_key in self.authorized_chats
    
    def authorize_chat(self, chat_id: int, thread_id: Optional[int] = None):
        """Авторизует чат"""
        chat_key = (chat_id, thread_id)
        self.authorized_chats.add(chat_key)
        logger.info(f"✅ Чат {chat_id} авторизован")
    
    def deauthorize_chat(self, chat_id: int, thread_id: Optional[int] = None):
        """Деавторизует чат"""
        chat_key = (chat_id, thread_id)
        self.authorized_chats.discard(chat_key)
        logger.info(f"❌ Чат {chat_id} деавторизован")
    
    async def setup_handlers(self, application: Application):
        """Настраивает обработчики команд"""
        # Основные команды
        application.add_handler(CommandHandler("start", self.command_handlers.handle_start))
        application.add_handler(CommandHandler("rules", self.command_handlers.handle_rules))
        application.add_handler(CommandHandler("join", self.command_handlers.handle_join))
        application.add_handler(CommandHandler("leave", self.command_handlers.handle_leave))
        application.add_handler(CommandHandler("status", self.command_handlers.handle_status))
        
        # Административные команды
        application.add_handler(CommandHandler("start_game", self.admin_handlers.handle_start_game))
        application.add_handler(CommandHandler("end_game", self.admin_handlers.handle_end_game))
        
        # Callback обработчики
        application.add_handler(CallbackQueryHandler(self.night_manager.handle_night_callback, pattern="^night_"))
        
        # Обработчик всех сообщений (для авторизации)
        application.add_handler(MessageHandler(filters.ALL, self._handle_message))
        
        logger.info("✅ Обработчики команд настроены")
    
    async def _handle_message(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех сообщений (для авторизации чатов)"""
        chat_id = update.effective_chat.id
        thread_id = update.effective_message.message_thread_id if update.effective_chat.is_forum else None
        
        # Автоматически авторизуем чат при первом сообщении
        if not self.is_chat_authorized(chat_id, thread_id):
            self.authorize_chat(chat_id, thread_id)
    
    async def setup_bot_commands(self, application: Application):
        """Настраивает команды бота"""
        commands = [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("rules", "Правила игры"),
            BotCommand("join", "Присоединиться к игре"),
            BotCommand("leave", "Покинуть игру"),
            BotCommand("status", "Статус текущей игры"),
            BotCommand("start_game", "Начать игру (админ)"),
            BotCommand("end_game", "Завершить игру (админ)"),
        ]
        
        await application.bot.set_my_commands(commands)
        logger.info("✅ Команды бота настроены")
    
    async def run_game_loop(self, application: Application):
        """Запускает игровой цикл"""
        while True:
            try:
                await self._process_games(application)
                await asyncio.sleep(5)  # Проверяем каждые 5 секунд
            except Exception as e:
                logger.error(f"❌ Ошибка в игровом цикле: {e}")
                await asyncio.sleep(10)
    
    async def _process_games(self, application: Application):
        """Обрабатывает все активные игры"""
        for chat_id, game in list(self.games.items()):
            try:
                await self._process_single_game(game, application)
            except Exception as e:
                logger.error(f"❌ Ошибка обработки игры {chat_id}: {e}")
    
    async def _process_single_game(self, game: Game, application: Application):
        """Обрабатывает одну игру"""
        if game.phase == GamePhase.GAME_OVER:
            return
        
        # Проверяем окончание фазы
        if game.is_phase_finished():
            await self._handle_phase_end(game, application)
        
        # Проверяем окончание игры
        winner = game.check_game_end()
        if winner:
            await self._handle_game_end(game, winner, application)
            return
        
        # Проверяем автоматическое окончание
        auto_winner = game.check_auto_game_end()
        if auto_winner:
            reason = game.get_auto_end_reason()
            await self._handle_game_end(game, auto_winner, application, reason)
            return
    
    async def _handle_phase_end(self, game: Game, application: Application):
        """Обрабатывает окончание фазы"""
        if game.phase == GamePhase.NIGHT:
            # Обрабатываем ночные действия
            await self.night_manager.process_night_actions(game, application.bot)
            
            # Переходим к дневной фазе
            game.start_day()
            await self._announce_day_start(game, application.bot)
            
        elif game.phase == GamePhase.DAY:
            # Переходим к голосованию
            game.start_voting()
            await self._announce_voting_start(game, application.bot)
            
        elif game.phase == GamePhase.VOTING:
            # Обрабатываем голосование
            exiled_player = game.process_voting()
            await self._announce_voting_results(game, exiled_player, application.bot)
            
            # Переходим к следующей ночи
            game.start_night()
            await self.night_manager.start_night_phase(game, application.bot)
        
        # Сохраняем состояние
        self.database_manager.update_game_phase(game)
    
    async def _handle_game_end(self, game: Game, winner: Game.Team, application: Application, reason: str = None):
        """Обрабатывает окончание игры"""
        game.phase = GamePhase.GAME_OVER
        
        # Отправляем сообщение об окончании
        await self._announce_game_end(game, winner, application.bot, reason)
        
        # Сохраняем в БД
        self.database_manager.finish_game(game, winner)
        
        # Очищаем игру
        self.game_state_manager.remove_game(game.chat_id)
        self.night_manager.cleanup_game(game.chat_id)
    
    async def _announce_day_start(self, game: Game, bot):
        """Объявляет о начале дневной фазы"""
        message = (
            f"☀️ **ДЕНЬ {game.current_round}** ☀️\n\n"
            f"🌅 Лес просыпается после ночи...\n"
            f"👥 Живых игроков: {len(game.get_alive_players())}\n\n"
            f"💬 У вас есть 5 минут на обсуждение событий ночи!"
        )
        
        await bot.send_message(
            chat_id=game.chat_id,
            text=message,
            message_thread_id=game.thread_id
        )
    
    async def _announce_voting_start(self, game: Game, bot):
        """Объявляет о начале голосования"""
        alive_players = game.get_alive_players()
        
        message = (
            f"🗳️ **ГОЛОСОВАНИЕ** 🗳️\n\n"
            f"👥 Живых игроков: {len(alive_players)}\n"
            f"⏰ У вас есть 2 минуты на голосование за изгнание!\n\n"
            f"**Правила голосования:**\n"
            f"• Требуется большинство голосов для изгнания\n"
            f"• Можно проголосовать за пропуск\n"
            f"• Голосование за себя запрещено"
        )
        
        await bot.send_message(
            chat_id=game.chat_id,
            text=message,
            message_thread_id=game.thread_id
        )
    
    async def _announce_voting_results(self, game: Game, exiled_player, bot):
        """Объявляет результаты голосования"""
        if exiled_player:
            message = f"🗳️ **Результаты голосования** 🗳️\n\n❌ {exiled_player.username} изгнан из леса!"
        else:
            import random
            message = f"🗳️ **Результаты голосования** 🗳️\n\n{random.choice(self.no_exile_messages)}"
        
        await bot.send_message(
            chat_id=game.chat_id,
            text=message,
            message_thread_id=game.thread_id
        )
    
    async def _announce_game_end(self, game: Game, winner: Game.Team, bot, reason: str = None):
        """Объявляет об окончании игры"""
        winner_name = "🦁 Хищники" if winner == Game.Team.PREDATORS else "🌿 Травоядные"
        
        message = (
            f"🌲 **ИГРА ЗАВЕРШЕНА** 🌲\n\n"
            f"🏆 Победители: {winner_name}\n"
            f"🎮 Раундов: {game.current_round}\n"
            f"👥 Участников: {len(game.players)}\n"
        )
        
        if reason:
            message += f"📋 Причина: {reason}\n"
        
        message += "\n🌲 Спасибо за игру! 🌲"
        
        await bot.send_message(
            chat_id=game.chat_id,
            text=message,
            message_thread_id=game.thread_id
        )
    
    async def cleanup(self):
        """Очищает ресурсы"""
        # Сохраняем все игры
        self.game_state_manager.save_all_games()
        
        # Закрываем БД
        self.database_manager.close()
        
        logger.info("✅ Бот завершил работу")


async def main():
    """Главная функция"""
    # Создаем бота
    bot = ForestMafiaBot()
    
    # Создаем приложение
    application = Application.builder().token(config.bot_token).build()
    
    # Настраиваем обработчики
    await bot.setup_handlers(application)
    await bot.setup_bot_commands(application)
    
    # Запускаем бота
    logger.info("🌲 ForestMafia Bot запущен! 🌲")
    
    try:
        # Запускаем игровой цикл в фоне
        asyncio.create_task(bot.run_game_loop(application))
        
        # Запускаем бота
        await application.run_polling()
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки")
    finally:
        await bot.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
