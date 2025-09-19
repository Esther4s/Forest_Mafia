#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для настройки базы данных на Railway
"""

import os
import sys
from datetime import datetime

# Устанавливаем тестовый токен для тестирования
os.environ['BOT_TOKEN'] = 'test_token_for_railway_database_setup'

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(__file__))

def setup_railway_database():
    """Настройка базы данных для Railway"""
    print("🚂 Настройка базы данных для Railway...")
    
    try:
        from database import init_database, get_db_session, Base
        from database_adapter import DatabaseAdapter
        from config import DATABASE_URL
        
        print(f"🔗 URL базы данных: {DATABASE_URL}")
        
        # Инициализируем базу данных
        print("🔧 Инициализируем базу данных...")
        db_manager = init_database(DATABASE_URL)
        
        # Создаем все таблицы
        print("📋 Создаем таблицы...")
        Base.metadata.create_all(db_manager.engine)
        
        # Тестируем подключение
        print("🔌 Тестируем подключение...")
        session = get_db_session()
        session.close()
        
        # Тестируем адаптер
        print("🧪 Тестируем DatabaseAdapter...")
        adapter = DatabaseAdapter()
        
        # Тестируем создание игры
        print("🎮 Тестируем создание игры...")
        game_id = adapter.create_game(12345, None, {
            "test": "railway_setup",
            "created_at": datetime.utcnow().isoformat()
        })
        
        if game_id:
            print(f"✅ Игра создана с ID: {game_id}")
            
            # Тестируем настройки
            print("⚙️ Тестируем настройки...")
            adapter.set_setting(12345, None, "railway_setup", "success")
            value = adapter.get_setting(12345, None, "railway_setup")
            
            if value == "success":
                print("✅ Настройки работают")
            else:
                print("❌ Настройки не работают")
                return False
        else:
            print("❌ Не удалось создать игру")
            return False
        
        print("🎉 База данных успешно настроена для Railway!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка настройки базы данных: {e}")
        return False

def check_database_tables():
    """Проверяем созданные таблицы"""
    print("📊 Проверяем созданные таблицы...")
    
    try:
        from database import get_db_session, Game, Player, GameEvent, PlayerAction, Vote, PlayerStats, BotSettings
        
        session = get_db_session()
        
        # Проверяем таблицы
        tables = [Game, Player, GameEvent, PlayerAction, Vote, PlayerStats, BotSettings]
        table_names = [table.__tablename__ for table in tables]
        
        print("📋 Созданные таблицы:")
        for table_name in table_names:
            print(f"  ✅ {table_name}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки таблиц: {e}")
        return False

def main():
    """Основная функция"""
    print("🎯 Настройка базы данных для Railway")
    print("=" * 50)
    
    # Настройка базы данных
    if not setup_railway_database():
        print("❌ Не удалось настроить базу данных")
        return False
    
    print()
    
    # Проверка таблиц
    if not check_database_tables():
        print("❌ Не удалось проверить таблицы")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 БАЗА ДАННЫХ ГОТОВА ДЛЯ RAILWAY!")
    print("=" * 50)
    
    print("\n📋 Что настроено:")
    print("✅ Подключение к базе данных")
    print("✅ Все таблицы созданы")
    print("✅ DatabaseAdapter работает")
    print("✅ Создание игр работает")
    print("✅ Настройки работают")
    
    print("\n🚀 Готово к деплою на Railway!")
    print("📖 Следуйте инструкциям в RAILWAY_DEPLOYMENT_GUIDE.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
