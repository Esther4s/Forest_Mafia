#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для запуска Forest Mafia Bot
"""

import os
import sys
import asyncio
from telegram import Bot
from telegram.ext import Application
from config import Config
from database import init_database

async def main():
    """Главная функция запуска бота"""
    print("🌲 Forest Mafia Bot - Запуск")
    print("=" * 50)
    
    try:
        # Создаем конфигурацию
        config = Config()
        print(f"✅ Конфигурация загружена")
        print(f"   Токен бота: {config.bot_token[:10]}...")
        print(f"   База данных: {config.database_url[:30]}...")
        
        # Инициализируем базу данных
        print("\n🗄️ Инициализация базы данных...")
        db_manager = init_database(config.database_url)
        print("✅ База данных подключена")
        
        # Создаем приложение бота
        print("\n🤖 Создание приложения бота...")
        application = Application.builder().token(config.bot_token).build()
        
        # Импортируем и регистрируем обработчики
        print("📝 Регистрация обработчиков...")
        
        # Здесь нужно будет добавить импорты всех обработчиков
        # Пока что просто создаем базовое приложение
        
        print("✅ Бот готов к работе!")
        print("\n🎮 Команды бота:")
        print("   /start - приветствие")
        print("   /rules - правила игры")
        print("   /join - присоединиться к игре")
        print("   /status - статус игры")
        print("\n🚀 Запуск бота...")
        print("   Нажмите Ctrl+C для остановки")
        
        # Запускаем бота
        await application.run_polling()
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Остановка бота...")
    except Exception as e:
        print(f"\n❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Устанавливаем переменные окружения
    os.environ['BOT_TOKEN'] = '8314318680:AAG1CDOB-SQhyFfCpqDIBm-U8ANz6Ggw94k'
    os.environ['DATABASE_URL'] = 'postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway'
    
    # Запускаем бота
    asyncio.run(main())