# Скрипт для деплоя ForestMafia Bot в продакшен (Windows PowerShell)
# Использование: .\deploy_production.ps1

param(
    [switch]$SkipTests,
    [switch]$Force
)

# Настройка ошибок
$ErrorActionPreference = "Stop"

# Функции для логирования
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARNING" { "Yellow" }
        "SUCCESS" { "Green" }
        default { "White" }
    }
    Write-Host "[$timestamp] $Message" -ForegroundColor $color
}

function Write-Success { param([string]$Message) Write-Log $Message "SUCCESS" }
function Write-Error { param([string]$Message) Write-Log $Message "ERROR" }
function Write-Warning { param([string]$Message) Write-Log $Message "WARNING" }

# Проверка переменных окружения
function Test-Environment {
    Write-Log "Проверяем переменные окружения..."
    
    if (-not $env:BOT_TOKEN) {
        Write-Error "BOT_TOKEN не установлен!"
        exit 1
    }
    
    if (-not $env:DATABASE_URL) {
        Write-Error "DATABASE_URL не установлен!"
        exit 1
    }
    
    Write-Success "✅ Переменные окружения настроены"
}

# Проверка зависимостей
function Test-Dependencies {
    Write-Log "Проверяем зависимости..."
    
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Python не найден"
        }
        Write-Log "Найден: $pythonVersion"
    }
    catch {
        Write-Error "Python не установлен или не найден в PATH!"
        exit 1
    }
    
    try {
        $pipVersion = pip --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "pip не найден"
        }
        Write-Log "Найден: $pipVersion"
    }
    catch {
        Write-Error "pip не установлен или не найден в PATH!"
        exit 1
    }
    
    Write-Success "✅ Зависимости проверены"
}

# Установка зависимостей
function Install-Dependencies {
    Write-Log "Устанавливаем зависимости..."
    
    try {
        pip install -r requirements.txt --no-cache-dir
        Write-Success "✅ Зависимости установлены"
    }
    catch {
        Write-Error "Ошибка установки зависимостей: $_"
        exit 1
    }
}

# Проверка базы данных
function Test-Database {
    Write-Log "Проверяем подключение к базе данных..."
    
    $testScript = @"
import os
import psycopg2
from urllib.parse import urlparse

try:
    url = urlparse(os.environ['DATABASE_URL'])
    conn = psycopg2.connect(
        host=url.hostname,
        port=url.port,
        database=url.path[1:],
        user=url.username,
        password=url.password
    )
    conn.close()
    print('✅ Подключение к базе данных успешно')
except Exception as e:
    print(f'❌ Ошибка подключения к базе данных: {e}')
    exit(1)
"@
    
    try {
        python -c $testScript
        Write-Success "✅ База данных доступна"
    }
    catch {
        Write-Error "Ошибка подключения к базе данных: $_"
        exit 1
    }
}

# Применение миграций
function Invoke-Migrations {
    Write-Log "Применяем миграции базы данных..."
    
    # Проверяем, есть ли миграции
    $migrationsPath = "alembic\versions"
    if (Test-Path $migrationsPath) {
        $migrations = Get-ChildItem $migrationsPath -Filter "*.py"
        if ($migrations.Count -gt 0) {
            try {
                alembic upgrade head
                Write-Success "✅ Миграции применены"
            }
            catch {
                Write-Warning "Ошибка применения миграций: $_"
                Write-Log "Создаем схему вручную..."
                Invoke-SchemaCreation
            }
        }
        else {
            Write-Log "Миграции не найдены, создаем схему вручную..."
            Invoke-SchemaCreation
        }
    }
    else {
        Write-Log "Папка миграций не найдена, создаем схему вручную..."
        Invoke-SchemaCreation
    }
}

# Создание схемы базы данных
function Invoke-SchemaCreation {
    Write-Log "Создаем схему базы данных..."
    
    $schemaScript = @"
import os
import psycopg2
from urllib.parse import urlparse

# Читаем схему
with open('fixed_database_schema.sql', 'r', encoding='utf-8') as f:
    schema = f.read()

# Подключаемся к базе
url = urlparse(os.environ['DATABASE_URL'])
conn = psycopg2.connect(
    host=url.hostname,
    port=url.port,
    database=url.path[1:],
    user=url.username,
    password=url.password
)

# Выполняем схему
with conn.cursor() as cur:
    cur.execute(schema)
    conn.commit()

conn.close()
print('✅ Схема базы данных создана')
"@
    
    try {
        python -c $schemaScript
        Write-Success "✅ Схема базы данных создана"
    }
    catch {
        Write-Error "Ошибка создания схемы базы данных: $_"
        exit 1
    }
}

