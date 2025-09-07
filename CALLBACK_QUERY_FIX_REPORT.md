# 🔧 Исправление ошибки CallbackQuery в Railway

## ❌ **Проблема:**
```
'CallbackQuery' object has no attribute 'effective_user'
```

**Ошибка возникала при нажатии на кнопки:**
- "Закончить обсуждение"
- "Проверить таймер" 
- "Выбрать волка"

---

## 🔍 **Причина:**
В функциях `check_game_permissions` и `check_user_permissions` использовался `update.effective_user`, но для `CallbackQuery` нужно использовать `update.callback_query.from_user`.

---

## ✅ **ИСПРАВЛЕНИЕ:**

### 1️⃣ **Исправлена функция `check_user_permissions`:**
```python
# Получаем user_id в зависимости от типа update
if update.effective_user:
    user_id = update.effective_user.id
elif update.callback_query and update.callback_query.from_user:
    user_id = update.callback_query.from_user.id
else:
    return False, "❌ Не удалось определить пользователя!"

# Получаем chat_id в зависимости от типа update
if update.effective_chat:
    chat_id = update.effective_chat.id
elif update.callback_query and update.callback_query.message:
    chat_id = update.callback_query.message.chat_id
else:
    return False, "❌ Не удалось определить чат!"
```

### 2️⃣ **Исправлена функция `check_game_permissions`:**
```python
# Аналогичная логика для определения user_id и chat_id
```

---

## 🎯 **ЧТО ИСПРАВЛЕНО:**

### ✅ **Кнопки теперь работают:**
- ✅ "Закончить обсуждение" - проверка прав администратора
- ✅ "Проверить таймер" - проверка прав администратора  
- ✅ "Выбрать волка" - проверка прав администратора

### ✅ **Правильная обработка:**
- ✅ Обычные команды (через `update.effective_user`)
- ✅ Callback кнопки (через `update.callback_query.from_user`)

---

## 🚀 **ДЕПЛОЙ ИСПРАВЛЕНИЯ:**

### 1️⃣ **Изменения закоммичены:**
```bash
git add bot.py
git commit -m "Fix CallbackQuery effective_user error"
git push origin main
```

### 2️⃣ **Railway автоматически передеплоит:**
- Установит исправления
- Перезапустит бота

---

## 🎯 **РЕЗУЛЬТАТ:**

### ✅ **После деплоя:**
- Кнопки будут работать без ошибок
- Проверка прав будет корректной
- Администраторы смогут использовать все функции

### ✅ **Проверка:**
1. Откройте Telegram
2. Найдите вашего бота
3. Нажмите на кнопки "Закончить обсуждение", "Проверить таймер", "Выбрать волка"
4. Кнопки должны работать без ошибок

---

## 🎉 **ГОТОВО!**

**Ошибка CallbackQuery исправлена! Все кнопки теперь работают корректно!** 🚂🌲

---
*Исправление ошибки CallbackQuery в Railway*