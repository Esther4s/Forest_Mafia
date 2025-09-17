#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Аналитика и рейтинги лесов
Детальная статистика, тренды, сравнения
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict, Counter
import statistics

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, Forest, ForestMember, ForestInvite
from forest_system import ForestManager, get_forest_manager

logger = logging.getLogger(__name__)


@dataclass
class ForestAnalytics:
    """Аналитика леса"""
    forest_id: str
    forest_name: str
    total_members: int
    active_members: int
    activity_rate: float
    total_summons: int
    successful_summons: int
    success_rate: float
    avg_response_time: float
    forest_age_days: int
    summon_frequency: float
    member_retention_rate: float
    peak_activity_hours: List[int]
    weekly_activity: Dict[str, int]
    member_growth_rate: float
    engagement_score: float


@dataclass
class MemberEngagement:
    """Вовлеченность участника"""
    user_id: int
    username: str
    first_name: str
    engagement_score: float
    response_rate: float
    days_in_forest: int
    summons_received: int
    summons_responded: int
    last_activity: Optional[datetime]
    activity_trend: str  # "increasing", "stable", "decreasing"
    rank_in_forest: int


class ForestAnalyticsManager:
    """Менеджер аналитики лесов"""
    
    def __init__(self, forest_manager: ForestManager):
        self.forest_manager = forest_manager
    
    async def get_forest_analytics(self, forest_id: str) -> Optional[ForestAnalytics]:
        """Получает детальную аналитику леса"""
        try:
            session = get_db_session()
            
            try:
                # Получаем лес
                forest = session.query(Forest).filter(Forest.id == forest_id).first()
                if not forest:
                    return None
                
                # Получаем участников
                members = session.query(ForestMember).filter(
                    ForestMember.forest_id == forest_id
                ).all()
                
                # Базовые метрики
                total_members = len(members)
                week_ago = datetime.utcnow() - timedelta(days=7)
                active_members = len([
                    m for m in members 
                    if m.last_called and m.last_called > week_ago
                ])
                
                activity_rate = (active_members / total_members * 100) if total_members > 0 else 0
                
                # Статистика вызовов
                total_summons = sum(1 for m in members if m.last_called)
                successful_summons = len([
                    m for m in members 
                    if m.last_called and m.is_opt_in
                ])
                success_rate = (successful_summons / total_summons * 100) if total_summons > 0 else 0
                
                # Среднее время отклика
                avg_response_time = self._calculate_avg_response_time(members)
                
                # Возраст леса
                forest_age_days = (datetime.utcnow() - forest.created_at).days
                summon_frequency = (total_summons / forest_age_days) if forest_age_days > 0 else 0
                
                # Retention rate (участники, которые остались более 7 дней)
                retention_members = len([
                    m for m in members 
                    if (datetime.utcnow() - m.joined_at).days >= 7
                ])
                member_retention_rate = (retention_members / total_members * 100) if total_members > 0 else 0
                
                # Пиковые часы активности
                peak_hours = self._calculate_peak_activity_hours(members)
                
                # Недельная активность
                weekly_activity = self._calculate_weekly_activity(members)
                
                # Рост участников
                member_growth_rate = self._calculate_member_growth_rate(forest, members)
                
                # Общий балл вовлеченности
                engagement_score = self._calculate_engagement_score(
                    activity_rate, success_rate, member_retention_rate, summon_frequency
                )
                
                return ForestAnalytics(
                    forest_id=forest_id,
                    forest_name=forest.name,
                    total_members=total_members,
                    active_members=active_members,
                    activity_rate=activity_rate,
                    total_summons=total_summons,
                    successful_summons=successful_summons,
                    success_rate=success_rate,
                    avg_response_time=avg_response_time,
                    forest_age_days=forest_age_days,
                    summon_frequency=summon_frequency,
                    member_retention_rate=member_retention_rate,
                    peak_activity_hours=peak_hours,
                    weekly_activity=weekly_activity,
                    member_growth_rate=member_growth_rate,
                    engagement_score=engagement_score
                )
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Ошибка при получении аналитики леса {forest_id}: {e}")
            return None
    
    def _calculate_avg_response_time(self, members: List[ForestMember]) -> float:
        """Вычисляет среднее время отклика"""
        response_times = []
        for member in members:
            if member.last_called and member.joined_at:
                response_time = (member.last_called - member.joined_at).total_seconds() / 60
                response_times.append(response_time)
        
        return statistics.mean(response_times) if response_times else 0.0
    
    def _calculate_peak_activity_hours(self, members: List[ForestMember]) -> List[int]:
        """Вычисляет пиковые часы активности"""
        activity_hours = []
        for member in members:
            if member.last_called:
                activity_hours.append(member.last_called.hour)
        
        if not activity_hours:
            return []
        
        # Считаем частоту по часам
        hour_counts = Counter(activity_hours)
        # Возвращаем топ-3 часа
        return [hour for hour, count in hour_counts.most_common(3)]
    
    def _calculate_weekly_activity(self, members: List[ForestMember]) -> Dict[str, int]:
        """Вычисляет активность по дням недели"""
        weekly_activity = defaultdict(int)
        
        for member in members:
            if member.last_called:
                day_name = member.last_called.strftime('%A')
                weekly_activity[day_name] += 1
        
        return dict(weekly_activity)
    
    def _calculate_member_growth_rate(self, forest: Forest, members: List[ForestMember]) -> float:
        """Вычисляет скорость роста участников"""
        if forest.created_at == forest.created_at:  # Если лес только создан
            return 0.0
        
        # Группируем участников по неделям
        weekly_joins = defaultdict(int)
        for member in members:
            week_start = member.joined_at - timedelta(days=member.joined_at.weekday())
            weekly_joins[week_start.strftime('%Y-%W')] += 1
        
        if len(weekly_joins) < 2:
            return 0.0
        
        # Вычисляем средний рост
        weeks = sorted(weekly_joins.keys())
        growth_rates = []
        
        for i in range(1, len(weeks)):
            prev_week = weekly_joins[weeks[i-1]]
            curr_week = weekly_joins[weeks[i]]
            if prev_week > 0:
                growth_rate = ((curr_week - prev_week) / prev_week) * 100
                growth_rates.append(growth_rate)
        
        return statistics.mean(growth_rates) if growth_rates else 0.0
    
    def _calculate_engagement_score(self, activity_rate: float, success_rate: float, 
                                  retention_rate: float, summon_frequency: float) -> float:
        """Вычисляет общий балл вовлеченности (0-100)"""
        # Нормализуем метрики
        activity_score = min(activity_rate, 100) / 100
        success_score = min(success_rate, 100) / 100
        retention_score = min(retention_rate, 100) / 100
        frequency_score = min(summon_frequency * 10, 100) / 100  # Нормализуем частоту
        
        # Взвешенная сумма
        engagement_score = (
            activity_score * 0.3 +
            success_score * 0.3 +
            retention_score * 0.2 +
            frequency_score * 0.2
        ) * 100
        
        return round(engagement_score, 1)
    
    async def get_member_engagement_ranking(self, forest_id: str) -> List[MemberEngagement]:
        """Получает рейтинг вовлеченности участников"""
        session = get_db_session()
        try:
            members = session.query(ForestMember).filter(
                ForestMember.forest_id == forest_id
            ).all()
            
            engagements = []
            
            for member in members:
                # Вычисляем метрики участника
                days_in_forest = (datetime.utcnow() - member.joined_at).days
                summons_received = 1 if member.last_called else 0
                summons_responded = 1 if member.is_opt_in and member.last_called else 0
                response_rate = (summons_responded / summons_received * 100) if summons_received > 0 else 0
                
                # Балл вовлеченности участника
                engagement_score = (
                    (1 if member.is_opt_in else 0) * 30 +  # За включенные уведомления
                    min(response_rate, 100) * 0.4 +  # За отклики
                    min(days_in_forest * 2, 30)  # За время в лесу
                )
                
                # Тренд активности (упрощенно)
                activity_trend = "stable"
                if member.last_called:
                    days_since_activity = (datetime.utcnow() - member.last_called).days
                    if days_since_activity <= 1:
                        activity_trend = "increasing"
                    elif days_since_activity >= 7:
                        activity_trend = "decreasing"
                
                engagement = MemberEngagement(
                    user_id=member.user_id,
                    username=member.username or "Unknown",
                    first_name=member.first_name or "Unknown",
                    engagement_score=engagement_score,
                    response_rate=response_rate,
                    days_in_forest=days_in_forest,
                    summons_received=summons_received,
                    summons_responded=summons_responded,
                    last_activity=member.last_called,
                    activity_trend=activity_trend,
                    rank_in_forest=0  # Будет установлен после сортировки
                )
                
                engagements.append(engagement)
            
            # Сортируем по баллу вовлеченности
            engagements.sort(key=lambda x: x.engagement_score, reverse=True)
            
            # Устанавливаем ранги
            for i, engagement in enumerate(engagements, 1):
                engagement.rank_in_forest = i
            
            return engagements
            
        finally:
            session.close()
    
    async def get_forest_comparison(self, forest_ids: List[str]) -> Dict[str, Any]:
        """Сравнивает несколько лесов"""
        analytics_list = []
        
        for forest_id in forest_ids:
            analytics = await self.get_forest_analytics(forest_id)
            if analytics:
                analytics_list.append(analytics)
        
        if not analytics_list:
            return {}
        
        # Находим лучшие показатели
        best_activity = max(analytics_list, key=lambda x: x.activity_rate)
        best_engagement = max(analytics_list, key=lambda x: x.engagement_score)
        best_retention = max(analytics_list, key=lambda x: x.member_retention_rate)
        most_active = max(analytics_list, key=lambda x: x.total_members)
        
        return {
            "forests": analytics_list,
            "best_activity": best_activity,
            "best_engagement": best_engagement,
            "best_retention": best_retention,
            "most_active": most_active,
            "total_forests": len(analytics_list)
        }
    
    def format_analytics_report(self, analytics: ForestAnalytics) -> str:
        """Форматирует отчет по аналитике"""
        text = f"📊 **Аналитика леса: {analytics.forest_name}** 📊\n\n"
        
        # Основные метрики
        text += "📈 **Ключевые показатели:**\n"
        text += f"• Участников: {analytics.total_members}\n"
        text += f"• Активных: {analytics.active_members} ({analytics.activity_rate:.1f}%)\n"
        text += f"• Вызовов: {analytics.total_summons}\n"
        text += f"• Успешных: {analytics.successful_summons} ({analytics.success_rate:.1f}%)\n"
        text += f"• Частота: {analytics.summon_frequency:.2f}/день\n"
        text += f"• Retention: {analytics.member_retention_rate:.1f}%\n\n"
        
        # Балл вовлеченности
        engagement_emoji = "🔥" if analytics.engagement_score >= 80 else "📈" if analytics.engagement_score >= 60 else "📊"
        text += f"{engagement_emoji} **Балл вовлеченности: {analytics.engagement_score}/100**\n\n"
        
        # Пиковые часы
        if analytics.peak_activity_hours:
            hours_str = ", ".join(map(str, analytics.peak_activity_hours))
            text += f"⏰ **Пиковые часы активности:** {hours_str}:00\n\n"
        
        # Недельная активность
        if analytics.weekly_activity:
            text += "📅 **Активность по дням недели:**\n"
            for day, count in sorted(analytics.weekly_activity.items(), key=lambda x: x[1], reverse=True):
                text += f"• {day}: {count} активностей\n"
            text += "\n"
        
        # Рост участников
        if analytics.member_growth_rate != 0:
            growth_emoji = "📈" if analytics.member_growth_rate > 0 else "📉"
            text += f"{growth_emoji} **Рост участников: {analytics.member_growth_rate:+.1f}%/неделя**\n\n"
        
        # Рекомендации
        text += "💡 **Рекомендации:**\n"
        
        if analytics.activity_rate < 50:
            text += "• Низкая активность - рассмотрите мотивационные мероприятия\n"
        
        if analytics.success_rate < 70:
            text += "• Низкий процент успешных вызовов - проверьте настройки уведомлений\n"
        
        if analytics.member_retention_rate < 60:
            text += "• Низкий retention - улучшите вовлеченность участников\n"
        
        if analytics.summon_frequency < 0.5:
            text += "• Редкие вызовы - увеличьте активность в лесу\n"
        
        if not text.endswith("\n"):
            text += "\n"
        
        return text
    
    def format_engagement_ranking(self, engagements: List[MemberEngagement]) -> str:
        """Форматирует рейтинг вовлеченности"""
        if not engagements:
            return "📊 Нет данных для рейтинга"
        
        text = "🏆 **Рейтинг вовлеченности участников:** 🏆\n\n"
        
        for i, engagement in enumerate(engagements[:10], 1):  # Топ-10
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = "🏅"
            
            trend_emoji = {
                "increasing": "📈",
                "stable": "➡️",
                "decreasing": "📉"
            }.get(engagement.activity_trend, "➡️")
            
            text += f"{emoji} **{engagement.first_name}** (@{engagement.username})\n"
            text += f"   📊 Балл: {engagement.engagement_score:.1f}\n"
            text += f"   📅 В лесу: {engagement.days_in_forest} дней\n"
            text += f"   📞 Отклики: {engagement.response_rate:.1f}%\n"
            text += f"   {trend_emoji} Тренд: {engagement.activity_trend}\n\n"
        
        return text


# Глобальный экземпляр менеджера аналитики
forest_analytics_manager: Optional[ForestAnalyticsManager] = None

def init_forest_analytics_manager(forest_manager: ForestManager) -> ForestAnalyticsManager:
    """Инициализирует менеджер аналитики лесов"""
    global forest_analytics_manager
    forest_analytics_manager = ForestAnalyticsManager(forest_manager)
    return forest_analytics_manager

def get_forest_analytics_manager() -> ForestAnalyticsManager:
    """Получает экземпляр менеджера аналитики лесов"""
    if forest_analytics_manager is None:
        raise RuntimeError("Менеджер аналитики лесов не инициализирован")
    return forest_analytics_manager
