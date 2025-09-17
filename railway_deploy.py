#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт деплоя на Railway
"""

import os
import sys
import subprocess
import time

def check_environment():
    """Проверяет переменные окружения"""
    print("🔍 Проверка переменных окружения...")
    
    required_vars = ['BOT_TOKEN', 'DATABASE_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные: {', '.join(missing_vars)}")
        return False
    
    print("✅ Переменные окружения настроены")
    return True

def install_dependencies():
    """Устанавливает зависимости"""
    print("📦 Установка зависимостей...")
    
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True, capture_output=True, text=True)
        print("✅ Зависимости установлены")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка установки зависимостей: {e}")
        return False

def test_imports():
    """Тестирует импорты"""
    print("🧪 Тестирование импортов...")
    
    try:
        from bot import ForestMafiaBot
        from game_logic import Game, Role, Team, Player
        from night_actions import NightActions
        from night_interface import NightInterface
        from config import BOT_TOKEN, MIN_PLAYERS
        print("✅ Все модули импортированы")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def test_database():
    """Тестирует базу данных"""
    print("🗄️ Тестирование базы данных...")
    
    try:
        from database_psycopg2 import init_db, execute_query, close_db
        
        db = init_db()
        if db is None:
            print("❌ Не удалось подключиться к БД")
            return False
        
        result = execute_query("SELECT 1 as test")
        if result:
            print("✅ База данных работает")
            close_db()
            return True
        else:
            print("❌ Запрос к БД не выполнился")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        return False

def start_bot():
    """Запускает бота"""
    print("🚀 Запуск бота...")
    
    try:
        from bot import ForestMafiaBot
        
        bot = ForestMafiaBot()
        print("✅ Бот создан успешно")
        print("🔄 Запуск бота...")
        
        # Запускаем бота
        bot.run()
        
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        return False

def main():
    """Основная функция деплоя"""
    print("🚀 ДЕПЛОЙ НА RAILWAY")
    print("=" * 50)
    
    # Проверяем окружение
    if not check_environment():
        print("❌ Деплой прерван: проблемы с окружением")
        return False
    
    # Устанавливаем зависимости
    if not install_dependencies():
        print("❌ Деплой прерван: проблемы с зависимостями")
        return False
    
    # Тестируем импорты
    if not test_imports():
        print("❌ Деплой прерван: проблемы с импортами")
        return False
    
    # Тестируем базу данных
    if not test_database():
        print("❌ Деплой прерван: проблемы с БД")
        return False
    
    print("✅ Все проверки пройдены!")
    print("🚀 Запуск бота...")
    
    # Запускаем бота
    start_bot()

if __name__ == "__main__":
    main()