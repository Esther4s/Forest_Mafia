#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для проверки HTML-форматирования во всех сообщениях бота
"""

import re

def check_html_formatting():
    """Проверяет все места с HTML-тегами в bot.py"""
    print("🔍 ПРОВЕРКА HTML-ФОРМАТИРОВАНИЯ В БОТЕ")
    print("=" * 50)
    
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Находим все строки с HTML-тегами
    html_pattern = r'<[^>]+>'
    lines = content.split('\n')
    
    issues = []
    html_lines = []
    
    for i, line in enumerate(lines, 1):
        if re.search(html_pattern, line):
            html_lines.append((i, line.strip()))
    
    print(f"📊 Найдено строк с HTML-тегами: {len(html_lines)}")
    print()
    
    # Проверяем каждую строку с HTML-тегами
    for line_num, line in html_lines:
        # Ищем reply_text или edit_message_text в этой строке или следующих
        is_reply_text = 'reply_text' in line
        is_edit_text = 'edit_message_text' in line
        
        # Если это не вызов функции, проверяем следующие строки
        if not (is_reply_text or is_edit_text):
            # Ищем в следующих 3 строках
            for j in range(1, 4):
                if line_num + j - 1 < len(lines):
                    next_line = lines[line_num + j - 1]
                    if 'reply_text' in next_line or 'edit_message_text' in next_line:
                        is_reply_text = 'reply_text' in next_line
                        is_edit_text = 'edit_message_text' in next_line
                        break
        
        if is_reply_text or is_edit_text:
            # Проверяем, есть ли parse_mode='HTML'
            if 'parse_mode' not in line:
                # Проверяем следующие строки
                has_parse_mode = False
                for j in range(1, 5):
                    if line_num + j - 1 < len(lines):
                        next_line = lines[line_num + j - 1]
                        if 'parse_mode' in next_line and 'HTML' in next_line:
                            has_parse_mode = True
                            break
                
                if not has_parse_mode:
                    issues.append((line_num, line))
    
    # Выводим результаты
    if issues:
        print("❌ НАЙДЕНЫ ПРОБЛЕМЫ С HTML-ФОРМАТИРОВАНИЕМ:")
        print()
        for line_num, line in issues:
            print(f"Строка {line_num}: {line}")
            print()
    else:
        print("✅ ВСЕ HTML-ТЕГИ КОРРЕКТНО ФОРМАТИРОВАНЫ!")
        print("Все сообщения с HTML-тегами имеют parse_mode='HTML'")
    
    print(f"\n📈 Статистика:")
    print(f"Всего строк с HTML-тегами: {len(html_lines)}")
    print(f"Проблемных строк: {len(issues)}")
    
    return len(issues) == 0

if __name__ == "__main__":
    success = check_html_formatting()
    exit(0 if success else 1)
