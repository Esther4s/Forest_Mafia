#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с эффектами предметов в игре "Лесная мафия"
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from database_psycopg2 import (
    get_user_inventory, 
    update_user_inventory, 
    add_active_effect, 
    get_active_effects,
    mark_effect_as_used,
    remove_effect
)

logger = logging.getLogger(__name__)

# Словарь предметов и их эффектов
ITEM_EFFECTS = {
    "🎭 Активная роль": {
        "effect_type": "role_boost",
        "description": "Гарантирует 99% шанс получить активную роль в следующей игре",
        "usage_phase": "before_game",
        "is_consumable": True,
        "effect_data": {"role_boost_chance": 0.99}
    },
    "🌿 Лесная маскировка": {
        "effect_type": "mole_protection",
        "description": "Скрывает твою роль от проверки крота один раз",
        "usage_phase": "any",
        "is_consumable": True,
        "effect_data": {"protection_count": 1}
    },
    "🛡️ Защита бобра": {
        "effect_type": "wolf_protection",
        "description": "Спасает тебя один раз от убийства волками",
        "usage_phase": "any",
        "is_consumable": True,
        "effect_data": {"shield": True}
    },
    "🌰 Золотой орешек": {
        "effect_type": "reward_double",
        "description": "Удваивает количество орешков, заработанных за следующую игру",
        "usage_phase": "before_game",
        "is_consumable": True,
        "effect_data": {"multiplier": 2.0}
    },
    "🌙 Ночное зрение": {
        "effect_type": "night_vision",
        "description": "Позволяет видеть все действия ночью",
        "usage_phase": "before_game",
        "is_consumable": True,
        "effect_data": {"night_log": True}
    },
    "🔍 Острый нюх": {
        "effect_type": "role_reveal",
        "description": "Показывает роли всех игроков в следующей игре",
        "usage_phase": "before_game",
        "is_consumable": True,
        "effect_data": {"reveal_all_roles": True}
    },
    "🍄 Лесной эликсир": {
        "effect_type": "resurrection",
        "description": "Воскрешает игрока один раз, если его убили",
        "usage_phase": "before_game",
        "is_consumable": True,
        "effect_data": {"resurrection_count": 1}
    },
    "🌲 Древо жизни": {
        "effect_type": "extra_life",
        "description": "Даёт дополнительную жизнь на всю игру",
        "usage_phase": "before_game",
        "is_consumable": False,
        "effect_data": {"extra_lives": 1}
    }
}


def get_item_info(item_name: str) -> Optional[Dict]:
    """
    Получает информацию о предмете
    
    Args:
        item_name: Название предмета
    
    Returns:
        Dict: Информация о предмете или None
    """
    return ITEM_EFFECTS.get(item_name)


def can_use_item(user_id: int, item_name: str, game_phase: str = None) -> Tuple[bool, str]:
    """
    Проверяет, можно ли использовать предмет
    
    Args:
        user_id: ID пользователя
        item_name: Название предмета
        game_phase: Текущая фаза игры
    
    Returns:
        Tuple[bool, str]: (можно_использовать, сообщение_об_ошибке)
    """
    # Проверяем, есть ли предмет в инвентаре
    inventory = get_user_inventory(user_id)
    if not inventory or item_name not in inventory:
        return False, "У тебя нет этого предмета!"
    
    # Получаем информацию о предмете
    item_info = get_item_info(item_name)
    if not item_info:
        return False, "Неизвестный предмет!"
    
    # Проверяем фазу использования
    if item_info["usage_phase"] == "before_game" and game_phase and game_phase != "waiting":
        return False, "Этот предмет можно использовать только до начала игры!"
    
    return True, ""


def apply_item_effect(user_id: int, item_name: str, game_id: str = None, chat_id: int = None) -> Tuple[bool, str]:
    """
    Применяет эффект предмета
    
    Args:
        user_id: ID пользователя
        item_name: Название предмета
        game_id: ID игры (опционально)
        chat_id: ID чата (опционально)
    
    Returns:
        Tuple[bool, str]: (успех, сообщение)
    """
    try:
        # Проверяем возможность использования
        can_use, error_msg = can_use_item(user_id, item_name)
        if not can_use:
            return False, error_msg
        
        # Получаем информацию о предмете
        item_info = get_item_info(item_name)
        
        # Добавляем активный эффект
        success = add_active_effect(
            user_id=user_id,
            item_name=item_name,
            effect_type=item_info["effect_type"],
            effect_data=item_info["effect_data"],
            game_id=game_id,
            chat_id=chat_id
        )
        
        if not success:
            return False, "Ошибка активации эффекта!"
        
        # Если предмет одноразовый, убираем его из инвентаря
        if item_info["is_consumable"]:
            current_count = get_user_inventory(user_id).get(item_name, 0)
            if current_count > 1:
                update_user_inventory(user_id, item_name, current_count - 1)
            else:
                # Удаляем предмет полностью
                update_user_inventory(user_id, item_name, 0)
        
        return True, f"Ты активировал {item_name}!\n\n{item_info['description']}"
        
    except Exception as e:
        logger.error(f"❌ Ошибка применения эффекта предмета: {e}")
        return False, "Произошла ошибка при активации предмета!"


