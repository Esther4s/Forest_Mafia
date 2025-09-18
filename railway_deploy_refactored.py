#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway Deployment Script - Refactored Version

Этот скрипт выполняет полный цикл деплоя бота на Railway:
1. Проверка переменных окружения
2. Установка зависимостей
3. Тестирование импортов
4. Проверка подключения к базе данных
5. Запуск бота

Автор: Refactored by AI Assistant
Версия: 2.0
"""

import os
import sys
import subprocess
import time
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from contextlib import contextmanager


class DeploymentStatus(Enum):
    """Статусы деплоя"""
    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"


@dataclass
class DeploymentConfig:
    """Конфигурация деплоя"""
    required_env_vars: List[str]
    requirements_file: str
    bot_module_name: str
    bot_class_name: str
    test_query: str


@dataclass
class DeploymentResult:
    """Результат операции деплоя"""
    status: DeploymentStatus
    message: str
    error: Optional[Exception] = None


class DeploymentLogger:
    """Логгер для операций деплоя с эмодзи и цветным выводом"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
    
    def _setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def info(self, message: str, emoji: str = "ℹ️"):
        """Информационное сообщение"""
        self.logger.info(f"{emoji} {message}")
    
    def success(self, message: str):
        """Сообщение об успехе"""
        self.logger.info(f"✅ {message}")
    
    def error(self, message: str):
        """Сообщение об ошибке"""
        self.logger.error(f"❌ {message}")
    
    def warning(self, message: str):
        """Предупреждение"""
        self.logger.warning(f"⚠️ {message}")
    
    def step(self, message: str):
        """Сообщение о шаге процесса"""
        self.logger.info(f"🔄 {message}")


class EnvironmentChecker:
    """Проверка переменных окружения"""
    
    def __init__(self, logger: DeploymentLogger):
        self.logger = logger
    
    def check_required_variables(self, required_vars: List[str]) -> DeploymentResult:
        """
        Проверяет наличие всех необходимых переменных окружения
        
        Args:
            required_vars: Список обязательных переменных
            
        Returns:
            DeploymentResult с результатом проверки
        """
        self.logger.info("Проверка переменных окружения...", "🔍")
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            error_msg = f"Отсутствуют переменные: {', '.join(missing_vars)}"
            self.logger.error(error_msg)
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                message=error_msg
            )
        
        self.logger.success("Переменные окружения настроены")
        return DeploymentResult(
            status=DeploymentStatus.SUCCESS,
            message="Все переменные окружения найдены"
        )


class DependencyManager:
    """Управление зависимостями"""
    
    def __init__(self, logger: DeploymentLogger):
        self.logger = logger
    
    def install_dependencies(self, requirements_file: str) -> DeploymentResult:
        """
        Устанавливает зависимости из requirements.txt
        
        Args:
            requirements_file: Путь к файлу requirements.txt
            
        Returns:
            DeploymentResult с результатом установки
        """
        self.logger.info("Установка зависимостей...", "📦")
        
        if not os.path.exists(requirements_file):
            error_msg = f"Файл {requirements_file} не найден"
            self.logger.error(error_msg)
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                message=error_msg
            )
        
        try:
            # Выполняем установку зависимостей
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', requirements_file],
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 минут таймаут
            )
            
            self.logger.success("Зависимости установлены")
            return DeploymentResult(
                status=DeploymentStatus.SUCCESS,
                message="Все зависимости установлены успешно"
            )
            
        except subprocess.TimeoutExpired:
            error_msg = "Таймаут при установке зависимостей"
            self.logger.error(error_msg)
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                message=error_msg
            )
        except subprocess.CalledProcessError as e:
            error_msg = f"Ошибка установки зависимостей: {e}"
            self.logger.error(error_msg)
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                message=error_msg,
                error=e
            )


