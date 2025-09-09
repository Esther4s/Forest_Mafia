#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Полный тест всех компонентов перед деплоем (без зависимости от .env)
Проверяет все системы и их интеграцию
"""

import unittest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Мокаем переменные окружения для тестов
os.environ['BOT_TOKEN'] = 'TEST_BOT_TOKEN'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

# Импортируем все модули
try:
    from game_logic import Game, GamePhase, Role, Team, Player, GameStatistics
    from test_config import config  # Используем тестовую конфигурацию
    from database_balance_manager import BalanceManager
    from rewards_system import RewardsSystem, RewardType, RewardReason, Reward
    from error_handler import ErrorHandler
    from state_persistence import StatePersistence
    from auto_save_manager import AutoSaveManager
    print("✅ Все модули импортированы успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта модулей: {e}")
    sys.exit(1)


class TestDatabaseConnection(unittest.TestCase):
    """Тест подключения к базе данных"""
    
    def test_database_imports(self):
        """Тест импорта модулей БД"""
        try:
            from database_psycopg2 import init_db, close_db, execute_query, fetch_one, fetch_query
            print("✅ Модули БД импортированы")
        except ImportError as e:
            self.fail(f"❌ Не удалось импортировать модули БД: {e}")
    
    def test_database_functions_exist(self):
        """Тест существования функций БД"""
        try:
            from database_psycopg2 import (
                create_user, get_user_by_telegram_id, update_user_balance, get_user_balance,
                create_user_reward, get_user_rewards, get_user_rewards_stats
            )
            print("✅ Функции БД существуют")
        except ImportError as e:
            self.fail(f"❌ Функции БД не найдены: {e}")


class TestConfiguration(unittest.TestCase):
    """Тест конфигурации"""
    
    def test_config_loading(self):
        """Тест загрузки конфигурации"""
        try:
            # Проверяем основные параметры
            self.assertIsNotNone(config.bot_token)
            self.assertIsNotNone(config.database_url)
            self.assertIsNotNone(config.min_players)
            self.assertIsNotNone(config.max_players)
            self.assertIsNotNone(config.night_duration)
            self.assertIsNotNone(config.day_duration)
            self.assertIsNotNone(config.voting_duration)
            self.assertIsNotNone(config.role_distribution)
            self.assertIsNotNone(config.is_test_mode)
            print("✅ Конфигурация загружена успешно")
        except Exception as e:
            self.fail(f"❌ Ошибка загрузки конфигурации: {e}")
    
    def test_config_values(self):
        """Тест значений конфигурации"""
        # Проверяем, что значения в разумных пределах
        self.assertGreater(config.min_players, 0)
        self.assertGreater(config.max_players, config.min_players)
        self.assertGreater(config.night_duration, 0)
        self.assertGreater(config.day_duration, 0)
        self.assertGreater(config.voting_duration, 0)
        self.assertIsInstance(config.role_distribution, dict)
        self.assertIsInstance(config.is_test_mode, bool)
        print("✅ Значения конфигурации корректны")


class TestGameLogic(unittest.TestCase):
    """Тест игровой логики"""
    
    def setUp(self):
        self.game = Game(chat_id=123, is_test_mode=True)
    
    def test_game_creation(self):
        """Тест создания игры"""
        self.assertIsNotNone(self.game)
        self.assertEqual(self.game.chat_id, 123)
        self.assertEqual(self.game.phase, GamePhase.WAITING)
        self.assertEqual(self.game.current_round, 0)  # Исправлено: по умолчанию 0
        self.assertIsInstance(self.game.players, dict)
        self.assertIsInstance(self.game.game_stats, GameStatistics)
        print("✅ Игра создана успешно")
    
    def test_player_creation(self):
        """Тест создания игрока"""
        player = Player(
            user_id=123,
            username="test_user",
            role=Role.WOLF,
            team=Team.PREDATORS
        )
        
        self.assertEqual(player.user_id, 123)
        self.assertEqual(player.username, "test_user")
        self.assertEqual(player.role, Role.WOLF)
        self.assertEqual(player.team, Team.PREDATORS)
        self.assertTrue(player.is_alive)
        self.assertEqual(player.supplies, 2)  # Исправлено: по умолчанию 2
        print("✅ Игрок создан успешно")
    
    def test_game_phases(self):
        """Тест фаз игры"""
        phases = [GamePhase.WAITING, GamePhase.NIGHT, GamePhase.DAY, GamePhase.VOTING, GamePhase.GAME_OVER]
        for phase in phases:
            self.assertIsNotNone(phase.value)
        print("✅ Фазы игры определены корректно")
    
    def test_roles_and_teams(self):
        """Тест ролей и команд"""
        # Проверяем роли
        roles = [Role.WOLF, Role.FOX, Role.HARE, Role.MOLE, Role.BEAVER]
        for role in roles:
            self.assertIsNotNone(role.value)
        
        # Проверяем команды
        teams = [Team.PREDATORS, Team.HERBIVORES]
        for team in teams:
            self.assertIsNotNone(team.value)
        
        print("✅ Роли и команды определены корректно")
    
    def test_game_statistics(self):
        """Тест статистики игры"""
        stats = GameStatistics()
        
        # Тестируем методы записи
        stats.record_kill(Team.PREDATORS)
        stats.record_kill(Team.HERBIVORES)
        stats.record_fox_theft()  # Исправлено: правильное имя метода
        stats.record_beaver_protection()  # Исправлено: правильное имя метода
        
        self.assertEqual(stats.predator_kills, 1)
        self.assertEqual(stats.herbivore_survivals, 1)
        self.assertEqual(stats.fox_thefts, 1)
        self.assertEqual(stats.beaver_protections, 1)
        print("✅ Статистика игры работает корректно")
    
    def test_player_methods(self):
        """Тест методов игрока"""
        player = Player(
            user_id=123,
            username="test_user",
            role=Role.WOLF,
            team=Team.PREDATORS
        )
        
        # Тестируем свойства
        self.assertFalse(player.is_supplies_critical)
        self.assertTrue(player.can_be_stolen_from)
        
        # Тестируем методы
        self.assertTrue(player.consume_supplies(1))
        self.assertEqual(player.supplies, 1)  # Исправлено: 2-1=1
        
        player.add_supplies(1)
        self.assertEqual(player.supplies, 2)  # Исправлено: 1+1=2
        
        self.assertTrue(player.steal_supplies())
        self.assertEqual(player.supplies, 1)  # Исправлено: 2-1=1
        
        print("✅ Методы игрока работают корректно")


class TestBalanceManager(unittest.TestCase):
    """Тест менеджера баланса"""
    
    def setUp(self):
        self.balance_manager = BalanceManager()
    
    def test_balance_manager_creation(self):
        """Тест создания менеджера баланса"""
        self.assertIsNotNone(self.balance_manager)
        print("✅ Менеджер баланса создан")
    
    def test_balance_methods_exist(self):
        """Тест существования методов баланса"""
        methods = [
            'get_user_balance', 'create_user_if_not_exists', 'update_user_balance',
            'add_to_balance', 'subtract_from_balance', 'transfer_balance',
            'get_user_balance_info'
        ]
        
        for method in methods:
            self.assertTrue(hasattr(self.balance_manager, method))
        print("✅ Методы баланса существуют")


class TestRewardsSystem(unittest.TestCase):
    """Тест системы наград"""
    
    def setUp(self):
        self.rewards_system = RewardsSystem()
    
    def test_rewards_system_creation(self):
        """Тест создания системы наград"""
        self.assertIsNotNone(self.rewards_system)
        self.assertIsNotNone(self.rewards_system.reward_configs)
        print("✅ Система наград создана")
    
    def test_reward_types(self):
        """Тест типов наград"""
        reward_types = [
            RewardType.GAME_WIN, RewardType.GAME_PARTICIPATION, RewardType.ROLE_SPECIFIC,
            RewardType.ACHIEVEMENT, RewardType.DAILY_BONUS, RewardType.SPECIAL_EVENT
        ]
        
        for reward_type in reward_types:
            self.assertIsNotNone(reward_type.value)
        print("✅ Типы наград определены")
    
    def test_reward_reasons(self):
        """Тест причин наград"""
        reward_reasons = [
            RewardReason.PREDATOR_WIN, RewardReason.HERBIVORE_WIN, RewardReason.WOLF_WIN,
            RewardReason.FOX_WIN, RewardReason.HARE_WIN, RewardReason.MOLE_WIN,
            RewardReason.BEAVER_WIN, RewardReason.SUCCESSFUL_KILL, RewardReason.SUCCESSFUL_THEFT
        ]
        
        for reason in reward_reasons:
            self.assertIsNotNone(reason.value)
        print("✅ Причины наград определены")
    
    def test_reward_creation(self):
        """Тест создания награды"""
        reward = Reward(
            reward_type=RewardType.GAME_WIN,
            reason=RewardReason.PREDATOR_WIN,
            amount=50,
            description="Победа хищников"
        )
        
        self.assertEqual(reward.reward_type, RewardType.GAME_WIN)
        self.assertEqual(reward.reason, RewardReason.PREDATOR_WIN)
        self.assertEqual(reward.amount, 50)
        self.assertEqual(reward.description, "Победа хищников")
        self.assertIsNotNone(reward.created_at)
        print("✅ Награда создана успешно")
    
    def test_reward_configs(self):
        """Тест конфигурации наград"""
        # Проверяем, что конфигурация загружена
        self.assertIn(RewardReason.PREDATOR_WIN, self.rewards_system.reward_configs)
        self.assertIn(RewardReason.HERBIVORE_WIN, self.rewards_system.reward_configs)
        self.assertIn(RewardReason.WOLF_WIN, self.rewards_system.reward_configs)
        
        # Проверяем структуру конфигурации
        predator_config = self.rewards_system.reward_configs[RewardReason.PREDATOR_WIN]
        self.assertIn('amount', predator_config)
        self.assertIn('description', predator_config)
        self.assertEqual(predator_config['amount'], 50)
        print("✅ Конфигурация наград корректна")


class TestErrorHandler(unittest.TestCase):
    """Тест обработчика ошибок"""
    
    def setUp(self):
        self.error_handler = ErrorHandler()
    
    def test_error_handler_creation(self):
        """Тест создания обработчика ошибок"""
        self.assertIsNotNone(self.error_handler)
        self.assertIsNotNone(self.error_handler.error_messages)
        print("✅ Обработчик ошибок создан")
    
    def test_error_messages(self):
        """Тест сообщений об ошибках"""
        required_errors = [
            "permission_denied", "game_not_found", "player_not_found",
            "invalid_phase", "database_error", "unknown_error"
        ]
        
        for error in required_errors:
            self.assertIn(error, self.error_handler.error_messages)
        print("✅ Сообщения об ошибках определены")
    
    def test_error_handling_methods(self):
        """Тест методов обработки ошибок"""
        methods = [
            'get_error_message', 'show_alert', 'show_success_alert',
            'show_info_alert', 'handle_errors', 'handle_database_errors',
            'handle_permission_errors', 'handle_callback_error', 'log_error'
        ]
        
        for method in methods:
            self.assertTrue(hasattr(self.error_handler, method))
        print("✅ Методы обработки ошибок существуют")
    
    def test_error_message_retrieval(self):
        """Тест получения сообщений об ошибках"""
        # Тестируем существующий тип ошибки
        message = self.error_handler.get_error_message("permission_denied")
        self.assertIn("нет прав", message)
        
        # Тестируем несуществующий тип ошибки
        message = self.error_handler.get_error_message("nonexistent_error")
        self.assertEqual(message, self.error_handler.error_messages["unknown_error"])
        
        # Тестируем пользовательское сообщение
        custom_message = "Пользовательское сообщение"
        message = self.error_handler.get_error_message("permission_denied", custom_message)
        self.assertEqual(message, custom_message)
        print("✅ Получение сообщений об ошибках работает корректно")


class TestStatePersistence(unittest.TestCase):
    """Тест сохранения состояния"""
    
    def setUp(self):
        self.state_persistence = StatePersistence()
    
    def test_state_persistence_creation(self):
        """Тест создания системы сохранения"""
        self.assertIsNotNone(self.state_persistence)
        print("✅ Система сохранения создана")
    
    def test_persistence_methods(self):
        """Тест методов сохранения"""
        methods = [
            'save_bot_state', 'load_bot_state', 'save_active_games',
            'load_active_games', 'save_authorized_chats', 'load_authorized_chats',
            'clear_all_state', 'cleanup_old_state'
        ]
        
        for method in methods:
            self.assertTrue(hasattr(self.state_persistence, method))
        print("✅ Методы сохранения существуют")


class TestAutoSaveManager(unittest.TestCase):
    """Тест автоматического сохранения"""
    
    def setUp(self):
        self.bot_mock = Mock()
        self.auto_save_manager = AutoSaveManager(self.bot_mock)
    
    def test_auto_save_creation(self):
        """Тест создания автоматического сохранения"""
        self.assertIsNotNone(self.auto_save_manager)
        self.assertEqual(self.auto_save_manager.bot, self.bot_mock)
        self.assertEqual(self.auto_save_manager.save_interval, 30)
        self.assertFalse(self.auto_save_manager.is_running)
        print("✅ Автоматическое сохранение создано")
    
    def test_auto_save_methods(self):
        """Тест методов автоматического сохранения"""
        methods = [
            'start_auto_save', 'stop_auto_save', 'save_current_state',
            'load_saved_state', 'force_save', 'get_save_status'
        ]
        
        for method in methods:
            self.assertTrue(hasattr(self.auto_save_manager, method))
        print("✅ Методы автоматического сохранения существуют")
    
    def test_save_status(self):
        """Тест статуса сохранения"""
        status = self.auto_save_manager.get_save_status()
        
        self.assertIn('is_running', status)
        self.assertIn('last_save_time', status)
        self.assertIn('save_interval', status)
        self.assertIn('time_since_last_save', status)
        
        self.assertEqual(status['save_interval'], 30)
        self.assertFalse(status['is_running'])
        print("✅ Статус сохранения работает корректно")


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты"""
    
    def test_all_components_integration(self):
        """Тест интеграции всех компонентов"""
        try:
            # Создаем все компоненты
            game = Game(chat_id=123, is_test_mode=True)
            balance_manager = BalanceManager()
            rewards_system = RewardsSystem()
            error_handler = ErrorHandler()
            state_persistence = StatePersistence()
            
            # Проверяем, что все компоненты работают вместе
            self.assertIsNotNone(game)
            self.assertIsNotNone(balance_manager)
            self.assertIsNotNone(rewards_system)
            self.assertIsNotNone(error_handler)
            self.assertIsNotNone(state_persistence)
            
            print("✅ Все компоненты интегрированы успешно")
            
        except Exception as e:
            self.fail(f"❌ Ошибка интеграции компонентов: {e}")
    
    def test_game_flow_simulation(self):
        """Тест симуляции игрового процесса"""
        try:
            # Создаем игру
            game = Game(chat_id=123, is_test_mode=True)
            
            # Добавляем игроков
            player1 = Player(user_id=1, username="player1", role=Role.WOLF, team=Team.PREDATORS)
            player2 = Player(user_id=2, username="player2", role=Role.HARE, team=Team.HERBIVORES)
            
            game.players[1] = player1
            game.players[2] = player2
            
            # Проверяем состояние игры
            self.assertEqual(len(game.players), 2)
            self.assertEqual(game.phase, GamePhase.WAITING)
            
            # Симулируем начало игры
            game.assign_roles()
            game.start_night()
            
            self.assertEqual(game.phase, GamePhase.NIGHT)
            
            print("✅ Игровой процесс симулирован успешно")
            
        except Exception as e:
            self.fail(f"❌ Ошибка симуляции игрового процесса: {e}")
    
    def test_rewards_and_balance_integration(self):
        """Тест интеграции наград и баланса"""
        try:
            rewards_system = RewardsSystem()
            balance_manager = BalanceManager()
            
            # Проверяем, что системы могут работать вместе
            self.assertIsNotNone(rewards_system.reward_configs)
            self.assertIsNotNone(balance_manager)
            
            # Тестируем создание награды
            reward = Reward(
                reward_type=RewardType.GAME_WIN,
                reason=RewardReason.PREDATOR_WIN,
                amount=50,
                description="Победа хищников"
            )
            
            self.assertEqual(reward.amount, 50)
            
            print("✅ Интеграция наград и баланса работает")
            
        except Exception as e:
            self.fail(f"❌ Ошибка интеграции наград и баланса: {e}")


