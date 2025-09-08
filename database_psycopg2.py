#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с PostgreSQL базой данных на Railway
Использует psycopg2 для прямого подключения к PostgreSQL
"""

import os
import json
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

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С НОВЫМИ ТАБЛИЦАМИ ====================

def save_player_action(game_id: str, player_id: str, action_type: str, target_id: str = None, action_data: dict = None):
    """
    Сохраняет действие игрока в таблицу player_actions
    
    Args:
        game_id: ID игры
        player_id: ID игрока
        action_type: Тип действия (vote, kill, protect, etc.)
        target_id: ID цели действия (опционально)
        action_data: Дополнительные данные действия (опционально)
    
    Returns:
        bool: True если успешно сохранено
    """
    try:
        query = """
        INSERT INTO player_actions (game_id, player_id, action_type, target_id, action_data)
        VALUES (%s, %s, %s, %s, %s)
        """
        params = (game_id, player_id, action_type, target_id, json.dumps(action_data) if action_data else '{}')
        execute_query(query, params)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения действия игрока: {e}")
        return False

def save_vote(game_id: str, voter_id: str, target_id: str, vote_type: str, round_number: int = 1):
    """
    Сохраняет голос в таблицу votes
    
    Args:
        game_id: ID игры
        voter_id: ID голосующего
        target_id: ID цели голосования
        vote_type: Тип голосования (exile, kill, etc.)
        round_number: Номер раунда
    
    Returns:
        bool: True если успешно сохранено
    """
    try:
        query = """
        INSERT INTO votes (game_id, voter_id, target_id, vote_type, round_number)
        VALUES (%s, %s, %s, %s, %s)
        """
        params = (game_id, voter_id, target_id, vote_type, round_number)
        execute_query(query, params)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения голоса: {e}")
        return False

def update_player_stats(player_id: str, user_id: int, **kwargs):
    """
    Обновляет статистику игрока в таблице player_stats
    
    Args:
        player_id: ID игрока
        user_id: ID пользователя Telegram
        **kwargs: Поля для обновления (games_played, games_won, games_lost, etc.)
    
    Returns:
        bool: True если успешно обновлено
    """
    try:
        # Проверяем существование записи
        check_query = "SELECT id FROM player_stats WHERE player_id = %s"
        existing = fetch_one(check_query, (player_id,))
        
        if not existing:
            # Создаем новую запись
            insert_query = """
            INSERT INTO player_stats (player_id, user_id, games_played, games_won, games_lost, 
                                    roles_played, total_kills, total_deaths, last_played)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                player_id, user_id,
                kwargs.get('games_played', 0),
                kwargs.get('games_won', 0),
                kwargs.get('games_lost', 0),
                json.dumps(kwargs.get('roles_played', {})),
                kwargs.get('total_kills', 0),
                kwargs.get('total_deaths', 0),
                kwargs.get('last_played')
            )
            execute_query(insert_query, params)
        else:
            # Обновляем существующую запись
            set_clauses = []
            params = []
            for key, value in kwargs.items():
                if key == 'roles_played':
                    set_clauses.append(f"{key} = %s")
                    params.append(json.dumps(value))
                else:
                    set_clauses.append(f"{key} = %s")
                    params.append(value)
            
            if set_clauses:
                params.append(player_id)
                update_query = f"UPDATE player_stats SET {', '.join(set_clauses)} WHERE player_id = %s"
                execute_query(update_query, params)
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления статистики игрока: {e}")
        return False

def get_bot_setting(setting_name: str, default_value: str = None):
    """
    Получает настройку бота из таблицы bot_settings
    
    Args:
        setting_name: Название настройки
        default_value: Значение по умолчанию
    
    Returns:
        str: Значение настройки или default_value
    """
    try:
        query = "SELECT setting_value FROM bot_settings WHERE setting_name = %s"
        result = fetch_one(query, (setting_name,))
        return result['setting_value'] if result else default_value
    except Exception as e:
        logger.error(f"❌ Ошибка получения настройки бота: {e}")
        return default_value

def set_bot_setting(setting_name: str, setting_value: str, description: str = None):
    """
    Устанавливает настройку бота в таблице bot_settings
    
    Args:
        setting_name: Название настройки
        setting_value: Значение настройки
        description: Описание настройки
    
    Returns:
        bool: True если успешно установлено
    """
    try:
        query = """
        INSERT INTO bot_settings (setting_name, setting_value, description)
        VALUES (%s, %s, %s)
        ON CONFLICT (setting_name) 
        DO UPDATE SET setting_value = EXCLUDED.setting_value, 
                      description = EXCLUDED.description
        """
        params = (setting_name, setting_value, description)
        execute_query(query, params)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка установки настройки бота: {e}")
        return False

