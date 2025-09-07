#!/usr/bin/env python3
"""
Тест новых функций бота Лес и Волки
"""

from game_logic import Game, GamePhase, Role, Team

def test_leave_game():
    """Тестирует механизм выхода из игры"""
    print("🧪 Тестирование механизма выхода из игры...")
    
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
    
    # Игрок покидает игру
    if game.leave_game(111):
        print("✅ Player1 успешно покинул игру")
        print(f"👥 Игроков после выхода: {len(game.players)}")
    else:
        print("❌ Player1 не смог покинуть игру")
    
    # Проверяем, можно ли начать игру
    print(f"🎮 Можно начать игру: {'✅' if game.can_start_game() else '❌'}")
    
    # Еще один игрок покидает игру
    if game.leave_game(222):
        print("✅ Player2 успешно покинул игру")
        print(f"👥 Игроков после выхода: {len(game.players)}")
        print(f"🎮 Можно начать игру: {'✅' if game.can_start_game() else '❌'}")
    else:
        print("❌ Player2 не смог покинуть игру")

def test_game_phases():
    """Тестирует фазы игры"""
    print("\n🧪 Тестирование фаз игры...")
    
    game = Game(chat_id=12345)
    
    # Добавляем минимальное количество игроков
    for i in range(6):
        game.add_player(100 + i, f"Player{i+1}")
    
    print(f"📊 Фаза до начала: {game.phase.value}")
    
    # Начинаем игру
    if game.start_game():
        print(f"📊 Фаза после начала: {game.phase.value}")
        print(f"🔄 Раунд: {game.current_round}")
        
        # Начинаем день
        game.start_day()
        print(f"📊 Фаза дня: {game.phase.value}")
        
        # Начинаем голосование
        game.start_voting()
        print(f"📊 Фаза голосования: {game.phase.value}")
        
        # Начинаем новую ночь
        game.start_night()
        print(f"📊 Фаза новой ночи: {game.phase.value}")
        print(f"🔄 Раунд: {game.current_round}")
    else:
        print("❌ Не удалось начать игру")

def test_voting_system():
    """Тестирует систему голосования"""
    print("\n🧪 Тестирование системы голосования...")
    
    game = Game(chat_id=12345)
    
    # Добавляем игроков
    for i in range(6):
        game.add_player(100 + i, f"Player{i+1}")
    
    # Начинаем игру
    if game.start_game():
        # Начинаем голосование
        game.start_voting()
        
        # Симулируем голоса
        alive_players = game.get_alive_players()
        if len(alive_players) > 1:
            target = alive_players[1]  # Второй живой игрок
            
            # Первые трое голосуют за цель
            for voter in alive_players[:3]:
                if voter.user_id != target.user_id:
                    success = game.vote(voter.user_id, target.user_id)
                    print(f"🗳️ {voter.username} проголосовал за {target.username}: {'✅' if success else '❌'}")
            
            # Обрабатываем голосование
            exiled = game.process_voting()
            if exiled:
                print(f"🚫 Изгнан: {exiled.username} ({exiled.role.value})")
                print(f"👥 Живых игроков после изгнания: {len(game.get_alive_players())}")
            else:
                print("🤝 Ничья в голосовании")
        else:
            print("❌ Недостаточно игроков для голосования")

if __name__ == "__main__":
    print("🚀 Тестирование новых функций бота 'Лес и Волки'")
    print("=" * 50)
    
    test_leave_game()
    test_game_phases()
    test_voting_system()
    
    print("\n✅ Тестирование новых функций завершено!")
