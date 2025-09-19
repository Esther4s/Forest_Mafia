#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для проверки структуры таблицы player_stats
"""

import os
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from database import init_database, get_db_session
from sqlalchemy import text

def check_player_stats_structure():
    """Проверяет структуру таблицы player_stats"""
    print("🔍 Проверка структуры таблицы player_stats...")
    
    try:
        # Инициализируем базу данных
        init_database()
        session = get_db_session()
        
        # Получаем информацию о колонках таблицы player_stats (SQLite)
        query = text("PRAGMA table_info(player_stats);")
        
        result = session.execute(query)
        columns = result.fetchall()
        
        if not columns:
            print("❌ Таблица player_stats не найдена!")
            return False
        
        print("📋 Структура таблицы player_stats:")
        print("-" * 60)
        for col in columns:
            # SQLite PRAGMA table_info возвращает: cid, name, type, notnull, dflt_value, pk
            print(f"  {col[1]:<20} {col[2]:<15} {'NOT NULL' if col[3] else 'NULL':<10} {col[4] or ''}")
        
        print("-" * 60)
        print(f"Всего колонок: {len(columns)}")
        
        # Проверяем наличие ключевых колонок
        column_names = [col[1] for col in columns]  # col[1] это name в SQLite
        required_columns = ['id', 'user_id', 'total_games', 'games_won', 'games_lost']
        missing_columns = [col for col in required_columns if col not in column_names]
        
        if missing_columns:
            print(f"❌ Отсутствующие колонки: {missing_columns}")
            return False
        else:
            print("✅ Все необходимые колонки присутствуют")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при проверке структуры: {e}")
        return False
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    check_player_stats_structure()
