#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Специализированные тесты для Docker контейнеризации
"""

import subprocess
import os
import time
import tempfile
import json
from typing import Dict, List, Optional


class DockerTestSuite:
    """Набор тестов для Docker"""
    
    def __init__(self):
        self.containers = []
        self.images = []
        self.temp_files = []
    
    def cleanup(self):
        """Очистка Docker ресурсов"""
        print("\n🧹 Очистка Docker ресурсов...")
        
        # Остановка и удаление контейнеров
        for container in self.containers:
            try:
                subprocess.run(['docker', 'stop', container], check=False, capture_output=True)
                subprocess.run(['docker', 'rm', container], check=False, capture_output=True)
                print(f"✅ Контейнер {container} удален")
            except Exception as e:
                print(f"⚠️ Ошибка удаления контейнера {container}: {e}")
        
        # Удаление образов
        for image in self.images:
            try:
                subprocess.run(['docker', 'rmi', image], check=False, capture_output=True)
                print(f"✅ Образ {image} удален")
            except Exception as e:
                print(f"⚠️ Ошибка удаления образа {image}: {e}")
        
        # Удаление временных файлов
        for temp_file in self.temp_files:
            try:
                os.remove(temp_file)
                print(f"✅ Временный файл {temp_file} удален")
            except Exception as e:
                print(f"⚠️ Ошибка удаления {temp_file}: {e}")
    
    def test_docker_installed(self) -> bool:
        """Проверяет установку Docker"""
        print("🐳 Проверка установки Docker...")
        
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Docker установлен: {result.stdout.strip()}")
                return True
            else:
                print("❌ Docker не установлен")
                return False
        except FileNotFoundError:
            print("❌ Docker не найден в PATH")
            return False
        except Exception as e:
            print(f"❌ Ошибка проверки Docker: {e}")
            return False
    
    def test_docker_compose_installed(self) -> bool:
        """Проверяет установку Docker Compose"""
        print("🐳 Проверка установки Docker Compose...")
        
        try:
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Docker Compose установлен: {result.stdout.strip()}")
                return True
            else:
                print("❌ Docker Compose не установлен")
                return False
        except FileNotFoundError:
            print("❌ Docker Compose не найден в PATH")
            return False
        except Exception as e:
            print(f"❌ Ошибка проверки Docker Compose: {e}")
            return False
    
    def test_dockerfile_syntax(self) -> bool:
        """Проверяет синтаксис Dockerfile"""
        print("🐳 Проверка синтаксиса Dockerfile...")
        
        if not os.path.exists('Dockerfile'):
            print("❌ Dockerfile не найден")
            return False
        
        try:
            # Читаем Dockerfile
            with open('Dockerfile', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Проверяем основные директивы
            required_directives = ['FROM', 'WORKDIR', 'COPY', 'RUN', 'CMD']
            missing_directives = []
            
            for directive in required_directives:
                if directive not in content:
                    missing_directives.append(directive)
            
            if missing_directives:
                print(f"❌ Отсутствуют директивы: {', '.join(missing_directives)}")
                return False
            
            # Проверяем базовый образ
            if 'FROM python:' not in content:
                print("❌ Неверный базовый образ Python")
                return False
            
            print("✅ Dockerfile синтаксически корректен")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка чтения Dockerfile: {e}")
            return False
    
    def test_docker_compose_syntax(self) -> bool:
        """Проверяет синтаксис docker-compose.yml"""
        print("🐳 Проверка синтаксиса docker-compose.yml...")
        
        if not os.path.exists('docker-compose.yml'):
            print("❌ docker-compose.yml не найден")
            return False
        
        try:
            result = subprocess.run(['docker-compose', 'config'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ docker-compose.yml синтаксически корректен")
                return True
            else:
                print(f"❌ Ошибка в docker-compose.yml: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Ошибка проверки docker-compose.yml: {e}")
            return False
    
    def test_docker_build(self) -> bool:
        """Тестирует сборку Docker образа"""
        print("🐳 Тестирование сборки Docker образа...")
        
        try:
            # Собираем образ
            result = subprocess.run([
                'docker', 'build', '-t', 'forest-mafia-test:latest', '.'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("✅ Docker образ собран успешно")
                self.images.append('forest-mafia-test:latest')
                return True
            else:
                print(f"❌ Ошибка сборки: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Таймаут сборки (5 минут)")
            return False
        except Exception as e:
            print(f"❌ Ошибка сборки: {e}")
            return False
    
    def test_docker_run_basic(self) -> bool:
        """Тестирует базовый запуск контейнера"""
        print("🐳 Тестирование базового запуска контейнера...")
        
        try:
            # Создаем временный .env файл
            env_content = """BOT_TOKEN=test_token_123456789
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
                '--name', 'forest-mafia-test-basic',
                '--env-file', env_file,
                'forest-mafia-test:latest'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.containers.append('forest-mafia-test-basic')
                
                # Ждем и проверяем статус
                time.sleep(10)
                status_result = subprocess.run([
                    'docker', 'ps', '--filter', 'name=forest-mafia-test-basic', '--format', '{{.Status}}'
                ], capture_output=True, text=True)
                
                if 'Up' in status_result.stdout:
                    print("✅ Контейнер запущен и работает")
                    return True
                else:
                    print("❌ Контейнер не запустился")
                    return False
            else:
                print(f"❌ Ошибка запуска: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка запуска: {e}")
            return False
    
    def test_docker_compose_up(self) -> bool:
        """Тестирует запуск через Docker Compose"""
        print("🐳 Тестирование Docker Compose...")
        
        try:
            # Создаем временный .env файл для compose
            env_content = """BOT_TOKEN=test_token_123456789
DATABASE_URL=postgresql://forest_mafia:forest_mafia_password@postgres:5432/forest_mafia
POSTGRES_USER=forest_mafia
POSTGRES_PASSWORD=forest_mafia_password
ENVIRONMENT=test
LOG_LEVEL=DEBUG
"""
            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
                f.write(env_content)
                env_file = f.name
                self.temp_files.append(env_file)
            
            # Запускаем через compose
            result = subprocess.run([
                'docker-compose', '--env-file', env_file, 'up', '-d'
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print("✅ Docker Compose запущен успешно")
                
                # Добавляем контейнеры для очистки
                self.containers.extend(['forest-mafia-bot', 'forest-mafia-postgres'])
                
                # Ждем и проверяем статус
                time.sleep(15)
                
                # Проверяем статус бота
                bot_status = subprocess.run([
                    'docker', 'ps', '--filter', 'name=forest-mafia-bot', '--format', '{{.Status}}'
                ], capture_output=True, text=True)
                
                # Проверяем статус PostgreSQL
                postgres_status = subprocess.run([
                    'docker', 'ps', '--filter', 'name=forest-mafia-postgres', '--format', '{{.Status}}'
                ], capture_output=True, text=True)
                
                if 'Up' in bot_status.stdout and 'Up' in postgres_status.stdout:
                    print("✅ Все сервисы запущены")
                    return True
                else:
                    print("❌ Не все сервисы запущены")
                    return False
            else:
                print(f"❌ Ошибка Docker Compose: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка Docker Compose: {e}")
            return False
    
    def test_docker_logs(self) -> bool:
        """Проверяет логи контейнера"""
        print("🐳 Проверка логов контейнера...")
        
        try:
            # Получаем логи бота
            result = subprocess.run([
                'docker', 'logs', 'forest-mafia-bot', '--tail', '50'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logs = result.stdout
                print("✅ Логи получены успешно")
                
                # Проверяем наличие ошибок
                error_keywords = ['ERROR', 'CRITICAL', 'Exception', 'Traceback']
                errors_found = []
                
                for keyword in error_keywords:
                    if keyword in logs:
                        errors_found.append(keyword)
                
                if errors_found:
                    print(f"⚠️ Найдены ошибки в логах: {', '.join(errors_found)}")
                    print("📄 Последние логи:")
                    print(logs[-500:])  # Последние 500 символов
                    return False
                else:
                    print("✅ Критических ошибок в логах не найдено")
                    return True
            else:
                print(f"❌ Ошибка получения логов: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка проверки логов: {e}")
            return False
    
    def test_docker_health(self) -> bool:
        """Проверяет здоровье контейнера"""
        print("🐳 Проверка здоровья контейнера...")
        
        try:
            # Проверяем, что контейнер работает
            result = subprocess.run([
                'docker', 'inspect', 'forest-mafia-bot', '--format', '{{.State.Status}}'
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and 'running' in result.stdout:
                print("✅ Контейнер работает")
                
                # Проверяем использование ресурсов
                stats_result = subprocess.run([
                    'docker', 'stats', 'forest-mafia-bot', '--no-stream', '--format', '{{.CPUPerc}} {{.MemUsage}}'
                ], capture_output=True, text=True)
                
                if stats_result.returncode == 0:
                    print(f"📊 Ресурсы: {stats_result.stdout.strip()}")
                
                return True
            else:
                print("❌ Контейнер не работает")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка проверки здоровья: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Запускает все Docker тесты"""
        print("🚀 Запуск Docker тестов\n")
        print("=" * 50)
        
        tests = [
            ("Docker Installation", self.test_docker_installed),
            ("Docker Compose Installation", self.test_docker_compose_installed),
            ("Dockerfile Syntax", self.test_dockerfile_syntax),
            ("Docker Compose Syntax", self.test_docker_compose_syntax),
            ("Docker Build", self.test_docker_build),
            ("Docker Run Basic", self.test_docker_run_basic),
            ("Docker Compose Up", self.test_docker_compose_up),
            ("Docker Logs", self.test_docker_logs),
            ("Docker Health", self.test_docker_health),
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
                print()
        
        # Очистка
        self.cleanup()
        
        # Результаты
        print("=" * 50)
        print(f"🏁 Docker тесты: {passed_tests}/{total_tests} пройдено")
        
        if passed_tests == total_tests:
            print("🎉 Все Docker тесты пройдены!")
            return True
        else:
            print("⚠️ Некоторые Docker тесты провалены!")
            return False


def main():
    """Основная функция"""
    test_suite = DockerTestSuite()
    
    try:
        success = test_suite.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано")
        test_suite.cleanup()
        return 1
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        test_suite.cleanup()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
