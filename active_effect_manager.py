#!/usr/bin/env python3
"""
Менеджер активных эффектов - центральный класс для управления эффектами предметов
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from database_psycopg2 import (
    add_enhanced_active_effect,
    get_enhanced_active_effects,
    trigger_effect,
    mark_effect_as_used,
    expire_effect,
    cleanup_expired_effects,
    get_effect_statistics
)

logger = logging.getLogger(__name__)

class ActiveEffectManager:
    """Менеджер активных эффектов предметов"""
    
    def __init__(self):
        self.effect_types = {
            'consumable': 'Расходный предмет',
            'boost': 'Усиление',
            'permanent': 'Постоянный эффект',
            'temporary': 'Временный эффект'
        }
        
        self.trigger_types = {
            'item_use': 'Использование предмета',
            'game_start': 'Начало игры',
            'game_end': 'Конец игры',
            'night_phase': 'Ночная фаза',
            'day_phase': 'Дневная фаза',
            'round_start': 'Начало раунда',
            'round_end': 'Конец раунда',
            'player_death': 'Смерть игрока',
            'manual': 'Ручное управление'
        }
    
    def add_item_effect(
        self,
        user_id: int,
        item_name: str,
        effect_type: str,
        effect_data: dict = None,
        game_id: str = None,
        chat_id: int = None,
        duration_rounds: int = 1,
        remaining_uses: int = 1,
        trigger_conditions: dict = None
    ) -> bool:
        """
        Добавляет эффект предмета
        
        Args:
            user_id: ID пользователя
            item_name: Название предмета
            effect_type: Тип эффекта
            effect_data: Данные эффекта
            game_id: ID игры
            chat_id: ID чата
            duration_rounds: Длительность в раундах
            remaining_uses: Количество использований
            trigger_conditions: Условия срабатывания
        
        Returns:
            bool: Успешность добавления
        """
        try:
            # Определяем время истечения
            expires_at = None
            if duration_rounds > 0:
                # Предполагаем, что один раунд = 1 час
                expires_at = (datetime.now() + timedelta(hours=duration_rounds)).isoformat()
            
            success = add_enhanced_active_effect(
                user_id=user_id,
                item_name=item_name,
                effect_type=effect_type,
                effect_data=effect_data,
                game_id=game_id,
                chat_id=chat_id,
                expires_at=expires_at,
                duration_rounds=duration_rounds,
                remaining_uses=remaining_uses,
                triggered_by='item_use',
                trigger_conditions=trigger_conditions,
                auto_remove=True
            )
            
            if success:
                logger.info(f"✅ Эффект {item_name} добавлен для пользователя {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления эффекта {item_name}: {e}")
            return False
    
    def get_user_effects(
        self,
        user_id: int,
        game_id: str = None,
        chat_id: int = None,
        status: str = 'active'
    ) -> List[Dict]:
        """
        Получает эффекты пользователя
        
        Args:
            user_id: ID пользователя
            game_id: ID игры
            chat_id: ID чата
            status: Статус эффектов
        
        Returns:
            List[Dict]: Список эффектов
        """
        try:
            return get_enhanced_active_effects(
                user_id=user_id,
                game_id=game_id,
                chat_id=chat_id,
                status=status
            )
        except Exception as e:
            logger.error(f"❌ Ошибка получения эффектов пользователя {user_id}: {e}")
            return []
    
    def trigger_effects_for_event(
        self,
        user_id: int,
        event_type: str,
        event_data: dict = None,
        game_id: str = None
    ) -> List[Dict]:
        """
        Срабатывает эффекты для определенного события
        
        Args:
            user_id: ID пользователя
            event_type: Тип события
            event_data: Данные события
            game_id: ID игры
        
        Returns:
            List[Dict]: Список сработавших эффектов
        """
        try:
            # Получаем активные эффекты пользователя
            effects = self.get_user_effects(user_id, game_id=game_id)
            
            triggered_effects = []
            
            for effect in effects:
                # Проверяем условия срабатывания
                if self._should_trigger_effect(effect, event_type, event_data):
                    # Срабатываем эффект
                    success = trigger_effect(
                        effect_id=effect['id'],
                        triggered_by=event_type,
                        trigger_data=event_data
                    )
                    
                    if success:
                        triggered_effects.append(effect)
                        logger.info(f"✅ Эффект {effect['item_name']} сработал от {event_type}")
            
            return triggered_effects
            
        except Exception as e:
            logger.error(f"❌ Ошибка срабатывания эффектов для события {event_type}: {e}")
            return []
    
    def _should_trigger_effect(self, effect: Dict, event_type: str, event_data: dict = None) -> bool:
        """
        Проверяет, должен ли эффект сработать
        
        Args:
            effect: Данные эффекта
            event_type: Тип события
            event_data: Данные события
        
        Returns:
            bool: Должен ли сработать
        """
        try:
            # Проверяем, что эффект активен и есть оставшиеся использования
            if effect['effect_status'] != 'active' or effect['remaining_uses'] <= 0:
                return False
            
            # Проверяем условия срабатывания
            trigger_conditions = effect.get('trigger_conditions', {})
            
            # Если нет условий, срабатываем для всех событий
            if not trigger_conditions:
                return True
            
            # Проверяем тип события
            if 'event_types' in trigger_conditions:
                if event_type not in trigger_conditions['event_types']:
                    return False
            
            # Проверяем фазу игры
            if 'game_phase' in trigger_conditions and event_data:
                if event_data.get('game_phase') != trigger_conditions['game_phase']:
                    return False
            
            # Проверяем количество игроков
            if 'min_players' in trigger_conditions and event_data:
                if event_data.get('player_count', 0) < trigger_conditions['min_players']:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки условий срабатывания: {e}")
            return False
    
    def cleanup_expired_effects(self) -> int:
        """
        Очищает истекшие эффекты
        
        Returns:
            int: Количество удаленных эффектов
        """
        try:
            return cleanup_expired_effects()
        except Exception as e:
            logger.error(f"❌ Ошибка очистки истекших эффектов: {e}")
            return 0
    
    def get_effect_statistics(self, user_id: int = None, game_id: str = None) -> Dict[str, Any]:
        """
        Получает статистику по эффектам
        
        Args:
            user_id: ID пользователя
            game_id: ID игры
        
        Returns:
            Dict: Статистика
        """
        try:
            return get_effect_statistics(user_id=user_id, game_id=game_id)
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики эффектов: {e}")
            return {}
    
    def format_effect_info(self, effect: Dict) -> str:
        """
        Форматирует информацию об эффекте для отображения
        
        Args:
            effect: Данные эффекта
        
        Returns:
            str: Отформатированная информация
        """
        try:
            info = f"🎯 **{effect['item_name']}**
"
            info += f"📊 Тип: {self.effect_types.get(effect['effect_type'], effect['effect_type'])}
"
            info += f"📈 Статус: {effect['effect_status']}
"
            info += f"🔄 Использований: {effect['remaining_uses']}
"
            
            if effect.get('used_at'):
                info += f"⏰ Использован: {effect['used_at']}
"
            
            if effect.get('expires_at'):
                info += f"⏳ Истекает: {effect['expires_at']}
"
            
            if effect.get('triggered_by'):
                info += f"🎪 Сработал от: {self.trigger_types.get(effect['triggered_by'], effect['triggered_by'])}
"
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования информации об эффекте: {e}")
            return f"❌ Ошибка отображения эффекта: {e}"

# Глобальный экземпляр менеджера
effect_manager = ActiveEffectManager()
