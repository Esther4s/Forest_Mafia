# 🌲 Лес и волки Bot - Production Guide

## 🚀 Быстрый старт

### 1. Подготовка окружения

```bash
# Клонируйте репозиторий
git clone https://github.com/your-username/forest-mafia-bot.git
cd forest-mafia-bot

# Скопируйте конфигурацию
cp production.env.example .env

# Отредактируйте .env файл
nano .env
```

### 2. Настройка переменных окружения

```bash
# .env файл
BOT_TOKEN=your_production_bot_token_here
DATABASE_URL=postgresql://username:password@host:port/database
TEST_MODE=false
LOG_LEVEL=INFO
```

### 3. Установка зависимостей

```bash
# Linux/macOS
pip install -r requirements.txt

# Windows
pip install -r requirements.txt
```

### 4. Настройка базы данных

```bash
# Примените миграции
alembic upgrade head

# Или создайте схему вручную
psql -d your_database -f fixed_database_schema.sql
```

### 5. Запуск

```bash
# Linux/macOS
./deploy_production.sh

# Windows
.\deploy_production.ps1
```

## 📋 Системные требования

### Минимальные требования
- **OS**: Linux (Ubuntu 20.04+), Windows 10+, macOS 10.15+
- **Python**: 3.8+
- **RAM**: 512 MB
- **CPU**: 1 core
- **Disk**: 1 GB

### Рекомендуемые требования
- **OS**: Linux (Ubuntu 22.04+)
- **Python**: 3.9+
- **RAM**: 2 GB
- **CPU**: 2 cores
- **Disk**: 5 GB
- **Database**: PostgreSQL 12+

## 🔧 Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию | Обязательная |
|------------|----------|--------------|--------------|
| `BOT_TOKEN` | Токен Telegram бота | - | ✅ |
| `DATABASE_URL` | URL базы данных | `sqlite:///forest_mafia.db` | ✅ |
| `TEST_MODE` | Тестовый режим | `false` | ❌ |
| `LOG_LEVEL` | Уровень логирования | `INFO` | ❌ |
| `MIN_PLAYERS` | Минимум игроков | `6` | ❌ |
| `MAX_PLAYERS` | Максимум игроков | `12` | ❌ |

### Игровые настройки

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `NIGHT_DURATION` | Длительность ночи (сек) | `60` |
| `DAY_DURATION` | Длительность дня (сек) | `300` |
| `VOTING_DURATION` | Длительность голосования (сек) | `120` |

## 🗄️ База данных

### PostgreSQL (рекомендуется)

```bash
# Установка PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Создание базы данных
sudo -u postgres createdb forest_mafia

# Создание пользователя
sudo -u postgres createuser forest_mafia_user

# Установка пароля
sudo -u postgres psql -c "ALTER USER forest_mafia_user PASSWORD 'your_password';"

# Предоставление прав
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE forest_mafia TO forest_mafia_user;"
```

### SQLite (для тестирования)

```bash
# SQLite не требует дополнительной настройки
# Просто укажите путь к файлу в DATABASE_URL
DATABASE_URL=sqlite:///forest_mafia.db
```

## 🚀 Деплой

### Linux (systemd)

```bash
# Запуск скрипта деплоя
./deploy_production.sh

# Проверка статуса
systemctl status forest-mafia-bot

# Просмотр логов
journalctl -u forest-mafia-bot -f
```

### Windows (Service)

```powershell
# Запуск скрипта деплоя
.\deploy_production.ps1

# Проверка статуса
Get-Service -Name ЛесИВолкиBot

# Просмотр логов
Get-EventLog -LogName Application -Source ЛесИВолкиBot -Newest 10
```

### Docker

```bash
# Сборка образа
docker build -t forest-mafia-bot .

# Запуск контейнера
docker run -d \
  --name forest-mafia-bot \
  --env-file .env \
  --restart unless-stopped \
  forest-mafia-bot
```

## 📊 Мониторинг

### Логи

```bash
# Linux
journalctl -u forest-mafia-bot -f

# Windows
Get-EventLog -LogName Application -Source ЛесИВолкиBot -Newest 100

# Docker
docker logs -f forest-mafia-bot
```

### Метрики

- **Активные игры**: Количество запущенных игр
- **Пользователи**: Количество зарегистрированных пользователей
- **Ошибки**: Количество ошибок в логах
- **Время отклика**: Время ответа на команды

### Алерты

Настройте алерты на:
- Ошибки в логах
- Высокое использование ресурсов
- Недоступность базы данных
- Остановку сервиса

## 🔒 Безопасность

### Рекомендации

1. **Токен бота**
   - Никогда не коммитьте токен в репозиторий
   - Используйте переменные окружения
   - Регулярно обновляйте токен

2. **База данных**
   - Используйте сильные пароли
   - Ограничьте доступ по IP
   - Включите SSL

3. **Сервер**
   - Обновляйте систему
   - Настройте файрвол
   - Используйте SSH ключи

4. **Логи**
   - Настройте ротацию логов
   - Не логируйте чувствительные данные
   - Мониторьте логи на подозрительную активность

## 🔄 Обновления

### Обновление кода

```bash
# Остановка сервиса
sudo systemctl stop forest-mafia-bot

# Обновление кода
git pull origin main

# Применение миграций
alembic upgrade head

# Запуск сервиса
sudo systemctl start forest-mafia-bot
```

### Откат изменений

```bash
# Откат кода
git checkout previous_commit

# Откат миграций
alembic downgrade -1

# Перезапуск
sudo systemctl restart forest-mafia-bot
```

## 🛠️ Устранение неполадок

### Частые проблемы

1. **Бот не отвечает**
   ```bash
   # Проверьте статус
   systemctl status forest-mafia-bot
   
   # Проверьте логи
   journalctl -u forest-mafia-bot -f
   ```

2. **Ошибки базы данных**
   ```bash
   # Проверьте подключение
   psql $DATABASE_URL -c "SELECT 1;"
   
   # Проверьте миграции
   alembic current
   ```

3. **Высокое использование ресурсов**
   ```bash
   # Проверьте процессы
   top -p $(pgrep -f bot.py)
   
   # Проверьте память
   free -h
   ```

### Логи и отладка

```bash
# Включить отладочные логи
export LOG_LEVEL=DEBUG

# Перезапустить сервис
sudo systemctl restart forest-mafia-bot

# Просмотреть логи
journalctl -u forest-mafia-bot -f
```

## 📞 Поддержка

### Контакты

- **GitHub Issues**: [github.com/your-username/forest-mafia-bot/issues](https://github.com/your-username/forest-mafia-bot/issues)
- **Email**: support@example.com
- **Telegram**: [@your_username](https://t.me/your_username)

### Документация

- **API**: [docs.example.com/api](https://docs.example.com/api)
- **FAQ**: [docs.example.com/faq](https://docs.example.com/faq)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для подробностей.

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта! См. файл [CONTRIBUTING.md](CONTRIBUTING.md) для подробностей.

---

**⚠️ ВАЖНО**: Перед деплоем в продакшен обязательно протестируйте все функции в тестовой среде!
