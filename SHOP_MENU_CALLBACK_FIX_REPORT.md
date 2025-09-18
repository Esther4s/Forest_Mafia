# 🛍️ ИСПРАВЛЕНИЕ: Обработка shop_menu в callback_handler.py

## 🛍️ Проблема
Пользователь сообщил, что кнопка "🛍️ Магазин" отправляет отдельное сообщение вместо обработки через callback. Проблема была в том, что callback `shop_menu` не обрабатывается в `callback_handler.py`.

## 🔧 Исправления

### 1. Добавлен обработчик shop_menu в callback_handlers
**Файл**: `callback_handler.py`, метод `_setup_handlers`
**Изменение**: Добавлен обработчик для `shop_menu` callback

```python
# Добавлено:
"shop_menu": self._handle_shop_menu,
```

### 2. Создан метод _handle_shop_menu
**Файл**: `callback_handler.py`, новый метод
**Функциональность**: Обрабатывает открытие магазина через callback_handler

```python
async def _handle_shop_menu(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
    """Обрабатывает открытие магазина"""
    try:
        user_id = query.from_user.id
        self.logger.info(f"🛍️ Обработка shop_menu для пользователя {user_id}")
        
        # Получаем экземпляр бота
        from bot import ForestWolvesBot
        bot_instance = ForestWolvesBot.get_instance()
        
        # Если не получили экземпляр, пробуем альтернативные способы
        if not bot_instance:
            try:
                import bot
                if hasattr(bot, 'bot_instance') and bot.bot_instance:
                    bot_instance = bot.bot_instance
                    self.logger.info(f"✅ Найден экземпляр бота через глобальную переменную")
                else:
                    # Попробуем получить экземпляр через sys.modules
                    import sys
                    for module_name, module in sys.modules.items():
                        if hasattr(module, 'bot_instance') and module.bot_instance:
                            bot_instance = module.bot_instance
                            self.logger.info(f"✅ Найден экземпляр бота через модуль {module_name}")
                            break
            except Exception as e:
                self.logger.warning(f"⚠️ Не удалось найти экземпляр бота: {e}")
        
        if bot_instance:
            # Вызываем метод show_shop_menu из bot.py
            await bot_instance.show_shop_menu(query, context)
        else:
            await query.answer("❌ Бот не инициализирован!", show_alert=True)
            
    except Exception as e:
        self.logger.error(f"❌ Ошибка открытия магазина: {e}")
        await query.answer("❌ Произошла ошибка при открытии магазина!", show_alert=True)
```

## 🎯 Результат

### ✅ До исправления:
- Кнопка "🛍️ Магазин" отправляла отдельное сообщение
- Callback `shop_menu` не обрабатывался в `callback_handler.py`
- Пользователь не мог открыть магазин

### ✅ После исправления:
- Кнопка "🛍️ Магазин" правильно обрабатывается через callback
- Вызывается метод `show_shop_menu` из `bot.py`
- Магазин открывается корректно

## 🔍 Техническая информация

### Архитектура обработки callback'ов:
1. **callback_handler.py** - основной обработчик callback'ов
2. **bot.py** - содержит методы для отображения интерфейсов
3. **callback_handler.py** получает экземпляр бота и вызывает соответствующие методы

### Обработчики для кнопок:
- `shop_menu` → `_handle_shop_menu` → `bot_instance.show_shop_menu()`
- `inventory_menu` → `_handle_inventory_menu` → `bot_instance.show_inventory()`

## 🚀 Статус
✅ **ИСПРАВЛЕНО** - Кнопка "🛍️ Магазин" теперь работает корректно!

## 📝 Примечания
- Исправление аналогично уже существующему исправлению для `inventory_menu`
- Оба callback'а теперь обрабатываются единообразно
- Добавлено подробное логирование для отладки
