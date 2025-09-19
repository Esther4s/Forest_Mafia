#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для принудительного обновления Railway
"""

import os
import subprocess
import time
import json

def update_railway_trigger():
    """Обновляет триггер для Railway"""
    print("🚀 Принудительное обновление Railway...")
    
    # Обновляем timestamp
    timestamp = int(time.time())
    
    # Создаем файл триггера
    trigger_content = f"""Railway deployment trigger
Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}
Timestamp: {timestamp}
Status: Force update
Version: 1.0.0
"""
    
    with open('railway_trigger.txt', 'w', encoding='utf-8') as f:
        f.write(trigger_content)
    
    print(f"✅ Триггер обновлен: {timestamp}")

def git_force_push():
    """Принудительно отправляет изменения в Git"""
    print("📤 Принудительная отправка в Git...")
    
    try:
        # Добавляем все файлы
        subprocess.run(['git', 'add', '.'], check=True)
        print("✅ Файлы добавлены")
        
        # Коммитим
        subprocess.run(['git', 'commit', '-m', f'🚀 Railway force update - {int(time.time())}'], check=True)
        print("✅ Коммит создан")
        
        # Принудительно отправляем
        subprocess.run(['git', 'push', 'origin', 'main', '--force'], check=True)
        print("✅ Изменения отправлены")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка Git: {e}")
        return False

def check_railway_files():
    """Проверяет файлы для Railway"""
    print("🔍 Проверка файлов Railway...")
    
    required_files = [
        'bot.py',
        'requirements.txt',
        'Procfile',
        'railway.json',
        'railway_trigger.txt'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Отсутствуют файлы: {', '.join(missing_files)}")
        return False
    
    print("✅ Все файлы Railway присутствуют")
    return True

def main():
    """Основная функция"""
    print("🚀 ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ RAILWAY")
    print("=" * 50)
    
    # Обновляем триггер
    update_railway_trigger()
    
    # Проверяем файлы
    if not check_railway_files():
        print("❌ Не все файлы присутствуют")
        return False
    
    # Принудительно отправляем
    if git_force_push():
        print("\n🎉 ОБНОВЛЕНИЕ ОТПРАВЛЕНО!")
        print("⏳ Railway должен подтянуть изменения в течение 1-2 минут")
        print("🔗 Проверьте статус деплоя в панели Railway")
        return True
    else:
        print("❌ Ошибка отправки обновлений")
        return False

if __name__ == "__main__":
    main()