# ==================== ФУНКЦИИ ДЛЯ СОХРАНЕНИЯ ИГР ====================

def save_game_to_db(game_id: str, chat_id: int, thread_id: int = None, 
                   status: str = 'waiting', phase: str = None, 
                   round_number: int = 0, settings: dict = None):
    """
    Сохраняет игру в базу данных
    
    Args:
        game_id: ID игры
        chat_id: ID чата
        thread_id: ID темы (опционально)
        status: Статус игры
        phase: Фаза игры
        round_number: Номер раунда
        settings: Настройки игры
    
    Returns:
        bool: True если успешно сохранено
    """
    try:
        query = """
        INSERT INTO games (id, chat_id, thread_id, status, phase, round_number, settings)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) 
        DO UPDATE SET 
            chat_id = EXCLUDED.chat_id,
            thread_id = EXCLUDED.thread_id,
            status = EXCLUDED.status,
            phase = EXCLUDED.phase,
            round_number = EXCLUDED.round_number,
            settings = EXCLUDED.settings
        """
        params = (game_id, chat_id, thread_id, status, phase, round_number, 
                 json.dumps(settings) if settings else '{}')
        execute_query(query, params)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения игры: {e}")
        return False

def save_player_to_db(player_id: str, game_id: str, user_id: int, 
                     username: str = None, first_name: str = None, 
                     last_name: str = None, role: str = None, 
                     team: str = None, is_alive: bool = True):
    """
    Сохраняет игрока в базу данных
    
    Args:
        player_id: ID игрока
        game_id: ID игры
        user_id: ID пользователя Telegram
        username: Имя пользователя
        first_name: Имя
        last_name: Фамилия
        role: Роль в игре
        team: Команда
        is_alive: Жив ли игрок
    
    Returns:
        bool: True если успешно сохранено
    """
    try:
        query = """
        INSERT INTO players (id, game_id, user_id, username, first_name, last_name, role, team, is_alive)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) 
        DO UPDATE SET 
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            role = EXCLUDED.role,
            team = EXCLUDED.team,
            is_alive = EXCLUDED.is_alive
        """
        params = (player_id, game_id, user_id, username, first_name, 
                 last_name, role, team, is_alive)
        execute_query(query, params)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения игрока: {e}")
        return False

def update_game_phase(game_id: str, phase: str, round_number: int = None):
    """
    Обновляет фазу игры в базе данных
    
    Args:
        game_id: ID игры
        phase: Новая фаза
        round_number: Номер раунда (опционально)
    
    Returns:
        bool: True если успешно обновлено
    """
    try:
        if round_number is not None:
            query = "UPDATE games SET phase = %s, round_number = %s WHERE id = %s"
            params = (phase, round_number, game_id)
        else:
            query = "UPDATE games SET phase = %s WHERE id = %s"
            params = (phase, game_id)
        
        execute_query(query, params)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления фазы игры: {e}")
        return False

def finish_game_in_db(game_id: str, winner_team: str):
    """
    Завершает игру в базе данных
    
    Args:
        game_id: ID игры
        winner_team: Команда-победитель
    
    Returns:
        bool: True если успешно завершено
    """
    try:
        query = """
        UPDATE games 
        SET status = 'finished', winner_team = %s, finished_at = CURRENT_TIMESTAMP 
        WHERE id = %s
        """
        params = (winner_team, game_id)
        execute_query(query, params)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка завершения игры: {e}")
        return False

# ==================== ФУНКЦИИ ДЛЯ СТАТИСТИКИ ====================

def get_team_stats() -> Dict[str, Any]:
    """
    Получает статистику команд (хищники vs мирные)
    
    Returns:
        Dict с статистикой команд
    """
    try:
        # Статистика побед команд
        query = """
        SELECT 
            winner_team,
            COUNT(*) as wins
        FROM games 
        WHERE status = 'finished' AND winner_team IS NOT NULL
        GROUP BY winner_team
        """
        team_wins = fetch_query(query)
        
        # Общая статистика игр
        total_games_query = "SELECT COUNT(*) as total FROM games WHERE status = 'finished'"
        total_games = fetch_one(total_games_query)
        
        # Статистика игроков по командам
        players_query = """
        SELECT 
            COUNT(*) as total_players,
            SUM(games_played) as total_games,
            SUM(games_won) as total_wins
        FROM stats
        """
        players_stats = fetch_one(players_query)
        
        # Формируем результат
        result = {
            'total_games': total_games['total'] if total_games else 0,
            'team_wins': {},
            'players_stats': players_stats or {}
        }
        
        for team_win in team_wins:
            result['team_wins'][team_win['winner_team']] = team_win['wins']
        
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики команд: {e}")
        return {'total_games': 0, 'team_wins': {}, 'players_stats': {}}

