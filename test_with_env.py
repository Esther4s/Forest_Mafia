#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест с автоматической настройкой окружения
"""

import os
import sys

# Устанавливаем переменные окружения перед импортом модулей
os.environ['BOT_TOKEN'] = 'test_token_123456789'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'
os.environ['POSTGRES_USER'] = 'forest_mafia'
os.environ['POSTGRES_PASSWORD'] = 'forest_mafia_password'
os.environ['ENVIRONMENT'] = 'test'
os.environ['LOG_LEVEL'] = 'DEBUG'

print("🔧 Переменные окружения установлены для тестирования")

# Теперь импортируем и запускаем тесты
try:
    from test_all import main as test_main
    print("✅ Модули импортированы успешно")
    
    print("\n🚀 Запуск тестов...")
    success = test_main()
    
    if success:
        print("\n🎉 Все тесты пройдены успешно!")
        sys.exit(0)
    else:
        print("\n❌ Некоторые тесты провалены!")
        sys.exit(1)
        
except Exception as e:
    print(f"\n💥 Ошибка при запуске тестов: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