# Проверка кода
function Test-Code {
    Write-Log "Проверяем код на ошибки..."
    
    try {
        # Проверяем синтаксис Python
        python -m py_compile bot.py
        Write-Log "✅ Синтаксис Python корректен"
        
        # Проверяем импорты
        $importScript = @"
import sys
sys.path.append('.')
try:
    import bot
    print('✅ Импорты работают корректно')
except ImportError as e:
    print(f'❌ Ошибка импорта: {e}')
    sys.exit(1)
"@
        python -c $importScript
        Write-Success "✅ Код проверен"
    }
    catch {
        Write-Error "Ошибка проверки кода: $_"
        exit 1
    }
}

# Создание Windows сервиса
function New-WindowsService {
    Write-Log "Создаем Windows сервис..."
    
    $serviceName = "ForestMafiaBot"
    $serviceDisplayName = "ForestMafia Bot"
    $serviceDescription = "Telegram Bot for ForestMafia Game"
    $servicePath = (Get-Location).Path
    $pythonPath = (Get-Command python).Source
    
    # Проверяем, существует ли сервис
    $existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($existingService) {
        if ($Force) {
            Write-Log "Останавливаем существующий сервис..."
            Stop-Service -Name $serviceName -Force
            Write-Log "Удаляем существующий сервис..."
            sc.exe delete $serviceName
        }
        else {
            Write-Warning "Сервис $serviceName уже существует. Используйте -Force для пересоздания."
            return
        }
    }
    
    # Создаем сервис
    try {
        $serviceArgs = @(
            "create", $serviceName,
            "binPath= `"$pythonPath`" `"$servicePath\bot.py`"",
            "DisplayName= `"$serviceDisplayName`"",
            "start= auto"
        )
        & sc.exe $serviceArgs
        
        # Устанавливаем описание
        & sc.exe description $serviceName $serviceDescription
        
        Write-Success "✅ Windows сервис создан"
    }
    catch {
        Write-Error "Ошибка создания сервиса: $_"
        exit 1
    }
}

# Запуск сервиса
function Start-WindowsService {
    Write-Log "Запускаем сервис..."
    
    $serviceName = "ForestMafiaBot"
    
    try {
        Start-Service -Name $serviceName
        Start-Sleep -Seconds 5
        
        $service = Get-Service -Name $serviceName
        if ($service.Status -eq "Running") {
            Write-Success "✅ Сервис запущен успешно"
        }
        else {
            Write-Error "❌ Ошибка запуска сервиса. Статус: $($service.Status)"
        }
    }
    catch {
        Write-Error "Ошибка запуска сервиса: $_"
        exit 1
    }
}

# Тестирование бота
function Test-Bot {
    Write-Log "Тестируем работу бота..."
    
    $serviceName = "ForestMafiaBot"
    $service = Get-Service -Name $serviceName
    
    if ($service.Status -eq "Running") {
        Write-Success "✅ Бот работает корректно"
        Write-Log "📊 Статус сервиса: Get-Service -Name $serviceName"
        Write-Log "📋 Логи: Get-EventLog -LogName Application -Source $serviceName -Newest 10"
        Write-Log "🔄 Перезапуск: Restart-Service -Name $serviceName"
    }
    else {
        Write-Warning "⚠️ Сервис не запущен. Статус: $($service.Status)"
    }
}

# Основная функция
function Main {
    Write-Log "🌲 ForestMafia Bot - Деплой в продакшен (Windows)"
    Write-Log "=================================================="
    
    Test-Environment
    Test-Dependencies
    Install-Dependencies
    Test-Database
    Invoke-Migrations
    Test-Code
    New-WindowsService
    Start-WindowsService
    Test-Bot
    
    Write-Success "🎉 Деплой завершен успешно!"
    Write-Log "📊 Управление сервисом:"
    Write-Log "  - Статус: Get-Service -Name ForestMafiaBot"
    Write-Log "  - Остановка: Stop-Service -Name ForestMafiaBot"
    Write-Log "  - Запуск: Start-Service -Name ForestMafiaBot"
    Write-Log "  - Перезапуск: Restart-Service -Name ForestMafiaBot"
}

# Запуск
Main
