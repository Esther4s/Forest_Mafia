#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для тестирования системы лесов
Проверяет основные функции без запуска бота
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from database import init_database, get_db_session
from forest_system import ForestManager, ForestConfig, ForestPrivacy

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class MockBot:
    """Мок-бот для тестирования"""
    
    async def send_message(self, chat_id, text, **kwargs):
        print(f"📤 Отправка сообщения в чат {chat_id}:")
        print(f"   {text}")
        if 'reply_markup' in kwargs:
            print(f"   Клавиатура: {kwargs['reply_markup']}")
        print()


async def test_forest_creation():
    """Тестирует создание леса"""
    print("🧪 Тестирование создания леса...")
    
    try:
        # Инициализируем базу данных
        init_database()
        
        # Создаем мок-бота
        mock_bot = MockBot()
        
        # Инициализируем менеджер лесов
        forest_manager = ForestManager(mock_bot)
        
        # Создаем тестовый лес
        config = await forest_manager.create_forest(
            creator_id=123456789,
            name="Тестовый лес",
            description="Лес для тестирования системы",
            privacy="public",
            max_size=10,
            batch_size=6,
            cooldown_minutes=30
        )
        
        print(f"✅ Лес создан успешно!")
        print(f"   ID: {config.forest_id}")
        print(f"   Название: {config.name}")
        print(f"   Описание: {config.description}")
        print(f"   Приватность: {config.privacy}")
        print(f"   Максимум участников: {config.max_size}")
        
        return config
        
    except Exception as e:
        print(f"❌ Ошибка при создании леса: {e}")
        return None


async def test_forest_membership():
    """Тестирует присоединение к лесу"""
    print("\n🧪 Тестирование присоединения к лесу...")
    
    try:
        mock_bot = MockBot()
        forest_manager = ForestManager(mock_bot)
        
        # Создаем лес
        config = await forest_manager.create_forest(
            creator_id=123456789,
            name="Лес для тестирования участников",
            description="Тестирование системы участников",
            privacy="public",
            max_size=5
        )
        
        # Добавляем участников
        test_members = [
            (111111111, "user1", "Пользователь 1"),
            (222222222, "user2", "Пользователь 2"),
            (333333333, "user3", "Пользователь 3"),
        ]
        
        for user_id, username, first_name in test_members:
            success = await forest_manager.join_forest(
                forest_id=config.forest_id,
                user_id=user_id,
                username=username,
                first_name=first_name
            )
            
            if success:
                print(f"✅ {first_name} присоединился к лесу")
            else:
                print(f"❌ Не удалось добавить {first_name}")
        
        # Получаем список участников
        members = await forest_manager.get_forest_members(config.forest_id)
        print(f"📋 Участников в лесу: {len(members)}")
        
        for member in members:
            print(f"   • {member.first_name} (@{member.username})")
        
        return config
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании участников: {e}")
        return None


async def test_summon_system():
    """Тестирует систему созыва"""
    print("\n🧪 Тестирование системы созыва...")
    
    try:
        from summon_system import SummonSystem
        
        mock_bot = MockBot()
        summon_system = SummonSystem(mock_bot)
        
        # Создаем лес с участниками
        mock_bot = MockBot()
        forest_manager = ForestManager(mock_bot)
        
        config = await forest_manager.create_forest(
            creator_id=123456789,
            name="Лес для тестирования созыва",
            description="Тестирование системы созыва",
            privacy="public",
            max_size=10,
            batch_size=3,  # Маленький батч для тестирования
            cooldown_minutes=1  # Короткий cooldown для тестирования
        )
        
        # Добавляем участников
        test_members = [
            (111111111, "user1", "Пользователь 1"),
            (222222222, "user2", "Пользователь 2"),
            (333333333, "user3", "Пользователь 3"),
            (444444444, "user4", "Пользователь 4"),
            (555555555, "user5", "Пользователь 5"),
        ]
        
        for user_id, username, first_name in test_members:
            await forest_manager.join_forest(
                forest_id=config.forest_id,
                user_id=user_id,
                username=username,
                first_name=first_name
            )
        
        # Тестируем созыв
        result = await summon_system.summon_forest_members(
            forest_id=config.forest_id,
            invoker_id=123456789,
            chat_id=-1001234567890,  # Тестовый чат
            config=config,
            game_time="20:00",
            location="Голосовой канал"
        )
        
        print(f"📊 Результат созыва:")
        print(f"   Статус: {result.status}")
        print(f"   Сообщение: {result.message}")
        print(f"   Всего участников: {result.total_members}")
        print(f"   Уведомлено: {result.notified_members}")
        print(f"   Батчей отправлено: {result.batches_sent}")
        
        if result.errors:
            print(f"   Ошибки: {len(result.errors)}")
            for error in result.errors:
                print(f"     • {error}")
        
        return result.status.value == "success"
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании созыва: {e}")
        return False


async def test_database_queries():
    """Тестирует запросы к базе данных"""
    print("\n🧪 Тестирование запросов к базе данных...")
    
    try:
        from database import Forest, ForestMember
        
        session = get_db_session()
        
        try:
            # Получаем все леса
            forests = session.query(Forest).all()
            print(f"📋 Лесов в базе: {len(forests)}")
            
            for forest in forests:
                member_count = len(forest.members)
                print(f"   • {forest.name} (ID: {forest.id}) - {member_count} участников")
            
            # Получаем всех участников
            members = session.query(ForestMember).all()
            print(f"👥 Всего участников: {len(members)}")
            
            # Группируем по лесам
            from collections import defaultdict
            forest_members = defaultdict(list)
            
            for member in members:
                forest_members[member.forest_id].append(member)
            
            for forest_id, members_list in forest_members.items():
                print(f"   Лес {forest_id}: {len(members_list)} участников")
                for member in members_list:
                    print(f"     • {member.first_name} (@{member.username})")
            
            return True
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании БД: {e}")
        return False


async def main():
    """Главная функция тестирования"""
    print("🌲 Тестирование системы лесов 🌲")
    print("=" * 50)
    
    # Инициализируем базу данных
    try:
        init_database()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return
    
    # Запускаем тесты
    tests = [
        ("Создание леса", test_forest_creation),
        ("Участники леса", test_forest_membership),
        ("Система созыва", test_summon_system),
        ("Запросы к БД", test_database_queries),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = await test_func()
            results.append((test_name, result is not False))
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте '{test_name}': {e}")
            results.append((test_name, False))
    
    # Выводим итоги
    print(f"\n{'='*50}")
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ ПРОШЕЛ" if success else "❌ ПРОВАЛЕН"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nРезультат: {passed}/{total} тестов прошли успешно")
    
    if passed == total:
        print("🎉 Все тесты прошли успешно! Система лесов готова к использованию.")
    else:
        print("⚠️ Некоторые тесты провалились. Проверьте логи выше.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")
