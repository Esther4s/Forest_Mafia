# 🔍 Как найти DATABASE_URL в Railway

## 📍 **Где найти ссылку на базу данных:**

### 1️⃣ **В Railway Dashboard:**

1. **Откройте Railway Dashboard** (railway.app)
2. **Нажмите на ваш проект** "Лес и волки Bot"
3. **Нажмите на PostgreSQL сервис** (синяя иконка базы данных)
4. **Перейдите в "Variables"** (вкладка справа)
5. **Найдите `DATABASE_URL`** - это и есть ваша ссылка!

### 2️⃣ **Ссылка выглядит так:**
```
postgresql://postgres:password@host:port/database
```

---

## 🔍 **Пошаговая инструкция:**

### **Шаг 1: Откройте Railway**
- Перейдите на railway.app
- Войдите в аккаунт

### **Шаг 2: Найдите проект**
- Нажмите на проект "Лес и волки Bot"

### **Шаг 3: Найдите PostgreSQL**
- Найдите синюю иконку базы данных
- Нажмите на неё

### **Шаг 4: Перейдите в Variables**
- В правой панели найдите вкладку "Variables"
- Нажмите на неё

### **Шаг 5: Скопируйте DATABASE_URL**
- Найдите строку с `DATABASE_URL`
- Скопируйте значение (начинается с `postgresql://`)

---

## 📋 **Пример ссылки:**
```
postgresql://postgres:abc123def456@containers-us-west-123.railway.app:5432/railway
```

---

## 🚨 **Важно:**
- **НЕ копируйте** `DATABASE_URL` из проекта
- **Копируйте** `DATABASE_URL` из PostgreSQL сервиса
- Ссылка должна начинаться с `postgresql://`

---

## 🎯 **После копирования:**
1. Перейдите в проект
2. Variables → New Variable
3. Name: `DATABASE_URL`
4. Value: вставьте скопированную ссылку
5. Add

---

**🌲 Найдите ссылку в PostgreSQL Variables!** 🚂🐺
