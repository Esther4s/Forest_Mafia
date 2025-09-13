#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Система наград для Лес и волки Bot
Механика выдачи наград и их корректная запись в БД
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from database_balance_manager import balance_manager
from database_psycopg2 import execute_query, fetch_one, fetch_query

logger = logging.getLogger(__name__)


class RewardType(Enum):
    """Типы наград"""
    GAME_WIN = "game_win"                    # Победа в игре
    GAME_PARTICIPATION = "game_participation" # Участие в игре
    ROLE_SPECIFIC = "role_specific"          # Награда за роль
    ACHIEVEMENT = "achievement"              # Достижение
    DAILY_BONUS = "daily_bonus"              # Ежедневный бонус
    SPECIAL_EVENT = "special_event"          # Специальное событие


class RewardReason(Enum):
    """Причины наград"""
    # Победы
    PREDATOR_WIN = "predator_win"            # Победа хищников
    HERBIVORE_WIN = "herbivore_win"          # Победа травоядных
    
    # Участие
    GAME_PARTICIPATION = "game_participation" # Участие в игре
    
    # Роли
    WOLF_WIN = "wolf_win"                    # Победа волка
    FOX_WIN = "fox_win"                      # Победа лисы
    HARE_WIN = "hare_win"                    # Победа зайца
    MOLE_WIN = "mole_win"                    # Победа крота
    BEAVER_WIN = "beaver_win"                # Победа бобра
    
    # Действия
    SUCCESSFUL_KILL = "successful_kill"      # Успешное убийство
    SUCCESSFUL_THEFT = "successful_theft"    # Успешная кража
    SUCCESSFUL_INVESTIGATION = "successful_investigation"  # Успешная проверка
    SUCCESSFUL_PROTECTION = "successful_protection"        # Успешная защита
    
    # Достижения
    FIRST_GAME = "first_game"                # Первая игра
    SURVIVAL_STREAK = "survival_streak"      # Серия выживаний
    KILL_STREAK = "kill_streak"              # Серия убийств
    LONG_GAME = "long_game"                  # Длинная игра
    
    # Специальные
    ADMIN_BONUS = "admin_bonus"              # Бонус администратора
    EVENT_BONUS = "event_bonus"              # Бонус события


class Reward:
    """Класс награды"""
    
    def __init__(self, reward_type: RewardType, reason: RewardReason, amount: int, 
                 description: str, metadata: Optional[Dict] = None):
        self.reward_type = reward_type
        self.reason = reason
        self.amount = amount
        self.description = description
        self.metadata = metadata or {}
        self.created_at = datetime.now()


