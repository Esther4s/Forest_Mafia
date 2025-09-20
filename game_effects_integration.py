#!/usr/bin/env python3
"""
Интеграция системы активных эффектов с игровым процессом
Эффекты действуют ровно одну игру
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from database_psycopg2 import (
    add_enhanced_active_effect,
    get_enhanced_active_effects,
    trigger_effect,
    mark_effect_as_used,
    expire_effect,
    cleanup_expired_effects
)

logger = logging.getLogger(__name__)

class GameEffectsManager:
    """Менеджер эффектов для игрового процесса"""
    
    def __init__(self):
        self.effect_types = {
            'game_start': 'Начало игры',
            'game_end': 'Конец игры',
            'night_phase': 'Ночная фаза',
            'day_phase': 'Дневная фаза',
            'round_start': 'Начало раунда',
            'round_end': 'Конец раунда',
            'player_death': 'Смерть игрока',
            'role_assignment': 'Назначение ролей'
        }
    
    def apply_effects_at_game_start(self, game_id: str, chat_id: int, players: List[Dict]) -> Dict[str, Any]:
        """
        Применяет эффекты при начале игры
        
        Args:
            game_id: ID игры
            chat_id: ID чата
            players: Список игроков
        
        Returns:
            Dict: Результат применения эффектов
        """
        try:
            logger.info(f"🎮 apply_effects_at_game_start: Начало применения эффектов для игры {game_id}")
            
            applied_effects = []
            total_effects = 0
            
            for player in players:
                user_id = player.get('user_id') or player.get('id')
                if not user_id:
                    continue
                
                # Получаем активные эффекты игрока
                effects = get_enhanced_active_effects(
                    user_id=user_id,
                    game_id=game_id,
                    status='active'
                )
                
                logger.info(f"🔍 apply_effects_at_game_start: Найдено {len(effects)} активных эффектов для игрока {user_id}")
                
                for effect in effects:
                    # Проверяем, можно ли применить эффект в начале игры
                    if self._can_apply_effect_at_game_start(effect):
                        # Срабатываем эффект
                        success = trigger_effect(
                            effect_id=effect['id'],
                            triggered_by='game_start',
                            trigger_data={
                                'game_id': game_id,
                                'chat_id': chat_id,
                                'round': 1,
                                'phase': 'night'
                            }
                        )
                        
                        if success:
                            applied_effects.append({
                                'user_id': user_id,
                                'item_name': effect['item_name'],
                                'effect_type': effect['effect_type'],
                                'message': f"✅ {effect['item_name']} активирован в начале игры!"
                            })
                            total_effects += 1
                            logger.info(f"✅ apply_effects_at_game_start: Эффект {effect['item_name']} применен для игрока {user_id}")
                        else:
                            logger.warning(f"❌ apply_effects_at_game_start: Не удалось применить эффект {effect['item_name']} для игрока {user_id}")
            
            logger.info(f"🎉 apply_effects_at_game_start: Применено {total_effects} эффектов для игры {game_id}")
            
            return {
                'success': True,
                'applied_effects': applied_effects,
                'total_effects': total_effects,
                'message': f"🎮 Активировано {total_effects} эффектов в начале игры"
            }
            
        except Exception as e:
            logger.error(f"❌ apply_effects_at_game_start: Ошибка применения эффектов: {e}")
            return {
                'success': False,
                'applied_effects': [],
                'total_effects': 0,
                'message': f"❌ Ошибка применения эффектов: {e}"
            }
    
    def apply_effects_at_game_end(self, game_id: str, chat_id: int, players: List[Dict]) -> Dict[str, Any]:
        """
        Обрабатывает эффекты при окончании игры
        
        Args:
            game_id: ID игры
            chat_id: ID чата
            players: Список игроков
        
        Returns:
            Dict: Результат обработки эффектов
        """
        try:
            logger.info(f"🏁 apply_effects_at_game_end: Обработка эффектов при окончании игры {game_id}")
            
            expired_effects = []
            total_effects = 0
            
            for player in players:
                user_id = player.get('user_id') or player.get('id')
                if not user_id:
                    continue
                
                # Получаем активные эффекты игрока для этой игры
                effects = get_enhanced_active_effects(
                    user_id=user_id,
                    game_id=game_id,
                    status='active'
                )
                
                for effect in effects:
                    # Отмечаем эффект как истекший
                    success = expire_effect(
                        effect_id=effect['id'],
                        reason='game_end'
                    )
                    
                    if success:
                        expired_effects.append({
                            'user_id': user_id,
                            'item_name': effect['item_name'],
                            'effect_type': effect['effect_type']
                        })
                        total_effects += 1
                        logger.info(f"✅ apply_effects_at_game_end: Эффект {effect['item_name']} истек для игрока {user_id}")
            
            # Очищаем истекшие эффекты
            cleaned = cleanup_expired_effects()
            
            logger.info(f"🧹 apply_effects_at_game_end: Истекло {total_effects} эффектов, очищено {cleaned} записей для игры {game_id}")
            
            return {
                'success': True,
                'expired_effects': expired_effects,
                'total_effects': total_effects,
                'cleaned_effects': cleaned,
                'message': f"🏁 Истекло {total_effects} эффектов при окончании игры"
            }
            
        except Exception as e:
            logger.error(f"❌ apply_effects_at_game_end: Ошибка обработки эффектов: {e}")
            return {
                'success': False,
                'expired_effects': [],
                'total_effects': 0,
                'message': f"❌ Ошибка обработки эффектов: {e}"
            }
    
    def apply_effects_during_game(self, game_id: str, chat_id: int, event_type: str, event_data: Dict = None) -> Dict[str, Any]:
        """
        Применяет эффекты во время игры
        
        Args:
            game_id: ID игры
            chat_id: ID чата
            event_type: Тип события
            event_data: Данные события
        
        Returns:
            Dict: Результат применения эффектов
        """
        try:
            logger.info(f"🎯 apply_effects_during_game: Применение эффектов для события {event_type} в игре {game_id}")
            
            # Получаем всех игроков игры
            from database_psycopg2 import get_game_players
            players = get_game_players(game_id)
            
            if not players:
                logger.warning(f"⚠️ apply_effects_during_game: Не найдены игроки для игры {game_id}")
                return {
                    'success': False,
                    'message': "Игроки не найдены"
                }
            
            triggered_effects = []
            total_effects = 0
            
            for player in players:
                user_id = player.get('user_id')
                if not user_id:
                    continue
                
                # Получаем активные эффекты игрока
                effects = get_enhanced_active_effects(
                    user_id=user_id,
                    game_id=game_id,
                    status='active'
                )
                
                for effect in effects:
                    # Проверяем, должен ли эффект сработать для этого события
                    if self._should_trigger_effect_for_event(effect, event_type, event_data):
                        # Срабатываем эффект
                        success = trigger_effect(
                            effect_id=effect['id'],
                            triggered_by=event_type,
                            trigger_data=event_data or {}
                        )
                        
                        if success:
                            triggered_effects.append({
                                'user_id': user_id,
                                'item_name': effect['item_name'],
                                'effect_type': effect['effect_type'],
                                'event_type': event_type
                            })
                            total_effects += 1
                            logger.info(f"✅ apply_effects_during_game: Эффект {effect['item_name']} сработал для события {event_type}")
            
            logger.info(f"🎉 apply_effects_during_game: Сработало {total_effects} эффектов для события {event_type}")
            
            return {
                'success': True,
                'triggered_effects': triggered_effects,
                'total_effects': total_effects,
                'message': f"🎯 Сработало {total_effects} эффектов для события {event_type}"
            }
            
        except Exception as e:
            logger.error(f"❌ apply_effects_during_game: Ошибка применения эффектов: {e}")
            return {
                'success': False,
                'triggered_effects': [],
                'total_effects': 0,
                'message': f"❌ Ошибка применения эффектов: {e}"
            }
    
    def _can_apply_effect_at_game_start(self, effect: Dict) -> bool:
        """
        Проверяет, можно ли применить эффект в начале игры
        
        Args:
            effect: Данные эффекта
        
        Returns:
            bool: Можно ли применить
        """
        try:
            # Проверяем условия срабатывания
            trigger_conditions = effect.get('trigger_conditions', {})
            
            # Если нет условий, применяем
            if not trigger_conditions:
                return True
            
            # Проверяем тип события
            if 'event_types' in trigger_conditions:
                if 'game_start' not in trigger_conditions['event_types']:
                    return False
            
            # Проверяем фазу игры
            if 'game_phase' in trigger_conditions:
                if trigger_conditions['game_phase'] != 'night':
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ _can_apply_effect_at_game_start: Ошибка проверки эффекта: {e}")
            return False
    
    def _should_trigger_effect_for_event(self, effect: Dict, event_type: str, event_data: Dict = None) -> bool:
        """
        Проверяет, должен ли эффект сработать для события
        
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
            
            return True
            
        except Exception as e:
            logger.error(f"❌ _should_trigger_effect_for_event: Ошибка проверки эффекта: {e}")
            return False
    
    def get_game_effects_summary(self, game_id: str) -> Dict[str, Any]:
        """
        Получает сводку по эффектам игры
        
        Args:
            game_id: ID игры
        
        Returns:
            Dict: Сводка по эффектам
        """
        try:
            from database_psycopg2 import get_game_players
            players = get_game_players(game_id)
            
            if not players:
                return {
                    'success': False,
                    'message': "Игроки не найдены"
                }
            
            total_effects = 0
            effects_by_player = {}
            
            for player in players:
                user_id = player.get('user_id')
                if not user_id:
                    continue
                
                effects = get_enhanced_active_effects(
                    user_id=user_id,
                    game_id=game_id,
                    status='active'
                )
                
                effects_by_player[user_id] = effects
                total_effects += len(effects)
            
            return {
                'success': True,
                'game_id': game_id,
                'total_effects': total_effects,
                'effects_by_player': effects_by_player,
                'message': f"📊 Найдено {total_effects} активных эффектов в игре"
            }
            
        except Exception as e:
            logger.error(f"❌ get_game_effects_summary: Ошибка получения сводки: {e}")
            return {
                'success': False,
                'message': f"❌ Ошибка получения сводки: {e}"
            }

# Глобальный экземпляр менеджера
game_effects_manager = GameEffectsManager()
