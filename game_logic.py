#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Игровая логика для Лес и волки Bot
Основные классы и логика игры "Лес и Волки"
"""

import random
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
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
    """Игрок в игре Лес и волки"""
    user_id: int
    username: str
    role: Role
    team: Team
    is_alive: bool = True
    supplies: int = 2
    max_supplies: int = 2
    is_fox_stolen: int = 0
    stolen_supplies: int = 0
    is_beaver_protected: bool = False
    consecutive_nights_survived: int = 0
    last_action_round: int = 0
    
    def __post_init__(self):
        """Валидация данных игрока после инициализации"""
        if self.supplies < 0:
            raise ValueError("Количество припасов не может быть отрицательным")
        if self.max_supplies < 1:
            raise ValueError("Максимальное количество припасов должно быть больше 0")
    
    @property
    def is_supplies_critical(self) -> bool:
        """Проверяет, критично ли мало припасов у игрока"""
        return self.supplies <= 1
    
    @property
    def can_be_stolen_from(self) -> bool:
        """Может ли у игрока быть украдено (жив и есть припасы)"""
        return self.is_alive and self.supplies > 0
    
    def consume_supplies(self, amount: int = 1) -> bool:
        """Потребляет припасы, возвращает True если успешно"""
        if self.supplies >= amount:
            self.supplies -= amount
            return True
        return False
    
    def add_supplies(self, amount: int) -> int:
        """Добавляет припасы, возвращает количество добавленных"""
        if amount <= 0:
            return 0
        
        old_supplies = self.supplies
        self.supplies = min(self.supplies + amount, self.max_supplies)
        return self.supplies - old_supplies
    
    def steal_supplies(self) -> bool:
        """Крадет припас у игрока, возвращает True если успешно"""
        if self.can_be_stolen_from:
            self.supplies -= 1
            self.stolen_supplies += 1
            self.is_fox_stolen += 1
            return True
        return False
    
    def die(self, reason: str = "unknown"):
        """Убивает игрока"""
        self.is_alive = False
        self.consecutive_nights_survived = 0
        # Можно добавить логирование причины смерти
    
    def survive_night(self):
        """Игрок выживает ночь"""
        self.consecutive_nights_survived += 1


@dataclass
class GameStatistics:
    """Статистика игры"""
    predator_kills: int = 0
    herbivore_survivals: int = 0
    fox_thefts: int = 0
    beaver_protections: int = 0
    total_voters: int = 0
    voting_type: str = ""
    
    def record_kill(self, team: Team):
        """Записывает убийство"""
        if team == Team.PREDATORS:
            self.predator_kills += 1
        else:
            self.herbivore_survivals += 1
    
    def record_fox_theft(self):
        """Записывает кражу лисы"""
        self.fox_thefts += 1
    
    def record_beaver_protection(self):
        """Записывает защиту бобра"""
        self.beaver_protections += 1


class Game:
    """Основной класс игры Лес и волки"""
    
    def __init__(self, chat_id: int, thread_id: Optional[int] = None, is_test_mode: bool = True):
        self.chat_id = chat_id
        self.thread_id = thread_id
        self.is_test_mode = is_test_mode
        
        # Игровое состояние
        self.players: Dict[int, Player] = {}
        self.phase = GamePhase.WAITING
        self.current_round = 0
        
        # Действия и голосования
        self.night_actions = {}
        self.votes = {}
        
        # Временные метки
        self.game_start_time: Optional[datetime] = None
        self.phase_end_time: Optional[datetime] = None
        self.day_start_time: Optional[datetime] = None
        
        # UI состояние
        self.pinned_message_id: Optional[int] = None
        self.stage_pinned_messages: Dict[str, int] = {}
        self.day_timer_task = None
        
        # Статистика
        self.game_stats = GameStatistics()
        
        # Состояние игры
        self.game_over_sent = False
        
        # Информация о последней жертве волка (для отправки ЛС)
        self.last_wolf_victim: Optional[Dict] = None
        
        # Информация о последней проверке крота (для отправки ЛС)
        self.last_mole_check: Optional[Dict] = None

    def add_player(self, user_id: int, username: str) -> bool:
        """Добавляет игрока в игру"""
        if not self._can_add_player():
            return False
        
        if user_id in self.players:
            return False

        # Создаем игрока с временной ролью (будет назначена при старте)
        self.players[user_id] = Player(
            user_id=user_id,
            username=username,
            role=Role.HARE,  # Временная роль
            team=Team.HERBIVORES  # Временная команда
        )
        return True
    
    def _can_add_player(self) -> bool:
        """Проверяет, можно ли добавить игрока"""
        max_players = 12 if not self.is_test_mode else float('inf')
        return len(self.players) < max_players

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
        min_players = 3 if self.is_test_mode else 6
        return len(self.players) >= min_players

    def assign_roles(self):
        """Распределяет роли между игроками"""
        player_list = list(self.players.values())
        total_players = len(player_list)
        
        # Вычисляем распределение ролей
        role_counts = self._calculate_role_distribution(total_players)
        
        # Создаем список ролей для распределения
        all_roles = self._create_role_list(role_counts)
        
        # Перемешиваем и назначаем роли
        random.shuffle(all_roles)
        self._assign_roles_to_players(player_list, all_roles)
    
    def _create_role_list(self, role_counts: Dict[str, int]) -> List[Tuple[Role, Team]]:
        """Создает список ролей для распределения"""
        all_roles = []
        
        # Добавляем роли хищников
        for _ in range(role_counts['wolves']):
            all_roles.append((Role.WOLF, Team.PREDATORS))
        for _ in range(role_counts['fox']):
            all_roles.append((Role.FOX, Team.PREDATORS))
        
        # Добавляем роли травоядных
        for _ in range(role_counts['mole']):
            all_roles.append((Role.MOLE, Team.HERBIVORES))
        for _ in range(role_counts['beaver']):
            all_roles.append((Role.BEAVER, Team.HERBIVORES))
        for _ in range(role_counts['hare']):
            all_roles.append((Role.HARE, Team.HERBIVORES))
        
        return all_roles
    
    def _assign_roles_to_players(self, players: List[Player], roles: List[Tuple[Role, Team]]):
        """Назначает роли игрокам"""
        for i, player in enumerate(players):
            if i < len(roles):
                role, team = roles[i]
                player.role = role
                player.team = team

    def _calculate_role_distribution(self, total_players: int) -> Dict[str, int]:
        """Вычисляет распределение ролей"""
        roles = {
            'wolves': self._calculate_wolves_count(total_players),
            'fox': 1 if total_players >= 6 else 0,
            'mole': 1 if total_players >= 4 else 0,
            'beaver': self._calculate_beaver_count(total_players),
            'hare': 0  # Будет вычислено в конце
        }
        
        # Зайцы - все оставшиеся игроки
        used_roles = sum(roles.values())
        roles['hare'] = total_players - used_roles
        
        # Обеспечиваем минимум 2 зайца
        self._ensure_minimum_hares(roles)
        
        return roles
    
    def _calculate_wolves_count(self, total_players: int) -> int:
        """Вычисляет количество волков"""
        if 3 <= total_players <= 6:
            return 1
        elif 7 <= total_players <= 9:
            return 2
        elif 10 <= total_players <= 12:
            return 3
        return 0
    
    def _calculate_beaver_count(self, total_players: int) -> int:
        """Вычисляет количество бобров"""
        if total_players < 6:
            return 0
        elif 11 <= total_players <= 12:
            return 2
        else:
            return 1
    
    def _ensure_minimum_hares(self, roles: Dict[str, int]):
        """Обеспечивает минимум 2 зайца"""
        if roles['hare'] < 2:
            deficit = 2 - roles['hare']
            # Уменьшаем бобров или кротов
            if roles['beaver'] > 0 and deficit > 0:
                roles['beaver'] = max(0, roles['beaver'] - deficit)
                roles['hare'] = 2
            elif roles['mole'] > 0 and deficit > 0:
                roles['mole'] = max(0, roles['mole'] - deficit)
                roles['hare'] = 2

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
    
    
    def check_auto_game_end(self) -> Optional[Team]:
        """Проверяет условия автоматического завершения игры"""
        alive_players = self.get_alive_players()
        
        # 1. Слишком мало игроков осталось (менее 3)
        if len(alive_players) < 3:
            # Определяем победителя по количеству живых игроков каждой команды
            predators = self.get_players_by_team(Team.PREDATORS)
            herbivores = self.get_players_by_team(Team.HERBIVORES)
            
            if len(predators) > len(herbivores):
                return Team.PREDATORS
            elif len(herbivores) > len(predators):
                return Team.HERBIVORES
            else:
                # Ничья - побеждают травоядные (по умолчанию)
                return Team.HERBIVORES
        
        # 2. Игра длится слишком долго (более 3 часов для лесной мафии)
        if self.game_start_time:
            game_duration = datetime.now() - self.game_start_time
            if game_duration.total_seconds() > 10800:  # 3 часа
                # При таймауте определяем победителя по статистике
                if self.game_stats.predator_kills > self.game_stats.herbivore_survivals:
                    return Team.PREDATORS
                else:
                    return Team.HERBIVORES
        
        # 3. Слишком много раундов (более 25 для лесной мафии)
        if self.current_round > 25:
            # При превышении лимита раундов определяем победителя по статистике
            if self.game_stats.predator_kills > self.game_stats.herbivore_survivals:
                return Team.PREDATORS
            else:
                return Team.HERBIVORES
        
        # 4. Равное количество хищников и травоядных при очень малом количестве игроков
        predators = self.get_players_by_team(Team.PREDATORS)
        herbivores = self.get_players_by_team(Team.HERBIVORES)
        
        # Завершаем игру ничьей только при 2 игроках с равенством команд
        if len(alive_players) == 2 and len(predators) == len(herbivores):
            # При равенстве 1 на 1 побеждают травоядные (ничья)
            return Team.HERBIVORES
            
        return None
    
    def get_auto_end_reason(self) -> Optional[str]:
        """Возвращает причину автоматического завершения игры"""
        alive_players = self.get_alive_players()
        
        # 1. Слишком мало игроков осталось (менее 3)
        if len(alive_players) < 3:
            return f"🌲 Автоматическое завершение: осталось слишком мало игроков ({len(alive_players)})"
        
        # 2. Игра длится слишком долго (более 3 часов)
        if self.game_start_time:
            game_duration = datetime.now() - self.game_start_time
            if game_duration.total_seconds() > 10800:  # 3 часа
                hours = int(game_duration.total_seconds() // 3600)
                minutes = int((game_duration.total_seconds() % 3600) // 60)
                return f"🌲 Автоматическое завершение: игра длится слишком долго ({hours}ч {minutes}м)"
        
        # 3. Слишком много раундов (более 25)
        if self.current_round > 25:
            return f"🌲 Автоматическое завершение: превышен лимит раундов ({self.current_round})"
        
        # 4. Равное количество хищников и травоядных при очень малом количестве игроков
        predators = self.get_players_by_team(Team.PREDATORS)
        herbivores = self.get_players_by_team(Team.HERBIVORES)
        
        if len(alive_players) == 2 and len(predators) == len(herbivores):
            return "🌲 Автоматическое завершение: ничья при финальном противостоянии (1 vs 1)"
            
        return None


    def process_night_actions(self):
        """Обрабатывает ночные действия согласно правилам Лесной Возни"""
        if self.phase != GamePhase.NIGHT:
            return

        # Сброс ночных действий
        self.night_actions = {}

        # Обработка действий по порядку: Волки -> Лиса -> Бобёр -> Крот
        # Этот метод теперь делегирует обработку классу NightActions
        # Реальная обработка происходит в night_actions.py

    def start_day(self):
        """Начинает дневную фазу"""
        self.phase = GamePhase.DAY
        self.phase_end_time = datetime.now() + timedelta(seconds=300)  # 5 минут на обсуждение
        self.day_start_time = datetime.now()

    def start_voting(self):
        """Начинает фазу голосования"""
        self.phase = GamePhase.VOTING
        self.votes = {}
        # Очищаем сохраненные результаты предыдущего голосования
        if hasattr(self, 'last_voting_results'):
            delattr(self, 'last_voting_results')
        self.phase_end_time = datetime.now() + timedelta(seconds=120)  # 2 минуты на голосование

    def vote(self, voter_id: int, target_id: Optional[int]) -> Tuple[bool, bool]:
        """
        Регистрирует голос игрока
        Возвращает: (успех, уже_голосовал)
        target_id может быть None для пропуска голосования
        """
        if not self._is_voting_valid(voter_id, target_id):
            return False, False

        # Проверяем, голосовал ли игрок ранее
        already_voted = voter_id in self.votes
        
        self.votes[voter_id] = target_id
        return True, already_voted
    
    def _is_voting_valid(self, voter_id: int, target_id: Optional[int]) -> bool:
        """Проверяет валидность голосования"""
        if self.phase != GamePhase.VOTING:
            return False

        voter = self.players.get(voter_id)
        if not voter or not voter.is_alive:
            return False

        # Если target_id не None, проверяем цель
        if target_id is not None:
            target = self.players.get(target_id)
            if not target or not target.is_alive:
                return False

            # Защита от голосования за себя
            if voter_id == target_id:
                return False

        return True

    def process_voting(self) -> Optional[Player]:
        """Обрабатывает результаты голосования"""
        # Сохраняем голоса для детального отображения
        self.last_voting_results = self.votes.copy()
        
        if not self.votes:
            return None

        vote_counts, skip_votes = self._count_votes()
        
        # Если нет голосов за конкретных игроков
        if not vote_counts:
            return None

        # Проверяем условия для изгнания
        if not self._should_exile_player(vote_counts, skip_votes):
            return None

        # Находим игрока для изгнания
        exiled_player = self._find_exiled_player(vote_counts)
        if exiled_player:
            exiled_player.die("voted_out")

        return exiled_player
    
    def _count_votes(self) -> Tuple[Dict[int, int], int]:
        """Подсчитывает голоса"""
        vote_counts = {}
        skip_votes = 0
        
        for target_id in self.votes.values():
            if target_id is not None:
                vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
            else:
                skip_votes += 1
        
        return vote_counts, skip_votes
    
    def _should_exile_player(self, vote_counts: Dict[int, int], skip_votes: int) -> bool:
        """Проверяет, должен ли быть изгнан игрок"""
        total_votes = len(self.votes)
        votes_for_exile = sum(vote_counts.values())
        
        # Голосов за пропуск больше или равно голосам за изгнание
        if skip_votes >= votes_for_exile:
            return False
            
        # Голосов за изгнание меньше половины от общего количества
        if votes_for_exile < total_votes / 2:
            return False

        return True
    
    def _find_exiled_player(self, vote_counts: Dict[int, int]) -> Optional[Player]:
        """Находит игрока для изгнания"""
        max_votes = max(vote_counts.values())
        max_vote_players = [pid for pid, votes in vote_counts.items() if votes == max_votes]

        # Если ничья между несколькими игроками - изгнания нет
        if len(max_vote_players) > 1:
            return None

        # Изгоняем игрока с наибольшим количеством голосов
        exiled_id = max_vote_players[0]
        return self.players.get(exiled_id)

    def get_voting_details(self) -> Dict[str, any]:
        """Возвращает детальную информацию о голосовании"""
        # Используем сохраненные результаты голосования, если они есть
        votes_to_analyze = getattr(self, 'last_voting_results', self.votes)
        
        if not votes_to_analyze:
            return {
                "total_votes": 0,
                "skip_votes": 0,
                "votes_for_exile": 0,
                "vote_breakdown": {},
                "voting_summary": "Голосование не проводилось"
            }
        
        # Подсчитываем голоса
        total_votes = len(votes_to_analyze)
        vote_counts = {}
        skip_votes = 0
        vote_breakdown = {}
        
        for voter_id, target_id in votes_to_analyze.items():
            voter = self.players.get(voter_id)
            voter_name = voter.username if voter else f"Игрок {voter_id}"
            
            if target_id is not None:  # Голос за конкретного игрока
                target = self.players.get(target_id)
                target_name = target.username if target else f"Игрок {target_id}"
                vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
                vote_breakdown[voter_name] = f"за {target_name}"
            else:  # Голос за пропуск
                skip_votes += 1
                vote_breakdown[voter_name] = "пропустил"
        
        votes_for_exile = sum(vote_counts.values())
        
        # Формируем сводку
        if votes_for_exile == 0:
            voting_summary = "Все игроки пропустили голосование"
        elif skip_votes >= votes_for_exile:
            voting_summary = f"Большинство за пропуск ({skip_votes} из {total_votes})"
        elif votes_for_exile < total_votes / 2:
            voting_summary = f"Недостаточно голосов за изгнание ({votes_for_exile} из {total_votes})"
        else:
            max_votes = max(vote_counts.values())
            max_vote_players = [pid for pid, votes in vote_counts.items() if votes == max_votes]
            if len(max_vote_players) == 1:
                exiled_player = self.players[max_vote_players[0]]
                voting_summary = f"Изгнан {exiled_player.username} ({max_votes} голосов)"
            else:
                voting_summary = f"Ничья между {len(max_vote_players)} игроками"
        
        return {
            "total_votes": total_votes,
            "skip_votes": skip_votes,
            "votes_for_exile": votes_for_exile,
            "vote_breakdown": vote_breakdown,
            "voting_summary": voting_summary,
            "vote_counts": vote_counts
        }

    def start_night(self):
        """Начинает ночную фазу"""
        self.phase = GamePhase.NIGHT
        self.current_round += 1
        self.phase_end_time = datetime.now() + timedelta(seconds=60)
        self.night_actions = {}
        
        # Обновляем статистику выживания
        for player in self.get_alive_players():
            player.consecutive_nights_survived += 1

        # Сбрасываем одноразовые защиты бобра
        for p in self.get_alive_players():
            p.is_beaver_protected = False

    def is_phase_finished(self) -> bool:
        """Проверяет, закончилась ли текущая фаза"""
        if not self.phase_end_time:
            return False
        return datetime.now() >= self.phase_end_time

    def get_game_statistics(self) -> Dict[str, any]:
        """Возвращает статистику игры"""
        alive_players = self.get_alive_players()
        predators_count = self.get_player_count_by_team(Team.PREDATORS)
        herbivores_count = self.get_player_count_by_team(Team.HERBIVORES)
        
        return {
            "current_round": self.current_round,
            "alive_players": len(alive_players),
            "predators": predators_count,
            "herbivores": herbivores_count,
            "predator_kills": self.game_stats.predator_kills,
            "herbivore_survivals": self.game_stats.herbivore_survivals,
            "fox_thefts": self.game_stats.fox_thefts,
            "beaver_protections": self.game_stats.beaver_protections,
            "game_duration": self._get_game_duration()
        }
    
    def _get_game_duration(self) -> float:
        """Возвращает длительность игры в секундах"""
        if not self.game_start_time:
            return 0
        return (datetime.now() - self.game_start_time).total_seconds()
    
    def get_voting_targets(self, voter_id: int) -> List[Player]:
        """Возвращает список игроков для голосования (исключая самого голосующего)"""
        return [p for p in self.get_alive_players() if p.user_id != voter_id]
    
    def get_final_game_summary(self) -> Dict[str, any]:
        """Возвращает финальную сводку игры"""
        all_players = list(self.players.values())
        alive_players = self.get_alive_players()
        dead_players = self.get_dead_players()
        
        # Группируем игроков по командам
        predators = [p for p in all_players if p.team == Team.PREDATORS]
        herbivores = [p for p in all_players if p.team == Team.HERBIVORES]
        
        # Группируем по ролям
        role_groups = self._group_players_by_role(all_players)
        
        return {
            "total_players": len(all_players),
            "alive_players": len(alive_players),
            "dead_players": len(dead_players),
            "predators": len(predators),
            "herbivores": len(herbivores),
            "role_distribution": role_groups,
            "all_players": all_players,
            "alive_players_list": alive_players,
            "dead_players_list": dead_players,
            "predators_list": predators,
            "herbivores_list": herbivores,
            "current_round": self.current_round,
            "game_duration": self._get_game_duration()
        }
    
    def _group_players_by_role(self, players: List[Player]) -> Dict[str, List[Player]]:
        """Группирует игроков по ролям с русскими названиями"""
        from role_translator import get_role_name_russian
        role_groups = {}
        for role in Role:
            role_groups[get_role_name_russian(role)] = [p for p in players if p.role == role]
        return role_groups
    
    def set_stage_pinned_message(self, stage: str, message_id: int):
        """Сохраняет ID закрепленного сообщения для этапа"""
        self.stage_pinned_messages[stage] = message_id
    
    def get_stage_pinned_message(self, stage: str) -> Optional[int]:
        """Возвращает ID закрепленного сообщения для этапа"""
        return self.stage_pinned_messages.get(stage)
    
    def clear_stage_pinned_message(self, stage: str):
        """Очищает ID закрепленного сообщения для этапа"""
        if stage in self.stage_pinned_messages:
            del self.stage_pinned_messages[stage]
    
    def clear_all_stage_pinned_messages(self):
        """Очищает все ID закрепленных сообщений этапов"""
        self.stage_pinned_messages.clear()
    
    def set_day_timer_task(self, task):
        """Устанавливает задачу таймера дневной фазы"""
        self.day_timer_task = task
    
    def cancel_day_timer(self):
        """Отменяет таймер дневной фазы"""
        if self.day_timer_task:
            if not self.day_timer_task.done():
                self.day_timer_task.cancel()
            self.day_timer_task = None
    
    def get_day_timer_status(self) -> str:
        """Возвращает статус дневного таймера"""
        if not self.day_start_time:
            return "Таймер не запущен"
        
        elapsed = self._get_day_elapsed_time()
        remaining = max(0, 300 - elapsed)  # 300 секунд = 5 минут
        
        if not self.day_timer_task:
            return f"Таймер не найден (прошло {elapsed:.1f}с)"
        
        if self.day_timer_task.done():
            return f"Таймер завершен (прошло {elapsed:.1f}с)"
        else:
            return f"Таймер активен (осталось {remaining:.1f}с)"
    
    def _get_day_elapsed_time(self) -> float:
        """Возвращает время, прошедшее с начала дневной фазы"""
        if not self.day_start_time:
            return 0
        return (datetime.now() - self.day_start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Сериализует состояние игры в словарь для сохранения в БД
        
        Returns:
            Dict с данными игры
        """
        # Сериализуем игроков
        players_data = []
        for player in self.players.values():
            players_data.append({
                'id': f"{self.chat_id}_{player.user_id}",
                'user_id': player.user_id,
                'username': player.username,
                'role': player.role.value if player.role else None,
                'is_alive': player.is_alive,
                'team': player.team.value if player.team else None
            })
        
        # Сериализуем голоса
        votes_data = {}
        for voter_id, target_id in self.votes.items():
            votes_data[str(voter_id)] = str(target_id) if target_id else None
        
        # Сериализуем ночные действия
        night_actions_data = {}
        for actor_id, action in self.night_actions.items():
            night_actions_data[str(actor_id)] = {
                'action': action.get('action'),
                'target': action.get('target'),
                'data': action.get('data', {})
            }
        
        return {
            'id': f"game_{self.chat_id}",
            'chat_id': self.chat_id,
            'thread_id': self.thread_id,
            'phase': self.phase.value,
            'round_number': self.current_round,
            'started_at': self.game_start_time.isoformat() if self.game_start_time else None,
            'finished_at': None,  # Будет установлено при завершении игры
            'winner_team': None,  # Будет установлено при завершении игры
            'is_test_mode': self.is_test_mode,
            'min_players': 3 if self.is_test_mode else 6,
            'max_players': 12,
            'day_duration': 300,
            'night_duration': 60,
            'voting_duration': 60,
            'discussion_duration': 300,
            'players': players_data,
            'votes': votes_data,
            'night_actions': night_actions_data,
            'pinned_message_id': self.pinned_message_id,
            'stage_pinned_messages': self.stage_pinned_messages,
            'game_over_sent': self.game_over_sent,
            'last_wolf_victim': self.last_wolf_victim,
            'last_mole_check': self.last_mole_check,
            'game_stats': {
                'predator_kills': self.game_stats.predator_kills,
                'herbivore_survivals': self.game_stats.herbivore_survivals,
                'fox_thefts': self.game_stats.fox_thefts,
                'beaver_protections': self.game_stats.beaver_protections
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Game':
        """
        Восстанавливает состояние игры из словаря
        
        Args:
            data: Словарь с данными игры
            
        Returns:
            Восстановленный объект Game
        """
        # Создаем новый объект игры
        game = cls(
            chat_id=data['chat_id'],
            thread_id=data.get('thread_id'),
            is_test_mode=data.get('is_test_mode', True)
        )
        
        # Восстанавливаем основное состояние
        game.phase = GamePhase(data['phase'])
        game.current_round = data.get('round_number', 0)
        
        # Восстанавливаем временные метки
        if data.get('started_at'):
            if isinstance(data['started_at'], str):
                game.game_start_time = datetime.fromisoformat(data['started_at'])
            else:
                game.game_start_time = data['started_at']
        
        # Восстанавливаем игроков
        game.players = {}
        for player_data in data.get('players', []):
            user_id = player_data['user_id']
            role = Role(player_data['role']) if player_data.get('role') else None
            team = Team(player_data['team']) if player_data.get('team') else None
            
            player = Player(
                user_id=user_id,
                username=player_data.get('username'),
                role=role,
                team=team
            )
            player.is_alive = player_data.get('is_alive', True)
            game.players[user_id] = player
        
        # Восстанавливаем голоса
        game.votes = {}
        for voter_id_str, target_id_str in data.get('votes', {}).items():
            voter_id = int(voter_id_str)
            target_id = int(target_id_str) if target_id_str else None
            game.votes[voter_id] = target_id
        
        # Восстанавливаем ночные действия
        game.night_actions = {}
        for actor_id_str, action_data in data.get('night_actions', {}).items():
            actor_id = int(actor_id_str)
            game.night_actions[actor_id] = action_data
        
        # Восстанавливаем UI состояние
        game.pinned_message_id = data.get('pinned_message_id')
        game.stage_pinned_messages = data.get('stage_pinned_messages', {})
        game.game_over_sent = data.get('game_over_sent', False)
        game.last_wolf_victim = data.get('last_wolf_victim')
        game.last_mole_check = data.get('last_mole_check')
        
        # Восстанавливаем статистику
        stats_data = data.get('game_stats', {})
        game.game_stats.predator_kills = stats_data.get('predator_kills', 0)
        game.game_stats.herbivore_survivals = stats_data.get('herbivore_survivals', 0)
        game.game_stats.fox_thefts = stats_data.get('fox_thefts', 0)
        game.game_stats.beaver_protections = stats_data.get('beaver_protections', 0)
        
        return game