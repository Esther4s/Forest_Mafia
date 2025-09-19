#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Пример использования рефакторированной архитектуры
Демонстрирует основные возможности новой системы
"""

import asyncio
import logging
from datetime import datetime

from ..domain.value_objects import ChatId, UserId, Username, GamePhase, Team, Role
from ..domain.entities import Game, Player
from ..application.services import GameService, UserService, VotingService
from ..application.factories import GameFactory, PlayerFactory, ValueObjectFactory
from ..infrastructure.repositories import (
    GameRepositoryImpl, PlayerRepositoryImpl, UserRepositoryImpl,
    GameEventRepositoryImpl, ChatSettingsRepositoryImpl
)
from ..infrastructure.config import Config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_game_flow():
    """Пример игрового процесса"""
    
    # Инициализация репозиториев
    game_repo = GameRepositoryImpl()
    player_repo = PlayerRepositoryImpl()
    user_repo = UserRepositoryImpl()
    event_repo = GameEventRepositoryImpl()
    chat_settings_repo = ChatSettingsRepositoryImpl()
    
    # Инициализация сервисов
    game_service = GameService(game_repo, player_repo, event_repo)
    user_service = UserService(user_repo)
    voting_service = VotingService()
    
    # Инициализация фабрик
    game_factory = GameFactory(None)  # RoleAssignmentService будет добавлен позже
    player_factory = PlayerFactory()
    
    print("🌲 Пример использования рефакторированной архитектуры 🌲\n")
    
    # 1. Создание игры
    print("1. Создание игры...")
    chat_id = ChatId(12345)
    game = game_factory.create_game(chat_id, is_test_mode=True)
    await game_repo.save(game)
    print(f"✅ Игра создана: {game.game_id.value}")
    
    # 2. Добавление игроков
    print("\n2. Добавление игроков...")
    players_data = [
        (UserId(1), Username("Alice"), "Алиса"),
        (UserId(2), Username("Bob"), "Боб"),
        (UserId(3), Username("Charlie"), "Чарли"),
        (UserId(4), Username("Diana"), "Диана"),
        (UserId(5), Username("Eve"), "Ева"),
        (UserId(6), Username("Frank"), "Фрэнк")
    ]
    
    for user_id, username, first_name in players_data:
        # Создаем пользователя
        await user_service.get_or_create_user(user_id, username.value, first_name)
        
        # Добавляем в игру
        success = await game_service.add_player_to_game(game, user_id, username)
        if success:
            print(f"✅ {first_name} присоединился к игре")
        else:
            print(f"❌ {first_name} не смог присоединиться")
    
    print(f"👥 Игроков в игре: {len(game.players)}")
    
    # 3. Начало игры
    print("\n3. Начало игры...")
    if game.can_start_game():
        success = await game_service.start_game(game)
        if success:
            print("✅ Игра началась!")
            print(f"📋 Фаза: {game.phase.value}")
            print(f"🎮 Раунд: {game.current_round}")
        else:
            print("❌ Не удалось начать игру")
    else:
        print("❌ Недостаточно игроков для начала игры")
    
    # 4. Показываем роли игроков
    print("\n4. Роли игроков:")
    for player in game.players.values():
        team_emoji = "🦁" if player.team == Team.PREDATORS else "🌿"
        role_emoji = {
            Role.WOLF: "🐺",
            Role.FOX: "🦊", 
            Role.HARE: "🐰",
            Role.MOLE: "🦫",
            Role.BEAVER: "🦦"
        }.get(player.role, "❓")
        
        print(f"  {role_emoji} {player.username.value} - {player.role.value} ({team_emoji} {player.team.value})")
    
    # 5. Демонстрация голосования
    print("\n5. Демонстрация голосования...")
    game.start_voting()
    
    # Игроки голосуют
    alive_players = list(game.get_alive_players())
    if len(alive_players) >= 2:
        voter = alive_players[0]
        target = alive_players[1]
        
        success = game.vote(voter.user_id, target.user_id)
        if success:
            print(f"✅ {voter.username.value} проголосовал за {target.username.value}")
        
        # Еще один голос
        if len(alive_players) >= 3:
            voter2 = alive_players[2]
            success2 = game.vote(voter2.user_id, target.user_id)
            if success2:
                print(f"✅ {voter2.username.value} проголосовал за {target.username.value}")
    
    # Обрабатываем голосование
    exiled_player = voting_service.process_voting(game)
    if exiled_player:
        print(f"🗳️ Изгнан: {exiled_player.username.value}")
    else:
        print("🗳️ Никто не изгнан")
    
    # 6. Показываем статистику
    print("\n6. Статистика игры:")
    stats = game.get_game_statistics()
    print(f"  👥 Живых игроков: {stats['alive_players']}")
    print(f"  🦁 Хищников: {stats['predators']}")
    print(f"  🌿 Травоядных: {stats['herbivores']}")
    print(f"  🎮 Раунд: {stats['current_round']}")
    
    # 7. Демонстрация работы с пользователями
    print("\n7. Работа с пользователями:")
    test_user_id = UserId(1)
    
    # Получаем баланс
    balance = await user_service.get_balance(test_user_id)
    print(f"💰 Баланс пользователя {test_user_id.value}: {balance} орехов")
    
    # Обновляем баланс
    await user_service.update_balance(test_user_id, 100)
    new_balance = await user_service.get_balance(test_user_id)
    print(f"💰 Новый баланс: {new_balance} орехов")
    
    # Получаем отображаемое имя
    display_name = await user_service.get_display_name(test_user_id, "Alice", "Алиса")
    print(f"👤 Отображаемое имя: {display_name}")
    
    # 8. Завершение игры
    print("\n8. Завершение игры...")
    winner = game.check_game_end()
    if winner:
        print(f"🏆 Победили: {winner.value}")
    else:
        print("🎮 Игра продолжается...")
    
    await game_service.end_game(game, winner, "Демонстрация завершена")
    print("✅ Игра завершена")
    
    print("\n🌲 Пример завершен! 🌲")


async def example_value_objects():
    """Пример работы с Value Objects"""
    
    print("\n🔧 Пример работы с Value Objects:\n")
    
    # Создание Value Objects
    user_id = ValueObjectFactory.create_user_id(12345)
    chat_id = ValueObjectFactory.create_chat_id(67890)
    username = ValueObjectFactory.create_username("test_user")
    
    print(f"User ID: {user_id.value}")
    print(f"Chat ID: {chat_id.value}")
    print(f"Username: {username.value}")
    
    # Работа с припасами
    supplies = ValueObjectFactory.create_supplies(2, 5)
    print(f"Припасы: {supplies.current}/{supplies.maximum}")
    print(f"Критично мало: {supplies.is_critical}")
    
    # Потребление припасов
    new_supplies = supplies.consume(1)
    print(f"После потребления: {new_supplies.current}/{new_supplies.maximum}")
    
    # Добавление припасов
    full_supplies = new_supplies.add(10)
    print(f"После добавления: {full_supplies.current}/{full_supplies.maximum}")
    
    # Длительность игры
    start_time = datetime.now()
    game_duration = ValueObjectFactory.create_game_duration(start_time)
    print(f"Игра началась: {game_duration.start_time}")
    print(f"Завершена: {game_duration.is_finished}")
    print(f"Длительность: {game_duration.total_seconds:.1f} секунд")


async def example_error_handling():
    """Пример обработки ошибок"""
    
    print("\n⚠️ Пример обработки ошибок:\n")
    
    try:
        # Попытка создать некорректный User ID
        invalid_user_id = ValueObjectFactory.create_user_id(-1)
    except ValueError as e:
        print(f"✅ Поймана ошибка валидации: {e}")
    
    try:
        # Попытка создать некорректный Chat ID
        invalid_chat_id = ValueObjectFactory.create_chat_id(0)
    except ValueError as e:
        print(f"✅ Поймана ошибка валидации: {e}")
    
    try:
        # Попытка создать пустой Username
        invalid_username = ValueObjectFactory.create_username("")
    except ValueError as e:
        print(f"✅ Поймана ошибка валидации: {e}")
    
    try:
        # Попытка потребить больше припасов, чем есть
        supplies = ValueObjectFactory.create_supplies(1, 5)
        supplies.consume(10)
    except ValueError as e:
        print(f"✅ Поймана ошибка валидации: {e}")


async def main():
    """Главная функция с примерами"""
    
    print("🚀 Запуск примеров рефакторированной архитектуры\n")
    
    # Пример игрового процесса
    await example_game_flow()
    
    # Пример работы с Value Objects
    await example_value_objects()
    
    # Пример обработки ошибок
    await example_error_handling()
    
    print("\n🎉 Все примеры выполнены успешно!")


if __name__ == "__main__":
    asyncio.run(main())
