#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для перевода ролей на русский язык
"""

from game_logic import Role

def get_role_name_russian(role: Role) -> str:
    """Возвращает русское название роли"""
    role_names = {
        Role.WOLF: "Волк",
        Role.FOX: "Лиса", 
        Role.HARE: "Заяц",
        Role.MOLE: "Крот",
        Role.BEAVER: "Бобёр"
    }
    return role_names.get(role, "Неизвестно")
