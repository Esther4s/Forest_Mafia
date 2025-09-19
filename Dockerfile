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

# Обновляем pip и устанавливаем wheel
RUN pip install --upgrade pip setuptools wheel

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаем пользователя для безопасности
RUN useradd -m -s /bin/bash bot && \
    chown -R bot:bot /app
USER bot

# Создаем директории для логов и данных
RUN mkdir -p logs data

# Запускаем бота
CMD ["python", "bot.py"]
