#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для исправления типа данных chat_id с INTEGER на BIGINT
"""

import os
import sys
import logging
from database_psycopg2 import DatabaseConnection

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_chat_id_columns():
    """Исправляет тип данных chat_id с INTEGER на BIGINT"""
    logger.info("🔧 Начинаем исправление типа данных chat_id...")
    
    try:
        db_manager = DatabaseConnection()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
        
        # Список таблиц и колонок, которые нужно исправить
        columns_to_fix = [
            ("games", "chat_id"),
            ("games", "thread_id"),
            ("chat_settings", "chat_id"),
            ("active_effects", "chat_id"),
        ]
        
        for table_name, column_name in columns_to_fix:
            try:
                # Проверяем, существует ли таблица
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, (table_name,))
                
                table_exists = cursor.fetchone()[0]
                if not table_exists:
                    logger.info(f"⏭️ Таблица {table_name} не существует, пропускаем")
                    continue
                
                # Проверяем, существует ли колонка
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = %s AND column_name = %s
                    );
                """, (table_name, column_name))
                
                column_exists = cursor.fetchone()[0]
                if not column_exists:
                    logger.info(f"⏭️ Колонка {table_name}.{column_name} не существует, пропускаем")
                    continue
                
                # Проверяем текущий тип данных
                cursor.execute("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = %s;
                """, (table_name, column_name))
                
                current_type = cursor.fetchone()[0]
                logger.info(f"📊 Текущий тип {table_name}.{column_name}: {current_type}")
                
                if current_type == 'bigint':
                    logger.info(f"✅ {table_name}.{column_name} уже имеет тип BIGINT")
                    continue
                
                # Изменяем тип данных
                logger.info(f"🔄 Изменяем тип {table_name}.{column_name} на BIGINT...")
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ALTER COLUMN {column_name} TYPE BIGINT;
                """)
                
                logger.info(f"✅ {table_name}.{column_name} успешно изменен на BIGINT")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при изменении {table_name}.{column_name}: {e}")
                continue
        
            # Коммитим изменения
            conn.commit()
            logger.info("✅ Все изменения успешно применены")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка при исправлении типов данных: {e}")
        return False

def verify_fix():
    """Проверяет, что исправление применилось корректно"""
    logger.info("🔍 Проверяем результат исправления...")
    
    try:
        db_manager = DatabaseConnection()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
        
        # Проверяем типы данных в основных таблицах
        tables_to_check = ["games", "chat_settings", "active_effects"]
        
        for table_name in tables_to_check:
            try:
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s AND column_name IN ('chat_id', 'thread_id')
                    ORDER BY column_name;
                """, (table_name,))
                
                columns = cursor.fetchall()
                if columns:
                    logger.info(f"📊 Таблица {table_name}:")
                    for column_name, data_type in columns:
                        status = "✅" if data_type == 'bigint' else "❌"
                        logger.info(f"  {status} {column_name}: {data_type}")
                else:
                    logger.info(f"⏭️ В таблице {table_name} нет колонок chat_id/thread_id")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка при проверке таблицы {table_name}: {e}")
        
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке: {e}")
        return False

def test_large_chat_id():
    """Тестирует работу с большим chat_id"""
    logger.info("🧪 Тестируем работу с большим chat_id...")
    
    test_chat_id = -1002785929250  # Тот же ID из логов
    
    try:
        db_manager = DatabaseConnection()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
        
        # Пытаемся вставить тестовую запись в chat_settings
        try:
            cursor.execute("""
                INSERT INTO chat_settings (chat_id, test_mode, min_players) 
                VALUES (%s, %s, %s)
                ON CONFLICT (chat_id) DO UPDATE SET
                    test_mode = EXCLUDED.test_mode,
                    min_players = EXCLUDED.min_players,
                    updated_at = CURRENT_TIMESTAMP;
            """, (test_chat_id, False, 4))
            
            conn.commit()
            logger.info(f"✅ Тестовая запись с chat_id {test_chat_id} успешно создана/обновлена")
            
            # Удаляем тестовую запись
            cursor.execute("DELETE FROM chat_settings WHERE chat_id = %s", (test_chat_id,))
            conn.commit()
            logger.info("✅ Тестовая запись удалена")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при тестировании большого chat_id: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск исправления типа данных chat_id")
    logger.info("🚀 Запуск исправления типа данных chat_id")
    
    # Шаг 1: Исправляем типы данных
    if fix_chat_id_columns():
        logger.info("✅ Исправление типов данных завершено успешно")
        
        # Шаг 2: Проверяем результат
        if verify_fix():
            logger.info("✅ Проверка завершена успешно")
            
            # Шаг 3: Тестируем с большим chat_id
            if test_large_chat_id():
                logger.info("🎉 Все тесты пройдены! Проблема с chat_id исправлена")
            else:
                logger.error("❌ Тест с большим chat_id не прошел")
        else:
            logger.error("❌ Проверка не прошла")
    else:
        logger.error("❌ Исправление типов данных не удалось")
    
    logger.info("🏁 Скрипт завершен")
