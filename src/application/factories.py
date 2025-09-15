#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Фабрики для создания объектов
Инкапсулируют логику создания сложных объектов
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from ..domain.entities import Game, Player, GameStatistics
from ..domain.value_objects import (
    GameId, ChatId, UserId, Username, Supplies, GameDuration,
    GamePhase, Team, Role
)
from .services import RoleAssignmentService


class GameFactory:
    """Фабрика для создания игр"""
    
    def __init__(self, role_assignment_service: RoleAssignmentService):
        self.role_assignment_service = role_assignment_service
    
    def create_game(
        self, 
        chat_id: ChatId, 
        thread_id: Optional[int] = None, 
        is_test_mode: bool = False
    ) -> Game:
        """Создает новую игру"""
        game_id = GameId(f"game_{chat_id.value}_{datetime.now().timestamp()}")
        
        return Game(
            game_id=game_id,
            chat_id=chat_id,
            thread_id=thread_id,
            is_test_mode=is_test_mode
        )
    
    def create_game_from_dict(self, data: Dict[str, Any]) -> Game:
        """Создает игру из словаря (для восстановления из БД)"""
        game_id = GameId(data['id'])
        chat_id = ChatId(data['chat_id'])
        
        game = Game(
            game_id=game_id,
            chat_id=chat_id,
            thread_id=data.get('thread_id'),
            is_test_mode=data.get('is_test_mode', True)
        )
        
        # Восстанавливаем состояние
        game.phase = GamePhase(data['phase'])
        game.current_round = data.get('round_number', 0)
        
        # Восстанавливаем временные метки
        if data.get('started_at'):
            if isinstance(data['started_at'], str):
                start_time = datetime.fromisoformat(data['started_at'])
            else:
                start_time = data['started_at']
            game.game_duration = GameDuration(start_time)
        
        # Восстанавливаем игроков
        for player_data in data.get('players', []):
            user_id = UserId(player_data['user_id'])
            username = Username(player_data.get('username', f"Player_{user_id.value}"))
            role = Role(player_data['role']) if player_data.get('role') else Role.HARE
            team = Team(player_data['team']) if player_data.get('team') else Team.HERBIVORES
            
            player = Player(
                user_id=user_id,
                username=username,
                role=role,
                team=team,
                supplies=Supplies(2, 2)  # Восстанавливаем припасы
            )
            player.is_alive = player_data.get('is_alive', True)
            game.players[user_id.value] = player
        
        # Восстанавливаем голоса
        for voter_id_str, target_id_str in data.get('votes', {}).items():
            voter_id = int(voter_id_str)
            target_id = int(target_id_str) if target_id_str else None
            game.votes[voter_id] = target_id
        
        # Восстанавливаем ночные действия
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


class PlayerFactory:
    """Фабрика для создания игроков"""
    
    def create_player(
        self, 
        user_id: UserId, 
        username: Username, 
        role: Role, 
        team: Team,
        supplies: Optional[Supplies] = None
    ) -> Player:
        """Создает нового игрока"""
        if supplies is None:
            supplies = Supplies(2, 2)
        
        return Player(
            user_id=user_id,
            username=username,
            role=role,
            team=team,
            supplies=supplies
        )
    
    def create_player_with_role_effects(
        self, 
        user_id: UserId, 
        username: Username, 
        role: Role, 
        team: Team,
        extra_lives: int = 0
    ) -> Player:
        """Создает игрока с эффектами предметов"""
        player = self.create_player(user_id, username, role, team)
        
        if extra_lives > 0:
            player.apply_extra_lives(extra_lives)
        
        return player


class GameStatisticsFactory:
    """Фабрика для создания статистики игры"""
    
    def create_empty_statistics(self) -> GameStatistics:
        """Создает пустую статистику"""
        return GameStatistics()
    
    def create_statistics_from_dict(self, data: Dict[str, Any]) -> GameStatistics:
        """Создает статистику из словаря"""
        stats = GameStatistics()
        stats.predator_kills = data.get('predator_kills', 0)
        stats.herbivore_survivals = data.get('herbivore_survivals', 0)
        stats.fox_thefts = data.get('fox_thefts', 0)
        stats.beaver_protections = data.get('beaver_protections', 0)
        stats.total_voters = data.get('total_voters', 0)
        stats.voting_type = data.get('voting_type', "")
        return stats


class ValueObjectFactory:
    """Фабрика для создания value objects"""
    
    @staticmethod
    def create_user_id(value: int) -> UserId:
        """Создает UserId"""
        return UserId(value)
    
    @staticmethod
    def create_chat_id(value: int) -> ChatId:
        """Создает ChatId"""
        return ChatId(value)
    
    @staticmethod
    def create_username(value: str) -> Username:
        """Создает Username"""
        return Username(value)
    
    @staticmethod
    def create_supplies(current: int, maximum: int = 2) -> Supplies:
        """Создает Supplies"""
        return Supplies(current, maximum)
    
    @staticmethod
    def create_game_duration(start_time: datetime, end_time: Optional[datetime] = None) -> GameDuration:
        """Создает GameDuration"""
        return GameDuration(start_time, end_time)
