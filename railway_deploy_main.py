#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт развертывания на Railway с основным ботом и интегрированной системой лесов
Автоматически применяет миграции и запускает основной бот с лесными командами
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from database import init_database
from enhanced_forest_integration import init_enhanced_forest_integration
from bot import ForestWolvesBot

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def deploy_main_bot_with_forests():
    """Развертывание основного бота с интегрированной системой лесов"""
    print("🚀 Развертывание основного бота с системой лесов на Railway")
    print("=" * 70)
    
    try:
        # Проверяем переменные окружения
        bot_token = os.environ.get('BOT_TOKEN')
        database_url = os.environ.get('DATABASE_URL')
        
        if not bot_token:
            logger.error("❌ BOT_TOKEN не установлен в переменных окружения")
            return False
        
        if not database_url:
            logger.error("❌ DATABASE_URL не установлен в переменных окружения")
            return False
        
        logger.info("✅ Переменные окружения настроены")
        logger.info(f"🔗 База данных: {database_url}")
        
        # Инициализируем базу данных (создаст все таблицы включая леса)
        logger.info("🗄️ Инициализация базы данных...")
        init_database()
        logger.info("✅ База данных инициализирована (включая таблицы лесов)")
        
        # Инициализируем database_psycopg2 для совместимости
        logger.info("🔄 Инициализация database_psycopg2...")
        try:
            from database_psycopg2 import init_db
            init_db()
            logger.info("✅ database_psycopg2 инициализирован")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при инициализации database_psycopg2: {e}, продолжаем...")
        
        # Исправляем реальную структуру базы данных
        logger.info("🔧 Исправление реальной структуры базы данных...")
        try:
            from fix_real_database_structure import fix_real_database_structure
            migration_success = fix_real_database_structure()
            if migration_success:
                logger.info("✅ Структура базы данных исправлена успешно")
            else:
                logger.warning("⚠️ Ошибка при исправлении структуры БД, продолжаем...")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при исправлении структуры БД: {e}, продолжаем...")
        
        # Создаем и запускаем основной бот
        logger.info("🤖 Создание основного бота с системой лесов...")
        bot = ForestWolvesBot()
        
        logger.info("✅ Основной бот инициализирован")
        logger.info("🌲 Система лесов интегрирована в основной бот")
        
        # Запускаем бота
        logger.info("🚀 Запуск основного бота...")
        bot.run()
        
        logger.info("🎉 Основной бот с системой лесов успешно запущен на Railway!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при развертывании: {e}")
        return False


async def main():
    """Главная функция"""
    try:
        success = await deploy_main_bot_with_forests()
        if not success:
            logger.error("❌ Развертывание не удалось")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
