#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Специализированные тесты для базы данных
"""

import os
import sys
import tempfile
import traceback
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Импорты для работы с базой данных
try:
    from database_psycopg2 import (
        init_db, close_db, create_tables,
        create_user, get_user_by_telegram_id, update_user_balance, get_user_balance,
        execute_query, fetch_one, fetch_query,
        get_chat_settings, update_chat_settings, reset_chat_settings,
        save_player_action, save_vote, update_player_stats, update_user_stats,
        get_bot_setting, set_bot_setting,
        save_game_to_db, save_player_to_db, update_game_phase, finish_game_in_db,
        get_team_stats, get_top_players, get_best_predator, get_best_herbivore, get_player_detailed_stats,
        get_player_chat_stats, add_nuts_to_user, get_shop_items
    )
    from database_adapter import DatabaseAdapter
    from config import DATABASE_URL
    print("✅ Модули базы данных импортированы успешно")
except Exception as e:
    print(f"❌ Ошибка импорта модулей БД: {e}")
    sys.exit(1)


class DatabaseTestSuite:
    """Набор тестов для базы данных"""
    
    def __init__(self):
        self.test_results = {}
        self.db_connection = None
        self.test_data = {
            'users': [],
            'games': [],
            'players': []
        }
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Логирует результат теста"""
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
        self.test_results[test_name] = {
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
    
    def cleanup(self):
        """Очистка тестовых данных"""
        print("\n🧹 Очистка тестовых данных...")
        
        try:
            if self.db_connection:
                # Удаляем тестовые данные
                for user_id in self.test_data['users']:
                    execute_query("DELETE FROM users WHERE user_id = %s", (user_id,))
                
                for game_id in self.test_data['games']:
                    execute_query("DELETE FROM games WHERE id = %s", (game_id,))
                
                close_db()
                print("✅ Тестовые данные очищены")
        except Exception as e:
            print(f"⚠️ Ошибка очистки: {e}")
    
    def test_database_connection(self) -> bool:
        """Тестирует подключение к базе данных"""
        print("🗄️ Тестирование подключения к базе данных...")
        
        try:
            self.db_connection = init_db()
            if self.db_connection is None:
                self.log_test("Database Connection", False, "Не удалось инициализировать БД")
                return False
            
            # Тестируем простой запрос
            result = execute_query("SELECT 1 as test")
            if result:
                self.log_test("Database Connection", True, "Подключение к БД работает")
                return True
            else:
                self.log_test("Database Connection", False, "Запрос к БД не выполнился")
                return False
                
        except Exception as e:
            self.log_test("Database Connection", False, f"Ошибка: {e}")
            return False
    
    def test_table_creation(self) -> bool:
        """Тестирует создание таблиц"""
        print("🗄️ Тестирование создания таблиц...")
        
        try:
            tables_created = create_tables()
            if not tables_created:
                self.log_test("Table Creation", False, "Не удалось создать таблицы")
                return False
            
            # Проверяем наличие основных таблиц
            required_tables = ['users', 'games', 'players', 'game_events', 'chat_settings']
            missing_tables = []
            
            for table in required_tables:
                result = execute_query(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                    (table,)
                )
                if not result or not result[0]:
                    missing_tables.append(table)
            
            if missing_tables:
                self.log_test("Table Creation", False, f"Отсутствуют таблицы: {', '.join(missing_tables)}")
                return False
            
            self.log_test("Table Creation", True, "Все таблицы созданы успешно")
            return True
            
        except Exception as e:
            self.log_test("Table Creation", False, f"Ошибка: {e}")
            return False
    
    def test_user_operations(self) -> bool:
        """Тестирует операции с пользователями"""
        print("🗄️ Тестирование операций с пользователями...")
        
        try:
            test_user_id = 999999
            test_username = "test_user"
            
            # Создаем пользователя
            success = create_user(test_user_id, test_username, "Test", "User")
            if not success:
                self.log_test("User Operations", False, "Не удалось создать пользователя")
                return False
            
            self.test_data['users'].append(test_user_id)
            
            # Получаем пользователя
            user = get_user_by_telegram_id(test_user_id)
            if not user:
                self.log_test("User Operations", False, "Не удалось получить пользователя")
                return False
            
            # Обновляем баланс
            success = update_user_balance(test_user_id, 100)
            if not success:
                self.log_test("User Operations", False, "Не удалось обновить баланс")
                return False
            
            # Проверяем баланс
            balance = get_user_balance(test_user_id)
            if balance != 100:
                self.log_test("User Operations", False, f"Неверный баланс: {balance}")
                return False
            
            self.log_test("User Operations", True, "Операции с пользователями работают")
            return True
            
        except Exception as e:
            self.log_test("User Operations", False, f"Ошибка: {e}")
            return False
    
    def test_game_operations(self) -> bool:
        """Тестирует операции с играми"""
        print("🗄️ Тестирование операций с играми...")
        
        try:
            test_chat_id = 888888
            test_game_id = "test_game_123"
            
            # Создаем игру
            success = save_game_to_db(test_game_id, test_chat_id, "registration", 0)
            if not success:
                self.log_test("Game Operations", False, "Не удалось создать игру")
                return False
            
            self.test_data['games'].append(test_game_id)
            
            # Обновляем фазу игры
            success = update_game_phase(test_game_id, "night", 1)
            if not success:
                self.log_test("Game Operations", False, "Не удалось обновить фазу игры")
                return False
            
            # Завершаем игру
            success = finish_game_in_db(test_game_id, "herbivores")
            if not success:
                self.log_test("Game Operations", False, "Не удалось завершить игру")
                return False
            
            self.log_test("Game Operations", True, "Операции с играми работают")
            return True
            
        except Exception as e:
            self.log_test("Game Operations", False, f"Ошибка: {e}")
            return False
    
    def test_player_operations(self) -> bool:
        """Тестирует операции с игроками"""
        print("🗄️ Тестирование операций с игроками...")
        
        try:
            test_user_id = 777777
            test_game_id = "test_game_456"
            test_chat_id = 666666
            
            # Создаем игру
            save_game_to_db(test_game_id, test_chat_id, "active", 1)
            self.test_data['games'].append(test_game_id)
            
            # Создаем игрока
            success = save_player_to_db(test_game_id, test_user_id, "test_player", "Test", "Player", "wolf", "predators")
            if not success:
                self.log_test("Player Operations", False, "Не удалось создать игрока")
                return False
            
            self.test_data['players'].append((test_game_id, test_user_id))
            
            # Сохраняем действие игрока
            success = save_player_action(test_game_id, test_user_id, "vote", "target_user_id")
            if not success:
                self.log_test("Player Operations", False, "Не удалось сохранить действие игрока")
                return False
            
            # Сохраняем голос
            success = save_vote(test_game_id, test_user_id, 555555)
            if not success:
                self.log_test("Player Operations", False, "Не удалось сохранить голос")
                return False
            
            self.log_test("Player Operations", True, "Операции с игроками работают")
            return True
            
        except Exception as e:
            self.log_test("Player Operations", False, f"Ошибка: {e}")
            return False
    
    def test_chat_settings(self) -> bool:
        """Тестирует настройки чата"""
        print("🗄️ Тестирование настроек чата...")
        
        try:
            test_chat_id = 555555
            test_settings = {
                "min_players": 3,
                "night_duration": 60,
                "day_duration": 300,
                "voting_duration": 120
            }
            
            # Обновляем настройки
            success = update_chat_settings(test_chat_id, test_settings)
            if not success:
                self.log_test("Chat Settings", False, "Не удалось обновить настройки чата")
                return False
            
            # Получаем настройки
            settings = get_chat_settings(test_chat_id)
            if not settings:
                self.log_test("Chat Settings", False, "Не удалось получить настройки чата")
                return False
            
            # Проверяем значения
            if settings.get("min_players") != 3:
                self.log_test("Chat Settings", False, "Неверные настройки чата")
                return False
            
            # Сбрасываем настройки
            success = reset_chat_settings(test_chat_id)
            if not success:
                self.log_test("Chat Settings", False, "Не удалось сбросить настройки чата")
                return False
            
            self.log_test("Chat Settings", True, "Настройки чата работают")
            return True
            
        except Exception as e:
            self.log_test("Chat Settings", False, f"Ошибка: {e}")
            return False
    
    def test_bot_settings(self) -> bool:
        """Тестирует настройки бота"""
        print("🗄️ Тестирование настроек бота...")
        
        try:
            test_key = "test_setting"
            test_value = "test_value_123"
            
            # Устанавливаем настройку
            success = set_bot_setting(test_key, test_value)
            if not success:
                self.log_test("Bot Settings", False, "Не удалось установить настройку бота")
                return False
            
            # Получаем настройку
            value = get_bot_setting(test_key)
            if value != test_value:
                self.log_test("Bot Settings", False, f"Неверное значение настройки: {value}")
                return False
            
            self.log_test("Bot Settings", True, "Настройки бота работают")
            return True
            
        except Exception as e:
            self.log_test("Bot Settings", False, f"Ошибка: {e}")
            return False
    
    def test_statistics(self) -> bool:
        """Тестирует статистику"""
        print("🗄️ Тестирование статистики...")
        
        try:
            # Тестируем получение статистики команд
            team_stats = get_team_stats()
            if team_stats is None:
                self.log_test("Statistics", False, "Не удалось получить статистику команд")
                return False
            
            # Тестируем получение топ игроков
            top_players = get_top_players(10)
            if top_players is None:
                self.log_test("Statistics", False, "Не удалось получить топ игроков")
                return False
            
            # Тестируем получение лучших хищников
            best_predator = get_best_predator()
            if best_predator is None:
                self.log_test("Statistics", False, "Не удалось получить лучшего хищника")
                return False
            
            # Тестируем получение лучших травоядных
            best_herbivore = get_best_herbivore()
            if best_herbivore is None:
                self.log_test("Statistics", False, "Не удалось получить лучшего травоядного")
                return False
            
            self.log_test("Statistics", True, "Статистика работает")
            return True
            
        except Exception as e:
            self.log_test("Statistics", False, f"Ошибка: {e}")
            return False
    
    def test_shop_operations(self) -> bool:
        """Тестирует операции магазина"""
        print("🗄️ Тестирование операций магазина...")
        
        try:
            test_user_id = 444444
            
            # Добавляем орехи пользователю
            success = add_nuts_to_user(test_user_id, 50)
            if not success:
                self.log_test("Shop Operations", False, "Не удалось добавить орехи")
                return False
            
            # Получаем предметы магазина
            shop_items = get_shop_items()
            if shop_items is None:
                self.log_test("Shop Operations", False, "Не удалось получить предметы магазина")
                return False
            
            self.log_test("Shop Operations", True, "Операции магазина работают")
            return True
            
        except Exception as e:
            self.log_test("Shop Operations", False, f"Ошибка: {e}")
            return False
    
    def test_database_adapter(self) -> bool:
        """Тестирует адаптер базы данных"""
        print("🗄️ Тестирование адаптера базы данных...")
        
        try:
            adapter = DatabaseAdapter()
            if not adapter:
                self.log_test("Database Adapter", False, "Не удалось создать адаптер")
                return False
            
            # Тестируем основные методы адаптера
            if not hasattr(adapter, 'get_user') or not hasattr(adapter, 'save_user'):
                self.log_test("Database Adapter", False, "Адаптер не имеет необходимых методов")
                return False
            
            self.log_test("Database Adapter", True, "Адаптер базы данных работает")
            return True
            
        except Exception as e:
            self.log_test("Database Adapter", False, f"Ошибка: {e}")
            return False
    
    def test_database_performance(self) -> bool:
        """Тестирует производительность базы данных"""
        print("🗄️ Тестирование производительности базы данных...")
        
        try:
            import time
            
            # Тестируем время выполнения запросов
            start_time = time.time()
            
            # Выполняем несколько запросов
            for i in range(10):
                execute_query("SELECT 1 as test")
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            if execution_time > 5.0:  # Больше 5 секунд
                self.log_test("Database Performance", False, f"Медленное выполнение: {execution_time:.2f}s")
                return False
            
            self.log_test("Database Performance", True, f"Производительность нормальная: {execution_time:.2f}s")
            return True
            
        except Exception as e:
            self.log_test("Database Performance", False, f"Ошибка: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Запускает все тесты базы данных"""
        print("🚀 Запуск тестов базы данных\n")
        print("=" * 50)
        
        tests = [
            ("Database Connection", self.test_database_connection),
            ("Table Creation", self.test_table_creation),
            ("User Operations", self.test_user_operations),
            ("Game Operations", self.test_game_operations),
            ("Player Operations", self.test_player_operations),
            ("Chat Settings", self.test_chat_settings),
            ("Bot Settings", self.test_bot_settings),
            ("Statistics", self.test_statistics),
            ("Shop Operations", self.test_shop_operations),
            ("Database Adapter", self.test_database_adapter),
            ("Database Performance", self.test_database_performance),
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
                print()  # Пустая строка между тестами
            except Exception as e:
                print(f"❌ Критическая ошибка в {test_name}: {e}")
                traceback.print_exc()
                print()
        
        # Очистка
        self.cleanup()
        
        # Результаты
        print("=" * 50)
        print(f"🏁 Тесты базы данных: {passed_tests}/{total_tests} пройдено")
        
        if passed_tests == total_tests:
            print("🎉 Все тесты базы данных пройдены!")
            return True
        else:
            print("⚠️ Некоторые тесты базы данных провалены!")
            return False


def main():
    """Основная функция"""
    test_suite = DatabaseTestSuite()
    
    try:
        success = test_suite.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано")
        test_suite.cleanup()
        return 1
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        traceback.print_exc()
        test_suite.cleanup()
        return 1


if __name__ == "__main__":
    sys.exit(main())
