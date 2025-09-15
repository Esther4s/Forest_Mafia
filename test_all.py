
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Полное тестирование бота Лес и Волки
"""

import asyncio
import sys
import traceback
from game_logic import Game, GamePhase, Role, Team, Player
from night_actions import NightActions
from night_interface import NightInterface
from config import MIN_PLAYERS, BOT_TOKEN

def test_imports():
    """Тестирует импорты всех модулей"""
    print("🧪 Тестирование импортов...")
    
    try:
        # Проверяем основные модули
        from game_logic import Game, GamePhase, Role, Team, Player
        print("✅ game_logic.py импортирован успешно")
        
        from night_actions import NightActions
        print("✅ night_actions.py импортирован успешно")
        
        from night_interface import NightInterface
        print("✅ night_interface.py импортирован успешно")
        
        from config import MIN_PLAYERS, BOT_TOKEN
        print("✅ config.py импортирован успешно")
        
        # Проверяем телеграм модули
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
        game = Game(chat_id=12345)
        print(f"✅ Игра создана для чата {game.chat_id}")
        print(f"📊 Начальная фаза: {game.phase.value}")
        print(f"👥 Игроков: {len(game.players)}")
        return game
    except Exception as e:
        print(f"❌ Ошибка создания игры: {e}")
        traceback.print_exc()
        return None

def test_player_management(game: Game):
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

def test_game_start_and_roles(game: Game):
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

def test_night_actions(game: Game):
    """Тестирует ночные действия"""
    print("\n🧪 Тестирование ночных действий...")
    
    try:
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

def test_voting_system(game: Game):
    """Тестирует систему голосования"""
    print("\n🧪 Тестирование системы голосования...")
    
    try:
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

def test_game_end_conditions(game: Game):
    """Тестирует условия окончания игры"""
    print("\n🧪 Тестирование условий окончания игры...")
    
    try:
        # Проверяем текущее состояние
        winner = game.check_game_end()
        predators = game.get_players_by_team(Team.PREDATORS)
        herbivores = game.get_players_by_team(Team.HERBIVORES)
        
        print(f"🐺 Хищников: {len(predators)}")
        print(f"🐰 Травоядных: {len(herbivores)}")
        print(f"🏆 Победитель: {winner.value if winner else 'Игра продолжается'}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка проверки окончания: {e}")
        traceback.print_exc()
        return False

def test_bot_token():
    """Тестирует токен бота"""
    print("\n🧪 Тестирование токена бота...")
    
    try:
        if BOT_TOKEN and BOT_TOKEN != "your_bot_token_here":
            print("✅ Токен бота настроен")
            print(f"🔑 Токен: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
            return True
        else:
            print("❌ Токен бота не настроен в config.py")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки токена: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск полного тестирования бота 'Лес и Волки'\n")
    
    tests_passed = 0
    total_tests = 6
    
    # Тест 1: Импорты
    if test_imports():
        tests_passed += 1
    
    # Тест 2: Токен
    if test_bot_token():
        tests_passed += 1
    
    # Тест 3: Создание игры
    game = test_game_creation()
    if game:
        tests_passed += 1
        
        # Тест 4: Управление игроками
        if test_player_management(game):
            tests_passed += 1
            
            # Тест 5: Начало игры и роли
            if test_game_start_and_roles(game):
                tests_passed += 1
                
                # Тест 6: Ночные действия
                if test_night_actions(game):
                    tests_passed += 1
    
    # Результаты
    print(f"\n🏁 Тестирование завершено!")
    print(f"📊 Пройдено тестов: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 Все тесты пройдены успешно! Бот готов к работе.")
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
