#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт развертывания на Railway с расширенной системой лесов
Автоматически применяет миграции и запускает бота
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
from bot_with_enhanced_forests import ForestWolvesBotWithEnhancedForests

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def deploy_to_railway():
    """Развертывание на Railway"""
    print("🚀 Развертывание бота с расширенной системой лесов на Railway")
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
        
# Применяем детальную миграцию для исправления player_stats
logger.info("🔧 Применение детальной миграции player_stats...")
try:
    from detailed_player_stats_fix import detailed_fix_player_stats
    migration_success = detailed_fix_player_stats()
    if migration_success:
        logger.info("✅ Детальная миграция player_stats применена успешно")
    else:
        logger.warning("⚠️ Ошибка при применении детальной миграции player_stats, продолжаем...")
except Exception as e:
    logger.warning(f"⚠️ Ошибка при применении детальной миграции player_stats: {e}, продолжаем...")
        
        # Создаем и инициализируем бота
        logger.info("🤖 Создание бота с расширенной системой лесов...")
        bot = ForestWolvesBotWithEnhancedForests()
        
        # Инициализируем бота
        if not await bot.initialize():
            logger.error("❌ Ошибка инициализации бота")
            return False
        
        logger.info("✅ Бот инициализирован успешно")
        
        # Запускаем бота
        logger.info("🚀 Запуск бота...")
        if not await bot.start_bot():
            logger.error("❌ Ошибка запуска бота")
            return False
        
        logger.info("🎉 Бот успешно запущен на Railway!")
        logger.info("🌲 Расширенная система лесов активна")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при развертывании: {e}")
        return False


async def main():
    """Главная функция"""
    try:
        success = await deploy_to_railway()
        if success:
            # Держим бота запущенным
            await asyncio.Event().wait()
        else:
            logger.error("❌ Развертывание не удалось")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
