#!/usr/bin/env python3
"""
Скрипт для улучшения таблицы active_effects
Добавляет недостающие колонки для полноценной системы отслеживания эффектов предметов
"""

import psycopg2
import json
import logging
from datetime import datetime, timedelta

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

def improve_active_effects_table():
    """Улучшает таблицу active_effects, добавляя недостающие колонки"""
    
    conn = get_database_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            logger.info("🔧 Начинаем улучшение таблицы active_effects...")
            
            # Список новых колонок для добавления
            new_columns = [
                {
                    'name': 'used_at',
                    'definition': 'TIMESTAMP',
                    'description': 'Время использования эффекта'
                },
                {
                    'name': 'triggered_by',
                    'definition': 'VARCHAR(100)',
                    'description': 'Что вызвало срабатывание эффекта'
                },
                {
                    'name': 'duration_rounds',
                    'definition': 'INTEGER DEFAULT 1',
                    'description': 'Количество раундов действия эффекта'
                },
                {
                    'name': 'remaining_uses',
                    'definition': 'INTEGER DEFAULT 1',
                    'description': 'Количество оставшихся использований'
                },
                {
                    'name': 'effect_status',
                    'definition': 'VARCHAR(50) DEFAULT \'active\'',
                    'description': 'Статус эффекта (active, expired, used, cancelled)'
                },
                {
                    'name': 'trigger_conditions',
                    'definition': 'JSONB DEFAULT \'{}\'::jsonb',
                    'description': 'Условия срабатывания эффекта'
                },
                {
                    'name': 'last_triggered_at',
                    'definition': 'TIMESTAMP',
                    'description': 'Время последнего срабатывания'
                },
                {
                    'name': 'auto_remove',
                    'definition': 'BOOLEAN DEFAULT TRUE',
                    'description': 'Автоматически удалять при истечении'
                },
                {
                    'name': 'updated_at',
                    'definition': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                    'description': 'Время последнего обновления'
                }
            ]
            
            # Проверяем существующие колонки
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'active_effects'
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            # Добавляем новые колонки
            for column in new_columns:
                if column['name'] not in existing_columns:
                    try:
                        cursor.execute(f"""
                            ALTER TABLE active_effects 
                            ADD COLUMN {column['name']} {column['definition']}
                        """)
                        logger.info(f"✅ Добавлена колонка: {column['name']} - {column['description']}")
                    except Exception as e:
                        logger.error(f"❌ Ошибка добавления колонки {column['name']}: {e}")
                else:
                    logger.info(f"ℹ️ Колонка {column['name']} уже существует")
            
            # Создаем индексы для новых колонок
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_active_effects_status ON active_effects(effect_status)",
                "CREATE INDEX IF NOT EXISTS idx_active_effects_triggered_by ON active_effects(triggered_by)",
                "CREATE INDEX IF NOT EXISTS idx_active_effects_used_at ON active_effects(used_at)",
                "CREATE INDEX IF NOT EXISTS idx_active_effects_last_triggered ON active_effects(last_triggered_at)",
                "CREATE INDEX IF NOT EXISTS idx_active_effects_remaining_uses ON active_effects(remaining_uses)"
            ]
            
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    logger.info(f"✅ Создан индекс: {index_sql.split('idx_')[1].split(' ON')[0]}")
                except Exception as e:
                    logger.error(f"❌ Ошибка создания индекса: {e}")
            
            # Создаем триггер для автоматического обновления updated_at
            trigger_function = """
                CREATE OR REPLACE FUNCTION update_active_effects_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """
            
            cursor.execute(trigger_function)
            logger.info("✅ Создана функция для обновления updated_at")
            
            # Создаем триггер
            trigger_sql = """
                DROP TRIGGER IF EXISTS trigger_active_effects_updated_at ON active_effects;
                CREATE TRIGGER trigger_active_effects_updated_at
                    BEFORE UPDATE ON active_effects
                    FOR EACH ROW
                    EXECUTE FUNCTION update_active_effects_updated_at();
            """
            
            cursor.execute(trigger_sql)
            logger.info("✅ Создан триггер для автоматического обновления updated_at")
            
            # Обновляем существующие записи (если есть)
            try:
                cursor.execute("""
                    UPDATE active_effects 
                    SET effect_status = 'active',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE effect_status IS NULL
                """)
                
                updated_rows = cursor.rowcount
                logger.info(f"✅ Обновлено {updated_rows} существующих записей")
            except Exception as e:
                logger.info(f"ℹ️ Нет записей для обновления: {e}")
            
            conn.commit()
            logger.info("🎉 Таблица active_effects успешно улучшена!")
            
            # Показываем финальную структуру таблицы
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'active_effects'
                ORDER BY ordinal_position
            """)
            
            columns_info = cursor.fetchall()
            logger.info("\n📋 Финальная структура таблицы active_effects:")
            logger.info("-" * 80)
            for col in columns_info:
                logger.info(f"{col[0]:<20} | {col[1]:<15} | {col[2]:<10} | {col[3] or 'None'}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка улучшения таблицы: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def create_cleanup_function():
    """Создает функцию для очистки истекших эффектов"""
    
    conn = get_database_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            cleanup_function = """
                CREATE OR REPLACE FUNCTION cleanup_expired_effects()
                RETURNS INTEGER AS $$
                DECLARE
                    deleted_count INTEGER;
                BEGIN
                    -- Удаляем истекшие эффекты с auto_remove = TRUE
                    DELETE FROM active_effects 
                    WHERE (expires_at IS NOT NULL AND expires_at < NOW())
                       OR (effect_status = 'expired')
                       OR (remaining_uses <= 0 AND auto_remove = TRUE);
                    
                    GET DIAGNOSTICS deleted_count = ROW_COUNT;
                    
                    -- Логируем результат
                    RAISE NOTICE 'Удалено % истекших эффектов', deleted_count;
                    
                    RETURN deleted_count;
                END;
                $$ LANGUAGE plpgsql;
            """
            
            cursor.execute(cleanup_function)
            conn.commit()
            logger.info("✅ Создана функция cleanup_expired_effects()")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания функции очистки: {e}")
        return False
    finally:
        conn.close()

def main():
    """Основная функция"""
    logger.info("🚀 Запуск улучшения таблицы active_effects...")
    
    # Улучшаем таблицу
    if improve_active_effects_table():
        logger.info("✅ Таблица успешно улучшена")
        
        # Создаем функцию очистки
        if create_cleanup_function():
            logger.info("✅ Функция очистки создана")
        else:
            logger.warning("⚠️ Не удалось создать функцию очистки")
        
        logger.info("\n🎉 Улучшение таблицы active_effects завершено!")
        logger.info("\n📝 Новые возможности:")
        logger.info("• Отслеживание времени использования эффектов")
        logger.info("• Отслеживание причин срабатывания")
        logger.info("• Поддержка многоразовых эффектов")
        logger.info("• Детальный статус эффектов")
        logger.info("• Условия срабатывания")
        logger.info("• Автоматическая очистка истекших эффектов")
        
    else:
        logger.error("❌ Не удалось улучшить таблицу")

if __name__ == "__main__":
    main()
