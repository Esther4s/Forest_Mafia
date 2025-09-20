#!/usr/bin/env python3
"""
Улучшенные функции для работы с активными эффектами
Поддерживает новые колонки и расширенную логику отслеживания эффектов
"""

import psycopg2
import psycopg2.extras
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_connection():
    """Получает соединение с базой данных"""
    try:
        # Читаем настройки из файла
        with open('database_url.txt', 'r') as f:
            database_url = f.read().strip()
        
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к базе данных: {e}")
        return None

def add_enhanced_active_effect(
    user_id: int, 
    item_name: str, 
    effect_type: str, 
    effect_data: dict = None,
    game_id: str = None, 
    chat_id: int = None, 
    expires_at: str = None,
    duration_rounds: int = 1,
    remaining_uses: int = 1,
    triggered_by: str = None,
    trigger_conditions: dict = None,
    auto_remove: bool = True
) -> bool:
    """
    Добавляет активный эффект предмета с расширенными параметрами
    
    Args:
        user_id: ID пользователя
        item_name: Название предмета
        effect_type: Тип эффекта
        effect_data: Данные эффекта (JSON)
        game_id: ID игры (если привязан к игре)
        chat_id: ID чата (если привязан к чату)
        expires_at: Время истечения эффекта
        duration_rounds: Количество раундов действия эффекта
        remaining_uses: Количество оставшихся использований
        triggered_by: Что вызвало срабатывание эффекта
        trigger_conditions: Условия срабатывания (JSON)
        auto_remove: Автоматически удалять при истечении
    
    Returns:
        bool: True если успешно добавлен
    """
    try:
        conn = get_database_connection()
        if not conn:
            return False
            
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO active_effects 
                (user_id, item_name, effect_type, effect_data, game_id, chat_id, 
                 expires_at, duration_rounds, remaining_uses, triggered_by, 
                 trigger_conditions, auto_remove, effect_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
            """, (
                str(user_id), 
                item_name, 
                effect_type, 
                json.dumps(effect_data or {}), 
                game_id, 
                str(chat_id) if chat_id else None, 
                expires_at,
                duration_rounds,
                remaining_uses,
                triggered_by,
                json.dumps(trigger_conditions or {}),
                auto_remove
            ))
            
            conn.commit()
            logger.info(f"✅ Расширенный активный эффект {item_name} добавлен для пользователя {user_id}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка добавления расширенного активного эффекта: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_enhanced_active_effects(
    user_id: int, 
    game_id: str = None, 
    chat_id: int = None,
    status: str = None
) -> List[Dict]:
    """
    Получает активные эффекты пользователя с расширенной фильтрацией
    
    Args:
        user_id: ID пользователя
        game_id: ID игры (опционально)
        chat_id: ID чата (опционально)
        status: Статус эффекта (active, expired, used, cancelled)
    
    Returns:
        List[Dict]: Список активных эффектов
    """
    try:
        conn = get_database_connection()
        if not conn:
            return []
            
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            query = """
                SELECT * FROM active_effects 
                WHERE user_id = %s
            """
            params = [str(user_id)]
            
            if game_id:
                query += " AND (game_id = %s OR game_id IS NULL)"
                params.append(game_id)
            
            if chat_id:
                query += " AND (chat_id = %s OR chat_id IS NULL)"
                params.append(str(chat_id))
            
            if status:
                query += " AND effect_status = %s"
                params.append(status)
            else:
                # По умолчанию показываем только активные эффекты
                query += " AND effect_status = 'active'"
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Конвертируем в обычные словари
            effects = []
            for row in results:
                effect = dict(row)
                if effect['effect_data']:
                    effect['effect_data'] = json.loads(effect['effect_data'])
                if effect['trigger_conditions']:
                    effect['trigger_conditions'] = json.loads(effect['trigger_conditions'])
                effects.append(effect)
            
            return effects
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения расширенных активных эффектов: {e}")
        return []
    finally:
        if conn:
            conn.close()

def trigger_effect(
    effect_id: int, 
    triggered_by: str,
    trigger_data: dict = None
) -> bool:
    """
    Отмечает эффект как сработавший и обновляет статистику
    
    Args:
        effect_id: ID эффекта
        triggered_by: Что вызвало срабатывание
        trigger_data: Дополнительные данные о срабатывании
    
    Returns:
        bool: True если успешно
    """
    try:
        conn = get_database_connection()
        if not conn:
            return False
            
        with conn.cursor() as cursor:
            # Обновляем эффект
            cursor.execute("""
                UPDATE active_effects 
                SET 
                    used_at = CURRENT_TIMESTAMP,
                    triggered_by = %s,
                    last_triggered_at = CURRENT_TIMESTAMP,
                    remaining_uses = remaining_uses - 1,
                    effect_data = effect_data || %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                triggered_by,
                json.dumps(trigger_data or {}),
                effect_id
            ))
            
            # Проверяем, нужно ли отметить как использованный
            cursor.execute("""
                UPDATE active_effects 
                SET 
                    effect_status = CASE 
                        WHEN remaining_uses <= 0 THEN 'used'
                        ELSE effect_status
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (effect_id,))
            
            conn.commit()
            logger.info(f"✅ Эффект {effect_id} сработал от {triggered_by}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка срабатывания эффекта {effect_id}: {e}")
        return False
    finally:
        if conn:
            conn.close()

def mark_effect_as_used(effect_id: int, reason: str = "manual") -> bool:
    """
    Отмечает эффект как использованный
    
    Args:
        effect_id: ID эффекта
        reason: Причина использования
    
    Returns:
        bool: True если успешно
    """
    try:
        conn = get_database_connection()
        if not conn:
            return False
            
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE active_effects 
                SET 
                    is_used = TRUE,
                    effect_status = 'used',
                    used_at = CURRENT_TIMESTAMP,
                    triggered_by = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (reason, effect_id))
            
            conn.commit()
            logger.info(f"✅ Эффект {effect_id} отмечен как использованный ({reason})")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка отметки эффекта как использованного: {e}")
        return False
    finally:
        if conn:
            conn.close()

def expire_effect(effect_id: int, reason: str = "expired") -> bool:
    """
    Отмечает эффект как истекший
    
    Args:
        effect_id: ID эффекта
        reason: Причина истечения
    
    Returns:
        bool: True если успешно
    """
    try:
        conn = get_database_connection()
        if not conn:
            return False
            
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE active_effects 
                SET 
                    effect_status = 'expired',
                    triggered_by = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (reason, effect_id))
            
            conn.commit()
            logger.info(f"✅ Эффект {effect_id} отмечен как истекший ({reason})")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка отметки эффекта как истекшего: {e}")
        return False
    finally:
        if conn:
            conn.close()

def cleanup_expired_effects() -> int:
    """
    Удаляет истекшие эффекты с учетом новых параметров
    
    Returns:
        int: Количество удаленных эффектов
    """
    try:
        conn = get_database_connection()
        if not conn:
            return 0
            
        with conn.cursor() as cursor:
            # Сначала отмечаем истекшие эффекты
            cursor.execute("""
                UPDATE active_effects 
                SET effect_status = 'expired'
                WHERE (expires_at IS NOT NULL AND expires_at < NOW())
                   OR (remaining_uses <= 0 AND effect_status = 'active')
            """)
            
            # Удаляем эффекты с auto_remove = TRUE
            cursor.execute("""
                DELETE FROM active_effects 
                WHERE (expires_at IS NOT NULL AND expires_at < NOW() AND auto_remove = TRUE)
                   OR (effect_status = 'expired' AND auto_remove = TRUE)
                   OR (remaining_uses <= 0 AND auto_remove = TRUE)
            """)
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"✅ Удалено {deleted_count} истекших эффектов")
            
            return deleted_count
            
    except Exception as e:
        logger.error(f"❌ Ошибка очистки истекших эффектов: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def get_effect_statistics(user_id: int = None, game_id: str = None) -> Dict[str, Any]:
    """
    Получает статистику по активным эффектам
    
    Args:
        user_id: ID пользователя (опционально)
        game_id: ID игры (опционально)
    
    Returns:
        Dict: Статистика по эффектам
    """
    try:
        conn = get_database_connection()
        if not conn:
            return {}
            
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            # Базовый запрос
            base_where = "1=1"
            params = []
            
            if user_id:
                base_where += " AND user_id = %s"
                params.append(str(user_id))
            
            if game_id:
                base_where += " AND game_id = %s"
                params.append(game_id)
            
            # Общая статистика
            cursor.execute(f"""
                SELECT 
                    effect_status,
                    COUNT(*) as count,
                    AVG(remaining_uses) as avg_remaining_uses,
                    COUNT(CASE WHEN used_at IS NOT NULL THEN 1 END) as triggered_count
                FROM active_effects 
                WHERE {base_where}
                GROUP BY effect_status
            """, params)
            
            status_stats = cursor.fetchall()
            
            # Статистика по типам эффектов
            cursor.execute(f"""
                SELECT 
                    effect_type,
                    item_name,
                    COUNT(*) as count,
                    AVG(remaining_uses) as avg_remaining_uses
                FROM active_effects 
                WHERE {base_where}
                GROUP BY effect_type, item_name
                ORDER BY count DESC
            """, params)
            
            type_stats = cursor.fetchall()
            
            # Статистика по триггерам
            cursor.execute(f"""
                SELECT 
                    triggered_by,
                    COUNT(*) as count
                FROM active_effects 
                WHERE {base_where} AND triggered_by IS NOT NULL
                GROUP BY triggered_by
                ORDER BY count DESC
            """, params)
            
            trigger_stats = cursor.fetchall()
            
            return {
                'status_breakdown': [dict(row) for row in status_stats],
                'effect_types': [dict(row) for row in type_stats],
                'triggers': [dict(row) for row in trigger_stats]
            }
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики эффектов: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def main():
    """Основная функция для тестирования"""
    logger.info("🧪 Тестирование улучшенных функций активных эффектов...")
    
    # Тестируем добавление эффекта
    test_user_id = 12345
    test_item = "🎭 Активная роль"
    
    logger.info("1. Тестируем добавление расширенного эффекта...")
    success = add_enhanced_active_effect(
        user_id=test_user_id,
        item_name=test_item,
        effect_type="boost",
        effect_data={"power": 99, "description": "99% шанс активной роли"},
        duration_rounds=3,
        remaining_uses=1,
        triggered_by="item_use",
        trigger_conditions={"phase": "waiting", "min_players": 4},
        auto_remove=True
    )
    
    if success:
        logger.info("✅ Эффект успешно добавлен")
        
        # Тестируем получение эффектов
        logger.info("2. Тестируем получение эффектов...")
        effects = get_enhanced_active_effects(test_user_id)
        logger.info(f"Найдено эффектов: {len(effects)}")
        
        if effects:
            effect = effects[0]
            logger.info(f"Эффект: {effect['item_name']} (статус: {effect['effect_status']})")
            
            # Тестируем срабатывание эффекта
            logger.info("3. Тестируем срабатывание эффекта...")
            trigger_success = trigger_effect(
                effect_id=effect['id'],
                triggered_by="game_start",
                trigger_data={"game_phase": "night", "round": 1}
            )
            
            if trigger_success:
                logger.info("✅ Эффект успешно сработал")
                
                # Тестируем статистику
                logger.info("4. Тестируем статистику...")
                stats = get_effect_statistics(test_user_id)
                logger.info(f"Статистика: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    # Тестируем очистку
    logger.info("5. Тестируем очистку истекших эффектов...")
    cleaned = cleanup_expired_effects()
    logger.info(f"Очищено эффектов: {cleaned}")
    
    logger.info("🎉 Тестирование завершено!")

if __name__ == "__main__":
    main()
