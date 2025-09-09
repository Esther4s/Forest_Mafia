#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Главный файл для запуска всех комплексных тестов системы ForestMafia
Запускает все тесты как сеньор разработчик
"""

import asyncio
import logging
import sys
import os
import time
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импорты тестовых модулей
from comprehensive_system_test import ComprehensiveSystemTest
from test_buttons_and_callbacks import ButtonsAndCallbacksTest
from test_night_actions_comprehensive import NightActionsComprehensiveTest
from test_database_comprehensive import DatabaseComprehensiveTest
from test_commands_comprehensive import CommandsComprehensiveTest

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_test_results.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MasterTestRunner:
    """Главный класс для запуска всех тестов"""
    
    def __init__(self):
        self.test_suites = []
        self.results = {}
        self.start_time = None
        self.end_time = None
        
    def add_test_suite(self, test_suite_class, name, description):
        """Добавляет тестовый набор"""
        self.test_suites.append({
            'class': test_suite_class,
            'name': name,
            'description': description
        })
    
    def run_all_tests(self):
        """Запускает все тестовые наборы"""
        logger.info("🚀 ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ СИСТЕМЫ FORESTMAFIA")
        logger.info("=" * 80)
        logger.info(f"📅 Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"👨‍💻 Тестирование как сеньор разработчик")
        logger.info("=" * 80)
        
        self.start_time = time.time()
        
        total_passed = 0
        total_failed = 0
        
        for i, test_suite in enumerate(self.test_suites, 1):
            logger.info(f"\n📋 ТЕСТОВЫЙ НАБОР {i}/{len(self.test_suites)}: {test_suite['name']}")
            logger.info(f"📝 Описание: {test_suite['description']}")
            logger.info("-" * 60)
            
            try:
                # Создаем экземпляр тестового набора
                suite_instance = test_suite['class']()
                suite_instance.setUp()
                
                # Запускаем тесты
                suite_start_time = time.time()
                success = suite_instance.run_all_tests()
                suite_end_time = time.time()
                suite_duration = suite_end_time - suite_start_time
                
                # Сохраняем результаты
                self.results[test_suite['name']] = {
                    'success': success,
                    'duration': suite_duration,
                    'passed': getattr(suite_instance, 'passed_tests', 0),
                    'failed': getattr(suite_instance, 'failed_tests', 0)
                }
                
                if success:
                    total_passed += 1
                    logger.info(f"✅ {test_suite['name']} - ПРОЙДЕН ({suite_duration:.2f}с)")
                else:
                    total_failed += 1
                    logger.error(f"❌ {test_suite['name']} - ПРОВАЛЕН ({suite_duration:.2f}с)")
                
                suite_instance.tearDown()
                
            except Exception as e:
                total_failed += 1
                logger.error(f"💥 {test_suite['name']} - КРИТИЧЕСКАЯ ОШИБКА: {e}")
                self.results[test_suite['name']] = {
                    'success': False,
                    'duration': 0,
                    'passed': 0,
                    'failed': 1,
                    'error': str(e)
                }
        
        self.end_time = time.time()
        total_duration = self.end_time - self.start_time
        
        # Выводим финальные результаты
        self.print_final_results(total_passed, total_failed, total_duration)
        
        return total_failed == 0
    
    def print_final_results(self, total_passed, total_failed, total_duration):
        """Выводит финальные результаты тестирования"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 ФИНАЛЬНЫЕ РЕЗУЛЬТАТЫ КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ")
        logger.info("=" * 80)
        
        # Общая статистика
        total_suites = total_passed + total_failed
        success_rate = (total_passed / total_suites * 100) if total_suites > 0 else 0
        
        logger.info(f"📈 Общая статистика:")
        logger.info(f"   • Всего тестовых наборов: {total_suites}")
        logger.info(f"   • Пройдено: {total_passed}")
        logger.info(f"   • Провалено: {total_failed}")
        logger.info(f"   • Успешность: {success_rate:.1f}%")
        logger.info(f"   • Общее время: {total_duration:.2f} секунд")
        
        # Детальная статистика по наборам
        logger.info(f"\n📋 Детальные результаты:")
        for suite_name, result in self.results.items():
            status = "✅ ПРОЙДЕН" if result['success'] else "❌ ПРОВАЛЕН"
            duration = result['duration']
            passed = result.get('passed', 0)
            failed = result.get('failed', 0)
            
            logger.info(f"   • {suite_name}: {status} ({duration:.2f}с)")
            if passed > 0 or failed > 0:
                logger.info(f"     - Пройдено тестов: {passed}")
                logger.info(f"     - Провалено тестов: {failed}")
            
            if 'error' in result:
                logger.info(f"     - Ошибка: {result['error']}")
        
        # Рекомендации
        logger.info(f"\n💡 Рекомендации:")
        if total_failed == 0:
            logger.info("   🎉 Все тесты пройдены успешно! Система готова к продакшену.")
        else:
            logger.info("   ⚠️ Обнаружены проблемы, требующие внимания:")
            for suite_name, result in self.results.items():
                if not result['success']:
                    logger.info(f"     - {suite_name}: требует исправления")
        
        # Время выполнения
        logger.info(f"\n⏱️ Время выполнения:")
        logger.info(f"   • Начало: {datetime.fromtimestamp(self.start_time).strftime('%H:%M:%S')}")
        logger.info(f"   • Конец: {datetime.fromtimestamp(self.end_time).strftime('%H:%M:%S')}")
        logger.info(f"   • Длительность: {total_duration:.2f} секунд")
        
        # Заключение
        if total_failed == 0:
            logger.info(f"\n🏆 ЗАКЛЮЧЕНИЕ: СИСТЕМА ПОЛНОСТЬЮ ПРОТЕСТИРОВАНА И ГОТОВА К РАБОТЕ!")
        else:
            logger.info(f"\n⚠️ ЗАКЛЮЧЕНИЕ: ОБНАРУЖЕНЫ ПРОБЛЕМЫ, ТРЕБУЮЩИЕ ИСПРАВЛЕНИЯ")
        
        logger.info("=" * 80)


