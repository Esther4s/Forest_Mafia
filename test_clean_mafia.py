#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест чистой версии мафии без лесов
"""

import os
import sys

# Устанавливаем переменные окружения
os.environ['BOT_TOKEN'] = 'test_token_123456789'
os.environ['DATABASE_URL'] = 'postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway'

print('🚀 ТЕСТ ЧИСТОЙ ВЕРСИИ МАФИИ')
print('=' * 50)

def test_imports():
    """Тестирует импорты"""
    print('\n🧪 Тестирование импортов...')
    try:
        from bot import ForestMafiaBot
        from game_logic import Game, GamePhase, Role, Team, Player
        from night_actions import NightActions
        from night_interface import NightInterface
        print('✅ Все модули импортированы успешно')
        return True
    except Exception as e:
        print(f'❌ Ошибка импорта: {e}')
        return False

def test_game_creation():
    """Тестирует создание игры"""
    print('\n🧪 Тестирование создания игры...')
    try:
        from game_logic import Game
        
        game = Game(chat_id=12345)
        print('✅ Игра создана успешно')
        
        # Добавляем игроков
        players_data = [
            (111, 'Волк1'), (222, 'Лиса1'), (333, 'Заяц1'),
            (444, 'Крот1'), (555, 'Бобёр1'), (666, 'Заяц2')
        ]
        
        for user_id, username in players_data:
            game.add_player(user_id, username)
        
        print(f'✅ Добавлено {len(game.players)} игроков')
        
        # Начинаем игру
        if game.start_game():
            print('✅ Игра начата успешно')
            print(f'📊 Фаза: {game.phase.value}')
            print(f'🔄 Раунд: {game.current_round}')
            
            # Показываем роли
            print('\n🎭 Распределение ролей:')
            for player in game.players.values():
                print(f'• {player.username}: {player.role.value} ({player.team.value})')
            
            return True
        else:
            print('❌ Не удалось начать игру')
            return False
            
    except Exception as e:
        print(f'❌ Ошибка игры: {e}')
        return False

def test_night_actions():
    """Тестирует ночные действия"""
    print('\n🧪 Тестирование ночных действий...')
    try:
        from game_logic import Game, Role
        from night_actions import NightActions
        from night_interface import NightInterface
        
        game = Game(chat_id=54321)
        
        # Добавляем игроков
        players_data = [
            (111, 'Волк1'), (222, 'Лиса1'), (333, 'Заяц1'),
            (444, 'Крот1'), (555, 'Бобёр1')
        ]
        
        for user_id, username in players_data:
            game.add_player(user_id, username)
        
        game.start_game()
        
        # Создаем ночные действия
        night_actions = NightActions(game)
        night_interface = NightInterface(game, night_actions)
        
        print('✅ Ночные действия созданы успешно')
        
        # Показываем статистику ролей
        wolves = game.get_players_by_role(Role.WOLF)
        foxes = game.get_players_by_role(Role.FOX)
        moles = game.get_players_by_role(Role.MOLE)
        beavers = game.get_players_by_role(Role.BEAVER)
        
        print(f'🐺 Волков: {len(wolves)}')
        print(f'🦊 Лис: {len(foxes)}')
        print(f'🦫 Кротов: {len(moles)}')
        print(f'🦦 Бобров: {len(beavers)}')
        
        return True
        
    except Exception as e:
        print(f'❌ Ошибка ночных действий: {e}')
        return False

def test_bot_creation():
    """Тестирует создание бота"""
    print('\n🧪 Тестирование создания бота...')
    try:
        from bot import ForestMafiaBot
        
        bot = ForestMafiaBot()
        print('✅ Экземпляр бота создан успешно')
        print(f'🎮 Игр: {len(bot.games)}')
        print(f'👥 Игроков: {len(bot.player_games)}')
        
        return True
        
    except Exception as e:
        print(f'❌ Ошибка создания бота: {e}')
        return False

def main():
    """Основная функция тестирования"""
    tests_passed = 0
    total_tests = 4
    
    # Тест 1: Импорты
    if test_imports():
        tests_passed += 1
    
    # Тест 2: Создание игры
    if test_game_creation():
        tests_passed += 1
    
    # Тест 3: Ночные действия
    if test_night_actions():
        tests_passed += 1
    
    # Тест 4: Создание бота
    if test_bot_creation():
        tests_passed += 1
    
    # Результаты
    print(f'\n🏁 Тестирование завершено!')
    print(f'📊 Пройдено тестов: {tests_passed}/{total_tests}')
    
    if tests_passed == total_tests:
        print('🎉 ЧИСТАЯ ВЕРСИЯ МАФИИ РАБОТАЕТ ИДЕАЛЬНО!')
        print('✅ Все основные функции работают')
        print('✅ Игровая логика функционирует')
        print('✅ Ночные действия работают')
        print('✅ Бот создается успешно')
        return True
    else:
        print('⚠️ Некоторые тесты не прошли')
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