class ImportTester:
    """Тестирование импортов модулей"""
    
    def __init__(self, logger: DeploymentLogger):
        self.logger = logger
    
    def test_critical_imports(self, bot_module: str, bot_class: str) -> DeploymentResult:
        """
        Тестирует импорт критически важных модулей
        
        Args:
            bot_module: Имя модуля бота
            bot_class: Имя класса бота
            
        Returns:
            DeploymentResult с результатом тестирования
        """
        self.logger.info("Тестирование импортов...", "🧪")
        
        critical_modules = [
            (bot_module, bot_class),
            ('game_logic', 'Game'),
            ('night_actions', 'NightActions'),
            ('night_interface', 'NightInterface'),
            ('config', 'BOT_TOKEN')
        ]
        
        failed_imports = []
        
        for module_name, class_name in critical_modules:
            try:
                module = __import__(module_name, fromlist=[class_name])
                getattr(module, class_name)
            except ImportError as e:
                failed_imports.append(f"{module_name}.{class_name}: {e}")
            except AttributeError as e:
                failed_imports.append(f"{module_name}.{class_name}: {e}")
        
        if failed_imports:
            error_msg = f"Ошибки импорта: {'; '.join(failed_imports)}"
            self.logger.error(error_msg)
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                message=error_msg
            )
        
        self.logger.success("Все модули импортированы")
        return DeploymentResult(
            status=DeploymentStatus.SUCCESS,
            message="Все критические модули импортированы успешно"
        )


class DatabaseTester:
    """Тестирование подключения к базе данных"""
    
    def __init__(self, logger: DeploymentLogger):
        self.logger = logger
    
    def test_database_connection(self, test_query: str) -> DeploymentResult:
        """
        Тестирует подключение к базе данных
        
        Args:
            test_query: Тестовый SQL запрос
            
        Returns:
            DeploymentResult с результатом тестирования
        """
        self.logger.info("Тестирование базы данных...", "🗄️")
        
        try:
            from database_psycopg2 import init_db, execute_query, close_db
            
            # Инициализируем подключение
            db_connection = init_db()
            if db_connection is None:
                error_msg = "Не удалось подключиться к базе данных"
                self.logger.error(error_msg)
                return DeploymentResult(
                    status=DeploymentStatus.FAILED,
                    message=error_msg
                )
            
            # Выполняем тестовый запрос
            result = execute_query(test_query)
            if not result:
                error_msg = "Тестовый запрос к БД не выполнился"
                self.logger.error(error_msg)
                close_db()
                return DeploymentResult(
                    status=DeploymentStatus.FAILED,
                    message=error_msg
                )
            
            # Закрываем подключение
            close_db()
            self.logger.success("База данных работает")
            return DeploymentResult(
                status=DeploymentStatus.SUCCESS,
                message="Подключение к базе данных успешно"
            )
            
        except ImportError as e:
            error_msg = f"Не удалось импортировать модули БД: {e}"
            self.logger.error(error_msg)
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                message=error_msg,
                error=e
            )
        except Exception as e:
            error_msg = f"Ошибка при тестировании БД: {e}"
            self.logger.error(error_msg)
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                message=error_msg,
                error=e
            )


class BotLauncher:
    """Запуск бота"""
    
    def __init__(self, logger: DeploymentLogger):
        self.logger = logger
    
    def launch_bot(self, bot_module: str, bot_class: str) -> DeploymentResult:
        """
        Запускает бота
        
        Args:
            bot_module: Имя модуля бота
            bot_class: Имя класса бота
            
        Returns:
            DeploymentResult с результатом запуска
        """
        self.logger.info("Запуск бота...", "🚀")
        
        try:
            # Импортируем модуль бота
            module = __import__(bot_module, fromlist=[bot_class])
            bot_class_obj = getattr(module, bot_class)
            
            # Создаем экземпляр бота
            bot_instance = bot_class_obj()
            self.logger.success("Бот создан успешно")
            
            self.logger.step("Запуск бота...")
            
            # Запускаем бота (блокирующий вызов)
            bot_instance.run()
            
            return DeploymentResult(
                status=DeploymentStatus.SUCCESS,
                message="Бот запущен успешно"
            )
            
        except ImportError as e:
            error_msg = f"Не удалось импортировать {bot_module}.{bot_class}: {e}"
            self.logger.error(error_msg)
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                message=error_msg,
                error=e
            )
        except Exception as e:
            error_msg = f"Ошибка запуска бота: {e}"
            self.logger.error(error_msg)
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                message=error_msg,
                error=e
            )


