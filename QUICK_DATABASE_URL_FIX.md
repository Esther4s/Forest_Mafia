# ⚡ Быстрое исправление DATABASE_URL

## ❌ **Проблема:**
```
Could not parse SQLAlchemy URL from given URL string
```

## ✅ **РЕШЕНИЕ (2 минуты):**

### 1️⃣ **Получите DATABASE_URL:**
1. **Railway Dashboard** → **PostgreSQL** → **Variables**
2. **Скопируйте** `DATABASE_URL`

### 2️⃣ **Добавьте в проект:**
1. **Project** → **Variables** → **New Variable**
2. **Name:** `DATABASE_URL`
3. **Value:** вставьте скопированный URL
4. **Add**

### 3️⃣ **Готово!**
Railway автоматически передеплоит

---

## 🔍 **Проверьте переменные:**

Должны быть:
```
BOT_TOKEN=your_token
DATABASE_URL=postgresql://postgres:password@host:port/database
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

**🌲 Готово! Бот будет работать!** 🚂🐺
