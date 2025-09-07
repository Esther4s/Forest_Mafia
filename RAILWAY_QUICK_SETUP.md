# ⚡ Быстрая настройка Railway (5 минут)

## 🎯 **ГОТОВ К НАСТРОЙКЕ!**

У вас есть все файлы: `railway.json`, `requirements.txt`, `bot.py` и документация!

---

## 🚀 **БЫСТРЫЕ ШАГИ:**

### 1️⃣ **Создайте аккаунт**
- [railway.app](https://railway.app) → **"Sign Up"** → **"Sign up with GitHub"**

### 2️⃣ **Создайте проект**
- **"New Project"** → **"Deploy from GitHub repo"** → **"Esther4s/Forest_Mafia"**

### 3️⃣ **Добавьте PostgreSQL**
- **"New"** → **"Database"** → **"PostgreSQL"**

### 4️⃣ **Настройте переменные**
В **"Variables"** добавьте:
```
BOT_TOKEN=your_actual_bot_token_here
ENVIRONMENT=production
LOG_LEVEL=INFO
DATABASE_URL=postgresql://postgres:password@host:port/database
```

**⚠️ ВАЖНО:** Замените `your_actual_bot_token_here` на ваш реальный токен от @BotFather!

### 5️⃣ **Готово!**
- Railway автоматически деплоит
- Следите за логами в **"Deployments"**
- Тестируйте бота в Telegram

---

## 🔧 **Где взять BOT_TOKEN?**

1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/mybots`
3. Выберите вашего бота
4. Нажмите **"API Token"**
5. Скопируйте токен
6. Вставьте в Railway Variables

---

## ✅ **Проверка работы**

### В логах должно быть:
```
✅ База данных инициализирована
✅ Бот запущен успешно
✅ Готов к работе
```

### Тест в Telegram:
1. Найдите вашего бота
2. Отправьте `/start` в группе
3. Попробуйте `/join`
4. Бот должен отвечать!

---

## 🆘 **Проблемы?**

### ❌ Бот не отвечает
- Проверьте `BOT_TOKEN` в Variables
- Убедитесь, что токен правильный

### ❌ Ошибки в логах
- Проверьте все переменные окружения
- Убедитесь, что `DATABASE_URL` установлен

### ❌ База данных не работает
- Перезапустите приложение
- Проверьте, что PostgreSQL сервис запущен

---

## 🎉 **Готово!**

**Ваш ForestMafia Bot теперь работает в продакшене на Railway!** 🚂🌲

**Бесплатно, быстро, надежно!** ✨

---
*Быстрая настройка Railway для ForestMafia Bot*
