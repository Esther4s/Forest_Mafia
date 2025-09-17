#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестирование расширенной системы лесов с профилями
Проверяет все функции: профили, аналитику, рейтинги, статистику
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from database import init_database, get_db_session
from forest_system import ForestManager, ForestConfig, ForestPrivacy
from forest_profiles import ForestProfileManager
from forest_analytics import ForestAnalyticsManager
from user_forest_profile import UserForestProfileManager

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


async def test_forest_creation_and_profiles():
    """Тестирует создание лесов и профили"""
    print("🧪 Тестирование создания лесов и профилей...")
    
    try:
        # Инициализируем базу данных
        init_database()
        
        # Создаем мок-бота
        mock_bot = MockBot()
        
        # Инициализируем менеджеры
        forest_manager = ForestManager(mock_bot)
        forest_profile_manager = ForestProfileManager(forest_manager)
        forest_analytics_manager = ForestAnalyticsManager(forest_manager)
        user_forest_profile_manager = UserForestProfileManager(
            forest_manager, forest_profile_manager, forest_analytics_manager
        )
        
        # Создаем тестовый лес
        config = await forest_manager.create_forest(
            creator_id=123456789,
            name="Тестовый лес для профилей",
            description="Лес для тестирования системы профилей",
            privacy="public",
            max_size=15,
            batch_size=6,
            cooldown_minutes=30
        )
        
        print(f"✅ Лес создан: {config.name} (ID: {config.forest_id})")
        
        # Добавляем участников
        test_members = [
            (111111111, "user1", "Активный участник"),
            (222222222, "user2", "Обычный участник"),
            (333333333, "user3", "Новичок"),
            (444444444, "user4", "Старый участник"),
            (555555555, "user5", "Молчаливый участник"),
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
        
        # Тестируем профиль леса
        print("\n📊 Тестирование профиля леса...")
        forest_profile = await forest_profile_manager.get_forest_profile(config.forest_id)
        
        if forest_profile:
            profile_text = forest_profile_manager.format_forest_profile(forest_profile)
            print("✅ Профиль леса получен:")
            print(profile_text[:200] + "..." if len(profile_text) > 200 else profile_text)
        else:
            print("❌ Не удалось получить профиль леса")
        
        # Тестируем аналитику леса
        print("\n📈 Тестирование аналитики леса...")
        analytics = await forest_analytics_manager.get_forest_analytics(config.forest_id)
        
        if analytics:
            analytics_text = forest_analytics_manager.format_analytics_report(analytics)
            print("✅ Аналитика леса получена:")
            print(analytics_text[:200] + "..." if len(analytics_text) > 200 else analytics_text)
        else:
            print("❌ Не удалось получить аналитику леса")
        
        # Тестируем рейтинг участников
        print("\n🏆 Тестирование рейтинга участников...")
        engagements = await forest_analytics_manager.get_member_engagement_ranking(config.forest_id)
        
        if engagements:
            ranking_text = forest_analytics_manager.format_engagement_ranking(engagements)
            print("✅ Рейтинг участников получен:")
            print(ranking_text[:200] + "..." if len(ranking_text) > 200 else ranking_text)
        else:
            print("❌ Не удалось получить рейтинг участников")
        
        # Тестируем профиль пользователя
        print("\n👤 Тестирование профиля пользователя...")
        user_profile = await user_forest_profile_manager.get_user_forest_profile(111111111)
        
        if user_profile:
            profile_text = user_forest_profile_manager.format_user_forest_profile(user_profile)
            print("✅ Профиль пользователя получен:")
            print(profile_text[:200] + "..." if len(profile_text) > 200 else profile_text)
        else:
            print("❌ Не удалось получить профиль пользователя")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании профилей: {e}")
        return False


async def test_forest_comparison():
    """Тестирует сравнение лесов"""
    print("\n🧪 Тестирование сравнения лесов...")
    
    try:
        mock_bot = MockBot()
        forest_manager = ForestManager(mock_bot)
        forest_analytics_manager = ForestAnalyticsManager(forest_manager)
        
        # Создаем несколько лесов для сравнения
        forests = []
        for i in range(3):
            config = await forest_manager.create_forest(
                creator_id=123456789 + i,
                name=f"Лес для сравнения {i+1}",
                description=f"Тестовый лес номер {i+1}",
                privacy="public",
                max_size=10
            )
            forests.append(config.forest_id)
            
            # Добавляем участников
            for j in range(3):
                await forest_manager.join_forest(
                    forest_id=config.forest_id,
                    user_id=111111111 + j,
                    username=f"user{j}",
                    first_name=f"Участник {j}"
                )
        
        # Тестируем сравнение
        comparison = await forest_analytics_manager.get_forest_comparison(forests)
        
        if comparison and comparison["forests"]:
            print(f"✅ Сравнение {len(comparison['forests'])} лесов выполнено")
            print(f"   Лучшая активность: {comparison['best_activity'].forest_name}")
            print(f"   Лучшая вовлеченность: {comparison['best_engagement'].forest_name}")
        else:
            print("❌ Не удалось выполнить сравнение лесов")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании сравнения: {e}")
        return False


async def test_user_forest_stats():
    """Тестирует лесную статистику пользователей"""
    print("\n🧪 Тестирование лесной статистики пользователей...")
    
    try:
        mock_bot = MockBot()
        forest_manager = ForestManager(mock_bot)
        forest_profile_manager = ForestProfileManager(forest_manager)
        forest_analytics_manager = ForestAnalyticsManager(forest_manager)
        user_forest_profile_manager = UserForestProfileManager(
            forest_manager, forest_profile_manager, forest_analytics_manager
        )
        
        # Создаем лес
        config = await forest_manager.create_forest(
            creator_id=123456789,
            name="Лес для статистики",
            description="Тестирование статистики пользователей",
            privacy="public",
            max_size=20
        )
        
        # Добавляем пользователя в лес
        await forest_manager.join_forest(
            forest_id=config.forest_id,
            user_id=999999999,
            username="test_user",
            first_name="Тестовый пользователь"
        )
        
        # Получаем лесную статистику пользователя
        user_forests = await forest_profile_manager.get_user_forests(999999999)
        
        if user_forests:
            forests_text = forest_profile_manager.format_user_forests(user_forests)
            print("✅ Лесная статистика пользователя получена:")
            print(forests_text[:200] + "..." if len(forests_text) > 200 else forests_text)
        else:
            print("❌ Не удалось получить лесную статистику пользователя")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании лесной статистики: {e}")
        return False


async def test_database_queries():
    """Тестирует запросы к базе данных"""
    print("\n🧪 Тестирование запросов к базе данных...")
    
    try:
        from database import Forest, ForestMember, PlayerStats
        
        session = get_db_session()
        
        try:
            # Получаем все леса
            forests = session.query(Forest).all()
            print(f"📋 Лесов в базе: {len(forests)}")
            
            # Получаем всех участников
            members = session.query(ForestMember).all()
            print(f"👥 Участников в лесах: {len(members)}")
            
            # Получаем статистику игроков
            player_stats = session.query(PlayerStats).all()
            print(f"🎮 Статистик игроков: {len(player_stats)}")
            
            # Группируем участников по лесам
            from collections import defaultdict
            forest_members = defaultdict(list)
            
            for member in members:
                forest_members[member.forest_id].append(member)
            
            print("🌲 Участники по лесам:")
            for forest_id, members_list in forest_members.items():
                print(f"   Лес {forest_id}: {len(members_list)} участников")
            
            return True
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании БД: {e}")
        return False


async def main():
    """Главная функция тестирования"""
    print("🌲 Тестирование расширенной системы лесов с профилями 🌲")
    print("=" * 70)
    
    # Инициализируем базу данных
    try:
        init_database()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return
    
    # Запускаем тесты
    tests = [
        ("Создание лесов и профили", test_forest_creation_and_profiles),
        ("Сравнение лесов", test_forest_comparison),
        ("Лесная статистика пользователей", test_user_forest_stats),
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
    print(f"\n{'='*70}")
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print(f"{'='*70}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ ПРОШЕЛ" if success else "❌ ПРОВАЛЕН"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nРезультат: {passed}/{total} тестов прошли успешно")
    
    if passed == total:
        print("🎉 Все тесты прошли успешно! Расширенная система лесов готова к использованию.")
        print("\n🌲 Доступные функции:")
        print("• Профили лесов с детальной статистикой")
        print("• Профили пользователей с лесной активностью")
        print("• Аналитика и рейтинги участников")
        print("• Сравнение лесов по ключевым показателям")
        print("• Система вовлеченности и активности")
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