def get_top_players(limit: int = 10, sort_by: str = 'games_won') -> List[Dict[str, Any]]:
    """
    Получает топ игроков
    
    Args:
        limit: Количество игроков в топе
        sort_by: Поле для сортировки (games_won, games_played, etc.)
    
    Returns:
        List с данными топ игроков
    """
    try:
        query = f"""
        SELECT 
            s.user_id,
            u.username,
            s.games_played,
            s.games_won,
            s.games_lost,
            s.last_played,
            ROUND((s.games_won::float / NULLIF(s.games_played, 0)) * 100, 1) as win_rate
        FROM stats s
        LEFT JOIN users u ON s.user_id = u.user_id
        WHERE s.games_played > 0
        ORDER BY {sort_by} DESC, win_rate DESC
        LIMIT %s
        """
        return fetch_query(query, (limit,))
    except Exception as e:
        logger.error(f"❌ Ошибка получения топ игроков: {e}")
        return []

def get_best_predator() -> Optional[Dict[str, Any]]:
    """
    Получает лучшего хищника (игрока с наибольшим количеством побед в роли хищника)
    
    Returns:
        Dict с данными лучшего хищника или None
    """
    try:
        # Получаем игроков, которые играли хищниками и выигрывали
        query = """
        SELECT 
            s.user_id,
            u.username,
            s.games_won,
            s.games_played,
            ROUND((s.games_won::float / NULLIF(s.games_played, 0)) * 100, 1) as win_rate
        FROM stats s
        LEFT JOIN users u ON s.user_id = u.user_id
        WHERE s.games_played > 0 AND s.games_won > 0
        ORDER BY s.games_won DESC, win_rate DESC
        LIMIT 1
        """
        return fetch_one(query)
    except Exception as e:
        logger.error(f"❌ Ошибка получения лучшего хищника: {e}")
        return None

def get_best_herbivore() -> Optional[Dict[str, Any]]:
    """
    Получает лучшего травоядного (игрока с наибольшим количеством побед в роли травоядного)
    
    Returns:
        Dict с данными лучшего травоядного или None
    """
    try:
        # Для травоядных используем общую статистику, так как у нас нет разделения по ролям в таблице stats
        # В будущем можно добавить отдельные поля для ролей
        query = """
        SELECT 
            s.user_id,
            u.username,
            s.games_won,
            s.games_played,
            ROUND((s.games_won::float / NULLIF(s.games_played, 0)) * 100, 1) as win_rate
        FROM stats s
        LEFT JOIN users u ON s.user_id = u.user_id
        WHERE s.games_played > 0 AND s.games_won > 0
        ORDER BY s.games_won DESC, win_rate DESC
        LIMIT 1
        """
        return fetch_one(query)
    except Exception as e:
        logger.error(f"❌ Ошибка получения лучшего травоядного: {e}")
        return None

