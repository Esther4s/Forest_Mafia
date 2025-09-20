#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для коммита и пуша изменений в GitHub
"""

import os
import subprocess
import sys
from datetime import datetime

def run_command(command, description):
    """Выполняет команду и выводит результат"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            print(f"✅ {description} выполнено успешно")
            if result.stdout.strip():
                print(f"   Вывод: {result.stdout.strip()}")
        else:
            print(f"❌ Ошибка при {description}")
            print(f"   Ошибка: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Исключение при {description}: {e}")
        return False
    return True

def main():
    """Главная функция"""
    print("🌲 Forest Mafia Bot - Коммит и пуш изменений")
    print("=" * 60)
    
    # Проверяем, что мы в git репозитории
    if not os.path.exists('.git'):
        print("❌ Это не git репозиторий!")
        return False
    
    # Получаем статус git
    print("\n📊 Статус git репозитория:")
    if not run_command("git status", "Проверка статуса"):
        return False
    
    # Добавляем все изменения
    print("\n📁 Добавление изменений:")
    if not run_command("git add .", "Добавление всех файлов"):
        return False
    
    # Создаем коммит
    commit_message = f"🌲 Настройка бота для работы с Railway PostgreSQL\n\n" \
                    f"- Настроены переменные окружения\n" \
                    f"- Исправлена схема базы данных\n" \
                    f"- Добавлены тесты и скрипты\n" \
                    f"- Созданы инструкции по развертыванию\n" \
                    f"- Бот готов к работе\n\n" \
                    f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    print(f"\n💾 Создание коммита:")
    print(f"   Сообщение: {commit_message[:100]}...")
    
    if not run_command(f'git commit -m "{commit_message}"', "Создание коммита"):
        return False
    
    # Пушим изменения
    print(f"\n🚀 Отправка изменений в GitHub:")
    if not run_command("git push origin main", "Отправка в GitHub"):
        return False
    
    print("\n🎉 Все изменения успешно отправлены в GitHub!")
    print("\n📋 Что было сделано:")
    print("   ✅ Настроены переменные окружения")
    print("   ✅ Исправлена схема базы данных")
    print("   ✅ Добавлены тесты и скрипты")
    print("   ✅ Созданы инструкции по развертыванию")
    print("   ✅ Бот готов к работе")
    
    print("\n🚀 Следующие шаги:")
    print("   1. Добавьте бота в группу: @Forest_fuss_bot")
    print("   2. Настройте права администратора")
    print("   3. Запустите бота: python bot.py")
    print("   4. Начните игру командой /start_game")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
