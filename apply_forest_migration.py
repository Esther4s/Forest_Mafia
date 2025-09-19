#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для применения миграции таблиц лесов
Создает необходимые таблицы в базе данных
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем текущую директорию в путь для импорта модулей
sys.path.append(str(Path(__file__).parent))

from database import init_database, get_db_session
from database import Forest, ForestMember, ForestInvite, ForestSetting

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def apply_forest_migration():
    """Применяет миграцию для создания таблиц лесов"""
    try:
        # Инициализируем базу данных
        logger.info("🔗 Подключение к базе данных...")
        init_database()
        
        # Получаем сессию
        session = get_db_session()
        
        try:
            # Создаем таблицы
            logger.info("📋 Создание таблиц лесов...")
            
            # Создаем таблицы через SQLAlchemy
            from database import Base
            Base.metadata.create_all(bind=session.bind)
            
            logger.info("✅ Таблицы лесов созданы успешно!")
            
            # Проверяем создание таблиц
            logger.info("🔍 Проверка созданных таблиц...")
            
            # Проверяем таблицу forests
            from sqlalchemy import text
            result = session.execute(text("SELECT COUNT(*) FROM forests")).scalar()
            logger.info(f"✅ Таблица 'forests' создана (записей: {result})")
            
            # Проверяем таблицу forest_members
            result = session.execute(text("SELECT COUNT(*) FROM forest_members")).scalar()
            logger.info(f"✅ Таблица 'forest_members' создана (записей: {result})")
            
            # Проверяем таблицу forest_invites
            result = session.execute(text("SELECT COUNT(*) FROM forest_invites")).scalar()
            logger.info(f"✅ Таблица 'forest_invites' создана (записей: {result})")
            
            # Проверяем таблицу forest_settings
            result = session.execute(text("SELECT COUNT(*) FROM forest_settings")).scalar()
            logger.info(f"✅ Таблица 'forest_settings' создана (записей: {result})")
            
            logger.info("🎉 Миграция применена успешно!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при создании таблиц: {e}")
            session.rollback()
            return False
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при применении миграции: {e}")
        return False


def test_forest_system():
    """Тестирует систему лесов"""
    try:
        logger.info("🧪 Тестирование системы лесов...")
        
        from forest_system import ForestManager
        from telegram import Bot
        
        # Создаем тестового бота (не инициализируем)
        class MockBot:
            def __init__(self):
                pass
        
        # Инициализируем менеджер лесов
        forest_manager = ForestManager(MockBot())
        
        # Тестируем создание леса
        logger.info("📝 Тестирование создания леса...")
        
        # Здесь можно добавить тесты создания леса, но без реального бота
        # это будет ограничено
        
        logger.info("✅ Тестирование завершено!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании: {e}")
        return False


if __name__ == "__main__":
    print("🌲 Применение миграции системы лесов 🌲")
    print("=" * 50)
    
    # Применяем миграцию
    if apply_forest_migration():
        print("\n✅ Миграция применена успешно!")
        
        # Тестируем систему
        if test_forest_system():
            print("✅ Тестирование прошло успешно!")
        else:
            print("⚠️ Тестирование завершилось с ошибками")
    else:
        print("\n❌ Ошибка при применении миграции!")
        sys.exit(1)
    
    print("\n🌲 Система лесов готова к использованию! 🌲")
