#!/usr/bin/env python3
"""
Скрипт для создания таблицы inventory в базе данных
"""

import os
import sys
from database_psycopg2 import init_db, close_db

def create_inventory_table():
    """Создает таблицу inventory в базе данных"""
    try:
        # Получаем DATABASE_URL из переменных окружения
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL не установлен в переменных окружения!")
            return False
        
        print(f"🔗 Подключаемся к базе данных...")
        
        # Инициализируем базу данных
        db = init_db()
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Проверяем, существует ли таблица inventory
                check_query = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'inventory'
                    );
                """
                cursor.execute(check_query)
                exists = cursor.fetchone()[0]
                
                if exists:
                    print("✅ Таблица inventory уже существует!")
                    return True
                
                print("🔧 Создаем таблицу inventory...")
                
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
                
                cursor.execute(create_table_sql)
                
                # Создаем индекс
                create_index_sql = """
                    CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id);
                """
                cursor.execute(create_index_sql)
                
                print("✅ Таблица inventory создана успешно!")
                print("✅ Индекс idx_inventory_user_id создан!")
                
                return True
                
    except Exception as e:
        print(f"❌ Ошибка создания таблицы inventory: {e}")
        return False
    finally:
        close_db()

if __name__ == "__main__":
    print("🚀 Создание таблицы inventory...")
    success = create_inventory_table()
    
    if success:
        print("✅ Таблица inventory успешно создана!")
        sys.exit(0)
    else:
        print("❌ Ошибка создания таблицы inventory!")
        sys.exit(1)
