#!/usr/bin/env python3
"""
Проверка переменных окружения
"""

import os
import sys

def check_environment():
    """Проверяет переменные окружения"""
    print("🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    print("=" * 40)
    
    # Проверяем DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print(f"✅ DATABASE_URL: {database_url[:30]}...")
        
        # Парсим URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            print(f"  - Хост: {parsed.hostname}")
            print(f"  - Порт: {parsed.port}")
            print(f"  - База данных: {parsed.path[1:]}")
            print(f"  - Пользователь: {parsed.username}")
        except Exception as e:
            print(f"❌ Ошибка парсинга URL: {e}")
    else:
        print("❌ DATABASE_URL не установлен!")
        print("💡 Установите переменную окружения DATABASE_URL")
        return False
    
    # Проверяем BOT_TOKEN
    bot_token = os.environ.get('BOT_TOKEN')
    if bot_token:
        print(f"✅ BOT_TOKEN: {bot_token[:10]}...")
    else:
        print("❌ BOT_TOKEN не установлен!")
        print("💡 Установите переменную окружения BOT_TOKEN")
        return False
    
    # Проверяем другие переменные
    env_vars = ['LOG_LEVEL', 'ENVIRONMENT', 'DEBUG']
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️ {var}: не установлен")
    
    print("\n🎉 ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ПРОВЕРЕНЫ!")
    return True

def test_database_connection():
    """Тестирует подключение к базе данных"""
    print("\n🔗 ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ К БД")
    print("=" * 40)
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL не установлен!")
        return False
    
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Простой тест
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result:
            print("✅ Подключение к базе данных успешно!")
            
            # Проверяем таблицы
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            print(f"✅ Найдено таблиц: {len(tables)}")
            
            cursor.close()
            conn.close()
            return True
        else:
            print("❌ Запрос не вернул результат!")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def main():
    """Основная функция"""
    print("🚨 ПРОВЕРКА СИСТЕМЫ")
    print("=" * 40)
    
    # Проверка переменных окружения
    env_ok = check_environment()
    
    if env_ok:
        # Тест подключения к БД
        db_ok = test_database_connection()
        
        if db_ok:
            print("\n🎉 ВСЕ СИСТЕМЫ РАБОТАЮТ!")
            return True
        else:
            print("\n❌ ПРОБЛЕМА С БАЗОЙ ДАННЫХ!")
            return False
    else:
        print("\n❌ ПРОБЛЕМА С ПЕРЕМЕННЫМИ ОКРУЖЕНИЯ!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
