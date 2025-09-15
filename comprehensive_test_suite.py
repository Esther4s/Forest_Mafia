#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Комплексный тест-сьют для бота Лес и волки
Тестирует все функции: новые и старые
"""

import asyncio
import logging
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import time

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импорты модулей для тестирования
from config import Config, BOT_TOKEN, DATABASE_URL, MIN_PLAYERS, MAX_PLAYERS
from game_logic import Game, GamePhase, Role, Team, Player
from night_actions import NightActions
from night_interface import NightInterface
from global_settings import GlobalSettings
from forest_mafia_settings import ForestWolvesSettings
from database_psycopg2 import DatabaseConnection, init_db, close_db
from bot import ForestWolvesBot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestConfig(unittest.TestCase):
    """Тестирование конфигурации"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.config = Config()
    
    def test_config_initialization(self):
        """Тест инициализации конфигурации"""
        self.assertIsNotNone(self.config)
        self.assertIsInstance(self.config.bot_token, str)
        self.assertIsInstance(self.config.database_url, str)
        self.assertIsInstance(self.config.min_players, int)
        self.assertIsInstance(self.config.max_players, int)
    
    def test_game_settings(self):
        """Тест игровых настроек"""
        settings = self.config.get_game_settings()
        self.assertIn('min_players', settings)
        self.assertIn('max_players', settings)
        self.assertIn('night_duration', settings)
        self.assertIn('day_duration', settings)
        self.assertIn('voting_duration', settings)
        self.assertIn('role_distribution', settings)
        self.assertIn('test_mode', settings)
    
    def test_role_distribution(self):
        """Тест распределения ролей"""
        distribution = self.config.role_distribution
        self.assertIn('wolves', distribution)
        self.assertIn('fox', distribution)
        self.assertIn('hares', distribution)
        self.assertIn('mole', distribution)
        self.assertIn('beaver', distribution)
        
        # Проверяем, что сумма процентов близка к 1.0
        total = sum(distribution.values())
        self.assertAlmostEqual(total, 1.0, places=2)
    
    def test_phase_durations(self):
        """Тест длительности фаз"""
        self.assertGreater(self.config.night_duration, 0)
        self.assertGreater(self.config.day_duration, 0)
        self.assertGreater(self.config.voting_duration, 0)
        
        # Проверяем разумные значения
        self.assertLessEqual(self.config.night_duration, 300)  # не более 5 минут
        self.assertLessEqual(self.config.day_duration, 600)    # не более 10 минут
        self.assertLessEqual(self.config.voting_duration, 300) # не более 5 минут


