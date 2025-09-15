#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Логика роли Лиса в игре "Лес и Волки"
"""

from typing import Optional, Tuple
from game_logic import Player, Role
from beaver_logic import Beaver


class Fox:
    """
    Класс для обработки логики роли Лиса
    Лиса ворует припасы у других животных. Если припасы украдены дважды, игрок лишается еды и выбывает из игры.
    """
    
    @staticmethod
    def steal(target: Player, beaver_protection: bool = False) -> Tuple[str, bool, bool]:
        """
        Лиса ворует припасы у целевого игрока
        
        Args:
            target: Целевой игрок для воровства
            beaver_protection: Защищён ли игрок бобром
            
        Returns:
            Tuple[str, bool, bool]: (сообщение, успех кражи, смерть жертвы)
        """
        if not target or not target.is_alive:
            return "🦊 Лиса пришла к норке, но там было пусто и тихо, как на кладбище.", False, False
        
        # Бобёр имеет иммунитет к воровству
        if target.role == Role.BEAVER:
            return f"🦊 Лиса сунулась к норке {target.username}, но наткнулась на Бобра — хранителя запасов. Пришлось ретироваться.", False, False
        
        # Если игрок защищён бобром
        if beaver_protection or Beaver.is_protected_from_fox(target):
            return f"🦦 Бобёр дежурил у норки {target.username}, и Лиса не смогла ничего украсть.", False, False
        
        # Если у игрока нет припасов
        if target.supplies <= 0:
            return f"🦊 Лиса заглянула к норке {target.username}, но припасов там и след простыл.", False, False
        
        # Лиса крадёт припас
        target.supplies -= 1
        target.stolen_supplies += 1  # Отслеживаем украденные припасы
        target.is_fox_stolen += 1
        
        # Проверяем, остались ли припасы
        if target.supplies > 0:
            # У игрока ещё есть припасы
            return f"🦊 Лиса подкралась к норке {target.username}, стащила припасы и улизнула в темноту.", True, False
        else:
            # У игрока закончились припасы - он умирает от голода
            target.is_alive = False
            return f"🦊 Лиса утащила последние припасы у {target.username}. Бедняга не выжил без еды.", True, True
    
    @staticmethod
    def can_steal_from(target: Player) -> bool:
        """
        Проверяет, может ли лиса воровать у данного игрока
        
        Args:
            target: Целевой игрок
            
        Returns:
            bool: Может ли лиса воровать
        """
        if not target or not target.is_alive:
            return False
        
        # Бобёр защищён от воровства
        if target.role == Role.BEAVER:
            return False
        
        # У мёртвого игрока нечего воровать
        if target.supplies <= 0:
            return False
        
        return True
    
    @staticmethod
    def get_steal_info(target: Player) -> str:
        """
        Возвращает информацию о возможности воровства у игрока
        
        Args:
            target: Целевой игрок
            
        Returns:
            str: Информация о возможности воровства
        """
        if not target or not target.is_alive:
            return "Мёртвый игрок"
        
        if target.role == Role.BEAVER:
            return "Бобёр (защищён)"
        
        if target.supplies <= 0:
            return "Без припасов"
        
        if target.supplies == 1:
            return f"1 припас (смерть при краже)"
        
        return f"{target.supplies} припасов"
    
    @staticmethod
    def get_supplies_status(target: Player) -> str:
        """
        Возвращает статус припасов игрока
        
        Args:
            target: Игрок
            
        Returns:
            str: Статус припасов
        """
        if not target or not target.is_alive:
            return "Мёртв"
        
        if target.supplies <= 0:
            return "Без припасов"
        elif target.supplies == 1:
            return "1 припас (критично)"
        else:
            return f"{target.supplies} припасов"
