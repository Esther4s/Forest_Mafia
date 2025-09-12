#!/usr/bin/env python3
"""
ДИАГНОСТИКА КОДА ТАБЛИЦ
"""

import os
import sys

# Устанавливаем переменную окружения
os.environ['DATABASE_URL'] = "postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway"

def debug_tables_code():
    """Диагностика кода таблиц"""
    print("🔍 ДИАГНОСТИКА КОДА ТАБЛИЦ")
    print("=" * 50)
    
    try:
        from database_psycopg2 import init_db, close_db, create_tables, fetch_query
        
        print("✅ Импорт модулей успешен")
        
        # Инициализация
        print("\n1️⃣ Инициализация базы данных...")
        db = init_db()
        print("✅ База данных инициализирована")
        
        # Проверяем существующие таблицы
        print("\n2️⃣ Проверка существующих таблиц...")
        check_tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('users', 'games', 'players', 'stats', 'chat_settings')
        ORDER BY table_name
        """
        
        existing_tables = fetch_query(check_tables_query)
        print(f"📊 Найдено основных таблиц: {len(existing_tables)}")
        for table in existing_tables:
            print(f"  - {table['table_name']}")
        
        # Проверяем таблицу inventory
        print("\n3️⃣ Проверка таблицы inventory...")
        inventory_check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'inventory'
        );
        """
        inventory_exists = fetch_query(inventory_check_query)
        print(f"✅ Таблица inventory существует: {inventory_exists[0][0] if inventory_exists else False}")
        
        # Проверяем таблицу shop
        print("\n4️⃣ Проверка таблицы shop...")
        shop_check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'shop'
        );
        """
        shop_exists = fetch_query(shop_check_query)
        print(f"✅ Таблица shop существует: {shop_exists[0][0] if shop_exists else False}")
        
        # Тестируем create_tables()
        print("\n5️⃣ Тестирование create_tables()...")
        try:
            result = create_tables()
            print(f"✅ create_tables() вернул: {result}")
            print(f"✅ Тип результата: {type(result)}")
        except Exception as e:
            print(f"❌ Ошибка в create_tables(): {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
        
        # Проверяем все таблицы после create_tables
        print("\n6️⃣ Проверка всех таблиц после create_tables...")
        all_tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
        """
        all_tables = fetch_query(all_tables_query)
        print(f"📊 Всего таблиц: {len(all_tables)}")
        for table in all_tables:
            print(f"  - {table['table_name']}")
        
        close_db()
        return True
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

def test_specific_functions():
    """Тестирование конкретных функций"""
    print("\n🧪 ТЕСТИРОВАНИЕ КОНКРЕТНЫХ ФУНКЦИЙ")
    print("=" * 50)
    
    try:
        from database_psycopg2 import get_shop_items, get_user_balance, create_user
        
        # Тест get_shop_items
        print("\n1️⃣ Тест get_shop_items()...")
        try:
            items = get_shop_items()
            print(f"✅ get_shop_items() вернул: {len(items)} товаров")
            for item in items[:3]:  # Показываем первые 3
                print(f"  - {item['item_name']}: {item['price']} орешков")
        except Exception as e:
            print(f"❌ Ошибка в get_shop_items(): {e}")
        
        # Тест get_user_balance
        print("\n2️⃣ Тест get_user_balance()...")
        try:
            balance = get_user_balance(123456789)
            print(f"✅ get_user_balance() вернул: {balance}")
        except Exception as e:
            print(f"❌ Ошибка в get_user_balance(): {e}")
        
        # Тест create_user
        print("\n3️⃣ Тест create_user()...")
        try:
            user_id = create_user(999999999, "test_user")
            print(f"✅ create_user() вернул: {user_id}")
        except Exception as e:
            print(f"❌ Ошибка в create_user(): {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования функций: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

def main():
    """Основная функция"""
    print("🚨 ДИАГНОСТИКА КОДА ТАБЛИЦ")
    print("=" * 50)
    
    # Тест 1: Диагностика таблиц
    tables_ok = debug_tables_code()
    
    # Тест 2: Конкретные функции
    functions_ok = test_specific_functions()
    
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 50)
    
    print(f"Диагностика таблиц: {'✅ РАБОТАЕТ' if tables_ok else '❌ НЕ РАБОТАЕТ'}")
    print(f"Тестирование функций: {'✅ РАБОТАЕТ' if functions_ok else '❌ НЕ РАБОТАЕТ'}")
    
    if tables_ok and functions_ok:
        print("\n🎉 ВСЕ СИСТЕМЫ РАБОТАЮТ!")
        print("💡 Проблема может быть в коде бота или логике инициализации")
    else:
        print("\n❌ НАЙДЕНЫ ПРОБЛЕМЫ В КОДЕ!")
        print("💡 Требуется исправление кода таблиц")
    
    return tables_ok and functions_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
