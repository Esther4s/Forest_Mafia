#!/usr/bin/env python3
"""
Проверка структуры таблицы active_effects
"""

from database_psycopg2 import get_database_connection

def check_table_structure():
    """Проверяет структуру таблицы active_effects"""
    try:
        conn = get_database_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных")
            return
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'active_effects'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            
            print("📋 Структура таблицы active_effects:")
            print("-" * 60)
            for col in columns:
                print(f"{col[0]:<20} | {col[1]:<15} | {col[2]:<10} | {col[3] or 'None'}")
            
            print(f"\n📊 Всего колонок: {len(columns)}")
            
    except Exception as e:
        print(f"❌ Ошибка проверки структуры: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_table_structure()
