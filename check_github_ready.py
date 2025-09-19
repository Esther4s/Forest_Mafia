#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Проверка готовности проекта к загрузке на GitHub
"""

import os
import sys

def check_git_status():
    """Проверяем статус Git"""
    print("🔍 Проверяем статус Git...")
    
    # Проверяем, инициализирован ли Git
    if not os.path.exists('.git'):
        print("⚠️ Git не инициализирован")
        print("💡 Выполните: git init")
        return False
    
    print("✅ Git инициализирован")
    return True

def check_gitignore():
    """Проверяем .gitignore"""
    print("🔍 Проверяем .gitignore...")
    
    if not os.path.exists('.gitignore'):
        print("❌ Файл .gitignore не найден!")
        return False
    
    with open('.gitignore', 'r', encoding='utf-8') as f:
        gitignore_content = f.read()
    
    required_ignores = ['.env', '*.db', '*.sqlite', '__pycache__']
    missing_ignores = []
    
    for ignore in required_ignores:
        if ignore not in gitignore_content:
            missing_ignores.append(ignore)
    
    if missing_ignores:
        print(f"⚠️ В .gitignore отсутствуют: {', '.join(missing_ignores)}")
        return False
    
    print("✅ .gitignore настроен правильно")
    return True

def check_env_file():
    """Проверяем .env файл"""
    print("🔍 Проверяем .env файл...")
    
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        if 'your_bot_token_here' in env_content or 'test_token' in env_content:
            print("✅ .env содержит тестовый токен (безопасно)")
        else:
            print("⚠️ .env может содержать реальный токен")
            print("💡 Убедитесь, что .env добавлен в .gitignore")
    else:
        print("✅ .env файл отсутствует (безопасно)")
    
    return True

def check_required_files():
    """Проверяем необходимые файлы"""
    print("🔍 Проверяем необходимые файлы...")
    
    required_files = [
        'README.md',
        'requirements.txt',
        'bot.py',
        'config.py',
        'database.py',
        'railway.json',
        'env.production'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Отсутствуют файлы: {', '.join(missing_files)}")
        return False
    
    print("✅ Все необходимые файлы присутствуют")
    return True

def check_documentation():
    """Проверяем документацию"""
    print("🔍 Проверяем документацию...")
    
    docs = [
        'DEPLOYMENT.md',
        'RAILWAY_DEPLOYMENT_GUIDE.md',
        'PRODUCTION_CHECKLIST.md',
        'IMPORTANT_FIXES_REPORT.md'
    ]
    
    missing_docs = []
    for doc in docs:
        if not os.path.exists(doc):
            missing_docs.append(doc)
    
    if missing_docs:
        print(f"⚠️ Отсутствует документация: {', '.join(missing_docs)}")
        return False
    
    print("✅ Документация полная")
    return True

def check_file_sizes():
    """Проверяем размеры файлов"""
    print("🔍 Проверяем размеры файлов...")
    
    large_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.startswith('.'):
                continue
            
            file_path = os.path.join(root, file)
            try:
                size = os.path.getsize(file_path)
                if size > 100 * 1024 * 1024:  # 100MB
                    large_files.append(f"{file_path} ({size // (1024*1024)}MB)")
            except:
                pass
    
    if large_files:
        print(f"⚠️ Большие файлы: {', '.join(large_files)}")
        print("💡 GitHub имеет лимит 100MB на файл")
        return False
    
    print("✅ Размеры файлов в норме")
    return True

def main():
    """Основная функция проверки"""
    print("🎯 Проверка готовности к загрузке на GitHub")
    print("=" * 50)
    
    checks = [
        ("Git статус", check_git_status),
        (".gitignore", check_gitignore),
        (".env файл", check_env_file),
        ("Необходимые файлы", check_required_files),
        ("Документация", check_documentation),
        ("Размеры файлов", check_file_sizes)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n🔍 {check_name}...")
        try:
            if check_func():
                passed += 1
        except Exception as e:
            print(f"❌ Ошибка в {check_name}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Результат: {passed}/{total} проверок пройдено")
    
    if passed == total:
        print("🎉 ГОТОВ К ЗАГРУЗКЕ НА GITHUB!")
        print("\n🚀 Команды для загрузки:")
        print("git init")
        print("git add .")
        print("git commit -m \"Initial commit: Лес и волки Bot ready for production\"")
        print("git remote add origin https://github.com/YOUR_USERNAME/forest-mafia-bot.git")
        print("git push -u origin main")
        return True
    elif passed >= total * 0.8:
        print("⚠️ ПОЧТИ ГОТОВ К ЗАГРУЗКЕ")
        print("🔧 Исправьте оставшиеся проблемы")
        return False
    else:
        print("❌ НЕ ГОТОВ К ЗАГРУЗКЕ")
        print("🛠️ Требуется серьезная доработка")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
