#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Система предметов Лесного магазина
Обрабатывает логику всех предметов и их эффекты
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from game_logic import Role, Team, GamePhase

# Настройка логирования
logger = logging.getLogger(__name__)

class ItemType(Enum):
    """Типы предметов"""
    BOOST = "boost"           # Усиления (действуют одну игру)
    CONSUMABLE = "consumable" # Расходники (тратятся при использовании)
    PERMANENT = "permanent"   # Постоянные (действуют всю игру)

class ItemEffect:
    """Класс для описания эффекта предмета"""
    
    def __init__(self, item_name: str, item_type: ItemType, description: str):
        self.item_name = item_name
        self.item_type = item_type
        self.description = description
    
    def can_use(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Проверяет, можно ли использовать предмет
        
        Args:
            user_id: ID пользователя
            game_state: Состояние игры
        
        Returns:
            Tuple[bool, str]: (можно_использовать, сообщение)
        """
        return True, "Предмет можно использовать"
    
    def apply_effect(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Применяет эффект предмета
        
        Args:
            user_id: ID пользователя
            game_state: Состояние игры
        
        Returns:
            Tuple[bool, str]: (успешно_применен, сообщение)
        """
        return True, "Эффект применен"

class ActiveRoleBoost(ItemEffect):
    """🎭 Активная роль - повышает шанс выпадения активной роли"""
    
    def __init__(self):
        super().__init__(
            "🎭 Активная роль",
            ItemType.BOOST,
            "Повышает шанс выпадения активной роли (волк, лиса, крот, бобёр) до 99%. Действует одну игру."
        )
    
    def apply_effect(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Устанавливает флаг active_role_boost для пользователя"""
        try:
            from database_psycopg2 import update_item_flags
            
            flags = {"active_role_boost": True}
            success = update_item_flags(user_id, self.item_name, flags)
            
            if success:
                return True, "🎭 Шанс выпадения активной роли повышен до 99%!"
            else:
                return False, "❌ Не удалось активировать усиление роли"
                
        except Exception as e:
            logger.error(f"❌ Ошибка применения {self.item_name}: {e}")
            return False, "❌ Ошибка активации предмета"

class ForestMask(ItemEffect):
    """🌿 Лесная маскировка - скрывает роль от проверки крота"""
    
    def __init__(self):
        super().__init__(
            "🌿 Лесная маскировка",
            ItemType.CONSUMABLE,
            "Один раз скрывает роль игрока от проверки крота. Тратится автоматически при проверке."
        )
    
    def can_use(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Проверяет, есть ли предмет в инвентаре"""
        try:
            from database_psycopg2 import has_item_in_inventory
            
            if has_item_in_inventory(user_id, self.item_name):
                return True, "🌿 Маскировка готова к использованию"
            else:
                return False, "❌ У вас нет лесной маскировки"
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки {self.item_name}: {e}")
            return False, "❌ Ошибка проверки предмета"
    
    def apply_effect(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Активирует маскировку (будет использована при проверке крота)"""
        try:
            from database_psycopg2 import update_item_flags
            
            flags = {"mask_active": True}
            success = update_item_flags(user_id, self.item_name, flags)
            
            if success:
                return True, "🌿 Лесная маскировка активирована! Ваша роль скрыта от проверки крота."
            else:
                return False, "❌ Не удалось активировать маскировку"
                
        except Exception as e:
            logger.error(f"❌ Ошибка применения {self.item_name}: {e}")
            return False, "❌ Ошибка активации предмета"

class BeaverProtection(ItemEffect):
    """🛡️ Защита бобра - спасает от атаки волков"""
    
    def __init__(self):
        super().__init__(
            "🛡️ Защита бобра",
            ItemType.CONSUMABLE,
            "Спасает игрока один раз от атаки волков. Активируется автоматически при атаке."
        )
    
    def can_use(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Проверяет, есть ли предмет в инвентаре"""
        try:
            from database_psycopg2 import has_item_in_inventory
            
            if has_item_in_inventory(user_id, self.item_name):
                return True, "🛡️ Защита бобра готова к использованию"
            else:
                return False, "❌ У вас нет защиты бобра"
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки {self.item_name}: {e}")
            return False, "❌ Ошибка проверки предмета"
    
    def apply_effect(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Активирует защиту (будет использована при атаке волков)"""
        try:
            from database_psycopg2 import update_item_flags
            
            flags = {"protection_active": True}
            success = update_item_flags(user_id, self.item_name, flags)
            
            if success:
                return True, "🛡️ Защита бобра активирована! Вы защищены от следующей атаки волков."
            else:
                return False, "❌ Не удалось активировать защиту"
                
        except Exception as e:
            logger.error(f"❌ Ошибка применения {self.item_name}: {e}")
            return False, "❌ Ошибка активации предмета"

class GoldenNut(ItemEffect):
    """🌰 Золотой орешек - удваивает награду за игру"""
    
    def __init__(self):
        super().__init__(
            "🌰 Золотой орешек",
            ItemType.BOOST,
            "Удваивает заработанные орешки за следующую игру. Действует одну игру."
        )
    
    def apply_effect(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Устанавливает флаг double_reward для пользователя"""
        try:
            from database_psycopg2 import update_item_flags
            
            flags = {"double_reward": True}
            success = update_item_flags(user_id, self.item_name, flags)
            
            if success:
                return True, "🌰 Золотой орешек активирован! Награда за следующую игру будет удвоена."
            else:
                return False, "❌ Не удалось активировать золотой орешек"
                
        except Exception as e:
            logger.error(f"❌ Ошибка применения {self.item_name}: {e}")
            return False, "❌ Ошибка активации предмета"

class NightVision(ItemEffect):
    """🌙 Ночное зрение - показывает действия других в ночи"""
    
    def __init__(self):
        super().__init__(
            "🌙 Ночное зрение",
            ItemType.CONSUMABLE,
            "В ночной фазе игрок видит действия других (кто кого проверял/атаковал). Действует одну игру."
        )
    
    def can_use(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Проверяет, есть ли предмет в инвентаре и ночная ли фаза"""
        try:
            from database_psycopg2 import has_item_in_inventory
            
            if not has_item_in_inventory(user_id, self.item_name):
                return False, "❌ У вас нет ночного зрения"
            
            # Проверяем, что это ночная фаза
            if game_state.get('phase') != GamePhase.NIGHT:
                return False, "❌ Ночное зрение можно использовать только ночью"
            
            return True, "🌙 Ночное зрение готово к использованию"
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки {self.item_name}: {e}")
            return False, "❌ Ошибка проверки предмета"
    
    def apply_effect(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Активирует ночное зрение"""
        try:
            from database_psycopg2 import update_item_flags
            
            flags = {"night_vision_active": True}
            success = update_item_flags(user_id, self.item_name, flags)
            
            if success:
                return True, "🌙 Ночное зрение активировано! Вы видите действия других игроков."
            else:
                return False, "❌ Не удалось активировать ночное зрение"
                
        except Exception as e:
            logger.error(f"❌ Ошибка применения {self.item_name}: {e}")
            return False, "❌ Ошибка активации предмета"

class SharpNose(ItemEffect):
    """🔍 Острый нюх - показывает роли всех игроков"""
    
    def __init__(self):
        super().__init__(
            "🔍 Острый нюх",
            ItemType.BOOST,
            "Показывает роли всех игроков в следующей игре. Действует одну игру."
        )
    
    def apply_effect(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Устанавливает флаг reveal_roles для пользователя"""
        try:
            from database_psycopg2 import update_item_flags
            
            flags = {"reveal_roles": True}
            success = update_item_flags(user_id, self.item_name, flags)
            
            if success:
                return True, "🔍 Острый нюх активирован! В следующей игре вы увидите роли всех игроков."
            else:
                return False, "❌ Не удалось активировать острый нюх"
                
        except Exception as e:
            logger.error(f"❌ Ошибка применения {self.item_name}: {e}")
            return False, "❌ Ошибка активации предмета"

class ForestElixir(ItemEffect):
    """🍄 Лесной эликсир - воскрешает игрока"""
    
    def __init__(self):
        super().__init__(
            "🍄 Лесной эликсир",
            ItemType.CONSUMABLE,
            "Воскрешает игрока один раз, если его убили. Активируется автоматически при смерти."
        )
    
    def can_use(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Проверяет, есть ли предмет в инвентаре и мертв ли игрок"""
        try:
            from database_psycopg2 import has_item_in_inventory
            
            if not has_item_in_inventory(user_id, self.item_name):
                return False, "❌ У вас нет лесного эликсира"
            
            # Проверяем, что игрок мертв
            if game_state.get('player_alive', True):
                return False, "❌ Лесной эликсир можно использовать только после смерти"
            
            return True, "🍄 Лесной эликсир готов к использованию"
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки {self.item_name}: {e}")
            return False, "❌ Ошибка проверки предмета"
    
    def apply_effect(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Воскрешает игрока"""
        try:
            from database_psycopg2 import remove_item_from_inventory
            
            # Удаляем предмет из инвентаря
            success = remove_item_from_inventory(user_id, self.item_name, 1)
            
            if success:
                return True, "🍄 Лесной эликсир использован! Вы воскрешены!"
            else:
                return False, "❌ Не удалось использовать лесной эликсир"
                
        except Exception as e:
            logger.error(f"❌ Ошибка применения {self.item_name}: {e}")
            return False, "❌ Ошибка активации предмета"

class TreeOfLife(ItemEffect):
    """🌲 Древо жизни - дает дополнительную жизнь"""
    
    def __init__(self):
        super().__init__(
            "🌲 Древо жизни",
            ItemType.PERMANENT,
            "Даёт дополнительную жизнь на всю игру (умереть можно только после двух атак). Действует всю игру."
        )
    
    def can_use(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Проверяет, есть ли предмет в инвентаре"""
        try:
            from database_psycopg2 import has_item_in_inventory
            
            if has_item_in_inventory(user_id, self.item_name):
                return True, "🌲 Древо жизни готово к использованию"
            else:
                return False, "❌ У вас нет древа жизни"
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки {self.item_name}: {e}")
            return False, "❌ Ошибка проверки предмета"
    
    def apply_effect(self, user_id: int, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Активирует дополнительную жизнь"""
        try:
            from database_psycopg2 import update_item_flags
            
            flags = {"extra_life_active": True}
            success = update_item_flags(user_id, self.item_name, flags)
            
            if success:
                return True, "🌲 Древо жизни активировано! У вас есть дополнительная жизнь."
            else:
                return False, "❌ Не удалось активировать древо жизни"
                
        except Exception as e:
            logger.error(f"❌ Ошибка применения {self.item_name}: {e}")
            return False, "❌ Ошибка активации предмета"

class ItemSystem:
    """Система управления предметами"""
    
    def __init__(self):
        self.items = {
            "🎭 Активная роль": ActiveRoleBoost(),
            "🌿 Лесная маскировка": ForestMask(),
            "🛡️ Защита бобра": BeaverProtection(),
            "🌰 Золотой орешек": GoldenNut(),
            "🌙 Ночное зрение": NightVision(),
            "🔍 Острый нюх": SharpNose(),
            "🍄 Лесной эликсир": ForestElixir(),
            "🌲 Древо жизни": TreeOfLife()
        }
    
    def get_item_effect(self, item_name: str) -> Optional[ItemEffect]:
        """Получает эффект предмета по названию"""
        return self.items.get(item_name)
    
    def can_use_item(self, user_id: int, item_name: str, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Проверяет, можно ли использовать предмет"""
        item_effect = self.get_item_effect(item_name)
        if not item_effect:
            return False, "❌ Неизвестный предмет"
        
        return item_effect.can_use(user_id, game_state)
    
    def use_item(self, user_id: int, item_name: str, game_state: Dict[str, Any]) -> Tuple[bool, str]:
        """Использует предмет"""
        item_effect = self.get_item_effect(item_name)
        if not item_effect:
            return False, "❌ Неизвестный предмет"
        
        # Проверяем, можно ли использовать
        can_use, check_message = item_effect.can_use(user_id, game_state)
        if not can_use:
            return False, check_message
        
        # Применяем эффект
        success, message = item_effect.apply_effect(user_id, game_state)
        
        # Если предмет расходный, удаляем его из инвентаря
        if success and item_effect.item_type == ItemType.CONSUMABLE:
            try:
                from database_psycopg2 import remove_item_from_inventory
                remove_item_from_inventory(user_id, item_name, 1)
            except Exception as e:
                logger.error(f"❌ Ошибка удаления расходного предмета {item_name}: {e}")
        
        return success, message
    
    def get_item_info(self, item_name: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о предмете"""
        item_effect = self.get_item_effect(item_name)
        if not item_effect:
            return None
        
        return {
            'name': item_effect.item_name,
            'type': item_effect.item_type.value,
            'description': item_effect.description
        }
    
    def get_all_items(self) -> Dict[str, ItemEffect]:
        """Получает все предметы"""
        return self.items.copy()

# Глобальный экземпляр системы предметов
item_system = ItemSystem()
