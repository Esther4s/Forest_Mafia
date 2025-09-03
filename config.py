import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '8314318680:AAG1CDOB-SQhyFfCpqDIBm-U8ANz6Ggw94k')

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