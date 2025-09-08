# 🗄️ Модуль database.py для PostgreSQL на Railway

## 📋 Описание

Модуль `database_psycopg2.py` предоставляет удобный интерфейс для работы с PostgreSQL базой данных на Railway, используя библиотеку `psycopg2`.

## 🚀 Особенности

- ✅ **Пул соединений** - эффективное управление подключениями
- ✅ **Автоматическое переподключение** - при разрыве соединения
- ✅ **Обработка ошибок** - с логированием и повторными попытками
- ✅ **Контекстные менеджеры** - безопасная работа с соединениями
- ✅ **Типизация** - полная поддержка type hints
- ✅ **Удобные функции** - для работы с новыми таблицами

## 📦 Установка зависимостей

```bash
pip install -r requirements_psycopg2.txt
```

Или вручную:
```bash
pip install psycopg2-binary python-dotenv
```

## 🔧 Настройка

### 1. Переменные окружения

Создайте файл `.env` или установите переменную окружения:

```bash
DATABASE_URL=postgresql://username:password@host:port/database
```

Пример для Railway:
```bash
DATABASE_URL=postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway
```

### 2. Инициализация

```python
from database_psycopg2 import init_db, close_db

# Инициализация базы данных
db = init_db()

# Ваш код здесь...

# Закрытие подключения (в конце программы)
close_db()
```

## 📚 Основные функции

### 1. `init_db(database_url=None)`
Инициализирует подключение к базе данных.

```python
# Читает DATABASE_URL из переменных окружения
db = init_db()

# Или передать URL напрямую
db = init_db("postgresql://user:pass@host:port/db")
```

### 2. `execute_query(query, params=None)`
Выполняет INSERT/UPDATE/DELETE запросы.

```python
# Вставка данных
query = "INSERT INTO users (user_id, username) VALUES (%s, %s)"
affected = execute_query(query, (123456, "username"))

# Обновление данных
query = "UPDATE users SET balance = %s WHERE user_id = %s"
affected = execute_query(query, (100.50, 123456))

# Удаление данных
query = "DELETE FROM users WHERE user_id = %s"
affected = execute_query(query, (123456,))
```

### 3. `fetch_query(query, params=None, fetch_one=False)`
Выполняет SELECT запросы и возвращает результат.

```python
# Получение всех записей
query = "SELECT * FROM users WHERE balance > %s"
users = fetch_query(query, (50.0,))

# Получение одной записи
query = "SELECT * FROM users WHERE user_id = %s"
user = fetch_query(query, (123456,), fetch_one=True)
```

### 4. `fetch_one(query, params=None)`
Удобная функция для получения одной записи.

```python
query = "SELECT * FROM users WHERE user_id = %s"
user = fetch_one(query, (123456,))
```

### 5. `execute_many(query, params_list)`
Выполняет batch операции.

```python
query = "INSERT INTO purchases (user_id, item_id, quantity) VALUES (%s, %s, %s)"
params_list = [
    (123456, 1, 2),
    (123456, 2, 1),
    (789012, 1, 3)
]
affected = execute_many(query, params_list)
```

## 🛠️ Удобные функции для новых таблиц

### Работа с пользователями

```python
# Создание пользователя
user_id = create_user(123456, "username")

# Получение пользователя
user = get_user_by_telegram_id(123456)

# Обновление баланса
success = update_user_balance(123456, 150.75)
```

### Работа с магазином

```python
# Получение товаров
items = get_shop_items()

# Создание покупки
success = create_purchase(123456, item_id=1, quantity=2)
```

### Работа со статистикой

```python
# Получение статистики
stats = get_user_stats(123456)

# Обновление статистики
success = update_user_stats(
    user_id=123456,
    games_played=10,
    games_won=7,
    games_lost=3
)
```

## 🔄 Обработка ошибок и переподключение

Модуль автоматически обрабатывает:

- **Разрывы соединения** - автоматическое переподключение
- **Временные ошибки** - повторные попытки с экспоненциальной задержкой
- **Логирование** - подробные логи всех операций

```python
try:
    result = fetch_query("SELECT * FROM users")
except Exception as e:
    print(f"Ошибка: {e}")
    # Модуль автоматически попытается переподключиться
```

## 📊 Примеры использования

### Полный пример

```python
#!/usr/bin/env python3
from database_psycopg2 import (
    init_db, close_db, 
    create_user, get_user_by_telegram_id,
    get_shop_items, create_purchase,
    get_user_stats, update_user_stats
)

def main():
    try:
        # Инициализация
        db = init_db()
        print("✅ База данных подключена")
        
        # Создание пользователя
        user_id = 123456789
        create_user(user_id, "test_user")
        print(f"✅ Пользователь {user_id} создан")
        
        # Получение пользователя
        user = get_user_by_telegram_id(user_id)
        print(f"✅ Пользователь найден: {user['username']}")
        
        # Получение товаров из магазина
        items = get_shop_items()
        print(f"✅ Товаров в магазине: {len(items)}")
        
        # Создание покупки (если есть товары)
        if items:
            success = create_purchase(user_id, items[0]['id'], 1)
            print(f"✅ Покупка создана: {success}")
        
        # Обновление статистики
        update_user_stats(user_id, games_played=1, games_won=1)
        print("✅ Статистика обновлена")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        close_db()

if __name__ == "__main__":
    main()
```

### Интеграция с ботом

```python
# В вашем bot.py
from database_psycopg2 import init_db, create_user, get_user_by_telegram_id

# Инициализация при запуске бота
db = init_db()

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Создаем или получаем пользователя
    create_user(user_id, username)
    user = get_user_by_telegram_id(user_id)
    
    bot.reply_to(message, f"Привет, {user['username']}! Ваш баланс: {user['balance']}")
```

## 🔒 Безопасность

- **Параметризованные запросы** - защита от SQL-инъекций
- **Пул соединений** - ограничение количества подключений
- **Автоматическое закрытие** - предотвращение утечек соединений
- **Логирование** - отслеживание всех операций

## 📈 Производительность

- **Пул соединений** - переиспользование подключений
- **Batch операции** - эффективная вставка множественных записей
- **Индексы** - быстрый поиск по ключевым полям
- **Кэширование** - минимизация запросов к базе данных

## 🐛 Отладка

Включите подробное логирование:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Это покажет все SQL-запросы и операции с базой данных.

## 📝 Примечания

- Модуль автоматически парсит `DATABASE_URL` из переменных окружения
- Все функции возвращают типизированные результаты
- Поддерживается как PostgreSQL, так и другие базы данных через psycopg2
- Модуль готов к использованию в продакшене на Railway
