#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Пример интеграции модуля database_psycopg2.py с существующим ботом
Демонстрирует, как добавить работу с базой данных в bot.py
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

# Инициализация базы данных при запуске модуля
try:
    db = init_db()
    logger.info("✅ База данных инициализирована успешно")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации базы данных: {e}")
    db = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start с интеграцией БД"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or "Unknown"
    
    try:
        if not db:
            await update.message.reply_text("❌ База данных недоступна. Попробуйте позже.")
            return
        
        # Создаем или получаем пользователя в базе данных
        create_user(user_id, username)
        db_user = get_user_by_telegram_id(user_id)
        
        if db_user:
            welcome_message = f"""
🎮 Добро пожаловать в Лес и волки Bot, {db_user['username']}!

🌰 Ваш баланс: {db_user['balance']} орешков
📊 Статус: {'Новый игрок' if db_user['balance'] == 0 else 'Опытный игрок'}

Доступные команды:
/balance - показать баланс
/profile - показать профиль
/shop - показать магазин
/stats - показать статистику
            """
        else:
            welcome_message = "🎮 Добро пожаловать в Лес и волки Bot!"
        
        await update.message.reply_text(welcome_message)
        
    except Exception as e:
        logger.error(f"Ошибка в команде /start: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать баланс пользователя"""
    user_id = update.effective_user.id
    
    try:
        if not db:
            await update.message.reply_text("❌ База данных недоступна.")
            return
        
        db_user = get_user_by_telegram_id(user_id)
        if db_user:
            await update.message.reply_text(f"🌰 Ваш баланс: {db_user['balance']} орешков")
        else:
            await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
            
    except Exception as e:
        logger.error(f"Ошибка в команде /balance: {e}")
        await update.message.reply_text("❌ Произошла ошибка.")

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать профиль пользователя"""
    user_id = update.effective_user.id
    
    try:
        if not db:
            await update.message.reply_text("❌ База данных недоступна.")
            return
        
        db_user = get_user_by_telegram_id(user_id)
        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
            return
        
        # Получаем статистику
        stats = get_user_stats(user_id)
        
        profile_message = f"""
👤 **Профиль игрока**

🆔 ID: {db_user['user_id']}
👤 Имя: {db_user['username']}
🌰 Баланс: {db_user['balance']} орешков
📅 Регистрация: {db_user['created_at'].strftime('%d.%m.%Y %H:%M')}
        """
        
        if stats:
            win_rate = (stats['games_won'] / stats['games_played'] * 100) if stats['games_played'] > 0 else 0
            profile_message += f"""
📊 **Статистика игр**

🎮 Игр сыграно: {stats['games_played']}
🏆 Побед: {stats['games_won']}
💔 Поражений: {stats['games_lost']}
📈 Процент побед: {win_rate:.1f}%
            """
        else:
            profile_message += "\n📊 Статистика игр пока пуста"
        
        await update.message.reply_text(profile_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в команде /profile: {e}")
        await update.message.reply_text("❌ Произошла ошибка.")

async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать магазин"""
    try:
        if not db:
            await update.message.reply_text("❌ База данных недоступна.")
            return
        
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
        await update.message.reply_text("❌ Произошла ошибка.")

async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Купить товар"""
    user_id = update.effective_user.id
    
    try:
        if not db:
            await update.message.reply_text("❌ База данных недоступна.")
            return
        
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
        await update.message.reply_text("❌ Произошла ошибка.")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать статистику"""
    user_id = update.effective_user.id
    
    try:
        if not db:
            await update.message.reply_text("❌ База данных недоступна.")
            return
        
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

🌰 Баланс: {db_user['balance']} орешков
            """
        else:
            stats_message = f"""
📊 **Статистика игрока {db_user['username']}**

🎮 Игр сыграно: 0
🏆 Побед: 0
💔 Поражений: 0
📈 Процент побед: 0%

🌰 Баланс: {db_user['balance']} орешков
            """
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в команде /stats: {e}")
        await update.message.reply_text("❌ Произошла ошибка.")

async def add_money(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Добавить деньги (для тестирования)"""
    user_id = update.effective_user.id
    
    try:
        if not db:
            await update.message.reply_text("❌ База данных недоступна.")
            return
        
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
        await update.message.reply_text("❌ Произошла ошибка.")

async def simulate_game_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Симуляция результата игры (для тестирования)"""
    user_id = update.effective_user.id
    
    try:
        if not db:
            await update.message.reply_text("❌ База данных недоступна.")
            return
        
        # Получаем текущую статистику
        stats = get_user_stats(user_id)
        
        if not stats:
            # Создаем новую статистику
            from database_psycopg2 import execute_query
            execute_query(
                "INSERT INTO stats (user_id, games_played, games_won, games_lost) VALUES (%s, %s, %s, %s)",
                (user_id, 1, 1, 0)
            )
            await update.message.reply_text("🎉 Поздравляем! Вы выиграли первую игру!")
        else:
            # Обновляем существующую статистику
            new_games_played = stats['games_played'] + 1
            new_games_won = stats['games_won'] + 1
            
            update_user_stats(user_id, games_played=new_games_played, games_won=new_games_won)
            await update.message.reply_text(f"🎉 Поздравляем! Вы выиграли игру! Всего побед: {new_games_won}")
        
        # Добавляем бонус за победу
        db_user = get_user_by_telegram_id(user_id)
        if db_user:
            bonus = 50.0
            new_balance = db_user['balance'] + bonus
            update_user_balance(user_id, new_balance)
            await update.message.reply_text(f"🌰 Бонус за победу: +{bonus} орешков. Новый баланс: {new_balance} орешков")
        
    except Exception as e:
        logger.error(f"Ошибка в команде /simulate_game: {e}")
        await update.message.reply_text("❌ Произошла ошибка.")

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
    
    if not db:
        print("❌ База данных недоступна!")
        return
    
    # Создаем приложение
    application = Application.builder().token(bot_token).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", show_balance))
    application.add_handler(CommandHandler("profile", show_profile))
    application.add_handler(CommandHandler("shop", show_shop))
    application.add_handler(CommandHandler("buy", buy_item))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("add_money", add_money))
    application.add_handler(CommandHandler("simulate_game", simulate_game_result))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    print("🚀 Бот запущен с поддержкой PostgreSQL!")
    print("📊 База данных подключена и готова к работе")
    print("🎮 Доступные команды:")
    print("   /start - начать работу с ботом")
    print("   /balance - показать баланс")
    print("   /profile - показать профиль")
    print("   /shop - показать магазин")
    print("   /buy <номер> - купить товар")
    print("   /stats - показать статистику")
    print("   /add_money <сумма> - добавить деньги (тест)")
    print("   /simulate_game - симуляция игры (тест)")
    
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