class TestGameLogic(unittest.TestCase):
    """Тестирование игровой логики"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.game = Game(chat_id=12345)
    
    def test_game_initialization(self):
        """Тест инициализации игры"""
        self.assertEqual(self.game.chat_id, 12345)
        self.assertEqual(self.game.phase, GamePhase.WAITING)
        self.assertEqual(len(self.game.players), 0)
        self.assertIsNone(self.game.day_number)
        self.assertIsNone(self.game.vote_target)
    
    def test_add_player(self):
        """Тест добавления игрока"""
        player = Player(
            user_id=123,
            username="test_user",
            role=Role.HARE,
            team=Team.HERBIVORES
        )
        
        result = self.game.add_player(player)
        self.assertTrue(result)
        self.assertIn(123, self.game.players)
        self.assertEqual(self.game.players[123].username, "test_user")
    
    def test_remove_player(self):
        """Тест удаления игрока"""
        player = Player(
            user_id=123,
            username="test_user",
            role=Role.HARE,
            team=Team.HERBIVORES
        )
        self.game.add_player(player)
        
        result = self.game.remove_player(123)
        self.assertTrue(result)
        self.assertNotIn(123, self.game.players)
    
    def test_start_game(self):
        """Тест начала игры"""
        # Добавляем минимальное количество игроков
        for i in range(6):
            player = Player(
                user_id=i,
                username=f"player_{i}",
                role=Role.HARE,
                team=Team.HERBIVORES
            )
            self.game.add_player(player)
        
        result = self.game.start_game()
        self.assertTrue(result)
        self.assertEqual(self.game.phase, GamePhase.NIGHT)
        self.assertEqual(self.game.day_number, 1)
    
    def test_vote(self):
        """Тест голосования"""
        # Добавляем игроков
        voter = Player(1, "voter", Role.HARE, Team.HERBIVORES)
        target = Player(2, "target", Role.HARE, Team.HERBIVORES)
        
        self.game.add_player(voter)
        self.game.add_player(target)
        
        result = self.game.vote(1, 2)
        self.assertTrue(result)
        self.assertEqual(self.game.votes[1], 2)
    
    def test_get_vote_results(self):
        """Тест получения результатов голосования"""
        # Добавляем игроков
        for i in range(3):
            player = Player(i, f"player_{i}", Role.HARE, Team.HERBIVORES)
            self.game.add_player(player)
        
        # Голосуем за игрока 0
        self.game.vote(1, 0)
        self.game.vote(2, 0)
        
        results = self.game.get_vote_results()
        self.assertEqual(results[0], 2)  # 2 голоса за игрока 0
        self.assertEqual(results[1], 0)  # 0 голосов за игрока 1
        self.assertEqual(results[2], 0)  # 0 голосов за игрока 2
    
    def test_check_game_end(self):
        """Тест проверки окончания игры"""
        # Игра не начата
        self.assertFalse(self.game.check_game_end())
        
        # Добавляем игроков и начинаем игру
        for i in range(6):
            player = Player(i, f"player_{i}", Role.HARE, Team.HERBIVORES)
            self.game.add_player(player)
        
        self.game.start_game()
        
        # Убиваем всех игроков кроме одного
        for i in range(1, 6):
            self.game.players[i].is_alive = False
        
        result = self.game.check_game_end()
        self.assertTrue(result)
        self.assertEqual(self.game.phase, GamePhase.GAME_OVER)


class TestPlayer(unittest.TestCase):
    """Тестирование класса Player"""
    
    def test_player_initialization(self):
        """Тест инициализации игрока"""
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
        self.assertEqual(player.supplies, 2)
        self.assertEqual(player.max_supplies, 2)
        self.assertEqual(player.is_fox_stolen, 0)
        self.assertEqual(player.stolen_supplies, 0)
        self.assertFalse(player.is_beaver_protected)
        self.assertEqual(player.consecutive_nights_survived, 0)
        self.assertEqual(player.last_action_round, 0)
    
    def test_player_validation(self):
        """Тест валидации игрока"""
        # Валидный игрок
        player = Player(123, "test", Role.HARE, Team.HERBIVORES)
        self.assertTrue(player.is_alive)
        
        # Проверяем, что роль соответствует команде
        wolf = Player(1, "wolf", Role.WOLF, Team.PREDATORS)
        self.assertEqual(wolf.team, Team.PREDATORS)
        
        hare = Player(2, "hare", Role.HARE, Team.HERBIVORES)
        self.assertEqual(hare.team, Team.HERBIVORES)
    
    def test_supplies_management(self):
        """Тест управления припасами"""
        player = Player(123, "test", Role.HARE, Team.HERBIVORES)
        
        # Изначально 2 припаса
        self.assertEqual(player.supplies, 2)
        
        # Уменьшаем припасы
        player.supplies -= 1
        self.assertEqual(player.supplies, 1)
        
        # Восстанавливаем припасы
        player.supplies = player.max_supplies
        self.assertEqual(player.supplies, 2)


class TestNightActions(unittest.TestCase):
    """Тестирование ночных действий"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.game = Game(chat_id=12345)
        self.night_actions = NightActions(self.game)
        
        # Добавляем игроков
        self.wolf = Player(1, "wolf", Role.WOLF, Team.PREDATORS)
        self.fox = Player(2, "fox", Role.FOX, Team.PREDATORS)
        self.hare = Player(3, "hare", Role.HARE, Team.HERBIVORES)
        self.mole = Player(4, "mole", Role.MOLE, Team.HERBIVORES)
        self.beaver = Player(5, "beaver", Role.BEAVER, Team.HERBIVORES)
        
        self.game.add_player(self.wolf)
        self.game.add_player(self.fox)
        self.game.add_player(self.hare)
        self.game.add_player(self.mole)
        self.game.add_player(self.beaver)
    
    def test_wolf_target_setting(self):
        """Тест установки цели для волка"""
        # Волк может атаковать зайца
        result = self.night_actions.set_wolf_target(1, 3)
        self.assertTrue(result)
        self.assertEqual(self.night_actions.wolf_targets[1], 3)
        
        # Волк не может атаковать другого волка
        wolf2 = Player(6, "wolf2", Role.WOLF, Team.PREDATORS)
        self.game.add_player(wolf2)
        result = self.night_actions.set_wolf_target(1, 6)
        self.assertFalse(result)
        
        # Волк не может атаковать лису
        result = self.night_actions.set_wolf_target(1, 2)
        self.assertFalse(result)
    
    def test_fox_target_setting(self):
        """Тест установки цели для лисы"""
        # Лиса может воровать у зайца
        result = self.night_actions.set_fox_target(2, 3)
        self.assertTrue(result)
        self.assertEqual(self.night_actions.fox_targets[2], 3)
        
        # Лиса не может воровать у волка
        result = self.night_actions.set_fox_target(2, 1)
        self.assertFalse(result)
    
    def test_mole_target_setting(self):
        """Тест установки цели для крота"""
        # Крот может копать под зайца
        result = self.night_actions.set_mole_target(4, 3)
        self.assertTrue(result)
        self.assertEqual(self.night_actions.mole_targets[4], 3)
    
    def test_beaver_target_setting(self):
        """Тест установки цели для бобра"""
        # Бобёр может защищать зайца
        result = self.night_actions.set_beaver_target(5, 3)
        self.assertTrue(result)
        self.assertEqual(self.night_actions.beaver_targets[5], 3)
    
    def test_skip_action(self):
        """Тест пропуска действия"""
        self.night_actions.skip_action(1)
        self.assertIn(1, self.night_actions.skipped_actions)
    
    def test_execute_night_actions(self):
        """Тест выполнения ночных действий"""
        # Настраиваем действия
        self.night_actions.set_wolf_target(1, 3)  # Волк атакует зайца
        self.night_actions.set_fox_target(2, 3)   # Лиса ворует у зайца
        self.night_actions.set_beaver_target(5, 3) # Бобёр защищает зайца
        
        # Выполняем действия
        results = self.night_actions.execute_night_actions()
        
        # Проверяем результаты
        self.assertIn('kills', results)
        self.assertIn('thefts', results)
        self.assertIn('protections', results)
        
        # Заяц должен быть защищён бобром от волка
        self.assertEqual(len(results['kills']), 0)
        self.assertEqual(len(results['thefts']), 1)
        self.assertEqual(len(results['protections']), 1)


