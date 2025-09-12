#!/usr/bin/env python3
"""
ЭКСТРЕННАЯ ДИАГНОСТИКА БАЗЫ ДАННЫХ
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def emergency_database_check():
    """Экстренная проверка базы данных"""
    print("🚨 ЭКСТРЕННАЯ ДИАГНОСТИКА БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    # URL базы данных
    database_url = "postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway"
    
    print(f"🔗 URL: {database_url[:30]}...")
    
    try:
        # 1. Прямое подключение
        print("\n1️⃣ Прямое подключение к PostgreSQL...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("✅ Подключение успешно!")
        
        # 2. Проверка таблиц
        print("\n2️⃣ Проверка таблиц...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        print(f"📊 Найдено таблиц: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 3. Проверка таблицы inventory
        print("\n3️⃣ Проверка таблицы inventory...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'inventory'
            )
        """)
        inventory_exists = cursor.fetchone()[0]
        print(f"✅ Таблица inventory существует: {inventory_exists}")
        
        # 4. Проверка таблицы shop
        print("\n4️⃣ Проверка таблицы shop...")
        cursor.execute("SELECT COUNT(*) FROM shop")
        shop_count = cursor.fetchone()[0]
        print(f"✅ Товаров в магазине: {shop_count}")
        
        # 5. Проверка таблицы users
        print("\n5️⃣ Проверка таблицы users...")
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        print(f"✅ Пользователей: {users_count}")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 БАЗА ДАННЫХ РАБОТАЕТ ОТЛИЧНО!")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ ОШИБКА ПОДКЛЮЧЕНИЯ: {e}")
        return False
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

def test_database_psycopg2():
    """Тестирование модуля database_psycopg2"""
    print("\n🔧 ТЕСТИРОВАНИЕ MODULE DATABASE_PSYCOPG2")
    print("=" * 50)
    
    # Устанавливаем переменную окружения
    os.environ['DATABASE_URL'] = "postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway"
    
    try:
        from database_psycopg2 import init_db, close_db, get_shop_items
        
        print("✅ Импорт модуля успешен")
        
        # Инициализация
        print("🔧 Инициализация базы данных...")
        db = init_db()
        print("✅ База данных инициализирована")
        
        # Тест подключения
        if db.test_connection():
            print("✅ Тест подключения успешен")
        else:
            print("❌ Тест подключения провален")
            return False
        
        # Тест получения товаров
        print("🛍️ Тестирование получения товаров...")
        items = get_shop_items()
        print(f"✅ Товаров получено: {len(items)}")
        
        close_db()
        print("✅ Модуль database_psycopg2 работает!")
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА В MODULE: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

def main():
    """Основная функция"""
    print("🚨 ЭКСТРЕННАЯ ДИАГНОСТИКА СИСТЕМЫ")
    print("=" * 50)
    
    # Тест 1: Прямое подключение
    direct_ok = emergency_database_check()
    
    # Тест 2: Модуль database_psycopg2
    module_ok = test_database_psycopg2()
    
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 50)
    
    print(f"Прямое подключение: {'✅ РАБОТАЕТ' if direct_ok else '❌ НЕ РАБОТАЕТ'}")
    print(f"Модуль database_psycopg2: {'✅ РАБОТАЕТ' if module_ok else '❌ НЕ РАБОТАЕТ'}")
    
    if direct_ok and module_ok:
        print("\n🎉 ВСЕ СИСТЕМЫ РАБОТАЮТ!")
        print("💡 Проблема может быть в коде бота или переменных окружения")
    elif direct_ok and not module_ok:
        print("\n⚠️ ПРОБЛЕМА В МОДУЛЕ DATABASE_PSYCOPG2")
        print("💡 Нужно исправить код модуля")
    elif not direct_ok:
        print("\n❌ КРИТИЧЕСКАЯ ПРОБЛЕМА С БАЗОЙ ДАННЫХ")
        print("💡 Нужно проверить подключение к Railway")
    else:
        print("\n❌ НЕИЗВЕСТНАЯ ПРОБЛЕМА")
        print("💡 Требуется дополнительная диагностика")
    
    return direct_ok and module_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
