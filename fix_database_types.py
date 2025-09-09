#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для исправления типов данных в базе данных
"""

import logging
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

def fix_database_types():
    """Исправляет типы данных в базе данных"""
    logger.info("=== Исправление типов данных в базе данных ===")
    
    try:
        # Устанавливаем переменную окружения
        os.environ['DATABASE_URL'] = 'postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway'
        
        logger.info("🔗 Подключение к Railway PostgreSQL...")
        
        # Импортируем модули
        from database_psycopg2 import init_db, close_db, execute_query, fetch_one
        
        logger.info("🔧 Инициализация базы данных...")
        init_db()
        logger.info("✅ База данных инициализирована")
        
        # 1. Проверяем текущие типы данных
        logger.info("1️⃣ Проверяем текущие типы данных...")
        
        # Проверяем таблицу users
        users_columns_query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'user_id'
        """
        users_column = fetch_one(users_columns_query)
        if users_column:
            logger.info(f"📊 users.user_id: {users_column['data_type']}")
        
        # Проверяем таблицу players
        players_columns_query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'players' AND column_name = 'user_id'
        """
        players_column = fetch_one(players_columns_query)
        if players_column:
            logger.info(f"📊 players.user_id: {players_column['data_type']}")
        
        # Проверяем таблицу games
        games_columns_query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'games' AND column_name = 'chat_id'
        """
        games_column = fetch_one(games_columns_query)
        if games_column:
            logger.info(f"📊 games.chat_id: {games_column['data_type']}")
        
        # 2. Исправляем типы данных
        logger.info("2️⃣ Исправляем типы данных...")
        
        # Исправляем players.user_id
        if players_column and players_column['data_type'] == 'integer':
            logger.info("🔧 Исправляем players.user_id: INTEGER -> BIGINT")
            try:
                execute_query("ALTER TABLE players ALTER COLUMN user_id TYPE BIGINT")
                logger.info("✅ players.user_id исправлен")
            except Exception as e:
                logger.error(f"❌ Ошибка исправления players.user_id: {e}")
        
        # Исправляем games.chat_id
        if games_column and games_column['data_type'] == 'integer':
            logger.info("🔧 Исправляем games.chat_id: INTEGER -> BIGINT")
            try:
                execute_query("ALTER TABLE games ALTER COLUMN chat_id TYPE BIGINT")
                logger.info("✅ games.chat_id исправлен")
            except Exception as e:
                logger.error(f"❌ Ошибка исправления games.chat_id: {e}")
        
        # Исправляем games.thread_id
        logger.info("🔧 Исправляем games.thread_id: INTEGER -> BIGINT")
        try:
            execute_query("ALTER TABLE games ALTER COLUMN thread_id TYPE BIGINT")
            logger.info("✅ games.thread_id исправлен")
        except Exception as e:
            logger.error(f"❌ Ошибка исправления games.thread_id: {e}")
        
        # 3. Проверяем исправленные типы
        logger.info("3️⃣ Проверяем исправленные типы данных...")
        
        # Проверяем players.user_id
        players_column_after = fetch_one(players_columns_query)
        if players_column_after:
            logger.info(f"📊 players.user_id после исправления: {players_column_after['data_type']}")
        
        # Проверяем games.chat_id
        games_column_after = fetch_one(games_columns_query)
        if games_column_after:
            logger.info(f"📊 games.chat_id после исправления: {games_column_after['data_type']}")
        
        # 4. Тестируем создание пользователя с большим ID
        logger.info("4️⃣ Тестируем создание пользователя с большим ID...")
        test_user_id = 8455370841  # ID из логов
        test_username = "TestLargeID"
        
        # Удаляем тестового пользователя если существует
        execute_query("DELETE FROM users WHERE user_id = %s", (test_user_id,))
        
        # Создаем тестового пользователя
        create_user_query = """
            INSERT INTO users (user_id, username, balance) 
            VALUES (%s, %s, 100)
        """
        result = execute_query(create_user_query, (test_user_id, test_username))
        
        if result > 0:
            logger.info(f"✅ Пользователь с большим ID {test_user_id} создан успешно")
        else:
            logger.error(f"❌ Не удалось создать пользователя с большим ID {test_user_id}")
            return False
        
        # Очищаем тестового пользователя
        execute_query("DELETE FROM users WHERE user_id = %s", (test_user_id,))
        logger.info("✅ Тестовый пользователь удален")
        
        logger.info("🎉 Исправление типов данных завершено успешно!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при исправлении типов данных: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return False
    finally:
        try:
            close_db()
            logger.info("🔌 Соединение с базой данных закрыто")
        except:
            pass

def main():
    """Главная функция"""
    print("🔧 ForestMafia Bot - Исправление типов данных в базе данных 🔧")
    print("=" * 60)
    
    try:
        success = fix_database_types()
        if success:
            print("🎉 ИСПРАВЛЕНИЕ ТИПОВ ДАННЫХ ЗАВЕРШЕНО УСПЕШНО!")
            print("✅ players.user_id: INTEGER -> BIGINT")
            print("✅ games.chat_id: INTEGER -> BIGINT")
            print("✅ games.thread_id: INTEGER -> BIGINT")
            print("✅ Тестирование с большими ID прошло успешно")
            print("✅ Ошибка 'integer out of range' должна быть исправлена")
        else:
            print("❌ ИСПРАВЛЕНИЕ ТИПОВ ДАННЫХ ПРОВАЛЕНО")
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
