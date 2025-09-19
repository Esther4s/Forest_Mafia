# PowerShell скрипт для сборки Docker образа с retry логикой

Write-Host "🐳 Сборка Docker образа для Forest Mafia Bot..." -ForegroundColor Green

# Функция для retry
function Retry-Build {
    param(
        [int]$MaxAttempts = 3
    )
    
    $attempt = 1
    
    while ($attempt -le $MaxAttempts) {
        Write-Host "🔄 Попытка $attempt из $MaxAttempts..." -ForegroundColor Yellow
        
        $result = docker build -t forest-mafia-bot .
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Сборка успешна!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Попытка $attempt неудачна" -ForegroundColor Red
            if ($attempt -lt $MaxAttempts) {
                Write-Host "⏳ Ожидание 10 секунд перед следующей попыткой..." -ForegroundColor Yellow
                Start-Sleep -Seconds 10
            }
            $attempt++
        }
    }
    
    Write-Host "❌ Все попытки неудачны. Пробуем альтернативный Dockerfile..." -ForegroundColor Red
    return $false
}

# Пробуем основной Dockerfile
if (Retry-Build) {
    Write-Host "🎉 Сборка завершена успешно!" -ForegroundColor Green
    Write-Host "📦 Образ: forest-mafia-bot" -ForegroundColor Cyan
    Write-Host "🚀 Для запуска: docker run -d --name forest-mafia forest-mafia-bot" -ForegroundColor Cyan
} else {
    Write-Host "🔄 Пробуем альтернативный Dockerfile с Ubuntu..." -ForegroundColor Yellow
    $result = docker build -f Dockerfile.ubuntu -t forest-mafia-bot .
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Сборка с Ubuntu успешна!" -ForegroundColor Green
        Write-Host "📦 Образ: forest-mafia-bot" -ForegroundColor Cyan
        Write-Host "🚀 Для запуска: docker run -d --name forest-mafia forest-mafia-bot" -ForegroundColor Cyan
    } else {
        Write-Host "❌ Обе попытки сборки неудачны" -ForegroundColor Red
        Write-Host "💡 Попробуйте:" -ForegroundColor Yellow
        Write-Host "   1. Проверить подключение к интернету" -ForegroundColor White
        Write-Host "   2. Очистить Docker кэш: docker system prune -a" -ForegroundColor White
        Write-Host "   3. Перезапустить Docker" -ForegroundColor White
        exit 1
    }
}
