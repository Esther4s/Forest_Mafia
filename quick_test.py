#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест системы "Лес и Волки"
"""

import os
import sys

def main():
    """Быстрый тест основных компонентов"""
    print("🚀 БЫСТРЫЙ ТЕСТ СИСТЕМЫ 'ЛЕС И ВОЛКИ'")
    print("=" * 50)
    
    # Устанавливаем переменные окружения
    os.environ['BOT_TOKEN'] = 'test_token_123456789'
    os.environ['DATABASE_URL'] = 'postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway'
    
    tests_passed = 0
    total_tests = 4
    
    # Тест 1: Импорты
    print("\n🧪 Тест 1: Импорты модулей...")
    try:
        from game_logic import Game, GamePhase, Role, Team, Player
        from night_actions import NightActions
        from night_interface import NightInterface
        from config import config, BOT_TOKEN
        print("✅ Импорты успешны")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка импортов: {e}")
    
    # Тест 2: Создание игры
    print("\n🧪 Тест 2: Создание игры...")
    try:
        game = Game(chat_id=12345)
        test_players = [
            (111, "Волк1"), (222, "Лиса1"), (333, "Заяц1"), 
            (444, "Заяц2"), (555, "Крот1"), (666, "Бобёр1")
        ]
        
        for user_id, username in test_players:
            game.add_player(user_id, username)
        
        if game.start_game():
            print("✅ Игра создана и начата успешно")
            tests_passed += 1
        else:
            print("❌ Не удалось начать игру")
    except Exception as e:
        print(f"❌ Ошибка создания игры: {e}")
    
    # Тест 3: Ночные действия
    print("\n🧪 Тест 3: Ночные действия...")
    try:
        night_actions = NightActions(game)
        night_interface = NightInterface(game, night_actions)
        print("✅ Ночные действия работают")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка ночных действий: {e}")
    
    # Тест 4: База данных
    print("\n🧪 Тест 4: База данных...")
    try:
        from database_psycopg2 import init_db, execute_query, close_db
        init_db()
        result = execute_query("SELECT 1 as test")
        close_db()
        if result:
            print("✅ База данных работает")
            tests_passed += 1
        else:
            print("❌ База данных не отвечает")
    except Exception as e:
        print(f"❌ Ошибка базы данных: {e}")
    
    # Результаты
    print(f"\n🏁 РЕЗУЛЬТАТЫ:")
    print(f"📊 Пройдено тестов: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система готова к работе.")
        print("✅ Можете запускать бота командой: python bot.py")
        return True
    else:
        print("⚠️ Некоторые тесты не прошли. Проверьте ошибки выше.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)