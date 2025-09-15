# 🚀 ИНСТРУКЦИИ ПО ДЕПЛОЮ НА RAILWAY

## ✅ ПОДГОТОВКА ЗАВЕРШЕНА

### 📋 Что уже сделано:
- ✅ Код закоммичен в Git
- ✅ Все файлы готовы к деплою
- ✅ Railway конфигурация настроена
- ✅ Requirements.txt обновлен
- ✅ .gitignore настроен

---

## 🚀 ПОШАГОВЫЙ ДЕПЛОЙ НА RAILWAY

### 1. 📱 Вход в Railway
1. Откройте [railway.app](https://railway.app)
2. Войдите в свой аккаунт
3. Нажмите "New Project"

### 2. 🔗 Подключение Git репозитория
1. Выберите "Deploy from GitHub repo"
2. Найдите ваш репозиторий "ЛесИВолки-1"
3. Нажмите "Deploy Now"

### 3. ⚙️ Настройка переменных окружения
В разделе "Variables" добавьте:

```
BOT_TOKEN=your_actual_bot_token_here
DATABASE_URL=postgresql://postgres:JOoSxKXEcnXImgvwCWsfcQQDlnWSDNyD@hopper.proxy.rlwy.net:23049/railway
```

### 4. 🗄️ Настройка базы данных
1. Railway автоматически создаст PostgreSQL базу
2. Скопируйте DATABASE_URL из настроек базы
3. Обновите переменную DATABASE_URL

### 5. 🚀 Запуск деплоя
1. Railway автоматически начнет деплой
2. Дождитесь завершения сборки
3. Проверьте логи на наличие ошибок

---

## 📁 ФАЙЛЫ ДЛЯ RAILWAY

### ✅ railway.json
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python bot.py"
  }
}
```

### ✅ requirements.txt
```
python-telegram-bot[job-queue]==20.7
python-dotenv==1.0.0
sqlalchemy>=2.0.25
alembic>=1.13.0
psycopg2-binary>=2.9.0
```

### ✅ .gitignore
- Исключает .env файлы
- Исключает временные файлы
- Исключает логи

---

## 🔧 НАСТРОЙКИ RAILWAY

### 🏗️ Build Settings
- **Builder**: NIXPACKS (автоматически)
- **Start Command**: `python bot.py`
- **Python Version**: 3.11+ (автоматически)

### 🌐 Environment Variables
```
BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://...
```

### 📊 Resources
- **CPU**: 1 vCPU
- **RAM**: 1GB
- **Storage**: 1GB

---

## 🧪 ПРОВЕРКА ДЕПЛОЯ

### 1. 📋 Проверка логов
1. Откройте вкладку "Deployments"
2. Нажмите на последний деплой
3. Проверьте логи на ошибки

### 2. 🤖 Тестирование бота
1. Найдите бота в Telegram
2. Отправьте `/start`
3. Проверьте все команды

### 3. 🗄️ Проверка базы данных
1. Откройте вкладку "Data"
2. Проверьте таблицы
3. Убедитесь, что данные сохраняются

---

## 🚨 УСТРАНЕНИЕ ПРОБЛЕМ

### ❌ Ошибка: "Module not found"
**Решение**: Проверьте requirements.txt

### ❌ Ошибка: "Database connection failed"
**Решение**: Проверьте DATABASE_URL

### ❌ Ошибка: "Bot token invalid"
**Решение**: Проверьте BOT_TOKEN

### ❌ Ошибка: "Port already in use"
**Решение**: Railway автоматически назначит порт

---

## 📊 МОНИТОРИНГ

### 📈 Метрики
- **CPU Usage**: Следите за нагрузкой
- **Memory Usage**: Проверяйте использование памяти
- **Network**: Мониторьте трафик

### 📝 Логи
- **Application Logs**: Логи бота
- **Build Logs**: Логи сборки
- **Deploy Logs**: Логи деплоя

---

## 🔄 ОБНОВЛЕНИЯ

### 📤 Новый деплой
1. Внесите изменения в код
2. Сделайте коммит: `git commit -m "Update"`
3. Запушьте: `git push`
4. Railway автоматически обновит деплой

### 🔄 Откат
1. Откройте вкладку "Deployments"
2. Выберите предыдущую версию
3. Нажмите "Redeploy"

---

## 🎉 ГОТОВО!

После выполнения всех шагов ваш Лес и волки Bot будет работать на Railway!

### ✅ Что должно работать:
- 🤖 Все команды бота
- 🎮 Игровая механика
- 👤 Профили игроков
- 🛍️ Магазин товаров
- 💰 Система орешков
- 📊 Статистика

### 🆘 Поддержка
Если возникли проблемы:
1. Проверьте логи Railway
2. Проверьте переменные окружения
3. Проверьте подключение к базе данных

---

**Дата создания**: 12 сентября 2025  
**Версия**: 1.0.0  
**Статус**: ✅ Готов к деплою