class RewardsSystem:
    """Система наград"""
    
    def __init__(self):
        self.logger = logger
        self.reward_configs = self._load_reward_configs()
    
    def _load_reward_configs(self) -> Dict[RewardReason, Dict[str, Any]]:
        """Загружает конфигурацию наград"""
        return {
            # Победы
            RewardReason.PREDATOR_WIN: {"amount": 50, "description": "Победа хищников"},
            RewardReason.HERBIVORE_WIN: {"amount": 50, "description": "Победа травоядных"},
            
            # Участие
            RewardReason.GAME_PARTICIPATION: {"amount": 10, "description": "Участие в игре"},
            
            # Роли
            RewardReason.WOLF_WIN: {"amount": 30, "description": "Победа в роли волка"},
            RewardReason.FOX_WIN: {"amount": 30, "description": "Победа в роли лисы"},
            RewardReason.HARE_WIN: {"amount": 20, "description": "Победа в роли зайца"},
            RewardReason.MOLE_WIN: {"amount": 25, "description": "Победа в роли крота"},
            RewardReason.BEAVER_WIN: {"amount": 25, "description": "Победа в роли бобра"},
            
            # Действия
            RewardReason.SUCCESSFUL_KILL: {"amount": 10, "description": "Успешное убийство"},
            RewardReason.SUCCESSFUL_THEFT: {"amount": 8, "description": "Успешная кража"},
            RewardReason.SUCCESSFUL_INVESTIGATION: {"amount": 5, "description": "Успешная проверка"},
            RewardReason.SUCCESSFUL_PROTECTION: {"amount": 5, "description": "Успешная защита"},
            
            # Достижения
            RewardReason.FIRST_GAME: {"amount": 15, "description": "Первая игра"},
            RewardReason.SURVIVAL_STREAK: {"amount": 20, "description": "Серия выживаний"},
            RewardReason.KILL_STREAK: {"amount": 25, "description": "Серия убийств"},
            RewardReason.LONG_GAME: {"amount": 15, "description": "Длинная игра"},
            
            # Специальные
            RewardReason.ADMIN_BONUS: {"amount": 100, "description": "Бонус администратора"},
            RewardReason.EVENT_BONUS: {"amount": 50, "description": "Бонус события"},
        }
    
    def give_reward(self, user_id: int, reason: RewardReason, 
                   custom_amount: Optional[int] = None, 
                   custom_description: Optional[str] = None,
                   metadata: Optional[Dict] = None) -> bool:
        """
        Выдает награду пользователю
        
        Args:
            user_id: ID пользователя
            reason: Причина награды
            custom_amount: Пользовательская сумма (если не указана, используется из конфига)
            custom_description: Пользовательское описание
            metadata: Дополнительные данные
            
        Returns:
            bool: True если награда выдана успешно
        """
        try:
            # Получаем конфигурацию награды
            config = self.reward_configs.get(reason, {})
            
            # Определяем сумму и описание
            amount = custom_amount if custom_amount is not None else config.get("amount", 0)
            description = custom_description or config.get("description", f"Награда: {reason.value}")
            
            if amount <= 0:
                self.logger.warning(f"⚠️ Попытка выдать награду с нулевой или отрицательной суммой: {amount}")
                return False
            
            # Создаем награду
            reward = Reward(
                reward_type=self._get_reward_type(reason),
                reason=reason,
                amount=amount,
                description=description,
                metadata=metadata or {}
            )
            
            # Выдаем награду
            success = self._process_reward(user_id, reward)
            
            if success:
                self.logger.info(f"✅ Награда выдана пользователю {user_id}: {amount} орешков за {description}")
                return True
            else:
                self.logger.error(f"❌ Не удалось выдать награду пользователю {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка выдачи награды пользователю {user_id}: {e}")
            return False
    
    def _get_reward_type(self, reason: RewardReason) -> RewardType:
        """Определяет тип награды по причине"""
        if reason in [RewardReason.PREDATOR_WIN, RewardReason.HERBIVORE_WIN]:
            return RewardType.GAME_WIN
        elif reason in [RewardReason.WOLF_WIN, RewardReason.FOX_WIN, RewardReason.HARE_WIN, 
                       RewardReason.MOLE_WIN, RewardReason.BEAVER_WIN]:
            return RewardType.ROLE_SPECIFIC
        elif reason in [RewardReason.SUCCESSFUL_KILL, RewardReason.SUCCESSFUL_THEFT, 
                       RewardReason.SUCCESSFUL_INVESTIGATION, RewardReason.SUCCESSFUL_PROTECTION]:
            return RewardType.ACHIEVEMENT
        elif reason in [RewardReason.FIRST_GAME, RewardReason.SURVIVAL_STREAK, 
                       RewardReason.KILL_STREAK, RewardReason.LONG_GAME]:
            return RewardType.ACHIEVEMENT
        else:
            return RewardType.SPECIAL_EVENT
    
    def _process_reward(self, user_id: int, reward: Reward) -> bool:
        """
        Обрабатывает выдачу награды
        
        Args:
            user_id: ID пользователя
            reward: Объект награды
            
        Returns:
            bool: True если награда обработана успешно
        """
        try:
            # Добавляем орешки к балансу
            balance_success = balance_manager.add_to_balance(user_id, reward.amount)
            
            if not balance_success:
                return False
            
            # Записываем награду в БД
            db_success = self._save_reward_to_db(user_id, reward)
            
            if not db_success:
                # Откатываем изменения баланса
                balance_manager.subtract_from_balance(user_id, reward.amount)
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки награды: {e}")
            return False
    
    def _save_reward_to_db(self, user_id: int, reward: Reward) -> bool:
        """
        Сохраняет награду в базу данных
        
        Args:
            user_id: ID пользователя
            reward: Объект награды
            
        Returns:
            bool: True если награда сохранена успешно
        """
        try:
            query = """
                INSERT INTO user_rewards 
                (user_id, reward_type, reason, amount, description, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            import json
            metadata_json = json.dumps(reward.metadata) if reward.metadata else None
            
            affected = execute_query(query, (
                user_id,
                reward.reward_type.value,
                reward.reason.value,
                reward.amount,
                reward.description,
                metadata_json,
                reward.created_at
            ))
            
            return affected > 0
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения награды в БД: {e}")
            return False
    
    def get_user_rewards(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получает награды пользователя
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей
            
        Returns:
            List[Dict]: Список наград
        """
        try:
            query = """
                SELECT * FROM user_rewards 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """
            
            return fetch_query(query, (user_id, limit))
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения наград пользователя {user_id}: {e}")
            return []
    
    def get_user_total_rewards(self, user_id: int) -> Dict[str, Any]:
        """
        Получает общую статистику наград пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict: Статистика наград
        """
        try:
            query = """
                SELECT 
                    COUNT(*) as total_rewards,
                    SUM(amount) as total_amount,
                    AVG(amount) as average_amount,
                    MAX(amount) as max_reward,
                    MIN(amount) as min_reward
                FROM user_rewards 
                WHERE user_id = %s
            """
            
            result = fetch_one(query, (user_id,))
            
            if result:
                return {
                    "total_rewards": result.get("total_rewards", 0),
                    "total_amount": float(result.get("total_amount", 0)),
                    "average_amount": float(result.get("average_amount", 0)),
                    "max_reward": result.get("max_reward", 0),
                    "min_reward": result.get("min_reward", 0)
                }
            else:
                return {
                    "total_rewards": 0,
                    "total_amount": 0.0,
                    "average_amount": 0.0,
                    "max_reward": 0,
                    "min_reward": 0
                }
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения статистики наград пользователя {user_id}: {e}")
            return {
                "total_rewards": 0,
                "total_amount": 0.0,
                "average_amount": 0.0,
                "max_reward": 0,
                "min_reward": 0
            }
    
    def process_game_rewards(self, game_result: Dict[str, Any]) -> Dict[int, List[Reward]]:
        """
        Обрабатывает награды за игру
        
        Args:
            game_result: Результат игры
            
        Returns:
            Dict: Награды по пользователям
        """
        try:
            rewards = {}
            
            # Получаем данные игры
            winner_team = game_result.get("winner_team")
            players = game_result.get("players", [])
            game_stats = game_result.get("stats", {})
            
            for player in players:
                user_id = player.get("user_id")
                if not user_id:
                    continue
                
                player_rewards = []
                
                # Награда за участие
                participation_reward = self.give_reward(
                    user_id, 
                    RewardReason.GAME_PARTICIPATION,
                    custom_amount=10,
                    custom_description="Участие в игре"
                )
                
                if participation_reward:
                    player_rewards.append(Reward(
                        RewardType.GAME_PARTICIPATION,
                        RewardReason.GAME_PARTICIPATION,
                        10,
                        "Участие в игре"
                    ))
                
                # Награда за победу
                if player.get("team") == winner_team:
                    win_reward = self.give_reward(
                        user_id,
                        RewardReason.PREDATOR_WIN if winner_team == "predators" else RewardReason.HERBIVORE_WIN
                    )
                    
                    if win_reward:
                        player_rewards.append(Reward(
                            RewardType.GAME_WIN,
                            RewardReason.PREDATOR_WIN if winner_team == "predators" else RewardReason.HERBIVORE_WIN,
                            50,
                            "Победа в игре"
                        ))
                
                # Награда за роль
                role = player.get("role")
                if role:
                    role_reward_reason = self._get_role_reward_reason(role)
                    if role_reward_reason:
                        role_reward = self.give_reward(user_id, role_reward_reason)
                        if role_reward:
                            player_rewards.append(Reward(
                                RewardType.ROLE_SPECIFIC,
                                role_reward_reason,
                                self.reward_configs[role_reward_reason]["amount"],
                                self.reward_configs[role_reward_reason]["description"]
                            ))
                
                rewards[user_id] = player_rewards
            
            return rewards
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки наград за игру: {e}")
            return {}
    
    def _get_role_reward_reason(self, role: str) -> Optional[RewardReason]:
        """Получает причину награды для роли"""
        role_rewards = {
            "wolf": RewardReason.WOLF_WIN,
            "fox": RewardReason.FOX_WIN,
            "hare": RewardReason.HARE_WIN,
            "mole": RewardReason.MOLE_WIN,
            "beaver": RewardReason.BEAVER_WIN
        }
        return role_rewards.get(role)


# Глобальный экземпляр системы наград
rewards_system = RewardsSystem()
