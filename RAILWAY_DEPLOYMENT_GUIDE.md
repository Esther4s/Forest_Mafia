# 🚀 Развертывание улучшенной системы активных эффектов в Railway

## 📋 Обзор

Это руководство поможет вам развернуть улучшенную систему активных эффектов в Railway с автоматическим обновлением базы данных.

## 🎯 Варианты развертывания

### Вариант 1: Быстрое развертывание (Рекомендуется)

```bash
python quick_railway_deploy.py
```

Этот скрипт:
- ✅ Автоматически обновляет `database_psycopg2.py`
- ✅ Создает скрипт запуска `start.sh`
- ✅ Создает `Procfile` для Railway
- ✅ Коммитит и пушит изменения

### Вариант 2: Полное развертывание

```bash
python deploy_enhanced_effects_to_railway.py
```

Этот скрипт:
- ✅ Проверяет Railway CLI
- ✅ Обновляет все файлы
- ✅ Создает детальные скрипты
- ✅ Настраивает переменные окружения

## 🔧 Ручное развертывание

### Шаг 1: Подготовка файлов

```bash
# 1. Обновляем database_psycopg2.py
python integrate_enhanced_effects.py

# 2. Создаем скрипт запуска
cat > start.sh << 'EOF'
#!/bin/bash
echo "🚀 Запуск Forest Mafia Bot с улучшенными эффектами..."

# Обновляем БД при запуске
python3 -c "
try:
    from improve_active_effects_table import improve_active_effects_table
    improve_active_effects_table()
    print('✅ БД обновлена')
except Exception as e:
    print(f'⚠️ Ошибка БД: {e}')
"

# Запускаем бота
python3 bot.py
EOF

chmod +x start.sh

# 3. Создаем Procfile
echo "web: bash start.sh" > Procfile
```

### Шаг 2: Коммит и push

```bash
git add .
git commit -m "🚀 Railway: Обновление системы активных эффектов"
git push origin master
```

## 📊 Структура файлов для Railway

```
Forest_Mafia-master/
├── bot.py                          # Основной бот
├── database_psycopg2.py            # Обновленная БД с новыми функциями
├── improve_active_effects_table.py # Миграция БД
├── enhanced_active_effects_functions.py # Новые функции
├── active_effect_manager.py        # Менеджер эффектов
├── start.sh                        # Скрипт запуска
├── Procfile                        # Конфигурация Railway
├── requirements.txt                # Зависимости
└── railway.json                    # Настройки Railway
```

## ⚙️ Настройка переменных окружения в Railway

### Обязательные переменные:

1. **DATABASE_URL** - URL подключения к PostgreSQL
2. **BOT_TOKEN** - Токен Telegram бота

### Дополнительные переменные:

3. **LOG_LEVEL** - Уровень логирования (DEBUG, INFO, WARNING, ERROR)
4. **ENVIRONMENT** - Окружение (production, development)

## 🔍 Проверка развертывания

### 1. Проверка логов

```bash
# В Railway Dashboard или через CLI
railway logs
```

### 2. Проверка статуса

```bash
railway status
```

### 3. Проверка базы данных

```bash
# Подключение к БД через Railway
railway connect postgres
```

## 🐛 Устранение неполадок

### Проблема: Бот не запускается

**Решение:**
1. Проверьте логи в Railway Dashboard
2. Убедитесь, что все переменные окружения установлены
3. Проверьте, что `start.sh` имеет права на выполнение

### Проблема: Ошибка подключения к БД

**Решение:**
1. Проверьте `DATABASE_URL` в переменных окружения
2. Убедитесь, что база данных доступна
3. Проверьте права доступа

### Проблема: Таблица не обновляется

**Решение:**
1. Проверьте, что `improve_active_effects_table.py` выполняется
2. Проверьте логи на ошибки миграции
3. Запустите миграцию вручную

## 📈 Мониторинг

### Логи для отслеживания:

- `✅ БД обновлена` - Успешное обновление БД
- `✅ Активный эффект добавлен` - Добавление эффекта
- `✅ Эффект сработал` - Срабатывание эффекта
- `✅ Удалено X истекших эффектов` - Очистка эффектов

### Метрики для мониторинга:

- Количество активных эффектов
- Частота срабатывания эффектов
- Ошибки в работе с БД
- Время отклика бота

## 🔄 Автоматическое обновление

### Настройка cron для очистки эффектов:

```bash
# Добавьте в Railway переменную окружения
CLEANUP_SCHEDULE="0 */6 * * *"  # Каждые 6 часов
```

### Скрипт автоматической очистки:

```python
# В bot.py добавьте:
import schedule
import time

def cleanup_effects():
    from database_psycopg2 import cleanup_expired_effects
    cleaned = cleanup_expired_effects()
    logger.info(f"🧹 Автоматически очищено {cleaned} эффектов")

# Запуск очистки каждые 6 часов
schedule.every(6).hours.do(cleanup_effects)
```

## 🚀 Продвинутые настройки

### 1. Масштабирование

```yaml
# railway.json
{
  "deploy": {
    "startCommand": "bash start.sh",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

### 2. Мониторинг производительности

```python
# Добавьте в bot.py
import psutil

def log_system_stats():
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent
    logger.info(f"📊 CPU: {cpu_percent}%, Memory: {memory_percent}%")
```

### 3. Резервное копирование

```bash
# Создайте скрипт backup.sh
#!/bin/bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи** в Railway Dashboard
2. **Проверьте переменные окружения**
3. **Запустите тесты** локально
4. **Обратитесь к документации Railway**

## 🎉 Готово!

После успешного развертывания ваша система активных эффектов будет:

- ✅ Автоматически обновлять структуру БД при запуске
- ✅ Отслеживать использование предметов
- ✅ Управлять жизненным циклом эффектов
- ✅ Очищать истекшие эффекты
- ✅ Предоставлять детальную статистику

**Удачного развертывания! 🚀**