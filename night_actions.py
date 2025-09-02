import random
from typing import Dict, List, Optional
from game_logic import Game, Player, Role, Team

class NightActions:
    def __init__(self, game: Game):
        self.game = game
        self.wolf_targets = {}  # user_id -> target_user_id
        self.fox_targets = {}   # user_id -> target_user_id
        self.beaver_targets = {} # user_id -> target_user_id
        self.mole_targets = {}  # user_id -> target_user_id
    
    def set_wolf_target(self, wolf_id: int, target_id: int) -> bool:
        """Устанавливает цель для волка"""
        wolf = self.game.players.get(wolf_id)
        target = self.game.players.get(target_id)
        
        if not wolf or not target:
            return False
        
        if wolf.role != Role.WOLF or not wolf.is_alive:
            return False
        
        if not target.is_alive:
            return False
        
        # Волки не могут есть друг друга
        if target.role == Role.WOLF:
            return False
        
        self.wolf_targets[wolf_id] = target_id
        return True
    
    def set_fox_target(self, fox_id: int, target_id: int) -> bool:
        """Устанавливает цель для лисы"""
        fox = self.game.players.get(fox_id)
        target = self.game.players.get(target_id)
        
        if not fox or not target:
            return False
        
        if fox.role != Role.FOX or not fox.is_alive:
            return False
        
        if not target.is_alive:
            return False
        
        # Лиса не может воровать у бобра (он защищен)
        if target.role == Role.BEAVER:
            return False
        
        self.fox_targets[fox_id] = target_id
        return True
    
    def set_beaver_target(self, beaver_id: int, target_id: int) -> bool:
        """Устанавливает цель для бобра"""
        beaver = self.game.players.get(beaver_id)
        target = self.game.players.get(target_id)
        
        if not beaver or not target:
            return False
        
        if beaver.role != Role.BEAVER or not beaver.is_alive:
            return False
        
        if not target.is_alive:
            return False
        
        # Бобёр может помогать только тем, у кого украли еду
        if target.is_fox_stolen == 0:
            return False
        
        self.beaver_targets[beaver_id] = target_id
        return True
    
    def set_mole_target(self, mole_id: int, target_id: int) -> bool:
        """Устанавливает цель для крота"""
        mole = self.game.players.get(mole_id)
        target = self.game.players.get(target_id)
        
        if not mole or not target:
            return False
        
        if mole.role != Role.MOLE or not mole.is_alive:
            return False
        
        if not target.is_alive:
            return False
        
        # Крот не может проверять себя
        if mole_id == target_id:
            return False
        
        self.mole_targets[mole_id] = target_id
        return True
    
    def process_all_actions(self) -> Dict[str, List[str]]:
        """Обрабатывает все ночные действия и возвращает результаты"""
        results = {
            "wolves": [],
            "fox": [],
            "beaver": [],
            "mole": [],
            "deaths": []
        }
        
        # Обрабатываем действия по порядку: Волки -> Лиса -> Бобёр -> Крот
        
        # 1. Волки едят
        if self.game.current_round > 1:  # В первую ночь волки не едят
            results["wolves"] = self._process_wolf_actions()
        
        # 2. Лиса ворует
        results["fox"] = self._process_fox_actions()
        
        # 3. Бобёр помогает
        results["beaver"] = self._process_beaver_actions()
        
        # 4. Крот проверяет
        results["mole"] = self._process_mole_actions()
        
        # Проверяем смерти от кражи лисы
        results["deaths"] = self._check_fox_deaths()
        
        return results
    
    def _process_wolf_actions(self) -> List[str]:
        """Обрабатывает действия волков"""
        results = []
        
        if not self.wolf_targets:
            return results
        
        # Подсчитываем голоса за каждую цель
        target_votes = {}
        for target_id in self.wolf_targets.values():
            target_votes[target_id] = target_votes.get(target_id, 0) + 1
        
        # Находим цель с наибольшим количеством голосов
        if target_votes:
            max_votes = max(target_votes.values())
            max_vote_targets = [tid for tid, votes in target_votes.items() if votes == max_votes]
            
            # Если ничья, выбираем случайную цель
            if len(max_vote_targets) > 1:
                target_id = random.choice(max_vote_targets)
            else:
                target_id = max_vote_targets[0]
            
            # Убиваем цель
            target = self.game.players[target_id]
            target.is_alive = False
            
            results.append(f"🐺 Волки съели {target.username}!")
        
        return results
    
    def _process_fox_actions(self) -> List[str]:
        """Обрабатывает действия лисы"""
        results = []
        
        for fox_id, target_id in self.fox_targets.items():
            fox = self.game.players[fox_id]
            target = self.game.players[target_id]
            
            if fox and target and fox.is_alive and target.is_alive:
                # Увеличиваем счетчик краж
                target.is_fox_stolen += 1
                
                if target.is_fox_stolen == 1:
                    results.append(f"🦊 Лиса украла запасы у {target.username}!")
                elif target.is_fox_stolen == 2:
                    results.append(f"🦊 Лиса снова украла запасы у {target.username}! У него не осталось еды на зиму.")
                else:
                    results.append(f"🦊 Лиса украла запасы у {target.username} (уже {target.is_fox_stolen} раз)!")
        
        return results
    
    def _process_beaver_actions(self) -> List[str]:
        """Обрабатывает действия бобра"""
        results = []
        
        for beaver_id, target_id in self.beaver_targets.items():
            beaver = self.game.players[beaver_id]
            target = self.game.players[target_id]
            
            if beaver and target and beaver.is_alive and target.is_alive:
                if target.is_fox_stolen > 0:
                    # Бобёр компенсирует весь ущерб
                    target.is_fox_stolen = 0
                    target.is_beaver_protected = True
                    results.append(f"🦦 Бобёр вернул запасы {target.username}!")
        
        return results
    
    def _process_mole_actions(self) -> List[str]:
        """Обрабатывает действия крота"""
        results = []
        
        for mole_id, target_id in self.mole_targets.items():
            mole = self.game.players[mole_id]
            target = self.game.players[target_id]
            
            if mole and target and mole.is_alive and target.is_alive:
                team_name = "Хищники" if target.team == Team.PREDATORS else "Травоядные"
                results.append(f"🦫 Крот узнал, что {target.username} - {team_name}")
        
        return results
    
    def _check_fox_deaths(self) -> List[str]:
        """Проверяет смерти от кражи лисы"""
        deaths = []
        
        for player in self.game.players.values():
            if player.is_alive and player.is_fox_stolen >= 2 and not player.is_beaver_protected:
                player.is_alive = False
                deaths.append(f"🦊 {player.username} ушел жить в соседний лес из-за кражи запасов!")
        
        return deaths
    
    def get_player_actions(self, player_id: int) -> Dict[str, any]:
        """Возвращает доступные действия для игрока"""
        player = self.game.players.get(player_id)
        if not player or not player.is_alive:
            return {}
        
        actions = {}
        
        if player.role == Role.WOLF:
            # Волк может выбрать цель для еды
            alive_targets = [p for p in self.game.get_alive_players() if p.role != Role.WOLF]
            actions["type"] = "wolf"
            actions["targets"] = alive_targets
            actions["current_target"] = self.wolf_targets.get(player_id)
        
        elif player.role == Role.FOX:
            # Лиса может выбрать цель для кражи
            alive_targets = [p for p in self.game.get_alive_players() if p.role != Role.BEAVER]
            actions["type"] = "fox"
            actions["targets"] = alive_targets
            actions["current_target"] = self.fox_targets.get(player_id)
        
        elif player.role == Role.BEAVER:
            # Бобёр может помочь тем, у кого украли еду
            stolen_targets = [p for p in self.game.get_alive_players() if p.is_fox_stolen > 0]
            actions["type"] = "beaver"
            actions["targets"] = stolen_targets
            actions["current_target"] = self.beaver_targets.get(player_id)
        
        elif player.role == Role.MOLE:
            # Крот может проверить любого живого игрока
            alive_targets = [p for p in self.game.get_alive_players() if p.user_id != player_id]
            actions["type"] = "mole"
            actions["targets"] = alive_targets
            actions["current_target"] = self.mole_targets.get(player_id)
        
        return actions
    
    def clear_actions(self):
        """Очищает все ночные действия"""
        self.wolf_targets.clear()
        self.fox_targets.clear()
        self.beaver_targets.clear()
        self.mole_targets.clear()
