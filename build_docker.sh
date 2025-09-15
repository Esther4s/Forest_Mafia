#!/bin/bash

# Скрипт для сборки Docker образа с retry логикой

echo "🐳 Сборка Docker образа для Forest Mafia Bot..."

# Функция для retry
retry_build() {
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "🔄 Попытка $attempt из $max_attempts..."
        
        if docker build -t forest-mafia-bot .; then
            echo "✅ Сборка успешна!"
            return 0
        else
            echo "❌ Попытка $attempt неудачна"
            if [ $attempt -lt $max_attempts ]; then
                echo "⏳ Ожидание 10 секунд перед следующей попыткой..."
                sleep 10
            fi
            ((attempt++))
        fi
    done
    
    echo "❌ Все попытки неудачны. Пробуем альтернативный Dockerfile..."
    return 1
}

# Пробуем основной Dockerfile
if retry_build; then
    echo "🎉 Сборка завершена успешно!"
    echo "📦 Образ: forest-mafia-bot"
    echo "🚀 Для запуска: docker run -d --name forest-mafia forest-mafia-bot"
else
    echo "🔄 Пробуем альтернативный Dockerfile с Ubuntu..."
    if docker build -f Dockerfile.ubuntu -t forest-mafia-bot .; then
        echo "✅ Сборка с Ubuntu успешна!"
        echo "📦 Образ: forest-mafia-bot"
        echo "🚀 Для запуска: docker run -d --name forest-mafia forest-mafia-bot"
    else
        echo "❌ Обе попытки сборки неудачны"
        echo "💡 Попробуйте:"
        echo "   1. Проверить подключение к интернету"
        echo "   2. Очистить Docker кэш: docker system prune -a"
        echo "   3. Перезапустить Docker"
        exit 1
    fi
fi
