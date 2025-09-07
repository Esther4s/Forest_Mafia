#!/bin/bash

# Скрипт для деплоя ForestMafia бота в продакшен

set -e

echo "🚀 Начинаем деплой ForestMafia бота..."

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

# Создаем директории для данных
echo "📁 Создаем директории для данных..."
mkdir -p data logs

echo "✅ Проверка конфигурации пройдена"

# Останавливаем существующий контейнер
echo "🛑 Останавливаем существующий контейнер..."
docker-compose down || true
docker-compose -f docker-compose.sqlite.yml down || true

# Выбираем конфигурацию базы данных
if grep -q "postgresql://" .env; then
    echo "🐘 Используем PostgreSQL..."
    COMPOSE_FILE="docker-compose.yml"
else
    echo "🗃️ Используем SQLite..."
    COMPOSE_FILE="docker-compose.sqlite.yml"
fi

# Собираем новый образ
echo "🔨 Собираем Docker образ..."
docker-compose -f $COMPOSE_FILE build --no-cache

# Запускаем бота
echo "🚀 Запускаем бота..."
docker-compose -f $COMPOSE_FILE up -d

# Проверяем статус
echo "📊 Проверяем статус..."
sleep 5
docker-compose -f $COMPOSE_FILE ps

echo "✅ Деплой завершен!"
echo "📋 Для просмотра логов используйте: docker-compose -f $COMPOSE_FILE logs -f"
echo "🛑 Для остановки используйте: docker-compose -f $COMPOSE_FILE down"
