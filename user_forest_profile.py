#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Расширенные профили пользователей с информацией о лесах
Интеграция лесной статистики в профили игроков
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, Forest, ForestMember, ForestInvite, PlayerStats
from forest_system import ForestManager, get_forest_manager
from forest_profiles import ForestProfileManager, get_forest_profile_manager
from forest_analytics import ForestAnalyticsManager, get_forest_analytics_manager

logger = logging.getLogger(__name__)


@dataclass
class UserForestStats:
    """Статистика пользователя в лесах"""
    total_forests: int
    created_forests: int
    member_forests: int
    total_summons_received: int
    total_summons_responded: int
    response_rate: float
    avg_forest_activity: float
    most_active_forest: Optional[Dict[str, Any]]
    forest_engagement_score: float
    days_in_forests: int
    recent_forest_activity: List[Dict[str, Any]]


@dataclass
class UserForestProfile:
    """Полный профиль пользователя с лесами"""
    user_id: int
    username: str
    first_name: str
    # Игровая статистика (из PlayerStats)
    total_games: int
    games_won: int
    games_lost: int
    win_rate: float
    times_wolf: int
    times_fox: int
    times_hare: int
    times_mole: int
    times_beaver: int
    kills_made: int
    votes_received: int
    last_played: Optional[datetime]
    # Лесная статистика
    forest_stats: UserForestStats
    # Леса пользователя
    forests: List[Dict[str, Any]]


