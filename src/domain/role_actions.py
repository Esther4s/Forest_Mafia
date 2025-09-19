#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Действия ролей
Содержит логику для каждой роли в игре
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .entities import Player, Game
from .value_objects import UserId, Role, Team


@dataclass
class ActionResult:
    """Результат действия роли"""
    success: bool
    message: str
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


class RoleAction(ABC):
    """Базовый класс для действий ролей"""
    
    def __init__(self, player: Player, game: Game):
        self.player = player
        self.game = game
    
    @abstractmethod
    def can_perform_action(self) -> bool:
        """Проверяет, может ли роль выполнить действие"""
        pass
    
    @abstractmethod
    def perform_action(self, target_id: Optional[UserId] = None) -> ActionResult:
        """Выполняет действие роли"""
        pass
    
    @abstractmethod
    def get_available_targets(self) -> List[Player]:
        """Возвращает список доступных целей"""
        pass


class WolfAction(RoleAction):
    """Действие волка - охота"""
    
    def can_perform_action(self) -> bool:
        """Волк может охотиться, если он жив"""
        return self.player.is_alive and self.player.role == Role.WOLF
    
    def perform_action(self, target_id: Optional[UserId] = None) -> ActionResult:
        """Выполняет охоту волка"""
        if not self.can_perform_action():
            return ActionResult(False, "Волк не может охотиться")
        
        if not target_id:
            return ActionResult(False, "Не выбрана цель для охоты")
        
        target = self.game.players.get(target_id.value)
        if not target or not target.is_alive:
            return ActionResult(False, "Цель недоступна")
        
        # Проверяем защиту бобра
        if target.is_beaver_protected:
            return ActionResult(True, "Охота заблокирована защитой бобра", {
                "target_id": target_id.value,
                "blocked": True
            })
        
        # Убиваем цель
        target.die("wolf_hunt")
        self.game.game_stats.record_kill(target.team)
        
        return ActionResult(True, "Охота успешна", {
            "target_id": target_id.value,
            "killed": True
        })
    
    def get_available_targets(self) -> List[Player]:
        """Волк может охотиться на всех живых игроков кроме других волков"""
        return [
            player for player in self.game.get_alive_players()
            if player.role != Role.WOLF
        ]


class FoxAction(RoleAction):
    """Действие лисы - кража припасов"""
    
    def can_perform_action(self) -> bool:
        """Лиса может воровать, если она жива"""
        return self.player.is_alive and self.player.role == Role.FOX
    
    def perform_action(self, target_id: Optional[UserId] = None) -> ActionResult:
        """Выполняет кражу лисы"""
        if not self.can_perform_action():
            return ActionResult(False, "Лиса не может воровать")
        
        if not target_id:
            return ActionResult(False, "Не выбрана цель для кражи")
        
        target = self.game.players.get(target_id.value)
        if not target or not target.is_alive:
            return ActionResult(False, "Цель недоступна")
        
        if not target.can_be_stolen_from:
            return ActionResult(False, "У цели нет припасов для кражи")
        
        # Крадем припас
        stolen = target.steal_supplies()
        if stolen:
            self.game.game_stats.record_fox_theft()
            return ActionResult(True, "Кража успешна", {
                "target_id": target_id.value,
                "stolen": True
            })
        
        return ActionResult(False, "Не удалось украсть припасы")
    
    def get_available_targets(self) -> List[Player]:
        """Лиса может воровать у всех живых игроков с припасами"""
        return [
            player for player in self.game.get_alive_players()
            if player.can_be_stolen_from
        ]


class MoleAction(RoleAction):
    """Действие крота - проверка роли"""
    
    def can_perform_action(self) -> bool:
        """Крот может проверять, если он жив"""
        return self.player.is_alive and self.player.role == Role.MOLE
    
    def perform_action(self, target_id: Optional[UserId] = None) -> ActionResult:
        """Выполняет проверку крота"""
        if not self.can_perform_action():
            return ActionResult(False, "Крот не может проверять")
        
        if not target_id:
            return ActionResult(False, "Не выбрана цель для проверки")
        
        target = self.game.players.get(target_id.value)
        if not target or not target.is_alive:
            return ActionResult(False, "Цель недоступна")
        
        # Проверяем роль цели
        team_name = "Хищники" if target.team == Team.PREDATORS else "Травоядные"
        
        return ActionResult(True, f"Проверка завершена", {
            "target_id": target_id.value,
            "target_team": team_name,
            "target_role": target.role.value
        })
    
    def get_available_targets(self) -> List[Player]:
        """Крот может проверять всех живых игроков кроме себя"""
        return [
            player for player in self.game.get_alive_players()
            if player.user_id != self.player.user_id
        ]


