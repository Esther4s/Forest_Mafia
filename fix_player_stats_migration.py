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
        existing_columns = [row[0] for row in result.fetchall()]
        
        print(f"📋 Существующие колонки: {existing_columns}")
        
        # Список колонок, которые нужно добавить
        columns_to_add = [
            ("username", "VARCHAR"),
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
            if column_name not in existing_columns:
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
