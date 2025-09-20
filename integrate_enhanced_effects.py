#!/usr/bin/env python3
"""
Скрипт для интеграции улучшенных функций активных эффектов в основной код
"""

import os
import shutil
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backup_original_file(file_path: str) -> bool:
    """Создает резервную копию оригинального файла"""
    try:
        backup_path = f"{file_path}.backup"
        shutil.copy2(file_path, backup_path)
        logger.info(f"✅ Создана резервная копия: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка создания резервной копии {file_path}: {e}")
        return False

def update_database_functions():
    """Обновляет функции в database_psycopg2.py"""
    
    # Читаем оригинальный файл
    try:
        with open('database_psycopg2.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"❌ Ошибка чтения database_psycopg2.py: {e}")
        return False
    
    # Создаем резервную копию
    if not backup_original_file('database_psycopg2.py'):
        return False
    
    # Читаем новые функции
    try:
        with open('enhanced_active_effects_functions.py', 'r', encoding='utf-8') as f:
            enhanced_functions = f.read()
    except Exception as e:
        logger.error(f"❌ Ошибка чтения enhanced_active_effects_functions.py: {e}")
        return False
    
    # Извлекаем только функции (без импортов и main)
    lines = enhanced_functions.split('\n')
    function_lines = []
    in_function = False
    
    for line in lines:
        if line.startswith('def ') and not line.startswith('def main'):
            in_function = True
            function_lines.append(line)
        elif in_function:
            if line.startswith('def ') and line.startswith('def main'):
                break
            function_lines.append(line)
    
    enhanced_functions_code = '\n'.join(function_lines)
    
    # Находим место для вставки (после последней функции active_effects)
    insert_marker = "def cleanup_expired_effects() -> int:"
    insert_position = content.find(insert_marker)
    
    if insert_position == -1:
        logger.error("❌ Не найдено место для вставки функций")
        return False
    
    # Находим конец последней функции
    end_marker = "        return 0"
    end_position = content.find(end_marker, insert_position) + len(end_marker)
    
    # Вставляем новые функции
    new_content = (
        content[:end_position] + 
        "\n\n# ===== УЛУЧШЕННЫЕ ФУНКЦИИ АКТИВНЫХ ЭФФЕКТОВ =====\n\n" +
        enhanced_functions_code + 
        "\n\n# ===== КОНЕЦ УЛУЧШЕННЫХ ФУНКЦИЙ =====\n" +
        content[end_position:]
    )
    
    # Записываем обновленный файл
    try:
        with open('database_psycopg2.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        logger.info("✅ Функции database_psycopg2.py обновлены")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка записи database_psycopg2.py: {e}")
        return False

def create_effect_manager():
    """Создает менеджер активных эффектов"""
    
    manager_code = '''#!/usr/bin/env python3
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
            info = f"🎯 **{effect['item_name']}**\n"
            info += f"📊 Тип: {self.effect_types.get(effect['effect_type'], effect['effect_type'])}\n"
            info += f"📈 Статус: {effect['effect_status']}\n"
            info += f"🔄 Использований: {effect['remaining_uses']}\n"
            
            if effect.get('used_at'):
                info += f"⏰ Использован: {effect['used_at']}\n"
            
            if effect.get('expires_at'):
                info += f"⏳ Истекает: {effect['expires_at']}\n"
            
            if effect.get('triggered_by'):
                info += f"🎪 Сработал от: {self.trigger_types.get(effect['triggered_by'], effect['triggered_by'])}\n"
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования информации об эффекте: {e}")
            return f"❌ Ошибка отображения эффекта: {e}"

# Глобальный экземпляр менеджера
effect_manager = ActiveEffectManager()
'''
    
    try:
        with open('active_effect_manager.py', 'w', encoding='utf-8') as f:
            f.write(manager_code)
        logger.info("✅ Создан менеджер активных эффектов")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка создания менеджера эффектов: {e}")
        return False

def main():
    """Основная функция интеграции"""
    logger.info("🚀 Начинаем интеграцию улучшенных функций активных эффектов...")
    
    # 1. Обновляем функции в database_psycopg2.py
    logger.info("1. Обновляем функции в database_psycopg2.py...")
    if update_database_functions():
        logger.info("✅ Функции database_psycopg2.py обновлены")
    else:
        logger.error("❌ Не удалось обновить database_psycopg2.py")
        return False
    
    # 2. Создаем менеджер активных эффектов
    logger.info("2. Создаем менеджер активных эффектов...")
    if create_effect_manager():
        logger.info("✅ Менеджер активных эффектов создан")
    else:
        logger.error("❌ Не удалось создать менеджер эффектов")
        return False
    
    logger.info("\n🎉 Интеграция завершена!")
    logger.info("\n📝 Что было сделано:")
    logger.info("• Обновлены функции в database_psycopg2.py")
    logger.info("• Создан менеджер активных эффектов (active_effect_manager.py)")
    logger.info("• Созданы резервные копии оригинальных файлов")
    logger.info("\n🔧 Следующие шаги:")
    logger.info("1. Запустите improve_active_effects_table.py для обновления структуры БД")
    logger.info("2. Протестируйте новые функции")
    logger.info("3. Интегрируйте effect_manager в основной код бота")
    
    return True

if __name__ == "__main__":
    main()