def get_user_active_effects(user_id: int, game_id: str = None, chat_id: int = None) -> List[Dict]:
    """
    Получает активные эффекты пользователя
    
    Args:
        user_id: ID пользователя
        game_id: ID игры (опционально)
        chat_id: ID чата (опционально)
    
    Returns:
        List[Dict]: Список активных эффектов
    """
    return get_active_effects(user_id, game_id, chat_id)


def check_role_boost_effect(user_id: int) -> float:
    """
    Проверяет эффект усиления роли
    
    Args:
        user_id: ID пользователя
    
    Returns:
        float: Коэффициент усиления (1.0 = без усиления)
    """
    effects = get_user_active_effects(user_id)
    for effect in effects:
        if effect["effect_type"] == "role_boost":
            return effect["effect_data"].get("role_boost_chance", 1.0)
    return 1.0


def check_mole_protection_effect(user_id: int) -> bool:
    """
    Проверяет защиту от крота
    
    Args:
        user_id: ID пользователя
    
    Returns:
        bool: True если защищен
    """
    effects = get_user_active_effects(user_id)
    for effect in effects:
        if effect["effect_type"] == "mole_protection":
            # Используем защиту и удаляем эффект
            mark_effect_as_used(effect["id"])
            return True
    return False


def check_wolf_protection_effect(user_id: int) -> bool:
    """
    Проверяет защиту от волков
    
    Args:
        user_id: ID пользователя
    
    Returns:
        bool: True если защищен
    """
    effects = get_user_active_effects(user_id)
    for effect in effects:
        if effect["effect_type"] == "wolf_protection":
            # Используем защиту и удаляем эффект
            mark_effect_as_used(effect["id"])
            return True
    return False


def check_reward_multiplier_effect(user_id: int) -> float:
    """
    Проверяет эффект удвоения награды
    
    Args:
        user_id: ID пользователя
    
    Returns:
        float: Множитель награды (1.0 = без усиления)
    """
    effects = get_user_active_effects(user_id)
    for effect in effects:
        if effect["effect_type"] == "reward_double":
            return effect["effect_data"].get("multiplier", 1.0)
    return 1.0


def check_night_vision_effect(user_id: int) -> bool:
    """
    Проверяет эффект ночного зрения
    
    Args:
        user_id: ID пользователя
    
    Returns:
        bool: True если есть ночное зрение
    """
    effects = get_user_active_effects(user_id)
    for effect in effects:
        if effect["effect_type"] == "night_vision":
            return True
    return False


def check_role_reveal_effect(user_id: int) -> bool:
    """
    Проверяет эффект раскрытия ролей
    
    Args:
        user_id: ID пользователя
    
    Returns:
        bool: True если есть эффект раскрытия
    """
    effects = get_user_active_effects(user_id)
    for effect in effects:
        if effect["effect_type"] == "role_reveal":
            return True
    return False


def check_resurrection_effect(user_id: int) -> bool:
    """
    Проверяет эффект воскрешения
    
    Args:
        user_id: ID пользователя
    
    Returns:
        bool: True если есть эффект воскрешения
    """
    effects = get_user_active_effects(user_id)
    for effect in effects:
        if effect["effect_type"] == "resurrection":
            # Используем воскрешение и удаляем эффект
            mark_effect_as_used(effect["id"])
            return True
    return False


def check_extra_lives_effect(user_id: int) -> int:
    """
    Проверяет эффект дополнительных жизней
    
    Args:
        user_id: ID пользователя
    
    Returns:
        int: Количество дополнительных жизней
    """
    effects = get_user_active_effects(user_id)
    total_extra_lives = 0
    for effect in effects:
        if effect["effect_type"] == "extra_life":
            total_extra_lives += effect["effect_data"].get("extra_lives", 0)
    return total_extra_lives


def cleanup_game_effects(game_id: str) -> int:
    """
    Очищает эффекты после завершения игры
    
    Args:
        game_id: ID игры
    
    Returns:
        int: Количество удаленных эффектов
    """
    try:
        from database_psycopg2 import get_connection
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM active_effects 
                    WHERE game_id = %s
                """, (game_id,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"✅ Удалено {deleted_count} эффектов игры {game_id}")
                
                return deleted_count
                
    except Exception as e:
        logger.error(f"❌ Ошибка очистки эффектов игры: {e}")
        return 0
