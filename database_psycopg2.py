#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с PostgreSQL базой данных на Railway
Использует psycopg2 для прямого подключения к PostgreSQL
"""

import os
import psycopg2
import psycopg2.extras
from psycopg2 import pool
from typing import Optional, List, Dict, Any, Tuple
import logging
import time
from contextlib import contextmanager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Класс для управления подключением к PostgreSQL"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Инициализация подключения к базе данных
        
        Args:
            database_url: URL подключения к PostgreSQL (если None, читается из DATABASE_URL)
        """
        self.database_url = database_url or os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL не установлен в переменных окружения!")
        
        # Парсим URL для получения параметров подключения
        self.connection_params = self._parse_database_url()
        
        # Создаем пул соединений
        self.connection_pool = None
        self._init_connection_pool()
        
        logger.info("✅ Подключение к PostgreSQL инициализировано")
    
    def _parse_database_url(self) -> Dict[str, str]:
        """
        Парсит DATABASE_URL и возвращает параметры подключения
        
        Returns:
            Dict с параметрами подключения
        """
        try:
            # Убираем префикс postgresql:// или postgres://
            url = self.database_url.replace('postgresql://', '').replace('postgres://', '')
            
            # Разделяем на части
            if '@' in url:
                auth_part, host_part = url.split('@', 1)
                if ':' in auth_part:
                    user, password = auth_part.split(':', 1)
                else:
                    user, password = auth_part, ''
            else:
                user, password = '', ''
                host_part = url
            
            # Парсим хост и базу данных
            if '/' in host_part:
                host_port, database = host_part.split('/', 1)
                if ':' in host_port:
                    host, port = host_port.split(':', 1)
                else:
                    host, port = host_port, '5432'
            else:
                host, port, database = host_part, '5432', ''
            
            return {
                'host': host,
                'port': port,
                'database': database,
                'user': user,
                'password': password
            }
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга DATABASE_URL: {e}")
            raise
    
    def _init_connection_pool(self):
        """Инициализирует пул соединений"""
        try:
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                **self.connection_params
            )
            logger.info("✅ Пул соединений создан успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка создания пула соединений: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        Контекстный менеджер для получения соединения из пула
        
        Yields:
            psycopg2.connection: Соединение с базой данных
        """
        connection = None
        try:
            connection = self.connection_pool.getconn()
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"❌ Ошибка получения соединения: {e}")
            raise
        finally:
            if connection:
                self.connection_pool.putconn(connection)
    
    @contextmanager
    def get_cursor(self, connection=None):
        """
        Контекстный менеджер для получения курсора
        
        Args:
            connection: Соединение (если None, получается из пула)
        
        Yields:
            psycopg2.cursor: Курсор для выполнения запросов
        """
        if connection:
            # Используем переданное соединение
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                yield cursor
            finally:
                cursor.close()
        else:
            # Получаем соединение из пула
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                try:
                    yield cursor
                finally:
                    cursor.close()
    
    def test_connection(self) -> bool:
        """
        Тестирует подключение к базе данных
        
        Returns:
            bool: True если подключение успешно
        """
        try:
            with self.get_connection() as conn:
                with self.get_cursor(conn) as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    logger.info("✅ Тест подключения к базе данных успешен")
                    return True
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования подключения: {e}")
            return False
    
    def close(self):
        """Закрывает пул соединений"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("✅ Пул соединений закрыт")

# Глобальный экземпляр подключения
db_connection: Optional[DatabaseConnection] = None

def init_db(database_url: Optional[str] = None) -> DatabaseConnection:
    """
    Инициализирует подключение к базе данных
    
    Args:
        database_url: URL подключения (если None, читается из DATABASE_URL)
    
    Returns:
        DatabaseConnection: Экземпляр подключения к базе данных
    """
    global db_connection
    
    try:
        db_connection = DatabaseConnection(database_url)
        
        # Тестируем подключение
        if db_connection.test_connection():
            logger.info("🚀 База данных инициализирована успешно")
            return db_connection
        else:
            raise Exception("Не удалось подключиться к базе данных")
            
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        raise

def execute_query(query: str, params: Optional[Tuple] = None) -> int:
    """
    Выполняет INSERT/UPDATE/DELETE запрос
    
    Args:
        query: SQL запрос
        params: Параметры для запроса
    
    Returns:
        int: Количество затронутых строк
    """
    if not db_connection:
        raise RuntimeError("База данных не инициализирована. Вызовите init_db() сначала.")
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            with db_connection.get_connection() as conn:
                with db_connection.get_cursor(conn) as cursor:
                    cursor.execute(query, params)
                    conn.commit()
                    
                    affected_rows = cursor.rowcount
                    logger.debug(f"✅ Запрос выполнен успешно. Затронуто строк: {affected_rows}")
                    return affected_rows
                    
        except psycopg2.OperationalError as e:
            logger.warning(f"⚠️ Ошибка подключения (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Экспоненциальная задержка
                continue
            else:
                logger.error(f"❌ Не удалось выполнить запрос после {max_retries} попыток")
                raise
                
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения запроса: {e}")
            raise

def fetch_query(query: str, params: Optional[Tuple] = None, fetch_one: bool = False) -> List[Dict[str, Any]]:
    """
    Выполняет SELECT запрос и возвращает результат
    
    Args:
        query: SQL запрос
        params: Параметры для запроса
        fetch_one: Если True, возвращает только одну запись
    
    Returns:
        List[Dict] или Dict: Результат запроса
    """
    if not db_connection:
        raise RuntimeError("База данных не инициализирована. Вызовите init_db() сначала.")
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            with db_connection.get_connection() as conn:
                with db_connection.get_cursor(conn) as cursor:
                    cursor.execute(query, params)
                    
                    if fetch_one:
                        result = cursor.fetchone()
                        if result:
                            return dict(result)
                        return None
                    else:
                        results = cursor.fetchall()
                        return [dict(row) for row in results]
                        
        except psycopg2.OperationalError as e:
            logger.warning(f"⚠️ Ошибка подключения (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                logger.error(f"❌ Не удалось выполнить запрос после {max_retries} попыток")
                raise
                
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения запроса: {e}")
            raise

def fetch_one(query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
    """
    Выполняет SELECT запрос и возвращает одну запись
    
    Args:
        query: SQL запрос
        params: Параметры для запроса
    
    Returns:
        Dict или None: Одна запись или None
    """
    return fetch_query(query, params, fetch_one=True)

def execute_many(query: str, params_list: List[Tuple]) -> int:
    """
    Выполняет запрос с множественными параметрами (batch insert/update)
    
    Args:
        query: SQL запрос
        params_list: Список кортежей с параметрами
    
    Returns:
        int: Количество затронутых строк
    """
    if not db_connection:
        raise RuntimeError("База данных не инициализирована. Вызовите init_db() сначала.")
    
    try:
        with db_connection.get_connection() as conn:
            with db_connection.get_cursor(conn) as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
                
                affected_rows = cursor.rowcount
                logger.debug(f"✅ Batch запрос выполнен успешно. Затронуто строк: {affected_rows}")
                return affected_rows
                
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения batch запроса: {e}")
        raise

def close_db():
    """Закрывает подключение к базе данных"""
    global db_connection
    if db_connection:
        db_connection.close()
        db_connection = None
        logger.info("✅ Подключение к базе данных закрыто")

# Удобные функции для работы с новыми таблицами

def create_user(user_id: int, username: str = None) -> int:
    """
    Создает нового пользователя
    
    Args:
        user_id: Telegram user ID
        username: Имя пользователя
    
    Returns:
        int: ID созданного пользователя
    """
    query = """
        INSERT INTO users (user_id, username) 
        VALUES (%s, %s) 
        ON CONFLICT (user_id) DO UPDATE SET 
            username = EXCLUDED.username,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
    """
    result = fetch_one(query, (user_id, username))
    return result['id'] if result else None

def get_user_by_telegram_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает пользователя по Telegram ID
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Dict или None: Данные пользователя
    """
    query = "SELECT * FROM users WHERE user_id = %s"
    return fetch_one(query, (user_id,))

def update_user_balance(user_id: int, new_balance: float) -> bool:
    """
    Обновляет баланс пользователя
    
    Args:
        user_id: Telegram user ID
        new_balance: Новый баланс
    
    Returns:
        bool: True если обновление успешно
    """
    query = "UPDATE users SET balance = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s"
    affected = execute_query(query, (new_balance, user_id))
    return affected > 0

def get_shop_items() -> List[Dict[str, Any]]:
    """
    Получает все активные товары из магазина
    
    Returns:
        List[Dict]: Список товаров
    """
    query = "SELECT * FROM shop WHERE is_active = TRUE ORDER BY category, price"
    return fetch_query(query)

def create_purchase(user_id: int, item_id: int, quantity: int = 1) -> bool:
    """
    Создает покупку в магазине
    
    Args:
        user_id: Telegram user ID
        item_id: ID товара
        quantity: Количество
    
    Returns:
        bool: True если покупка создана успешно
    """
    # Получаем цену товара
    item_query = "SELECT price FROM shop WHERE id = %s AND is_active = TRUE"
    item = fetch_one(item_query, (item_id,))
    
    if not item:
        logger.error(f"❌ Товар с ID {item_id} не найден или неактивен")
        return False
    
    total_price = item['price'] * quantity
    
    # Создаем покупку
    purchase_query = """
        INSERT INTO purchases (user_id, item_id, quantity, total_price)
        VALUES (%s, %s, %s, %s)
    """
    
    try:
        execute_query(purchase_query, (user_id, item_id, quantity, total_price))
        logger.info(f"✅ Покупка создана: пользователь {user_id}, товар {item_id}, количество {quantity}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка создания покупки: {e}")
        return False

def get_user_stats(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает статистику пользователя
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Dict или None: Статистика пользователя
    """
    query = "SELECT * FROM stats WHERE user_id = %s"
    return fetch_one(query, (user_id,))

def update_user_stats(user_id: int, games_played: int = None, games_won: int = None, 
                     games_lost: int = None) -> bool:
    """
    Обновляет статистику пользователя
    
    Args:
        user_id: Telegram user ID
        games_played: Количество сыгранных игр
        games_won: Количество выигранных игр
        games_lost: Количество проигранных игр
    
    Returns:
        bool: True если обновление успешно
    """
    # Строим динамический запрос
    updates = []
    params = []
    
    if games_played is not None:
        updates.append("games_played = %s")
        params.append(games_played)
    
    if games_won is not None:
        updates.append("games_won = %s")
        params.append(games_won)
    
    if games_lost is not None:
        updates.append("games_lost = %s")
        params.append(games_lost)
    
    if not updates:
        return False
    
    updates.append("last_played = CURRENT_TIMESTAMP")
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user_id)
    
    query = f"UPDATE stats SET {', '.join(updates)} WHERE user_id = %s"
    
    try:
        affected = execute_query(query, tuple(params))
        return affected > 0
    except Exception as e:
        logger.error(f"❌ Ошибка обновления статистики: {e}")
        return False

# ==================== ФУНКЦИИ ДЛЯ НАСТРОЕК ЧАТА ====================

def get_chat_settings(chat_id: int) -> Dict[str, Any]:
    """
    Получает настройки чата. Если настройки не существуют, создает их с дефолтными значениями.
    
    Args:
        chat_id: ID чата в Telegram
    
    Returns:
        Dict: Настройки чата
    """
    # Сначала пытаемся получить существующие настройки
    query = "SELECT * FROM chat_settings WHERE chat_id = %s"
    settings = fetch_one(query, (chat_id,))
    
    if settings:
        logger.info(f"✅ Настройки чата {chat_id} найдены")
        return settings
    
    # Если настройки не найдены, создаем их с дефолтными значениями
    logger.info(f"📝 Создаем настройки чата {chat_id} с дефолтными значениями")
    
    default_settings = {
        'chat_id': chat_id,
        'test_mode': False,
        'min_players': 4,
        'max_players': 12,
        'night_duration': 60,
        'day_duration': 300,
        'vote_duration': 120,
        'fox_death_threshold': 2,
        'beaver_protection': True,
        'mole_reveal_threshold': 3,
        'herbivore_survival_threshold': 1,
        'max_rounds': 20,
        'max_time': 3600,
        'min_alive': 2
    }
    
    insert_query = """
        INSERT INTO chat_settings (
            chat_id, test_mode, min_players, max_players, night_duration, 
            day_duration, vote_duration, fox_death_threshold, beaver_protection,
            mole_reveal_threshold, herbivore_survival_threshold, max_rounds,
            max_time, min_alive
        ) VALUES (
            %(chat_id)s, %(test_mode)s, %(min_players)s, %(max_players)s, 
            %(night_duration)s, %(day_duration)s, %(vote_duration)s, 
            %(fox_death_threshold)s, %(beaver_protection)s, %(mole_reveal_threshold)s,
            %(herbivore_survival_threshold)s, %(max_rounds)s, %(max_time)s, %(min_alive)s
        )
    """
    
    try:
        execute_query(insert_query, default_settings)
        logger.info(f"✅ Настройки чата {chat_id} созданы с дефолтными значениями")
        
        # Возвращаем созданные настройки
        return get_chat_settings(chat_id)
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания настроек чата {chat_id}: {e}")
        return default_settings

def update_chat_settings(chat_id: int, **kwargs) -> bool:
    """
    Обновляет настройки чата. Обновляет только переданные поля.
    
    Args:
        chat_id: ID чата в Telegram
        **kwargs: Поля для обновления
    
    Returns:
        bool: True если обновление успешно
    """
    if not kwargs:
        logger.warning(f"⚠️ Нет полей для обновления настроек чата {chat_id}")
        return False
    
    # Список допустимых полей
    allowed_fields = {
        'test_mode', 'min_players', 'max_players', 'night_duration', 
        'day_duration', 'vote_duration', 'fox_death_threshold', 
        'beaver_protection', 'mole_reveal_threshold', 'herbivore_survival_threshold',
        'max_rounds', 'max_time', 'min_alive'
    }
    
    # Фильтруем только допустимые поля
    valid_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not valid_fields:
        logger.error(f"❌ Нет допустимых полей для обновления настроек чата {chat_id}")
        return False
    
    # Создаем SQL запрос для обновления
    set_clauses = []
    values = []
    
    for field, value in valid_fields.items():
        set_clauses.append(f"{field} = %s")
        values.append(value)
    
    values.append(chat_id)  # Для WHERE условия
    
    query = f"""
        UPDATE chat_settings 
        SET {', '.join(set_clauses)}
        WHERE chat_id = %s
    """
    
    try:
        execute_query(query, values)
        logger.info(f"✅ Настройки чата {chat_id} обновлены: {list(valid_fields.keys())}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления настроек чата {chat_id}: {e}")
        return False

def reset_chat_settings(chat_id: int) -> bool:
    """
    Сбрасывает настройки чата к дефолтным значениям.
    
    Args:
        chat_id: ID чата в Telegram
    
    Returns:
        bool: True если сброс успешен
    """
    default_settings = {
        'test_mode': False,
        'min_players': 4,
        'max_players': 12,
        'night_duration': 60,
        'day_duration': 300,
        'vote_duration': 120,
        'fox_death_threshold': 2,
        'beaver_protection': True,
        'mole_reveal_threshold': 3,
        'herbivore_survival_threshold': 1,
        'max_rounds': 20,
        'max_time': 3600,
        'min_alive': 2
    }
    
    try:
        success = update_chat_settings(chat_id, **default_settings)
        if success:
            logger.info(f"✅ Настройки чата {chat_id} сброшены к дефолтным значениям")
        return success
        
    except Exception as e:
        logger.error(f"❌ Ошибка сброса настроек чата {chat_id}: {e}")
        return False

def delete_chat_settings(chat_id: int) -> bool:
    """
    Удаляет настройки чата.
    
    Args:
        chat_id: ID чата в Telegram
    
    Returns:
        bool: True если удаление успешно
    """
    query = "DELETE FROM chat_settings WHERE chat_id = %s"
    
    try:
        execute_query(query, (chat_id,))
        logger.info(f"✅ Настройки чата {chat_id} удалены")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка удаления настроек чата {chat_id}: {e}")
        return False

def get_all_chat_settings() -> List[Dict[str, Any]]:
    """
    Получает настройки всех чатов.
    
    Returns:
        List[Dict]: Список настроек всех чатов
    """
    query = "SELECT * FROM chat_settings ORDER BY chat_id"
    return fetch_query(query)

def create_tables():
    """
    Создает все необходимые таблицы в базе данных
    """
    try:
        # SQL для создания таблицы chat_settings
        chat_settings_sql = """
        CREATE TABLE IF NOT EXISTS chat_settings (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL UNIQUE,
            test_mode BOOLEAN DEFAULT FALSE,
            min_players INTEGER DEFAULT 4,
            max_players INTEGER DEFAULT 12,
            night_duration INTEGER DEFAULT 60,
            day_duration INTEGER DEFAULT 300,
            vote_duration INTEGER DEFAULT 120,
            fox_death_threshold INTEGER DEFAULT 2,
            beaver_protection BOOLEAN DEFAULT TRUE,
            mole_reveal_threshold INTEGER DEFAULT 3,
            herbivore_survival_threshold INTEGER DEFAULT 1,
            max_rounds INTEGER DEFAULT 20,
            max_time INTEGER DEFAULT 3600,
            min_alive INTEGER DEFAULT 2,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_chat_settings_chat_id ON chat_settings(chat_id);
        
        CREATE OR REPLACE FUNCTION update_chat_settings_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER trigger_chat_settings_updated_at
            BEFORE UPDATE ON chat_settings
            FOR EACH ROW
            EXECUTE FUNCTION update_chat_settings_updated_at();
        """
        
        # Выполняем SQL
        execute_query(chat_settings_sql)
        logger.info("✅ Таблица chat_settings создана успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблиц: {e}")
        raise

# Пример использования
if __name__ == "__main__":
    try:
        # Инициализация базы данных
        db = init_db()
        
        # Тест подключения
        if db.test_connection():
            print("✅ Подключение к базе данных успешно!")
        
        # Пример создания пользователя
        user_id = 123456789
        create_user(user_id, "test_user")
        print(f"✅ Пользователь {user_id} создан")
        
        # Пример получения товаров из магазина
        items = get_shop_items()
        print(f"✅ Найдено товаров в магазине: {len(items)}")
        
        # Закрытие подключения
        close_db()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
