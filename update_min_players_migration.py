#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Миграция для обновления минимального количества игроков
Устанавливает min_players = 3 для чатов с быстрым режимом
"""

import os
import sys
import logging
from database_psycopg2 import DatabaseConnection, execute_query

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_min_players_for_quick_mode():
    """Обновляет минимальное количество игроков для быстрого режима"""
    try:
        # Создаем подключение к базе данных
        db = DatabaseConnection()
        
        # SQL для обновления чатов с быстрым режимом
        update_sql = """
        UPDATE chat_settings 
        SET min_players = 3 
        WHERE test_mode = TRUE AND min_players > 3
        """
        
        logger.info("🔧 Обновляем минимальное количество игроков для быстрого режима...")
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(update_sql)
                affected_rows = cursor.rowcount
                conn.commit()
        
        logger.info(f"✅ Обновлено {affected_rows} чатов с быстрым режимом!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления минимального количества игроков: {e}")
        return False

def main():
    """Главная функция"""
    print("🌲 Обновление минимального количества игроков для быстрого режима")
    print("=" * 70)
    
    if update_min_players_for_quick_mode():
        print("✅ Миграция успешно применена!")
        print("⚡ Теперь в быстром режиме достаточно 3 игроков для начала игры")
        sys.exit(0)
    else:
        print("❌ Ошибка применения миграции!")
        sys.exit(1)

if __name__ == "__main__":
    main()
