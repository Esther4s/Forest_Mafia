#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Миграция для включения быстрого режима по умолчанию
Обновляет все существующие чаты, у которых быстрый режим отключен
"""

import os
import sys
import logging
from database_psycopg2 import DatabaseConnection, execute_query

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def enable_quick_mode_for_existing_chats():
    """Включает быстрый режим для всех существующих чатов"""
    try:
        # Создаем подключение к базе данных
        db = DatabaseConnection()
        
        # SQL для обновления всех чатов, у которых быстрый режим отключен
        update_sql = """
        UPDATE chat_settings 
        SET test_mode = TRUE 
        WHERE test_mode = FALSE
        """
        
        logger.info("🔧 Включаем быстрый режим для всех существующих чатов...")
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(update_sql)
                affected_rows = cursor.rowcount
                conn.commit()
        
        logger.info(f"✅ Быстрый режим включен для {affected_rows} чатов!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка включения быстрого режима: {e}")
        return False

def main():
    """Главная функция"""
    print("🌲 Включение быстрого режима для существующих чатов")
    print("=" * 60)
    
    if enable_quick_mode_for_existing_chats():
        print("✅ Миграция успешно применена!")
        print("⚡ Теперь все чаты используют быстрый режим по умолчанию")
        sys.exit(0)
    else:
        print("❌ Ошибка применения миграции!")
        sys.exit(1)

if __name__ == "__main__":
    main()
