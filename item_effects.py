"""
Система игровых эффектов предметов из магазина
Каждый предмет имеет уникальный эффект, который влияет на игровой процесс
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class EffectType(Enum):
    """Типы эффектов предметов"""
    CONSUMABLE = "consumable"  # Одноразовый
    BOOST = "boost"  # Усиление на игру
    PERMANENT = "permanent"  # Постоянный эффект

@dataclass
class PlayerState:
    """Состояние игрока в игре"""
    user_id: int
    role: str
    is_alive: bool
    lives: int = 1
    balance: int = 0
    buffs: List[str] = None
    debuffs: List[str] = None
    game_id: str = None
    chat_id: int = None
    
    def __post_init__(self):
        if self.buffs is None:
            self.buffs = []
        if self.debuffs is None:
            self.debuffs = []

@dataclass
class GameState:
    """Состояние игры"""
    game_id: str
    chat_id: int
    phase: str
    players: Dict[int, PlayerState]
    round_number: int = 1

class ItemEffect:
    """Базовый класс для эффектов предметов"""
    
    def __init__(self, item_name: str, effect_type: EffectType, description: str):
        self.item_name = item_name
        self.effect_type = effect_type
        self.description = description
    
    def can_use(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str]:
        """Проверяет, можно ли использовать предмет"""
        return True, ""
    
    def apply_effect(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str, PlayerState]:
        """Применяет эффект предмета"""
        return True, "Эффект применен", player_state

class ActiveRoleEffect(ItemEffect):
    """Активная роль - 99% шанс выпадения активной роли"""
    
    def __init__(self):
        super().__init__(
            item_name="🎭 Активная роль",
            effect_type=EffectType.BOOST,
            description="Повышает шанс выпадения активной роли (волк, лиса, крот, бобёр) до 99%. Действует одну игру."
        )
    
    def can_use(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str]:
        """Можно использовать только в фазе ожидания"""
        if game_state.phase != "waiting":
            return False, "Можно использовать только перед началом игры"
        return True, ""
    
    def apply_effect(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str, PlayerState]:
        """Добавляет бафф активной роли"""
        if "active_role_boost" not in player_state.buffs:
            player_state.buffs.append("active_role_boost")
            return True, "🎭 Теперь у вас 99% шанс получить активную роль!", player_state
        return False, "Эффект уже активен", player_state

class ForestCamouflageEffect(ItemEffect):
    """Лесная маскировка - скрывает роль от проверки крота"""
    
    def __init__(self):
        super().__init__(
            item_name="🌿 Лесная маскировка",
            effect_type=EffectType.CONSUMABLE,
            description="Один раз скрывает роль игрока от проверки крота. Тратится автоматически при проверке."
        )
    
    def can_use(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str]:
        """Можно использовать всегда"""
        return True, ""
    
    def apply_effect(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str, PlayerState]:
        """Добавляет защиту от проверки крота"""
        if "forest_camouflage" not in player_state.buffs:
            player_state.buffs.append("forest_camouflage")
            return True, "🌿 Лесная маскировка активирована! Крот не сможет проверить вашу роль.", player_state
        return False, "Эффект уже активен", player_state

class BeaverShieldEffect(ItemEffect):
    """Защита бобра - блокирует первую атаку волков"""
    
    def __init__(self):
        super().__init__(
            item_name="🛡️ Защита бобра",
            effect_type=EffectType.CONSUMABLE,
            description="Спасает игрока один раз от атаки волков. Активируется автоматически при атаке."
        )
    
    def can_use(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str]:
        """Можно использовать всегда"""
        return True, ""
    
    def apply_effect(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str, PlayerState]:
        """Добавляет защиту от атаки волков"""
        if "beaver_shield" not in player_state.buffs:
            player_state.buffs.append("beaver_shield")
            return True, "🛡️ Защита бобра активирована! Первая атака волков будет заблокирована.", player_state
        return False, "Эффект уже активен", player_state

class GoldenNutEffect(ItemEffect):
    """Золотой орешек - удваивает награду за следующую игру"""
    
    def __init__(self):
        super().__init__(
            item_name="🌰 Золотой орешек",
            effect_type=EffectType.BOOST,
            description="Удваивает заработанные орешки за следующую игру. Действует одну игру."
        )
    
    def can_use(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str]:
        """Можно использовать всегда"""
        return True, ""
    
    def apply_effect(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str, PlayerState]:
        """Добавляет бафф удвоения награды"""
        if "golden_nut_boost" not in player_state.buffs:
            player_state.buffs.append("golden_nut_boost")
            return True, "🌰 Золотой орешек активирован! Следующая игра принесет двойную награду.", player_state
        return False, "Эффект уже активен", player_state

class NightVisionEffect(ItemEffect):
    """Ночное зрение - видит действия других игроков в ночной фазе"""
    
    def __init__(self):
        super().__init__(
            item_name="🌙 Ночное зрение",
            effect_type=EffectType.CONSUMABLE,
            description="В ночной фазе игрок видит действия других (кто кого проверял/атаковал). Действует одну игру."
        )
    
    def can_use(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str]:
        """Можно использовать всегда"""
        return True, ""
    
    def apply_effect(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str, PlayerState]:
        """Добавляет ночное зрение"""
        if "night_vision" not in player_state.buffs:
            player_state.buffs.append("night_vision")
            return True, "🌙 Ночное зрение активировано! Вы будете видеть действия других игроков в ночной фазе.", player_state
        return False, "Эффект уже активен", player_state

class SharpNoseEffect(ItemEffect):
    """Острый нюх - показывает роли всех игроков в следующей игре"""
    
    def __init__(self):
        super().__init__(
            item_name="🔍 Острый нюх",
            effect_type=EffectType.BOOST,
            description="Показывает роли всех игроков в следующей игре. Действует одну игру."
        )
    
    def can_use(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str]:
        """Можно использовать только в фазе ожидания"""
        if game_state.phase != "waiting":
            return False, "Можно использовать только перед началом игры"
        return True, ""
    
    def apply_effect(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str, PlayerState]:
        """Добавляет острый нюх"""
        if "sharp_nose" not in player_state.buffs:
            player_state.buffs.append("sharp_nose")
            return True, "🔍 Острый нюх активирован! В следующей игре вы увидите роли всех игроков.", player_state
        return False, "Эффект уже активен", player_state

class ForestElixirEffect(ItemEffect):
    """Лесной эликсир - воскрешает игрока после смерти"""
    
    def __init__(self):
        super().__init__(
            item_name="🍄 Лесной эликсир",
            effect_type=EffectType.CONSUMABLE,
            description="Воскрешает игрока один раз, если его убили. Активируется автоматически при смерти."
        )
    
    def can_use(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str]:
        """Можно использовать всегда"""
        return True, ""
    
    def apply_effect(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str, PlayerState]:
        """Добавляет эффект воскрешения"""
        if "forest_elixir" not in player_state.buffs:
            player_state.buffs.append("forest_elixir")
            return True, "🍄 Лесной эликсир активирован! Если вас убьют, вы воскреснете с 1 жизнью.", player_state
        return False, "Эффект уже активен", player_state

class TreeOfLifeEffect(ItemEffect):
    """Древо жизни - дает дополнительную жизнь на всю игру"""
    
    def __init__(self):
        super().__init__(
            item_name="🌲 Древо жизни",
            effect_type=EffectType.PERMANENT,
            description="Даёт дополнительную жизнь на всю игру (умереть можно только после двух атак). Действует всю игру."
        )
    
    def can_use(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str]:
        """Можно использовать только в фазе ожидания"""
        if game_state.phase != "waiting":
            return False, "Можно использовать только перед началом игры"
        return True, ""
    
    def apply_effect(self, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str, PlayerState]:
        """Добавляет дополнительную жизнь"""
        if "tree_of_life" not in player_state.buffs:
            player_state.buffs.append("tree_of_life")
            player_state.lives += 1
            return True, f"🌲 Древо жизни активировано! Теперь у вас {player_state.lives} жизней.", player_state
        return False, "Эффект уже активен", player_state

class ItemEffectManager:
    """Менеджер эффектов предметов"""
    
    def __init__(self):
        self.effects = {
            "🎭 Активная роль": ActiveRoleEffect(),
            "🌿 Лесная маскировка": ForestCamouflageEffect(),
            "🛡️ Защита бобра": BeaverShieldEffect(),
            "🌰 Золотой орешек": GoldenNutEffect(),
            "🌙 Ночное зрение": NightVisionEffect(),
            "🔍 Острый нюх": SharpNoseEffect(),
            "🍄 Лесной эликсир": ForestElixirEffect(),
            "🌲 Древо жизни": TreeOfLifeEffect(),
        }
    
    def get_effect(self, item_name: str) -> Optional[ItemEffect]:
        """Получает эффект по названию предмета"""
        return self.effects.get(item_name)
    
    def can_use_item(self, item_name: str, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str]:
        """Проверяет, можно ли использовать предмет"""
        effect = self.get_effect(item_name)
        if not effect:
            return False, f"Предмет '{item_name}' не найден"
        
        return effect.can_use(player_state, game_state)
    
    def apply_item_effect(self, item_name: str, player_state: PlayerState, game_state: GameState) -> Tuple[bool, str, PlayerState]:
        """Применяет эффект предмета"""
        effect = self.get_effect(item_name)
        if not effect:
            return False, f"Предмет '{item_name}' не найден", player_state
        
        return effect.apply_effect(player_state, game_state)
    
    def get_item_info(self, item_name: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о предмете"""
        effect = self.get_effect(item_name)
        if not effect:
            return None
        
        return {
            "item_name": effect.item_name,
            "effect_type": effect.effect_type.value,
            "description": effect.description,
            "is_consumable": effect.effect_type == EffectType.CONSUMABLE
        }

# Глобальный экземпляр менеджера эффектов
effect_manager = ItemEffectManager()

def get_item_info(item_name: str) -> Optional[Dict[str, Any]]:
    """Получает информацию о предмете"""
    return effect_manager.get_item_info(item_name)

def can_use_item(user_id: int, item_name: str) -> Tuple[bool, str]:
    """Проверяет, можно ли использовать предмет"""
    # Здесь нужно получить состояние игрока и игры из базы данных
    # Пока возвращаем True для тестирования
    return True, ""

def apply_item_effect(user_id: int, item_name: str) -> Tuple[bool, str]:
    """Применяет эффект предмета"""
    # Здесь нужно получить состояние игрока и игры из базы данных
    # Пока возвращаем успех для тестирования
    return True, f"Эффект предмета '{item_name}' применен"