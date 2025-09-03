import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
# Читаем токен из переменных окружения, если это не заглушка - используем его
token_from_env = os.environ.get('BOT_TOKEN', '').strip("'\"")
if token_from_env and token_from_env != 'your_bot_token_here':
    BOT_TOKEN = token_from_env
else:
    # Используем резервный токен
    BOT_TOKEN = '8314318680:AAG1CDOB-SQhyFfCpqDIBm-U8ANz6Ggw94k'

# Game settings
MIN_PLAYERS = 6
MAX_PLAYERS = 12

# Test mode settings
TEST_MODE = True  # Включить для тестирования с меньшим количеством игроков
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