#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Система профилей лесов
Статистика, рейтинги участников, аналитика активности
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, Forest, ForestMember, ForestInvite
from forest_system import ForestManager, get_forest_manager

logger = logging.getLogger(__name__)


@dataclass
class ForestStats:
    """Статистика леса"""
    total_members: int
    active_members: int
    total_summons: int
    successful_summons: int
    avg_response_time: float  # в минутах
    most_active_member: Optional[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    forest_age_days: int
    summon_frequency: float  # вызовов в день


@dataclass
class MemberActivity:
    """Активность участника в лесу"""
    user_id: int
    username: str
    first_name: str
    joined_at: datetime
    last_activity: Optional[datetime]
    summons_received: int
    summons_responded: int
    response_rate: float
    days_in_forest: int
    activity_score: float


class ForestProfileManager:
    """Менеджер профилей лесов"""
    
    def __init__(self, forest_manager: ForestManager):
        self.forest_manager = forest_manager
    
    async def get_forest_profile(self, forest_id: str) -> Optional[Dict[str, Any]]:
        """Получает полный профиль леса"""
        try:
            # Получаем информацию о лесе
            forest = await self.forest_manager.get_forest_info(forest_id)
            if not forest:
                return None
            
            # Получаем статистику
            stats = await self._calculate_forest_stats(forest_id)
            
            # Получаем топ участников
            top_members = await self._get_top_members(forest_id, limit=5)
            
            # Получаем недавнюю активность
            recent_activity = await self._get_recent_activity(forest_id, limit=10)
            
            # Формируем профиль
            profile = {
                "forest": {
                    "id": forest.id,
                    "name": forest.name,
                    "description": forest.description,
                    "privacy": forest.privacy,
                    "max_size": forest.max_size,
                    "created_at": forest.created_at,
                    "creator_id": forest.creator_id
                },
                "stats": stats,
                "top_members": top_members,
                "recent_activity": recent_activity
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Ошибка при получении профиля леса {forest_id}: {e}")
            return None
    
    async def _calculate_forest_stats(self, forest_id: str) -> ForestStats:
        """Вычисляет статистику леса"""
        session = get_db_session()
        try:
            # Получаем участников
            members = session.query(ForestMember).filter(
                ForestMember.forest_id == forest_id
            ).all()
            
            total_members = len(members)
            
            # Считаем активных участников (с активностью за последние 7 дней)
            week_ago = datetime.utcnow() - timedelta(days=7)
            active_members = len([
                m for m in members 
                if m.last_called and m.last_called > week_ago
            ])
            
            # Считаем общее количество вызовов
            total_summons = sum(1 for m in members if m.last_called)
            
            # Считаем успешные вызовы (с откликом)
            successful_summons = len([
                m for m in members 
                if m.last_called and m.is_opt_in
            ])
            
            # Среднее время отклика (упрощенно)
            avg_response_time = 0.0
            if total_summons > 0:
                response_times = []
                for member in members:
                    if member.last_called and member.joined_at:
                        response_time = (member.last_called - member.joined_at).total_seconds() / 60
                        response_times.append(response_time)
                
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
            
            # Самый активный участник
            most_active = None
            if members:
                most_active_member = max(members, key=lambda m: m.last_called or datetime.min)
                if most_active_member.last_called:
                    most_active = {
                        "user_id": most_active_member.user_id,
                        "username": most_active_member.username,
                        "first_name": most_active_member.first_name,
                        "last_activity": most_active_member.last_called
                    }
            
            # Возраст леса
            forest = session.query(Forest).filter(Forest.id == forest_id).first()
            forest_age_days = 0
            if forest:
                forest_age_days = (datetime.utcnow() - forest.created_at).days
            
            # Частота вызовов (вызовов в день)
            summon_frequency = 0.0
            if forest_age_days > 0:
                summon_frequency = total_summons / forest_age_days
            
            return ForestStats(
                total_members=total_members,
                active_members=active_members,
                total_summons=total_summons,
                successful_summons=successful_summons,
                avg_response_time=avg_response_time,
                most_active_member=most_active,
                recent_activity=[],  # Будет заполнено отдельно
                forest_age_days=forest_age_days,
                summon_frequency=summon_frequency
            )
            
        finally:
            session.close()
    
    async def _get_top_members(self, forest_id: str, limit: int = 5) -> List[MemberActivity]:
        """Получает топ участников по активности"""
        session = get_db_session()
        try:
            members = session.query(ForestMember).filter(
                ForestMember.forest_id == forest_id
            ).all()
            
            # Вычисляем активность для каждого участника
            member_activities = []
            
            for member in members:
                # Считаем дни в лесу
                days_in_forest = (datetime.utcnow() - member.joined_at).days
                
                # Считаем полученные вызовы
                summons_received = 1 if member.last_called else 0
                
                # Считаем отклики (упрощенно - если opt_in, значит откликается)
                summons_responded = 1 if member.is_opt_in and member.last_called else 0
                
                # Процент откликов
                response_rate = (summons_responded / summons_received * 100) if summons_received > 0 else 0
                
                # Очки активности (комплексная формула)
                activity_score = (
                    summons_responded * 10 +  # За отклики
                    days_in_forest * 0.1 +   # За время в лесу
                    (1 if member.is_opt_in else 0) * 5  # За включенные уведомления
                )
                
                member_activity = MemberActivity(
                    user_id=member.user_id,
                    username=member.username or "Unknown",
                    first_name=member.first_name or "Unknown",
                    joined_at=member.joined_at,
                    last_activity=member.last_called,
                    summons_received=summons_received,
                    summons_responded=summons_responded,
                    response_rate=response_rate,
                    days_in_forest=days_in_forest,
                    activity_score=activity_score
                )
                
                member_activities.append(member_activity)
            
            # Сортируем по очкам активности
            member_activities.sort(key=lambda x: x.activity_score, reverse=True)
            
            return member_activities[:limit]
            
        finally:
            session.close()
    
    async def _get_recent_activity(self, forest_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает недавнюю активность леса"""
        session = get_db_session()
        try:
            # Получаем недавно присоединившихся
            recent_joins = session.query(ForestMember).filter(
                ForestMember.forest_id == forest_id,
                ForestMember.joined_at > datetime.utcnow() - timedelta(days=7)
            ).order_by(ForestMember.joined_at.desc()).limit(limit).all()
            
            activities = []
            for member in recent_joins:
                activities.append({
                    "type": "join",
                    "user_id": member.user_id,
                    "username": member.username,
                    "first_name": member.first_name,
                    "timestamp": member.joined_at,
                    "description": f"{member.first_name} присоединился к лесу"
                })
            
            # Получаем недавние вызовы
            recent_summons = session.query(ForestMember).filter(
                ForestMember.forest_id == forest_id,
                ForestMember.last_called > datetime.utcnow() - timedelta(days=3)
            ).order_by(ForestMember.last_called.desc()).limit(limit).all()
            
            for member in recent_summons:
                activities.append({
                    "type": "summon",
                    "user_id": member.user_id,
                    "username": member.username,
                    "first_name": member.first_name,
                    "timestamp": member.last_called,
                    "description": f"Вызов участников (включен {member.first_name})"
                })
            
            # Сортируем по времени
            activities.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return activities[:limit]
            
        finally:
            session.close()
    
    def format_forest_profile(self, profile: Dict[str, Any]) -> str:
        """Форматирует профиль леса для отображения"""
        if not profile:
            return "❌ Лес не найден"
        
        forest = profile["forest"]
        stats = profile["stats"]
        top_members = profile["top_members"]
        recent_activity = profile["recent_activity"]
        
        # Основная информация
        text = f"🌲 **Профиль леса: {forest['name']}** 🌲\n\n"
        
        # Описание и настройки
        text += f"📝 **Описание:** {forest['description']}\n"
        text += f"🔒 **Приватность:** {'Приватный' if forest['privacy'] == 'private' else 'Публичный'}\n"
        text += f"👥 **Участников:** {stats.total_members}/{forest['max_size'] or '∞'}\n"
        text += f"📅 **Создан:** {forest['created_at'].strftime('%d.%m.%Y')}\n"
        text += f"⏰ **Возраст:** {stats.forest_age_days} дней\n\n"
        
        # Статистика
        text += "📊 **Статистика:**\n"
        text += f"• Активных участников: {stats.active_members}\n"
        text += f"• Всего вызовов: {stats.total_summons}\n"
        text += f"• Успешных вызовов: {stats.successful_summons}\n"
        text += f"• Частота вызовов: {stats.summon_frequency:.1f}/день\n"
        
        if stats.avg_response_time > 0:
            text += f"• Среднее время отклика: {stats.avg_response_time:.1f} мин\n"
        
        text += "\n"
        
        # Топ участников
        if top_members:
            text += "🏆 **Самые активные участники:**\n"
            for i, member in enumerate(top_members, 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                text += f"{emoji} {member.first_name} (@{member.username})\n"
                text += f"   📈 Очки: {member.activity_score:.1f}\n"
                text += f"   📅 В лесу: {member.days_in_forest} дней\n"
                if member.response_rate > 0:
                    text += f"   📞 Отклики: {member.response_rate:.0f}%\n"
                text += "\n"
        
        # Недавняя активность
        if recent_activity:
            text += "🕐 **Недавняя активность:**\n"
            for activity in recent_activity[:5]:
                emoji = "➕" if activity["type"] == "join" else "📢"
                time_str = activity["timestamp"].strftime("%d.%m %H:%M")
                text += f"{emoji} {activity['description']} ({time_str})\n"
        
        return text
    
    async def get_user_forests(self, user_id: int) -> List[Dict[str, Any]]:
        """Получает леса пользователя"""
        session = get_db_session()
        try:
            # Леса, в которых состоит пользователь
            member_forests = session.query(Forest).join(ForestMember).filter(
                ForestMember.user_id == user_id
            ).all()
            
            # Леса, созданные пользователем
            created_forests = session.query(Forest).filter(
                Forest.creator_id == user_id
            ).all()
            
            forests_info = []
            
            # Добавляем леса, в которых состоит
            for forest in member_forests:
                member = session.query(ForestMember).filter(
                    ForestMember.forest_id == forest.id,
                    ForestMember.user_id == user_id
                ).first()
                
                forests_info.append({
                    "forest": forest,
                    "role": "creator" if forest.creator_id == user_id else "member",
                    "joined_at": member.joined_at if member else None,
                    "is_opt_in": member.is_opt_in if member else False,
                    "last_called": member.last_called if member else None
                })
            
            # Добавляем созданные леса (если еще не добавлены)
            for forest in created_forests:
                if not any(f["forest"].id == forest.id for f in forests_info):
                    forests_info.append({
                        "forest": forest,
                        "role": "creator",
                        "joined_at": forest.created_at,
                        "is_opt_in": True,
                        "last_called": None
                    })
            
            return forests_info
            
        finally:
            session.close()
    
    def format_user_forests(self, forests_info: List[Dict[str, Any]]) -> str:
        """Форматирует список лесов пользователя"""
        if not forests_info:
            return "🌲 Вы пока не состоите ни в одном лесу.\n\nИспользуйте /forests чтобы найти леса для присоединения!"
        
        text = "🌲 **Ваши леса:**\n\n"
        
        # Группируем по ролям
        created_forests = [f for f in forests_info if f["role"] == "creator"]
        member_forests = [f for f in forests_info if f["role"] == "member"]
        
        if created_forests:
            text += "🏗️ **Созданные вами леса:**\n"
            for forest_info in created_forests:
                forest = forest_info["forest"]
                member_count = len(forest.members)
                max_count = forest.max_size or "∞"
                
                text += f"• **{forest.name}** (ID: `{forest.id}`)\n"
                text += f"  👥 {member_count}/{max_count} участников\n"
                text += f"  📝 {forest.description}\n"
                text += f"  📅 Создан: {forest.created_at.strftime('%d.%m.%Y')}\n\n"
        
        if member_forests:
            text += "🌿 **Леса, в которых вы состоите:**\n"
            for forest_info in member_forests:
                forest = forest_info["forest"]
                member_count = len(forest.members)
                max_count = forest.max_size or "∞"
                opt_status = "🟢" if forest_info["is_opt_in"] else "🔴"
                
                text += f"• {opt_status} **{forest.name}** (ID: `{forest.id}`)\n"
                text += f"  👥 {member_count}/{max_count} участников\n"
                text += f"  📝 {forest.description}\n"
                text += f"  📅 Присоединился: {forest_info['joined_at'].strftime('%d.%m.%Y')}\n"
                
                if forest_info["last_called"]:
                    text += f"  📞 Последний вызов: {forest_info['last_called'].strftime('%d.%m %H:%M')}\n"
                
                text += "\n"
        
        text += "🟢 - получает уведомления | 🔴 - не получает уведомления"
        
        return text


class ForestProfileHandlers:
    """Обработчики команд профилей лесов"""
    
    def __init__(self, profile_manager: ForestProfileManager):
        self.profile_manager = profile_manager
    
    async def handle_forest_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /forest_profile"""
        if not context.args:
            await update.message.reply_text(
                "🌲 **Профиль леса** 🌲\n\n"
                "Использование: /forest_profile <ID_леса>\n"
                "Пример: /forest_profile les_i_volki\n\n"
                "Используйте /forests чтобы найти ID лесов"
            )
            return
        
        forest_id = context.args[0]
        
        try:
            # Получаем профиль леса
            profile = await self.profile_manager.get_forest_profile(forest_id)
            
            if not profile:
                await update.message.reply_text("❌ Лес не найден.")
                return
            
            # Форматируем и отправляем
            profile_text = self.profile_manager.format_forest_profile(profile)
            
            # Создаем клавиатуру
            keyboard = [
                [
                    InlineKeyboardButton("🌲 Присоединиться", callback_data=f"join_forest_{forest_id}"),
                    InlineKeyboardButton("📋 Список участников", callback_data=f"list_forest_{forest_id}")
                ],
                [InlineKeyboardButton("📊 Статистика", callback_data=f"forest_stats_{forest_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                profile_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении профиля леса: {e}")
            await update.message.reply_text("❌ Ошибка при получении профиля леса.")
    
    async def handle_my_forests_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /my_forests_profile"""
        user = update.effective_user
        
        try:
            # Получаем леса пользователя
            forests_info = await self.profile_manager.get_user_forests(user.id)
            
            # Форматируем и отправляем
            forests_text = self.profile_manager.format_user_forests(forests_info)
            
            # Создаем клавиатуру
            keyboard = [
                [InlineKeyboardButton("🌲 Все леса", callback_data="show_all_forests")],
                [InlineKeyboardButton("🏗️ Создать лес", callback_data="create_forest")]
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
    
    async def handle_forest_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /forest_stats"""
        if not context.args:
            await update.message.reply_text(
                "📊 **Статистика леса** 📊\n\n"
                "Использование: /forest_stats <ID_леса>\n"
                "Пример: /forest_stats les_i_volki"
            )
            return
        
        forest_id = context.args[0]
        
        try:
            # Получаем профиль леса
            profile = await self.profile_manager.get_forest_profile(forest_id)
            
            if not profile:
                await update.message.reply_text("❌ Лес не найден.")
                return
            
            # Формируем детальную статистику
            forest = profile["forest"]
            stats = profile["stats"]
            top_members = profile["top_members"]
            
            text = f"📊 **Детальная статистика леса: {forest['name']}** 📊\n\n"
            
            # Общая статистика
            text += "📈 **Общие показатели:**\n"
            text += f"• Всего участников: {stats.total_members}\n"
            text += f"• Активных (7 дней): {stats.active_members}\n"
            text += f"• Процент активности: {(stats.active_members/stats.total_members*100):.1f}%\n"
            text += f"• Всего вызовов: {stats.total_summons}\n"
            text += f"• Успешных вызовов: {stats.successful_summons}\n"
            text += f"• Процент успеха: {(stats.successful_summons/stats.total_summons*100):.1f}%\n"
            text += f"• Частота вызовов: {stats.summon_frequency:.2f} в день\n\n"
            
            # Топ участников с детальной статистикой
            if top_members:
                text += "🏆 **Рейтинг участников:**\n"
                for i, member in enumerate(top_members, 1):
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                    text += f"{emoji} **{member.first_name}** (@{member.username})\n"
                    text += f"   📊 Очки активности: {member.activity_score:.1f}\n"
                    text += f"   📅 В лесу: {member.days_in_forest} дней\n"
                    text += f"   📞 Получено вызовов: {member.summons_received}\n"
                    text += f"   ✅ Откликов: {member.summons_responded}\n"
                    text += f"   📈 Процент откликов: {member.response_rate:.1f}%\n"
                    if member.last_activity:
                        text += f"   🕐 Последняя активность: {member.last_activity.strftime('%d.%m %H:%M')}\n"
                    text += "\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики леса: {e}")
            await update.message.reply_text("❌ Ошибка при получении статистики леса.")


# Глобальный экземпляр менеджера профилей
forest_profile_manager: Optional[ForestProfileManager] = None

def init_forest_profile_manager(forest_manager: ForestManager) -> ForestProfileManager:
    """Инициализирует менеджер профилей лесов"""
    global forest_profile_manager
    forest_profile_manager = ForestProfileManager(forest_manager)
    return forest_profile_manager

def get_forest_profile_manager() -> ForestProfileManager:
    """Получает экземпляр менеджера профилей лесов"""
    if forest_profile_manager is None:
        raise RuntimeError("Менеджер профилей лесов не инициализирован")
    return forest_profile_manager