class TestDatabaseConnection(unittest.TestCase):
    """Тестирование подключения к базе данных"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        # Используем тестовую базу данных
        self.test_db_url = "sqlite:///test_forest_mafia.db"
    
    @patch('database_psycopg2.DatabaseConnection')
    def test_database_initialization(self, mock_db):
        """Тест инициализации базы данных"""
        mock_instance = Mock()
        mock_db.return_value = mock_instance
        
        # Тестируем инициализацию
        db = DatabaseConnection(self.test_db_url)
        self.assertIsNotNone(db)
    
    def test_database_url_parsing(self):
        """Тест парсинга URL базы данных"""
        # Тестируем с SQLite URL
        db = DatabaseConnection("sqlite:///test.db")
        self.assertIsNotNone(db.database_url)
        
        # Тестируем с PostgreSQL URL
        postgres_url = "postgresql://user:pass@localhost:5432/db"
        db = DatabaseConnection(postgres_url)
        self.assertEqual(db.database_url, postgres_url)


class TestBotIntegration(unittest.TestCase):
    """Интеграционное тестирование бота"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        # Мокаем токен бота для тестирования
        with patch.dict(os.environ, {'BOT_TOKEN': 'test_token_123'}):
            self.bot = ForestWolvesBot()
    
    def test_bot_initialization(self):
        """Тест инициализации бота"""
        self.assertIsNotNone(self.bot)
        self.assertIsInstance(self.bot.games, dict)
        self.assertIsInstance(self.bot.player_games, dict)
        self.assertIsInstance(self.bot.night_actions, dict)
        self.assertIsInstance(self.bot.night_interfaces, dict)
        self.assertIsNotNone(self.bot.global_settings)
    
    def test_authorized_chats_management(self):
        """Тест управления авторизованными чатами"""
        chat_id = 12345
        thread_id = 67890
        
        # Добавляем чат
        self.bot.add_authorized_chat(chat_id, thread_id)
        self.assertIn((chat_id, thread_id), self.bot.authorized_chats)
        
        # Проверяем авторизацию
        self.assertTrue(self.bot.is_authorized(chat_id, thread_id))
        
        # Удаляем чат
        self.bot.remove_authorized_chat(chat_id, thread_id)
        self.assertNotIn((chat_id, thread_id), self.bot.authorized_chats)
        self.assertFalse(self.bot.is_authorized(chat_id, thread_id))
    
    def test_game_creation(self):
        """Тест создания игры"""
        chat_id = 12345
        thread_id = 67890
        
        # Создаём игру
        game = self.bot.create_game(chat_id, thread_id)
        self.assertIsNotNone(game)
        self.assertEqual(game.chat_id, chat_id)
        self.assertIn(chat_id, self.bot.games)
    
    def test_player_registration(self):
        """Тест регистрации игрока"""
        chat_id = 12345
        thread_id = 67890
        user_id = 123
        username = "test_user"
        
        # Создаём игру
        self.bot.create_game(chat_id, thread_id)
        
        # Регистрируем игрока
        result = self.bot.register_player(chat_id, user_id, username)
        self.assertTrue(result)
        
        # Проверяем, что игрок добавлен
        game = self.bot.games[chat_id]
        self.assertIn(user_id, game.players)
        self.assertEqual(game.players[user_id].username, username)


