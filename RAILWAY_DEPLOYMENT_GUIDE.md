# 🚀 Развертывание расширенной системы лесов на Railway

## 📋 Предварительные требования

1. **Аккаунт Railway** - зарегистрируйтесь на [railway.app](https://railway.app)
2. **Railway CLI** - установите командную строку:
   ```bash
   npm install -g @railway/cli
   ```
3. **Git репозиторий** - код должен быть в GitHub

## 🔧 Настройка проекта

### 1. Переменные окружения

В настройках проекта Railway добавьте:

```bash
BOT_TOKEN=your_telegram_bot_token_here
DATABASE_URL=postgresql://username:password@host:port/database
LOG_LEVEL=INFO
```

### 2. Файлы конфигурации

Убедитесь, что у вас есть:
- `railway_enhanced.json` - конфигурация Railway
- `Procfile` - команда запуска
- `railway_deploy.py` - скрипт развертывания
- `requirements.txt` - зависимости Python

## 🚀 Развертывание

### Способ 1: Через Railway CLI

```bash
# Клонируйте репозиторий
git clone https://github.com/your-username/Forest_Mafia.git
cd Forest_Mafia

# Авторизуйтесь в Railway
railway login

# Создайте новый проект
railway new

# Примените миграции
python apply_forest_migration.py

# Разверните
railway up
```

### Способ 2: Через веб-интерфейс

1. Зайдите на [railway.app](https://railway.app)
2. Нажмите "New Project"
3. Выберите "Deploy from GitHub repo"
4. Выберите ваш репозиторий
5. Настройте переменные окружения
6. Railway автоматически развернет проект

### Способ 3: Автоматический скрипт

```bash
# Сделайте скрипт исполняемым
chmod +x deploy_railway_enhanced.sh

# Запустите развертывание
./deploy_railway_enhanced.sh
```

## ⚙️ Настройка переменных окружения

### BOT_TOKEN
Получите токен бота у [@BotFather](https://t.me/botfather):
1. Отправьте `/newbot`
2. Следуйте инструкциям
3. Скопируйте полученный токен

### DATABASE_URL
Railway автоматически создаст PostgreSQL базу данных:
1. В настройках проекта найдите "Database"
2. Скопируйте "Connection String"
3. Вставьте как значение `DATABASE_URL`

## 🔄 Обновление

Для обновления бота:

```bash
# Получите последние изменения
git pull origin main

# Примените миграции (если есть новые)
python apply_forest_migration.py

# Разверните обновления
railway up
```

## 📊 Мониторинг

### Логи
```bash
# Просмотр логов
railway logs

# Следить за логами в реальном времени
railway logs --follow
```

### Статистика
- Зайдите в веб-интерфейс Railway
- Откройте ваш проект
- Перейдите в раздел "Metrics"

## 🛠️ Отладка

### Проверка статуса
```bash
# Статус развертывания
railway status

# Информация о проекте
railway info
```

### Подключение к базе данных
```bash
# Открыть консоль PostgreSQL
railway connect
```

### Локальное тестирование
```bash
# Запустить локально с переменными Railway
railway run python bot_with_enhanced_forests.py
```

## 🔧 Конфигурация

### railway_enhanced.json
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python railway_deploy.py"
  }
}
```

### Procfile
```
web: python railway_deploy.py
```

## 📱 Команды бота после развертывания

После успешного развертывания бот будет поддерживать:

### Основные команды:
- `/start` - запуск бота
- `/help` - справка
- `/profile` - профиль пользователя

### Система лесов:
- `/create_forest` - создать лес
- `/forests` - список лесов
- `/forest_profile <ID>` - профиль леса
- `/forest_analytics <ID>` - аналитика леса
- `/top_forests` - топ лесов

### Аналитика:
- `/forest_comparison <ID1> <ID2>` - сравнение лесов
- `/forest_ranking <ID>` - рейтинг участников

## 🚨 Устранение неполадок

### Бот не запускается
1. Проверьте `BOT_TOKEN` в переменных окружения
2. Убедитесь, что токен действителен
3. Проверьте логи: `railway logs`

### Ошибки базы данных
1. Проверьте `DATABASE_URL`
2. Убедитесь, что база данных доступна
3. Примените миграции: `python apply_forest_migration.py`

### Ошибки зависимостей
1. Проверьте `requirements.txt`
2. Убедитесь, что все пакеты указаны
3. Пересоберите проект: `railway up --detach`

## 📈 Масштабирование

### Автоматическое масштабирование
Railway автоматически масштабирует ваш бот в зависимости от нагрузки.

### Ручное масштабирование
В настройках проекта можно настроить:
- Количество реплик
- Ресурсы (CPU, RAM)
- Регион развертывания

## 💰 Стоимость

Railway предлагает:
- **Бесплатный план**: $5 кредитов в месяц
- **Pro план**: $20/месяц за неограниченное использование

Для бота "Лес и Волки" бесплатного плана должно хватить.

## 🎉 Готово!

После развертывания ваш бот с расширенной системой лесов будет доступен 24/7 на Railway!

### Проверка работы:
1. Найдите вашего бота в Telegram
2. Отправьте `/start`
3. Попробуйте команды лесов
4. Создайте тестовый лес

🌲 **Удачной игры в лесу!** 🌲
