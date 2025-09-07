#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы бота Лес и Волки
"""

import asyncio
from game_logic import Game, GamePhase, Role, Team
from night_actions import NightActions

def test_game_logic():
    """Тестирует основную игровую логику"""
    print("🧪 Тестирование игровой логики...")
    
    # Создаем игру
    game = Game(chat_id=12345)
    
    # Добавляем игроков
    players_data = [
        (111, "Player1"),
        (222, "Player2"),
        (333, "Player3"),
        (444, "Player4"),
        (555, "Player5"),
        (666, "Player6"),
    ]
    
    for user_id, username in players_data:
        success = game.add_player(user_id, username)
        print(f"Добавлен игрок {username}: {'✅' if success else '❌'}")
    
    print(f"\n👥 Всего игроков: {len(game.players)}")
    print(f"🎮 Можно начать игру: {'✅' if game.can_start_game() else '❌'}")
    
    # Начинаем игру
    if game.start_game():
        print("🎮 Игра началась!")
        print(f"📊 Фаза: {game.phase.value}")
        print(f"🔄 Раунд: {game.current_round}")
        
        # Проверяем распределение ролей
        print("\n🎭 Распределение ролей:")
        for player in game.players.values():
            print(f"• {player.username}: {player.role.value} ({player.team.value})")
        
        # Проверяем команды
        predators = game.get_players_by_team(Team.PREDATORS)
        herbivores = game.get_players_by_team(Team.HERBIVORES)
        
        print(f"\n🐺 Хищники ({len(predators)}):")
        for player in predators:
            print(f"• {player.username} ({player.role.value})")
        
        print(f"\n🐰 Травоядные ({len(herbivores)}):")
        for player in herbivores:
            print(f"• {player.username} ({player.role.value})")
        
        # Тестируем ночные действия
        print("\n🌙 Тестирование ночных действий...")
        night_actions = NightActions(game)
        
        # Симулируем действия волков
        wolves = game.get_players_by_role(Role.WOLF)
        if wolves:
            target = [p for p in game.players.values() if p.role != Role.WOLF][0]
            night_actions.set_wolf_target(wolves[0].user_id, target.user_id)
            print(f"🐺 Волк {wolves[0].username} выбрал цель: {target.username}")
        
        # Симулируем действия лисы
        foxes = game.get_players_by_role(Role.FOX)
        if foxes:
            target = [p for p in game.players.values() if p.role != Role.BEAVER][0]
            night_actions.set_fox_target(foxes[0].user_id, target.user_id)
            print(f"🦊 Лиса {foxes[0].username} выбрала цель: {target.username}")
        
        # Симулируем действия крота
        moles = game.get_players_by_role(Role.MOLE)
        if moles:
            target = [p for p in game.players.values() if p.user_id != moles[0].user_id][0]
            night_actions.set_mole_target(moles[0].user_id, target.user_id)
            print(f"🦫 Крот {moles[0].username} выбрал цель: {target.username}")
        
        # Обрабатываем ночные действия
        results = night_actions.process_all_actions()
        print("\n📊 Результаты ночи:")
        for category, actions in results.items():
            if actions:
                print(f"{category}:")
                for action in actions:
                    print(f"  • {action}")
        
        # Проверяем состояние после ночи
        print(f"\n👥 Живых игроков после ночи: {len(game.get_alive_players())}")
        
        # Начинаем день
        game.start_day()
        print(f"☀️ Начался день. Фаза: {game.phase.value}")
        
        # Начинаем голосование
        game.start_voting()
        print(f"🗳️ Началось голосование. Фаза: {game.phase.value}")
        
        # Симулируем голоса
        alive_players = game.get_alive_players()
        if len(alive_players) > 1:
            target = alive_players[1]  # Второй живой игрок
            for voter in alive_players[:3]:  # Первые трое голосуют
                if voter.user_id != target.user_id:
                    game.vote(voter.user_id, target.user_id)
                    print(f"🗳️ {voter.username} проголосовал за {target.username}")
        
        # Обрабатываем голосование
        exiled = game.process_voting()
        if exiled:
            print(f"🚫 Изгнан: {exiled.username} ({exiled.role.value})")
        else:
            print("🤝 Ничья в голосовании")
        
        # Проверяем конец игры
        winner = game.check_game_end()
        if winner:
            winner_text = "Травоядные" if winner == Team.HERBIVORES else "Хищники"
            print(f"🏆 Победили: {winner_text}!")
        else:
            print("🔄 Игра продолжается...")
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    test_game_logic()
