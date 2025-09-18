#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для быстрого запуска бота "Лес и Волки"
"""

import os
import sys
import subprocess

def check_requirements():
    """Проверяет наличие необходимых зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    try:
        import telegram
        import psycopg2
        import sqlalchemy
        print("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("📦 Установите зависимости: pip install -r requirements.txt")
        return False

def check_env_file():
    """Проверяет наличие .env файла"""
    print("🔍 Проверка .env файла...")
    
    if os.path.exists('.env'):
        print("✅ .env файл найден")
        return True
    else:
        print("⚠️ .env файл не найден")
        print("📝 Создайте .env файл с BOT_TOKEN")
        return False

def main():
    """Основная функция запуска"""
    print("🚀 ЗАПУСК БОТА 'ЛЕС И ВОЛКИ'")
    print("=" * 40)
    
    # Проверяем зависимости
    if not check_requirements():
        return False
    
    # Проверяем .env файл
    if not check_env_file():
        print("\n💡 Создайте .env файл со следующим содержимым:")
        print("BOT_TOKEN=your_bot_token_here")
        print("DATABASE_URL=postgresql://postgres:password@host:port/database")
        return False
    
    # Запускаем бота
    print("\n🎮 Запуск бота...")
    try:
        subprocess.run([sys.executable, "bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска бота: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
        return True
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
