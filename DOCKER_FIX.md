# 🐳 Исправление проблемы Docker

## ❌ Проблема
```
/bin/sh: 1: apk: not found
ERROR: failed to build: failed to solve: process "/bin/sh -c apk add --no-cache..." did not complete successfully: exit code: 127
```

## 🔍 Причина
Dockerfile использовал команды Alpine Linux (`apk`), но базовый образ `python:3.11` основан на Debian, где используется `apt-get`.

## ✅ Решение

### 1. Исправленный Dockerfile (Debian)
```dockerfile
# Используем официальный образ Python с Docker Hub
FROM python:3.11

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости для Debian
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ... остальной код
```

### 2. Альтернативный Dockerfile (Alpine)
Создан `Dockerfile.alpine` для использования с Alpine Linux:
```dockerfile
FROM python:3.11-alpine
# ... использует apk команды
```

## 🚀 Команды для сборки

### Debian (по умолчанию)
```bash
docker build -t forest-mafia-bot .
```

### Alpine (альтернатива)
```bash
docker build -f Dockerfile.alpine -t forest-mafia-bot .
```

## 📋 Изменения
- ✅ Заменены `apk` команды на `apt-get`
- ✅ Исправлена установка PostgreSQL зависимостей (`libpq-dev`)
- ✅ Исправлена команда создания пользователя (`useradd` вместо `adduser -D`)
- ✅ Добавлен альтернативный Alpine Dockerfile

Теперь Docker сборка должна работать корректно! 🎉
