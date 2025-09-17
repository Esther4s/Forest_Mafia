#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест SQLite базы данных
"""

import os
import sys
import tempfile
import traceback
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Устанавливаем переменные окружения
os.environ['BOT_TOKEN'] = 'test_token_123456789'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'
os.environ['POSTGRES_USER'] = 'forest_mafia'
os.environ['POSTGRES_PASSWORD'] = 'forest_mafia_password'
os.environ['ENVIRONMENT'] = 'test'
os.environ['LOG_LEVEL'] = 'DEBUG'

print("🚀 ТЕСТ SQLITE БАЗЫ ДАННЫХ")
print("=" * 50)

def test_sqlite_imports():
    """Тестирует импорты SQLite модулей"""
    print("\n🧪 Тестирование импортов SQLite...")
    
    try:
        from database import Base, Game, Player, GameEvent, PlayerAction, Vote
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        print("✅ SQLite модули импортированы успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта SQLite: {e}")
        traceback.print_exc()
        return False

def test_sqlite_connection():
    """Тестирует подключение к SQLite"""
    print("\n🧪 Тестирование подключения к SQLite...")
    
    try:
        from database import Base
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Создаем временную базу данных
        engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Тестируем простой запрос
        result = session.execute("SELECT 1 as test").fetchone()
        if result and result[0] == 1:
            print("✅ Подключение к SQLite работает")
            session.close()
            return True
        else:
            print("❌ Запрос к SQLite не выполнился")
            session.close()
            return False
            
    except Exception as e:
        print(f"❌ Ошибка подключения к SQLite: {e}")
        traceback.print_exc()
        return False

def test_sqlite_models():
    """Тестирует модели SQLite"""
    print("\n🧪 Тестирование моделей SQLite...")
    
    try:
        from database import Base, Game, Player, GameEvent, PlayerAction, Vote
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Создаем временную базу данных
        engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Создаем тестовую игру
        game = Game(
            chat_id=12345,
            status='active',
            phase='night',
            round_number=1
        )
        session.add(game)
        session.commit()
        
        # Создаем тестового игрока
        player = Player(
            user_id=111,
            username="TestPlayer",
            first_name="Test",
            last_name="User",
            game_id=game.id,
            role="wolf",
            team="predators"
        )
        session.add(player)
        session.commit()
        
        # Проверяем, что данные сохранились
        saved_game = session.query(Game).filter_by(chat_id=12345).first()
        saved_player = session.query(Player).filter_by(user_id=111).first()
        
        if saved_game and saved_player:
            print("✅ Модели SQLite работают корректно")
            session.close()
            return True
        else:
            print("❌ Данные не сохранились в SQLite")
            session.close()
            return False
            
    except Exception as e:
        print(f"❌ Ошибка моделей SQLite: {e}")
        traceback.print_exc()
        return False

def test_sqlite_operations():
    """Тестирует операции с SQLite"""
    print("\n🧪 Тестирование операций с SQLite...")
    
    try:
        from database import Base, Game, Player, GameEvent, PlayerAction, Vote
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Создаем временную базу данных
        engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Создаем игру
        game = Game(chat_id=54321, status='active', phase='day', round_number=1)
        session.add(game)
        session.commit()
        
        # Добавляем игроков
        players_data = [
            (111, "Волк1", "wolf", "predators"),
            (222, "Лиса1", "fox", "predators"),
            (333, "Заяц1", "hare", "herbivores"),
            (444, "Крот1", "mole", "herbivores"),
            (555, "Бобёр1", "beaver", "herbivores")
        ]
        
        for user_id, username, role, team in players_data:
            player = Player(
                user_id=user_id,
                username=username,
                game_id=game.id,
                role=role,
                team=team
            )
            session.add(player)
        
        session.commit()
        
        # Проверяем количество игроков
        player_count = session.query(Player).filter_by(game_id=game.id).count()
        if player_count == 5:
            print("✅ Операции с SQLite работают корректно")
            session.close()
            return True
        else:
            print(f"❌ Неверное количество игроков: {player_count}")
            session.close()
            return False
            
    except Exception as e:
        print(f"❌ Ошибка операций с SQLite: {e}")
        traceback.print_exc()
        return False

def test_sqlite_queries():
    """Тестирует запросы к SQLite"""
    print("\n🧪 Тестирование запросов к SQLite...")
    
    try:
        from database import Base, Game, Player, GameEvent, PlayerAction, Vote
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Создаем временную базу данных
        engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Создаем тестовые данные
        game = Game(chat_id=99999, status='active', phase='night', round_number=1)
        session.add(game)
        session.commit()
        
        # Добавляем игроков разных команд
        predators = [
            (111, "Волк1", "wolf", "predators"),
            (222, "Лиса1", "fox", "predators")
        ]
        
        herbivores = [
            (333, "Заяц1", "hare", "herbivores"),
            (444, "Крот1", "mole", "herbivores"),
            (555, "Бобёр1", "beaver", "herbivores")
        ]
        
        for user_id, username, role, team in predators + herbivores:
            player = Player(
                user_id=user_id,
                username=username,
                game_id=game.id,
                role=role,
                team=team
            )
            session.add(player)
        
        session.commit()
        
        # Тестируем запросы
        predators_count = session.query(Player).filter_by(game_id=game.id, team="predators").count()
        herbivores_count = session.query(Player).filter_by(game_id=game.id, team="herbivores").count()
        wolves_count = session.query(Player).filter_by(game_id=game.id, role="wolf").count()
        
        if predators_count == 2 and herbivores_count == 3 and wolves_count == 1:
            print("✅ Запросы к SQLite работают корректно")
            session.close()
            return True
        else:
            print(f"❌ Неверные результаты запросов: predators={predators_count}, herbivores={herbivores_count}, wolves={wolves_count}")
            session.close()
            return False
            
    except Exception as e:
        print(f"❌ Ошибка запросов к SQLite: {e}")
        traceback.print_exc()
        return False

def main():
    """Основная функция тестирования"""
    print("🔧 Переменные окружения установлены для тестирования")
    
    tests_passed = 0
    total_tests = 5
    
    # Тест 1: Импорты
    if test_sqlite_imports():
        tests_passed += 1
    
    # Тест 2: Подключение
    if test_sqlite_connection():
        tests_passed += 1
    
    # Тест 3: Модели
    if test_sqlite_models():
        tests_passed += 1
    
    # Тест 4: Операции
    if test_sqlite_operations():
        tests_passed += 1
    
    # Тест 5: Запросы
    if test_sqlite_queries():
        tests_passed += 1
    
    # Результаты
    print(f"\n🏁 Тестирование завершено!")
    print(f"📊 Пройдено тестов: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 ВСЕ ТЕСТЫ SQLITE ПРОЙДЕНЫ!")
        print("✅ SQLite база данных работает корректно")
        print("✅ Модели создаются и сохраняются")
        print("✅ Запросы выполняются правильно")
        return True
    else:
        print("⚠️ Некоторые тесты SQLite не прошли. Проверьте ошибки выше.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
