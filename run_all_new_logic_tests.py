#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для запуска всех тестов новых логик
"""

import subprocess
import sys
import os


def run_test_file(test_file):
    """Запускает тестовый файл и возвращает результат"""
    print(f"\n{'='*60}")
    print(f"🧪 Запуск тестов: {test_file}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, encoding='utf-8')
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Ошибка запуска тестов {test_file}: {e}")
        return False


def main():
    """Основная функция"""
    print("🎮 Запуск всех тестов новых логик Лесной Мафии")
    print("=" * 60)
    
    # Список тестовых файлов
    test_files = [
        "test_mole_logic.py",
        "test_fox_logic.py", 
        "test_beaver_logic.py",
        "test_supplies_restoration.py"
    ]
    
    results = {}
    total_tests = 0
    passed_tests = 0
    
    # Запускаем каждый тест
    for test_file in test_files:
        if os.path.exists(test_file):
            success = run_test_file(test_file)
            results[test_file] = success
            if success:
                passed_tests += 1
            total_tests += 1
        else:
            print(f"⚠️  Файл {test_file} не найден")
            results[test_file] = False
            total_tests += 1
    
    # Выводим итоговый отчет
    print(f"\n{'='*60}")
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print(f"{'='*60}")
    
    for test_file, success in results.items():
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print(f"{test_file:<35} {status}")
    
    print(f"\n📈 Статистика:")
    print(f"   Всего тестов: {total_tests}")
    print(f"   Пройдено: {passed_tests}")
    print(f"   Провалено: {total_tests - passed_tests}")
    print(f"   Процент успеха: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print(f"\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✨ Все новые логики работают корректно!")
        return True
    else:
        print(f"\n⚠️  Некоторые тесты провалены. Проверьте логи выше.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
