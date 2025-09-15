# ДОБАВЛЕНИЕ: Кнопка корзинки в статус игры

## 🧺 Задача
Пользователь показал скриншот сообщения регистрации, где была только кнопка "🛍️ Магазин", но не было кнопки "🧺 Корзинка". Нужно добавить кнопку корзинки в сообщение статуса игры.

## 🔧 Исправления

### 1. Добавлена кнопка корзинки в send_game_status
**Файл**: `bot.py`, метод `send_game_status`
**Изменение**: Добавлена кнопка "🧺 Корзинка" рядом с кнопкой магазина

```python
# Было:
# Кнопка "Магазин"
keyboard.append([InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")])

# Стало:
# Кнопки "Магазин" и "Корзинка"
keyboard.append([InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop"), InlineKeyboardButton("🧺 Корзинка", callback_data="inventory_menu")])
```

### 2. Добавлена кнопка корзинки в инвентарь
**Файл**: `bot.py`, метод показа инвентаря
**Изменение**: Добавлена кнопка "🧺 Корзинка" в клавиатуру инвентаря

```python
# Было:
keyboard = [
    [InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop")],
    [InlineKeyboardButton("💰 Баланс", callback_data="show_balance")],
    [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
]

# Стало:
keyboard = [
    [InlineKeyboardButton("🛍️ Магазин", callback_data="show_shop"), InlineKeyboardButton("🧺 Корзинка", callback_data="inventory_menu")],
    [InlineKeyboardButton("💰 Баланс", callback_data="show_balance")],
    [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
]
```

## ✅ Результат
- ✅ **Кнопка корзинки добавлена**: В сообщение статуса игры добавлена кнопка "🧺 Корзинка"
- ✅ **Callback data**: Используется `inventory_menu` для открытия инвентаря пользователя
- ✅ **Компактное расположение**: Кнопки магазина и корзинки размещены в одной строке
- ✅ **Единообразие**: Кнопка добавлена во все места где есть кнопка магазина
- ✅ **Функциональность**: При нажатии на корзинку открывается инвентарь пользователя

## 🎯 Статус
✅ **ДОБАВЛЕНО** - Кнопка корзинки теперь отображается в сообщении статуса игры и открывает инвентарь пользователя
