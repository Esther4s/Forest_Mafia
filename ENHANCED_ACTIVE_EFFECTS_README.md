# 🎯 Улучшенная система активных эффектов

## 📋 Описание

Система активных эффектов была значительно улучшена для полноценного отслеживания эффектов предметов в игре Forest Mafia. Теперь система поддерживает детальное отслеживание использования, срабатывания и истечения эффектов.

## 🆕 Новые возможности

### 📊 Расширенная структура таблицы `active_effects`

Добавлены новые колонки:

| Колонка | Тип | Описание |
|---------|-----|----------|
| `used_at` | TIMESTAMP | Время использования эффекта |
| `triggered_by` | VARCHAR(100) | Что вызвало срабатывание эффекта |
| `duration_rounds` | INTEGER | Количество раундов действия эффекта |
| `remaining_uses` | INTEGER | Количество оставшихся использований |
| `effect_status` | VARCHAR(50) | Статус эффекта (active, expired, used, cancelled) |
| `trigger_conditions` | JSONB | Условия срабатывания эффекта |
| `last_triggered_at` | TIMESTAMP | Время последнего срабатывания |
| `auto_remove` | BOOLEAN | Автоматически удалять при истечении |
| `updated_at` | TIMESTAMP | Время последнего обновления |

### 🎮 Типы эффектов

- **`consumable`** - Расходный предмет (используется один раз)
- **`boost`** - Усиление (действует несколько раундов)
- **`permanent`** - Постоянный эффект
- **`temporary`** - Временный эффект

### 🎪 Типы триггеров

- **`item_use`** - Использование предмета
- **`game_start`** - Начало игры
- **`game_end`** - Конец игры
- **`night_phase`** - Ночная фаза
- **`day_phase`** - Дневная фаза
- **`round_start`** - Начало раунда
- **`round_end`** - Конец раунда
- **`player_death`** - Смерть игрока
- **`manual`** - Ручное управление

## 🚀 Установка и настройка

### 1. Обновление структуры базы данных

```bash
python improve_active_effects_table.py
```

### 2. Интеграция функций

```bash
python integrate_enhanced_effects.py
```

### 3. Тестирование системы

```bash
python test_enhanced_effects_system.py
```

## 📚 Использование

### Базовое использование

```python
from active_effect_manager import effect_manager

# Добавление эффекта
effect_manager.add_item_effect(
    user_id=12345,
    item_name="🎭 Активная роль",
    effect_type="boost",
    effect_data={"power": 99},
    duration_rounds=3,
    remaining_uses=1,
    trigger_conditions={"phase": "waiting"}
)

# Получение эффектов пользователя
effects = effect_manager.get_user_effects(user_id=12345)

# Срабатывание эффектов для события
triggered = effect_manager.trigger_effects_for_event(
    user_id=12345,
    event_type="game_start",
    event_data={"game_phase": "night"}
)
```

### Расширенное использование

```python
from enhanced_active_effects_functions import *

# Добавление эффекта с полными параметрами
add_enhanced_active_effect(
    user_id=12345,
    item_name="🌿 Лесная маскировка",
    effect_type="consumable",
    effect_data={"stealth": True},
    game_id="game_123",
    chat_id=67890,
    duration_rounds=1,
    remaining_uses=1,
    triggered_by="item_use",
    trigger_conditions={"event_types": ["night_phase"]},
    auto_remove=True
)

# Срабатывание эффекта
trigger_effect(
    effect_id=effect_id,
    triggered_by="night_phase",
    trigger_data={"round": 1, "phase": "night"}
)

# Получение статистики
stats = get_effect_statistics(user_id=12345)
```

## 🔧 API функций

### `add_enhanced_active_effect()`

Добавляет активный эффект с расширенными параметрами.

**Параметры:**
- `user_id` (int) - ID пользователя
- `item_name` (str) - Название предмета
- `effect_type` (str) - Тип эффекта
- `effect_data` (dict) - Данные эффекта
- `game_id` (str) - ID игры
- `chat_id` (int) - ID чата
- `expires_at` (str) - Время истечения
- `duration_rounds` (int) - Длительность в раундах
- `remaining_uses` (int) - Количество использований
- `triggered_by` (str) - Что вызвало срабатывание
- `trigger_conditions` (dict) - Условия срабатывания
- `auto_remove` (bool) - Автоудаление

