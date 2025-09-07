#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from database import (
    Game, Player, GameEvent, PlayerAction, Vote, PlayerStats, BotSettings,
    get_db_session
)

class GameService:
    """Сервис для работы с играми"""
    
    @staticmethod
    def create_game(chat_id: int, thread_id: Optional[int] = None, settings: Dict[str, Any] = None) -> Game:
        """Создать новую игру"""
        session = get_db_session()
        try:
            game = Game(
                chat_id=chat_id,
                thread_id=thread_id,
                settings=settings or {}
            )
            session.add(game)
            session.commit()
            session.refresh(game)
            return game
        finally:
            session.close()
    
    @staticmethod
    def get_active_game(chat_id: int, thread_id: Optional[int] = None) -> Optional[Game]:
        """Получить активную игру в чате"""
        session = get_db_session()
        try:
            query = session.query(Game).filter(
                and_(
                    Game.chat_id == chat_id,
                    Game.thread_id == thread_id,
                    Game.status.in_(['waiting', 'active'])
                )
            )
            return query.first()
        finally:
            session.close()
    
    @staticmethod
    def get_game_by_id(game_id: str) -> Optional[Game]:
        """Получить игру по ID"""
        session = get_db_session()
        try:
            return session.query(Game).filter(Game.id == game_id).first()
        finally:
            session.close()
    
    @staticmethod
    def update_game_status(game_id: str, status: str, phase: str = None) -> bool:
        """Обновить статус игры"""
        session = get_db_session()
        try:
            game = session.query(Game).filter(Game.id == game_id).first()
            if game:
                game.status = status
                if phase:
                    game.phase = phase
                if status == 'active' and not game.started_at:
                    game.started_at = datetime.utcnow()
                elif status == 'finished' and not game.finished_at:
                    game.finished_at = datetime.utcnow()
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    @staticmethod
    def finish_game(game_id: str, winner_team: str) -> bool:
        """Завершить игру"""
        session = get_db_session()
        try:
            game = session.query(Game).filter(Game.id == game_id).first()
            if game:
                game.status = 'finished'
                game.phase = 'finished'
                game.winner_team = winner_team
                game.finished_at = datetime.utcnow()
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    @staticmethod
    def get_all_active_games() -> List[Dict[str, Any]]:
        """Получить все активные игры"""
        session = get_db_session()
        try:
            games = session.query(Game).filter(
                Game.status.in_(['waiting', 'active'])
            ).all()
            
            result = []
            for game in games:
                result.append({
                    'id': game.id,
                    'chat_id': game.chat_id,
                    'thread_id': game.thread_id,
                    'status': game.status,
                    'phase': game.phase,
                    'round_number': game.round_number,
                    'created_at': game.created_at,
                    'started_at': game.started_at,
                    'finished_at': game.finished_at,
                    'winner_team': game.winner_team,
                    'settings': game.settings
                })
            return result
        finally:
            session.close()

