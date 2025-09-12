#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт проверки готовности к деплою на Railway
"""

import os
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_git_status():
    """Проверка статуса Git"""
    logger.info("🔍 Проверка статуса Git...")
    
    try:
        import subprocess
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            logger.warning("⚠️ Есть несохраненные изменения:")
            logger.warning(result.stdout)
            return False
        else:
            logger.info("✅ Git репозиторий чист")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки Git: {e}")
        return False

def check_required_files():
    """Проверка необходимых файлов"""
    logger.info("🔍 Проверка необходимых файлов...")
    
    required_files = [
        'bot.py',
        'requirements.txt',
        'railway.json',
        'config.py',
        'database_psycopg2.py',
        'game_logic.py',
        'night_actions.py',
        'forest_mafia_settings.py',
        'global_settings.py',
        'database_balance_manager.py'
    ]
    
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"❌ Отсутствуют файлы: {', '.join(missing_files)}")
        return False
    else:
        logger.info("✅ Все необходимые файлы присутствуют")
        return True

def check_railway_config():
    """Проверка конфигурации Railway"""
    logger.info("🔍 Проверка конфигурации Railway...")
    
    try:
        import json
        
        with open('railway.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Проверяем обязательные поля
        if 'deploy' not in config:
            logger.error("❌ Отсутствует секция 'deploy' в railway.json")
            return False
        
        if 'startCommand' not in config['deploy']:
            logger.error("❌ Отсутствует 'startCommand' в railway.json")
            return False
        
        if config['deploy']['startCommand'] != 'python bot.py':
            logger.warning("⚠️ Нестандартная команда запуска")
        
        logger.info("✅ Конфигурация Railway корректна")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки railway.json: {e}")
        return False

def check_requirements():
    """Проверка requirements.txt"""
    logger.info("🔍 Проверка requirements.txt...")
    
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            requirements = f.read()
        
        required_packages = [
            'python-telegram-bot',
            'python-dotenv',
            'sqlalchemy',
            'alembic',
            'psycopg2-binary'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            if package not in requirements:
                missing_packages.append(package)
        
        if missing_packages:
            logger.error(f"❌ Отсутствуют пакеты: {', '.join(missing_packages)}")
            return False
        else:
            logger.info("✅ Все необходимые пакеты указаны")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки requirements.txt: {e}")
        return False

def check_gitignore():
    """Проверка .gitignore"""
    logger.info("🔍 Проверка .gitignore...")
    
    try:
        with open('.gitignore', 'r', encoding='utf-8') as f:
            gitignore = f.read()
        
        important_patterns = [
            '.env',
            '__pycache__',
            '*.pyc',
            '*.log',
            '*.db'
        ]
        
        missing_patterns = []
        
        for pattern in important_patterns:
            if pattern not in gitignore:
                missing_patterns.append(pattern)
        
        if missing_patterns:
            logger.warning(f"⚠️ Рекомендуется добавить в .gitignore: {', '.join(missing_patterns)}")
        else:
            logger.info("✅ .gitignore настроен корректно")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки .gitignore: {e}")
        return False

def check_code_syntax():
    """Проверка синтаксиса кода"""
    logger.info("🔍 Проверка синтаксиса кода...")
    
    python_files = [
        'bot.py',
        'config.py',
        'database_psycopg2.py',
        'game_logic.py',
        'night_actions.py',
        'forest_mafia_settings.py',
        'global_settings.py',
        'database_balance_manager.py'
    ]
    
    syntax_errors = []
    
    for file in python_files:
        if os.path.exists(file):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    compile(f.read(), file, 'exec')
            except SyntaxError as e:
                syntax_errors.append(f"{file}: {e}")
    
    if syntax_errors:
        logger.error("❌ Синтаксические ошибки:")
        for error in syntax_errors:
            logger.error(f"  {error}")
        return False
    else:
        logger.info("✅ Синтаксис кода корректен")
        return True

def main():
    """Главная функция проверки"""
    logger.info("🚀 ПРОВЕРКА ГОТОВНОСТИ К ДЕПЛОЮ НА RAILWAY")
    logger.info("=" * 60)
    
    checks = [
        ("Статус Git", check_git_status),
        ("Необходимые файлы", check_required_files),
        ("Конфигурация Railway", check_railway_config),
        ("Requirements.txt", check_requirements),
        (".gitignore", check_gitignore),
        ("Синтаксис кода", check_code_syntax)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        logger.info(f"\n📋 Проверка: {check_name}")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в проверке {check_name}: {e}")
            results.append((check_name, False))
    
    # Статистика
    total = len(results)
    passed = sum(1 for _, result in results if result)
    failed = total - passed
    
    logger.info("\n" + "=" * 60)
    logger.info("📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ")
    logger.info("=" * 60)
    logger.info(f"Всего проверок: {total}")
    logger.info(f"✅ Пройдено: {passed}")
    logger.info(f"❌ Провалено: {failed}")
    logger.info(f"📊 Готовность: {(passed/total)*100:.1f}%")
    
    logger.info("\n📋 Детали проверок:")
    for check_name, result in results:
        status = "✅" if result else "❌"
        logger.info(f"  {status} {check_name}")
    
    if failed == 0:
        logger.info("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        logger.info("🚀 ПРОЕКТ ГОТОВ К ДЕПЛОЮ НА RAILWAY!")
        logger.info("\n📋 Следующие шаги:")
        logger.info("1. Откройте railway.app")
        logger.info("2. Создайте новый проект")
        logger.info("3. Подключите Git репозиторий")
        logger.info("4. Настройте переменные окружения")
        logger.info("5. Запустите деплой")
        return True
    else:
        logger.warning(f"\n⚠️ {failed} проверок провалено.")
        logger.warning("🔧 Исправьте ошибки перед деплоем.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
