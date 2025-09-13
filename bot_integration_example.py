#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Пример интеграции модуля database_psycopg2.py с Telegram ботом
"""

import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Импортируем наш модуль базы данных
from database_psycopg2 import (
    init_db, close_db,
    create_user, get_user_by_telegram_id, update_user_balance,
    get_shop_items, create_purchase,
    get_user_stats, update_user_stats
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных при запуске
db = init_db()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    
    try:
        # Создаем или получаем пользователя
        create_user(user_id, username)
        db_user = get_user_by_telegram_id(user_id)
        
        welcome_message = f"""
🎮 Добро пожаловать в Лес и волки Bot, {db_user['username']}!

🌰 Ваш баланс: {db_user['balance']} орешков

Доступные команды:
/balance - показать баланс
/shop - показать магазин
/stats - показать статистику
/buy <номер_товара> - купить товар
        """
        
        await update.message.reply_text(welcome_message)
        
    except Exception as e:
        logger.error(f"Ошибка в команде /start: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /balance"""
    user_id = update.effective_user.id
    
    try:
        db_user = get_user_by_telegram_id(user_id)
        if db_user:
            await update.message.reply_text(f"🌰 Ваш баланс: {db_user['balance']} орешков")
        else:
            await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
            
    except Exception as e:
        logger.error(f"Ошибка в команде /balance: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /shop"""
    try:
        items = get_shop_items()
        
        if not items:
            await update.message.reply_text("🛍️ Магазин пуст")
            return
        
        shop_message = "🛍️ **Магазин товаров:**\n\n"
        
        for i, item in enumerate(items, 1):
            shop_message += f"{i}. {item['item_name']}\n"
            shop_message += f"   🌰 Цена: {item['price']} орешков\n"
            shop_message += f"   📝 {item['description']}\n\n"
        
        shop_message += "💡 Для покупки используйте: /buy <номер_товара>"
        
        await update.message.reply_text(shop_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в команде /shop: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /buy"""
    user_id = update.effective_user.id
    
    try:
        if not context.args:
            await update.message.reply_text("❌ Укажите номер товара. Пример: /buy 1")
            return
        
        try:
            item_number = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Номер товара должен быть числом")
            return
        
        # Получаем товары
        items = get_shop_items()
        
        if item_number < 1 or item_number > len(items):
            await update.message.reply_text("❌ Неверный номер товара")
            return
        
        item = items[item_number - 1]
        
        # Проверяем баланс пользователя
        db_user = get_user_by_telegram_id(user_id)
        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
            return
        
        if db_user['balance'] < item['price']:
            await update.message.reply_text(
                f"❌ Недостаточно средств. Нужно: {item['price']} орешков, у вас: {db_user['balance']} орешков"
            )
            return
        
        # Создаем покупку
        success = create_purchase(user_id, item['id'], 1)
        
        if success:
            # Обновляем баланс
            new_balance = db_user['balance'] - item['price']
            update_user_balance(user_id, new_balance)
            
            await update.message.reply_text(
                f"✅ Покупка успешна!\n"
                f"🛍️ Куплено: {item['item_name']}\n"
                f"🌰 Потрачено: {item['price']} орешков\n"
                f"💳 Остаток: {new_balance} орешков"
            )
        else:
            await update.message.reply_text("❌ Ошибка при создании покупки")
            
    except Exception as e:
        logger.error(f"Ошибка в команде /buy: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /stats"""
    user_id = update.effective_user.id
    
    try:
        db_user = get_user_by_telegram_id(user_id)
        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
            return
        
        stats = get_user_stats(user_id)
        
        if stats:
            win_rate = (stats['games_won'] / stats['games_played'] * 100) if stats['games_played'] > 0 else 0
            
            stats_message = f"""
📊 **Статистика игрока {db_user['username']}**

🎮 Игр сыграно: {stats['games_played']}
🏆 Побед: {stats['games_won']}
💔 Поражений: {stats['games_lost']}
📈 Процент побед: {win_rate:.1f}%

💰 Баланс: {db_user['balance']} руб.
            """
        else:
            stats_message = f"""
📊 **Статистика игрока {db_user['username']}**

🎮 Игр сыграно: 0
🏆 Побед: 0
💔 Поражений: 0
📈 Процент побед: 0%

💰 Баланс: {db_user['balance']} руб.
            """
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в команде /stats: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

async def add_money(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /add_money (для тестирования)"""
    user_id = update.effective_user.id
    
    try:
        if not context.args:
            await update.message.reply_text("❌ Укажите сумму. Пример: /add_money 100")
            return
        
        try:
            amount = float(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Сумма должна быть числом")
            return
        
        db_user = get_user_by_telegram_id(user_id)
        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
            return
        
        new_balance = db_user['balance'] + amount
        success = update_user_balance(user_id, new_balance)
        
        if success:
            await update.message.reply_text(f"✅ Добавлено {amount} орешков. Новый баланс: {new_balance} орешков")
        else:
            await update.message.reply_text("❌ Ошибка при обновлении баланса")
            
    except Exception as e:
        logger.error(f"Ошибка в команде /add_money: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления: {context.error}")

def main():
    """Основная функция запуска бота"""
    # Получаем токен бота
    bot_token = os.environ.get('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN не установлен в переменных окружения!")
        return
    
    # Создаем приложение
    application = Application.builder().token(bot_token).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", show_balance))
    application.add_handler(CommandHandler("shop", show_shop))
    application.add_handler(CommandHandler("buy", buy_item))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("add_money", add_money))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    print("🚀 Бот запущен с поддержкой PostgreSQL!")
    print("📊 База данных подключена и готова к работе")
    
    try:
        # Запускаем бота
        application.run_polling()
    except KeyboardInterrupt:
        print("\n⏹️ Остановка бота...")
    finally:
        # Закрываем подключение к базе данных
        close_db()
        print("✅ Подключение к базе данных закрыто")

if __name__ == "__main__":
    main()
