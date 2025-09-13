#!/bin/bash

# Скрипт для деплоя Лес и волки Bot в продакшен
# Использование: ./deploy_production.sh

set -e  # Остановить при ошибке

echo "🚀 Начинаем деплой Лес и волки Bot в продакшен..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для логирования
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Проверка переменных окружения
check_env() {
    log "Проверяем переменные окружения..."
    
    if [ -z "$BOT_TOKEN" ]; then
        error "BOT_TOKEN не установлен!"
    fi
    
    if [ -z "$DATABASE_URL" ]; then
        error "DATABASE_URL не установлен!"
    fi
    
    log "✅ Переменные окружения настроены"
}

# Проверка зависимостей
check_dependencies() {
    log "Проверяем зависимости..."
    
    if ! command -v python3 &> /dev/null; then
        error "Python3 не установлен!"
    fi
    
    if ! command -v pip3 &> /dev/null; then
        error "pip3 не установлен!"
    fi
    
    log "✅ Зависимости проверены"
}

# Установка зависимостей
install_dependencies() {
    log "Устанавливаем зависимости..."
    
    pip3 install -r requirements.txt --no-cache-dir
    
    log "✅ Зависимости установлены"
}

# Проверка базы данных
check_database() {
    log "Проверяем подключение к базе данных..."
    
    python3 -c "
import os
import psycopg2
from urllib.parse import urlparse

try:
    url = urlparse(os.environ['DATABASE_URL'])
    conn = psycopg2.connect(
        host=url.hostname,
        port=url.port,
        database=url.path[1:],
        user=url.username,
        password=url.password
    )
    conn.close()
    print('✅ Подключение к базе данных успешно')
except Exception as e:
    print(f'❌ Ошибка подключения к базе данных: {e}')
    exit(1)
"
    
    log "✅ База данных доступна"
}

# Применение миграций
run_migrations() {
    log "Применяем миграции базы данных..."
    
    # Проверяем, есть ли миграции
    if [ -d "alembic/versions" ] && [ "$(ls -A alembic/versions)" ]; then
        alembic upgrade head
        log "✅ Миграции применены"
    else
        warning "Миграции не найдены, создаем схему вручную..."
        python3 -c "
import os
import psycopg2
from urllib.parse import urlparse

# Читаем схему
with open('fixed_database_schema.sql', 'r', encoding='utf-8') as f:
    schema = f.read()

# Подключаемся к базе
url = urlparse(os.environ['DATABASE_URL'])
conn = psycopg2.connect(
    host=url.hostname,
    port=url.port,
    database=url.path[1:],
    user=url.username,
    password=url.password
)

# Выполняем схему
with conn.cursor() as cur:
    cur.execute(schema)
    conn.commit()

conn.close()
print('✅ Схема базы данных создана')
"
        log "✅ Схема базы данных создана"
    fi
}

# Проверка кода
check_code() {
    log "Проверяем код на ошибки..."
    
    # Проверяем синтаксис Python
    python3 -m py_compile bot.py
    
    # Проверяем импорты
    python3 -c "
import sys
sys.path.append('.')
try:
    import bot
    print('✅ Импорты работают корректно')
except ImportError as e:
    print(f'❌ Ошибка импорта: {e}')
    sys.exit(1)
"
    
    log "✅ Код проверен"
}

# Создание systemd сервиса
create_systemd_service() {
    log "Создаем systemd сервис..."
    
    cat > /etc/systemd/system/forest-mafia-bot.service << EOF
[Unit]
Description=Лес и волки Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$(pwd)
Environment=PATH=$(which python3)
EnvironmentFile=$(pwd)/.env
ExecStart=$(which python3) $(pwd)/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    log "✅ Systemd сервис создан"
}

# Запуск сервиса
start_service() {
    log "Запускаем сервис..."
    
    systemctl enable forest-mafia-bot
    systemctl start forest-mafia-bot
    
    # Ждем запуска
    sleep 5
    
    # Проверяем статус
    if systemctl is-active --quiet forest-mafia-bot; then
        log "✅ Сервис запущен успешно"
    else
        error "❌ Ошибка запуска сервиса"
    fi
}

# Проверка работы бота
test_bot() {
    log "Тестируем работу бота..."
    
    # Проверяем логи
    if journalctl -u forest-mafia-bot --since "1 minute ago" | grep -q "✅"; then
        log "✅ Бот работает корректно"
    else
        warning "⚠️ Проверьте логи: journalctl -u forest-mafia-bot -f"
    fi
}

# Основная функция
main() {
    log "🌲 Лес и волки Bot - Деплой в продакшен"
    log "========================================"
    
    check_env
    check_dependencies
    install_dependencies
    check_database
    run_migrations
    check_code
    create_systemd_service
    start_service
    test_bot
    
    log "🎉 Деплой завершен успешно!"
    log "📊 Статус сервиса: systemctl status forest-mafia-bot"
    log "📋 Логи: journalctl -u forest-mafia-bot -f"
    log "🔄 Перезапуск: systemctl restart forest-mafia-bot"
}

# Запуск
main "$@"
