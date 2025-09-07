#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Логика роли Бобёр в игре "Лес и Волки"
"""

from typing import Optional, Tuple
from game_logic import Player, Role


class Beaver:
    """
    Класс для обработки логики роли Бобёр
    Бобёр — защитник. Его задача охранять припасы (свои или чужие).
    """
    
    @staticmethod
    def defend(target: Optional[Player] = None) -> str:
        """
        Бобёр защищает указанного игрока или себя
        
        Args:
            target: Целевой игрок для защиты (None = защита себя)
            
        Returns:
            str: Сообщение с результатом защиты
        """
        if target is None:
            # Бобёр защищает только себя
            return "🦦 Бобёр сторожит свои припасы, и никто не решился сунуться."
        
        if not target or not target.is_alive:
            return f"🦦 Бобёр пришёл к норке, но она была пуста и тиха, как на кладбище."
        
        # Бобёр дежурит у норки указанного игрока
        return f"🦦 Бобёр всю ночь сидел у норки {target.username}, но никто так и не пришёл."
    
    @staticmethod
    def protect_from_fox(target: Player, fox: Player) -> Tuple[str, bool]:
        """
        Бобёр защищает игрока от лисы
        
        Args:
            target: Защищаемый игрок
            fox: Лиса, которая пытается украсть
            
        Returns:
            Tuple[str, bool]: (сообщение, успех защиты)
        """
        if not target or not target.is_alive:
            return f"🦦 Бобёр пришёл к норке, но она была пуста и тиха, как на кладбище.", False
        
        if not fox or not fox.is_alive:
            return f"🦦 Бобёр дежурил у норки {target.username}, но лиса так и не появилась.", True
        
        # Бобёр успешно защищает от лисы
        return f"🦦 Бобёр дежурил у норки {target.username}, и Лиса не смогла ничего украсть.", True
    
    @staticmethod
    def protect_from_wolf(target: Player, wolf: Player) -> Tuple[str, bool]:
        """
        Бобёр защищает игрока от волка
        
        Args:
            target: Защищаемый игрок
            wolf: Волк, который пытается убить
            
        Returns:
            Tuple[str, bool]: (сообщение, успех защиты)
        """
        if not target or not target.is_alive:
            return f"🦦 Бобёр пришёл к норке, но она была пуста и тиха, как на кладбище.", False
        
        if not wolf or not wolf.is_alive:
            return f"🦦 Бобёр дежурил у норки {target.username}, но волк так и не появился.", True
        
        # Бобёр успешно защищает от волка
        return f"🦦 Волк подкрался к {target.username}, но Бобёр встал на защиту. Волку пришлось ретироваться.", True
    
    @staticmethod
    def is_protected_from_fox(target: Player) -> bool:
        """
        Проверяет, защищён ли игрок от лисы
        
        Args:
            target: Игрок для проверки
            
        Returns:
            bool: Защищён ли игрок
        """
        if not target or not target.is_alive:
            return False
        
        # Бобёр всегда защищён от лисы
        if target.role == Role.BEAVER:
            return True
        
        # Проверяем, защищён ли игрок бобром
        return getattr(target, 'is_beaver_protected', False)
    
    @staticmethod
    def is_protected_from_wolf(target: Player) -> bool:
        """
        Проверяет, защищён ли игрок от волка
        
        Args:
            target: Игрок для проверки
            
        Returns:
            bool: Защищён ли игрок
        """
        if not target or not target.is_alive:
            return False
        
        # Проверяем, защищён ли игрок бобром
        return getattr(target, 'is_beaver_protected', False)
    
    @staticmethod
    def set_protection(target: Player, protected: bool = True):
        """
        Устанавливает защиту бобра для игрока
        
        Args:
            target: Игрок
            protected: Защищён ли игрок
        """
        if target:
            target.is_beaver_protected = protected
    
    @staticmethod
    def restore_supplies(target: Player) -> Tuple[str, bool]:
        """
        Бобёр восстанавливает припасы игрока, у которого их украли
        
        Args:
            target: Игрок для восстановления припасов
            
        Returns:
            Tuple[str, bool]: (сообщение, успех восстановления)
        """
        if not target or not target.is_alive:
            return f"🦦 Бобёр пришёл к норке, но она была пуста и тиха, как на кладбище.", False
        
        # Проверяем, есть ли украденные припасы для восстановления
        if getattr(target, 'stolen_supplies', 0) <= 0:
            return f"🦦 Бобёр заглянул к норке {target.username}, но восстанавливать было нечего.", False
        
        # Восстанавливаем припасы (но не больше максимального количества)
        stolen_count = target.stolen_supplies
        restored_count = min(stolen_count, target.max_supplies - target.supplies)
        
        if restored_count > 0:
            target.supplies += restored_count
            target.stolen_supplies -= restored_count
            
            if restored_count == stolen_count:
                return f"🦦 Бобёр вернул все украденные припасы {target.username}! Теперь у него {target.supplies} припасов.", True
            else:
                return f"🦦 Бобёр вернул {restored_count} припасов {target.username}! Теперь у него {target.supplies} припасов.", True
        else:
            return f"🦦 Бобёр заглянул к норке {target.username}, но у него уже полные запасы.", False
    
    @staticmethod
    def can_restore_supplies(target: Player) -> bool:
        """
        Проверяет, может ли бобёр восстановить припасы игрока
        
        Args:
            target: Игрок
            
        Returns:
            bool: Может ли восстановить припасы
        """
        if not target or not target.is_alive:
            return False
        
        # Проверяем, есть ли украденные припасы и место для восстановления
        stolen_supplies = getattr(target, 'stolen_supplies', 0)
        return stolen_supplies > 0 and target.supplies < target.max_supplies
    
    @staticmethod
    def get_restoration_info(target: Player) -> str:
        """
        Возвращает информацию о возможности восстановления припасов
        
        Args:
            target: Игрок
            
        Returns:
            str: Информация о восстановлении
        """
        if not target or not target.is_alive:
            return "Мёртв"
        
        stolen_supplies = getattr(target, 'stolen_supplies', 0)
        if stolen_supplies <= 0:
            return "Нет украденных припасов"
        
        if target.supplies >= target.max_supplies:
            return f"{stolen_supplies} украденных припасов (полные запасы)"
        
        can_restore = min(stolen_supplies, target.max_supplies - target.supplies)
        return f"{stolen_supplies} украденных припасов (можно восстановить {can_restore})"
    
    @staticmethod
    def get_protection_status(target: Player) -> str:
        """
        Возвращает статус защиты игрока
        
        Args:
            target: Игрок
            
        Returns:
            str: Статус защиты
        """
        if not target or not target.is_alive:
            return "Мёртв"
        
        if target.role == Role.BEAVER:
            return "Бобёр (самозащита)"
        
        if getattr(target, 'is_beaver_protected', False):
            return "Защищён бобром"
        
        return "Не защищён"
