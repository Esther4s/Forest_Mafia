#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Доменные сущности
Основные объекты предметной области с бизнес-логикой
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

from .value_objects import (
    UserId, ChatId, GameId, Username, Supplies, GameDuration, 
    GamePhase, Team, Role
)


@dataclass
class Player:
    """Игрок в игре"""
    user_id: UserId
    username: Username
    role: Role
    team: Team
    supplies: Supplies
    is_alive: bool = True
    is_fox_stolen: int = 0
    stolen_supplies: int = 0
    is_beaver_protected: bool = False
    consecutive_nights_survived: int = 0
    last_action_round: int = 0
    extra_lives: int = 0
    
    def __post_init__(self):
        """Валидация после инициализации"""
        if self.role == Role.WOLF and self.team != Team.PREDATORS:
            raise ValueError("Волк должен быть в команде хищников")
        if self.role == Role.FOX and self.team != Team.PREDATORS:
            raise ValueError("Лиса должна быть в команде хищников")
        if self.role in [Role.HARE, Role.MOLE, Role.BEAVER] and self.team != Team.HERBIVORES:
            raise ValueError("Травоядные должны быть в команде травоядных")
    
    @property
    def can_be_stolen_from(self) -> bool:
        """Может ли у игрока быть украдено (жив и есть припасы)"""
        return self.is_alive and self.supplies.current > 0
    
    def consume_supplies(self, amount: int = 1) -> bool:
        """Потребляет припасы, возвращает True если успешно"""
        if self.supplies.can_consume(amount):
            self.supplies = self.supplies.consume(amount)
            return True
        return False
    
    def add_supplies(self, amount: int) -> int:
        """Добавляет припасы, возвращает количество добавленных"""
        old_supplies = self.supplies.current
        self.supplies = self.supplies.add(amount)
        return self.supplies.current - old_supplies
    
    def apply_extra_lives(self, lives: int) -> None:
        """Применяет дополнительные жизни от предметов"""
        if lives > 0:
            self.extra_lives += lives
    
    def use_extra_life(self) -> bool:
        """Использует дополнительную жизнь, возвращает True если есть жизни"""
        if self.extra_lives > 0:
            self.extra_lives -= 1
            return True
        return False
    
    def steal_supplies(self) -> bool:
        """Крадет припас у игрока, возвращает True если успешно"""
        if self.can_be_stolen_from:
            self.supplies = self.supplies.consume(1)
            self.stolen_supplies += 1
            self.is_fox_stolen += 1
            return True
        return False
    
    def die(self, reason: str = "unknown") -> None:
        """Убивает игрока"""
        self.is_alive = False
        self.consecutive_nights_survived = 0
    
    def survive_night(self) -> None:
        """Игрок выживает ночь"""
        self.consecutive_nights_survived += 1
    
    def reset_protection(self) -> None:
        """Сбрасывает защиту бобра"""
        self.is_beaver_protected = False


@dataclass
class GameStatistics:
    """Статистика игры"""
    predator_kills: int = 0
    herbivore_survivals: int = 0
    fox_thefts: int = 0
    beaver_protections: int = 0
    total_voters: int = 0
    voting_type: str = ""
    
    def record_kill(self, team: Team) -> None:
        """Записывает убийство"""
        if team == Team.PREDATORS:
            self.predator_kills += 1
        else:
            self.herbivore_survivals += 1
    
    def record_fox_theft(self) -> None:
        """Записывает кражу лисы"""
        self.fox_thefts += 1
    
    def record_beaver_protection(self) -> None:
        """Записывает защиту бобра"""
        self.beaver_protections += 1