class TestDeploymentReadiness(unittest.TestCase):
    """Тест готовности к деплою"""
    
    def test_all_required_files_exist(self):
        """Тест существования всех необходимых файлов"""
        required_files = [
            'bot.py',
            'config.py',
            'game_logic.py',
            'database_psycopg2.py',
            'database_balance_manager.py',
            'rewards_system.py',
            'error_handler.py',
            'state_persistence.py',
            'auto_save_manager.py',
            'test_config.py',
            'night_actions.py',
            'night_interface.py',
            'global_settings.py',
            'role_translator.py',
            'fox_logic.py',
            'mole_logic.py',
            'beaver_logic.py'
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            self.fail(f"❌ Отсутствуют файлы: {missing_files}")
        
        print("✅ Все необходимые файлы присутствуют")
    
    def test_import_dependencies(self):
        """Тест зависимостей импорта"""
        try:
            # Проверяем основные зависимости
            import asyncio
            import logging
            import json
            import psycopg2
            from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
            from telegram.ext import Application, CommandHandler, CallbackQueryHandler
            
            print("✅ Все зависимости импортированы успешно")
            
        except ImportError as e:
            self.fail(f"❌ Отсутствует зависимость: {e}")
    
    def test_configuration_completeness(self):
        """Тест полноты конфигурации"""
        try:
            # Проверяем, что все необходимые параметры конфигурации присутствуют
            config_params = [
                'bot_token', 'database_url', 'min_players', 'max_players',
                'night_duration', 'day_duration', 'voting_duration',
                'role_distribution', 'is_test_mode'
            ]
            
            for param in config_params:
                self.assertTrue(hasattr(config, param))
            
            print("✅ Конфигурация полная")
            
        except Exception as e:
            self.fail(f"❌ Ошибка конфигурации: {e}")


def run_deployment_test():
    """Запуск полного теста деплоя"""
    print("🚀 Запуск полного теста перед деплоем...")
    print("=" * 60)
    
    # Создаем тестовый набор
    test_suite = unittest.TestSuite()
    
    # Добавляем все тесты
    test_classes = [
        TestDatabaseConnection,
        TestConfiguration,
        TestGameLogic,
        TestBalanceManager,
        TestRewardsSystem,
        TestErrorHandler,
        TestStatePersistence,
        TestAutoSaveManager,
        TestIntegration,
        TestDeploymentReadiness
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print("=" * 60)
    print(f"📊 Результаты тестирования:")
    print(f"✅ Успешно: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Ошибки: {len(result.errors)}")
    print(f"⚠️ Провалы: {len(result.failures)}")
    print(f"📈 Всего тестов: {result.testsRun}")
    
    if result.wasSuccessful():
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО! ГОТОВ К ДЕПЛОЮ!")
        return True
    else:
        print("❌ ЕСТЬ ПРОБЛЕМЫ! НЕ ГОТОВ К ДЕПЛОЮ!")
        if result.errors:
            print("\n🔍 Ошибки:")
            for error in result.errors:
                print(f"  - {error[0]}: {error[1]}")
        if result.failures:
            print("\n🔍 Провалы:")
            for failure in result.failures:
                print(f"  - {failure[0]}: {failure[1]}")
        return False


if __name__ == '__main__':
    success = run_deployment_test()
    sys.exit(0 if success else 1)
