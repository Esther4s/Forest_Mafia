# ИСПРАВЛЕНИЕ: Обработка inventory_menu в callback_handler.py

## 🧺 Проблема
Пользователь сообщил, что кнопка "🧺 Корзинка" не открывается. Проблема была в том, что callback `inventory_menu` обрабатывается в `callback_handler.py`, а не в `bot.py`.

## 🔧 Исправления

### 1. Добавлен обработчик inventory в callback_handlers
**Файл**: `callback_handler.py`, метод `_setup_handlers`
**Изменение**: Добавлен обработчик для `inventory` callback

```python
# Добавлено:
"inventory": self._handle_inventory_menu,
```

### 2. Создан метод _handle_inventory_menu
**Файл**: `callback_handler.py`, новый метод
**Функциональность**: Обрабатывает открытие инвентаря через callback_handler

```python
async def _handle_inventory_menu(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
    """Обрабатывает открытие инвентаря (корзинки)"""
    try:
        user_id = query.from_user.id
        
        # Получаем экземпляр бота
        from bot import ForestWolvesBot
        bot_instance = ForestWolvesBot.get_instance()
        
        # Альтернативные способы получения экземпляра бота
        if not bot_instance:
            # ... (логика поиска экземпляра бота)
        
        if bot_instance:
            # Вызываем метод show_inventory из bot.py
            await bot_instance.show_inventory(query, context)
        else:
            await query.answer("❌ Бот не инициализирован!", show_alert=True)
            
    except Exception as e:
        self.logger.error(f"❌ Ошибка открытия инвентаря: {e}")
        await query.answer("❌ Произошла ошибка при открытии инвентаря!", show_alert=True)
```

## ✅ Результат
- ✅ **Обработчик добавлен**: `inventory` теперь обрабатывается в callback_handler.py
- ✅ **Правильная архитектура**: Callback обрабатывается в правильном месте
- ✅ **Вызов show_inventory**: Метод вызывает существующий метод show_inventory из bot.py
- ✅ **Обработка ошибок**: Есть обработка ошибок и альтернативные способы получения экземпляра бота
- ✅ **Логирование**: Добавлено подробное логирование для диагностики

## 🎯 Статус
✅ **ИСПРАВЛЕНО** - Кнопка "🧺 Корзинка" теперь должна корректно открывать инвентарь пользователя
