#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Миграция для исправления таблицы player_stats в PostgreSQL
Добавляет недостающие колонки статистики игр
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from database import init_database, get_db_session
from sqlalchemy import text

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def fix_player_stats_table():
    """Исправляет таблицу player_stats, добавляя недостающие колонки"""
    print("🔧 Исправление таблицы player_stats...")
    
    try:
        # Инициализируем базу данных
        init_database()
        session = get_db_session()
        
        # Проверяем, какие колонки уже есть
        check_columns_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'player_stats'
        """)
        
        result = session.execute(check_columns_query)
        existing_columns = result.fetchall()
        column_names = [row[0] for row in existing_columns]
        
        print(f"📋 Существующие колонки: {column_names}")
        
        # Проверяем, есть ли колонка player_id (старая структура)
        has_player_id = 'player_id' in column_names
        has_id = 'id' in column_names
        
        if has_player_id and not has_id:
            print(f"⚠️ Обнаружена старая структура с player_id, нужно пересоздать таблицу")
            try:
                # Создаем новую таблицу с правильной структурой
                create_new_table_query = text("""
                    CREATE TABLE player_stats_new (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        total_games INTEGER DEFAULT 0,
                        games_won INTEGER DEFAULT 0,
                        games_lost INTEGER DEFAULT 0,
                        times_wolf INTEGER DEFAULT 0,
                        times_fox INTEGER DEFAULT 0,
                        times_hare INTEGER DEFAULT 0,
                        times_mole INTEGER DEFAULT 0,
                        times_beaver INTEGER DEFAULT 0,
                        kills_made INTEGER DEFAULT 0,
                        votes_received INTEGER DEFAULT 0,
                        last_played TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                session.execute(create_new_table_query)
                
                # Копируем данные из старой таблицы (если есть)
                copy_data_query = text("""
                    INSERT INTO player_stats_new (user_id, total_games, games_won, games_lost, 
                        times_wolf, times_fox, times_hare, times_mole, times_beaver, 
                        kills_made, votes_received, last_played, created_at, updated_at)
                    SELECT user_id, 
                        COALESCE(total_games, 0),
                        COALESCE(games_won, 0),
                        COALESCE(games_lost, 0),
                        COALESCE(times_wolf, 0),
                        COALESCE(times_fox, 0),
                        COALESCE(times_hare, 0),
                        COALESCE(times_mole, 0),
                        COALESCE(times_beaver, 0),
                        COALESCE(kills_made, 0),
                        COALESCE(votes_received, 0),
                        last_played,
                        COALESCE(created_at, CURRENT_TIMESTAMP),
                        COALESCE(updated_at, CURRENT_TIMESTAMP)
                    FROM player_stats
                """)
                session.execute(copy_data_query)
                
                # Удаляем старую таблицу и переименовываем новую
                session.execute(text("DROP TABLE player_stats"))
                session.execute(text("ALTER TABLE player_stats_new RENAME TO player_stats"))
                
                print("✅ Структура таблицы player_stats исправлена (пересоздана)")
            except Exception as e:
                print(f"⚠️ Ошибка при исправлении структуры таблицы: {e}")
        elif has_id:
            # Проверяем тип колонки id
            check_id_type_query = text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'player_stats' AND column_name = 'id'
            """)
            result = session.execute(check_id_type_query)
            id_type = result.fetchone()
            if id_type and id_type[0] != 'integer':
                print(f"⚠️ Колонка id имеет тип {id_type[0]}, нужно изменить на INTEGER")
                try:
                    # Создаем новую таблицу с правильной структурой
                    create_new_table_query = text("""
                        CREATE TABLE player_stats_new (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            total_games INTEGER DEFAULT 0,
                            games_won INTEGER DEFAULT 0,
                            games_lost INTEGER DEFAULT 0,
                            times_wolf INTEGER DEFAULT 0,
                            times_fox INTEGER DEFAULT 0,
                            times_hare INTEGER DEFAULT 0,
                            times_mole INTEGER DEFAULT 0,
                            times_beaver INTEGER DEFAULT 0,
                            kills_made INTEGER DEFAULT 0,
                            votes_received INTEGER DEFAULT 0,
                            last_played TIMESTAMP,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    session.execute(create_new_table_query)
                    
                    # Копируем данные (если есть)
                    copy_data_query = text("""
                        INSERT INTO player_stats_new (user_id, total_games, games_won, games_lost, 
                            times_wolf, times_fox, times_hare, times_mole, times_beaver, 
                            kills_made, votes_received, last_played, created_at, updated_at)
                        SELECT user_id, total_games, games_won, games_lost, 
                            times_wolf, times_fox, times_hare, times_mole, times_beaver, 
                            kills_made, votes_received, last_played, created_at, updated_at
                        FROM player_stats
                    """)
                    session.execute(copy_data_query)
                    
                    # Удаляем старую таблицу и переименовываем новую
                    session.execute(text("DROP TABLE player_stats"))
                    session.execute(text("ALTER TABLE player_stats_new RENAME TO player_stats"))
                    
                    print("✅ Структура таблицы player_stats исправлена")
                except Exception as e:
                    print(f"⚠️ Ошибка при исправлении структуры таблицы: {e}")
        
        # Список колонок, которые нужно добавить
        columns_to_add = [
            ("total_games", "INTEGER DEFAULT 0"),
            ("games_won", "INTEGER DEFAULT 0"),
            ("games_lost", "INTEGER DEFAULT 0"),
            ("times_wolf", "INTEGER DEFAULT 0"),
            ("times_fox", "INTEGER DEFAULT 0"),
            ("times_hare", "INTEGER DEFAULT 0"),
            ("times_mole", "INTEGER DEFAULT 0"),
            ("times_beaver", "INTEGER DEFAULT 0"),
            ("kills_made", "INTEGER DEFAULT 0"),
            ("votes_received", "INTEGER DEFAULT 0"),
            ("last_played", "TIMESTAMP"),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        ]
        
        # Добавляем недостающие колонки
        for column_name, column_def in columns_to_add:
            if column_name not in column_names:
                try:
                    alter_query = text(f"ALTER TABLE player_stats ADD COLUMN {column_name} {column_def}")
                    session.execute(alter_query)
                    print(f"✅ Добавлена колонка: {column_name}")
                except Exception as e:
                    print(f"⚠️ Ошибка при добавлении колонки {column_name}: {e}")
            else:
                print(f"ℹ️ Колонка {column_name} уже существует")
        
        # Коммитим изменения
        session.commit()
        print("✅ Миграция player_stats завершена успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при миграции player_stats: {e}")
        session.rollback()
        return False
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    fix_player_stats_table()
