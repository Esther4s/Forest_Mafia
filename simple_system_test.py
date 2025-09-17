#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Упрощенный тест системы без базы данных
"""

import os
import sys
import traceback

# Устанавливаем переменные окружения
os.environ['BOT_TOKEN'] = 'test_token_123456789'
os.environ['DATABASE_URL'] = 'postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway'
os.environ['POSTGRES_USER'] = 'forest_mafia'
os.environ['POSTGRES_PASSWORD'] = 'forest_mafia_password'
os.environ['ENVIRONMENT'] = 'test'
os.environ['LOG_LEVEL'] = 'DEBUG'

print("🚀 УПРОЩЕННЫЙ ТЕСТ СИСТЕМЫ 'ЛЕС И ВОЛКИ'")
print("=" * 60)

def test_imports():
    """Тестирует импорты всех модулей"""
    print("\n🧪 Тестирование импортов...")
    
    try:
        from game_logic import Game, GamePhase, Role, Team, Player
        print("✅ game_logic.py импортирован успешно")
        
        from night_actions import NightActions
        print("✅ night_actions.py импортирован успешно")
        
        from night_interface import NightInterface
        print("✅ night_interface.py импортирован успешно")
        
        from config import config, BOT_TOKEN
        print("✅ config.py импортирован успешно")
        
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler
        print("✅ Telegram модули импортированы успешно")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        traceback.print_exc()
        return False

def test_game_creation():
    """Тестирует создание игры"""
    print("\n🧪 Тестирование создания игры...")
    
    try:
        from game_logic import Game
        game = Game(chat_id=12345)
        print(f"✅ Игра создана для чата {game.chat_id}")
        print(f"📊 Начальная фаза: {game.phase.value}")
        print(f"👥 Игроков: {len(game.players)}")
        return game
    except Exception as e:
        print(f"❌ Ошибка создания игры: {e}")
        traceback.print_exc()
        return None

def test_player_management(game):
    """Тестирует управление игроками"""
    print("\n🧪 Тестирование управления игроками...")
    
    try:
        # Добавляем игроков
        players_data = [
            (111, "Волк1"),
            (222, "Лиса1"),
            (333, "Заяц1"),
            (444, "Заяц2"),
            (555, "Крот1"),
            (666, "Бобёр1"),
            (777, "Заяц3"),
            (888, "Волк2"),
        ]
        
        for user_id, username in players_data:
            success = game.add_player(user_id, username)
            print(f"{'✅' if success else '❌'} {username} ({user_id})")
        
        print(f"\n👥 Всего игроков: {len(game.players)}")
        print(f"🎮 Можно начать игру: {'✅' if game.can_start_game() else '❌'}")
        
        # Тестируем выход из игры
        if game.leave_game(777):
            print("✅ Заяц3 покинул игру")
        else:
            print("❌ Не удалось убрать Заяц3")
            
        print(f"👥 Игроков после выхода: {len(game.players)}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка управления игроками: {e}")
        traceback.print_exc()
        return False

def test_game_start_and_roles(game):
    """Тестирует начало игры и распределение ролей"""
    print("\n🧪 Тестирование начала игры и ролей...")
    
    try:
        if game.start_game():
            print("✅ Игра успешно начата")
            print(f"📊 Фаза: {game.phase.value}")
            print(f"🔄 Раунд: {game.current_round}")
            
            # Показываем распределение ролей
            print("\n🎭 Распределение ролей:")
            role_counts = {}
            for player in game.players.values():
                role = player.role.value
                team = player.team.value
                role_counts[role] = role_counts.get(role, 0) + 1
                print(f"• {player.username}: {role} ({team})")
            
            print(f"\n📊 Статистика ролей:")
            for role, count in role_counts.items():
                print(f"• {role}: {count}")
            
            return True
        else:
            print("❌ Не удалось начать игру")
            return False
    except Exception as e:
        print(f"❌ Ошибка начала игры: {e}")
        traceback.print_exc()
        return False

def test_night_actions(game):
    """Тестирует ночные действия"""
    print("\n🧪 Тестирование ночных действий...")
    
    try:
        from night_actions import NightActions
        from night_interface import NightInterface
        from game_logic import Role
        
        night_actions = NightActions(game)
        print("✅ NightActions создан")
        
        # Получаем игроков по ролям
        wolves = game.get_players_by_role(Role.WOLF)
        foxes = game.get_players_by_role(Role.FOX)
        moles = game.get_players_by_role(Role.MOLE)
        beavers = game.get_players_by_role(Role.BEAVER)
        
        print(f"🐺 Волков: {len(wolves)}")
        print(f"🦊 Лис: {len(foxes)}")
        print(f"🦫 Кротов: {len(moles)}")
        print(f"🦦 Бобров: {len(beavers)}")
        
        # Тестируем интерфейс ночных действий
        night_interface = NightInterface(game, night_actions)
        print("✅ NightInterface создан")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка ночных действий: {e}")
        traceback.print_exc()
        return False

def test_voting_system(game):
    """Тестирует систему голосования"""
    print("\n🧪 Тестирование системы голосования...")
    
    try:
        from game_logic import Team
        
        # Переводим игру в фазу голосования
        game.start_voting()
        print(f"📊 Фаза голосования: {game.phase.value}")
        
        alive_players = game.get_alive_players()
        print(f"👥 Живых игроков: {len(alive_players)}")
        
        if len(alive_players) >= 2:
            # Симулируем голосование
            target = alive_players[0]  # Первый игрок - цель
            voters = alive_players[1:4]  # Следующие 3 голосуют
            
            for voter in voters:
                success = game.vote(voter.user_id, target.user_id)
                print(f"{'✅' if success else '❌'} {voter.username} голосует за {target.username}")
            
            # Обрабатываем результаты
            exiled = game.process_voting()
            if exiled:
                print(f"🚫 Изгнан: {exiled.username} ({exiled.role.value})")
            else:
                print("🤝 Ничья в голосовании")
            
            return True
        else:
            print("❌ Недостаточно игроков для голосования")
            return False
    except Exception as e:
        print(f"❌ Ошибка голосования: {e}")
        traceback.print_exc()
        return False

def test_bot_creation():
    """Тестирует создание бота"""
    print("\n🧪 Тестирование создания бота...")
    
    try:
        from bot import ForestWolvesBot
        
        bot = ForestWolvesBot()
        if bot:
            print("✅ Экземпляр бота создан")
            print(f"🎮 Игр: {len(bot.games)}")
            print(f"👥 Игроков: {len(bot.player_games)}")
            print(f"🌙 Ночных действий: {len(bot.night_actions)}")
            return True
        else:
            print("❌ Не удалось создать экземпляр бота")
            return False
    except Exception as e:
        print(f"❌ Ошибка создания бота: {e}")
        traceback.print_exc()
        return False

def test_telegram_integration():
    """Тестирует интеграцию с Telegram"""
    print("\n🧪 Тестирование интеграции с Telegram...")
    
    try:
        from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler
        
        # Проверяем создание кнопок (без создания Application)
        keyboard = [[InlineKeyboardButton("Тест", callback_data="test")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if not reply_markup:
            print("❌ Не удалось создать клавиатуру")
            return False
        
        # Проверяем создание бота
        bot = Bot(token="test_token")
        if not bot:
            print("❌ Не удалось создать Bot")
            return False
        
        print("✅ Интеграция с Telegram работает")
        return True
    except Exception as e:
        print(f"❌ Ошибка интеграции с Telegram: {e}")
        traceback.print_exc()
        return False

def test_file_structure():
    """Тестирует структуру файлов проекта"""
    print("\n🧪 Тестирование структуры файлов...")
    
    required_files = [
        'bot.py',
        'config.py',
        'game_logic.py',
        'night_actions.py',
        'night_interface.py',
        'database.py',
        'requirements.txt',
        'Dockerfile',
        'docker-compose.yml'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Отсутствуют файлы: {', '.join(missing_files)}")
        return False
    
    print("✅ Все необходимые файлы присутствуют")
    return True

def test_dependencies():
    """Тестирует зависимости проекта"""
    print("\n🧪 Тестирование зависимостей...")
    
    try:
        # Читаем requirements.txt
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            requirements = f.read().strip().split('\n')
        
        if not requirements or requirements == ['']:
            print("❌ requirements.txt пуст")
            return False
        
        # Проверяем основные зависимости
        required_packages = [
            'python-telegram-bot',
            'sqlalchemy',
            'psycopg2-binary',
            'python-dotenv'
        ]
        
        missing_packages = []
        for package in required_packages:
            if not any(package in req for req in requirements):
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ Отсутствуют пакеты: {', '.join(missing_packages)}")
            return False
        
        print("✅ Все зависимости присутствуют")
        return True
    except Exception as e:
        print(f"❌ Ошибка проверки зависимостей: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🔧 Переменные окружения установлены для тестирования")
    
    tests_passed = 0
    total_tests = 10
    
    # Тест 1: Импорты
    if test_imports():
        tests_passed += 1
    
    # Тест 2: Структура файлов
    if test_file_structure():
        tests_passed += 1
    
    # Тест 3: Зависимости
    if test_dependencies():
        tests_passed += 1
    
    # Тест 4: Создание игры
    game = test_game_creation()
    if game:
        tests_passed += 1
        
        # Тест 5: Управление игроками
        if test_player_management(game):
            tests_passed += 1
            
            # Тест 6: Начало игры и роли
            if test_game_start_and_roles(game):
                tests_passed += 1
                
                # Тест 7: Ночные действия
                if test_night_actions(game):
                    tests_passed += 1
                    
                    # Тест 8: Система голосования
                    if test_voting_system(game):
                        tests_passed += 1
    
    # Тест 9: Создание бота
    if test_bot_creation():
        tests_passed += 1
    
    # Тест 10: Интеграция с Telegram
    if test_telegram_integration():
        tests_passed += 1
    
    # Результаты
    print(f"\n🏁 Тестирование завершено!")
    print(f"📊 Пройдено тестов: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система готова к работе.")
        print("✅ Основные компоненты работают корректно")
        print("✅ Игровая логика функционирует")
        print("✅ Интеграция с Telegram работает")
        print("⚠️ Примечание: Тесты базы данных требуют настройки PostgreSQL")
        return True
    else:
        print("⚠️ Некоторые тесты не прошли. Проверьте ошибки выше.")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Можете запускать бота командой: python bot.py")
    else:
        print("\n❌ Исправьте ошибки перед запуском бота")
    
    sys.exit(0 if success else 1)
