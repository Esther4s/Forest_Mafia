#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Комплексный тест системы перед деплоем
Включает тестирование Docker, базы данных, бота и интеграции
"""

import asyncio
import sys
import os
import subprocess
import time
import traceback
import json
import tempfile
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Импорты для тестирования
try:
    from game_logic import Game, GamePhase, Role, Team, Player
    from night_actions import NightActions
    from night_interface import NightInterface
    from config import config, BOT_TOKEN, DATABASE_URL
    from database_adapter import DatabaseAdapter
    from database_psycopg2 import init_db, close_db, create_tables
    from telegram import Bot
    from telegram.ext import Application
    print("✅ Все модули импортированы успешно")
except Exception as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)


class ComprehensiveTestSuite:
    """Комплексный набор тестов для системы"""
    
    def __init__(self):
        self.test_results = {}
        self.docker_containers = []
        self.temp_files = []
        
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
        """Очистка ресурсов после тестов"""
        print("\n🧹 Очистка ресурсов...")
        
        # Остановка Docker контейнеров
        for container in self.docker_containers:
            try:
                subprocess.run(['docker', 'stop', container], check=False, capture_output=True)
                subprocess.run(['docker', 'rm', container], check=False, capture_output=True)
                print(f"✅ Контейнер {container} остановлен и удален")
            except Exception as e:
                print(f"⚠️ Не удалось остановить контейнер {container}: {e}")
        
        # Удаление временных файлов
        for temp_file in self.temp_files:
            try:
                os.remove(temp_file)
                print(f"✅ Временный файл {temp_file} удален")
            except Exception as e:
                print(f"⚠️ Не удалось удалить {temp_file}: {e}")
    
    def test_docker_build(self) -> bool:
        """Тестирует сборку Docker образа"""
        print("\n🐳 Тестирование сборки Docker образа...")
        
        try:
            # Проверяем наличие Dockerfile
            if not os.path.exists('Dockerfile'):
                self.log_test("Docker Build", False, "Dockerfile не найден")
                return False
            
            # Собираем образ
            result = subprocess.run([
                'docker', 'build', '-t', 'forest-mafia-test', '.'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.log_test("Docker Build", True, "Образ собран успешно")
                return True
            else:
                self.log_test("Docker Build", False, f"Ошибка сборки: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log_test("Docker Build", False, "Таймаут сборки (5 минут)")
            return False
        except Exception as e:
            self.log_test("Docker Build", False, f"Ошибка: {e}")
            return False
    
    def test_docker_compose(self) -> bool:
        """Тестирует Docker Compose конфигурацию"""
        print("\n🐳 Тестирование Docker Compose...")
        
        try:
            # Проверяем наличие docker-compose.yml
            if not os.path.exists('docker-compose.yml'):
                self.log_test("Docker Compose", False, "docker-compose.yml не найден")
                return False
            
            # Валидируем конфигурацию
            result = subprocess.run([
                'docker-compose', 'config'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.log_test("Docker Compose", True, "Конфигурация валидна")
                return True
            else:
                self.log_test("Docker Compose", False, f"Ошибка конфигурации: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_test("Docker Compose", False, f"Ошибка: {e}")
            return False
    
    def test_docker_run(self) -> bool:
        """Тестирует запуск Docker контейнера"""
        print("\n🐳 Тестирование запуска Docker контейнера...")
        
        try:
            # Создаем временный .env файл для тестов
            env_content = f"""BOT_TOKEN=test_token_123456789
