#!/usr/bin/env python3
"""
Скрипт для развертывания улучшенной системы активных эффектов в Railway
"""

import os
import sys
import logging
import subprocess
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_railway_cli():
    """Проверяет установлен ли Railway CLI"""
    try:
        result = subprocess.run(['railway', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ Railway CLI установлен: {result.stdout.strip()}")
            return True
        else:
            logger.error("❌ Railway CLI не найден")
            return False
    except FileNotFoundError:
        logger.error("❌ Railway CLI не установлен")
        return False

def check_railway_project():
    """Проверяет подключение к проекту Railway"""
    try:
        result = subprocess.run(['railway', 'status'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Подключение к Railway проекту успешно")
            logger.info(f"Статус: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"❌ Ошибка подключения к Railway: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка проверки Railway проекта: {e}")
        return False

def update_database_psycopg2():
    """Обновляет database_psycopg2.py с новыми функциями"""
    logger.info("🔧 Обновляем database_psycopg2.py...")
    
    try:
        # Читаем оригинальный файл
        with open('database_psycopg2.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Читаем новые функции
        with open('enhanced_active_effects_functions.py', 'r', encoding='utf-8') as f:
            enhanced_functions = f.read()
        
        # Извлекаем только функции (без импортов и main)
        lines = enhanced_functions.split('\n')
        function_lines = []
        in_function = False
        
        for line in lines:
            if line.startswith('def ') and not line.startswith('def main'):
                in_function = True
                function_lines.append(line)
            elif in_function:
                if line.startswith('def ') and line.startswith('def main'):
                    break
                function_lines.append(line)
        
        enhanced_functions_code = '\n'.join(function_lines)
        
        # Находим место для вставки (после последней функции active_effects)
        insert_marker = "def cleanup_expired_effects() -> int:"
        insert_position = content.find(insert_marker)
        
        if insert_position == -1:
            logger.error("❌ Не найдено место для вставки функций")
            return False
        
        # Находим конец последней функции
        end_marker = "        return 0"
        end_position = content.find(end_marker, insert_position) + len(end_marker)
        
        # Вставляем новые функции
        new_content = (
            content[:end_position] + 
            "\n\n# ===== УЛУЧШЕННЫЕ ФУНКЦИИ АКТИВНЫХ ЭФФЕКТОВ =====\n\n" +
            enhanced_functions_code + 
            "\n\n# ===== КОНЕЦ УЛУЧШЕННЫХ ФУНКЦИЙ =====\n" +
            content[end_position:]
        )
        
        # Записываем обновленный файл
        with open('database_psycopg2.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info("✅ database_psycopg2.py обновлен")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления database_psycopg2.py: {e}")
        return False

def create_railway_startup_script():
    """Создает скрипт запуска для Railway с обновлением БД"""
    
    startup_script = '''#!/bin/bash
# Скрипт запуска для Railway с обновлением системы активных эффектов

echo "🚀 Запуск Forest Mafia Bot с улучшенной системой активных эффектов..."

# Проверяем подключение к базе данных
echo "🔌 Проверяем подключение к базе данных..."
python3 -c "
import sys
sys.path.append('.')
try:
    from database_psycopg2 import get_database_connection
    conn = get_database_connection()
    if conn:
        print('✅ Подключение к БД успешно')
        conn.close()
    else:
        print('❌ Ошибка подключения к БД')
        sys.exit(1)
except Exception as e:
    print(f'❌ Ошибка БД: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Не удалось подключиться к базе данных"
    exit 1
fi

# Обновляем структуру таблицы active_effects
echo "🔧 Обновляем структуру таблицы active_effects..."
python3 -c "
import sys
sys.path.append('.')
try:
    from improve_active_effects_table import improve_active_effects_table
    if improve_active_effects_table():
        print('✅ Структура таблицы обновлена')
    else:
        print('⚠️ Не удалось обновить структуру таблицы')
except Exception as e:
    print(f'⚠️ Ошибка обновления таблицы: {e}')
"

# Запускаем основной бот
echo "🤖 Запускаем Forest Mafia Bot..."
python3 bot.py
'''
    
    try:
        with open('railway_startup.sh', 'w', encoding='utf-8') as f:
            f.write(startup_script)
        
        # Делаем файл исполняемым
        os.chmod('railway_startup.sh', 0o755)
        
        logger.info("✅ Создан скрипт запуска railway_startup.sh")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания скрипта запуска: {e}")
        return False

def create_railway_json():
    """Создает railway.json с новыми настройками"""
    
    railway_config = {
        "$schema": "https://railway.app/railway.schema.json",
        "build": {
            "builder": "NIXPACKS"
        },
        "deploy": {
            "startCommand": "bash railway_startup.sh",
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 3
        }
    }
    
    try:
        import json
        with open('railway.json', 'w', encoding='utf-8') as f:
            json.dump(railway_config, f, indent=2, ensure_ascii=False)
        
        logger.info("✅ Создан railway.json с новыми настройками")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания railway.json: {e}")
        return False

def update_requirements():
    """Обновляет requirements.txt если нужно"""
    logger.info("📦 Проверяем requirements.txt...")
    
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            requirements = f.read()
        
        # Проверяем, есть ли все необходимые зависимости
        required_packages = [
            'psycopg2-binary',
            'python-telegram-bot',
            'python-dotenv'
        ]
        
        missing_packages = []
        for package in required_packages:
            if package not in requirements:
                missing_packages.append(package)
        
        if missing_packages:
            logger.info(f"📦 Добавляем недостающие пакеты: {missing_packages}")
            with open('requirements.txt', 'a', encoding='utf-8') as f:
                f.write('\n# Дополнительные пакеты для системы активных эффектов\n')
                for package in missing_packages:
                    f.write(f'{package}\n')
            logger.info("✅ requirements.txt обновлен")
        else:
            logger.info("✅ Все необходимые пакеты уже присутствуют")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления requirements.txt: {e}")
        return False

def deploy_to_railway():
    """Развертывает обновления в Railway"""
    logger.info("🚀 Развертываем обновления в Railway...")
    
    try:
        # Добавляем все файлы в git
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Коммитим изменения
        commit_message = f"🚀 Railway: Обновление системы активных эффектов - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        
        # Пушим в Railway
        subprocess.run(['git', 'push', 'origin', 'master'], check=True)
        
        logger.info("✅ Изменения успешно развернуты в Railway")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Ошибка развертывания в Railway: {e}")
        return False

def create_railway_environment_setup():
    """Создает скрипт для настройки переменных окружения Railway"""
    
    env_setup = '''#!/bin/bash
# Настройка переменных окружения для Railway

echo "🔧 Настройка переменных окружения Railway..."

# Проверяем наличие переменных
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL не установлена"
    exit 1
fi

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN не установлен"
    exit 1
fi

echo "✅ Переменные окружения настроены"
echo "📊 DATABASE_URL: ${DATABASE_URL:0:20}..."
echo "🤖 BOT_TOKEN: ${BOT_TOKEN:0:10}..."

# Создаем файл database_url.txt для совместимости
echo "$DATABASE_URL" > database_url.txt

echo "✅ Настройка завершена"
'''
    
    try:
        with open('railway_env_setup.sh', 'w', encoding='utf-8') as f:
            f.write(env_setup)
        
        os.chmod('railway_env_setup.sh', 0o755)
        
        logger.info("✅ Создан скрипт настройки окружения railway_env_setup.sh")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания скрипта окружения: {e}")
        return False

def main():
    """Основная функция развертывания"""
    logger.info("🚀 Начинаем развертывание улучшенной системы активных эффектов в Railway...")
    
    # 1. Проверяем Railway CLI
    if not check_railway_cli():
        logger.error("❌ Установите Railway CLI: https://docs.railway.app/develop/cli")
        return False
    
    # 2. Проверяем подключение к проекту
    if not check_railway_project():
        logger.error("❌ Подключитесь к Railway проекту: railway login && railway link")
        return False
    
    # 3. Обновляем database_psycopg2.py
    if not update_database_psycopg2():
        logger.error("❌ Не удалось обновить database_psycopg2.py")
        return False
    
    # 4. Создаем скрипт запуска
    if not create_railway_startup_script():
        logger.error("❌ Не удалось создать скрипт запуска")
        return False
    
    # 5. Создаем railway.json
    if not create_railway_json():
        logger.error("❌ Не удалось создать railway.json")
        return False
    
    # 6. Обновляем requirements.txt
    if not update_requirements():
        logger.error("❌ Не удалось обновить requirements.txt")
        return False
    
    # 7. Создаем скрипт настройки окружения
    if not create_railway_environment_setup():
        logger.error("❌ Не удалось создать скрипт окружения")
        return False
    
    # 8. Развертываем в Railway
    if not deploy_to_railway():
        logger.error("❌ Не удалось развернуть в Railway")
        return False
    
    logger.info("\n🎉 Развертывание завершено!")
    logger.info("\n📝 Что было сделано:")
    logger.info("• Обновлен database_psycopg2.py с новыми функциями")
    logger.info("• Создан railway_startup.sh для автоматического обновления БД")
    logger.info("• Создан railway.json с новыми настройками")
    logger.info("• Обновлен requirements.txt")
    logger.info("• Создан railway_env_setup.sh для настройки окружения")
    logger.info("• Изменения развернуты в Railway")
    
    logger.info("\n🔧 Следующие шаги:")
    logger.info("1. Проверьте логи в Railway Dashboard")
    logger.info("2. Убедитесь, что переменные окружения настроены")
    logger.info("3. Протестируйте бота в Telegram")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