class PlayerService:
    """Сервис для работы с игроками"""
    
    @staticmethod
    def add_player_to_game(game_id: str, user_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> Optional[Player]:
        """Добавить игрока в игру"""
        session = get_db_session()
        try:
            # Проверяем, не участвует ли уже игрок в этой игре
            existing_player = session.query(Player).filter(
                and_(
                    Player.game_id == game_id,
                    Player.user_id == user_id
                )
            ).first()
            
            if existing_player:
                return existing_player
            
            player = Player(
                game_id=game_id,
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            session.add(player)
            session.commit()
            session.refresh(player)
            return player
        finally:
            session.close()
    
    @staticmethod
    def remove_player_from_game(game_id: str, user_id: int) -> bool:
        """Удалить игрока из игры"""
        session = get_db_session()
        try:
            player = session.query(Player).filter(
                and_(
                    Player.game_id == game_id,
                    Player.user_id == user_id
                )
            ).first()
            
            if player:
                session.delete(player)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    @staticmethod
    def get_game_players(game_id: str, alive_only: bool = False) -> List[Player]:
        """Получить игроков игры"""
        session = get_db_session()
        try:
            query = session.query(Player).filter(Player.game_id == game_id)
            if alive_only:
                query = query.filter(Player.is_alive == True)
            return query.all()
        finally:
            session.close()
    
    @staticmethod
    def assign_role(player_id: str, role: str, team: str) -> bool:
        """Назначить роль игроку"""
        session = get_db_session()
        try:
            player = session.query(Player).filter(Player.id == player_id).first()
            if player:
                player.role = role
                player.team = team
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    @staticmethod
    def kill_player(player_id: str, reason: str = "killed") -> bool:
        """Убить игрока"""
        session = get_db_session()
        try:
            player = session.query(Player).filter(Player.id == player_id).first()
            if player:
                player.is_alive = False
                player.died_at = datetime.utcnow()
                player.death_reason = reason
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    @staticmethod
    def get_game_players(game_id: str) -> List[Dict[str, Any]]:
        """Получить всех игроков игры"""
        session = get_db_session()
        try:
            players = session.query(Player).filter(Player.game_id == game_id).all()
            
            result = []
            for player in players:
                result.append({
                    'id': player.id,
                    'user_id': player.user_id,
                    'username': player.username,
                    'first_name': player.first_name,
                    'last_name': player.last_name,
                    'role': player.role,
                    'team': player.team,
                    'is_alive': player.is_alive,
                    'created_at': player.created_at,
                    'updated_at': player.updated_at
                })
            return result
        finally:
            session.close()

class GameEventService:
    """Сервис для работы с событиями игры"""
    
    @staticmethod
    def log_event(game_id: str, event_type: str, event_data: Dict[str, Any] = None) -> GameEvent:
        """Записать событие игры"""
        session = get_db_session()
        try:
            event = GameEvent(
                game_id=game_id,
                event_type=event_type,
                event_data=event_data or {}
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return event
        finally:
            session.close()
    
    @staticmethod
    def get_game_events(game_id: str, event_type: str = None) -> List[GameEvent]:
        """Получить события игры"""
        session = get_db_session()
        try:
            query = session.query(GameEvent).filter(GameEvent.game_id == game_id)
            if event_type:
                query = query.filter(GameEvent.event_type == event_type)
            return query.order_by(GameEvent.created_at).all()
        finally:
            session.close()

class PlayerActionService:
    """Сервис для работы с действиями игроков"""
    
    @staticmethod
    def record_action(player_id: str, game_id: str, action_type: str, 
                     target_id: str = None, action_data: Dict[str, Any] = None,
                     round_number: int = 0, phase: str = "night") -> PlayerAction:
        """Записать действие игрока"""
        session = get_db_session()
        try:
            action = PlayerAction(
                player_id=player_id,
                game_id=game_id,
                action_type=action_type,
                target_id=target_id,
                action_data=action_data or {},
                round_number=round_number,
                phase=phase
            )
            session.add(action)
            session.commit()
            session.refresh(action)
            return action
        finally:
            session.close()
    
    @staticmethod
    def get_player_actions(game_id: str, round_number: int = None, 
                          action_type: str = None) -> List[PlayerAction]:
        """Получить действия игроков"""
        session = get_db_session()
        try:
            query = session.query(PlayerAction).filter(PlayerAction.game_id == game_id)
            if round_number is not None:
                query = query.filter(PlayerAction.round_number == round_number)
            if action_type:
                query = query.filter(PlayerAction.action_type == action_type)
            return query.all()
        finally:
            session.close()

class VoteService:
    """Сервис для работы с голосованиями"""
    
    @staticmethod
    def cast_vote(game_id: str, voter_id: str, target_id: str = None,
                 round_number: int = 0, phase: str = "voting") -> Vote:
        """Записать голос"""
        session = get_db_session()
        try:
            # Удаляем предыдущий голос этого игрока в этом раунде
            session.query(Vote).filter(
                and_(
                    Vote.game_id == game_id,
                    Vote.voter_id == voter_id,
                    Vote.round_number == round_number,
                    Vote.phase == phase
                )
            ).delete()
            
            vote = Vote(
                game_id=game_id,
                voter_id=voter_id,
                target_id=target_id,
                round_number=round_number,
                phase=phase
            )
            session.add(vote)
            session.commit()
            session.refresh(vote)
            return vote
        finally:
            session.close()
    
    @staticmethod
    def get_votes(game_id: str, round_number: int = None, phase: str = None) -> List[Vote]:
        """Получить голоса"""
        session = get_db_session()
        try:
            query = session.query(Vote).filter(Vote.game_id == game_id)
            if round_number is not None:
                query = query.filter(Vote.round_number == round_number)
            if phase:
                query = query.filter(Vote.phase == phase)
            return query.all()
        finally:
            session.close()
    
    @staticmethod
    def get_vote_results(game_id: str, round_number: int, phase: str = "voting") -> Dict[str, int]:
        """Получить результаты голосования"""
        session = get_db_session()
        try:
            votes = session.query(Vote).filter(
                and_(
                    Vote.game_id == game_id,
                    Vote.round_number == round_number,
                    Vote.phase == phase
                )
            ).all()
            
            results = {}
            for vote in votes:
                target_id = vote.target_id or "abstain"
                results[target_id] = results.get(target_id, 0) + 1
            
            return results
        finally:
            session.close()

class PlayerStatsService:
    """Сервис для работы со статистикой игроков"""
    
    @staticmethod
    def get_or_create_stats(user_id: int, username: str = None) -> PlayerStats:
        """Получить или создать статистику игрока"""
        session = get_db_session()
        try:
            stats = session.query(PlayerStats).filter(PlayerStats.user_id == user_id).first()
            if not stats:
                stats = PlayerStats(
                    user_id=user_id,
                    username=username
                )
                session.add(stats)
                session.commit()
                session.refresh(stats)
            elif username and stats.username != username:
                stats.username = username
                stats.updated_at = datetime.utcnow()
                session.commit()
            return stats
        finally:
            session.close()
    
    @staticmethod
    def update_stats_after_game(user_id: int, role: str, won: bool, 
                               kills: int = 0, votes_received: int = 0) -> bool:
        """Обновить статистику после игры"""
        session = get_db_session()
        try:
            stats = session.query(PlayerStats).filter(PlayerStats.user_id == user_id).first()
            if stats:
                stats.total_games += 1
                if won:
                    stats.games_won += 1
                else:
                    stats.games_lost += 1
                
                # Обновляем статистику по ролям
                role_field = f"times_{role}"
                if hasattr(stats, role_field):
                    setattr(stats, role_field, getattr(stats, role_field) + 1)
                
                stats.kills_made += kills
                stats.votes_received += votes_received
                stats.last_played = datetime.utcnow()
                stats.updated_at = datetime.utcnow()
                
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    @staticmethod
    def get_top_players(limit: int = 10, sort_by: str = "games_won") -> List[PlayerStats]:
        """Получить топ игроков"""
        session = get_db_session()
        try:
            return session.query(PlayerStats).order_by(
                desc(getattr(PlayerStats, sort_by))
            ).limit(limit).all()
        finally:
            session.close()

class BotSettingsService:
    """Сервис для работы с настройками бота"""
    
    @staticmethod
    def set_setting(chat_id: int, thread_id: Optional[int], key: str, value: str) -> bool:
        """Установить настройку"""
        session = get_db_session()
        try:
            # Ищем существующую настройку
            existing = session.query(BotSettings).filter(
                and_(
                    BotSettings.chat_id == chat_id,
                    BotSettings.thread_id == thread_id,
                    BotSettings.setting_key == key
                )
            ).first()
            
            if existing:
                # Обновляем существующую
                existing.setting_value = value
                existing.updated_at = datetime.utcnow()
            else:
                # Создаем новую
                setting = BotSettings(
                    chat_id=chat_id,
                    thread_id=thread_id,
                    setting_key=key,
                    setting_value=value
                )
                session.add(setting)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()
    
    @staticmethod
    def get_setting(chat_id: int, thread_id: Optional[int], key: str, default: str = None) -> Optional[str]:
        """Получить настройку"""
        session = get_db_session()
        try:
            setting = session.query(BotSettings).filter(
                and_(
                    BotSettings.chat_id == chat_id,
                    BotSettings.thread_id == thread_id,
                    BotSettings.setting_key == key
                )
            ).first()
            
            return setting.setting_value if setting else default
        finally:
            session.close()
    
    @staticmethod
    def get_all_settings(chat_id: int, thread_id: Optional[int] = None) -> Dict[str, str]:
        """Получить все настройки для чата"""
        session = get_db_session()
        try:
            settings = session.query(BotSettings).filter(
                and_(
                    BotSettings.chat_id == chat_id,
                    BotSettings.thread_id == thread_id
                )
            ).all()
            
            return {setting.setting_key: setting.setting_value for setting in settings}
        finally:
            session.close()
    
    @staticmethod
    def delete_setting(chat_id: int, thread_id: Optional[int], key: str) -> bool:
        """Удалить настройку"""
        session = get_db_session()
        try:
            setting = session.query(BotSettings).filter(
                and_(
                    BotSettings.chat_id == chat_id,
                    BotSettings.thread_id == thread_id,
                    BotSettings.setting_key == key
                )
            ).first()
            
            if setting:
                session.delete(setting)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()
