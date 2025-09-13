# 🗄️ Схема базы данных Лес и волки Bot

## 📋 Описание

Этот проект содержит SQL-скрипты для создания полной схемы базы данных PostgreSQL для игрового бота Лес и волки.

## 📁 Файлы

### 1. `complete_database_schema.sql`
**Полная схема базы данных** - включает все существующие таблицы игрового бота + новые таблицы для расширенной функциональности.

### 2. `new_tables_schema.sql`
**Только новые таблицы** - содержит только 5 новых таблиц, которые вы запросили.

## 🏗️ Структура таблиц

### Существующие таблицы (из игрового бота):
- `games` - информация об играх
- `players` - игроки в играх
- `game_events` - события игр
- `player_actions` - действия игроков
- `votes` - голосования
- `player_stats` - статистика игроков (legacy)
- `bot_settings` - настройки бота

### Новые таблицы (запрошенные):

#### 1. `users` - Основная таблица пользователей
```sql
- id (SERIAL PRIMARY KEY)
- user_id (BIGINT UNIQUE) - Telegram user ID
- username (VARCHAR) - Имя пользователя
- balance (DECIMAL) - Баланс пользователя
- created_at (TIMESTAMP)
```

#### 2. `user_games` - Игры пользователей
```sql
- id (SERIAL PRIMARY KEY)
- user_id (BIGINT) - Ссылка на users.user_id
- game_type (VARCHAR) - Тип игры
- status (VARCHAR) - Статус игры
- created_at, updated_at (TIMESTAMP)
```

#### 3. `stats` - Расширенная статистика
```sql
- id (SERIAL PRIMARY KEY)
- user_id (BIGINT) - Ссылка на users.user_id
- games_played (INTEGER) - Количество сыгранных игр
- games_won (INTEGER) - Количество выигранных игр
- games_lost (INTEGER) - Количество проигранных игр
- last_played (TIMESTAMP) - Последняя игра
```

#### 4. `shop` - Магазин товаров
```sql
- id (SERIAL PRIMARY KEY)
- item_name (VARCHAR UNIQUE) - Название товара
- price (DECIMAL) - Цена товара
- description (TEXT) - Описание
- category (VARCHAR) - Категория товара
- is_active (BOOLEAN) - Активен ли товар
```

#### 5. `purchases` - История покупок
```sql
- id (SERIAL PRIMARY KEY)
- user_id (BIGINT) - Ссылка на users.user_id
- item_id (INTEGER) - Ссылка на shop.id
- purchased_at (TIMESTAMP) - Время покупки
- quantity (INTEGER) - Количество
- total_price (DECIMAL) - Общая стоимость
```

## 🔗 Связи между таблицами

Все связи настроены с `ON DELETE CASCADE`:

- `user_games.user_id` → `users.user_id`
- `stats.user_id` → `users.user_id`
- `purchases.user_id` → `users.user_id`
- `purchases.item_id` → `shop.id`

## ⚡ Особенности

### Автоматические триггеры
- Автоматическое обновление `updated_at` при изменении записей
- Триггеры созданы для всех таблиц с полем `updated_at`

### Индексы для производительности
- Индексы на всех внешних ключах
- Индексы на часто используемых полях поиска
- Уникальные индексы для предотвращения дублирования

### Представления (Views)
- `user_full_stats` - полная статистика пользователя с процентом побед
- `top_players` - топ игроков по количеству побед

### Начальные данные
- 8 базовых товаров в магазине (маски, инструменты, специальные предметы)

## 🚀 Использование

### Для полной схемы:
```bash
psql -d your_database -f complete_database_schema.sql
```

### Для только новых таблиц:
```bash
psql -d your_database -f new_tables_schema.sql
```

## 📊 Типы данных

- `SERIAL` - автоинкрементный первичный ключ
- `BIGINT` - для Telegram user ID (может быть очень большим)
- `DECIMAL(10,2)` - для денежных сумм (точность до копеек)
- `VARCHAR` - для текстовых полей переменной длины
- `TEXT` - для длинных описаний
- `JSONB` - для JSON данных (PostgreSQL)
- `TIMESTAMP` - для дат и времени
- `BOOLEAN` - для логических значений

## 🔒 Безопасность

- Все внешние ключи с `ON DELETE CASCADE`
- Уникальные ограничения для предотвращения дублирования
- Правильные типы данных для всех полей
- Индексы для оптимизации производительности

## 📈 Расширяемость

Схема легко расширяется:
- Добавление новых полей в существующие таблицы
- Создание новых таблиц с правильными связями
- Добавление новых индексов по мере необходимости
- Создание дополнительных представлений для аналитики
