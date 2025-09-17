#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест готовности системы к деплою
"""

import os
import sys

# Устанавливаем переменные окружения
os.environ['BOT_TOKEN'] = 'test_token_123456789'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'
os.environ['POSTGRES_USER'] = 'forest_mafia'
os.environ['POSTGRES_PASSWORD'] = 'forest_mafia_password'
os.environ['ENVIRONMENT'] = 'test'
os.environ['LOG_LEVEL'] = 'DEBUG'

def quick_test():
    """Быстрый тест основных компонентов"""
    print("🚀 БЫСТРЫЙ ТЕСТ ГОТОВНОСТИ К ДЕПЛОЮ")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 5
    
    # Тест 1: Импорты
    print("\n🧪 Тест 1: Импорты модулей...")
    try:
        from game_logic import Game, GamePhase, Role, Team, Player
        from night_actions import NightActions
        from night_interface import NightInterface
        from config import config, BOT_TOKEN
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        print("✅ Все модули импортированы успешно")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
    
    # Тест 2: Создание игры
    print("\n🧪 Тест 2: Создание игры...")
    try:
        game = Game(chat_id=12345)
        print("✅ Игра создана успешно")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка создания игры: {e}")
    
    # Тест 3: Управление игроками
    print("\n🧪 Тест 3: Управление игроками...")
    try:
        game.add_player(111, "ТестИгрок1")
        game.add_player(222, "ТестИгрок2")
        game.add_player(333, "ТестИгрок3")
        print(f"✅ Добавлено {len(game.players)} игроков")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка управления игроками: {e}")
    
    # Тест 4: Начало игры
    print("\n🧪 Тест 4: Начало игры...")
    try:
        if game.start_game():
            print("✅ Игра начата успешно")
            print(f"📊 Фаза: {game.phase.value}")
            print(f"👥 Игроков: {len(game.players)}")
            tests_passed += 1
        else:
            print("❌ Не удалось начать игру")
    except Exception as e:
        print(f"❌ Ошибка начала игры: {e}")
    
    # Тест 5: Ночные действия
    print("\n🧪 Тест 5: Ночные действия...")
    try:
        night_actions = NightActions(game)
        night_interface = NightInterface(game, night_actions)
        print("✅ Ночные действия работают")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Ошибка ночных действий: {e}")
    
    # Результаты
    print("\n" + "=" * 50)
    print(f"🏁 РЕЗУЛЬТАТ: {tests_passed}/{total_tests} тестов пройдено")
    
    if tests_passed == total_tests:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("✅ Система готова к деплою")
        print("📋 Следующие шаги:")
        print("   1. Настройте PostgreSQL")
        print("   2. Установите Docker")
        print("   3. Создайте .env файл с реальными токенами")
        print("   4. Запустите: python bot.py")
        return True
    else:
        print("⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ!")
        print("🔧 Исправьте ошибки перед деплоем")
        return False

if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)