class TestErrorHandling(unittest.TestCase):
    """Тестирование обработки ошибок"""
    
    def test_invalid_player_creation(self):
        """Тест создания невалидного игрока"""
        with self.assertRaises(ValueError):
            Player(
                user_id=None,  # Невалидный user_id
                username="test",
                role=Role.HARE,
                team=Team.HERBIVORES
            )
    
    def test_invalid_game_operations(self):
        """Тест невалидных операций с игрой"""
        game = Game(chat_id=12345)
        
        # Попытка начать игру без игроков
        result = game.start_game()
        self.assertFalse(result)
        
        # Попытка проголосовать в несуществующего игрока
        result = game.vote(1, 999)
        self.assertFalse(result)
    
    def test_database_connection_error(self):
        """Тест ошибки подключения к базе данных"""
        with patch('database_psycopg2.init_db', side_effect=Exception("Connection failed")):
            with self.assertLogs(level='ERROR') as log:
                bot = ForestWolvesBot()
                self.assertIn("Ошибка инициализации базы данных", log.output[0])


class TestPerformance(unittest.TestCase):
    """Тестирование производительности"""
    
    def test_large_game_performance(self):
        """Тест производительности с большим количеством игроков"""
        game = Game(chat_id=12345)
        
        # Добавляем максимальное количество игроков
        start_time = time.time()
        
        for i in range(12):  # MAX_PLAYERS
            player = Player(
                user_id=i,
                username=f"player_{i}",
                role=Role.HARE,
                team=Team.HERBIVORES
            )
            game.add_player(player)
        
        add_time = time.time() - start_time
        self.assertLess(add_time, 1.0)  # Должно быть быстрее 1 секунды
        
        # Тестируем голосование
        start_time = time.time()
        for i in range(12):
            game.vote(i, (i + 1) % 12)
        
        vote_time = time.time() - start_time
        self.assertLess(vote_time, 0.5)  # Должно быть быстрее 0.5 секунды
    
    def test_memory_usage(self):
        """Тест использования памяти"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Создаём много игр
        games = []
        for i in range(100):
            game = Game(chat_id=i)
            for j in range(6):
                player = Player(
                    user_id=j,
                    username=f"player_{j}",
                    role=Role.HARE,
                    team=Team.HERBIVORES
                )
                game.add_player(player)
            games.append(game)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Увеличение памяти не должно быть критическим
        self.assertLess(memory_increase, 50 * 1024 * 1024)  # Менее 50MB


def run_comprehensive_tests():
    """Запуск всех тестов"""
    print("🧪 Запуск комплексного тестирования бота Лес и волки...")
    print("=" * 60)
    
    # Создаём тестовый сьют
    test_suite = unittest.TestSuite()
    
    # Добавляем тесты
    test_classes = [
        TestConfig,
        TestGameLogic,
        TestPlayer,
        TestNightActions,
        TestDatabaseConnection,
        TestBotIntegration,
        TestErrorHandling,
        TestPerformance
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )
    
    result = runner.run(test_suite)
    
    # Выводим результаты
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"✅ Успешных тестов: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Неудачных тестов: {len(result.failures)}")
    print(f"💥 Ошибок: {len(result.errors)}")
    print(f"📈 Всего тестов: {result.testsRun}")
    
    if result.failures:
        print("\n❌ НЕУДАЧНЫЕ ТЕСТЫ:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n💥 ОШИБКИ:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
    print(f"\n🎯 Процент успешности: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 Отличные результаты! Система работает стабильно.")
    elif success_rate >= 70:
        print("⚠️  Хорошие результаты, но есть области для улучшения.")
    else:
        print("🚨 Критические проблемы! Требуется срочное исправление.")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
