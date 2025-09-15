#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для применения миграции никнеймов
Добавляет поле nickname в таблицу users
"""

import os
import sys
import logging
from database_psycopg2 import DatabaseConnection

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_nickname_migration():
    """Применяет миграцию для добавления поля nickname"""
    try:
        # Создаем подключение к базе данных
        db = DatabaseConnection()
        
        # Читаем SQL миграции
        migration_sql = """
        -- Добавляем поле nickname в таблицу users
        ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname VARCHAR(50);
        
        -- Создаем индекс для быстрого поиска по никнейму
        CREATE INDEX IF NOT EXISTS idx_users_nickname ON users(nickname);
        
        -- Добавляем комментарий к полю
        COMMENT ON COLUMN users.nickname IS 'Пользовательский никнейм для отображения в игре';
        """
        
        # Выполняем миграцию
        logger.info("🔧 Применяем миграцию никнеймов...")
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(migration_sql)
                conn.commit()
        
        logger.info("✅ Миграция никнеймов успешно применена!")
        logger.info("📝 Добавлено поле 'nickname' в таблицу 'users'")
        logger.info("🔍 Создан индекс для быстрого поиска по никнейму")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка применения миграции: {e}")
        return False

def main():
    """Главная функция"""
    print("🌲 Применение миграции никнеймов для Лес и волки Bot")
    print("=" * 60)
    
    if apply_nickname_migration():
        print("✅ Миграция успешно применена!")
        print("🎭 Теперь игроки могут использовать команду /nickname")
        sys.exit(0)
    else:
        print("❌ Ошибка применения миграции!")
        sys.exit(1)

if __name__ == "__main__":
    main()
