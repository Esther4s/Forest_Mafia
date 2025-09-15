# Руководство по миграции на новую архитектуру

## Обзор

Данное руководство поможет вам перейти с оригинальной архитектуры на рефакторированную версию с применением принципов чистой архитектуры.

## Преимущества новой архитектуры

### ✅ Что улучшилось

1. **Читаемость кода**
   - Четкое разделение ответственности
   - Понятные имена классов и методов
   - Подробная документация

2. **Поддерживаемость**
   - Модульная структура
   - Легкое добавление новых функций
   - Простое тестирование

3. **Расширяемость**
   - Интерфейсы для замены реализаций
   - Фабрики для создания объектов
   - Сервисы для бизнес-логики

4. **Безопасность типов**
   - Value Objects с валидацией
   - Типизированные параметры
   - Защита от некорректных данных

## Структура новой архитектуры

```
src/
├── domain/              # Доменный слой
│   ├── entities.py      # Основные сущности
│   ├── value_objects.py # Value Objects
│   ├── repositories.py  # Интерфейсы репозиториев
│   └── role_actions.py  # Действия ролей
├── application/         # Слой приложения
│   ├── services.py      # Сервисы приложения
│   ├── factories.py     # Фабрики
│   ├── bot_service.py   # Основной сервис бота
│   ├── command_handlers.py    # Обработчики команд
│   └── callback_handlers.py   # Обработчики callback'ов
├── infrastructure/      # Инфраструктурный слой
│   ├── repositories.py  # Реализации репозиториев
│   ├── config.py        # Конфигурация
│   └── bot_main.py      # Точка входа
└── examples/            # Примеры использования
    └── usage_example.py # Демонстрация возможностей
```

## Пошаговая миграция

### Шаг 1: Установка зависимостей

Убедитесь, что у вас установлены все необходимые зависимости:

```bash
pip install python-telegram-bot python-dotenv
```

### Шаг 2: Настройка конфигурации

Создайте файл `.env` в корне проекта:

```env
BOT_TOKEN=your_bot_token_here
DATABASE_URL=sqlite:///forest_mafia.db
TEST_MODE=false
DEBUG_MODE=false
LOG_LEVEL=INFO
```

### Шаг 3: Запуск новой версии

Для запуска рефакторированной версии используйте:

```python
from src.infrastructure.bot_main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
```

### Шаг 4: Тестирование

Запустите примеры для проверки работоспособности:

```python
from src.examples.usage_example import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
```

## Основные изменения

### 1. Value Objects

**Было:**
```python
user_id = 12345  # Простое число
```

**Стало:**
```python
user_id = UserId(12345)  # Типизированный объект с валидацией
```

### 2. Сервисы

**Было:**
```python
# Логика разбросана по разным файлам
game.add_player(user_id, username)
```

**Стало:**
```python
# Централизованная логика в сервисах
await game_service.add_player_to_game(game, user_id, username)
```

### 3. Репозитории

**Было:**
```python
# Прямая работа с БД
db.execute("INSERT INTO games ...")
```

**Стало:**
```python
# Абстракция через репозитории
await game_repo.save(game)
```

### 4. Фабрики

**Было:**
```python
# Сложная инициализация
game = Game(chat_id, thread_id, is_test_mode, ...)
```

**Стало:**
```python
# Простое создание через фабрику
game = game_factory.create_game(chat_id, thread_id, is_test_mode)
```

## Совместимость

### ✅ Что осталось без изменений

1. **Команды бота** - все команды работают как прежде
2. **API Telegram** - интерфейс взаимодействия не изменился
3. **Форматы данных** - структура данных сохранена
4. **Функциональность** - все возможности остались

### 🔄 Что изменилось

1. **Внутренняя архитектура** - код переструктурирован
2. **Обработка ошибок** - улучшена валидация
3. **Логирование** - добавлено подробное логирование
4. **Тестирование** - упрощено создание тестов

## Примеры использования

### Создание игры

```python
# Создание игры через фабрику
game = game_factory.create_game(
    chat_id=ChatId(12345),
    thread_id=None,
    is_test_mode=True
)

# Сохранение через репозиторий
await game_repo.save(game)
```

### Добавление игрока

```python
# Создание пользователя
user_id = UserId(12345)
username = Username("test_user")

# Добавление в игру через сервис
success = await game_service.add_player_to_game(game, user_id, username)
```

### Обработка голосования

```python
# Голосование через сервис
result = await bot_service.vote(chat_id, voter_id, target_id)

# Обработка результатов
exiled_player = voting_service.process_voting(game)
```

## Отладка и логирование

### Включение отладки

```env
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

### Просмотр логов

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Тестирование

### Unit тесты

```python
def test_player_creation():
    user_id = UserId(12345)
    username = Username("test_user")
    player = Player(user_id, username, Role.HARE, Team.HERBIVORES)
    assert player.user_id == user_id
    assert player.role == Role.HARE
```

### Интеграционные тесты

```python
async def test_game_flow():
    game = game_factory.create_game(ChatId(12345))
    await game_repo.save(game)
    
    # Тестируем игровой процесс
    assert game.phase == GamePhase.WAITING
```

## Производительность

### Оптимизации

1. **Кэширование** - активные игры кэшируются в памяти
2. **Ленивая загрузка** - данные загружаются по требованию
3. **Батчинг** - группировка операций с БД

### Мониторинг

```python
# Метрики производительности
logger.info(f"Время выполнения операции: {execution_time}ms")
logger.info(f"Количество активных игр: {len(active_games)}")
```

## Поддержка и развитие

### Добавление новых функций

1. **Новая роль** - добавьте класс в `role_actions.py`
2. **Новая команда** - добавьте обработчик в `command_handlers.py`
3. **Новая фаза** - добавьте в `value_objects.py`

### Расширение функциональности

```python
# Добавление нового сервиса
class NewFeatureService:
    def __init__(self, repo: SomeRepository):
        self.repo = repo
    
    async def do_something(self):
        # Логика нового сервиса
        pass
```

## Заключение

Новая архитектура предоставляет:

- 🏗️ **Прочную основу** для дальнейшего развития
- 🔧 **Инструменты** для быстрой разработки
- 🧪 **Возможности** для качественного тестирования
- 📈 **Масштабируемость** для роста проекта

Миграция на новую архитектуру - это инвестиция в будущее проекта, которая окупится повышением качества кода и скорости разработки.
