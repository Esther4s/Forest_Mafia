#!/bin/bash

# Скрипт развертывания расширенной системы лесов на Railway

echo "🌲 Развертывание расширенной системы лесов на Railway"
echo "=================================================="

# Проверяем наличие Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI не установлен"
    echo "Установите: npm install -g @railway/cli"
    exit 1
fi

# Проверяем авторизацию
if ! railway whoami &> /dev/null; then
    echo "🔐 Авторизация в Railway..."
    railway login
fi

# Применяем миграции
echo "🗄️ Применение миграций базы данных..."
python apply_forest_migration.py

# Тестируем систему
echo "🧪 Тестирование системы..."
python test_enhanced_forest_system.py

# Развертываем на Railway
echo "🚀 Развертывание на Railway..."
railway up

echo "✅ Развертывание завершено!"
echo "🌲 Расширенная система лесов активна на Railway"
