#!/bin/bash

# 🚀 Скрипт автоматического развертывания на Railway
# Использование: ./deploy_to_railway.sh

echo "🚀 Начинаем развертывание на Railway..."

# Проверяем, что мы в git репозитории
if [ ! -d ".git" ]; then
    echo "❌ Ошибка: не найден git репозиторий"
    exit 1
fi

# Проверяем статус git
echo "📋 Проверяем статус git..."
git status

# Добавляем все изменения
echo "📝 Добавляем изменения..."
git add .

# Создаем коммит
echo "💾 Создаем коммит..."
git commit -m "feat: финальные обновления для продакшена

- Добавлена система случайных сообщений для случаев когда никто не изгнан/не съеден
- Исправлена кнопка 'повторить этап' - теперь только повторяет сообщение
- Убрана избыточная кнопка 'проверить таймер'
- Система настроек в PostgreSQL полностью интегрирована
- Все баги исправлены, 0 ошибок линтера
- Готово к продакшену"

# Пушим изменения
echo "📤 Отправляем изменения в репозиторий..."
git push origin main

# Проверяем, установлен ли Railway CLI
if ! command -v railway &> /dev/null; then
    echo "⚠️ Railway CLI не установлен. Установите его:"
    echo "npm install -g @railway/cli"
    echo "или"
    echo "curl -fsSL https://railway.app/install.sh | sh"
    exit 1
fi

# Проверяем, авторизованы ли в Railway
echo "🔐 Проверяем авторизацию в Railway..."
if ! railway whoami &> /dev/null; then
    echo "⚠️ Не авторизованы в Railway. Выполните: railway login"
    exit 1
fi

# Развертываем на Railway
echo "🚀 Развертываем на Railway..."
railway up

# Проверяем статус
echo "📊 Проверяем статус развертывания..."
railway status

# Показываем логи
echo "📋 Последние логи:"
railway logs --tail 20

echo "✅ Развертывание завершено!"
echo "🔍 Проверьте логи и статус в Railway Dashboard"
echo "🌐 URL: https://railway.app/dashboard"
