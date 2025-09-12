#!/usr/bin/env python3
"""
Скрипт инициализации базы данных для продакшна
Создает таблицу inventory если её нет
"""

import os
import sys
from database_psycopg2 import init_db, close_db

def init_inventory_table():
    """Создает таблицу inventory если её нет"""
    try:
        # Инициализируем подключение к базе данных
        db = init_db()
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Проверяем, существует ли таблица inventory
                check_table_sql = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'inventory'
                );
                """
                
                cursor.execute(check_table_sql)
                exists = cursor.fetchone()[0]
                
                if exists:
                    print("✅ Таблица inventory уже существует")
                    return True
                
                # Создаем таблицу inventory
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    item_name VARCHAR(255) NOT NULL,
                    count INTEGER DEFAULT 1,
                    flags JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, item_name)
                );
                """
                
                print("🔧 Создаем таблицу inventory...")
                cursor.execute(create_table_sql)
                print("✅ Таблица inventory создана успешно!")
                
                # Создаем индекс для user_id
                create_index_sql = """
                CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id);
                """
                
                print("🔧 Создаем индекс для user_id...")
                cursor.execute(create_index_sql)
                print("✅ Индекс idx_inventory_user_id создан успешно!")
                
                return True
                
    except Exception as e:
        print(f"❌ Ошибка при создании таблицы inventory: {e}")
        return False
    finally:
        # Закрываем подключение
        close_db()

def main():
    """Главная функция"""
    print("🚀 Инициализация базы данных...")
    
    # Проверяем переменную окружения DATABASE_URL
    if not os.getenv('DATABASE_URL'):
        print("❌ Ошибка: Переменная окружения DATABASE_URL не установлена!")
        return False
    
    print(f"🔗 Подключение к базе данных...")
    
    # Создаем таблицу
    success = init_inventory_table()
    
    if success:
        print("🎉 База данных инициализирована успешно!")
        return True
    else:
        print("❌ Ошибка при инициализации базы данных!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
