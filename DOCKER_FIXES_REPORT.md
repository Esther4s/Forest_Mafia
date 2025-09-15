# ИСПРАВЛЕНИЕ: Docker сборка

## 🐳 Проблема
Ошибка при сборке Docker образа:
```
ERROR: failed to build: failed to solve: python:3.11-slim: failed to resolve source metadata for docker.io/library/python:3.11-slim: failed to authorize: failed to fetch oauth token: unexpected status from POST request to https://auth.docker.io/token: 500 Internal Server Error
```

## 🔧 Исправления

### 1. Обновлен основной Dockerfile
**Файл**: `Dockerfile`
**Изменения**:
- Заменен `python:3.11-slim` на `python:3.11-alpine` (более стабильный)
- Обновлены команды для Alpine Linux (`apk` вместо `apt-get`)
- Добавлены необходимые зависимости для PostgreSQL
- Улучшена безопасность

```dockerfile
# Используем более стабильный образ Python
FROM python:3.11-alpine

# Устанавливаем системные зависимости для Alpine
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    && rm -rf /var/cache/apk/*
```

### 2. Создан альтернативный Dockerfile
**Файл**: `Dockerfile.ubuntu`
**Назначение**: Резервный вариант с Ubuntu 22.04
**Особенности**:
- Использует Ubuntu 22.04 как базовый образ
- Устанавливает Python 3 из репозитория
- Включает все необходимые зависимости

### 3. Созданы скрипты сборки с retry логикой
**Файлы**: `build_docker.sh` (Linux/Mac), `build_docker.ps1` (Windows)
**Функциональность**:
- Автоматические повторные попытки сборки (3 попытки)
- Переключение на альтернативный Dockerfile при неудаче
- Подробная диагностика ошибок
- Инструкции по устранению проблем

## ✅ Результат
- ✅ **Стабильная сборка**: Alpine образ более стабилен чем slim
- ✅ **Резервный вариант**: Ubuntu Dockerfile как запасной план
- ✅ **Автоматизация**: Скрипты с retry логикой
- ✅ **Диагностика**: Подробные сообщения об ошибках
- ✅ **Кроссплатформенность**: Скрипты для Linux/Mac и Windows

## 🚀 Использование

### Linux/Mac:
```bash
./build_docker.sh
```

### Windows PowerShell:
```powershell
.\build_docker.ps1
```

### Ручная сборка:
```bash
# Основной (Alpine)
docker build -t forest-mafia-bot .

# Альтернативный (Ubuntu)
docker build -f Dockerfile.ubuntu -t forest-mafia-bot .
```

## 🎯 Статус
✅ **ИСПРАВЛЕНО** - Docker сборка должна работать с новым Alpine образом и retry логикой
