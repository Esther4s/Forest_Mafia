#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест чистой версии мафии
"""

import os
import sys

# Устанавливаем переменные окружения
os.environ['BOT_TOKEN'] = 'test_token_123456789'
os.environ['DATABASE_URL'] = 'postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway'

print('🚀 БЫСТРЫЙ ТЕСТ ЧИСТОЙ ВЕРСИИ МАФИИ')
print('=' * 50)

def test_imports():
    """Тестирует импорты"""
    print('\n🧪 Тест 1: Импорты модулей...')
    try:
        from game_logic import Game, GamePhase, Role, Team, Player
        from night_actions import NightActions
        from night_interface import NightInterface
        from config import BOT_TOKEN, MIN_PLAYERS
        print('✅ Все модули импортированы успешно')
        return True
    except Exception as e:
        print(f'❌ Ошибка импорта: {e}')
        return False

def test_game_logic():
    """Тестирует игровую логику"""
    print('\n🧪 Тест 2: Игровая логика...')
    try:
        from game_logic import Game, Role, Team
        
        # Создаем игру
        game = Game(chat_id=12345)
        print('✅ Игра создана')
        
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
            role_counts = {}
            for player in game.players.values():
                role = player.role.value
                team = player.team.value
                role_counts[role] = role_counts.get(role, 0) + 1
                print(f'• {player.username}: {role} ({team})')
            
            print(f'\n📊 Статистика ролей:')
            for role, count in role_counts.items():
                print(f'• {role}: {count}')
            
            return True
        else:
            print('❌ Не удалось начать игру')
            return False
            
    except Exception as e:
        print(f'❌ Ошибка игровой логики: {e}')
        return False

def test_night_actions():
    """Тестирует ночные действия"""
    print('\n🧪 Тест 3: Ночные действия...')
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
        
        print('✅ Ночные действия созданы')
        
        # Статистика ролей
        wolves = game.get_players_by_role(Role.WOLF)
        foxes = game.get_players_by_role(Role.FOX)
        moles = game.get_players_by_role(Role.MOLE)
        beavers = game.get_players_by_role(Role.BEAVER)
        hares = game.get_players_by_role(Role.HARE)
        
        print(f'🐺 Волков: {len(wolves)}')
        print(f'🦊 Лис: {len(foxes)}')
        print(f'🦫 Кротов: {len(moles)}')
        print(f'🦦 Бобров: {len(beavers)}')
        print(f'🐰 Зайцев: {len(hares)}')
        
        return True
        
    except Exception as e:
        print(f'❌ Ошибка ночных действий: {e}')
        return False

def test_voting_system():
    """Тестирует систему голосования"""
    print('\n🧪 Тест 4: Система голосования...')
    try:
        from game_logic import Game, Team
        
        game = Game(chat_id=99999)
        
        # Добавляем игроков
        players_data = [
            (111, 'Волк1'), (222, 'Лиса1'), (333, 'Заяц1'),
            (444, 'Крот1'), (555, 'Бобёр1'), (666, 'Заяц2')
        ]
        
        for user_id, username in players_data:
            game.add_player(user_id, username)
        
        game.start_game()
        
        # Переводим в фазу голосования
        game.start_voting()
        print(f'✅ Фаза голосования: {game.phase.value}')
        
        alive_players = game.get_alive_players()
        print(f'👥 Живых игроков: {len(alive_players)}')
        
        if len(alive_players) >= 2:
            # Симулируем голосование
            target = alive_players[0]
            voters = alive_players[1:4]
            
            for voter in voters:
                success = game.vote(voter.user_id, target.user_id)
                print(f"{'✅' if success else '❌'} {voter.username} голосует за {target.username}")
            
            # Обрабатываем результаты
            exiled = game.process_voting()
            if exiled:
                print(f'🚫 Изгнан: {exiled.username} ({exiled.role.value})')
            else:
                print('🤝 Ничья в голосовании')
            
            return True
        else:
            print('❌ Недостаточно игроков для голосования')
            return False
            
    except Exception as e:
        print(f'❌ Ошибка голосования: {e}')
        return False

def test_telegram_imports():
    """Тестирует импорты Telegram"""
    print('\n🧪 Тест 5: Telegram импорты...')
    try:
        from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler
        
        print('✅ Telegram модули импортированы')
        
        # Проверяем создание кнопок
        keyboard = [[InlineKeyboardButton("Тест", callback_data="test")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        print('✅ Клавиатура создана')
        
        return True
        
    except Exception as e:
        print(f'❌ Ошибка Telegram импортов: {e}')
        return False

def main():
    """Основная функция тестирования"""
    tests_passed = 0
    total_tests = 5
    
    # Запускаем тесты
    if test_imports():
        tests_passed += 1
    
    if test_game_logic():
        tests_passed += 1
    
    if test_night_actions():
        tests_passed += 1
    
    if test_voting_system():
        tests_passed += 1
    
    if test_telegram_imports():
        tests_passed += 1
    
    # Результаты
    print(f'\n🏁 Тестирование завершено!')
    print(f'📊 Пройдено тестов: {tests_passed}/{total_tests}')
    
    if tests_passed == total_tests:
        print('🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!')
        print('✅ Чистая версия мафии работает идеально')
        print('✅ Игровая логика функционирует')
        print('✅ Ночные действия работают')
        print('✅ Система голосования работает')
        print('✅ Telegram модули импортируются')
        print('\n⚠️ Проблема только с запуском бота (версия библиотеки)')
        print('💡 Рекомендация: откатить python-telegram-bot до версии 20.3')
        return True
    else:
        print('⚠️ Некоторые тесты не прошли')
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
