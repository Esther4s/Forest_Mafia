#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для настройки тестового окружения
"""

import os
import sys

def setup_test_environment():
    """Устанавливает переменные окружения для тестирования"""
    print("🔧 Настройка тестового окружения...")
    
    # Устанавливаем переменные окружения
    os.environ['BOT_TOKEN'] = 'test_token_123456789'
    os.environ['DATABASE_URL'] = 'sqlite:///test.db'
    os.environ['POSTGRES_USER'] = 'forest_mafia'
    os.environ['POSTGRES_PASSWORD'] = 'forest_mafia_password'
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    
    print("✅ Переменные окружения установлены")
    print(f"🔑 BOT_TOKEN: {os.environ['BOT_TOKEN']}")
    print(f"🗄️ DATABASE_URL: {os.environ['DATABASE_URL']}")
    print(f"🌍 ENVIRONMENT: {os.environ['ENVIRONMENT']}")

if __name__ == "__main__":
    setup_test_environment()
    print("\n🚀 Окружение готово для тестирования!")
