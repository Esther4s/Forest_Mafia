# 🚀 Быстрый старт с database_psycopg2.py

## 📋 Что создано

1. **`database_psycopg2.py`** - основной модуль для работы с PostgreSQL
2. **`test_database_psycopg2.py`** - тестовый файл
3. **`bot_integration_example.py`** - пример интеграции с ботом
4. **`requirements_psycopg2.txt`** - зависимости

## ⚡ Быстрая установка

```bash
# 1. Установить зависимости
pip install psycopg2-binary python-dotenv

# 2. Установить переменную окружения
export DATABASE_URL="postgresql://user:password@host:port/database"

# 3. Запустить тест
python test_database_psycopg2.py
```

## 🔧 Основные функции

### Инициализация
```python
from database_psycopg2 import init_db, close_db

# Подключение
db = init_db()

# Закрытие
close_db()
```

### Выполнение запросов
```python
from database_psycopg2 import execute_query, fetch_query, fetch_one

# INSERT/UPDATE/DELETE
execute_query("INSERT INTO users (user_id, username) VALUES (%s, %s)", (123, "user"))

# SELECT (все записи)
users = fetch_query("SELECT * FROM users WHERE balance > %s", (50,))

# SELECT (одна запись)
user = fetch_one("SELECT * FROM users WHERE user_id = %s", (123,))
```

### Удобные функции
```python
from database_psycopg2 import create_user, get_user_by_telegram_id, update_user_balance

# Создание пользователя
create_user(123456, "username")

# Получение пользователя
user = get_user_by_telegram_id(123456)

# Обновление баланса
update_user_balance(123456, 100.50)
```

## 🎯 Интеграция с ботом

```python
# В начале bot.py
from database_psycopg2 import init_db, create_user, get_user_by_telegram_id

# Инициализация при запуске
db = init_db()

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Создаем пользователя
    create_user(user_id, username)
    user = get_user_by_telegram_id(user_id)
    
    bot.reply_to(message, f"Привет! Баланс: {user['balance']} руб.")
```

## 🔍 Тестирование

```bash
# Запуск тестов
python test_database_psycopg2.py

# Ожидаемый вывод:
# ✅ База данных инициализирована
# ✅ Подключение к базе данных успешно
# ✅ SELECT запрос: [{'test_value': 1}]
# ✅ Пользователь создан с ID: 1
# ✅ Пользователь найден: test_user_psycopg2, баланс: 0.00
# ✅ Баланс обновлен
# ✅ Новый баланс: 100.50
# ✅ Найдено товаров в магазине: 8
# ✅ Статистика обновлена
# ✅ Тестовые данные очищены
# 🎉 Все тесты пройдены успешно!
```

## 🛠️ Особенности

- ✅ **Автоматическое переподключение** при разрыве соединения
- ✅ **Пул соединений** для эффективности
- ✅ **Обработка ошибок** с логированием
- ✅ **Типизация** для IDE поддержки
- ✅ **Безопасность** - защита от SQL-инъекций

## 📊 Готовые таблицы

Модуль работает с таблицами из `complete_database_schema.sql`:

- `users` - пользователи бота
- `user_games` - игры пользователей  
- `stats` - статистика игроков
- `shop` - магазин товаров
- `purchases` - история покупок

## 🚨 Важно

1. **Установите DATABASE_URL** в переменных окружения
2. **Создайте таблицы** используя `complete_database_schema.sql`
3. **Инициализируйте** базу данных перед использованием
4. **Закрывайте** подключение в конце программы

## 📞 Поддержка

При возникновении проблем:
1. Проверьте `DATABASE_URL`
2. Убедитесь, что таблицы созданы
3. Запустите тесты для диагностики
4. Проверьте логи в консоли
