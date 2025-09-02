from telegram.ext import ApplicationBuilder, JobQueue

# Initialize the application
application = ApplicationBuilder().token('8314318680:AAHcpsrR4ffz19Ur6xc6cw1zZ0uydfTsCAQ').build()

# Set up the JobQueue
job_queue = JobQueue(application)import random
from game_logic import Game, GamePhase, Role, Team, Player

# Your other game logic here

if __name__ == "__main__":
    # This should be the last line of your main execution block
    application.run_polling()poetry add "python-telegram-bot[job-queue]"import random
from job_queue import JobQueue

job_queue = JobQueue(application)job_queue = JobQueue(application)import randomjob_queue = JobQueue(application)
import randomimport random
job_queue = JobQueue(application)
application.job_queue = job_queue

# Now you can schedule jobs using:
# job_queue.run_once(your_callback_function, when=5)

# Start the bot
application.run_polling()pip install "python-telegram-bot[job-queue]"import random
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta

class GamePhase(Enum):
    WAITING = "waiting"
    NIGHT = "night"
    DAY = "day"
    VOTING = "voting"
    GAME_OVER = "game_over"

class Team(Enum):
    PREDATORS = "predators"  # Хищники
    HERBIVORES = "herbivores"  # Травоядные

class Role(Enum):
    WOLF = "wolf"        # Волк
    FOX = "fox"          # Лиса
    HARE = "hare"        # Заяц
    MOLE = "mole"        # Крот
    BEAVER = "beaver"    # Бобёр

@dataclass
class Player:
    user_id: int
    username: str
    role: Role
    team: Team
    is_alive: bool = True
    is_fox_stolen: int = 0  # Количество краж Лисой
    is_beaver_protected: bool = False  # Защищен ли Бобром

