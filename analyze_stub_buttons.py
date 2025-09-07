#!/usr/bin/env python3
"""
Скрипт для анализа кнопок с заглушками в боте
"""

import re
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def analyze_bot_buttons():
    """Анализирует все кнопки в боте и находит заглушки"""
    
    print("🔍 Анализ кнопок бота на предмет заглушек...")
    
    # Читаем файл бота
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Находим все кнопки с callback_data
    button_pattern = r'InlineKeyboardButton\([^,]+,\s*callback_data="([^"]+)"\)'
    buttons = re.findall(button_pattern, content)
    
    print(f"📋 Найдено {len(buttons)} кнопок с callback_data")
    
    # Находим все обработчики callback'ов
    handler_pattern = r'def handle_([^(]+)\([^)]*\):'
    handlers = re.findall(handler_pattern, content)
    
    print(f"🔧 Найдено {len(handlers)} обработчиков")
    
    # Группируем кнопки по типам
    button_groups = {
        'welcome': [],
        'game_control': [],
        'settings': [],
        'timers': [],
        'roles': [],
        'voting': [],
        'night_actions': [],
        'day_actions': [],
        'other': []
    }
    
    for button in buttons:
        if button.startswith('welcome_'):
            button_groups['welcome'].append(button)
        elif button in ['join_game', 'start_game', 'leave_registration', 'cancel_game', 'end_game']:
            button_groups['game_control'].append(button)
        elif button.startswith('settings_'):
            button_groups['settings'].append(button)
        elif button.startswith('timer_') or button.startswith('set_'):
            button_groups['timers'].append(button)
        elif button.startswith('role_'):
            button_groups['roles'].append(button)
        elif button.startswith('vote_') or button.startswith('wolf_vote_'):
            button_groups['voting'].append(button)
        elif button.startswith('night_'):
            button_groups['night_actions'].append(button)
        elif button.startswith('day_'):
            button_groups['day_actions'].append(button)
        else:
            button_groups['other'].append(button)
    
    # Анализируем каждую группу
    print("\n📊 Анализ групп кнопок:")
    
    for group_name, group_buttons in button_groups.items():
        if group_buttons:
            print(f"\n🔹 {group_name.upper()} ({len(group_buttons)} кнопок):")
            for button in group_buttons:
                print(f"  • {button}")
    
    # Проверяем, какие кнопки могут быть заглушками
    print("\n🚨 ПОТЕНЦИАЛЬНЫЕ ЗАГЛУШКИ:")
    
    potential_stubs = []
    
    # Проверяем кнопки настроек ролей
    role_buttons = [b for b in buttons if b.startswith('role_')]
    if role_buttons:
        print(f"\n🎭 Кнопки настроек ролей (возможно заглушки):")
        for button in role_buttons:
            print(f"  • {button}")
            potential_stubs.append({
                'button': button,
                'type': 'role_settings',
                'description': 'Настройка распределения ролей',
                'priority': 'medium'
            })
    
    # Проверяем кнопки таймеров
    timer_buttons = [b for b in buttons if b.startswith('set_')]
    if timer_buttons:
        print(f"\n⏱️ Кнопки настройки таймеров (возможно заглушки):")
        for button in timer_buttons:
            print(f"  • {button}")
            potential_stubs.append({
                'button': button,
                'type': 'timer_settings',
                'description': 'Настройка длительности фаз игры',
                'priority': 'medium'
            })
    
    # Проверяем кнопки глобальных настроек
    global_settings_buttons = [b for b in buttons if b.startswith('settings_global')]
    if global_settings_buttons:
        print(f"\n🌐 Кнопки глобальных настроек (возможно заглушки):")
        for button in global_settings_buttons:
            print(f"  • {button}")
            potential_stubs.append({
                'button': button,
                'type': 'global_settings',
                'description': 'Глобальные настройки бота',
                'priority': 'low'
            })
    
    # Проверяем кнопки сброса статистики
    reset_buttons = [b for b in buttons if 'reset' in b]
    if reset_buttons:
        print(f"\n📊 Кнопки сброса статистики (возможно заглушки):")
        for button in reset_buttons:
            print(f"  • {button}")
            potential_stubs.append({
                'button': button,
                'type': 'reset_stats',
                'description': 'Сброс статистики игры',
                'priority': 'low'
            })
    
    # Проверяем кнопки ночных действий
    night_buttons = [b for b in buttons if b.startswith('night_')]
    if night_buttons:
        print(f"\n🌙 Кнопки ночных действий (возможно заглушки):")
        for button in night_buttons:
            print(f"  • {button}")
            potential_stubs.append({
                'button': button,
                'type': 'night_actions',
                'description': 'Ночные действия игроков',
                'priority': 'high'
            })
    
    return potential_stubs

def check_handler_implementation():
    """Проверяет реализацию обработчиков"""
    
    print("\n🔍 Проверка реализации обработчиков...")
    
    # Читаем файл бота
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Список обработчиков, которые могут быть заглушками
    handlers_to_check = [
        'handle_timer_values',
        'handle_role_settings', 
        'show_global_settings',
        'reset_game_stats',
        'toggle_test_mode',
        'show_night_duration_options',
        'show_day_duration_options',
        'show_vote_duration_options'
    ]
    
    print("\n🔧 Проверка обработчиков:")
    
    for handler in handlers_to_check:
        # Ищем определение метода
        pattern = rf'async def {handler}\([^)]*\):'
        if re.search(pattern, content):
            print(f"  ✅ {handler} - найден")
            
            # Ищем содержимое метода
            method_pattern = rf'async def {handler}\([^)]*\):(.*?)(?=async def|\Z)'
            match = re.search(method_pattern, content, re.DOTALL)
            if match:
                method_content = match.group(1)
                
                # Проверяем на заглушки
                if 'pass' in method_content or 'NotImplemented' in method_content:
                    print(f"    🚨 {handler} - содержит заглушку!")
                elif len(method_content.strip()) < 100:
                    print(f"    ⚠️ {handler} - возможно неполная реализация")
                else:
                    print(f"    ✅ {handler} - реализован")
        else:
            print(f"  ❌ {handler} - не найден")

def main():
    """Основная функция"""
    print("🚀 Анализ кнопок с заглушками в боте 'Лес и Волки'")
    print("=" * 60)
    
    # Анализируем кнопки
    potential_stubs = analyze_bot_buttons()
    
    # Проверяем обработчики
    check_handler_implementation()
    
    # Выводим итоговый список заглушек
    print("\n" + "=" * 60)
    print("📋 ИТОГОВЫЙ СПИСОК ПОТЕНЦИАЛЬНЫХ ЗАГЛУШЕК:")
    print("=" * 60)
    
    if potential_stubs:
        for i, stub in enumerate(potential_stubs, 1):
            priority_emoji = {
                'high': '🔴',
                'medium': '🟡', 
                'low': '🟢'
            }
            print(f"{i}. {priority_emoji.get(stub['priority'], '⚪')} {stub['button']}")
            print(f"   Тип: {stub['type']}")
            print(f"   Описание: {stub['description']}")
            print(f"   Приоритет: {stub['priority']}")
            print()
    else:
        print("✅ Потенциальных заглушек не найдено!")
    
    print("🎯 Рекомендации для разработки:")
    print("1. 🔴 Высокий приоритет - ночные действия игроков")
    print("2. 🟡 Средний приоритет - настройки ролей и таймеров")
    print("3. 🟢 Низкий приоритет - глобальные настройки и сброс статистики")

if __name__ == "__main__":
    main()