def main():
    """Главная функция"""
    print("🌲 ForestMafia Bot - Комплексное тестирование системы 🌲")
    print("=" * 80)
    print("👨‍💻 Тестирование как сеньор разработчик")
    print("=" * 80)
    
    # Создаем главный тестовый раннер
    master_runner = MasterTestRunner()
    
    # Добавляем все тестовые наборы
    master_runner.add_test_suite(
        ComprehensiveSystemTest,
        "Основная система",
        "Тестирование основной игровой логики, команд, фаз и механик"
    )
    
    master_runner.add_test_suite(
        ButtonsAndCallbacksTest,
        "Кнопки и Callbacks",
        "Тестирование всех кнопок, callback handlers и интерфейсов"
    )
    
    master_runner.add_test_suite(
        NightActionsComprehensiveTest,
        "Ночные действия",
        "Тестирование ночных действий, ролей и фаз игры"
    )
    
    master_runner.add_test_suite(
        DatabaseComprehensiveTest,
        "База данных",
        "Тестирование всех операций с базой данных, миграций и персистентности"
    )
    
    master_runner.add_test_suite(
        CommandsComprehensiveTest,
        "Команды бота",
        "Тестирование всех команд бота и их обработчиков"
    )
    
    # Запускаем все тесты
    try:
        success = master_runner.run_all_tests()
        
        # Сохраняем результаты в файл
        with open('test_summary.txt', 'w', encoding='utf-8') as f:
            f.write(f"ForestMafia Bot - Результаты комплексного тестирования\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Результат: {'УСПЕШНО' if success else 'ОБНАРУЖЕНЫ ПРОБЛЕМЫ'}\n")
            f.write(f"Время выполнения: {master_runner.end_time - master_runner.start_time:.2f} секунд\n\n")
            
            for suite_name, result in master_runner.results.items():
                status = "ПРОЙДЕН" if result['success'] else "ПРОВАЛЕН"
                f.write(f"{suite_name}: {status} ({result['duration']:.2f}с)\n")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Тестирование прервано пользователем")
        return 1
    except Exception as e:
        logger.error(f"\n💥 Критическая ошибка при тестировании: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