class RailwayDeploymentManager:
    """Основной менеджер деплоя на Railway"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.logger = DeploymentLogger()
        self.env_checker = EnvironmentChecker(self.logger)
        self.dependency_manager = DependencyManager(self.logger)
        self.import_tester = ImportTester(self.logger)
        self.db_tester = DatabaseTester(self.logger)
        self.bot_launcher = BotLauncher(self.logger)
    
    def run_deployment(self) -> DeploymentResult:
        """
        Выполняет полный цикл деплоя
        
        Returns:
            DeploymentResult с результатом деплоя
        """
        self.logger.info("ДЕПЛОЙ НА RAILWAY", "🚀")
        self.logger.info("=" * 50)
        
        # Список шагов деплоя
        deployment_steps = [
            ("Проверка окружения", self._check_environment),
            ("Установка зависимостей", self._install_dependencies),
            ("Тестирование импортов", self._test_imports),
            ("Проверка базы данных", self._test_database),
            ("Запуск бота", self._launch_bot)
        ]
        
        # Выполняем каждый шаг
        for step_name, step_function in deployment_steps:
            self.logger.step(f"Выполнение: {step_name}")
            
            result = step_function()
            if result.status == DeploymentStatus.FAILED:
                self.logger.error(f"Деплой прерван на шаге '{step_name}': {result.message}")
                return result
        
        self.logger.success("Все проверки пройдены!")
        return DeploymentResult(
            status=DeploymentStatus.SUCCESS,
            message="Деплой выполнен успешно"
        )
    
    def _check_environment(self) -> DeploymentResult:
        """Проверка переменных окружения"""
        return self.env_checker.check_required_variables(self.config.required_env_vars)
    
    def _install_dependencies(self) -> DeploymentResult:
        """Установка зависимостей"""
        return self.dependency_manager.install_dependencies(self.config.requirements_file)
    
    def _test_imports(self) -> DeploymentResult:
        """Тестирование импортов"""
        return self.import_tester.test_critical_imports(
            self.config.bot_module_name,
            self.config.bot_class_name
        )
    
    def _test_database(self) -> DeploymentResult:
        """Тестирование базы данных"""
        return self.db_tester.test_database_connection(self.config.test_query)
    
    def _launch_bot(self) -> DeploymentResult:
        """Запуск бота"""
        return self.bot_launcher.launch_bot(
            self.config.bot_module_name,
            self.config.bot_class_name
        )


def create_deployment_config() -> DeploymentConfig:
    """Создает конфигурацию деплоя"""
    return DeploymentConfig(
        required_env_vars=['BOT_TOKEN', 'DATABASE_URL'],
        requirements_file='requirements.txt',
        bot_module_name='bot',
        bot_class_name='ForestWolvesBot',  # Исправлено: было ForestMafiaBot
        test_query='SELECT 1 as test'
    )


def main() -> int:
    """
    Основная функция деплоя
    
    Returns:
        Код выхода (0 - успех, 1 - ошибка)
    """
    try:
        # Создаем конфигурацию
        config = create_deployment_config()
        
        # Создаем менеджер деплоя
        deployment_manager = RailwayDeploymentManager(config)
        
        # Выполняем деплой
        result = deployment_manager.run_deployment()
        
        if result.status == DeploymentStatus.SUCCESS:
            return 0
        else:
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Деплой прерван пользователем")
        return 1
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