class BeaverAction(RoleAction):
    """Действие бобра - защита и восстановление"""
    
    def can_perform_action(self) -> bool:
        """Бобр может защищать, если он жив"""
        return self.player.is_alive and self.player.role == Role.BEAVER
    
    def perform_action(self, target_id: Optional[UserId] = None) -> ActionResult:
        """Выполняет защиту бобра"""
        if not self.can_perform_action():
            return ActionResult(False, "Бобр не может защищать")
        
        if not target_id:
            return ActionResult(False, "Не выбрана цель для защиты")
        
        target = self.game.players.get(target_id.value)
        if not target or not target.is_alive:
            return ActionResult(False, "Цель недоступна")
        
        # Защищаем цель
        target.is_beaver_protected = True
        self.game.game_stats.record_beaver_protection()
        
        # Восстанавливаем припасы, если они критичны
        restored = 0
        if target.supplies.is_critical:
            restored = target.add_supplies(1)
        
        return ActionResult(True, "Защита применена", {
            "target_id": target_id.value,
            "protected": True,
            "restored_supplies": restored
        })
    
    def get_available_targets(self) -> List[Player]:
        """Бобр может защищать всех живых игроков"""
        return self.game.get_alive_players()


class HareAction(RoleAction):
    """Действие зайца - сон (никаких ночных действий)"""
    
    def can_perform_action(self) -> bool:
        """Зайцы не имеют ночных действий"""
        return False
    
    def perform_action(self, target_id: Optional[UserId] = None) -> ActionResult:
        """Зайцы спят всю ночь"""
        return ActionResult(False, "Зайцы спят всю ночь")
    
    def get_available_targets(self) -> List[Player]:
        """Зайцы не имеют целей"""
        return []


class RoleActionFactory:
    """Фабрика для создания действий ролей"""
    
    @staticmethod
    def create_action(player: Player, game: Game) -> RoleAction:
        """Создает действие для роли игрока"""
        if player.role == Role.WOLF:
            return WolfAction(player, game)
        elif player.role == Role.FOX:
            return FoxAction(player, game)
        elif player.role == Role.MOLE:
            return MoleAction(player, game)
        elif player.role == Role.BEAVER:
            return BeaverAction(player, game)
        elif player.role == Role.HARE:
            return HareAction(player, game)
        else:
            raise ValueError(f"Неизвестная роль: {player.role}")


class NightActionsProcessor:
    """Обработчик ночных действий"""
    
    def __init__(self, game: Game):
        self.game = game
        self.actions: Dict[int, RoleAction] = {}
        self._initialize_actions()
    
    def _initialize_actions(self) -> None:
        """Инициализирует действия для всех игроков"""
        for player in self.game.get_alive_players():
            if player.role != Role.HARE:  # Зайцы не имеют ночных действий
                self.actions[player.user_id.value] = RoleActionFactory.create_action(player, self.game)
    
    def set_action(self, user_id: UserId, target_id: Optional[UserId] = None) -> ActionResult:
        """Устанавливает действие игрока"""
        action = self.actions.get(user_id.value)
        if not action:
            return ActionResult(False, "Игрок не может выполнять ночные действия")
        
        return action.perform_action(target_id)
    
    def process_all_actions(self) -> List[ActionResult]:
        """Обрабатывает все ночные действия"""
        results = []
        
        # Обрабатываем действия в порядке: Волки -> Лиса -> Бобёр -> Крот
        action_order = [Role.WOLF, Role.FOX, Role.BEAVER, Role.MOLE]
        
        for role in action_order:
            for user_id, action in self.actions.items():
                if action.player.role == role and user_id in self.game.night_actions:
                    action_data = self.game.night_actions[user_id]
                    target_id = UserId(action_data.get('target')) if action_data.get('target') else None
                    result = action.perform_action(target_id)
                    results.append(result)
        
        return results
    
    def get_available_targets(self, user_id: UserId) -> List[Player]:
        """Возвращает доступные цели для игрока"""
        action = self.actions.get(user_id.value)
        if not action:
            return []
        return action.get_available_targets()
