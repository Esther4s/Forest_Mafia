#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка подключения к Railway
"""

import os
import subprocess
import time

def check_git_status():
    """Проверяет статус Git"""
    print("🔍 Проверка статуса Git...")
    
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            print("📝 Есть неотслеживаемые изменения:")
            print(result.stdout)
            return True
        else:
            print("✅ Рабочая директория чистая")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка Git: {e}")
        return False

def check_remote():
    """Проверяет удаленный репозиторий"""
    print("\n🌐 Проверка удаленного репозитория...")
    
    try:
        result = subprocess.run(['git', 'remote', '-v'], 
                              capture_output=True, text=True, check=True)
        print("📡 Удаленные репозитории:")
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка проверки remote: {e}")
        return False

def check_last_commit():
    """Проверяет последний коммит"""
    print("\n📋 Проверка последнего коммита...")
    
    try:
        result = subprocess.run(['git', 'log', '-1', '--oneline'], 
                              capture_output=True, text=True, check=True)
        print(f"📝 Последний коммит: {result.stdout.strip()}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка проверки коммита: {e}")
        return False

def force_update():
    """Принудительно обновляет Railway"""
    print("\n🚀 Принудительное обновление Railway...")
    
    try:
        # Добавляем все файлы
        subprocess.run(['git', 'add', '.'], check=True)
        print("✅ Файлы добавлены")
        
        # Коммитим с timestamp
        timestamp = int(time.time())
        commit_msg = f"🚀 Railway force update - {timestamp}"
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        print("✅ Коммит создан")
        
        # Отправляем
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        print("✅ Изменения отправлены")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка обновления: {e}")
        return False

def main():
    """Основная функция"""
    print("🔍 ПРОВЕРКА ПОДКЛЮЧЕНИЯ К RAILWAY")
    print("=" * 50)
    
    # Проверяем статус
    has_changes = check_git_status()
    
    # Проверяем remote
    check_remote()
    
    # Проверяем последний коммит
    check_last_commit()
    
    # Принудительно обновляем
    if force_update():
        print("\n🎉 ОБНОВЛЕНИЕ ОТПРАВЛЕНО!")
        print("⏳ Railway должен подтянуть изменения")
        print("🔗 Проверьте панель Railway через 1-2 минуты")
    else:
        print("\n❌ Ошибка обновления Railway")

if __name__ == "__main__":
    main()
