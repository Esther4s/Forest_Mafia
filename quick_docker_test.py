#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест Docker для проверки готовности к деплою
"""

import subprocess
import os
import time
import tempfile
import sys


def run_command(cmd, timeout=60):
    """Выполняет команду с таймаутом"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Таймаут выполнения"
    except Exception as e:
        return False, "", str(e)


def test_docker_installation():
    """Проверяет установку Docker"""
    print("🐳 Проверка установки Docker...")
    
    success, stdout, stderr = run_command(['docker', '--version'])
    if success:
        print(f"✅ Docker установлен: {stdout.strip()}")
        return True
    else:
        print(f"❌ Docker не установлен: {stderr}")
        return False


def test_docker_compose_installation():
    """Проверяет установку Docker Compose"""
    print("🐳 Проверка установки Docker Compose...")
    
    success, stdout, stderr = run_command(['docker-compose', '--version'])
    if success:
        print(f"✅ Docker Compose установлен: {stdout.strip()}")
        return True
    else:
        print(f"❌ Docker Compose не установлен: {stderr}")
        return False


def test_dockerfile():
    """Проверяет Dockerfile"""
    print("🐳 Проверка Dockerfile...")
    
    if not os.path.exists('Dockerfile'):
        print("❌ Dockerfile не найден")
        return False
    
    # Читаем Dockerfile
    with open('Dockerfile', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем основные директивы
    required_directives = ['FROM', 'WORKDIR', 'COPY', 'RUN', 'CMD']
    missing = [d for d in required_directives if d not in content]
    
    if missing:
        print(f"❌ Отсутствуют директивы: {', '.join(missing)}")
        return False
    
    print("✅ Dockerfile корректен")
    return True


def test_docker_compose_file():
    """Проверяет docker-compose.yml"""
    print("🐳 Проверка docker-compose.yml...")
    
    if not os.path.exists('docker-compose.yml'):
        print("❌ docker-compose.yml не найден")
        return False
    
    success, stdout, stderr = run_command(['docker-compose', 'config'])
    if success:
        print("✅ docker-compose.yml корректен")
        return True
    else:
        print(f"❌ Ошибка в docker-compose.yml: {stderr}")
        return False


def test_docker_build():
    """Тестирует сборку образа"""
    print("🐳 Тестирование сборки Docker образа...")
    
    success, stdout, stderr = run_command(['docker', 'build', '-t', 'forest-mafia-quick-test', '.'], timeout=300)
    if success:
        print("✅ Образ собран успешно")
        return True
    else:
        print(f"❌ Ошибка сборки: {stderr}")
        return False


def test_docker_run():
    """Тестирует запуск контейнера"""
    print("🐳 Тестирование запуска контейнера...")
    
    # Создаем временный .env файл
    env_content = """BOT_TOKEN=test_token_123456789
DATABASE_URL=sqlite:///test.db
ENVIRONMENT=test
LOG_LEVEL=DEBUG
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(env_content)
        env_file = f.name
    
    try:
        # Запускаем контейнер
        success, stdout, stderr = run_command([
            'docker', 'run', '-d',
            '--name', 'forest-mafia-quick-test',
            '--env-file', env_file,
            'forest-mafia-quick-test'
        ], timeout=60)
        
        if success:
            print("✅ Контейнер запущен")
            
            # Ждем и проверяем статус
            time.sleep(5)
            success, stdout, stderr = run_command([
                'docker', 'ps', '--filter', 'name=forest-mafia-quick-test', '--format', '{{.Status}}'
            ])
            
            if success and 'Up' in stdout:
                print("✅ Контейнер работает")
                return True
            else:
                print("❌ Контейнер не запустился")
                return False
        else:
            print(f"❌ Ошибка запуска: {stderr}")
            return False
    
    finally:
        # Очистка
        try:
            run_command(['docker', 'stop', 'forest-mafia-quick-test'])
            run_command(['docker', 'rm', 'forest-mafia-quick-test'])
            run_command(['docker', 'rmi', 'forest-mafia-quick-test'])
            os.unlink(env_file)
        except:
            pass


def main():
    """Основная функция"""
    print("🚀 БЫСТРЫЙ ТЕСТ DOCKER ДЛЯ ДЕПЛОЯ")
    print("=" * 50)
    
    tests = [
        ("Docker Installation", test_docker_installation),
        ("Docker Compose Installation", test_docker_compose_installation),
        ("Dockerfile", test_dockerfile),
        ("Docker Compose File", test_docker_compose_file),
        ("Docker Build", test_docker_build),
        ("Docker Run", test_docker_run),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - ПРОЙДЕН")
            else:
                print(f"❌ {test_name} - ПРОВАЛЕН")
        except Exception as e:
            print(f"💥 {test_name} - ОШИБКА: {e}")
    
    print("\n" + "=" * 50)
    print(f"🏁 РЕЗУЛЬТАТ: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Docker готов к деплою!")
        return 0
    else:
        print("⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ! Исправьте ошибки.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
