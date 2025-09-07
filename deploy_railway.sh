#!/bin/bash

# Скрипт для быстрого деплоя ForestMafia Bot на Railway

set -e

echo "🚀 Деплой ForestMafia Bot на Railway..."

# Проверяем наличие Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI не установлен!"
    echo "📥 Установите Railway CLI:"
    echo "   npm install -g @railway/cli"
    echo "   или"
    echo "   curl -fsSL https://railway.app/install.sh | sh"
    exit 1
fi

# Проверяем авторизацию
if ! railway whoami &> /dev/null; then
    echo "🔐 Авторизуйтесь в Railway:"
    railway login
fi

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте файл .env на основе env.production"
    echo "   cp env.production .env"
    echo "   # Затем отредактируйте .env и добавьте ваш BOT_TOKEN"
    exit 1
fi

# Проверяем наличие BOT_TOKEN
if ! grep -q "BOT_TOKEN=" .env || grep -q "BOT_TOKEN=your_bot_token_here" .env; then
    echo "❌ BOT_TOKEN не установлен в .env файле!"
    echo "📝 Добавьте ваш токен бота в .env файл"
    exit 1
fi

echo "✅ Проверка конфигурации пройдена"

# Инициализируем Railway проект
echo "🚂 Инициализируем Railway проект..."
railway init

# Создаем PostgreSQL базу данных
echo "🗄️ Создаем PostgreSQL базу данных..."
railway add postgresql

# Деплоим приложение
echo "🚀 Деплоим приложение..."
railway up

# Получаем URL базы данных
echo "🔗 Получаем URL базы данных..."
DATABASE_URL=$(railway variables --service postgresql | grep DATABASE_URL | cut -d'=' -f2-)

# Устанавливаем переменные окружения
echo "⚙️ Настраиваем переменные окружения..."
railway variables set BOT_TOKEN=$(grep BOT_TOKEN .env | cut -d'=' -f2-)
railway variables set ENVIRONMENT=production
railway variables set LOG_LEVEL=INFO
railway variables set DATABASE_URL=$DATABASE_URL

echo "✅ Деплой завершен!"
echo "🌐 Ваш бот доступен по адресу:"
railway domain

echo "📋 Полезные команды:"
echo "   railway logs - просмотр логов"
echo "   railway status - статус приложения"
echo "   railway variables - переменные окружения"
echo "   railway connect postgresql - подключение к БД"
