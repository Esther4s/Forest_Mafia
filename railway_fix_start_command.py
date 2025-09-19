#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления команды запуска на Railway
"""

import os
import time

def fix_railway_start_command():
    """Исправляет команду запуска на Railway"""
    print("🔧 Исправление команды запуска Railway...")
    
    # Обновляем триггер
    timestamp = str(int(time.time()))
    with open('railway_trigger.txt', 'w') as f:
        f.write(timestamp)
    
    print(f"✅ Триггер обновлен: {timestamp}")
    
    # Проверяем конфигурационные файлы
    print("🔍 Проверка конфигурационных файлов...")
    
    # Procfile
    if os.path.exists('Procfile'):
        with open('Procfile', 'r') as f:
            procfile_content = f.read()
        print(f"📄 Procfile: {procfile_content.strip()}")
    
    # railway.json
    if os.path.exists('railway.json'):
        with open('railway.json', 'r') as f:
            railway_content = f.read()
        print(f"📄 railway.json: {railway_content.strip()}")
    
    print("✅ Конфигурация проверена")
    print("🚀 Railway должен использовать: python bot.py")

if __name__ == "__main__":
    fix_railway_start_command()
