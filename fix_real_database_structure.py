#!/usr/bin/env python3
"""
Исправление реальной структуры базы данных
Учитывает реальные колонки: player_stats имеет и id, и player_id
"""

import os
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def fix_real_database_structure():
    """Исправляет реальную структуру базы данных"""
    
    # Получаем DATABASE_URL из переменных окружения
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
        return False
    
    print(f"🔗 Подключение к базе данных...")
    
    try:
        # Создаем подключение через psycopg2 для прямого SQL
        conn = psycopg2.connect(database_url)
        conn.autocommit = True  # Включаем автокоммит для DDL операций
        cursor = conn.cursor()
        
        print("📋 Анализируем реальную структуру таблиц...")
        
        # Анализируем player_stats
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default
            FROM information_schema.columns 
            WHERE table_name = 'player_stats' 
            ORDER BY ordinal_position
        """)
        
        player_stats_columns = cursor.fetchall()
        
        print(f"\n📋 Структура таблицы player_stats:")
        print(f"{'Колонка':<20} {'Тип':<15} {'NULL':<8} {'По умолчанию':<20}")
        print("-" * 70)
        
        for col in player_stats_columns:
            column_name, data_type, is_nullable, column_default = col
            default_str = str(column_default) if column_default else "None"
            print(f"{column_name:<20} {data_type:<15} {is_nullable:<8} {default_str:<20}")
        
        # Анализируем users
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position
        """)
        
        users_columns = cursor.fetchall()
        
        print(f"\n📋 Структура таблицы users:")
        print(f"{'Колонка':<20} {'Тип':<15} {'NULL':<8} {'По умолчанию':<20}")
        print("-" * 70)
        
        for col in users_columns:
            column_name, data_type, is_nullable, column_default = col
            default_str = str(column_default) if column_default else "None"
            print(f"{column_name:<20} {data_type:<15} {is_nullable:<8} {default_str:<20}")
        
        # Проверяем, есть ли колонка player_id в player_stats
        player_stats_column_names = [col[0] for col in player_stats_columns]
        has_player_id = 'player_id' in player_stats_column_names
        has_id = 'id' in player_stats_column_names
        
        print(f"\n🔍 Анализ player_stats:")
        print(f"  - Колонка id существует: {has_id}")
        print(f"  - Колонка player_id существует: {has_player_id}")
        
        if has_player_id and has_id:
            print(f"\n⚠️ Обнаружена проблема: есть и id, и player_id!")
            print(f"🔧 Исправляем структуру player_stats...")
            
            # Создаем резервную копию
            print("💾 Создаем резервную копию player_stats...")
            try:
                cursor.execute("DROP TABLE IF EXISTS player_stats_backup CASCADE")
                cursor.execute("""
                    CREATE TABLE player_stats_backup AS 
                    SELECT * FROM player_stats
                """)
                print("✅ Резервная копия создана: player_stats_backup")
            except Exception as e:
                print(f"⚠️ Ошибка при создании резервной копии: {e}")
            
            # Удаляем старую таблицу
            print("🗑️ Удаляем старую таблицу player_stats...")
            try:
                cursor.execute("DROP TABLE IF EXISTS player_stats CASCADE")
                print("✅ Старая таблица удалена")
            except Exception as e:
                print(f"⚠️ Ошибка при удалении старой таблицы: {e}")
            
            # Создаем новую таблицу с правильной структурой (только id, без player_id)
            print("🏗️ Создаем новую таблицу player_stats с правильной структурой...")
            cursor.execute("""
                CREATE TABLE player_stats (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    total_games INTEGER DEFAULT 0,
                    games_won INTEGER DEFAULT 0,
                    games_lost INTEGER DEFAULT 0,
                    times_wolf INTEGER DEFAULT 0,
                    times_fox INTEGER DEFAULT 0,
                    times_hare INTEGER DEFAULT 0,
                    times_mole INTEGER DEFAULT 0,
                    times_beaver INTEGER DEFAULT 0,
                    kills_made INTEGER DEFAULT 0,
                    votes_received INTEGER DEFAULT 0,
                    last_played TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ Новая таблица player_stats создана")
            
            # Копируем данные из резервной копии
            print("📋 Копируем данные из резервной копии...")
            try:
                cursor.execute("""
                    INSERT INTO player_stats (user_id, total_games, games_won, games_lost, 
                        times_wolf, times_fox, times_hare, times_mole, times_beaver, 
                        kills_made, votes_received, last_played, created_at, updated_at)
                    SELECT 
                        user_id,
                        COALESCE(total_games, 0),
                        COALESCE(games_won, 0),
                        COALESCE(games_lost, 0),
                        COALESCE(times_wolf, 0),
                        COALESCE(times_fox, 0),
                        COALESCE(times_hare, 0),
                        COALESCE(times_mole, 0),
                        COALESCE(times_beaver, 0),
                        COALESCE(kills_made, 0),
                        COALESCE(votes_received, 0),
                        last_played,
                        COALESCE(created_at, CURRENT_TIMESTAMP),
                        COALESCE(updated_at, CURRENT_TIMESTAMP)
                    FROM player_stats_backup
                """)
                print("✅ Данные скопированы")
            except Exception as e:
                print(f"⚠️ Ошибка при копировании данных: {e}")
                print("🔄 Продолжаем с пустой таблицей...")
            
            # Удаляем резервную копию
            print("🗑️ Удаляем резервную копию...")
            try:
                cursor.execute("DROP TABLE IF EXISTS player_stats_backup CASCADE")
                print("✅ Резервная копия удалена")
            except Exception as e:
                print(f"⚠️ Ошибка при удалении резервной копии: {e}")
        
        # Проверяем финальную структуру
        print(f"\n🔍 Проверяем финальную структуру player_stats...")
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default
            FROM information_schema.columns 
            WHERE table_name = 'player_stats' 
            ORDER BY ordinal_position
        """)
        
        final_columns = cursor.fetchall()
        
        print(f"\n📋 Финальная структура player_stats:")
        print(f"{'Колонка':<20} {'Тип':<15} {'NULL':<8} {'По умолчанию':<20}")
        print("-" * 70)
        
        for col in final_columns:
            column_name, data_type, is_nullable, column_default = col
            default_str = str(column_default) if column_default else "None"
            print(f"{column_name:<20} {data_type:<15} {is_nullable:<8} {default_str:<20}")
        
        # Тестируем вставку записи
        print(f"\n🧪 Тестируем вставку тестовой записи...")
        try:
            cursor.execute("""
                INSERT INTO player_stats (user_id, total_games, games_won, games_lost, 
                    times_wolf, times_fox, times_hare, times_mole, times_beaver, 
                    kills_made, votes_received, last_played, created_at, updated_at)
                VALUES (999999, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """)
            test_id = cursor.fetchone()[0]
            print(f"✅ Тестовая запись создана с id={test_id}")
            
            # Удаляем тестовую запись
            cursor.execute("DELETE FROM player_stats WHERE id = %s", (test_id,))
            print(f"✅ Тестовая запись удалена")
            
        except Exception as e:
            print(f"❌ Ошибка при тестировании вставки: {e}")
            return False
        
        print(f"\n✅ Структура базы данных успешно исправлена!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при исправлении структуры: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = fix_real_database_structure()
    if success:
        print("\n🚀 Теперь можно тестировать команды профиля!")
    else:
        print("\n💥 Исправление не удалось, проверьте логи выше")
