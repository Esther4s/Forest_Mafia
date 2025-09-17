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
            logger.info("🌲 Инициализируем расширенную систему лесов...")
            self.enhanced_forest_integration = init_enhanced_forest_integration(self.application.bot)
            logger.info("✅ Расширенная система лесов инициализирована")
            
            # Добавляем обработчики команд
            logger.info("🌲 Добавляем обработчики команд...")
            await self._add_command_handlers()
            logger.info("✅ Обработчики команд добавлены")
            
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
        # Создаем экземпляр основного бота для получения всех обработчиков
        from bot import ForestMafiaBot
        main_bot = ForestMafiaBot()
        
        # Добавляем ВСЕ обработчики команд из основного бота
        logger.info("🎮 Добавляем все игровые команды из основного бота...")
        
        # Основные команды
        self.application.add_handler(CommandHandler("start", main_bot.start_command))
        self.application.add_handler(CommandHandler("help", main_bot.help_command))
        self.application.add_handler(CommandHandler("rules", main_bot.rules))
        self.application.add_handler(CommandHandler("balance", main_bot.balance_command))
        
        # Игровые команды
        self.application.add_handler(CommandHandler("join", main_bot.join))
        self.application.add_handler(CommandHandler("leave", main_bot.leave))
        self.application.add_handler(CommandHandler("start_game", main_bot.start_game))
        self.application.add_handler(CommandHandler("end_game", main_bot.end_game))
        self.application.add_handler(CommandHandler("end", main_bot.end_game))  # Алиас
        self.application.add_handler(CommandHandler("force_end", main_bot.force_end))
        self.application.add_handler(CommandHandler("clear_all_games", main_bot.clear_all_games))
        self.application.add_handler(CommandHandler("settings", main_bot.settings))
        self.application.add_handler(CommandHandler("status", main_bot.status))
        
        # Дополнительные команды
        self.application.add_handler(CommandHandler("inventory", main_bot.inventory_command))
        self.application.add_handler(CommandHandler("use", main_bot.use_command))
        self.application.add_handler(CommandHandler("stats", main_bot.stats_command))
        self.application.add_handler(CommandHandler("profile", main_bot.profile_command))
        self.application.add_handler(CommandHandler("nickname", main_bot.nickname_command))
        self.application.add_handler(CommandHandler("reset_nickname", main_bot.reset_nickname_command))
        self.application.add_handler(CommandHandler("game", main_bot.game_command))
        self.application.add_handler(CommandHandler("cancel", main_bot.cancel_command))
        self.application.add_handler(CommandHandler("bite", main_bot.bite_command))
        self.application.add_handler(CommandHandler("poke", main_bot.poke_command))
        
        # Режимы игры
        self.application.add_handler(CommandHandler("hare_wolf", main_bot.hare_wolf_command))
        self.application.add_handler(CommandHandler("wolf_sheep", main_bot.wolf_sheep_command))
        self.application.add_handler(CommandHandler("hedgehogs", main_bot.hedgehogs_command))
        self.application.add_handler(CommandHandler("casino", main_bot.casino_command))
        
        # Дополнительные команды
        self.application.add_handler(CommandHandler("quick_mode", main_bot.handle_quick_mode_command))
        self.application.add_handler(CommandHandler("setup_channel", main_bot.setup_channel))
        self.application.add_handler(CommandHandler("remove_channel", main_bot.remove_channel))
        self.application.add_handler(CommandHandler("save_state", main_bot.save_state_command))
        self.application.add_handler(CommandHandler("auto_save_status", main_bot.auto_save_status_command))
        self.application.add_handler(CommandHandler("shop", main_bot.shop_command))
        self.application.add_handler(CommandHandler("global_stats", main_bot.global_stats_command))
        
        logger.info("✅ Все игровые команды добавлены")
        
        # Обработчик для команд с упоминанием бота (например, /start@forestwolf_bot)
        self.application.add_handler(MessageHandler(filters.Regex(r'^/start@'), self._handle_start))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/help@'), self._handle_help))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/balance@'), self._handle_balance))
        
        # Игровые команды с упоминанием бота
        self.application.add_handler(MessageHandler(filters.Regex(r'^/join@'), main_bot.join))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/leave@'), main_bot.leave))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/start_game@'), main_bot.start_game))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/end_game@'), main_bot.end_game))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/settings@'), main_bot.settings))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/inventory@'), main_bot.inventory_command))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/use@'), main_bot.use_command))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/stats@'), main_bot.stats_command))
        
        # Команды расширенной системы лесов
        logger.info("🌲 Добавляем обработчики команд лесов...")
        forest_handlers = self.enhanced_forest_integration.get_command_handlers()
        logger.info(f"🌲 Получено {len(forest_handlers)} обработчиков команд лесов")
        for handler in forest_handlers:
            self.application.add_handler(handler)
        logger.info("✅ Обработчики команд лесов добавлены")
        
        # Динамические команды лесов (с параметрами)
        logger.info("🌲 Добавляем динамические команды лесов...")
        from forest_handlers import handle_join_forest, handle_summon_forest
        
        self.application.add_handler(MessageHandler(filters.Regex(r'^/join_forest_\d+$'), handle_join_forest))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/summon_forest_\d+$'), handle_summon_forest))
        
        # Команды лесов с упоминанием бота
        self.application.add_handler(MessageHandler(filters.Regex(r'^/create_forest@'), self._handle_create_forest_with_mention))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/forests@'), self._handle_forests_with_mention))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/join_forest_\d+@'), handle_join_forest))
        self.application.add_handler(MessageHandler(filters.Regex(r'^/summon_forest_\d+@'), handle_summon_forest))
        
        logger.info("✅ Динамические команды лесов добавлены")
        
        # Добавляем обработчик для логирования всех команд
        self.application.add_handler(MessageHandler(filters.Regex(r'^/'), self._log_command))
        
        logger.info("✅ Обработчики команд добавлены")
    
    async def _add_callback_handlers(self):
        """Добавляет обработчики callback-ов"""
        # Создаем экземпляр основного бота для получения всех callback-ов
        from bot import ForestMafiaBot
        main_bot = ForestMafiaBot()
        
        # Добавляем ВСЕ callback-ы из основного бота
        logger.info("🎮 Добавляем все callback-ы из основного бота...")
        
        # Основные callback-ы игры
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_vote, pattern=r"^vote_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_night_action, pattern=r"^night_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^settings_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_welcome_buttons, pattern=r"^welcome_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_day_actions, pattern=r"^day_"))
        
        # Callback-ы для управления игрой
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_join_game_callback, pattern=r"^join_game$"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_start_game_callback, pattern=r"^start_game$"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_duel_callback, pattern=r"^duel_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_leave_registration_callback, pattern=r"^leave_registration$"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_cancel_game_callback, pattern=r"^cancel_game$"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_end_game_callback, pattern=r"^end_game$"))
        
        # Callback-ы настроек
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_timer_settings, pattern=r"^timer_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_role_settings, pattern=r"^role_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings_back, pattern=r"^settings_back$"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_timer_values, pattern=r"^set_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_timer_values, pattern=r"^timer_back"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_view_my_role, pattern=r"^view_my_role$"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_view_my_role, pattern=r"^night_view_role_"))
        
        # Callback-ы магазина и профилей
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_buy_item_callback, pattern=r"^buy_item_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^show_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^back_to_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^close_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^farewell_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^leave_forest"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^join_chat"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^language_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^show_profile_pm"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^show_roles_pm"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^lang_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^show_rules_pm"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^back_to_start"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_settings, pattern=r"^repeat_role_actions"))
        
        # Callback-ы ночных действий
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_night_action_callback, pattern=r"^wolf_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_night_action_callback, pattern=r"^fox_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_night_action_callback, pattern=r"^mole_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_night_action_callback, pattern=r"^beaver_"))
        
        # Callback-ы пропуска
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_night_skip_callback, pattern=r"^night_skip_"))
        self.application.add_handler(CallbackQueryHandler(main_bot.handle_hare_skip_callback, pattern=r"^hare_skip_"))
        
        logger.info("✅ Все callback-ы из основного бота добавлены")
        
        # Callback-ы расширенной системы лесов
        forest_callbacks = self.enhanced_forest_integration.get_callback_handlers()
        for handler in forest_callbacks:
            self.application.add_handler(handler)
        
        logger.info("✅ Все обработчики callback-ов добавлены")
    
    async def _set_bot_commands(self):
        """Устанавливает команды бота"""
        commands = [
            # Основные команды
            BotCommand("start", "Запустить бота"),
            BotCommand("help", "Помощь и команды"),
            BotCommand("balance", "💰 Показать баланс"),
            BotCommand("rules", "Правила игры"),
            
            # Игровые команды
            BotCommand("join", "🎮 Присоединиться к игре"),
            BotCommand("leave", "🚪 Покинуть игру"),
            BotCommand("start_game", "🚀 Начать игру"),
            BotCommand("end_game", "⏹️ Завершить игру"),
            BotCommand("settings", "⚙️ Настройки игры"),
            BotCommand("inventory", "🎒 Инвентарь"),
            BotCommand("use", "🔧 Использовать предмет"),
            BotCommand("stats", "📊 Статистика игрока"),
            
            # Профили и статистика
            BotCommand("profile", "Мой профиль"),
            BotCommand("profile_compact", "Компактный профиль"),
            BotCommand("user_forest_stats", "Лесная статистика"),
            
            # Леса - создание и управление
            BotCommand("create_forest", "Создать лес"),
            BotCommand("forests", "Список всех лесов"),
            BotCommand("my_forests_profile", "Мои леса"),
            
            # Профили лесов
            BotCommand("forest_profile", "Профиль леса"),
            BotCommand("forest_stats", "Статистика леса"),
            BotCommand("forest_analytics", "Аналитика леса"),
            
            # Рейтинги и сравнения
            BotCommand("top_forests", "Топ лесов"),
            BotCommand("forest_comparison", "Сравнение лесов"),
            BotCommand("forest_ranking", "Рейтинг участников"),
            
            # Справка
            BotCommand("help_forests", "Справка по лесам"),
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("✅ Команды бота установлены")
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        welcome_text = (
            "🌲 <b>Добро пожаловать в Лес и Волки Bot!</b> 🌲\n\n"
            "Это бот для игры 'Лес и Волки' с расширенной системой управления лесами.\n\n"
            "🎮 <b>Основные возможности:</b>\n"
            "• Игра в мафию с лесной тематикой\n"
            "• Создание и управление лесами (группами участников)\n"
            "• Детальные профили лесов и пользователей\n"
            "• Аналитика и рейтинги активности\n"
            "• Система созыва с батчингом\n"
            "• Статистика и сравнения\n\n"
            "🌲 <b>Быстрый старт:</b>\n"
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
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def _handle_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /balance"""
        user = update.effective_user
        user_id = user.id
        
        try:
            from database_balance_manager import balance_manager
            from database_psycopg2 import get_display_name
            
            # Получаем баланс пользователя
            balance = balance_manager.get_user_balance(user_id)
            
            # Получаем отображаемое имя с правильным приоритетом (nickname > username > first_name)
            display_name = get_display_name(
                user_id=user_id,
                username=user.username,
                first_name=user.first_name
            )
            
            clickable_name = f'<a href="tg://user?id={user_id}">{display_name}</a>'
            
            logger.info(f"✅ Баланс пользователя {display_name}: {balance}")
            
            balance_text = (
                f"🌲 <b>Баланс Лес и волки</b>\n\n"
                f"👤 <b>{clickable_name}:</b>\n"
                f"🌰 Орешки: {int(balance)}\n\n"
                f"💡 Орешки можно заработать, играя в Лес и волки!"
            )
            
            await update.message.reply_text(balance_text, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении баланса: {e}")
            await update.message.reply_text("❌ Ошибка при получении баланса. Попробуйте позже.")
    
    async def _log_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик для логирования всех команд (для отладки)"""
        user = update.effective_user
        command = update.message.text
        logger.info(f"🔍 LOG_COMMAND: User {user.id} ({user.username}) sent command: {command}")
        
        # Check if it's a forest command
        if any(cmd in command for cmd in ['create_forest', 'forests', 'my_forests_profile', 'forest_profile', 'forest_analytics', 'top_forests', 'help_forests', 'join_forest', 'summon_forest']):
            logger.info(f"🌲 LOG_COMMAND: Forest command detected: {command}")
        
        # Do not respond to the command, just log
        return
    
    async def _handle_create_forest_with_mention(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /create_forest@bot для групповых чатов"""
        # Убираем упоминание бота из команды
        command_text = update.message.text
        if '@' in command_text:
            command_text = command_text.split('@')[0]
        
        # Создаем новое сообщение с исправленной командой
        update.message.text = command_text
        
        # Вызываем основной обработчик
        from forest_handlers import handle_create_forest
        await handle_create_forest(update, context)
    
    async def _handle_forests_with_mention(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /forests@bot для групповых чатов"""
        # Убираем упоминание бота из команды
        command_text = update.message.text
        if '@' in command_text:
            command_text = command_text.split('@')[0]
        
        # Создаем новое сообщение с исправленной командой
        update.message.text = command_text
        
        # Вызываем основной обработчик
        from forest_handlers import handle_forests
        await handle_forests(update, context)
    
    
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