class Game:
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.players: Dict[int, Player] = {}
        self.phase = GamePhase.WAITING
        self.current_round = 0
        self.night_actions = {}
        self.votes = {}
        self.game_start_time = None
        self.phase_end_time = None
        
    def add_player(self, user_id: int, username: str) -> bool:
        """Добавляет игрока в игру"""
        if len(self.players) >= 12:
            return False
        if user_id in self.players:
            return False
        
        # Роль будет назначена при старте игры
        self.players[user_id] = Player(
            user_id=user_id,
            username=username,
            role=Role.HARE,  # Временная роль
            team=Team.HERBIVORES  # Временная команда
        )
        return True
    
    def remove_player(self, user_id: int) -> bool:
        """Удаляет игрока из игры"""
        if user_id in self.players:
            del self.players[user_id]
            return True
        return False
    
    def leave_game(self, user_id: int) -> bool:
        """Игрок добровольно покидает игру"""
        if user_id in self.players:
            player = self.players[user_id]
            if player.is_alive and self.phase == GamePhase.WAITING:
                del self.players[user_id]
                return True
        return False
    
    def can_start_game(self) -> bool:
        """Проверяет, можно ли начать игру"""
        return len(self.players) >= 6
    
    def assign_roles(self):
        """Распределяет роли между игроками"""
        player_list = list(self.players.values())
        random.shuffle(player_list)
        
        # Вычисляем количество каждой роли
        total_players = len(player_list)
        wolves_count = max(1, int(total_players * 0.25))
        fox_count = max(1, int(total_players * 0.15))
        mole_count = max(1, int(total_players * 0.15))
        beaver_count = max(1, int(total_players * 0.10))
        hares_count = total_players - wolves_count - fox_count - mole_count - beaver_count
        
        # Назначаем роли
        role_index = 0
        
        # Волки
        for i in range(wolves_count):
            if role_index < len(player_list):
                player_list[role_index].role = Role.WOLF
                player_list[role_index].team = Team.PREDATORS
                role_index += 1
        
        # Лиса
        for i in range(fox_count):
            if role_index < len(player_list):
                player_list[role_index].role = Role.FOX
                player_list[role_index].team = Team.PREDATORS
                role_index += 1
        
        # Крот
        for i in range(mole_count):
            if role_index < len(player_list):
                player_list[role_index].role = Role.MOLE
                player_list[role_index].team = Team.HERBIVORES
                role_index += 1
        
        # Бобёр
        for i in range(beaver_count):
            if role_index < len(player_list):
                player_list[role_index].role = Role.BEAVER
                player_list[role_index].team = Team.HERBIVORES
                role_index += 1
        
        # Зайцы
        for i in range(hares_count):
            if role_index < len(player_list):
                player_list[role_index].role = Role.HARE
                player_list[role_index].team = Team.HERBIVORES
                role_index += 1
    
    def start_game(self):
        """Начинает игру"""
        if not self.can_start_game():
            return False
        
        self.assign_roles()
        self.phase = GamePhase.NIGHT
        self.current_round = 1
        self.game_start_time = datetime.now()
        self.phase_end_time = datetime.now() + timedelta(seconds=60)  # Первая ночь короче
        return True
    
    def get_alive_players(self) -> List[Player]:
        """Возвращает список живых игроков"""
        return [p for p in self.players.values() if p.is_alive]
    
    def get_players_by_role(self, role: Role) -> List[Player]:
        """Возвращает список игроков с определенной ролью"""
        return [p for p in self.players.values() if p.role == role and p.is_alive]
    
    def get_players_by_team(self, team: Team) -> List[Player]:
        """Возвращает список игроков определенной команды"""
        return [p for p in self.players.values() if p.team == team and p.is_alive]
    
    def check_game_end(self) -> Optional[Team]:
        """Проверяет, закончилась ли игра"""
        predators = self.get_players_by_team(Team.PREDATORS)
        herbivores = self.get_players_by_team(Team.HERBIVORES)
        
        if not predators:
            return Team.HERBIVORES
        if not herbivores:
            return Team.PREDATORS
        
        return None
    
    def process_night_actions(self):
        """Обрабатывает ночные действия"""
        if self.phase != GamePhase.NIGHT:
            return
        
        # Сброс ночных действий
        self.night_actions = {}
        
        # Обработка действий по порядку: Волки -> Лиса -> Бобёр -> Крот
        
        # Волки выбирают жертву
        wolves = self.get_players_by_role(Role.WOLF)
        if wolves and self.current_round > 1:  # В первую ночь волки не едят
            # Здесь будет логика выбора жертвы волками
            pass
        
        # Лиса ворует еду
        foxes = self.get_players_by_role(Role.FOX)
        if foxes:
            # Здесь будет логика кражи еды лисой
            pass
        
        # Бобёр возвращает запасы
        beavers = self.get_players_by_role(Role.BEAVER)
        if beavers:
            # Здесь будет логика помощи бобра
            pass
        
        # Крот роет норки
        moles = self.get_players_by_role(Role.MOLE)
        if moles:
            # Здесь будет логика проверки кем-то кротом
            pass
    
    def start_day(self):
        """Начинает дневную фазу"""
        self.phase = GamePhase.DAY
        self.phase_end_time = datetime.now() + timedelta(seconds=300)  # 5 минут на обсуждение
    
    def start_voting(self):
        """Начинает фазу голосования"""
        self.phase = GamePhase.VOTING
        self.votes = {}
        self.phase_end_time = datetime.now() + timedelta(seconds=120)  # 2 минуты на голосование
    
    def vote(self, voter_id: int, target_id: int) -> bool:
        """Регистрирует голос игрока"""
        if self.phase != GamePhase.VOTING:
            return False
        
        voter = self.players.get(voter_id)
        target = self.players.get(target_id)
        
        if not voter or not target or not voter.is_alive or not target.is_alive:
            return False
        
        self.votes[voter_id] = target_id
        return True
    
    def process_voting(self) -> Optional[Player]:
        """Обрабатывает результаты голосования"""
        if not self.votes:
            return None
        
        # Подсчет голосов
        vote_counts = {}
        for target_id in self.votes.values():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
        
        # Находим игрока с максимальным количеством голосов
        max_votes = max(vote_counts.values())
        max_vote_players = [pid for pid, votes in vote_counts.items() if votes == max_votes]
        
        # Если ничья - изгнания нет
        if len(max_vote_players) > 1:
            return None
        
        # Изгоняем игрока с наибольшим количеством голосов
        exiled_id = max_vote_players[0]
        exiled_player = self.players[exiled_id]
        exiled_player.is_alive = False
        
        return exiled_player
    
    def start_night(self):
        """Начинает ночную фазу"""
        self.phase = GamePhase.NIGHT
        self.current_round += 1
        self.phase_end_time = datetime.now() + timedelta(seconds=60)
        self.night_actions = {}
    
    def is_phase_finished(self) -> bool:
        """Проверяет, закончилась ли текущая фаза"""
        if not self.phase_end_time:
            return False
        return datetime.now() >= self.phase_end_time
