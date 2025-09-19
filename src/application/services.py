#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервисы приложения
Содержат бизнес-логику и координируют работу между доменом и инфраструктурой
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from ..domain.entities import Game, Player, GameStatistics
from ..domain.value_objects import GameId, ChatId, UserId, Username, GamePhase, Team, Role
from ..domain.repositories import (
    GameRepository, PlayerRepository, UserRepository, 
    GameEventRepository, ChatSettingsRepository, StatisticsRepository
)


class GameService:
    """Сервис для управления играми"""
    
    def __init__(
        self,
        game_repo: GameRepository,
        player_repo: PlayerRepository,
        event_repo: GameEventRepository
    ):
        self.game_repo = game_repo
        self.player_repo = player_repo
        self.event_repo = event_repo
    
    async def create_game(self, chat_id: ChatId, thread_id: Optional[int] = None, is_test_mode: bool = False) -> Game:
        """Создает новую игру"""
        game_id = GameId(f"game_{chat_id.value}_{datetime.now().timestamp()}")
        
        game = Game(
            game_id=game_id,
            chat_id=chat_id,
            thread_id=thread_id,
            is_test_mode=is_test_mode
        )
        
        await self.game_repo.save(game)
        await self.event_repo.log_event(game_id, "game_created", {
            "chat_id": chat_id.value,
            "thread_id": thread_id,
            "is_test_mode": is_test_mode
        })
        
        return game
    
    async def get_active_game(self, chat_id: ChatId, thread_id: Optional[int] = None) -> Optional[Game]:
        """Получает активную игру в чате"""
        return await self.game_repo.get_by_chat(chat_id, thread_id)
    
    async def add_player_to_game(self, game: Game, user_id: UserId, username: Username) -> bool:
        """Добавляет игрока в игру"""
        if game.phase != GamePhase.WAITING:
            return False
        
        success = game.add_player(user_id, username)
        if success:
            await self.game_repo.save(game)
            await self.event_repo.log_event(game.game_id, "player_joined", {
                "user_id": user_id.value,
                "username": username.value
            })
        
        return success
    
    async def remove_player_from_game(self, game: Game, user_id: UserId) -> bool:
        """Удаляет игрока из игры"""
        success = game.remove_player(user_id)
        if success:
            await self.game_repo.save(game)
            await self.event_repo.log_event(game.game_id, "player_left", {
                "user_id": user_id.value
            })
        
        return success
    
    async def start_game(self, game: Game) -> bool:
        """Начинает игру"""
        if not game.can_start_game():
            return False
        
        success = game.start_game()
        if success:
            await self.game_repo.save(game)
            await self.event_repo.log_event(game.game_id, "game_started", {
                "player_count": len(game.players),
                "round": game.current_round
            })
        
        return success
    
    async def end_game(self, game: Game, winner: Optional[Team], reason: str) -> None:
        """Завершает игру"""
        game.phase = GamePhase.GAME_OVER
        if game.game_duration:
            game.game_duration = game.game_duration.finish()
        
        await self.game_repo.save(game)
        await self.event_repo.log_event(game.game_id, "game_ended", {
            "winner": winner.value if winner else None,
            "reason": reason,
            "duration": game.game_duration.total_seconds if game.game_duration else 0
        })


class RoleAssignmentService:
    """Сервис для распределения ролей"""
    
    def assign_roles(self, players: List[Player]) -> None:
        """Распределяет роли между игроками"""
        total_players = len(players)
        
        # Вычисляем распределение ролей
        role_counts = self._calculate_role_distribution(total_players)
        
        # Создаем список ролей для распределения
        all_roles = self._create_role_list(role_counts)
        
        # Перемешиваем и назначаем роли
        import random
        random.shuffle(all_roles)
        self._assign_roles_to_players(players, all_roles)
    
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
    
    def _ensure_minimum_hares(self, roles: Dict[str, int]) -> None:
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
    
    def _assign_roles_to_players(self, players: List[Player], roles: List[Tuple[Role, Team]]) -> None:
        """Назначает роли игрокам"""
        for i, player in enumerate(players):
            if i < len(roles):
                role, team = roles[i]
                player.role = role
                player.team = team


class VotingService:
    """Сервис для обработки голосования"""
    
    def process_voting(self, game: Game) -> Optional[Player]:
        """Обрабатывает результаты голосования"""
        if not game.votes:
            return None

        vote_counts, skip_votes = self._count_votes(game.votes)
        
        # Если нет голосов за конкретных игроков
        if not vote_counts:
            return None

        # Проверяем условия для изгнания
        if not self._should_exile_player(vote_counts, skip_votes, len(game.votes)):
            return None

        # Находим игрока для изгнания
        exiled_player = self._find_exiled_player(game, vote_counts)
        if exiled_player:
            exiled_player.die("voted_out")

        return exiled_player
    
    def _count_votes(self, votes: Dict[int, Optional[int]]) -> tuple[Dict[int, int], int]:
        """Подсчитывает голоса"""
        vote_counts = {}
        skip_votes = 0
        
        for target_id in votes.values():
            if target_id is not None:
                vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
            else:
                skip_votes += 1
        
        return vote_counts, skip_votes
    
    def _should_exile_player(self, vote_counts: Dict[int, int], skip_votes: int, total_votes: int) -> bool:
        """Проверяет, должен ли быть изгнан игрок"""
        votes_for_exile = sum(vote_counts.values())
        
        # Голосов за пропуск больше или равно голосам за изгнание
        if skip_votes >= votes_for_exile:
            return False
            
        # Голосов за изгнание меньше половины от общего количества
        if votes_for_exile < total_votes / 2:
            return False

        return True
    
    def _find_exiled_player(self, game: Game, vote_counts: Dict[int, int]) -> Optional[Player]:
        """Находит игрока для изгнания"""
        max_votes = max(vote_counts.values())
        max_vote_players = [pid for pid, votes in vote_counts.items() if votes == max_votes]

        # Если ничья между несколькими игроками - изгнания нет
        if len(max_vote_players) > 1:
            return None

        # Изгоняем игрока с наибольшим количеством голосов
        exiled_id = max_vote_players[0]
        return game.players.get(exiled_id)


class UserService:
    """Сервис для работы с пользователями"""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    async def get_or_create_user(self, user_id: UserId, username: str, first_name: str = None) -> Dict[str, Any]:
        """Получает или создает пользователя"""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            await self.user_repo.create(user_id, username, first_name)
            user = await self.user_repo.get_by_id(user_id)
        
        return user or {}
    
    async def get_display_name(self, user_id: UserId, username: str = None, first_name: str = None) -> str:
        """Получает отображаемое имя пользователя"""
        nickname = await self.user_repo.get_nickname(user_id)
        if nickname:
            return nickname
        elif username and not username.isdigit():
            return f"@{username}"
        elif first_name:
            return first_name
        else:
            return f"ID:{user_id.value}"
    
    async def update_balance(self, user_id: UserId, amount: int) -> None:
        """Обновляет баланс пользователя"""
        await self.user_repo.update_balance(user_id, amount)
    
    async def get_balance(self, user_id: UserId) -> int:
        """Получает баланс пользователя"""
        return await self.user_repo.get_balance(user_id)