### `get_enhanced_active_effects()`

Получает активные эффекты с фильтрацией.

**Параметры:**
- `user_id` (int) - ID пользователя
- `game_id` (str) - ID игры
- `chat_id` (int) - ID чата
- `status` (str) - Статус эффектов

### `trigger_effect()`

Срабатывает эффект и обновляет статистику.

**Параметры:**
- `effect_id` (int) - ID эффекта
- `triggered_by` (str) - Причина срабатывания
- `trigger_data` (dict) - Данные срабатывания

### `cleanup_expired_effects()`

Очищает истекшие эффекты.

**Возвращает:** Количество удаленных эффектов

## 🎯 Менеджер активных эффектов

Класс `ActiveEffectManager` предоставляет удобный интерфейс для работы с эффектами:

```python
from active_effect_manager import effect_manager

# Добавление эффекта
effect_manager.add_item_effect(...)

# Получение эффектов
effects = effect_manager.get_user_effects(user_id)

# Срабатывание для события
triggered = effect_manager.trigger_effects_for_event(
    user_id, event_type, event_data
)

# Форматирование информации
info = effect_manager.format_effect_info(effect)

# Статистика
stats = effect_manager.get_effect_statistics(user_id)
```

## 📊 Мониторинг и статистика

### Получение статистики

```python
stats = get_effect_statistics(user_id=12345, game_id="game_123")

# Результат:
{
    'status_breakdown': [
        {'effect_status': 'active', 'count': 5, 'avg_remaining_uses': 2.4},
        {'effect_status': 'used', 'count': 3, 'avg_remaining_uses': 0.0}
    ],
    'effect_types': [
        {'effect_type': 'boost', 'item_name': '🎭 Активная роль', 'count': 2},
        {'effect_type': 'consumable', 'item_name': '🌿 Лесная маскировка', 'count': 1}
    ],
    'triggers': [
        {'triggered_by': 'item_use', 'count': 4},
        {'triggered_by': 'game_start', 'count': 2}
    ]
}
```

### Автоматическая очистка

Система автоматически очищает истекшие эффекты:

```python
# Ручная очистка
cleaned_count = cleanup_expired_effects()

# Автоматическая очистка (рекомендуется запускать периодически)
# Можно добавить в cron или планировщик задач
```

## 🔍 Отладка и логирование

Все функции поддерживают детальное логирование:

```python
import logging

# Настройка уровня логирования
logging.basicConfig(level=logging.DEBUG)

# Логи будут показывать:
# - Добавление эффектов
# - Срабатывание эффектов
# - Ошибки и предупреждения
# - Статистику операций
```

## ⚠️ Важные замечания

1. **Резервные копии**: Перед обновлением создаются резервные копии файлов
2. **Совместимость**: Новые функции совместимы со старыми
3. **Производительность**: Добавлены индексы для быстрого поиска
4. **Безопасность**: Все SQL-запросы используют параметризованные запросы

## 🐛 Устранение неполадок

### Проблема: Таблица не обновлена

**Решение:**
```bash
python improve_active_effects_table.py
```

### Проблема: Функции не найдены

**Решение:**
```bash
python integrate_enhanced_effects.py
```

### Проблема: Ошибки в тестах

**Решение:**
1. Проверьте подключение к базе данных
2. Убедитесь, что таблица обновлена
3. Проверьте права доступа к базе данных

## 📈 Планы развития

- [ ] Веб-интерфейс для мониторинга эффектов
- [ ] API для внешних интеграций
- [ ] Машинное обучение для оптимизации эффектов
- [ ] Графики и аналитика использования эффектов

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте логи
2. Запустите тесты
3. Проверьте структуру базы данных
4. Обратитесь к разработчикам

---

**Версия:** 2.0  
**Дата обновления:** $(date)  
**Автор:** Forest Mafia Development Team
