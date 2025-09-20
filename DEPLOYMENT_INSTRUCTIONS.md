# 🌲 Forest Mafia Bot - Инструкции по развертыванию

## ✅ Статус настройки

Все компоненты настроены и протестированы:
- ✅ Бот подключен к Telegram (@Forest_fuss_bot)
- ✅ База данных PostgreSQL (Railway) настроена и работает
- ✅ Схема базы данных исправлена
- ✅ Все тесты пройдены успешно

## 🚀 Быстрый запуск

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения
Файл `.env` уже создан с правильными настройками:
```
BOT_TOKEN=8314318680:AAG1CDOB-SQhyFfCpqDIBm-U8ANz6Ggw94k
DATABASE_URL=postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway
```

### 3. Запуск бота
```bash
python bot.py
```

## 🔧 Тестирование

### Проверка подключения к базе данных
```bash
python simple_db_test.py
```

### Полное тестирование системы
```bash
python test_bot.py
```

## 📊 Информация о системе

### Бот
- **Имя**: Лес и волки
- **Username**: @Forest_fuss_bot
- **ID**: 8314318680
- **Статус**: Активен и готов к работе

### База данных
- **Тип**: PostgreSQL (Railway)
- **Хост**: hopper.proxy.rlwy.net:23049
- **База**: railway
- **Статус**: Подключена и работает

### Текущие данные в базе
- Игр: 4
- Игроков: 18
- Событий: 0

## 🐳 Docker развертывание

### Создание образа
```bash
docker build -t forest-mafia-bot .
```

### Запуск контейнера
```bash
docker run -d --name forest-mafia-bot \
  -e BOT_TOKEN=8314318680:AAG1CDOB-SQhyFfCpqDIBm-U8ANz6Ggw94k \
  -e DATABASE_URL=postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway \
  forest-mafia-bot
```

### Docker Compose
```bash
docker-compose up -d
```

## 🌐 Развертывание на Railway

### 1. Подготовка
- Репозиторий уже настроен
- База данных PostgreSQL уже создана
- Переменные окружения настроены

### 2. Деплой
```bash
# Установка Railway CLI
npm install -g @railway/cli

# Вход в аккаунт
railway login

# Подключение к проекту
railway link

# Деплой
railway up
```

### 3. Настройка переменных окружения в Railway
```
BOT_TOKEN=8314318680:AAG1CDOB-SQhyFfCpqDIBm-U8ANz6Ggw94k
DATABASE_URL=postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway
```

## 📋 Команды бота

- `/start` - приветствие и список команд
- `/rules` - правила игры
- `/join` - присоединиться к игре
- `/leave` - покинуть игру (только до начала игры)
- `/start_game` - начать игру (только для администраторов)
- `/end_game` - завершить игру (только для администраторов)
- `/force_end` - принудительно завершить игру (только для администраторов)
- `/settings` - настройки игры (только для администраторов)
- `/status` - статус текущей игры
- `/stats` - ваша статистика игр
- `/stats top` - топ игроков по победам

## 🎮 Как играть

### Начало игры
1. Игроки используют команду `/join` для присоединения
2. Администратор использует `/start_game` когда набралось минимум 6 игроков
3. Бот автоматически распределяет роли между игроками

### Игровой процесс
1. **Ночь** - игроки с ночными ролями совершают действия
2. **День** - все игроки обсуждают события (5 минут)
3. **Голосование** - голосование за изгнание (2 минуты)
4. Повторение циклов до победы одной из команд

## 🔒 Безопасность

- Все токены и секреты хранятся в переменных окружения
- Файл `.env` исключен из git через `.gitignore`
- База данных защищена паролем
- Регулярно обновляйте зависимости

## 🐛 Устранение неполадок

### Проблемы с подключением к базе данных
```bash
python fix_database_schema.py
```

### Проблемы с переменными окружения
Убедитесь, что файл `.env` создан правильно:
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('BOT_TOKEN:', os.environ.get('BOT_TOKEN'))"
```

### Проблемы с ботом
Проверьте токен бота в @BotFather и убедитесь, что бот не заблокирован.

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи бота
2. Запустите тесты: `python test_bot.py`
3. Проверьте подключение к базе данных: `python simple_db_test.py`

## 🎉 Готово!

Бот полностью настроен и готов к работе. Можете добавлять его в группы и начинать играть в "Лес и Волки"!
