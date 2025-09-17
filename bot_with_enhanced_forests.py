#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Бот "Лес и Волки" с расширенной системой лесов и профилей
Включает все функции: профили лесов, аналитику, рейтинги, статистику
"""

import asyncio
import logging
from typing import Dict, Optional

from telegram import Update, Bot, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Импорты существующего бота
from config import BOT_TOKEN
from database import init_database

# Импорты расширенной системы лесов
from enhanced_forest_integration import init_enhanced_forest_integration, get_enhanced_forest_integration

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ForestWolvesBotWithEnhancedForests:
    """Бот Лес и Волки с расширенной системой лесов"""
    
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.application = None
        self.enhanced_forest_integration = None
    
    async def initialize(self):
        """Инициализирует бота и расширенную систему лесов"""
        try:
            # Инициализируем базу данных
            init_database()
            
            # Создаем приложение
            self.application = Application.builder().token(self.bot_token).build()
            
            # Инициализируем расширенную систему лесов
            self.enhanced_forest_integration = init_enhanced_forest_integration(self.application.bot)
            
            # Добавляем обработчики команд
            await self._add_command_handlers()
            
            # Добавляем обработчики callback-ов
            await self._add_callback_handlers()
            
            # Устанавливаем команды бота
            await self._set_bot_commands()
            
            logger.info("✅ Бот с расширенной системой лесов инициализирован успешно")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бота: {e}")
            return False
    
    async def _add_command_handlers(self):
        """Добавляет обработчики команд"""
        # Основные команды бота
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        self.application.add_handler(CommandHandler("help_forests", self._handle_help_forests))
        self.application.add_handler(CommandHandler("rules", self._handle_rules))
        
        # Команды расширенной системы лесов
        forest_handlers = self.enhanced_forest_integration.get_command_handlers()
        for handler in forest_handlers:
            self.application.add_handler(handler)
        
        logger.info("✅ Обработчики команд добавлены")
    
    async def _add_callback_handlers(self):
        """Добавляет обработчики callback-ов"""
        # Callback-ы расширенной системы лесов
        forest_callbacks = self.enhanced_forest_integration.get_callback_handlers()
        for handler in forest_callbacks:
            self.application.add_handler(handler)
        
        logger.info("✅ Обработчики callback-ов добавлены")
    
    async def _set_bot_commands(self):
        """Устанавливает команды бота"""
        commands = [
            BotCommand("start", "Запустить бота"),
            BotCommand("help", "Помощь и команды"),
            BotCommand("help_forests", "Справка по лесам"),
            BotCommand("rules", "Правила игры"),
            BotCommand("profile", "Мой профиль"),
            BotCommand("create_forest", "Создать лес"),
            BotCommand("forests", "Список лесов"),
            BotCommand("top_forests", "Топ лесов"),
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("✅ Команды бота установлены")
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        welcome_text = (
            "🌲 **Добро пожаловать в Лес и Волки Bot!** 🌲\n\n"
            "Это бот для игры 'Лес и Волки' с расширенной системой управления лесами.\n\n"
            "🎮 **Основные возможности:**\n"
            "• Игра в мафию с лесной тематикой\n"
            "• Создание и управление лесами (группами участников)\n"
            "• Детальные профили лесов и пользователей\n"
            "• Аналитика и рейтинги активности\n"
            "• Система созыва с батчингом\n"
            "• Статистика и сравнения\n\n"
            "🌲 **Быстрый старт:**\n"
            "• /profile - посмотреть свой профиль\n"
            "• /forests - найти леса для присоединения\n"
            "• /create_forest - создать свой лес\n"
            "• /help_forests - полная справка по лесам\n\n"
            "🌲 Удачной игры в лесу! 🌲"
        )
        
        # Создаем клавиатуру
        keyboard = [
            [
                InlineKeyboardButton("👤 Мой профиль", callback_data="my_profile"),
                InlineKeyboardButton("🌲 Все леса", callback_data="show_all_forests")
            ],
            [
                InlineKeyboardButton("🏗️ Создать лес", callback_data="create_forest"),
                InlineKeyboardButton("🏆 Топ лесов", callback_data="top_forests")
            ],
            [
                InlineKeyboardButton("📋 Справка", callback_data="help_forests")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = (
            "🌲 **Справка по командам** 🌲\n\n"
            "**Основные команды:**\n"
            "• /start - запустить бота\n"
            "• /help - эта справка\n"
            "• /help_forests - справка по лесам\n"
            "• /rules - правила игры\n\n"
        )
        
        # Добавляем справку по лесам
        help_text += self.enhanced_forest_integration.get_forest_commands_summary()
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def _handle_help_forests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help_forests"""
        help_text = self.enhanced_forest_integration.get_help_text()
        
        # Создаем клавиатуру
        keyboard = [
            [
                InlineKeyboardButton("👤 Мой профиль", callback_data="my_profile"),
                InlineKeyboardButton("🌲 Все леса", callback_data="show_all_forests")
            ],
            [
                InlineKeyboardButton("🏗️ Создать лес", callback_data="create_forest"),
                InlineKeyboardButton("🏆 Топ лесов", callback_data="top_forests")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _handle_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            "**🌲 Система лесов:**\n"
            "• Леса - это группы участников для игры\n"
            "• Создавайте леса и приглашайте друзей\n"
            "• Используйте созыв для быстрого сбора участников\n"
            "• Отслеживайте статистику и рейтинги\n"
            "• Настраивайте уведомления и cooldown\n\n"
            "**📊 Профили и аналитика:**\n"
            "• Детальные профили лесов и участников\n"
            "• Рейтинги активности и вовлеченности\n"
            "• Статистика игр и лесной активности\n"
            "• Сравнение лесов и участников\n\n"
            "🌲 Удачной игры! 🌲"
        )
        
        await update.message.reply_text(rules_text)
    
    async def start_bot(self):
        """Запускает бота"""
        if not self.application:
            logger.error("❌ Бот не инициализирован")
            return False
        
        try:
            logger.info("🚀 Запуск бота с расширенной системой лесов...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("✅ Бот запущен успешно!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота: {e}")
            return False
    
    async def stop_bot(self):
        """Останавливает бота"""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("🛑 Бот остановлен")


async def main():
    """Главная функция"""
    bot = ForestWolvesBotWithEnhancedForests()
    
    # Инициализируем бота
    if not await bot.initialize():
        logger.error("❌ Не удалось инициализировать бота")
        return
    
    # Запускаем бота
    if not await bot.start_bot():
        logger.error("❌ Не удалось запустить бота")
        return
    
    try:
        # Держим бота запущенным
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки")
    finally:
        await bot.stop_bot()


if __name__ == "__main__":
    print("🌲 Запуск бота Лес и Волки с расширенной системой лесов 🌲")
    print("=" * 70)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")
