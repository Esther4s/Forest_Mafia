#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Логика роли Крот (аналог Шерифа) в игре "Лес и Волки"
"""

from typing import Optional
from game_logic import Player, Role


class Mole:
    """
    Класс для обработки логики роли Крот
    Крот может раз в ночь проверить норку другого игрока и узнать его роль
    """
    
    @staticmethod
    def check_player(target: Player, current_round: int) -> str:
        """
        Проверяет игрока и возвращает результат проверки
        
        Args:
            target: Целевой игрок для проверки
            current_round: Текущий раунд игры
            
        Returns:
            str: Сообщение с результатом проверки
        """
        if not target or not target.is_alive:
            return "🦡 Крот заглянул в норку, но она оказалась пустой..."
        
        # Получаем русское название роли
        role_names = {
            Role.WOLF: "Волк",
            Role.FOX: "Лиса", 
            Role.HARE: "Заяц",
            Role.MOLE: "Крот",
            Role.BEAVER: "Бобёр"
        }
        role_name = role_names.get(target.role, "Неизвестно")
        
        # Получаем правильное склонение для родительного падежа
        role_genitive = {
            Role.WOLF: "волка",
            Role.FOX: "лисы", 
            Role.HARE: "зайца",
            Role.MOLE: "крота",
            Role.BEAVER: "бобра"
        }
        role_genitive_name = role_genitive.get(target.role, "неизвестного")
        
        # Проверяем, действовал ли игрок в эту ночь
        last_action_round = getattr(target, "last_action_round", 0)
        is_active_this_night = last_action_round == current_round
        
        # Логика для разных ролей
        if target.role == Role.WOLF:
            if is_active_this_night:
                # Волк вышел на охоту
                return "🦡 Крот заглянул в норку, но она была пуста. Похоже, хозяин отправился на охоту..."
            else:
                # Волк дома
                return "🦡 Крот посмотрел из-под тишка и заметил, что это Волк!"
        
        elif target.role == Role.FOX:
            if is_active_this_night:
                # Лиса воровала
                return f"🦡 Крот заглянул в норку, но она была пуста. Похоже, {role_name} отправилась на дело..."
            else:
                # Лиса дома
                return f"🦡 Крот посмотрел из-под тишка и заметил, что это {role_name}!"
        
        elif target.role == Role.HARE:
            if is_active_this_night:
                # Заяц что-то делал (редко, но возможно)
                return f"🦡 Крот заглянул в норку, но она была пуста. Похоже, {role_name} отправился по делам..."
            else:
                # Заяц дома
                return f"🦡 Крот пришёл к норке {role_genitive_name}, тот ему открыл дверь. Всё спокойно, он мирный."
        
        elif target.role == Role.BEAVER:
            if is_active_this_night:
                # Бобёр помогал
                return f"🦡 Крот заглянул в норку, но она была пуста. Похоже, {role_name} отправился помогать..."
            else:
                # Бобёр дома
                return f"🦡 Крот пришёл к норке {role_genitive_name}, тот ему открыл дверь. Всё спокойно, он мирный."
        
        elif target.role == Role.MOLE:
            if is_active_this_night:
                # Другой крот проверял
                return f"🦡 Крот заглянул в норку, но она была пуста. Похоже, {role_name} отправился на разведку..."
            else:
                # Другой крот дома
                return f"🦡 Крот посмотрел из-под тишка и заметил, что это {role_name}!"
        
        else:
            # Неизвестная роль
            return "🦡 Крот заглянул в норку, но не смог понять, кто здесь живёт..."
    
    @staticmethod
    def get_role_hint(target: Player, current_round: int) -> str:
        """
        Возвращает подсказку о роли игрока для крота
        
        Args:
            target: Целевой игрок
            current_round: Текущий раунд
            
        Returns:
            str: Подсказка о роли
        """
        if not target or not target.is_alive:
            return "Мёртвый игрок"
        
        last_action_round = getattr(target, "last_action_round", 0)
        is_active_this_night = last_action_round == current_round
        
        if target.role == Role.WOLF:
            if is_active_this_night:
                return "Волк (на охоте)"
            else:
                return "Волк (дома)"
        
        elif target.role == Role.FOX:
            if is_active_this_night:
                return "Лиса (ворует)"
            else:
                return "Лиса (дома)"
        
        elif target.role == Role.HARE:
            if is_active_this_night:
                return "Заяц (активен)"
            else:
                return "Заяц (мирный)"
        
        elif target.role == Role.BEAVER:
            if is_active_this_night:
                return "Бобёр (помогает)"
            else:
                return "Бобёр (мирный)"
        
        elif target.role == Role.MOLE:
            if is_active_this_night:
                return "Крот (проверяет)"
            else:
                return "Крот (дома)"
        
        else:
            return "Неизвестная роль"


