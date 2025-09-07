import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
# Читаем токен из переменных окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN', '').strip("'\"")
if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
    raise ValueError(
        "BOT_TOKEN не установлен! Создайте файл .env и добавьте BOT_TOKEN=your_actual_token"
    )

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///forest_mafia.db')

# Game settings
MIN_PLAYERS = 6
MAX_PLAYERS = 12

# Production mode settings
TEST_MODE = False  # Отключить для продакшена
TEST_MIN_PLAYERS = 3  # Минимум игроков в тестовом режиме

# Role distribution (percentages)
ROLE_DISTRIBUTION = {
    'wolves': 0.25,      # 25% - Волки
    'fox': 0.15,         # 15% - Лиса
    'hares': 0.35,       # 35% - Зайцы
    'mole': 0.15,        # 15% - Крот
    'beaver': 0.10       # 10% - Бобёр
}

# Night phases duration (in seconds)
NIGHT_PHASE_DURATION = 60
DAY_PHASE_DURATION = 300  # 5 minutes for discussion
VOTING_DURATION = 120     # 2 minutes for voting