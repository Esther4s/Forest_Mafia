#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Проверка готовности к деплою на Railway
"""

import os
import sys

def check_railway_files():
    """Проверяем наличие файлов для Railway"""
    print("🚂 Проверяем готовность к деплою на Railway...")
    
    required_files = [
        'requirements.txt',
        'bot.py',
        'config.py',
        'railway.json',
        'env.production'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Отсутствуют файлы: {', '.join(missing_files)}")
        return False
    
    print("✅ Все необходимые файлы присутствуют")
    return True

def check_requirements():
    """Проверяем requirements.txt"""
    print("📦 Проверяем requirements.txt...")
    
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            requirements = f.read()
        
        required_packages = [
            'python-telegram-bot',
            'python-dotenv',
            'sqlalchemy',
            'alembic'
        ]
        
        missing_packages = []
        for package in required_packages:
            if package not in requirements:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ Отсутствуют пакеты: {', '.join(missing_packages)}")
            return False
        
        print("✅ Все зависимости присутствуют")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка чтения requirements.txt: {e}")
        return False

def check_railway_config():
    """Проверяем конфигурацию Railway"""
    print("⚙️ Проверяем конфигурацию Railway...")
    
    try:
        with open('railway.json', 'r', encoding='utf-8') as f:
            config = f.read()
        
        if 'python bot.py' in config:
            print("✅ Конфигурация Railway корректна")
            return True
        else:
            print("❌ Неправильная конфигурация Railway")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка чтения railway.json: {e}")
        return False

def check_env_template():
    """Проверяем шаблон переменных окружения"""
    print("🔧 Проверяем шаблон переменных окружения...")
    
    try:
        with open('env.production', 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        required_vars = [
            'BOT_TOKEN',
            'DATABASE_URL',
            'ENVIRONMENT',
            'LOG_LEVEL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if var not in env_content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Отсутствуют переменные: {', '.join(missing_vars)}")
            return False
        
        print("✅ Шаблон переменных окружения корректен")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка чтения env.production: {e}")
        return False

def main():
    """Основная функция проверки"""
    print("🎯 Проверка готовности к деплою на Railway")
    print("=" * 50)
    
    checks = [
        ("Файлы для Railway", check_railway_files),
        ("Зависимости", check_requirements),
        ("Конфигурация Railway", check_railway_config),
        ("Переменные окружения", check_env_template)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n🔍 {check_name}...")
        try:
            if check_func():
                passed += 1
        except Exception as e:
            print(f"❌ Ошибка в {check_name}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Результат: {passed}/{total} проверок пройдено")
    
    if passed == total:
        print("🎉 ГОТОВ К ДЕПЛОЮ НА RAILWAY!")
        print("\n🚀 Следующие шаги:")
        print("1. Создайте аккаунт на railway.app")
        print("2. Подключите GitHub репозиторий")
        print("3. Добавьте PostgreSQL базу данных")
        print("4. Настройте переменные окружения")
        print("5. Деплойте!")
        print("\n📖 Подробное руководство: RAILWAY_DEPLOYMENT_GUIDE.md")
        return True
    else:
        print("⚠️ НЕ ГОТОВ К ДЕПЛОЮ")
        print("🔧 Исправьте ошибки и повторите проверку")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
