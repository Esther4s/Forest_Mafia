#!/usr/bin/env python3
"""
Скрипт для проверки существования таблицы inventory
"""

import os
import sys
from database_psycopg2 import init_db, close_db

def check_inventory_table():
    """Проверяет существование таблицы inventory"""
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
                    print("✅ Таблица inventory существует!")
                    
                    # Проверяем структуру таблицы
                    structure_query = """
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns 
                        WHERE table_name = 'inventory' 
                        ORDER BY ordinal_position;
                    """
                    cursor.execute(structure_query)
                    columns = cursor.fetchall()
                    
                    print("📋 Структура таблицы inventory:")
                    for col in columns:
                        print(f"  - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
                    
                    return True
                else:
                    print("❌ Таблица inventory НЕ существует!")
                    return False
                
    except Exception as e:
        print(f"❌ Ошибка проверки таблицы inventory: {e}")
        return False
    finally:
        close_db()

if __name__ == "__main__":
    print("🔍 Проверка таблицы inventory...")
    success = check_inventory_table()
    
    if success:
        print("✅ Таблица inventory найдена!")
        sys.exit(0)
    else:
        print("❌ Таблица inventory не найдена!")
        sys.exit(1)
