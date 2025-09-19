#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный скрипт для запуска полного тестирования системы перед деплоем
"""

import os
import sys
import subprocess
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple


class FullTestRunner:
    """Главный класс для запуска всех тестов"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now()
        
    def log_section(self, title: str):
        """Логирует раздел тестов"""
        print("\n" + "=" * 80)
        print(f"🧪 {title}")
        print("=" * 80)
    
    def run_script(self, script_name: str, description: str) -> Tuple[bool, str]:
        """Запускает тестовый скрипт"""
        print(f"\n🚀 Запуск: {description}")
        print(f"📄 Скрипт: {script_name}")
        print("-" * 60)
        
        try:
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                timeout=300  # 5 минут таймаут
            )
            
            # Выводим результат
            if result.stdout:
                print("📤 Вывод:")
                print(result.stdout)
            
            if result.stderr:
                print("⚠️ Ошибки:")
                print(result.stderr)
            
            success = result.returncode == 0
            message = "Успешно" if success else f"Ошибка (код: {result.returncode})"
            
            print(f"\n{'✅' if success else '❌'} Результат: {message}")
            return success, message
            
        except subprocess.TimeoutExpired:
            print("⏰ Таймаут выполнения (5 минут)")
            return False, "Таймаут"
        except FileNotFoundError:
            print(f"❌ Файл {script_name} не найден")
            return False, "Файл не найден"
        except Exception as e:
            print(f"❌ Ошибка выполнения: {e}")
            return False, f"Ошибка: {e}"
    
    def check_environment(self) -> bool:
        """Проверяет окружение"""
        print("\n🔍 Проверка окружения...")
        
        # Проверяем Python версию
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            print(f"❌ Требуется Python 3.8+, текущая версия: {python_version.major}.{python_version.minor}")
            return False
        print(f"✅ Python версия: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # Проверяем наличие необходимых файлов
        required_files = [
            'bot.py',
            'config.py',
            'game_logic.py',
            'database.py',
            'requirements.txt',
            'Dockerfile',
            'docker-compose.yml'
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            print(f"❌ Отсутствуют файлы: {', '.join(missing_files)}")
            return False
        
        print("✅ Все необходимые файлы присутствуют")
        
        # Проверяем Docker
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Docker: {result.stdout.strip()}")
            else:
                print("⚠️ Docker не установлен или не работает")
        except FileNotFoundError:
            print("⚠️ Docker не найден в PATH")
        
        # Проверяем Docker Compose
        try:
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Docker Compose: {result.stdout.strip()}")
            else:
                print("⚠️ Docker Compose не установлен или не работает")
        except FileNotFoundError:
            print("⚠️ Docker Compose не найден в PATH")
        
        return True
    
    def run_basic_tests(self) -> bool:
        """Запускает базовые тесты"""
        self.log_section("БАЗОВЫЕ ТЕСТЫ")
        
        # Тест 1: Существующий тест
        if os.path.exists('test_all.py'):
            success, message = self.run_script('test_all.py', 'Базовое тестирование системы')
            self.test_results['basic_tests'] = {'success': success, 'message': message}
            if not success:
                return False
        else:
            print("⚠️ Файл test_all.py не найден, пропускаем базовые тесты")
            self.test_results['basic_tests'] = {'success': True, 'message': 'Пропущено'}
        
        return True
    
    def run_database_tests(self) -> bool:
        """Запускает тесты базы данных"""
        self.log_section("ТЕСТЫ БАЗЫ ДАННЫХ")
        
        success, message = self.run_script('database_test.py', 'Тестирование базы данных')
        self.test_results['database_tests'] = {'success': success, 'message': message}
        return success
    
    def run_docker_tests(self) -> bool:
        """Запускает тесты Docker"""
        self.log_section("ТЕСТЫ DOCKER")
        
        success, message = self.run_script('docker_test.py', 'Тестирование Docker')
        self.test_results['docker_tests'] = {'success': success, 'message': message}
        return success
    
    def run_comprehensive_tests(self) -> bool:
        """Запускает комплексные тесты"""
        self.log_section("КОМПЛЕКСНЫЕ ТЕСТЫ")
        
        success, message = self.run_script('comprehensive_test_suite.py', 'Комплексное тестирование')
        self.test_results['comprehensive_tests'] = {'success': success, 'message': message}
        return success
    
    def run_integration_tests(self) -> bool:
        """Запускает интеграционные тесты"""
        self.log_section("ИНТЕГРАЦИОННЫЕ ТЕСТЫ")
        
        print("🔗 Тестирование интеграции компонентов...")
        
        # Тест 1: Проверка импортов
        try:
            from bot import ForestWolvesBot
            from game_logic import Game, GamePhase, Role, Team, Player
            from config import config, BOT_TOKEN
            print("✅ Все основные модули импортируются")
        except Exception as e:
            print(f"❌ Ошибка импорта: {e}")
            self.test_results['integration_tests'] = {'success': False, 'message': f'Ошибка импорта: {e}'}
            return False
        
        # Тест 2: Создание экземпляра бота
        try:
            bot = ForestWolvesBot()
            if bot:
                print("✅ Экземпляр бота создан")
            else:
                print("❌ Не удалось создать экземпляр бота")
                self.test_results['integration_tests'] = {'success': False, 'message': 'Не удалось создать бота'}
                return False
        except Exception as e:
            print(f"❌ Ошибка создания бота: {e}")
            self.test_results['integration_tests'] = {'success': False, 'message': f'Ошибка создания бота: {e}'}
            return False
        
        # Тест 3: Создание игры
        try:
            game = Game(chat_id=12345)
            if game:
                print("✅ Игра создана")
            else:
                print("❌ Не удалось создать игру")
                self.test_results['integration_tests'] = {'success': False, 'message': 'Не удалось создать игру'}
                return False
        except Exception as e:
            print(f"❌ Ошибка создания игры: {e}")
            self.test_results['integration_tests'] = {'success': False, 'message': f'Ошибка создания игры: {e}'}
            return False
        
        self.test_results['integration_tests'] = {'success': True, 'message': 'Интеграция работает'}
        return True
    
    def run_deployment_tests(self) -> bool:
        """Запускает тесты готовности к деплою"""
        self.log_section("ТЕСТЫ ГОТОВНОСТИ К ДЕПЛОЮ")
        
        print("🚀 Проверка готовности к деплою...")
        
        # Тест 1: Проверка переменных окружения
        env_vars = ['BOT_TOKEN', 'DATABASE_URL']
        missing_vars = []
        
        for var in env_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
            print("💡 Создайте файл .env с необходимыми переменными")
        else:
            print("✅ Переменные окружения настроены")
        
        # Тест 2: Проверка конфигурации
        try:
            if BOT_TOKEN and BOT_TOKEN != "your_bot_token_here":
                print("✅ Токен бота настроен")
            else:
                print("❌ Токен бота не настроен")
                self.test_results['deployment_tests'] = {'success': False, 'message': 'Токен бота не настроен'}
                return False
        except Exception as e:
            print(f"❌ Ошибка проверки токена: {e}")
            self.test_results['deployment_tests'] = {'success': False, 'message': f'Ошибка проверки токена: {e}'}
            return False
        
        # Тест 3: Проверка Docker файлов
        docker_files = ['Dockerfile', 'docker-compose.yml']
        missing_docker = []
        
        for file in docker_files:
            if not os.path.exists(file):
                missing_docker.append(file)
        
        if missing_docker:
            print(f"❌ Отсутствуют Docker файлы: {', '.join(missing_docker)}")
            self.test_results['deployment_tests'] = {'success': False, 'message': f'Отсутствуют Docker файлы: {missing_docker}'}
            return False
        else:
            print("✅ Docker файлы присутствуют")
        
        # Тест 4: Проверка зависимостей
        try:
            with open('requirements.txt', 'r') as f:
                requirements = f.read()
            
            if requirements.strip():
                print("✅ requirements.txt не пуст")
            else:
                print("❌ requirements.txt пуст")
                self.test_results['deployment_tests'] = {'success': False, 'message': 'requirements.txt пуст'}
                return False
        except Exception as e:
            print(f"❌ Ошибка чтения requirements.txt: {e}")
            self.test_results['deployment_tests'] = {'success': False, 'message': f'Ошибка чтения requirements.txt: {e}'}
            return False
        
        self.test_results['deployment_tests'] = {'success': True, 'message': 'Готов к деплою'}
        return True
    
    def generate_report(self) -> str:
        """Генерирует отчет о тестировании"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        report = f"""
# ОТЧЕТ О ТЕСТИРОВАНИИ СИСТЕМЫ "ЛЕС И ВОЛКИ"

## Общая информация
- **Дата и время**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
- **Длительность**: {duration.total_seconds():.2f} секунд
- **Версия Python**: {sys.version}

## Результаты тестов

"""
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        
        for test_name, result in self.test_results.items():
            status = "✅ ПРОЙДЕН" if result['success'] else "❌ ПРОВАЛЕН"
            report += f"### {test_name.replace('_', ' ').title()}\n"
            report += f"- **Статус**: {status}\n"
            report += f"- **Сообщение**: {result['message']}\n\n"
        
        report += f"""
## Итоговая статистика
- **Всего тестов**: {total_tests}
- **Пройдено**: {passed_tests}
- **Провалено**: {total_tests - passed_tests}
- **Процент успеха**: {(passed_tests / total_tests * 100):.1f}%

## Рекомендации
"""
        
        if passed_tests == total_tests:
            report += "- ✅ **СИСТЕМА ГОТОВА К ДЕПЛОЮ**\n"
            report += "- Все тесты пройдены успешно\n"
            report += "- Можно приступать к развертыванию\n"
        else:
            report += "- ⚠️ **ТРЕБУЕТСЯ ДОРАБОТКА**\n"
            report += "- Исправьте проваленные тесты перед деплоем\n"
            report += "- Проверьте логи ошибок выше\n"
        
        return report
    
    def save_report(self, report: str):
        """Сохраняет отчет в файл"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'test_report_{timestamp}.md'
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n📄 Отчет сохранен в файл: {filename}")
        except Exception as e:
            print(f"\n⚠️ Не удалось сохранить отчет: {e}")
    
    def run_all_tests(self) -> bool:
        """Запускает все тесты"""
        print("🚀 ЗАПУСК ПОЛНОГО ТЕСТИРОВАНИЯ СИСТЕМЫ 'ЛЕС И ВОЛКИ'")
        print("=" * 80)
        print(f"⏰ Начало: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Проверка окружения
        if not self.check_environment():
            print("\n❌ Проверка окружения провалена!")
            return False
        
        # Запуск тестов
        test_suites = [
            ("Базовые тесты", self.run_basic_tests),
            ("Тесты базы данных", self.run_database_tests),
            ("Тесты Docker", self.run_docker_tests),
            ("Комплексные тесты", self.run_comprehensive_tests),
            ("Интеграционные тесты", self.run_integration_tests),
            ("Тесты готовности к деплою", self.run_deployment_tests),
        ]
        
        all_passed = True
        
        for suite_name, suite_func in test_suites:
            try:
                if not suite_func():
                    all_passed = False
                    print(f"\n❌ {suite_name} провалены!")
                else:
                    print(f"\n✅ {suite_name} пройдены!")
            except Exception as e:
                print(f"\n💥 Критическая ошибка в {suite_name}: {e}")
                all_passed = False
        
        # Генерация отчета
        print("\n" + "=" * 80)
        print("📊 ГЕНЕРАЦИЯ ОТЧЕТА")
        print("=" * 80)
        
        report = self.generate_report()
        print(report)
        
        # Сохранение отчета
        self.save_report(report)
        
        # Сохранение JSON результатов
        json_filename = f'test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        try:
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, ensure_ascii=False, indent=2)
            print(f"📄 JSON результаты сохранены в: {json_filename}")
        except Exception as e:
            print(f"⚠️ Не удалось сохранить JSON: {e}")
        
        # Итоговый результат
        print("\n" + "=" * 80)
        if all_passed:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! СИСТЕМА ГОТОВА К ДЕПЛОЮ!")
            print("🚀 Можете приступать к развертыванию")
        else:
            print("⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ!")
            print("🔧 Исправьте ошибки перед деплоем")
        print("=" * 80)
        
        return all_passed


def main():
    """Основная функция"""
    runner = FullTestRunner()
    
    try:
        success = runner.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
        return 1
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
