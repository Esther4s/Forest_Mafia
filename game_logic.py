import random
from enum import Enum
from typing import Dict, List, Optional
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
    supplies: int = 2  # Количество припасов (по умолчанию 2)
    max_supplies: int = 2  # Максимальное количество припасов
    is_fox_stolen: int = 0  # Количество краж Лисой
    stolen_supplies: int = 0  # Количество украденных припасов (для восстановления)
    is_beaver_protected: bool = False  # Защищен ли Бобром
    consecutive_nights_survived: int = 0  # Сколько ночей подряд выжил
    last_action_round: int = 0  # В каком раунде последний раз действовал

class Game:
    def __init__(self, chat_id: int, thread_id: Optional[int] = None):
        self.chat_id = chat_id
        self.thread_id = thread_id  # ID темы для форумных групп
        self.players: Dict[int, Player] = {}
        self.phase = GamePhase.WAITING
        self.current_round = 0
        self.night_actions = {}
        self.votes = {}
        self.game_start_time = None
        self.phase_end_time = None
        self.is_test_mode = True  # Enabled test mode by default
        self.pinned_message_id = None  # ID закрепленного сообщения о присоединении
        self.stage_pinned_messages = {}  # ID закрепленных сообщений для каждого этапа
        self.total_voters = 0  # Общее количество голосующих
        self.voting_type = ""  # Тип голосования (exile, wolf, etc.)
        self.predator_kills = 0  # Количество убийств хищников
        self.herbivore_survivals = 0  # Количество выживаний травоядных
        self.fox_thefts = 0  # Общее количество краж лисы
        self.beaver_protections = 0  # Количество защит бобра
        self.game_over_sent = False  # сообщение об окончании уже отправлено?
        self.day_timer_task = None  # Задача таймера дневной фазы
        self.day_start_time = None  # Время начала дневной фазы

    def add_player(self, user_id: int, username: str) -> bool:
        """Добавляет игрока в игру"""
        # Limit player count to 12 in normal mode, no limit in test mode for now
        if not self.is_test_mode and len(self.players) >= 12:
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
        # Allow starting with 3 players in test mode
        if self.is_test_mode:
            return len(self.players) >= 3
        return len(self.players) >= 6

    def assign_roles(self):
        """Распределяет роли между игроками согласно новой логике"""
        player_list = list(self.players.values())
        total_players = len(player_list)
        
        # Вычисляем количество каждой роли согласно новой логике
        roles = self._calculate_role_distribution(total_players)
        
        # Создаем список всех ролей для распределения
        all_roles = []
        
        # Добавляем волков
        for _ in range(roles['wolves']):
            all_roles.append((Role.WOLF, Team.PREDATORS))
        
        # Добавляем лису
        for _ in range(roles['fox']):
            all_roles.append((Role.FOX, Team.PREDATORS))
        
        # Добавляем крота
        for _ in range(roles['mole']):
            all_roles.append((Role.MOLE, Team.HERBIVORES))
        
        # Добавляем бобров
        for _ in range(roles['beaver']):
            all_roles.append((Role.BEAVER, Team.HERBIVORES))
        
        # Добавляем зайцев
        for _ in range(roles['hare']):
            all_roles.append((Role.HARE, Team.HERBIVORES))
        
        # Перемешиваем роли для случайности
        random.shuffle(all_roles)
        
        # Назначаем роли игрокам
        for i, player in enumerate(player_list):
            if i < len(all_roles):
                role, team = all_roles[i]
                player.role = role
                player.team = team

    def _calculate_role_distribution(self, total_players: int) -> dict:
        """Вычисляет распределение ролей согласно новой логике"""
        roles = {
            'wolves': 0,
            'fox': 0,
            'mole': 0,
            'beaver': 0,
            'hare': 0
        }
        
        # 1. Волки
        if 3 <= total_players <= 6:
            roles['wolves'] = 1
        elif 7 <= total_players <= 9:
            roles['wolves'] = 2
        elif 10 <= total_players <= 12:
            roles['wolves'] = 3
        
        # 2. Крот (добавляется с 4 игроков, всегда 1)
        if total_players >= 4:
            roles['mole'] = 1
        
        # 3. Бобер (добавляется с 6 игроков, при 11-12 игроках становится 2)
        if total_players >= 6:
            if 11 <= total_players <= 12:
                roles['beaver'] = 2
            else:
                roles['beaver'] = 1
        
        # 4. Лиса (добавляется с 6 игроков, всегда 1)
        if total_players >= 6:
            roles['fox'] = 1
        
        # 5. Зайцы (всегда остаются большинством, минимум 2)
        used_roles = roles['wolves'] + roles['fox'] + roles['mole'] + roles['beaver']
        roles['hare'] = total_players - used_roles
        
        # Проверяем, что зайцев минимум 2
        if roles['hare'] < 2:
            # Если зайцев меньше 2, корректируем другие роли
            deficit = 2 - roles['hare']
            if roles['beaver'] > 0 and deficit > 0:
                roles['beaver'] = max(0, roles['beaver'] - deficit)
                roles['hare'] = 2
            elif roles['mole'] > 0 and deficit > 0:
                roles['mole'] = max(0, roles['mole'] - deficit)
                roles['hare'] = 2
        
        return roles

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
        """
        Правила:
        - Волки выигрывают, если их >= остальных.
        - Травоядные выигрывают, если волков нет.
        """
        alive = self.get_alive_players()
        total_alive = len(alive)

        if total_alive == 0:
            return Team.HERBIVORES

        wolves = [p for p in alive if p.role == Role.WOLF]
        wolves_count = len(wolves)

        if wolves_count > 0 and wolves_count >= (total_alive - wolves_count):
            return Team.PREDATORS

        if wolves_count == 0:
            return Team.HERBIVORES

        return None
    
    
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
                if self.predator_kills > self.herbivore_survivals:
                    return Team.PREDATORS
                else:
                    return Team.HERBIVORES
        
        # 3. Слишком много раундов (более 25 для лесной мафии)
        if self.current_round > 25:
            # При превышении лимита раундов определяем победителя по статистике
            if self.predator_kills > self.herbivore_survivals:
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
        self.day_start_time = datetime.now()  # Записываем время начала дневной фазы

    def start_voting(self):
        """Начинает фазу голосования"""
        self.phase = GamePhase.VOTING
        self.votes = {}
        # Очищаем сохраненные результаты предыдущего голосования
        if hasattr(self, 'last_voting_results'):
            delattr(self, 'last_voting_results')
        self.phase_end_time = datetime.now() + timedelta(seconds=120)  # 2 минуты на голосование

    def vote(self, voter_id: int, target_id: Optional[int]) -> tuple[bool, bool]:
        """
        Регистрирует голос игрока
        Возвращает: (успех, уже_голосовал)
        target_id может быть None для пропуска голосования
        """
        if self.phase != GamePhase.VOTING:
            return False, False

        voter = self.players.get(voter_id)
        if not voter or not voter.is_alive:
            return False, False

        # Если target_id не None, проверяем цель
        if target_id is not None:
            target = self.players.get(target_id)
            if not target or not target.is_alive:
                return False, False

            # Защита от голосования за себя
            if voter_id == target_id:
                return False, False

        # Проверяем, голосовал ли игрок ранее
        already_voted = voter_id in self.votes
        
        self.votes[voter_id] = target_id
        return True, already_voted

    def process_voting(self) -> Optional[Player]:
        """Обрабатывает результаты голосования с учетом мнения большинства"""
        # Сохраняем голоса для детального отображения (даже если их нет)
        self.last_voting_results = self.votes.copy()
        
        if not self.votes:
            return None

        # Подсчитываем общее количество голосов
        total_votes = len(self.votes)
        
        # Подсчет голосов за конкретных игроков (исключаем голоса за None - пропуски)
        vote_counts = {}
        skip_votes = 0
        
        for target_id in self.votes.values():
            if target_id is not None:  # Голос за конкретного игрока
                vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
            else:  # Голос за пропуск
                skip_votes += 1

        # Если нет голосов за конкретных игроков (все проголосовали за пропуск)
        if not vote_counts:
            return None

        # Находим игрока с максимальным количеством голосов
        max_votes = max(vote_counts.values())
        max_vote_players = [pid for pid, votes in vote_counts.items() if votes == max_votes]

        # НОВАЯ ЛОГИКА: Проверяем, что голосов за изгнание больше, чем за пропуск
        # И что голосов за изгнание больше половины от общего количества голосов
        votes_for_exile = sum(vote_counts.values())
        
        # Если голосов за пропуск больше или равно голосам за изгнание - никто не изгоняется
        if skip_votes >= votes_for_exile:
            return None
            
        # Если голосов за изгнание меньше половины от общего количества - никто не изгоняется
        if votes_for_exile < total_votes / 2:
            return None

        # Если ничья между несколькими игроками - изгнания нет
        if len(max_vote_players) > 1:
            return None

        # Изгоняем игрока с наибольшим количеством голосов
        exiled_id = max_vote_players[0]
        exiled_player = self.players[exiled_id]
        exiled_player.is_alive = False

        return exiled_player

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
        """Возвращает статистику игры для лесной мафии"""
        alive_players = self.get_alive_players()
        predators = self.get_players_by_team(Team.PREDATORS)
        herbivores = self.get_players_by_team(Team.HERBIVORES)
        
        return {
            "current_round": self.current_round,
            "alive_players": len(alive_players),
            "predators": len(predators),
            "herbivores": len(herbivores),
            "predator_kills": self.predator_kills,
            "herbivore_survivals": self.herbivore_survivals,
            "fox_thefts": self.fox_thefts,
            "beaver_protections": self.beaver_protections,
            "game_duration": (datetime.now() - self.game_start_time).total_seconds() if self.game_start_time else 0
        }
    
    def get_voting_targets(self, voter_id: int) -> List[Player]:
        """Возвращает список игроков для голосования (исключая самого голосующего)"""
        return [p for p in self.get_alive_players() if p.user_id != voter_id]
    
    def get_final_game_summary(self) -> Dict[str, any]:
        """Возвращает финальную сводку игры с ролями всех участников"""
        all_players = list(self.players.values())
        alive_players = self.get_alive_players()
        dead_players = [p for p in all_players if not p.is_alive]
        
        # Группируем игроков по командам
        predators = [p for p in all_players if p.team == Team.PREDATORS]
        herbivores = [p for p in all_players if p.team == Team.HERBIVORES]
        
        # Группируем по ролям с русскими названиями
        from role_translator import get_role_name_russian
        role_groups = {}
        for role in Role:
            role_groups[get_role_name_russian(role)] = [p for p in all_players if p.role == role]
        
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
            "game_duration": (datetime.now() - self.game_start_time).total_seconds() if self.game_start_time else 0
        }
    
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
    
    def get_day_timer_status(self):
        """Возвращает статус дневного таймера"""
        if not self.day_start_time:
            return "Таймер не запущен"
        
        from datetime import datetime
        elapsed = (datetime.now() - self.day_start_time).total_seconds()
        remaining = max(0, 300 - elapsed)  # 300 секунд = 5 минут
        
        if self.day_timer_task:
            if self.day_timer_task.done():
                return f"Таймер завершен (прошло {elapsed:.1f}с)"
            else:
                return f"Таймер активен (осталось {remaining:.1f}с)"
        else:
            return f"Таймер не найден (прошло {elapsed:.1f}с)"