DATABASE_URL=sqlite:///test.db
ENVIRONMENT=test
LOG_LEVEL=DEBUG
"""
            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
                f.write(env_content)
                env_file = f.name
                self.temp_files.append(env_file)
            
            # Запускаем контейнер
            result = subprocess.run([
                'docker', 'run', '-d',
                '--name', 'forest-mafia-test-container',
                '--env-file', env_file,
                'forest-mafia-test'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                container_id = result.stdout.strip()
                self.docker_containers.append('forest-mafia-test-container')
                
                # Ждем немного и проверяем статус
                time.sleep(5)
                status_result = subprocess.run([
                    'docker', 'ps', '--filter', 'name=forest-mafia-test-container', '--format', '{{.Status}}'
                ], capture_output=True, text=True)
                
                if 'Up' in status_result.stdout:
                    self.log_test("Docker Run", True, "Контейнер запущен успешно")
                    return True
                else:
                    self.log_test("Docker Run", False, "Контейнер не запустился")
                    return False
            else:
                self.log_test("Docker Run", False, f"Ошибка запуска: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_test("Docker Run", False, f"Ошибка: {e}")
            return False
    
    def test_database_connection(self) -> bool:
        """Тестирует подключение к базе данных"""
        print("\n🗄️ Тестирование подключения к базе данных...")
        
        try:
            # Инициализируем базу данных
            db = init_db()
            if db is None:
                self.log_test("Database Connection", False, "Не удалось инициализировать БД")
                return False
            
            # Создаем таблицы
            tables_created = create_tables()
            if not tables_created:
                self.log_test("Database Connection", False, "Не удалось создать таблицы")
                return False
            
            # Тестируем простой запрос
            from database_psycopg2 import execute_query
            result = execute_query("SELECT 1 as test")
            if result:
                self.log_test("Database Connection", True, "Подключение к БД работает")
                close_db()
                return True
            else:
                self.log_test("Database Connection", False, "Запрос к БД не выполнился")
                return False
                
        except Exception as e:
            self.log_test("Database Connection", False, f"Ошибка: {e}")
            return False
    
    def test_bot_configuration(self) -> bool:
        """Тестирует конфигурацию бота"""
        print("\n🤖 Тестирование конфигурации бота...")
        
        try:
            # Проверяем токен
            if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
                self.log_test("Bot Configuration", False, "Токен бота не настроен")
                return False
            
            # Проверяем конфигурацию
            if not hasattr(config, 'bot_token'):
                self.log_test("Bot Configuration", False, "Конфигурация бота не найдена")
                return False
            
            # Проверяем игровые настройки
            game_settings = config.get_game_settings()
            required_keys = ['min_players', 'max_players', 'night_duration', 'day_duration']
            
            for key in required_keys:
                if key not in game_settings:
                    self.log_test("Bot Configuration", False, f"Отсутствует настройка: {key}")
                    return False
            
            self.log_test("Bot Configuration", True, "Конфигурация бота корректна")
            return True
            
        except Exception as e:
            self.log_test("Bot Configuration", False, f"Ошибка: {e}")
            return False
    
    def test_game_logic(self) -> bool:
        """Тестирует игровую логику"""
        print("\n🎮 Тестирование игровой логики...")
        
        try:
            # Создаем игру
            game = Game(chat_id=12345)
            if not game:
                self.log_test("Game Logic", False, "Не удалось создать игру")
                return False
            
            # Добавляем игроков
            test_players = [
                (111, "Волк1"), (222, "Лиса1"), (333, "Заяц1"), 
                (444, "Заяц2"), (555, "Крот1"), (666, "Бобёр1")
            ]
            
            for user_id, username in test_players:
                if not game.add_player(user_id, username):
                    self.log_test("Game Logic", False, f"Не удалось добавить игрока {username}")
                    return False
            
            # Начинаем игру
            if not game.start_game():
                self.log_test("Game Logic", False, "Не удалось начать игру")
                return False
            
            # Проверяем распределение ролей
            if len(game.players) != len(test_players):
                self.log_test("Game Logic", False, "Количество игроков не совпадает")
                return False
            
            # Проверяем, что все игроки имеют роли
            for player in game.players.values():
                if not player.role or not player.team:
                    self.log_test("Game Logic", False, f"Игрок {player.username} не имеет роли")
                    return False
            
            self.log_test("Game Logic", True, "Игровая логика работает корректно")
            return True
            
        except Exception as e:
            self.log_test("Game Logic", False, f"Ошибка: {e}")
            return False
    
    def test_night_actions(self) -> bool:
        """Тестирует ночные действия"""
        print("\n🌙 Тестирование ночных действий...")
        
        try:
            # Создаем игру с игроками
            game = Game(chat_id=12345)
            test_players = [
                (111, "Волк1"), (222, "Лиса1"), (333, "Заяц1"), 
                (444, "Заяц2"), (555, "Крот1"), (666, "Бобёр1")
            ]
            
            for user_id, username in test_players:
                game.add_player(user_id, username)
            
            game.start_game()
            
            # Создаем ночные действия
            night_actions = NightActions(game)
            if not night_actions:
                self.log_test("Night Actions", False, "Не удалось создать NightActions")
                return False
            
            # Создаем интерфейс ночных действий
            night_interface = NightInterface(game, night_actions)
            if not night_interface:
                self.log_test("Night Actions", False, "Не удалось создать NightInterface")
                return False
            
            self.log_test("Night Actions", True, "Ночные действия работают корректно")
            return True
            
        except Exception as e:
            self.log_test("Night Actions", False, f"Ошибка: {e}")
            return False
    
    def test_telegram_integration(self) -> bool:
        """Тестирует интеграцию с Telegram"""
        print("\n📱 Тестирование интеграции с Telegram...")
        
        try:
            # Проверяем импорты Telegram
            from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
            from telegram.ext import Application, CommandHandler, CallbackQueryHandler
            
            # Создаем приложение (без реального токена)
            app = Application.builder().token("test_token").build()
            if not app:
                self.log_test("Telegram Integration", False, "Не удалось создать Application")
                return False
            
            # Проверяем создание кнопок
            keyboard = [[InlineKeyboardButton("Тест", callback_data="test")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if not reply_markup:
                self.log_test("Telegram Integration", False, "Не удалось создать клавиатуру")
                return False
            
            self.log_test("Telegram Integration", True, "Интеграция с Telegram работает")
            return True
            
        except Exception as e:
            self.log_test("Telegram Integration", False, f"Ошибка: {e}")
            return False
    
    def test_file_structure(self) -> bool:
        """Тестирует структуру файлов проекта"""
        print("\n📁 Тестирование структуры файлов...")
        
        required_files = [
            'bot.py',
            'config.py',
            'game_logic.py',
            'night_actions.py',
            'night_interface.py',
            'database.py',
            'database_adapter.py',
            'requirements.txt',
            'Dockerfile',
            'docker-compose.yml'
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            self.log_test("File Structure", False, f"Отсутствуют файлы: {', '.join(missing_files)}")
            return False
        
        self.log_test("File Structure", True, "Все необходимые файлы присутствуют")
        return True
    
    def test_dependencies(self) -> bool:
        """Тестирует зависимости проекта"""
        print("\n📦 Тестирование зависимостей...")
        
        try:
            # Читаем requirements.txt
            with open('requirements.txt', 'r', encoding='utf-8') as f:
                requirements = f.read().strip().split('\n')
            
            if not requirements or requirements == ['']:
                self.log_test("Dependencies", False, "requirements.txt пуст")
                return False
            
            # Проверяем основные зависимости
            required_packages = [
                'python-telegram-bot',
                'sqlalchemy',
                'psycopg2-binary',
                'python-dotenv'
            ]
            
            missing_packages = []
            for package in required_packages:
                if not any(package in req for req in requirements):
                    missing_packages.append(package)
            
            if missing_packages:
                self.log_test("Dependencies", False, f"Отсутствуют пакеты: {', '.join(missing_packages)}")
                return False
            
            self.log_test("Dependencies", True, "Все зависимости присутствуют")
            return True
            
        except Exception as e:
            self.log_test("Dependencies", False, f"Ошибка: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Запускает все тесты"""
        print("🚀 Запуск комплексного тестирования системы 'Лес и Волки'\n")
        print("=" * 60)
        
        tests = [
            ("File Structure", self.test_file_structure),
            ("Dependencies", self.test_dependencies),
            ("Docker Build", self.test_docker_build),
            ("Docker Compose", self.test_docker_compose),
            ("Database Connection", self.test_database_connection),
            ("Bot Configuration", self.test_bot_configuration),
            ("Game Logic", self.test_game_logic),
            ("Night Actions", self.test_night_actions),
            ("Telegram Integration", self.test_telegram_integration),
            ("Docker Run", self.test_docker_run),
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
            except Exception as e:
                self.log_test(test_name, False, f"Критическая ошибка: {e}")
                traceback.print_exc()
        
        # Очистка
        self.cleanup()
        
        # Результаты
        print("\n" + "=" * 60)
        print("🏁 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        print("=" * 60)
        
        for test_name, result in self.test_results.items():
            status = "✅ ПРОЙДЕН" if result['success'] else "❌ ПРОВАЛЕН"
            print(f"{status}: {test_name}")
            if result['message']:
                print(f"    💬 {result['message']}")
        
        print(f"\n📊 Итого: {passed_tests}/{total_tests} тестов пройдено")
        
        if passed_tests == total_tests:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система готова к деплою.")
            return True
        else:
            print("⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ! Исправьте ошибки перед деплоем.")
            return False


def main():
    """Основная функция"""
    test_suite = ComprehensiveTestSuite()
    
    try:
        success = test_suite.run_all_tests()
        
        # Сохраняем результаты в файл
        with open('test_results.json', 'w', encoding='utf-8') as f:
            json.dump(test_suite.test_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Результаты сохранены в test_results.json")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
        test_suite.cleanup()
        return 1
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        traceback.print_exc()
        test_suite.cleanup()
        return 1


if __name__ == "__main__":
    sys.exit(main())