@dataclass
class Game:
    """Основная сущность игры"""
    game_id: GameId
    chat_id: ChatId
    thread_id: Optional[int]
    is_test_mode: bool
    
    # Игровое состояние
    players: Dict[int, Player] = field(default_factory=dict)
    phase: GamePhase = GamePhase.WAITING
    current_round: int = 0
    day_number: Optional[int] = None
    
    # Действия и голосования
    night_actions: Dict[int, Dict] = field(default_factory=dict)
    votes: Dict[int, Optional[int]] = field(default_factory=dict)
    
    # Временные метки
    game_duration: Optional[GameDuration] = None
    phase_end_time: Optional[datetime] = None
    day_start_time: Optional[datetime] = None
    
    # UI состояние
    pinned_message_id: Optional[int] = None
    stage_pinned_messages: Dict[str, int] = field(default_factory=dict)
    day_timer_task = None
    
    # Статистика
    game_stats: GameStatistics = field(default_factory=GameStatistics)
    
    # Состояние игры
    game_over_sent: bool = False
    last_wolf_victim: Optional[Dict] = None
    last_mole_check: Optional[Dict] = None
    
    def add_player(self, user_id: UserId, username: Username) -> bool:
        """Добавляет игрока в игру"""
        if not self._can_add_player():
            return False
        
        if user_id.value in self.players:
            return False

        # Создаем игрока с временной ролью (будет назначена при старте)
        self.players[user_id.value] = Player(
            user_id=user_id,
            username=username,
            role=Role.HARE,  # Временная роль
            team=Team.HERBIVORES,  # Временная команда
            supplies=Supplies(2, 2)
        )
        return True
    
    def _can_add_player(self) -> bool:
        """Проверяет, можно ли добавить игрока"""
        max_players = 12 if not self.is_test_mode else float('inf')
        return len(self.players) < max_players

    def remove_player(self, user_id: UserId) -> bool:
        """Удаляет игрока из игры"""
        if user_id.value in self.players:
            del self.players[user_id.value]
            return True
        return False

    def leave_game(self, user_id: UserId) -> bool:
        """Игрок добровольно покидает игру"""
        if user_id.value in self.players:
            player = self.players[user_id.value]
            if player.is_alive and self.phase == GamePhase.WAITING:
                del self.players[user_id.value]
                return True
        return False

    def can_start_game(self) -> bool:
        """Проверяет, можно ли начать игру"""
        min_players = 3 if self.is_test_mode else 6
        return len(self.players) >= min_players

    def get_alive_players(self) -> List[Player]:
        """Возвращает список живых игроков"""
        return [player for player in self.players.values() if player.is_alive]

    def get_players_by_role(self, role: Role) -> List[Player]:
        """Возвращает список живых игроков с определенной ролью"""
        return [player for player in self.players.values() 
                if player.role == role and player.is_alive]

    def get_players_by_team(self, team: Team) -> List[Player]:
        """Возвращает список живых игроков определенной команды"""
        return [player for player in self.players.values() 
                if player.team == team and player.is_alive]
    
    def get_dead_players(self) -> List[Player]:
        """Возвращает список мертвых игроков"""
        return [player for player in self.players.values() if not player.is_alive]
    
    def get_player_count_by_team(self, team: Team) -> int:
        """Возвращает количество живых игроков в команде"""
        return len(self.get_players_by_team(team))

    def check_game_end(self) -> Optional[Team]:
        """Проверяет условия окончания игры"""
        alive_players = self.get_alive_players()
        
        if not alive_players:
            return Team.HERBIVORES  # По умолчанию побеждают травоядные
        
        predators_count = self.get_player_count_by_team(Team.PREDATORS)
        herbivores_count = self.get_player_count_by_team(Team.HERBIVORES)
        
        # Хищники побеждают, если их больше или равно травоядным
        if predators_count >= herbivores_count:
            return Team.PREDATORS
        
        # Травоядные побеждают, если хищников нет
        if predators_count == 0:
            return Team.HERBIVORES
        
        return None  # Игра продолжается

    def start_game(self) -> bool:
        """Начинает игру"""
        if not self.can_start_game():
            return False

        # Назначаем роли (логика будет вынесена в отдельный сервис)
        self._assign_roles()
        
        # Применяем эффекты предметов при старте игры
        self._apply_start_game_effects()
        
        self.phase = GamePhase.NIGHT
        self.current_round = 1
        self.day_number = 1
        self.game_duration = GameDuration(datetime.now())
        self.phase_end_time = datetime.now() + timedelta(seconds=60)  # Первая ночь короче
        return True

    def _assign_roles(self) -> None:
        """Распределяет роли между игроками (упрощенная версия)"""
        # Эта логика будет вынесена в отдельный сервис RoleAssignmentService
        player_list = list(self.players.values())
        # Временная реализация - просто назначаем роли по порядку
        roles = [Role.WOLF, Role.FOX, Role.HARE, Role.MOLE, Role.BEAVER]
        for i, player in enumerate(player_list):
            if i < len(roles):
                player.role = roles[i]
                if roles[i] in [Role.WOLF, Role.FOX]:
                    player.team = Team.PREDATORS
                else:
                    player.team = Team.HERBIVORES

    def _apply_start_game_effects(self) -> None:
        """Применяет эффекты предметов при старте игры"""
        # Эта логика будет вынесена в отдельный сервис ItemEffectService
        pass

    def start_day(self) -> None:
        """Начинает дневную фазу"""
        self.phase = GamePhase.DAY
        self.phase_end_time = datetime.now() + timedelta(seconds=300)  # 5 минут на обсуждение
        self.day_start_time = datetime.now()

    def start_voting(self) -> None:
        """Начинает фазу голосования"""
        self.phase = GamePhase.VOTING
        self.votes = {}
        self.phase_end_time = datetime.now() + timedelta(seconds=120)  # 2 минуты на голосование

    def vote(self, voter_id: UserId, target_id: Optional[UserId]) -> bool:
        """Регистрирует голос игрока"""
        if not self._is_voting_valid(voter_id, target_id):
            return False
        
        self.votes[voter_id.value] = target_id.value if target_id else None
        return True
    
    def _is_voting_valid(self, voter_id: UserId, target_id: Optional[UserId]) -> bool:
        """Проверяет валидность голосования"""
        if self.phase != GamePhase.VOTING:
            return False

        voter = self.players.get(voter_id.value)
        if not voter or not voter.is_alive:
            return False

        # Если target_id не None, проверяем цель
        if target_id is not None:
            target = self.players.get(target_id.value)
            if not target or not target.is_alive:
                return False

            # Защита от голосования за себя
            if voter_id.value == target_id.value:
                return False

        return True

    def start_night(self) -> None:
        """Начинает ночную фазу"""
        self.phase = GamePhase.NIGHT
        self.current_round += 1
        self.phase_end_time = datetime.now() + timedelta(seconds=60)
        self.night_actions = {}
        
        # Обновляем статистику выживания
        for player in self.get_alive_players():
            player.survive_night()

        # Сбрасываем одноразовые защиты бобра
        for player in self.get_alive_players():
            player.reset_protection()

    def is_phase_finished(self) -> bool:
        """Проверяет, закончилась ли текущая фаза"""
        if not self.phase_end_time:
            return False
        return datetime.now() >= self.phase_end_time
