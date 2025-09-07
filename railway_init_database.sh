#!/bin/bash
# Скрипт инициализации базы данных для Railway

echo "🚂 Инициализация базы данных ForestMafia Bot на Railway..."

# Проверяем переменные окружения
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL не установлен!"
    exit 1
fi

echo "✅ DATABASE_URL установлен"

# Запускаем Python скрипт для создания таблиц
python3 -c "
import os
import sys
sys.path.append('.')

from database import init_database, Base
from config import DATABASE_URL

print('🔧 Инициализируем базу данных...')
db_manager = init_database(DATABASE_URL)

print('📋 Создаем таблицы...')
Base.metadata.create_all(db_manager.engine)

print('✅ База данных инициализирована успешно!')
"

echo "🎉 Инициализация завершена!"
