#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основной файл бота - рефакторированная версия
Использует чистую архитектуру с разделением на слои
"""

import asyncio
import logging
from typing import Dict, Optional

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from ..application.bot_service import BotService
from ..application.command_handlers import CommandHandlers, AdminCommandHandlers, VotingHandlers
from ..application.callback_handlers import CallbackHandlers
from ..infrastructure.repositories import (
    GameRepositoryImpl, PlayerRepositoryImpl, UserRepositoryImpl,
    GameEventRepositoryImpl, ChatSettingsRepositoryImpl, StatisticsRepositoryImpl
)
from ..infrastructure.config import Config

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ForestWolvesBot:
    """Основной класс бота - рефакторированная версия"""
    
    def __init__(self):
        self.config = Config()
        
        # Инициализируем репозитории
        self.game_repo = GameRepositoryImpl()
        self.player_repo = PlayerRepositoryImpl()
        self.user_repo = UserRepositoryImpl()
        self.event_repo = GameEventRepositoryImpl()
        self.chat_settings_repo = ChatSettingsRepositoryImpl()
        self.stats_repo = StatisticsRepositoryImpl()
        
        # Инициализируем сервисы
        self.bot_service = BotService(
            game_repo=self.game_repo,
            player_repo=self.player_repo,
            user_repo=self.user_repo,
            event_repo=self.event_repo,
            chat_settings_repo=self.chat_settings_repo
        )
        
        # Инициализируем обработчики
        self.command_handlers = CommandHandlers(self.bot_service)
        self.admin_handlers = AdminCommandHandlers(self.bot_service)
        self.voting_handlers = VotingHandlers(self.bot_service)
        self.callback_handlers = CallbackHandlers(self.bot_service)
        
        # Telegram приложение
        self.application = None
        
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
    
    async def initialize(self) -> None:
        """Инициализация бота"""
        try:
            # Инициализируем сервисы
            await self.bot_service.initialize()
            
            # Создаем Telegram приложение
            self.application = Application.builder().token(self.config.bot_token).build()
            
            # Регистрируем обработчики
            await self._register_handlers()
            
            # Устанавливаем команды бота
            await self._set_bot_commands()
            
            logger.info("✅ Бот инициализирован успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бота: {e}")
            raise
    
    async def _register_handlers(self) -> None:
        """Регистрирует обработчики команд"""
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.command_handlers.handle_start))
        self.application.add_handler(CommandHandler("rules", self.command_handlers.handle_rules))
        self.application.add_handler(CommandHandler("join", self.command_handlers.handle_join))
        self.application.add_handler(CommandHandler("leave", self.command_handlers.handle_leave))
        self.application.add_handler(CommandHandler("status", self.command_handlers.handle_status))
        self.application.add_handler(CommandHandler("stats", self.command_handlers.handle_stats))
        
        # Административные команды
        self.application.add_handler(CommandHandler("start_game", self.admin_handlers.handle_start_game))
        self.application.add_handler(CommandHandler("end_game", self.admin_handlers.handle_end_game))
        
        # Обработчики callback'ов
        self.application.add_handler(CallbackQueryHandler(self.callback_handlers.handle_callback))
        
        # Обработчики сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text_message))
    
    async def _set_bot_commands(self) -> None:
        """Устанавливает команды бота"""
        commands = [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("rules", "Правила игры"),
            BotCommand("join", "Присоединиться к игре"),
            BotCommand("leave", "Покинуть игру"),
            BotCommand("status", "Статус текущей игры"),
            BotCommand("stats", "Ваша статистика"),
            BotCommand("start_game", "Начать игру (админ)"),
            BotCommand("end_game", "Завершить игру (админ)")
        ]
        
        await self.application.bot.set_my_commands(commands)
    
    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает текстовые сообщения"""
        # Здесь можно добавить логику для обработки обычных сообщений
        # Например, для чатов с играми
        pass
    
    async def start_polling(self) -> None:
        """Запускает бота в режиме polling"""
        if not self.application:
            raise RuntimeError("Бот не инициализирован. Вызовите initialize() сначала.")
        
        logger.info("🚀 Запуск бота...")
        await self.application.run_polling()
    
    async def stop(self) -> None:
        """Останавливает бота"""
        if self.application:
            await self.application.stop()
        logger.info("🛑 Бот остановлен")
    
    def get_random_no_exile_message(self) -> str:
        """Возвращает случайное сообщение о том, что никто не изгнан"""
        import random
        return random.choice(self.no_exile_messages)
    
    def get_random_no_kill_message(self) -> str:
        """Возвращает случайное сообщение о том, что никто не убит"""
        import random
        return random.choice(self.no_kill_messages)


async def main():
    """Главная функция"""
    bot = ForestWolvesBot()
    
    try:
        await bot.initialize()
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
