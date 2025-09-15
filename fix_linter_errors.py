#!/usr/bin/env python3
"""
Скрипт для исправления ошибок линтера в bot.py
"""

import re

def fix_linter_errors():
    """Исправляет ошибки линтера в bot.py"""
    
    print("🔧 Исправление ошибок линтера в bot.py...")
    
    # Читаем файл
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Исправления
    fixes = [
        # Исправляем f-string без placeholders
        (r'f"([^"]*)"', lambda m: f'"{m.group(1)}"' if '{' not in m.group(1) else m.group(0)),
        
        # Исправляем неиспользуемые переменные
        (r'except Exception as e:\s*\n\s*logger\.error\(f"[^"]*{e}[^"]*"\)', 
         lambda m: m.group(0).replace(' as e:', ':')),
        
        # Исправляем проблемы с типами в callback query
        (r'query\.answer\(\)', 'await query.answer()'),
        (r'query\.edit_message_text\(', 'await query.edit_message_text('),
        (r'query\.data', 'query.data if query else None'),
    ]
    
    # Применяем исправления
    for pattern, replacement in fixes:
        if callable(replacement):
            content = re.sub(pattern, replacement, content)
        else:
            content = re.sub(pattern, replacement, content)
    
    # Записываем исправленный файл
    with open('bot.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Исправления применены!")

if __name__ == "__main__":
    fix_linter_errors()