def get_player_detailed_stats(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает детальную статистику игрока
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Dict с детальной статистикой или None
    """
    try:
        query = """
        SELECT 
            s.user_id,
            u.username,
            s.games_played,
            s.games_won,
            s.games_lost,
            s.last_played,
            ROUND((s.games_won::float / NULLIF(s.games_played, 0)) * 100, 1) as win_rate
        FROM stats s
        LEFT JOIN users u ON s.user_id = u.user_id
        WHERE s.user_id = %s
        """
        return fetch_one(query, (user_id,))
    except Exception as e:
        logger.error(f"❌ Ошибка получения детальной статистики: {e}")
        return None

def create_tables():
    """
    Создает все необходимые таблицы в базе данных
    """
    try:
        # Сначала удаляем все таблицы если они существуют
        drop_sql = """
        DROP TABLE IF EXISTS votes CASCADE;
        DROP TABLE IF EXISTS player_actions CASCADE;
        DROP TABLE IF EXISTS player_stats CASCADE;
        DROP TABLE IF EXISTS purchases CASCADE;
        DROP TABLE IF EXISTS game_events CASCADE;
        DROP TABLE IF EXISTS players CASCADE;
        DROP TABLE IF EXISTS games CASCADE;
        DROP TABLE IF EXISTS stats CASCADE;
        DROP TABLE IF EXISTS shop CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        DROP TABLE IF EXISTS chat_settings CASCADE;
        DROP TABLE IF EXISTS bot_settings CASCADE;
        """
        
        logger.info("🗑️ Удаляем существующие таблицы...")
        execute_query(drop_sql)
        
        # SQL для создания всех таблиц
        tables_sql = """
        -- Включаем расширения PostgreSQL
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        
        -- Таблица пользователей
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL UNIQUE,
            username VARCHAR(255),
            balance INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Таблица игр
        CREATE TABLE games (
            id VARCHAR PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            thread_id INTEGER,
            status VARCHAR DEFAULT 'waiting',
            phase VARCHAR,
            round_number INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            winner_team VARCHAR,
            settings JSONB DEFAULT '{}'::jsonb
        );
        
        -- Таблица игроков
        CREATE TABLE players (
            id VARCHAR PRIMARY KEY,
            game_id VARCHAR NOT NULL,
            user_id INTEGER NOT NULL,
            username VARCHAR,
            first_name VARCHAR,
            last_name VARCHAR,
            role VARCHAR,
            team VARCHAR,
            is_alive BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Таблица событий игры
        CREATE TABLE game_events (
            id VARCHAR PRIMARY KEY,
            game_id VARCHAR NOT NULL,
            event_type VARCHAR NOT NULL,
            description TEXT,
            data JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Таблица статистики
        CREATE TABLE stats (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL UNIQUE,
            games_played INTEGER DEFAULT 0,
            games_won INTEGER DEFAULT 0,
            games_lost INTEGER DEFAULT 0,
            last_played TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Таблица магазина
        CREATE TABLE shop (
            id SERIAL PRIMARY KEY,
            item_name VARCHAR(255) NOT NULL,
            price INTEGER NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Таблица покупок
        CREATE TABLE purchases (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            item_id INTEGER NOT NULL,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Таблица настроек чата
        CREATE TABLE chat_settings (
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
        
        -- Таблица настроек бота
        CREATE TABLE bot_settings (
            id SERIAL PRIMARY KEY,
            setting_name VARCHAR(255) NOT NULL UNIQUE,
            setting_value TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Таблица действий игроков
        CREATE TABLE player_actions (
            id SERIAL PRIMARY KEY,
            game_id VARCHAR NOT NULL,
            player_id VARCHAR NOT NULL,
            action_type VARCHAR NOT NULL,
            target_id VARCHAR,
            action_data JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Таблица статистики игроков
        CREATE TABLE player_stats (
            id SERIAL PRIMARY KEY,
            player_id VARCHAR NOT NULL,
            user_id BIGINT NOT NULL,
            games_played INTEGER DEFAULT 0,
            games_won INTEGER DEFAULT 0,
            games_lost INTEGER DEFAULT 0,
            roles_played JSONB DEFAULT '{}'::jsonb,
            total_kills INTEGER DEFAULT 0,
            total_deaths INTEGER DEFAULT 0,
            last_played TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Таблица голосований
        CREATE TABLE votes (
            id SERIAL PRIMARY KEY,
            game_id VARCHAR NOT NULL,
            voter_id VARCHAR NOT NULL,
            target_id VARCHAR,
            vote_type VARCHAR NOT NULL,
            round_number INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Создаем индексы
        CREATE INDEX idx_users_user_id ON users(user_id);
        CREATE INDEX idx_games_chat_id ON games(chat_id);
        CREATE INDEX idx_games_status ON games(status);
        CREATE INDEX idx_players_game_id ON players(game_id);
        CREATE INDEX idx_players_user_id ON players(user_id);
        CREATE INDEX idx_game_events_game_id ON game_events(game_id);
        CREATE INDEX idx_stats_user_id ON stats(user_id);
        CREATE INDEX idx_purchases_user_id ON purchases(user_id);
        CREATE INDEX idx_purchases_item_id ON purchases(item_id);
        CREATE INDEX idx_chat_settings_chat_id ON chat_settings(chat_id);
        CREATE INDEX idx_bot_settings_name ON bot_settings(setting_name);
        CREATE INDEX idx_player_actions_game_id ON player_actions(game_id);
        CREATE INDEX idx_player_actions_player_id ON player_actions(player_id);
        CREATE INDEX idx_player_stats_player_id ON player_stats(player_id);
        CREATE INDEX idx_player_stats_user_id ON player_stats(user_id);
        CREATE INDEX idx_votes_game_id ON votes(game_id);
        CREATE INDEX idx_votes_voter_id ON votes(voter_id);
        
        -- Функция для обновления updated_at
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Триггеры для автоматического обновления updated_at
        CREATE TRIGGER trigger_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            
        CREATE TRIGGER trigger_players_updated_at
            BEFORE UPDATE ON players
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            
        CREATE TRIGGER trigger_stats_updated_at
            BEFORE UPDATE ON stats
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            
        CREATE TRIGGER trigger_chat_settings_updated_at
            BEFORE UPDATE ON chat_settings
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            
        CREATE TRIGGER trigger_bot_settings_updated_at
            BEFORE UPDATE ON bot_settings
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            
        CREATE TRIGGER trigger_player_stats_updated_at
            BEFORE UPDATE ON player_stats
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
        
        # Выполняем SQL
        logger.info("🔧 Создаем таблицы заново...")
        execute_query(tables_sql)
        logger.info("✅ Все таблицы созданы успешно")
        
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
