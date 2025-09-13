# 🚀 Руководство по развертыванию Лес и волки Bot

## 📋 Предварительные требования

- Python 3.11+
- Docker и Docker Compose (для контейнерного развертывания)
- Telegram Bot Token от [@BotFather](https://t.me/BotFather)

## 🔧 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd forest-mafia-bot
```

### 2. Настройка переменных окружения
```bash
# Копируем шаблон
cp env.production .env

# Редактируем .env файл
nano .env
```

Добавьте ваш токен бота:
```env
BOT_TOKEN=your_actual_bot_token_here
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Запуск бота
```bash
python bot.py
```

## 🐳 Развертывание с Docker

### Автоматический деплой
```bash
# Делаем скрипт исполняемым
chmod +x deploy.sh

# Запускаем деплой
./deploy.sh
```

### Ручной деплой
```bash
# Сборка образа
docker-compose build

# Запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

## 🐧 Развертывание на Linux сервере

### 1. Создание пользователя
```bash
sudo useradd -m -s /bin/bash bot
sudo mkdir -p /opt/forest-mafia-bot
sudo chown bot:bot /opt/forest-mafia-bot
```

### 2. Копирование файлов
```bash
sudo cp -r . /opt/forest-mafia-bot/
sudo chown -R bot:bot /opt/forest-mafia-bot
```

### 3. Создание виртуального окружения
```bash
sudo -u bot python3 -m venv /opt/forest-mafia-bot/venv
sudo -u bot /opt/forest-mafia-bot/venv/bin/pip install -r /opt/forest-mafia-bot/requirements.txt
```

### 4. Настройка systemd сервиса
```bash
sudo cp forest-mafia-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable forest-mafia-bot
sudo systemctl start forest-mafia-bot
```

### 5. Проверка статуса
```bash
sudo systemctl status forest-mafia-bot
sudo journalctl -u forest-mafia-bot -f
```

## 🔒 Безопасность

### Обязательные меры:
1. **Никогда не коммитьте .env файл в git**
2. **Используйте сильные токены ботов**
3. **Ограничьте права бота в Telegram**
4. **Регулярно обновляйте зависимости**

### Рекомендуемые настройки бота в Telegram:
- Отключите групповые приваты
- Ограничьте команды только необходимыми
- Настройте webhook для продакшена

## 📊 Мониторинг

### Логи
```bash
# Docker
docker-compose logs -f

# Systemd
sudo journalctl -u forest-mafia-bot -f

# Прямой запуск
python bot.py 2>&1 | tee bot.log
```

### Проверка здоровья
```bash
# Проверка статуса контейнера
docker-compose ps

# Проверка systemd сервиса
sudo systemctl status forest-mafia-bot
```

## 🔄 Обновление

### Docker
```bash
git pull
./deploy.sh
```

### Systemd
```bash
sudo systemctl stop forest-mafia-bot
git pull
sudo -u bot /opt/forest-mafia-bot/venv/bin/pip install -r requirements.txt
sudo systemctl start forest-mafia-bot
```

## 🛠️ Устранение неполадок

### Бот не запускается
1. Проверьте токен в .env файле
2. Убедитесь, что все зависимости установлены
3. Проверьте логи на наличие ошибок

### Проблемы с правами
```bash
# Docker
sudo chown -R $USER:$USER .

# Systemd
sudo chown -R bot:bot /opt/forest-mafia-bot
```

### Проблемы с сетью
- Проверьте firewall настройки
- Убедитесь, что порты открыты
- Проверьте DNS разрешение

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи
2. Убедитесь в корректности конфигурации
3. Создайте issue в репозитории
