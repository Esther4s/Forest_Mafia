# 🔍 ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ: Кнопки "Магазин" и "Корзинка"

## 🔍 Проблема
Пользователь сообщил, что в ветке с лесами не работают кнопки "🛍️ Магазин" и "🧺 Корзинка" в стартовом меню. Требовалось добавить детальное логирование для диагностики проблемы.

## 🔧 Добавленное логирование

### 1. Логирование в callback_handler.py

#### В методе `handle_callback`:
```python
# Добавлено логирование входящих callback'ов
user_id = query.from_user.id if query.from_user else "unknown"
self.logger.info(f"🔍 handle_callback: Получен callback от пользователя {user_id}, data: '{callback_data}'")

# Добавлено логирование поиска обработчиков
self.logger.info(f"🔍 handle_callback: main_handler = '{main_handler}', parts = {parts}")
self.logger.info(f"🔍 handle_callback: Поиск обработчика для '{main_handler}': {'найден' if handler_func else 'не найден'}")

# Добавлено логирование доступных обработчиков при ошибке
self.logger.warning(f"⚠️ handle_callback: Обработчик для '{main_handler}' не найден, доступные: {list(self.callback_handlers.keys())}")
```

#### В методе `_handle_shop_menu`:
```python
self.logger.info(f"🛍️ _handle_shop_menu: Начало обработки для пользователя {user_id}, parts: {parts}")
```

#### В методе `_handle_inventory_menu`:
```python
self.logger.info(f"🧺 _handle_inventory_menu: Начало обработки для пользователя {user_id}, parts: {parts}")
```

### 2. Логирование в bot.py

#### В методе `handle_welcome_buttons`:
```python
# Добавлено логирование входящих callback'ов
user_id = query.from_user.id if query.from_user else "unknown"
logger.info(f"🔍 handle_welcome_buttons: Получен callback от пользователя {user_id}, data: '{query.data}'")

# Добавлено логирование обработки shop_menu
logger.info(f"🛍️ handle_welcome_buttons: Обработка shop_menu для пользователя {user_id}")

# Добавлено логирование обработки inventory_menu
logger.info(f"🧺 handle_welcome_buttons: Обработка inventory_menu для пользователя {user_id}")
```

#### В методе `show_shop_menu`:
```python
logger.info(f"🛍️ show_shop_menu: Начало показа магазина для пользователя {user_id} ({username})")
```

#### В методе `show_inventory`:
```python
logger.info(f"🧺 show_inventory: Начало показа инвентаря для пользователя {user_id} ({username})")
```

## 🎯 Что покажет логирование

### ✅ **Для диагностики проблем:**
1. **Входящие callback'ы** - какие данные приходят от пользователя
2. **Поиск обработчиков** - находится ли нужный обработчик
3. **Доступные обработчики** - список всех зарегистрированных обработчиков
4. **Выполнение методов** - доходят ли вызовы до конкретных методов
5. **Права пользователя** - есть ли у пользователя права на выполнение действий

### 🔍 **Трассировка выполнения:**
```
🔍 handle_callback: Получен callback от пользователя 12345, data: 'shop_menu'
🔍 handle_callback: main_handler = 'shop', parts = ['shop', 'menu']
🔍 handle_callback: Поиск обработчика для 'shop': не найден
⚠️ handle_callback: Обработчик для 'shop' не найден, доступные: ['view_my_role', 'repeat_current_phase', ...]
```

## 🚀 Статус
✅ **ЛОГИРОВАНИЕ ДОБАВЛЕНО** - Теперь можно диагностировать проблемы с кнопками!

## 📝 Примечания
- Логирование добавлено во все ключевые точки обработки callback'ов
- Включено логирование ошибок и предупреждений
- Добавлена трассировка выполнения для методов магазина и инвентаря
- Логирование поможет быстро найти причину неработающих кнопок
