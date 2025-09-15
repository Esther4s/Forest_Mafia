#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для обновления предметов в Лесном магазине
Добавляет новые предметы и создает таблицу inventory
"""

import os
import sys
from database_psycopg2 import init_db, close_db

def update_forest_shop(database_url=None):
    """Обновляет предметы в магазине и создает таблицу inventory"""
    try:
        # Устанавливаем DATABASE_URL если передан
        if database_url:
            os.environ['DATABASE_URL'] = database_url
        
        # Инициализируем подключение к БД
        db = init_db()
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                print("🔄 Обновляем схему базы данных...")
                
                # Создаем таблицу inventory если её нет
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    item_name VARCHAR(255) NOT NULL,
                    count INTEGER DEFAULT 1,
                    flags JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, item_name)
                );
                """)
                
                # Создаем индекс для быстрого поиска
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id);
                """)
                
                print("✅ Таблица inventory создана")
                
                # Очищаем старые товары
                cursor.execute("DELETE FROM shop")
                print("🗑️ Старые товары удалены")
                
                # Добавляем новые товары Лесного магазина
                forest_items = [
                    ('🎭 Активная роль', 1.00, 'Повышает шанс выпадения активной роли (волк, лиса, крот, бобёр) до 99%. Действует одну игру.', 'boosts', True),
                    ('🌿 Лесная маскировка', 100.00, 'Один раз скрывает роль игрока от проверки крота. Тратится автоматически при проверке.', 'consumables', True),
                    ('🛡️ Защита бобра', 150.00, 'Спасает игрока один раз от атаки волков. Активируется автоматически при атаке.', 'consumables', True),
                    ('🌰 Золотой орешек', 200.00, 'Удваивает заработанные орешки за следующую игру. Действует одну игру.', 'boosts', True),
                    ('🌙 Ночное зрение', 250.00, 'В ночной фазе игрок видит действия других (кто кого проверял/атаковал). Действует одну игру.', 'consumables', True),
                    ('🔍 Острый нюх', 300.00, 'Показывает роли всех игроков в следующей игре. Действует одну игру.', 'boosts', True),
                    ('🍄 Лесной эликсир', 400.00, 'Воскрешает игрока один раз, если его убили. Активируется автоматически при смерти.', 'consumables', True),
                    ('🌲 Древо жизни', 500.00, 'Даёт дополнительную жизнь на всю игру (умереть можно только после двух атак). Действует всю игру.', 'permanent', True)
                ]
                
                # Вставляем новые товары
                insert_query = """
                INSERT INTO shop (item_name, price, description, category, is_active)
                VALUES (%s, %s, %s, %s, %s)
                """
                
                for item in forest_items:
                    cursor.execute(insert_query, item)
                    print(f"✅ Добавлен товар: {item[0]} - {item[1]} орешков")
                
                # Подтверждаем изменения
                conn.commit()
                print("\n🎉 Лесной магазин успешно обновлен!")
                print("📦 Добавлено товаров:", len(forest_items))
                print("🗄️ Таблица inventory создана")
                
    except Exception as e:
        print(f"❌ Ошибка обновления магазина: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        close_db()
    
    return True

if __name__ == "__main__":
    print("🌲 Обновление Лесного магазина...")
    print("=" * 50)
    
    # Пробуем получить DATABASE_URL из аргументов командной строки
    database_url = None
    if len(sys.argv) > 1:
        database_url = sys.argv[1]
    elif os.environ.get('DATABASE_URL'):
        database_url = os.environ.get('DATABASE_URL')
    else:
        print("❌ DATABASE_URL не установлен!")
        print("Использование: python update_forest_shop_items.py <DATABASE_URL>")
        print("Или установите переменную окружения DATABASE_URL")
        sys.exit(1)
    
    success = update_forest_shop(database_url)
    
    if success:
        print("\n✅ Обновление завершено успешно!")
        print("🚀 Теперь можно использовать новый Лесной магазин!")
    else:
        print("\n❌ Обновление завершилось с ошибками!")
        sys.exit(1)
