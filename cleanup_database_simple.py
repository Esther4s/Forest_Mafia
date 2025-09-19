#!/usr/bin/env python3
"""
Простой скрипт для очистки зависших игр в PostgreSQL
"""

import psycopg2
from datetime import datetime

def cleanup_database():
    """Очищает зависшие игры в PostgreSQL"""
    print("🧹 Очистка зависших игр в PostgreSQL на Railway...")
    
    try:
        # Читаем URL базы данных из файла
        with open('database_url.txt', 'r') as f:
            database_url = f.read().strip()
        
        print(f"🔗 Подключение к базе данных: {database_url[:50]}...")
        
        # Подключаемся к базе данных
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("✅ Подключение к базе данных успешно!")
        
        # Получаем статистику до очистки
        cursor.execute("SELECT status, COUNT(*) FROM games GROUP BY status")
        status_stats = cursor.fetchall()
        
        print("\n📊 Статистика до очистки:")
        for status, count in status_stats:
            print(f"  {status}: {count}")
        
        # Находим активные игры
        cursor.execute("SELECT id, chat_id, status, phase, created_at FROM games WHERE status = 'active'")
        active_games = cursor.fetchall()
        
        print(f"\n📋 Найдено активных игр: {len(active_games)}")
        
        if active_games:
            print("🎮 Активные игры:")
            for game_id, chat_id, status, phase, created_at in active_games:
                print(f"  ID: {game_id}, Чат: {chat_id}, Статус: {status}, Фаза: {phase}, Создана: {created_at}")
            
            # Обновляем статус всех активных игр на 'cancelled'
            cursor.execute("""
                UPDATE games 
                SET status = 'cancelled', finished_at = CURRENT_TIMESTAMP 
                WHERE status = 'active'
            """)
            
            updated_count = cursor.rowcount
            print(f"\n✅ Обновлено игр: {updated_count}")
            
            # Подтверждаем изменения
            conn.commit()
            print("✅ Изменения сохранены в базе данных")
        else:
            print("✅ Активных игр не найдено")
        
        # Получаем статистику после очистки
        cursor.execute("SELECT status, COUNT(*) FROM games GROUP BY status")
        status_stats = cursor.fetchall()
        
        print("\n📊 Статистика после очистки:")
        for status, count in status_stats:
            print(f"  {status}: {count}")
        
        # Закрываем соединение
        cursor.close()
        conn.close()
        
        print("\n🎉 Очистка завершена успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при очистке базы данных: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        print("🚀 Запуск очистки зависших игр...")
        
        cleanup_database()
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
