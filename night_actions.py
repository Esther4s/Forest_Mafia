import random
import logging
from typing import Dict, List, Optional
from game_logic import Game, Player, Role, Team
from mole_logic import Mole
from fox_logic import Fox
from beaver_logic import Beaver

logger = logging.getLogger(__name__)

class NightActions:
    def __init__(self, game: Game):
        self.game = game
        self.wolf_targets = {}  # user_id -> target_user_id
        self.fox_targets = {}   # user_id -> target_user_id
        self.beaver_targets = {} # user_id -> target_user_id
        self.mole_targets = {}  # user_id -> target_user_id
        self.skipped_actions = set()  # user_id игроков, которые пропустили ход
    
    def get_display_name(self, user_id: int, username: str = None, first_name: str = None) -> str:
        """Получает отображаемое имя пользователя (приоритет: никнейм > username > first_name)"""
        try:
            from database_psycopg2 import get_user_nickname
            nickname = get_user_nickname(user_id)
            if nickname:
                return nickname
            elif username and not username.isdigit():
                return f"@{username}"
            elif first_name:
                return first_name
            else:
                return f"ID:{user_id}"
        except Exception as e:
            if username and not username.isdigit():
                return f"@{username}"
            elif first_name:
                return first_name
            else:
                return f"ID:{user_id}"
    
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
        
        # Волки могут есть лису (согласно новым правилам)
        # if target.role == Role.FOX:
        #     return False
        
        self.wolf_targets[wolf_id] = target_id
        return True
    
    def set_fox_target(self, fox_id: int, target_id: int) -> bool:
        """Устанавливает цель для лисы согласно правилам Лесной Возни"""
        fox = self.game.players.get(fox_id)
        target = self.game.players.get(target_id)
        
        if not fox or not target:
            return False
        
        if fox.role != Role.FOX or not fox.is_alive:
            return False
        
        if not target.is_alive:
            return False
        
        # Лиса не может воровать у бобра (он защищен от лисы)
        if target.role == Role.BEAVER:
            return False
        
        # Лиса не может воровать у волков (союзники)
        if target.role == Role.WOLF:
            return False
        
        # Лиса не может воровать у лисы
        if target.role == Role.FOX:
            return False
        
        self.fox_targets[fox_id] = target_id
        return True
    
    def set_beaver_target(self, beaver_id: int, target_id: int) -> bool:
        """Устанавливает цель для бобра согласно правилам Лесной Возни"""
        beaver = self.game.players.get(beaver_id)
        target = self.game.players.get(target_id)
        
        if not beaver or not target:
            return False
        
        if beaver.role != Role.BEAVER or not beaver.is_alive:
            return False
        
        if not target.is_alive:
            return False
        
        # Бобёр может помогать только тем, у кого украли еду
        if getattr(target, 'stolen_supplies', 0) == 0:
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
    
    def skip_action(self, player_id: int) -> bool:
        """Пропускает ночное действие для игрока"""
        player = self.game.players.get(player_id)
        if not player or not player.is_alive:
            return False
        
        # Добавляем в список пропустивших
        self.skipped_actions.add(player_id)
        
        # Удаляем из всех списков целей (если был)
        self.wolf_targets.pop(player_id, None)
        self.fox_targets.pop(player_id, None)
        self.beaver_targets.pop(player_id, None)
        self.mole_targets.pop(player_id, None)
        
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
            logger.warning("⚠️ У волков нет выбранных целей для атаки")
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
            
            # Проверяем защиту от волков
            target = self.game.players[target_id]
            
            # Проверяем эффект защиты от волков
            from item_effects import check_wolf_protection_effect
            is_protected = check_wolf_protection_effect(target_id)
            
            if is_protected:
                # Цель защищена, не убиваем
                results.append(f"🛡️ {self.get_display_name(target_id, target.username, target.first_name)} был защищен от атаки волков!")
            else:
                # Проверяем эффект воскрешения перед убийством
                from item_effects import check_resurrection_effect
                has_resurrection = check_resurrection_effect(target_id)
                
                if has_resurrection:
                    # Игрок воскрешается, не убиваем
                    results.append(f"🍄 {self.get_display_name(target_id, target.username, target.first_name)} был воскрешен эликсиром!")
                else:
                    # Проверяем дополнительные жизни
                    if target.use_extra_life():
                        # Игрок использует дополнительную жизнь
                        results.append(f"🌲 {self.get_display_name(target_id, target.username, target.first_name)} использовал дополнительную жизнь!")
                    else:
                        # Убиваем цель
                        target.is_alive = False
                        
                        # Обновляем статистику
                        self.game.game_stats.predator_kills += 1
            
            # Сбрасываем счетчик выживания для убитого игрока
            target.consecutive_nights_survived = 0
            
            # Получаем русское название роли
            from role_translator import get_role_name_russian
            role_name = get_role_name_russian(target.role)
            results.append(f"🐺 Волки съели {target.username} ({role_name})!")
            
            # Сохраняем информацию об убитом игроке для отправки ЛС
            self.game.last_wolf_victim = {
                'user_id': target.user_id,
                'username': target.username,
                'role': target.role,
                'role_name': role_name
            }
        
        return results
    
    def _process_fox_actions(self) -> List[str]:
        """Обрабатывает действия лисы согласно правилам Лесной Возни"""
        results = []
        
        for fox_id, target_id in self.fox_targets.items():
            fox = self.game.players[fox_id]
            target = self.game.players[target_id]
            
            if fox and target and fox.is_alive:
                # Обновляем время последнего действия лисы
                fox.last_action_round = self.game.current_round
                
                # Проверяем, защищён ли игрок бобром
                beaver_protection = Beaver.is_protected_from_fox(target)
                
                # Используем новую логику воровства лисы
                message, success, death = Fox.steal(target, beaver_protection)
                results.append(message)
                
                if success:
                    self.game.game_stats.fox_thefts += 1
                
                if death:
                    # Обновляем статистику смертей
                    if target.team == Team.HERBIVORES:
                        self.game.game_stats.herbivore_survivals += 1
                    self.game.game_stats.predator_kills += 1
        
        return results
    
    def _process_beaver_actions(self) -> List[str]:
        """Обрабатывает действия бобра согласно правилам Лесной Возни"""
        results = []
        
        for beaver_id, target_id in self.beaver_targets.items():
            beaver = self.game.players[beaver_id]
            target = self.game.players[target_id]
            
            if beaver and beaver.is_alive:
                # Обновляем время последнего действия бобра
                beaver.last_action_round = self.game.current_round
                
                if target and target.is_alive:
                    # Бобёр защищает указанного игрока
                    Beaver.set_protection(target, True)
                    self.game.game_stats.beaver_protections += 1
                    
                    # Проверяем, может ли бобёр восстановить припасы
                    if Beaver.can_restore_supplies(target):
                        restore_message, restore_success = Beaver.restore_supplies(target)
                        if restore_success:
                            results.append(restore_message)
                        else:
                            # Если не может восстановить, просто защищает
                            message = Beaver.defend(target)
                            results.append(message)
                    else:
                        # Если нечего восстанавливать, просто защищает
                        message = Beaver.defend(target)
                        results.append(message)
                else:
                    # Бобёр защищает только себя
                    message = Beaver.defend(None)
                    results.append(message)
        
        return results
    
    def _process_mole_actions(self) -> List[str]:
        """Обрабатывает действия крота согласно правилам Лесной Возни"""
        results = []
        
        for mole_id, target_id in self.mole_targets.items():
            mole = self.game.players[mole_id]
            target = self.game.players[target_id]
            
            if mole and target and mole.is_alive:
                # Обновляем время последнего действия крота
                mole.last_action_round = self.game.current_round

                # Проверяем защиту от проверки крота
                from item_effects import check_mole_protection_effect
                is_protected = check_mole_protection_effect(target_id)
                
                if is_protected:
                    # Цель защищена от проверки крота
                    check_result = f"🌿 {self.get_display_name(target_id, target.username, target.first_name)} скрыт от проверки крота!"
                    results.append(check_result)
                else:
                    # Используем новую логику проверки крота
                    check_result = Mole.check_player(target, self.game.current_round)
                    results.append(check_result)
                
                # Сохраняем информацию о проверке крота для отправки ЛС только если крот жив
                if mole.is_alive:
                    self.game.last_mole_check = {
                        'mole_id': mole_id,
                        'mole_username': mole.username,
                        'target_id': target_id,
                        'target_username': target.username,
                        'target_role': target.role,
                        'check_result': check_result
                    }
                    logger.info(f"✅ Сохранена информация о проверке крота {mole_id} (жив)")
                else:
                    logger.warning(f"⚠️ Крот {mole_id} мертв, не сохраняем информацию о проверке")
        
        return results
    
    def _check_fox_deaths(self) -> List[str]:
        """Проверяет смерти от кражи лисы согласно правилам Лесной Возни"""
        deaths = []
        
        for player in self.game.players.values():
            if player.is_alive and player.is_fox_stolen >= 2 and not player.is_beaver_protected:
                # Проверяем эффект воскрешения перед смертью
                from item_effects import check_resurrection_effect
                has_resurrection = check_resurrection_effect(player.user_id)
                
                display_name = self.get_display_name(player.user_id, player.username, None)
                
                if has_resurrection:
                    # Игрок воскрешается, не убиваем
                    deaths.append(f"🍄 {display_name} был воскрешен эликсиром!")
                else:
                    # Проверяем дополнительные жизни
                    if player.use_extra_life():
                        # Игрок использует дополнительную жизнь
                        deaths.append(f"🌲 {display_name} использовал дополнительную жизнь!")
                    else:
                        player.is_alive = False
                        
                        # Сбрасываем счетчик выживания
                        player.consecutive_nights_survived = 0
                        
                        deaths.append(f"🦊 {display_name} ушел жить в соседний лес из-за кражи запасов!")
        
        return deaths
    
    def get_player_actions(self, player_id: int) -> Dict[str, any]:
        """Возвращает доступные действия для игрока"""
        player = self.game.players.get(player_id)
        if not player or not player.is_alive:
            return {}
        
        actions = {}
        
        if player.role == Role.WOLF:
            # Волк может выбрать цель для еды
            alive_targets = [p for p in self.game.get_alive_players() 
                           if p.role not in [Role.WOLF, Role.FOX]]
            actions["type"] = "wolf"
            actions["targets"] = alive_targets
            actions["current_target"] = self.wolf_targets.get(player_id)
            actions["description"] = "Выберите жертву для охоты"
        
        elif player.role == Role.FOX:
            # Лиса может выбрать цель для кражи (кроме бобра, волков и лис)
            alive_targets = [p for p in self.game.get_alive_players() 
                           if p.role not in [Role.BEAVER, Role.WOLF, Role.FOX]]
            actions["type"] = "fox"
            actions["targets"] = alive_targets
            actions["current_target"] = self.fox_targets.get(player_id)
            actions["description"] = "Выберите жертву для кражи запасов (бобёр защищен)"
        
        elif player.role == Role.BEAVER:
            # Бобёр может помочь всем, у кого украли еду (не знает команды)
            stolen_targets = [p for p in self.game.get_alive_players() 
                            if p.is_fox_stolen > 0]
            actions["type"] = "beaver"
            actions["targets"] = stolen_targets
            actions["current_target"] = self.beaver_targets.get(player_id)
            actions["description"] = "Выберите кого защитить от лисы"
        
        elif player.role == Role.MOLE:
            # Крот может проверить любого живого игрока
            alive_targets = [p for p in self.game.get_alive_players() if p.user_id != player_id]
            actions["type"] = "mole"
            actions["targets"] = alive_targets
            actions["current_target"] = self.mole_targets.get(player_id)
            actions["description"] = "Выберите кого проверить"
        
        elif player.role == Role.HARE:
            # Заяц не имеет ночных действий
            actions["type"] = "hare"
            actions["description"] = "Заяц спит и набирается сил"
        
        return actions
    
    def clear_actions(self):
        """Очищает все ночные действия"""
        self.wolf_targets.clear()
        self.fox_targets.clear()
        self.beaver_targets.clear()
        self.mole_targets.clear()
        self.skipped_actions.clear()
    
    def are_all_actions_completed(self) -> bool:
        """Проверяет, все ли игроки выполнили ночные действия"""
        alive_players = [p for p in self.game.players.values() if p.is_alive]
        
        for player in alive_players:
            if player.role == Role.WOLF:
                # Волк должен выбрать цель или пропустить
                if player.user_id not in self.wolf_targets and player.user_id not in self.skipped_actions:
                    return False
            elif player.role == Role.FOX:
                # Лиса должна выбрать цель или пропустить
                if player.user_id not in self.fox_targets and player.user_id not in self.skipped_actions:
                    return False
            elif player.role == Role.BEAVER:
                # Бобер должен выбрать цель или пропустить
                if player.user_id not in self.beaver_targets and player.user_id not in self.skipped_actions:
                    return False
            elif player.role == Role.MOLE:
                # Крот должен выбрать цель или пропустить
                if player.user_id not in self.mole_targets and player.user_id not in self.skipped_actions:
                    return False
            elif player.role == Role.HARE:
                # Зайцы автоматически пропускают ход (не требуют действий)
                pass
        
        return True
    
    def get_action_summary(self) -> str:
        """Возвращает краткое описание всех ночных действий"""
        summary = []
        
        if self.wolf_targets:
            wolf_count = len(self.wolf_targets)
            summary.append(f"🐺 {wolf_count} волк(ов) выбрали цели")
        
        if self.fox_targets:
            fox_count = len(self.fox_targets)
            summary.append(f"🦊 {fox_count} лиса(ы) готовятся к краже")
        
        if self.beaver_targets:
            beaver_count = len(self.beaver_targets)
            summary.append(f"🦦 {beaver_count} бобёр(ов) готовятся помочь")
        
        if self.mole_targets:
            mole_count = len(self.mole_targets)
            summary.append(f"🦫 {mole_count} крот(ов) роют норки")
        
        if not summary:
            summary.append("🌙 Все спят спокойно")
        
        return " | ".join(summary)
