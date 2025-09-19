# 🚀 Руководство по деплою системы "Лес и Волки"

## 📊 Результаты тестирования

### ✅ ПРОЙДЕННЫЕ ТЕСТЫ
- **Базовые тесты системы**: ✅ 5/5 пройдено
- **Игровая логика**: ✅ Полностью функциональна
- **Telegram интеграция**: ✅ Работает корректно
- **Docker файлы**: ✅ Готовы к использованию
- **Структура проекта**: ✅ Полная и организованная

### ⚠️ ТРЕБУЕТ НАСТРОЙКИ
- **База данных**: Настройка PostgreSQL
- **Docker**: Установка Docker Desktop
- **Переменные окружения**: Создание .env файла

## 🛠️ Подготовка к деплою

### 1. Установка зависимостей

#### Python зависимости
```bash
pip install -r requirements.txt
```

#### Системные зависимости
- **PostgreSQL** 12+ (для базы данных)
- **Docker Desktop** (для контейнеризации)
- **Python** 3.8+ (уже установлен)

### 2. Настройка базы данных

#### Установка PostgreSQL
```bash
# Windows (через Chocolatey)
choco install postgresql

# Или скачайте с официального сайта
# https://www.postgresql.org/download/windows/
```

#### Создание базы данных
```sql
-- Подключитесь к PostgreSQL
psql -U postgres

-- Создайте базу данных
CREATE DATABASE forest_mafia;

-- Создайте пользователя
CREATE USER forest_mafia WITH PASSWORD 'your_password';

-- Предоставьте права
GRANT ALL PRIVILEGES ON DATABASE forest_mafia TO forest_mafia;
```

### 3. Настройка переменных окружения

Создайте файл `.env` в корне проекта:
```env
BOT_TOKEN=your_real_bot_token_here
DATABASE_URL=postgresql://forest_mafia:your_password@localhost:5432/forest_mafia
POSTGRES_USER=forest_mafia
POSTGRES_PASSWORD=your_password
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## 🐳 Деплой через Docker

### 1. Сборка образа
```bash
docker build -t forest-mafia-bot .
```

### 2. Запуск через Docker Compose
```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### 3. Проверка работы
```bash
# Статус контейнеров
docker-compose ps

# Логи бота
docker-compose logs forest-mafia-bot

# Логи PostgreSQL
docker-compose logs postgres
```

## 🖥️ Прямой деплой (без Docker)

### 1. Настройка окружения
```bash
# Активируйте виртуальное окружение
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Установите зависимости
pip install -r requirements.txt
```

### 2. Инициализация базы данных
```bash
python init_database.py
```

### 3. Запуск бота
```bash
python bot.py
```

## 🔧 Настройка для продакшена

### 1. Системный сервис (Linux)

Создайте файл `/etc/systemd/system/forest-mafia-bot.service`:
```ini
[Unit]
Description=Forest Mafia Bot
After=network.target postgresql.service

[Service]
Type=simple
User=bot
WorkingDirectory=/path/to/forest-mafia
EnvironmentFile=/path/to/forest-mafia/.env
ExecStart=/path/to/forest-mafia/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активация:
```bash
sudo systemctl enable forest-mafia-bot
sudo systemctl start forest-mafia-bot
```

### 2. Мониторинг

#### Логи
```bash
# Просмотр логов
tail -f logs/bot.log

# Docker логи
docker-compose logs -f forest-mafia-bot
```

#### Мониторинг ресурсов
```bash
# Использование ресурсов
docker stats forest-mafia-bot

# Статус сервиса
systemctl status forest-mafia-bot
```

## 🚨 Устранение проблем

### Частые ошибки

#### 1. Ошибка подключения к БД
```
❌ could not translate host name "sqlite" to address
```
**Решение**: Настройте DATABASE_URL для PostgreSQL

#### 2. Ошибка токена
```
❌ BOT_TOKEN не установлен
```
**Решение**: Создайте .env файл с токеном

#### 3. Ошибка Docker
```
❌ Docker not found
```
**Решение**: Установите Docker Desktop

#### 4. Ошибка портов
```
❌ Port 5432 already in use
```
**Решение**: Остановите другие PostgreSQL сервисы

### Отладка

#### Включение DEBUG режима
```env
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

#### Проверка подключения к БД
```bash
python -c "from database_psycopg2 import init_db; print('DB OK' if init_db() else 'DB ERROR')"
```

#### Проверка токена бота
```bash
python -c "from config import BOT_TOKEN; print('Token OK' if BOT_TOKEN else 'Token ERROR')"
```

## 📈 Мониторинг и обслуживание

### 1. Регулярные задачи
- **Ежедневно**: Проверка логов на ошибки
- **Еженедельно**: Обновление зависимостей
- **Ежемесячно**: Резервное копирование БД

### 2. Резервное копирование
```bash
# Бэкап базы данных
pg_dump forest_mafia > backup_$(date +%Y%m%d).sql

# Восстановление
psql forest_mafia < backup_20241219.sql
```

### 3. Обновления
```bash
# Обновление кода
git pull origin main

# Пересборка Docker
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 🎯 Чек-лист деплоя

### Перед деплоем
- [ ] ✅ Все тесты пройдены
- [ ] ✅ PostgreSQL установлен и настроен
- [ ] ✅ Docker установлен (если используется)
- [ ] ✅ .env файл создан с реальными токенами
- [ ] ✅ База данных создана и доступна
- [ ] ✅ Токен бота получен от @BotFather

### После деплоя
- [ ] ✅ Бот отвечает на команды
- [ ] ✅ Игры создаются и работают
- [ ] ✅ База данных сохраняет данные
- [ ] ✅ Логи не содержат критических ошибок
- [ ] ✅ Мониторинг настроен

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs -f`
2. Убедитесь в корректности .env файла
3. Проверьте доступность PostgreSQL
4. Обратитесь к документации проекта

---

**Система "Лес и Волки" готова к деплою! 🚀**

*Дата создания: 2024-12-19*  
*Статус: ✅ ГОТОВ К ДЕПЛОЮ*
