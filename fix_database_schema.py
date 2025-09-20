#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для исправления схемы базы данных
Добавляет недостающие колонки в существующие таблицы
"""

import os
import sys
from sqlalchemy import create_engine, text
from database import Base

def fix_database_schema():
    """Исправляет схему базы данных"""
    print("🔧 Исправление схемы базы данных...")
    
    # Устанавливаем переменные окружения
    os.environ['BOT_TOKEN'] = '8314318680:AAG1CDOB-SQhyFfCpqDIBm-U8ANz6Ggw94k'
    os.environ['DATABASE_URL'] = 'postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway'
    
    database_url = os.environ['DATABASE_URL']
    print(f"🔗 DATABASE_URL: {database_url}")
    
    try:
        # Создаем подключение к базе данных
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Начинаем транзакцию
            trans = connection.begin()
            
            try:
                print("\n📊 Проверка существующих таблиц...")
                
                # Проверяем структуру таблицы players
                result = connection.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'players' 
                    ORDER BY ordinal_position
                """))
                
                existing_columns = [row[0] for row in result]
                print(f"Существующие колонки в таблице players: {existing_columns}")
                
                # Добавляем недостающие колонки
                missing_columns = []
                
                if 'is_online' not in existing_columns:
                    missing_columns.append("is_online BOOLEAN DEFAULT TRUE")
                
                if 'joined_at' not in existing_columns:
                    missing_columns.append("joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                
                if 'died_at' not in existing_columns:
                    missing_columns.append("died_at TIMESTAMP")
                
                if 'death_reason' not in existing_columns:
                    missing_columns.append("death_reason VARCHAR(50)")
                
                if missing_columns:
                    print(f"\n➕ Добавляем недостающие колонки: {missing_columns}")
                    
                    for column_def in missing_columns:
                        alter_sql = f"ALTER TABLE players ADD COLUMN {column_def}"
                        print(f"Выполняем: {alter_sql}")
                        connection.execute(text(alter_sql))
                    
                    print("✅ Недостающие колонки добавлены успешно")
                else:
                    print("✅ Все необходимые колонки уже существуют")
                
                # Проверяем другие таблицы
                print("\n🔍 Проверка других таблиц...")
                
                # Проверяем таблицу games
                result = connection.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'games' 
                    ORDER BY ordinal_position
                """))
                
                games_columns = [row[0] for row in result]
                print(f"Колонки в таблице games: {games_columns}")
                
                # Проверяем таблицу game_events
                result = connection.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'game_events' 
                    ORDER BY ordinal_position
                """))
                
                events_columns = [row[0] for row in result]
                print(f"Колонки в таблице game_events: {events_columns}")
                
                # Добавляем недостающие колонки в game_events
                events_missing = []
                if 'event_data' not in events_columns:
                    events_missing.append("event_data JSON")
                
                if events_missing:
                    print(f"➕ Добавляем недостающие колонки в game_events: {events_missing}")
                    for column_def in events_missing:
                        alter_sql = f"ALTER TABLE game_events ADD COLUMN {column_def}"
                        print(f"Выполняем: {alter_sql}")
                        connection.execute(text(alter_sql))
                
                # Проверяем таблицу player_actions
                result = connection.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'player_actions' 
                    ORDER BY ordinal_position
                """))
                
                actions_columns = [row[0] for row in result]
                print(f"Колонки в таблице player_actions: {actions_columns}")
                
                # Добавляем недостающие колонки в player_actions
                actions_missing = []
                if 'round_number' not in actions_columns:
                    actions_missing.append("round_number INTEGER NOT NULL DEFAULT 0")
                if 'phase' not in actions_columns:
                    actions_missing.append("phase VARCHAR(20) NOT NULL DEFAULT 'night'")
                
                if actions_missing:
                    print(f"➕ Добавляем недостающие колонки в player_actions: {actions_missing}")
                    for column_def in actions_missing:
                        alter_sql = f"ALTER TABLE player_actions ADD COLUMN {column_def}"
                        print(f"Выполняем: {alter_sql}")
                        connection.execute(text(alter_sql))
                
                # Проверяем таблицу votes
                result = connection.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'votes' 
                    ORDER BY ordinal_position
                """))
                
                votes_columns = [row[0] for row in result]
                print(f"Колонки в таблице votes: {votes_columns}")
                
                # Добавляем недостающие колонки в votes
                votes_missing = []
                if 'phase' not in votes_columns:
                    votes_missing.append("phase VARCHAR(20) NOT NULL DEFAULT 'voting'")
                
                if votes_missing:
                    print(f"➕ Добавляем недостающие колонки в votes: {votes_missing}")
                    for column_def in votes_missing:
                        alter_sql = f"ALTER TABLE votes ADD COLUMN {column_def}"
                        print(f"Выполняем: {alter_sql}")
                        connection.execute(text(alter_sql))
                
                # Проверяем таблицу player_stats
                result = connection.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'player_stats' 
                    ORDER BY ordinal_position
                """))
                
                stats_columns = [row[0] for row in result]
                print(f"Колонки в таблице player_stats: {stats_columns}")
                
                # Проверяем таблицу bot_settings
                result = connection.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'bot_settings' 
                    ORDER BY ordinal_position
                """))
                
                settings_columns = [row[0] for row in result]
                print(f"Колонки в таблице bot_settings: {settings_columns}")
                
                # Коммитим изменения
                trans.commit()
                print("\n✅ Схема базы данных исправлена успешно!")
                
            except Exception as e:
                print(f"❌ Ошибка при исправлении схемы: {e}")
                trans.rollback()
                raise
                
    except Exception as e:
        print(f"❌ Ошибка при подключении к базе данных: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_fixed_schema():
    """Тестирует исправленную схему"""
    print("\n🧪 Тестирование исправленной схемы...")
    
    try:
        from database import init_database, get_db_session, Game, Player, GameEvent
        
        # Инициализируем базу данных
        db_manager = init_database(os.environ['DATABASE_URL'])
        
        # Получаем сессию
        session = get_db_session()
        
        try:
            # Тестируем запросы
            games_count = session.query(Game).count()
            print(f"🎮 Игр в базе: {games_count}")
            
            players_count = session.query(Player).count()
            print(f"👤 Игроков в базе: {players_count}")
            
            events_count = session.query(GameEvent).count()
            print(f"📝 Событий в базе: {events_count}")
            
            print("✅ Схема работает корректно!")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании схемы: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🌲 Forest Mafia Bot - Исправление схемы базы данных")
    print("=" * 60)
    
    if fix_database_schema():
        if test_fixed_schema():
            print("\n🎉 Схема базы данных исправлена и протестирована успешно!")
        else:
            print("\n💥 Тест исправленной схемы не прошел.")
            sys.exit(1)
    else:
        print("\n💥 Исправление схемы не удалось.")
        sys.exit(1)
