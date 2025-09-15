#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для проверки состояния базы данных
"""

import os
import sys
from database import init_database, get_db_session, Game, Player, GameEvent
from database_services import GameService, PlayerService
from config import DATABASE_URL

def check_database():
    """Проверяет состояние базы данных"""
    print("🔍 Проверка базы данных...")
    
    try:
        # Инициализируем базу данных
        print(f"🔗 DATABASE_URL: {DATABASE_URL}")
        db_manager = init_database(DATABASE_URL)
        
        # Получаем сессию
        session = get_db_session()
        
        try:
            # Проверяем таблицы
            print("\n📊 Проверка таблиц:")
            
            # Проверяем игры
            games_count = session.query(Game).count()
            print(f"🎮 Игр в базе: {games_count}")
            
            if games_count > 0:
                games = session.query(Game).limit(5).all()
                for game in games:
                    print(f"  - Игра {game.id}: чат {game.chat_id}, статус {game.status}, фаза {game.phase}")
            
            # Проверяем игроков
            players_count = session.query(Player).count()
            print(f"👤 Игроков в базе: {players_count}")
            
            if players_count > 0:
                players = session.query(Player).limit(5).all()
                for player in players:
                    print(f"  - Игрок {player.user_id}: игра {player.game_id}, роль {player.role}")
            
            # Проверяем события
            events_count = session.query(GameEvent).count()
            print(f"📝 Событий в базе: {events_count}")
            
            if events_count > 0:
                events = session.query(GameEvent).limit(5).all()
                for event in events:
                    print(f"  - Событие {event.event_type}: игра {event.game_id}")
            
            print("\n✅ База данных работает корректно!")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Ошибка при проверке базы данных: {e}")
        import traceback
        traceback.print_exc()

def test_create_game():
    """Тестирует создание игры"""
    print("\n🧪 Тестирование создания игры...")
    
    try:
        # Создаем тестовую игру
        game = GameService.create_game(
            chat_id=-1001234567890,  # Тестовый чат
            thread_id=None,
            settings={"test": True}
        )
        
        print(f"✅ Тестовая игра создана: {game.id}")
        
        # Добавляем тестового игрока
        player = PlayerService.add_player_to_game(
            game_id=game.id,
            user_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        
        print(f"✅ Тестовый игрок добавлен: {player.id}")
        
        # Удаляем тестовые данные
        session = get_db_session()
        try:
            session.delete(player)
            session.delete(game)
            session.commit()
            print("✅ Тестовые данные удалены")
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()
    test_create_game()