class UserForestProfileManager:
    """Менеджер профилей пользователей с лесами"""
    
    def __init__(self, forest_manager: ForestManager, 
                 forest_profile_manager: ForestProfileManager,
                 forest_analytics_manager: ForestAnalyticsManager):
        self.forest_manager = forest_manager
        self.forest_profile_manager = forest_profile_manager
        self.forest_analytics_manager = forest_analytics_manager
    
    async def get_user_forest_profile(self, user_id: int) -> Optional[UserForestProfile]:
        """Получает полный профиль пользователя с лесами"""
        try:
            session = get_db_session()
            
            try:
                # Получаем игровую статистику
                player_stats = session.query(PlayerStats).filter(
                    PlayerStats.user_id == user_id
                ).first()
                
                if not player_stats:
                    # Создаем базовую статистику если её нет
                    player_stats = PlayerStats(
                        user_id=user_id,
                        total_games=0,
                        games_won=0,
                        games_lost=0,
                        times_wolf=0,
                        times_fox=0,
                        times_hare=0,
                        times_mole=0,
                        times_beaver=0,
                        kills_made=0,
                        votes_received=0
                    )
                    session.add(player_stats)
                    session.commit()
                
                # Получаем лесную статистику
                forest_stats = await self._calculate_user_forest_stats(user_id)
                
                # Получаем информацию о пользователе из таблицы users
                from database_psycopg2 import get_user_by_telegram_id, create_user
                user_info = get_user_by_telegram_id(user_id)
                
                # Если пользователь не найден в таблице users, создаем его
                if not user_info:
                    try:
                        # Получаем информацию из Telegram
                        from telegram import Bot
                        bot = Bot(token=os.environ.get('BOT_TOKEN'))
                        tg_user = await bot.get_chat(user_id)
                        
                        # Создаем пользователя в базе данных
                        create_user(
                            user_id=user_id,
                            username=tg_user.username or f"User_{user_id}"
                        )
                        
                        # Получаем информацию о созданном пользователе
                        user_info = get_user_by_telegram_id(user_id)
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось создать пользователя {user_id}: {e}")
                        user_info = None
                
                # Получаем леса пользователя
                forests = await self.forest_profile_manager.get_user_forests(user_id)
                
                # Формируем профиль (приоритет: username из БД > first_name из Telegram)
                display_name = "Unknown"
                if user_info:
                    display_name = user_info.get('username') or "Unknown"
                else:
                    # Если нет информации из БД, используем данные из Telegram
                    display_name = user.first_name or user.username or f"User_{user_id}"
                
                profile = UserForestProfile(
                    user_id=user_id,
                    username=user_info.get('username', 'Unknown') if user_info else "Unknown",
                    first_name=display_name,
                    total_games=player_stats.total_games,
                    games_won=player_stats.games_won,
                    games_lost=player_stats.games_lost,
                    win_rate=(player_stats.games_won / player_stats.total_games * 100) if player_stats.total_games > 0 else 0,
                    times_wolf=player_stats.times_wolf,
                    times_fox=player_stats.times_fox,
                    times_hare=player_stats.times_hare,
                    times_mole=player_stats.times_mole,
                    times_beaver=player_stats.times_beaver,
                    kills_made=player_stats.kills_made,
                    votes_received=player_stats.votes_received,
                    last_played=player_stats.last_played,
                    forest_stats=forest_stats,
                    forests=forests
                )
                
                return profile
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Ошибка при получении профиля пользователя {user_id}: {e}")
            return None
    
    async def _calculate_user_forest_stats(self, user_id: int) -> UserForestStats:
        """Вычисляет лесную статистику пользователя"""
        session = get_db_session()
        try:
            # Получаем все леса пользователя
            member_forests = session.query(Forest).join(ForestMember).filter(
                ForestMember.user_id == user_id
            ).all()
            
            created_forests = session.query(Forest).filter(
                Forest.creator_id == user_id
            ).all()
            
            total_forests = len(set([f.id for f in member_forests + created_forests]))
            created_count = len(created_forests)
            member_count = len([f for f in member_forests if f.creator_id != user_id])
            
            # Статистика вызовов
            total_summons_received = 0
            total_summons_responded = 0
            
            for forest in member_forests:
                member = session.query(ForestMember).filter(
                    ForestMember.forest_id == forest.id,
                    ForestMember.user_id == user_id
                ).first()
                
                if member:
                    if member.last_called:
                        total_summons_received += 1
                    if member.is_opt_in and member.last_called:
                        total_summons_responded += 1
            
            response_rate = (total_summons_responded / total_summons_received * 100) if total_summons_received > 0 else 0
            
            # Средняя активность в лесах
            avg_forest_activity = 0
            if member_forests:
                activity_scores = []
                for forest in member_forests:
                    analytics = await self.forest_analytics_manager.get_forest_analytics(forest.id)
                    if analytics:
                        activity_scores.append(analytics.activity_rate)
                
                if activity_scores:
                    avg_forest_activity = sum(activity_scores) / len(activity_scores)
            
            # Самый активный лес
            most_active_forest = None
            if member_forests:
                best_forest = max(member_forests, key=lambda f: f.created_at)
                most_active_forest = {
                    "id": best_forest.id,
                    "name": best_forest.name,
                    "description": best_forest.description
                }
            
            # Балл вовлеченности в лесах
            forest_engagement_score = self._calculate_forest_engagement_score(
                total_forests, response_rate, avg_forest_activity, total_summons_responded
            )
            
            # Дни в лесах
            days_in_forests = 0
            for forest in member_forests:
                member = session.query(ForestMember).filter(
                    ForestMember.forest_id == forest.id,
                    ForestMember.user_id == user_id
                ).first()
                if member:
                    days_in_forests += (datetime.utcnow() - member.joined_at).days
            
            # Недавняя активность в лесах
            recent_activity = []
            for forest in member_forests:
                member = session.query(ForestMember).filter(
                    ForestMember.forest_id == forest.id,
                    ForestMember.user_id == user_id
                ).first()
                
                if member and member.last_called:
                    recent_activity.append({
                        "forest_id": forest.id,
                        "forest_name": forest.name,
                        "activity_type": "summon_response",
                        "timestamp": member.last_called,
                        "description": f"Отклик на вызов в лесу {forest.name}"
                    })
            
            # Сортируем по времени
            recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return UserForestStats(
                total_forests=total_forests,
                created_forests=created_count,
                member_forests=member_count,
                total_summons_received=total_summons_received,
                total_summons_responded=total_summons_responded,
                response_rate=response_rate,
                avg_forest_activity=avg_forest_activity,
                most_active_forest=most_active_forest,
                forest_engagement_score=forest_engagement_score,
                days_in_forests=days_in_forests,
                recent_forest_activity=recent_activity[:5]
            )
            
        finally:
            session.close()
    
    def _calculate_forest_engagement_score(self, total_forests: int, response_rate: float, 
                                         avg_activity: float, summons_responded: int) -> float:
        """Вычисляет балл вовлеченности в лесах (0-100)"""
        # Нормализуем метрики
        forests_score = min(total_forests * 10, 50)  # До 50 баллов за количество лесов
        response_score = min(response_rate, 100) * 0.3  # 30% за отклики
        activity_score = min(avg_activity, 100) * 0.2  # 20% за активность
        
        total_score = forests_score + response_score + activity_score
        return min(total_score, 100)
    
    def format_user_forest_profile(self, profile: UserForestProfile) -> str:
        """Форматирует профиль пользователя с лесами"""
        if not profile:
            return "❌ Профиль не найден"
        
        text = f"👤 **Профиль игрока: {profile.first_name}** 👤\n\n"
        
        # Основная информация
        text += f"🆔 **ID:** {profile.user_id}\n"
        text += f"👤 **Имя:** {profile.first_name}\n"
        if profile.username:
            text += f"📱 **Username:** @{profile.username}\n"
        text += "\n"
        
        # Игровая статистика
        text += "🎮 **Игровая статистика:**\n"
        text += f"• Игр сыграно: {profile.total_games}\n"
        text += f"• Побед: {profile.games_won}\n"
        text += f"• Поражений: {profile.games_lost}\n"
        text += f"• Процент побед: {profile.win_rate:.1f}%\n"
        text += f"• Убийств: {profile.kills_made}\n"
        text += f"• Голосов против: {profile.votes_received}\n"
        
        if profile.last_played:
            text += f"• Последняя игра: {profile.last_played.strftime('%d.%m.%Y %H:%M')}\n"
        
        text += "\n"
        
        # Роли
        text += "🎭 **Роли:**\n"
        roles = [
            ("🐺 Волк", profile.times_wolf),
            ("🦊 Лиса", profile.times_fox),
            ("🐰 Заяц", profile.times_hare),
            ("🦫 Крот", profile.times_mole),
            ("🦦 Бобёр", profile.times_beaver)
        ]
        
        for role_name, count in roles:
            if count > 0:
                text += f"• {role_name}: {count} раз\n"
        
        text += "\n"
        
        # Лесная статистика
        forest_stats = profile.forest_stats
        text += "🌲 **Лесная статистика:**\n"
        text += f"• Лесов создано: {forest_stats.created_forests}\n"
        text += f"• Лесов участник: {forest_stats.member_forests}\n"
        text += f"• Всего лесов: {forest_stats.total_forests}\n"
        text += f"• Вызовов получено: {forest_stats.total_summons_received}\n"
        text += f"• Вызовов откликнулся: {forest_stats.total_summons_responded}\n"
        text += f"• Процент откликов: {forest_stats.response_rate:.1f}%\n"
        text += f"• Дней в лесах: {forest_stats.days_in_forests}\n"
        
        # Балл вовлеченности в лесах
        engagement_emoji = "🔥" if forest_stats.forest_engagement_score >= 80 else "📈" if forest_stats.forest_engagement_score >= 60 else "📊"
        text += f"• {engagement_emoji} Вовлеченность в лесах: {forest_stats.forest_engagement_score:.1f}/100\n"
        
        if forest_stats.most_active_forest:
            text += f"• Самый активный лес: {forest_stats.most_active_forest['name']}\n"
        
        text += "\n"
        
        # Леса пользователя
        if profile.forests:
            text += "🌲 **Ваши леса:**\n"
            
            # Группируем по ролям
            created_forests = [f for f in profile.forests if f["role"] == "creator"]
            member_forests = [f for f in profile.forests if f["role"] == "member"]
            
            if created_forests:
                text += "🏗️ **Созданные:**\n"
                for forest_info in created_forests[:3]:  # Показываем только первые 3
                    forest = forest_info["forest"]
                    member_count = len(forest.members)
                    text += f"• {forest.name} ({member_count} участников)\n"
                
                if len(created_forests) > 3:
                    text += f"• ... и ещё {len(created_forests) - 3} лесов\n"
                text += "\n"
            
            if member_forests:
                text += "🌿 **Участник:**\n"
                for forest_info in member_forests[:3]:  # Показываем только первые 3
                    forest = forest_info["forest"]
                    member_count = len(forest.members)
                    opt_status = "🟢" if forest_info["is_opt_in"] else "🔴"
                    text += f"• {opt_status} {forest.name} ({member_count} участников)\n"
                
                if len(member_forests) > 3:
                    text += f"• ... и ещё {len(member_forests) - 3} лесов\n"
        
        return text
    
    def format_compact_user_profile(self, profile: UserForestProfile) -> str:
        """Форматирует компактный профиль пользователя"""
        if not profile:
            return "❌ Профиль не найден"
        
        text = f"👤 **{profile.first_name}**"
        
        if profile.username:
            text += f" (@{profile.username})"
        
        text += "\n\n"
        
        # Основные игровые показатели
        text += f"🎮 Игр: {profile.total_games} | Побед: {profile.games_won} ({profile.win_rate:.1f}%)\n"
        text += f"🌲 Лесов: {profile.forest_stats.total_forests} | Отклики: {profile.forest_stats.response_rate:.1f}%\n"
        
        # Топ роли
        roles = [
            ("🐺", profile.times_wolf),
            ("🦊", profile.times_fox),
            ("🐰", profile.times_hare),
            ("🦫", profile.times_mole),
            ("🦦", profile.times_beaver)
        ]
        
        top_roles = [f"{emoji}{count}" for emoji, count in roles if count > 0]
        if top_roles:
            text += f"🎭 Роли: {', '.join(top_roles[:3])}\n"
        
        return text


