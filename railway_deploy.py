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
        
        # Инициализируем базу данных
        logger.info("🗄️ Инициализация базы данных...")
        init_database()
        logger.info("✅ База данных инициализирована")
        
        # Применяем миграции лесов
        logger.info("🌲 Применение миграций системы лесов...")
        try:
            from apply_forest_migration import apply_forest_migration
            migration_success = apply_forest_migration()
            if migration_success:
                logger.info("✅ Миграции лесов применены успешно")
            else:
                logger.warning("⚠️ Ошибка при применении миграций лесов, продолжаем...")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при применении миграций: {e}, продолжаем...")
        
        # Создаем и инициализируем бота
        logger.info("🤖 Создание бота...")
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
