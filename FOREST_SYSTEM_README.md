# 🌲 Система лесов для бота "Лес и Волки" 🌲

Система управления лесами (группами участников) с возможностью созыва, приглашений и батчинга уведомлений.

## 🚀 Возможности

- **Создание лесов** - создавайте именованные группы участников
- **Управление участниками** - присоединение, покидание, список участников
- **Созыв с батчингом** - умная система уведомлений с разбивкой на батчи
- **Система приглашений** - персональные приглашения с callback-кнопками
- **Cooldown система** - защита от спама с настраиваемыми интервалами
- **Настройки приватности** - публичные и приватные леса
- **HTML-упоминания** - красивые упоминания участников в сообщениях

## 📁 Структура файлов

```
forest_system.py          # Основная система управления лесами
forest_handlers.py        # Обработчики команд и callback-ов
summon_system.py          # Система созыва с батчингом
forest_integration.py     # Интеграция с основным ботом
forest_tables_migration.sql # SQL миграция для создания таблиц
apply_forest_migration.py  # Скрипт применения миграции
bot_with_forests.py       # Пример интеграции с ботом
```

## 🗄️ База данных

### Таблицы

- **forests** - информация о лесах
- **forest_members** - участники лесов
- **forest_invites** - приглашения в леса
- **forest_settings** - настройки лесов

### Применение миграции

```bash
python apply_forest_migration.py
```

## 🤖 Команды бота

### Основные команды

- `/create_forest <название> <описание>` - создать лес
- `/forests` - список всех лесов
- `/my_forests` - мои леса

### Команды лесов (динамические)

- `/join_forest_<id>` - присоединиться к лесу
- `/leave_forest_<id>` - покинуть лес
- `/summon_forest_<id>` - созвать участников леса
- `/list_forest_<id>` - список участников леса
- `/invite_forest_<id> @username` - пригласить в лес

### Параметры создания леса

- `--private` - приватный лес (только по приглашениям)
- `--max <число>` - максимальное количество участников
- `--batch <число>` - размер батча для созыва (по умолчанию 6)
- `--cooldown <минуты>` - cooldown между вызовами (по умолчанию 30)

## 🔧 Интеграция с существующим ботом

### 1. Добавьте импорты

```python
from forest_integration import init_forest_integration, get_forest_integration
```

### 2. Инициализируйте систему

```python
# В методе __init__ или initialize вашего бота
self.forest_integration = init_forest_integration(self.application.bot)
```

### 3. Добавьте обработчики

```python
# Добавьте в метод добавления обработчиков
forest_handlers = self.forest_integration.get_command_handlers()
for handler in forest_handlers:
    self.application.add_handler(handler)

forest_callbacks = self.forest_integration.get_callback_handlers()
for handler in forest_callbacks:
    self.application.add_handler(handler)

dynamic_handlers = self.forest_integration.get_dynamic_command_handlers()
for handler in dynamic_handlers:
    self.application.add_handler(handler)
```

### 4. Обновите команды бота

```python
commands = [
    BotCommand("create_forest", "Создать лес"),
    BotCommand("forests", "Список лесов"),
    BotCommand("my_forests", "Мои леса"),
    # ... ваши существующие команды
]
await self.application.bot.set_my_commands(commands)
```

## 📝 Примеры использования

### Создание леса

```
/create_forest Лес Волков Еженедельные игры в мафию --max 20 --batch 8
```

### Создание приватного леса

```
/create_forest Секретный лес Только для друзей --private --max 10
```

### Присоединение к лесу

```
/join_forest_les_volkov
```

### Созыв участников

```
/summon_forest_les_volkov
```

## ⚙️ Настройки

### Конфигурация леса

```python
config = ForestConfig(
    forest_id="les_volkov",
    name="Лес Волков",
    creator_id=123456789,
    description="Еженедельные игры в мафию",
    privacy=ForestPrivacy.PUBLIC,
    max_size=20,
    batch_size=6,
    cooldown_minutes=30,
    allowed_invokers="admins",
    include_invite_phrase=True,
    default_cta="Играть",
    tone="mystic",
    max_length=400
)
```

### Тоны сообщений

- **mystic** - мистический тон с эмодзи и атмосферой
- **thematic** - тематический тон игры
- **mob** - краткий мобильный стиль
- **neutral** - нейтральный деловой стиль

## 🔄 Система созыва

### Алгоритм работы

1. Проверка прав вызывающего
2. Проверка cooldown для вызывающего
3. Получение списка участников леса
4. Фильтрация по opt-in и cooldown участников
5. Разбивка на батчи
6. Отправка сообщений с интервалом 500ms
7. Обновление времени последнего вызова

### Батчинг

- Размер батча настраивается (по умолчанию 6)
- Пауза между батчами 500ms
- HTML-упоминания участников
- Callback-кнопки для быстрого ответа

## 🛡️ Безопасность

- Проверка прав на созыв
- Cooldown защита от спама
- Валидация входных данных
- Экранирование HTML-символов
- Ограничение размера сообщений

## 📊 Мониторинг

### Логирование

Все действия логируются с уровнем INFO:
- Создание лесов
- Присоединение/покидание участников
- Созывы и результаты
- Ошибки и исключения

### Метрики

- Количество участников в лесах
- Успешность созывов
- Ошибки отправки
- Время выполнения операций

## 🐛 Отладка

### Проверка состояния

```python
# Получить информацию о лесе
forest = await forest_manager.get_forest_info(forest_id)

# Получить участников
members = await forest_manager.get_forest_members(forest_id)

# Проверить cooldown
can_summon, remaining = summon_system.get_cooldown_status(user_id, forest_id, 30)
```

### Логи

```bash
# Включить подробное логирование
export LOG_LEVEL=DEBUG
python bot_with_forests.py
```

## 🚀 Развертывание

### 1. Примените миграцию

```bash
python apply_forest_migration.py
```

### 2. Настройте переменные окружения

```bash
export BOT_TOKEN="your_bot_token"
export DATABASE_URL="your_database_url"
```

### 3. Запустите бота

```bash
python bot_with_forests.py
```

## 📈 Производительность

### Рекомендации

- Размер батча: 6-8 участников
- Cooldown: 30 минут
- Пауза между батчами: 500ms
- Максимальная длина сообщения: 400 символов

### Ограничения

- Максимум 100 участников в лесу
- Максимум 10 батчей за один созыв
- Cooldown минимум 5 минут

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте логи бота
2. Убедитесь в корректности миграции БД
3. Проверьте права доступа к БД
4. Убедитесь в корректности токена бота

## 📄 Лицензия

Система лесов является частью проекта "Лес и Волки" и распространяется под той же лицензией.
