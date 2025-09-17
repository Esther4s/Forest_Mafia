#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправлений
"""

import os
os.environ['BOT_TOKEN'] = 'test_token_123456789'
os.environ['DATABASE_URL'] = 'postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway'

print('🔧 ТЕСТ ИСПРАВЛЕНИЙ')
print('=' * 40)

# Тест 1: Импорты
print('\n1. Тест импортов...')
try:
    from game_logic import Game, Role, Team, Player
    from night_actions import NightActions
    from night_interface import NightInterface
    from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler
    print('✅ Все импорты работают')
except Exception as e:
    print(f'❌ Ошибка импорта: {e}')

# Тест 2: Создание игры
print('\n2. Тест создания игры...')
try:
    game = Game(chat_id=12345)
    game.add_player(111, 'Волк1')
    game.add_player(222, 'Лиса1')
    game.add_player(333, 'Заяц1')
    game.add_player(444, 'Крот1')
    game.add_player(555, 'Бобёр1')
    game.add_player(666, 'Заяц2')
    
    if game.start_game():
        print('✅ Игра создана и начата')
        print(f'📊 Фаза: {game.phase.value}')
        print(f'👥 Игроков: {len(game.players)}')
        
        # Показываем роли
        print('\n🎭 Роли:')
        for player in game.players.values():
            print(f'• {player.username}: {player.role.value} ({player.team.value})')
    else:
        print('❌ Не удалось начать игру')
except Exception as e:
    print(f'❌ Ошибка игры: {e}')

# Тест 3: Ночные действия
print('\n3. Тест ночных действий...')
try:
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
except Exception as e:
    print(f'❌ Ошибка ночных действий: {e}')

# Тест 4: Telegram
print('\n4. Тест Telegram...')
try:
    bot = Bot(token="test_token")
    keyboard = [[InlineKeyboardButton("Тест", callback_data="test")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    print('✅ Telegram компоненты работают')
except Exception as e:
    print(f'❌ Ошибка Telegram: {e}')

print('\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!')
