#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Быстрый запуск расширенной системы лесов
Применяет миграции, тестирует систему и запускает бота
"""

import asyncio
import logging
import sys
import subprocess
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def run_command(command: str, description: str) -> bool:
    """Выполняет команду и возвращает результат"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - успешно")
            return True
        else:
            print(f"❌ {description} - ошибка:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ {description} - исключение: {e}")
        return False


async def test_system():
    """Тестирует систему"""
    print("\n🧪 Тестирование расширенной системы лесов...")
    
    try:
        from test_enhanced_forest_system import main as test_main
        await test_main()
        return True
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False


def check_requirements():
    """Проверяет требования"""
    print("🔍 Проверка требований...")
    
    required_files = [
        "forest_system.py",
        "forest_profiles.py", 
        "forest_analytics.py",
        "user_forest_profile.py",
        "enhanced_forest_integration.py",
        "bot_with_enhanced_forests.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Отсутствуют файлы: {', '.join(missing_files)}")
        return False
    
    print("✅ Все необходимые файлы найдены")
    return True


def apply_migrations():
    """Применяет миграции"""
    print("\n🗄️ Применение миграций базы данных...")
    
    try:
        from apply_forest_migration import apply_forest_migration
        success = apply_forest_migration()
        return success
    except Exception as e:
        print(f"❌ Ошибка при применении миграций: {e}")
        return False


async def start_bot():
    """Запускает бота"""
    print("\n🚀 Запуск бота с расширенной системой лесов...")
    
    try:
        from bot_with_enhanced_forests import main as bot_main
        await bot_main()
        return True
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
        return True
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        return False


async def main():
    """Главная функция быстрого запуска"""
    print("🌲 Быстрый запуск расширенной системы лесов 🌲")
    print("=" * 60)
    
    # Проверяем требования
    if not check_requirements():
        print("\n❌ Требования не выполнены. Завершение.")
        return
    
    # Применяем миграции
    if not apply_migrations():
        print("\n❌ Ошибка при применении миграций. Завершение.")
        return
    
    # Тестируем систему
    print("\n" + "="*60)
    test_success = await test_system()
    
    if not test_success:
        print("\n⚠️ Тестирование завершилось с ошибками, но продолжаем...")
    
    # Запускаем бота
    print("\n" + "="*60)
    print("🎉 Система готова! Запускаем бота...")
    print("="*60)
    
    await start_bot()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Быстрый запуск прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")
