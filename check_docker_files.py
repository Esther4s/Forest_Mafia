#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка Docker файлов без запуска Docker
"""

import os
import re

def check_dockerfile():
    """Проверяет Dockerfile"""
    print("🐳 Проверка Dockerfile...")
    
    if not os.path.exists('Dockerfile'):
        print("❌ Dockerfile не найден")
        return False
    
    with open('Dockerfile', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем основные директивы
    required_directives = ['FROM', 'WORKDIR', 'COPY', 'RUN', 'CMD']
    missing = [d for d in required_directives if d not in content]
    
    if missing:
        print(f"❌ Отсутствуют директивы: {', '.join(missing)}")
        return False
    
    # Проверяем базовый образ
    if 'FROM python:' not in content:
        print("❌ Неверный базовый образ Python")
        return False
    
    # Проверяем установку зависимостей
    if 'pip install' not in content:
        print("❌ Не найдена установка зависимостей")
        return False
    
    print("✅ Dockerfile корректен")
    return True

def check_docker_compose():
    """Проверяет docker-compose.yml"""
    print("🐳 Проверка docker-compose.yml...")
    
    if not os.path.exists('docker-compose.yml'):
        print("❌ docker-compose.yml не найден")
        return False
    
    with open('docker-compose.yml', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем основные секции
    required_sections = ['version', 'services', 'volumes', 'networks']
    missing = [s for s in required_sections if s not in content]
    
    if missing:
        print(f"❌ Отсутствуют секции: {', '.join(missing)}")
        return False
    
    # Проверяем сервисы
    if 'forest-mafia-bot' not in content:
        print("❌ Сервис forest-mafia-bot не найден")
        return False
    
    if 'postgres' not in content:
        print("❌ Сервис postgres не найден")
        return False
    
    print("✅ docker-compose.yml корректен")
    return True

def check_requirements():
    """Проверяет requirements.txt"""
    print("🐳 Проверка requirements.txt...")
    
    if not os.path.exists('requirements.txt'):
        print("❌ requirements.txt не найден")
        return False
    
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        print("❌ requirements.txt пуст")
        return False
    
    # Проверяем основные зависимости
    required_packages = [
        'python-telegram-bot',
        'sqlalchemy',
        'psycopg2-binary',
        'python-dotenv'
    ]
    
    missing = []
    for package in required_packages:
        if package not in content:
            missing.append(package)
    
    if missing:
        print(f"❌ Отсутствуют пакеты: {', '.join(missing)}")
        return False
    
    print("✅ requirements.txt корректен")
    return True

def check_env_example():
    """Проверяет примеры .env файлов"""
    print("🐳 Проверка примеров .env файлов...")
    
    env_files = ['env_example.txt', 'production.env.example', '.env.example']
    found_files = []
    
    for file in env_files:
        if os.path.exists(file):
            found_files.append(file)
    
    if not found_files:
        print("⚠️ Примеры .env файлов не найдены")
        return False
    
    print(f"✅ Найдены примеры .env: {', '.join(found_files)}")
    return True

def main():
    """Основная функция"""
    print("🚀 ПРОВЕРКА DOCKER ФАЙЛОВ")
    print("=" * 40)
    
    tests = [
        ("Dockerfile", check_dockerfile),
        ("Docker Compose", check_docker_compose),
        ("Requirements", check_requirements),
        ("Env Examples", check_env_example),
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
    
    print("\n" + "=" * 40)
    print(f"🏁 РЕЗУЛЬТАТ: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ DOCKER ФАЙЛЫ КОРРЕКТНЫ!")
        print("✅ Готово к сборке и деплою")
        print("📋 Команды для деплоя:")
        print("   docker build -t forest-mafia-bot .")
        print("   docker-compose up -d")
        return True
    else:
        print("⚠️ НЕКОТОРЫЕ ФАЙЛЫ ТРЕБУЮТ ИСПРАВЛЕНИЯ!")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
