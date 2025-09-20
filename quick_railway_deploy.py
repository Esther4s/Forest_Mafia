#!/usr/bin/env python3
"""
Быстрое развертывание улучшенной системы активных эффектов в Railway
"""

import os
import subprocess
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def quick_deploy():
    """Быстрое развертывание в Railway"""
    logger.info("🚀 Быстрое развертывание в Railway...")
    
    try:
        # 1. Обновляем database_psycopg2.py
        logger.info("1. Обновляем database_psycopg2.py...")
        subprocess.run([sys.executable, 'integrate_enhanced_effects.py'], check=True)
        
        # 2. Создаем простой скрипт запуска
        startup_script = '''#!/bin/bash
echo "🚀 Запуск Forest Mafia Bot с улучшенными эффектами..."

# Обновляем БД при запуске
python3 -c "
try:
    from improve_active_effects_table import improve_active_effects_table
    improve_active_effects_table()
    print('✅ БД обновлена')
except Exception as e:
    print(f'⚠️ Ошибка БД: {e}')
"

# Запускаем бота
python3 bot.py
'''
        
        with open('start.sh', 'w', encoding='utf-8') as f:
            f.write(startup_script)
        os.chmod('start.sh', 0o755)
        
        # 3. Создаем Procfile для Railway
        with open('Procfile', 'w', encoding='utf-8') as f:
            f.write('web: bash start.sh\n')
        
        # 4. Коммитим и пушим
        logger.info("2. Коммитим изменения...")
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', '🚀 Railway: Быстрое обновление системы эффектов'], check=True)
        
        logger.info("3. Пушим в Railway...")
        subprocess.run(['git', 'push', 'origin', 'master'], check=True)
        
        logger.info("✅ Быстрое развертывание завершено!")
        logger.info("🔍 Проверьте логи в Railway Dashboard")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Ошибка развертывания: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = quick_deploy()
    sys.exit(0 if success else 1)
