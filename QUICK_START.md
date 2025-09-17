# 🚀 Быстрый запуск системы лесов

## 1. Применение миграции

```bash
python apply_forest_migration.py
```

## 2. Тестирование системы

```bash
python test_forest_system.py
```

## 3. Запуск бота с лесами

```bash
python bot_with_forests.py
```

## 📋 Основные команды

- `/create_forest Лес Волков Описание` - создать лес
- `/forests` - список лесов
- `/join_forest_<id>` - присоединиться
- `/summon_forest_<id>` - созвать участников

## ⚙️ Настройки

Создайте файл `.env`:
```
BOT_TOKEN=your_bot_token_here
DATABASE_URL=sqlite:///forest_mafia.db
```

## 🔧 Интеграция с существующим ботом

Добавьте в ваш `bot.py`:

```python
from forest_integration import init_forest_integration

# В __init__:
self.forest_integration = init_forest_integration(self.application.bot)

# В добавление обработчиков:
forest_handlers = self.forest_integration.get_command_handlers()
for handler in forest_handlers:
    self.application.add_handler(handler)
```

## 📁 Созданные файлы

- `forest_system.py` - основная система
- `forest_handlers.py` - обработчики команд
- `summon_system.py` - система созыва
- `forest_integration.py` - интеграция с ботом
- `forest_tables_migration.sql` - SQL миграция
- `bot_with_forests.py` - пример бота
- `test_forest_system.py` - тесты

## ✅ Готово!

Система лесов полностью интегрирована и готова к использованию!
