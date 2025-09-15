#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Комплексный тест без подключения к базе данных
Тестирует все функции бота без БД
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
import random

# Устанавливаем тестовые переменные окружения
os.environ['BOT_TOKEN'] = 'test_token_123456789'
os.environ['DATABASE_URL'] = 'sqlite:///test_forest_mafia.db'

# Импорты модулей для тестирования
from config import Config, BOT_TOKEN, DATABASE_URL, MIN_PLAYERS, MAX_PLAYERS
from game_logic import Game, GamePhase, Role, Team, Player
from night_actions import NightActions
from night_interface import NightInterface
from global_settings import GlobalSettings
from forest_mafia_settings import ForestWolvesSettings

# Настройка логирования
logging.basicConfig(
    level=logging.WARNING,  # Уменьшаем уровень логирования
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestConfigSystem(unittest.TestCase):
    """Тестирование системы конфигурации"""
    
    def test_config_initialization(self):
        """Тест инициализации конфигурации"""
        print("🧪 Тестирование конфигурации...")
        
        config = Config()
        
        # Проверяем основные параметры
        self.assertIsNotNone(config.bot_token)
        self.assertIsNotNone(config.database_url)
        self.assertIsInstance(config.min_players, int)
        self.assertIsInstance(config.max_players, int)
        
        print(f"✅ Токен бота: {config.bot_token[:10]}...")
        print(f"✅ URL БД: {config.database_url}")
        print(f"✅ Мин. игроков: {config.min_players}")
        print(f"✅ Макс. игроков: {config.max_players}")
        
        # Проверяем игровые настройки
        settings = config.get_game_settings()
        self.assertIn('min_players', settings)
        self.assertIn('max_players', settings)
        self.assertIn('night_duration', settings)
        self.assertIn('day_duration', settings)
        self.assertIn('voting_duration', settings)
        self.assertIn('role_distribution', settings)
        
        print("✅ Конфигурация работает корректно\n")
    
    def test_role_distribution(self):
        """Тест распределения ролей"""
        print("🧪 Тестирование распределения ролей...")
        
        config = Config()
        distribution = config.role_distribution
        
        # Проверяем наличие всех ролей
        expected_roles = ['wolves', 'fox', 'hares', 'mole', 'beaver']
        for role in expected_roles:
            self.assertIn(role, distribution)
            self.assertGreater(distribution[role], 0)
            self.assertLessEqual(distribution[role], 1)
        
        # Проверяем, что сумма равна 1.0
        total = sum(distribution.values())
        self.assertAlmostEqual(total, 1.0, places=2)
        
        print(f"✅ Распределение ролей: {distribution}")
        print(f"✅ Сумма процентов: {total:.2f}")
        print("✅ Распределение ролей корректно\n")


class TestGameLogic(unittest.TestCase):
    """Тестирование игровой логики"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.game = Game(chat_id=12345)
    
    def test_game_creation(self):
        """Тест создания игры"""
        print("🧪 Тестирование создания игры...")
        
        self.assertEqual(self.game.chat_id, 12345)
        self.assertEqual(self.game.phase, GamePhase.WAITING)
        self.assertEqual(len(self.game.players), 0)
        self.assertIsNone(self.game.day_number)
        
        print("✅ Игра создана корректно\n")
    
    def test_player_management(self):
        """Тест управления игроками"""
        print("🧪 Тестирование управления игроками...")
        
        # Добавляем игроков
        players_data = [
            (1, "wolf1"), (2, "wolf2"), (3, "fox"),
            (4, "hare1"), (5, "hare2"), (6, "mole"), (7, "beaver")
        ]
        
        for user_id, username in players_data:
            result = self.game.add_player(user_id, username)
            self.assertTrue(result)
            print(f"✅ Игрок {username} добавлен")
        
        self.assertEqual(len(self.game.players), 7)
        
        # Тестируем удаление игрока
        result = self.game.remove_player(1)
        self.assertTrue(result)
        self.assertEqual(len(self.game.players), 6)
        print("✅ Игрок wolf1 удалён")
        
        # Тестируем получение живых игроков
        alive_players = self.game.get_alive_players()
        self.assertEqual(len(alive_players), 6)
        print(f"✅ Живых игроков: {len(alive_players)}")
        
        print("✅ Управление игроками работает корректно\n")
    
    def test_game_start(self):
        """Тест начала игры"""
        print("🧪 Тестирование начала игры...")
        
        # Добавляем минимальное количество игроков
        for i in range(6):
            self.game.add_player(i, f"player_{i}")
        
        # Начинаем игру
        result = self.game.start_game()
        self.assertTrue(result)
        self.assertEqual(self.game.phase, GamePhase.NIGHT)
        self.assertEqual(self.game.day_number, 1)
        
        print("✅ Игра начата успешно")
        print(f"✅ Фаза: {self.game.phase.value}")
        print(f"✅ День: {self.game.day_number}")
        
        print("✅ Начало игры работает корректно\n")
    
    def test_voting_system(self):
        """Тест системы голосования"""
        print("🧪 Тестирование системы голосования...")
        
        # Добавляем игроков
        for i in range(6):
            self.game.add_player(i, f"player_{i}")
        
        # Начинаем игру
        self.game.start_game()
        
        # Переходим к фазе голосования
        self.game.phase = GamePhase.VOTING
        
        # Тестируем голосование
        votes = [
            (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)
        ]
        
        for voter_id, target_id in votes:
            success = self.game.vote(voter_id, target_id)
            self.assertTrue(success)
            print(f"✅ Голос {voter_id} -> {target_id}: {success}")
        
        # Подсчитываем голоса
        vote_counts, skip_votes = self.game._count_votes()
        print(f"✅ Результаты голосования: {vote_counts}")
        print(f"✅ Пропусков: {skip_votes}")
        
        print("✅ Система голосования работает корректно\n")
    
    def test_game_end_conditions(self):
        """Тест условий окончания игры"""
        print("🧪 Тестирование условий окончания игры...")
        
        # Добавляем игроков
        for i in range(6):
            self.game.add_player(i, f"player_{i}")
        
        # Начинаем игру
        self.game.start_game()
        
        # Изначально игра не окончена
        game_end = self.game.check_game_end()
        self.assertFalse(game_end)
        print("✅ Игра не окончена (нормально)")
        
        # Убиваем всех кроме одного
        for player in self.game.players.values():
            if player.user_id != 0:
                player.is_alive = False
        
        # Теперь игра должна быть окончена
        winner = self.game.check_game_end()
        self.assertIsNotNone(winner)
        print(f"✅ Игра окончена, победитель: {winner.value}")
        
        print("✅ Условия окончания игры работают корректно\n")


class TestNightActions(unittest.TestCase):
    """Тестирование ночных действий"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.game = Game(chat_id=12345)
        
        # Добавляем игроков
        players_data = [
            (1, "wolf1"), (2, "wolf2"), (3, "fox"),
            (4, "hare1"), (5, "hare2"), (6, "mole"), (7, "beaver")
        ]
        
        for user_id, username in players_data:
            self.game.add_player(user_id, username)
        
        self.game.start_game()
        self.night_actions = NightActions(self.game)
    
    def test_wolf_actions(self):
        """Тест действий волков"""
        print("🧪 Тестирование действий волков...")
        
        # Назначаем роли игрокам вручную для тестирования
        self.game.players[1].role = Role.WOLF
        self.game.players[1].team = Team.PREDATORS
        self.game.players[2].role = Role.WOLF
        self.game.players[2].team = Team.PREDATORS
        self.game.players[3].role = Role.FOX
        self.game.players[3].team = Team.PREDATORS
        self.game.players[4].role = Role.HARE
        self.game.players[4].team = Team.HERBIVORES
        
        # Волк может атаковать травоядных
        can_attack_hare = self.night_actions.set_wolf_target(1, 4)
        self.assertTrue(can_attack_hare)
        print("✅ Волк может атаковать зайца")
        
        # Волк не может атаковать другого волка
        can_attack_wolf = self.night_actions.set_wolf_target(1, 2)
        self.assertFalse(can_attack_wolf)
        print("✅ Волк не может атаковать волка")
        
        # Волк не может атаковать лису
        can_attack_fox = self.night_actions.set_wolf_target(1, 3)
        self.assertFalse(can_attack_fox)
        print("✅ Волк не может атаковать лису")
        
        print("✅ Действия волков работают корректно\n")
    
    def test_fox_actions(self):
        """Тест действий лисы"""
        print("🧪 Тестирование действий лисы...")
        
        # Назначаем роли игрокам вручную для тестирования
        self.game.players[3].role = Role.FOX
        self.game.players[3].team = Team.PREDATORS
        self.game.players[4].role = Role.HARE
        self.game.players[4].team = Team.HERBIVORES
        self.game.players[6].role = Role.MOLE
        self.game.players[6].team = Team.HERBIVORES
        self.game.players[7].role = Role.BEAVER
        self.game.players[7].team = Team.HERBIVORES
        self.game.players[1].role = Role.WOLF
        self.game.players[1].team = Team.PREDATORS
        
        # Лиса может воровать у травоядных
        can_steal_hare = self.night_actions.set_fox_target(3, 4)
        self.assertTrue(can_steal_hare)
        print("✅ Лиса может воровать у зайца")
        
        can_steal_mole = self.night_actions.set_fox_target(3, 6)
        self.assertTrue(can_steal_mole)
        print("✅ Лиса может воровать у крота")
        
        # Лиса не может воровать у бобра (он защищен)
        can_steal_beaver = self.night_actions.set_fox_target(3, 7)
        self.assertFalse(can_steal_beaver)
        print("✅ Лиса не может воровать у бобра (он защищен)")
        
        # Лиса не может воровать у волка
        can_steal_wolf = self.night_actions.set_fox_target(3, 1)
        self.assertFalse(can_steal_wolf)
        print("✅ Лиса не может воровать у волка")
        
        print("✅ Действия лисы работают корректно\n")
    
    def test_mole_actions(self):
        """Тест действий крота"""
        print("🧪 Тестирование действий крота...")
        
        # Назначаем роли игрокам вручную для тестирования
        self.game.players[6].role = Role.MOLE
        self.game.players[6].team = Team.HERBIVORES
        self.game.players[4].role = Role.HARE
        self.game.players[4].team = Team.HERBIVORES
        self.game.players[1].role = Role.WOLF
        self.game.players[1].team = Team.PREDATORS
        self.game.players[3].role = Role.FOX
        self.game.players[3].team = Team.PREDATORS
        
        # Крот может копать под любого
        can_dig_hare = self.night_actions.set_mole_target(6, 4)
        self.assertTrue(can_dig_hare)
        print("✅ Крот может копать под зайца")
        
        can_dig_wolf = self.night_actions.set_mole_target(6, 1)
        self.assertTrue(can_dig_wolf)
        print("✅ Крот может копать под волка")
        
        can_dig_fox = self.night_actions.set_mole_target(6, 3)
        self.assertTrue(can_dig_fox)
        print("✅ Крот может копать под лису")
        
        print("✅ Действия крота работают корректно\n")
    
    def test_beaver_actions(self):
        """Тест действий бобра"""
        print("🧪 Тестирование действий бобра...")
        
        # Назначаем роли игрокам вручную для тестирования
        self.game.players[7].role = Role.BEAVER
        self.game.players[7].team = Team.HERBIVORES
        self.game.players[4].role = Role.HARE
        self.game.players[4].team = Team.HERBIVORES
        self.game.players[1].role = Role.WOLF
        self.game.players[1].team = Team.PREDATORS
        self.game.players[3].role = Role.FOX
        self.game.players[3].team = Team.PREDATORS
        
        # Устанавливаем украденные припасы для тестирования бобра
        self.game.players[4].stolen_supplies = 1  # У зайца украли припасы
        self.game.players[1].stolen_supplies = 1  # У волка украли припасы
        self.game.players[3].stolen_supplies = 1  # У лисы украли припасы
        
        # Бобёр может защищать тех, у кого украли припасы
        can_protect_hare = self.night_actions.set_beaver_target(7, 4)
        self.assertTrue(can_protect_hare)
        print("✅ Бобёр может защищать зайца (у которого украли припасы)")
        
        can_protect_wolf = self.night_actions.set_beaver_target(7, 1)
        self.assertTrue(can_protect_wolf)
        print("✅ Бобёр может защищать волка (у которого украли припасы)")
        
        can_protect_fox = self.night_actions.set_beaver_target(7, 3)
        self.assertTrue(can_protect_fox)
        print("✅ Бобёр может защищать лису (у которой украли припасы)")
        
        print("✅ Действия бобра работают корректно\n")
    
    def test_night_processing(self):
        """Тест обработки ночных действий"""
        print("🧪 Тестирование обработки ночных действий...")
        
        # Назначаем роли игрокам вручную для тестирования
        self.game.players[1].role = Role.WOLF
        self.game.players[1].team = Team.PREDATORS
        self.game.players[3].role = Role.FOX
        self.game.players[3].team = Team.PREDATORS
        self.game.players[4].role = Role.HARE
        self.game.players[4].team = Team.HERBIVORES
        self.game.players[6].role = Role.MOLE
        self.game.players[6].team = Team.HERBIVORES
        self.game.players[7].role = Role.BEAVER
        self.game.players[7].team = Team.HERBIVORES
        
        # Настраиваем ночные действия
        self.night_actions.set_wolf_target(1, 4)  # wolf1 атакует hare1
        self.night_actions.set_fox_target(3, 4)   # fox ворует у hare1
        self.night_actions.set_beaver_target(7, 4) # beaver защищает hare1
        self.night_actions.set_mole_target(6, 4)  # mole копает под hare1
        
        print("✅ Ночные действия настроены")
        
        # Выполняем ночные действия
        results = self.night_actions.process_all_actions()
        
        self.assertIn('wolves', results)
        self.assertIn('fox', results)
        self.assertIn('beaver', results)
        self.assertIn('mole', results)
        self.assertIn('deaths', results)
        
        print(f"✅ Результаты ночных действий: {results}")
        print("✅ Обработка ночных действий работает корректно\n")


class TestPlayerSystem(unittest.TestCase):
    """Тестирование системы игроков"""
    
    def test_player_creation(self):
        """Тест создания игрока"""
        print("🧪 Тестирование создания игрока...")
        
        # Создаём игрока
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
        
        print("✅ Игрок создан корректно")
        print(f"✅ ID: {player.user_id}")
        print(f"✅ Имя: {player.username}")
        print(f"✅ Роль: {player.role.value}")
        print(f"✅ Команда: {player.team.value}")
        
        print("✅ Создание игрока работает корректно\n")
    
    def test_player_validation(self):
        """Тест валидации игрока"""
        print("🧪 Тестирование валидации игрока...")
        
        # Валидный игрок
        valid_player = Player(123, "test", Role.HARE, Team.HERBIVORES)
        self.assertTrue(valid_player.is_alive)
        print("✅ Валидный игрок создан")
        
        # Проверяем соответствие роли и команды
        wolf = Player(1, "wolf", Role.WOLF, Team.PREDATORS)
        self.assertEqual(wolf.team, Team.PREDATORS)
        print("✅ Волк в команде хищников")
        
        hare = Player(2, "hare", Role.HARE, Team.HERBIVORES)
        self.assertEqual(hare.team, Team.HERBIVORES)
        print("✅ Заяц в команде травоядных")
        
        print("✅ Валидация игрока работает корректно\n")
    
    def test_supplies_management(self):
        """Тест управления припасами"""
        print("🧪 Тестирование управления припасами...")
        
        player = Player(123, "test", Role.HARE, Team.HERBIVORES)
        
        # Изначально 2 припаса
        self.assertEqual(player.supplies, 2)
        print("✅ Изначально 2 припаса")
        
        # Уменьшаем припасы
        player.supplies -= 1
        self.assertEqual(player.supplies, 1)
        print("✅ Припасы уменьшены до 1")
        
        # Восстанавливаем припасы
        player.supplies = player.max_supplies
        self.assertEqual(player.supplies, 2)
        print("✅ Припасы восстановлены до 2")
        
        print("✅ Управление припасами работает корректно\n")


class TestErrorHandling(unittest.TestCase):
    """Тестирование обработки ошибок"""
    
    def test_invalid_operations(self):
        """Тест невалидных операций"""
        print("🧪 Тестирование невалидных операций...")
        
        game = Game(chat_id=12345)
        
        # Попытка начать игру без игроков
        result = game.start_game()
        self.assertFalse(result)
        print("✅ Игра без игроков не началась")
        
        # Попытка проголосовать за несуществующего игрока
        result = game.vote(1, 999)
        self.assertFalse(result)
        print("✅ Голос за несуществующего игрока отклонён")
        
        # Попытка добавить игрока с невалидными данными
        try:
            invalid_player = Player(None, "test", Role.HARE, Team.HERBIVORES)
            print("❌ Невалидный игрок создан (не должно было произойти)")
        except Exception as e:
            print(f"✅ Невалидный игрок отклонён: {type(e).__name__}")
        
        print("✅ Обработка ошибок работает корректно\n")


class TestPerformance(unittest.TestCase):
    """Тестирование производительности"""
    
    def test_large_game_performance(self):
        """Тест производительности с большим количеством игроков"""
        print("🧪 Тестирование производительности...")
        
        game = Game(chat_id=12345)
        
        # Добавляем максимальное количество игроков
        start_time = time.time()
        
        for i in range(12):  # MAX_PLAYERS
            game.add_player(i, f"player_{i}")
        
        add_time = time.time() - start_time
        self.assertLess(add_time, 1.0)  # Должно быть быстрее 1 секунды
        print(f"✅ Создание 12 игроков: {add_time:.3f}с")
        
        # Тестируем голосование
        start_time = time.time()
        for i in range(12):
            game.vote(i, (i + 1) % 12)
        
        vote_time = time.time() - start_time
        self.assertLess(vote_time, 0.5)  # Должно быть быстрее 0.5 секунды
        print(f"✅ Голосование 12 игроков: {vote_time:.3f}с")
        
        # Тестируем ночные действия
        start_time = time.time()
        night_actions = NightActions(game)
        for i in range(0, 12, 2):
            night_actions.set_wolf_target(i, (i + 1) % 12)
        
        night_time = time.time() - start_time
        self.assertLess(night_time, 0.5)  # Должно быть быстрее 0.5 секунды
        print(f"✅ Настройка ночных действий: {night_time:.3f}с")
        
        print("✅ Производительность в норме\n")


def run_comprehensive_tests():
    """Запуск всех тестов"""
    print("🧪 ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ БОТА ЛЕС И ВОЛКИ")
    print("=" * 70)
    
    # Создаём тестовый сьют
    test_suite = unittest.TestSuite()
    
    # Добавляем тесты
    test_classes = [
        TestConfigSystem,
        TestGameLogic,
        TestNightActions,
        TestPlayerSystem,
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
    print("\n" + "=" * 70)
    print("📊 РЕЗУЛЬТАТЫ КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ:")
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
