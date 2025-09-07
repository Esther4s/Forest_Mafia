#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Dict, List, Optional, Any
from datetime import datetime
from database import init_database, get_db_session
from database_services import (
    GameService, PlayerService, GameEventService, 
    PlayerActionService, VoteService, PlayerStatsService, BotSettingsService
)
from config import DATABASE_URL

class DatabaseAdapter:
    """Адаптер для интеграции базы данных с игровой логикой"""
    
    def __init__(self):
        self.db_manager = init_database(DATABASE_URL)
        self.game_service = GameService()
        self.player_service = PlayerService()
        self.event_service = GameEventService()
        self.action_service = PlayerActionService()
        self.vote_service = VoteService()
        self.stats_service = PlayerStatsService()
        self.settings_service = BotSettingsService()
    
    # === Управление играми ===
    
    def create_game(self, chat_id: int, thread_id: Optional[int] = None, 
                   settings: Dict[str, Any] = None) -> str:
        """Создать новую игру и вернуть её ID"""
        game = self.game_service.create_game(chat_id, thread_id, settings)
        self.event_service.log_event(
            game.id, 
            "game_created", 
            {"chat_id": chat_id, "thread_id": thread_id}
        )
        return game.id
    
    def get_active_game(self, chat_id: int, thread_id: Optional[int] = None) -> Optional[str]:
        """Получить ID активной игры в чате"""
        game = self.game_service.get_active_game(chat_id, thread_id)
        return game.id if game else None
    
    def start_game(self, game_id: str) -> bool:
        """Начать игру"""
        success = self.game_service.update_game_status(game_id, "active", "night")
        if success:
            self.event_service.log_event(game_id, "game_started")
        return success
    
    def finish_game(self, game_id: str, winner_team: str) -> bool:
        """Завершить игру"""
        success = self.game_service.finish_game(game_id, winner_team)
        if success:
            self.event_service.log_event(
                game_id, 
                "game_finished", 
                {"winner_team": winner_team}
            )
            # Обновляем статистику игроков
            self._update_player_stats_after_game(game_id, winner_team)
        return success
    
    def get_game_info(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию об игре"""
        game = self.game_service.get_game_by_id(game_id)
        if not game:
            return None
        
        return {
            "id": game.id,
            "chat_id": game.chat_id,
            "thread_id": game.thread_id,
            "status": game.status,
            "phase": game.phase,
            "round_number": game.round_number,
            "created_at": game.created_at,
            "started_at": game.started_at,
            "finished_at": game.finished_at,
            "winner_team": game.winner_team,
            "settings": game.settings
        }
    
    # === Управление игроками ===
    
    def add_player(self, game_id: str, user_id: int, username: str = None,
                  first_name: str = None, last_name: str = None) -> bool:
        """Добавить игрока в игру"""
        player = self.player_service.add_player_to_game(
            game_id, user_id, username, first_name, last_name
        )
        if player:
            self.event_service.log_event(
                game_id, 
                "player_joined", 
                {"user_id": user_id, "username": username}
            )
            return True
        return False
    
    def remove_player(self, game_id: str, user_id: int) -> bool:
        """Удалить игрока из игры"""
        success = self.player_service.remove_player_from_game(game_id, user_id)
        if success:
            self.event_service.log_event(
                game_id, 
                "player_left", 
                {"user_id": user_id}
            )
        return success
    
    def get_players(self, game_id: str, alive_only: bool = False) -> List[Dict[str, Any]]:
        """Получить список игроков"""
        players = self.player_service.get_game_players(game_id, alive_only)
        return [
            {
                "id": player.id,
                "user_id": player.user_id,
                "username": player.username,
                "first_name": player.first_name,
                "last_name": player.last_name,
                "role": player.role,
                "team": player.team,
                "is_alive": player.is_alive,
                "is_online": player.is_online,
                "joined_at": player.joined_at,
                "died_at": player.died_at,
                "death_reason": player.death_reason
            }
            for player in players
        ]
    
    def assign_roles(self, game_id: str, role_assignments: Dict[int, Dict[str, str]]) -> bool:
        """Назначить роли игрокам"""
        success = True
        for user_id, role_info in role_assignments.items():
            # Находим игрока по user_id
            players = self.player_service.get_game_players(game_id)
            player = next((p for p in players if p.user_id == user_id), None)
            if player:
                role_success = self.player_service.assign_role(
                    player.id, role_info["role"], role_info["team"]
                )
                if not role_success:
                    success = False
        
        if success:
            self.event_service.log_event(
                game_id, 
                "roles_assigned", 
                {"assignments": role_assignments}
            )
        return success
    
    def kill_player(self, game_id: str, user_id: int, reason: str = "killed") -> bool:
        """Убить игрока"""
        players = self.player_service.get_game_players(game_id)
        player = next((p for p in players if p.user_id == user_id), None)
        if player:
            success = self.player_service.kill_player(player.id, reason)
            if success:
                self.event_service.log_event(
                    game_id, 
                    "player_died", 
                    {"user_id": user_id, "reason": reason}
                )
            return success
        return False
    
    # === Действия игроков ===
    
    def record_action(self, game_id: str, user_id: int, action_type: str,
                     target_user_id: int = None, action_data: Dict[str, Any] = None,
                     round_number: int = 0, phase: str = "night") -> bool:
        """Записать действие игрока"""
        players = self.player_service.get_game_players(game_id)
        player = next((p for p in players if p.user_id == user_id), None)
        target_player = None
        
        if target_user_id:
            target_player = next((p for p in players if p.user_id == target_user_id), None)
        
        if player:
            action = self.action_service.record_action(
                player.id, game_id, action_type,
                target_player.id if target_player else None,
                action_data, round_number, phase
            )
            return action is not None
        return False
    
    def get_actions(self, game_id: str, round_number: int = None, 
                   action_type: str = None) -> List[Dict[str, Any]]:
        """Получить действия игроков"""
        actions = self.action_service.get_player_actions(game_id, round_number, action_type)
        return [
            {
                "id": action.id,
                "player_id": action.player_id,
                "game_id": action.game_id,
                "action_type": action.action_type,
                "target_id": action.target_id,
                "action_data": action.action_data,
                "round_number": action.round_number,
                "phase": action.phase,
                "created_at": action.created_at
            }
            for action in actions
        ]
    
    # === Голосования ===
    
    def cast_vote(self, game_id: str, voter_user_id: int, target_user_id: int = None,
                 round_number: int = 0, phase: str = "voting") -> bool:
        """Записать голос"""
        players = self.player_service.get_game_players(game_id)
        voter = next((p for p in players if p.user_id == voter_user_id), None)
        target = None
        
        if target_user_id:
            target = next((p for p in players if p.user_id == target_user_id), None)
        
        if voter:
            vote = self.vote_service.cast_vote(
                game_id, voter.id, target.id if target else None,
                round_number, phase
            )
            return vote is not None
        return False
    
    def get_votes(self, game_id: str, round_number: int = None, 
                 phase: str = None) -> List[Dict[str, Any]]:
        """Получить голоса"""
        votes = self.vote_service.get_votes(game_id, round_number, phase)
        return [
            {
                "id": vote.id,
                "game_id": vote.game_id,
                "voter_id": vote.voter_id,
                "target_id": vote.target_id,
                "round_number": vote.round_number,
                "phase": vote.phase,
                "created_at": vote.created_at
            }
            for vote in votes
        ]
    
    def get_vote_results(self, game_id: str, round_number: int, 
                        phase: str = "voting") -> Dict[str, int]:
        """Получить результаты голосования"""
        return self.vote_service.get_vote_results(game_id, round_number, phase)
    
    # === События ===
    
    def log_event(self, game_id: str, event_type: str, event_data: Dict[str, Any] = None):
        """Записать событие игры"""
        return self.event_service.log_event(game_id, event_type, event_data)
    
    def get_events(self, game_id: str, event_type: str = None) -> List[Dict[str, Any]]:
        """Получить события игры"""
        events = self.event_service.get_game_events(game_id, event_type)
        return [
            {
                "id": event.id,
                "game_id": event.game_id,
                "event_type": event.event_type,
                "event_data": event.event_data,
                "created_at": event.created_at
            }
            for event in events
        ]
    
    # === Статистика ===
    
    def get_player_stats(self, user_id: int) -> Dict[str, Any]:
        """Получить статистику игрока"""
        stats = self.stats_service.get_or_create_stats(user_id)
        return {
            "user_id": stats.user_id,
            "username": stats.username,
            "total_games": stats.total_games,
            "games_won": stats.games_won,
            "games_lost": stats.games_lost,
            "times_wolf": stats.times_wolf,
            "times_fox": stats.times_fox,
            "times_hare": stats.times_hare,
            "times_mole": stats.times_mole,
            "times_beaver": stats.times_beaver,
            "kills_made": stats.kills_made,
            "votes_received": stats.votes_received,
            "last_played": stats.last_played,
            "created_at": stats.created_at,
            "updated_at": stats.updated_at
        }
    
    def get_top_players(self, limit: int = 10, sort_by: str = "games_won") -> List[Dict[str, Any]]:
        """Получить топ игроков"""
        players = self.stats_service.get_top_players(limit, sort_by)
        return [
            {
                "user_id": player.user_id,
                "username": player.username,
                "total_games": player.total_games,
                "games_won": player.games_won,
                "games_lost": player.games_lost,
                "times_wolf": player.times_wolf,
                "times_fox": player.times_fox,
                "times_hare": player.times_hare,
                "times_mole": player.times_mole,
                "times_beaver": player.times_beaver,
                "kills_made": player.kills_made,
                "votes_received": player.votes_received,
                "last_played": player.last_played
            }
            for player in players
        ]
    
    # === Вспомогательные методы ===
    
    def _update_player_stats_after_game(self, game_id: str, winner_team: str):
        """Обновить статистику игроков после завершения игры"""
        players = self.player_service.get_game_players(game_id)
        
        for player in players:
            won = (player.team == winner_team)
            
            # Подсчитываем убийства и голоса
            kills = len(self.action_service.get_player_actions(
                game_id, action_type="kill"
            ))
            votes_received = len(self.vote_service.get_votes(game_id))
            
            self.stats_service.update_stats_after_game(
                player.user_id, player.role, won, kills, votes_received
            )
    
    # === Настройки ===
    
    def set_setting(self, chat_id: int, thread_id: Optional[int], key: str, value: str) -> bool:
        """Установить настройку"""
        return self.settings_service.set_setting(chat_id, thread_id, key, value)
    
    def get_setting(self, chat_id: int, thread_id: Optional[int], key: str, default: str = None) -> Optional[str]:
        """Получить настройку"""
        return self.settings_service.get_setting(chat_id, thread_id, key, default)
    
    def get_all_settings(self, chat_id: int, thread_id: Optional[int] = None) -> Dict[str, str]:
        """Получить все настройки для чата"""
        return self.settings_service.get_all_settings(chat_id, thread_id)
    
    def delete_setting(self, chat_id: int, thread_id: Optional[int], key: str) -> bool:
        """Удалить настройку"""
        return self.settings_service.delete_setting(chat_id, thread_id, key)
    
    def close(self):
        """Закрыть соединение с базой данных"""
        if self.db_manager:
            self.db_manager.close()
