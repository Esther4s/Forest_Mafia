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
        # Инициализируем подключение к базе данных
        db = init_db()
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
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
                
                # Проверяем, что таблица создана
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
                    print("✅ Таблица inventory существует в базе данных!")
                else:
                    print("❌ Ошибка: Таблица inventory не была создана!")
                    return False
                
                # Показываем структуру таблицы
                describe_sql = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'inventory' 
                ORDER BY ordinal_position;
                """
                
                cursor.execute(describe_sql)
                columns = cursor.fetchall()
                
                print("\n📋 Структура таблицы inventory:")
                print("┌─────────────┬─────────────┬─────────────┬─────────────────┐")
                print("│ Column Name │ Data Type   │ Nullable    │ Default         │")
                print("├─────────────┼─────────────┼─────────────┼─────────────────┤")
                for col in columns:
                    col_name, data_type, nullable, default = col
                    default_str = str(default) if default else "NULL"
                    print(f"│ {col_name:<11} │ {data_type:<11} │ {nullable:<11} │ {default_str:<15} │")
                print("└─────────────┴─────────────┴─────────────┴─────────────────┘")
                
                return True
                
    except Exception as e:
        print(f"❌ Ошибка при создании таблицы inventory: {e}")
        return False
    finally:
        # Закрываем подключение
        close_db()

def main():
    """Главная функция"""
    print("🚀 Создание таблицы inventory в базе данных...")
    print("=" * 50)
    
    # Проверяем переменную окружения DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    
    # Если не установлена, пытаемся прочитать из файла
    if not database_url:
        try:
            with open('env_local.txt', 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL='):
                        database_url = line.strip().split('=', 1)[1]
                        os.environ['DATABASE_URL'] = database_url
                        break
        except FileNotFoundError:
            pass
    
    if not database_url:
        print("❌ Ошибка: Переменная окружения DATABASE_URL не установлена!")
        print("💡 Установите DATABASE_URL перед запуском скрипта")
        return False
    
    print(f"🔗 Подключение к базе данных...")
    print(f"📊 DATABASE_URL: {os.getenv('DATABASE_URL')[:20]}...")
    
    # Создаем таблицу
    success = create_inventory_table()
    
    if success:
        print("\n🎉 УСПЕШНО! Таблица inventory создана!")
        print("✅ Теперь покупки товаров будут работать корректно")
        return True
    else:
        print("\n❌ ОШИБКА! Не удалось создать таблицу inventory")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