class UserForestProfileHandlers:
    """Обработчики команд профилей пользователей с лесами"""
    
    def __init__(self, profile_manager: UserForestProfileManager):
        self.profile_manager = profile_manager
    
    async def handle_user_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /profile"""
        user = update.effective_user
        
        # Проверяем, указан ли другой пользователь
        target_user_id = user.id
        if context.args and context.args[0].startswith('@'):
            # Поиск по username (упрощенно)
            username = context.args[0][1:]  # Убираем @
            # В реальной реализации здесь должен быть поиск по username
            await update.message.reply_text("🔍 Поиск по username пока не реализован")
            return
        
        try:
            # Получаем профиль пользователя
            profile = await self.profile_manager.get_user_forest_profile(target_user_id)
            
            if not profile:
                await update.message.reply_text("❌ Профиль не найден")
                return
            
            # Форматируем и отправляем
            profile_text = self.profile_manager.format_user_forest_profile(profile)
            
            # Создаем клавиатуру
            keyboard = [
                [
                    InlineKeyboardButton("🌲 Мои леса", callback_data="my_forests"),
                    InlineKeyboardButton("📊 Статистика", callback_data="user_stats")
                ],
                [
                    InlineKeyboardButton("🎮 Игровая статистика", callback_data="game_stats"),
                    InlineKeyboardButton("🌲 Лесная статистика", callback_data="forest_stats")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                profile_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении профиля пользователя: {e}")
            await update.message.reply_text("❌ Ошибка при получении профиля пользователя.")
    
    async def handle_compact_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /profile_compact"""
        user = update.effective_user
        
        try:
            profile = await self.profile_manager.get_user_forest_profile(user.id)
            
            if not profile:
                await update.message.reply_text("❌ Профиль не найден")
                return
            
            # Форматируем компактный профиль
            profile_text = self.profile_manager.format_compact_user_profile(profile)
            
            # Создаем клавиатуру для детального просмотра
            keyboard = [
                [InlineKeyboardButton("📋 Полный профиль", callback_data="full_profile")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                profile_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении компактного профиля: {e}")
            await update.message.reply_text("❌ Ошибка при получении профиля.")
    
    async def handle_user_forests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /my_forests_profile"""
        user = update.effective_user
        
        try:
            # Получаем леса пользователя
            forests_info = await self.profile_manager.forest_profile_manager.get_user_forests(user.id)
            
            # Форматируем
            forests_text = self.profile_manager.forest_profile_manager.format_user_forests(forests_info)
            
            # Создаем клавиатуру
            keyboard = [
                [InlineKeyboardButton("🌲 Все леса", callback_data="show_all_forests")],
                [InlineKeyboardButton("🏗️ Создать лес", callback_data="create_forest")],
                [InlineKeyboardButton("📊 Статистика лесов", callback_data="forest_analytics")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                forests_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении лесов пользователя: {e}")
            await update.message.reply_text("❌ Ошибка при получении ваших лесов.")


# Глобальный экземпляр менеджера профилей пользователей
user_forest_profile_manager: Optional[UserForestProfileManager] = None

def init_user_forest_profile_manager(forest_manager: ForestManager, 
                                   forest_profile_manager: ForestProfileManager,
                                   forest_analytics_manager: ForestAnalyticsManager) -> UserForestProfileManager:
    """Инициализирует менеджер профилей пользователей с лесами"""
    global user_forest_profile_manager
    user_forest_profile_manager = UserForestProfileManager(
        forest_manager, forest_profile_manager, forest_analytics_manager
    )
    return user_forest_profile_manager

def get_user_forest_profile_manager() -> UserForestProfileManager:
    """Получает экземпляр менеджера профилей пользователей с лесами"""
    if user_forest_profile_manager is None:
        raise RuntimeError("Менеджер профилей пользователей с лесами не инициализирован")
    return user_forest_profile_manager
