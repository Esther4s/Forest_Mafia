#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчики команд для системы профилей лесов
Команды просмотра профилей, статистики и аналитики
"""

import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from forest_profiles import ForestProfileHandlers, get_forest_profile_manager
from forest_analytics import ForestAnalyticsManager, get_forest_analytics_manager
from user_forest_profile import UserForestProfileHandlers, get_user_forest_profile_manager
from forest_system import get_forest_manager

logger = logging.getLogger(__name__)


class ExtendedForestProfileHandlers:
    """Расширенные обработчики команд профилей лесов"""
    
    def __init__(self):
        self.forest_manager = get_forest_manager()
        self.forest_profile_manager = get_forest_profile_manager()
        self.forest_analytics_manager = get_forest_analytics_manager()
        self.user_forest_profile_manager = get_user_forest_profile_manager()
        
        # Создаем обработчики
        self.forest_profile_handlers = ForestProfileHandlers(self.forest_profile_manager)
        self.user_forest_profile_handlers = UserForestProfileHandlers(self.user_forest_profile_manager)
        
        # Импортируем обработчики команд лесов
        from forest_handlers import (
            handle_create_forest, handle_join_forest, handle_leave_forest, handle_forests,
            handle_my_forests_profile, handle_forest_profile, handle_forest_analytics,
            handle_top_forests, handle_help_forests, handle_summon_forest
        )
        
        # Сохраняем ссылки на функции-обработчики
        self.handle_create_forest = handle_create_forest
        self.handle_join_forest = handle_join_forest
        self.handle_leave_forest = handle_leave_forest
        self.handle_forests = handle_forests
        self.handle_my_forests_profile = handle_my_forests_profile
        self.handle_forest_profile = handle_forest_profile
        self.handle_forest_analytics = handle_forest_analytics
        self.handle_top_forests = handle_top_forests
        self.handle_help_forests = handle_help_forests
        self.handle_summon_forest = handle_summon_forest
    
    def get_command_handlers(self):
        """Возвращает все обработчики команд профилей"""
        return [
            # Основные команды лесов
            CommandHandler("create_forest", self.handle_create_forest),
            CommandHandler("forests", self.handle_forests),
            CommandHandler("join_forest", self.handle_join_forest),
            CommandHandler("leave_forest", self.handle_leave_forest),
            CommandHandler("summon_forest", self.handle_summon_forest),
            
            # Профили лесов
            CommandHandler("forest_profile", self.forest_profile_handlers.handle_forest_profile),
            CommandHandler("forest_stats", self.forest_profile_handlers.handle_forest_stats),
            CommandHandler("my_forests_profile", self.forest_profile_handlers.handle_my_forests_profile),
            
            # Профили пользователей с лесами
            CommandHandler("profile", self.user_forest_profile_handlers.handle_user_profile),
            CommandHandler("profile_compact", self.user_forest_profile_handlers.handle_compact_profile),
            CommandHandler("my_forests_profile", self.user_forest_profile_handlers.handle_user_forests),
            
            # Аналитика лесов
            CommandHandler("forest_analytics", self.handle_forest_analytics),
            CommandHandler("forest_ranking", self.handle_forest_ranking),
            CommandHandler("forest_comparison", self.handle_forest_comparison),
            CommandHandler("top_forests", self.handle_top_forests),
            
            # Статистика пользователей в лесах
            CommandHandler("user_forest_stats", self.handle_user_forest_stats),
            CommandHandler("forest_members_ranking", self.handle_forest_members_ranking),
        ]
    
    def get_callback_handlers(self):
        """Возвращает все обработчики callback-ов профилей"""
        return [
            # Callback-ы для профилей лесов
            CallbackQueryHandler(self.handle_forest_profile_callback, pattern="^forest_profile_"),
            CallbackQueryHandler(self.handle_forest_stats_callback, pattern="^forest_stats_"),
            CallbackQueryHandler(self.handle_forest_analytics_callback, pattern="^forest_analytics_"),
            
            # Callback-ы для профилей пользователей
            CallbackQueryHandler(self.handle_user_profile_callback, pattern="^user_profile_"),
            CallbackQueryHandler(self.handle_my_forests_callback, pattern="^my_forests$"),
            CallbackQueryHandler(self.handle_show_all_forests_callback, pattern="^show_all_forests$"),
            
            # Callback-ы для аналитики
            CallbackQueryHandler(self.handle_forest_ranking_callback, pattern="^forest_ranking_"),
            CallbackQueryHandler(self.handle_forest_comparison_callback, pattern="^forest_comparison_"),
        ]
    
    async def handle_forest_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /forest_analytics"""
        if not context.args:
            await update.message.reply_text(
                "📊 **Аналитика леса** 📊\n\n"
                "Использование: /forest_analytics <ID_леса>\n"
                "Пример: /forest_analytics les_i_volki\n\n"
                "Показывает детальную аналитику леса с трендами и рекомендациями."
            )
            return
        
        forest_id = context.args[0]
        
        try:
            # Получаем аналитику леса
            analytics = await self.forest_analytics_manager.get_forest_analytics(forest_id)
            
            if not analytics:
                await update.message.reply_text("❌ Лес не найден или нет данных для анализа.")
                return
            
            # Форматируем отчет
            report_text = self.forest_analytics_manager.format_analytics_report(analytics)
            
            # Создаем клавиатуру
            keyboard = [
                [
                    InlineKeyboardButton("📊 Детальная статистика", callback_data=f"forest_stats_{forest_id}"),
                    InlineKeyboardButton("🏆 Рейтинг участников", callback_data=f"forest_ranking_{forest_id}")
                ],
                [
                    InlineKeyboardButton("🌲 Профиль леса", callback_data=f"forest_profile_{forest_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                report_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении аналитики леса: {e}")
            await update.message.reply_text("❌ Ошибка при получении аналитики леса.")
    
    async def handle_forest_ranking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /forest_ranking"""
        if not context.args:
            await update.message.reply_text(
                "🏆 **Рейтинг участников леса** 🏆\n\n"
                "Использование: /forest_ranking <ID_леса>\n"
                "Пример: /forest_ranking les_i_volki\n\n"
                "Показывает рейтинг участников по вовлеченности."
            )
            return
        
        forest_id = context.args[0]
        
        try:
            # Получаем рейтинг участников
            engagements = await self.forest_analytics_manager.get_member_engagement_ranking(forest_id)
            
            if not engagements:
                await update.message.reply_text("❌ В лесу нет участников для рейтинга.")
                return
            
            # Форматируем рейтинг
            ranking_text = self.forest_analytics_manager.format_engagement_ranking(engagements)
            
            # Создаем клавиатуру
            keyboard = [
                [
                    InlineKeyboardButton("📊 Аналитика леса", callback_data=f"forest_analytics_{forest_id}"),
                    InlineKeyboardButton("🌲 Профиль леса", callback_data=f"forest_profile_{forest_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                ranking_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении рейтинга леса: {e}")
            await update.message.reply_text("❌ Ошибка при получении рейтинга леса.")
    
    async def handle_forest_comparison(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /forest_comparison"""
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "⚖️ **Сравнение лесов** ⚖️\n\n"
                "Использование: /forest_comparison <ID1> <ID2> [ID3] ...\n"
                "Пример: /forest_comparison les_i_volki les_volkov les_foxes\n\n"
                "Сравнивает несколько лесов по ключевым показателям."
            )
            return
        
        forest_ids = context.args
        
        try:
            # Получаем сравнение лесов
            comparison = await self.forest_analytics_manager.get_forest_comparison(forest_ids)
            
            if not comparison or not comparison["forests"]:
                await update.message.reply_text("❌ Не удалось найти леса для сравнения.")
                return
            
            # Форматируем сравнение
            text = "⚖️ **Сравнение лесов** ⚖️\n\n"
            
            # Общая информация
            text += f"📊 **Сравнивается {comparison['total_forests']} лесов:**\n\n"
            
            # Таблица сравнения
            text += "| Лес | Участники | Активность | Вовлеченность | Retention |\n"
            text += "|-----|-----------|------------|---------------|----------|\n"
            
            for forest in comparison["forests"]:
                text += f"| {forest.forest_name[:15]}... | {forest.total_members} | {forest.activity_rate:.1f}% | {forest.engagement_score:.1f} | {forest.member_retention_rate:.1f}% |\n"
            
            text += "\n"
            
            # Лучшие показатели
            text += "🏆 **Лучшие показатели:**\n"
            text += f"• Самая высокая активность: {comparison['best_activity'].forest_name} ({comparison['best_activity'].activity_rate:.1f}%)\n"
            text += f"• Лучшая вовлеченность: {comparison['best_engagement'].forest_name} ({comparison['best_engagement'].engagement_score:.1f})\n"
            text += f"• Лучший retention: {comparison['best_retention'].forest_name} ({comparison['best_retention'].member_retention_rate:.1f}%)\n"
            text += f"• Больше всего участников: {comparison['most_active'].forest_name} ({comparison['most_active'].total_members})\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка при сравнении лесов: {e}")
            await update.message.reply_text("❌ Ошибка при сравнении лесов.")
    
    async def handle_top_forests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /top_forests"""
        try:
            from database import get_db_session, Forest
            session = get_db_session()
            
            try:
                # Получаем все леса
                forests = session.query(Forest).all()
                
                if not forests:
                    await update.message.reply_text("🌲 Пока нет лесов для рейтинга.")
                    return
                
                # Получаем аналитику для каждого леса
                forest_analytics = []
                for forest in forests:
                    analytics = await self.forest_analytics_manager.get_forest_analytics(forest.id)
                    if analytics:
                        forest_analytics.append(analytics)
                
                # Сортируем по баллу вовлеченности
                forest_analytics.sort(key=lambda x: x.engagement_score, reverse=True)
                
                # Форматируем топ лесов
                text = "🏆 **Топ лесов по вовлеченности** 🏆\n\n"
                
                for i, analytics in enumerate(forest_analytics[:10], 1):
                    if i == 1:
                        emoji = "🥇"
                    elif i == 2:
                        emoji = "🥈"
                    elif i == 3:
                        emoji = "🥉"
                    else:
                        emoji = "🏅"
                    
                    text += f"{emoji} **{analytics.forest_name}**\n"
                    text += f"   📊 Вовлеченность: {analytics.engagement_score:.1f}/100\n"
                    text += f"   👥 Участников: {analytics.total_members}\n"
                    text += f"   📈 Активность: {analytics.activity_rate:.1f}%\n"
                    text += f"   🆔 ID: `{analytics.forest_id}`\n\n"
                
                await update.message.reply_text(text, parse_mode='Markdown')
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Ошибка при получении топа лесов: {e}")
            await update.message.reply_text("❌ Ошибка при получении топа лесов.")
    
    async def handle_user_forest_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /user_forest_stats"""
        user = update.effective_user
        
        try:
            # Получаем профиль пользователя
            profile = await self.user_forest_profile_manager.get_user_forest_profile(user.id)
            
            if not profile:
                await update.message.reply_text("❌ Профиль не найден")
                return
            
            # Форматируем лесную статистику
            forest_stats = profile.forest_stats
            
            text = f"🌲 **Лесная статистика: {profile.first_name}** 🌲\n\n"
            
            text += "📊 **Общие показатели:**\n"
            text += f"• Лесов создано: {forest_stats.created_forests}\n"
            text += f"• Лесов участник: {forest_stats.member_forests}\n"
            text += f"• Всего лесов: {forest_stats.total_forests}\n"
            text += f"• Дней в лесах: {forest_stats.days_in_forests}\n\n"
            
            text += "📞 **Активность в вызовах:**\n"
            text += f"• Вызовов получено: {forest_stats.total_summons_received}\n"
            text += f"• Вызовов откликнулся: {forest_stats.total_summons_responded}\n"
            text += f"• Процент откликов: {forest_stats.response_rate:.1f}%\n"
            text += f"• Средняя активность лесов: {forest_stats.avg_forest_activity:.1f}%\n\n"
            
            # Балл вовлеченности
            engagement_emoji = "🔥" if forest_stats.forest_engagement_score >= 80 else "📈" if forest_stats.forest_engagement_score >= 60 else "📊"
            text += f"{engagement_emoji} **Балл вовлеченности в лесах: {forest_stats.forest_engagement_score:.1f}/100**\n\n"
            
            # Самый активный лес
            if forest_stats.most_active_forest:
                text += f"🌟 **Самый активный лес:** {forest_stats.most_active_forest['name']}\n\n"
            
            # Недавняя активность
            if forest_stats.recent_forest_activity:
                text += "🕐 **Недавняя активность в лесах:**\n"
                for activity in forest_stats.recent_forest_activity[:3]:
                    time_str = activity["timestamp"].strftime("%d.%m %H:%M")
                    text += f"• {activity['description']} ({time_str})\n"
            
            # Создаем клавиатуру
            keyboard = [
                [
                    InlineKeyboardButton("👤 Полный профиль", callback_data="full_profile"),
                    InlineKeyboardButton("🌲 Мои леса", callback_data="my_forests")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении лесной статистики пользователя: {e}")
            await update.message.reply_text("❌ Ошибка при получении лесной статистики.")
    
    async def handle_forest_members_ranking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /forest_members_ranking"""
        if not context.args:
            await update.message.reply_text(
                "🏆 **Рейтинг участников леса** 🏆\n\n"
                "Использование: /forest_members_ranking <ID_леса>\n"
                "Пример: /forest_members_ranking les_i_volki\n\n"
                "Показывает рейтинг участников по активности и вовлеченности."
            )
            return
        
        forest_id = context.args[0]
        
        try:
            # Получаем рейтинг участников
            engagements = await self.forest_analytics_manager.get_member_engagement_ranking(forest_id)
            
            if not engagements:
                await update.message.reply_text("❌ В лесу нет участников для рейтинга.")
                return
            
            # Форматируем рейтинг
            ranking_text = self.forest_analytics_manager.format_engagement_ranking(engagements)
            
            await update.message.reply_text(ranking_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка при получении рейтинга участников: {e}")
            await update.message.reply_text("❌ Ошибка при получении рейтинга участников.")
    
    # Callback обработчики
    async def handle_forest_profile_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для профиля леса"""
        query = update.callback_query
        forest_id = query.data.replace("forest_profile_", "")
        
        try:
            profile = await self.forest_profile_manager.get_forest_profile(forest_id)
            if profile:
                profile_text = self.forest_profile_manager.format_forest_profile(profile)
                await query.edit_message_text(profile_text, parse_mode='Markdown')
            else:
                await query.answer("❌ Лес не найден")
        except Exception as e:
            logger.error(f"Ошибка в callback профиля леса: {e}")
            await query.answer("❌ Ошибка при получении профиля леса")
    
    async def handle_forest_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для статистики леса"""
        query = update.callback_query
        forest_id = query.data.replace("forest_stats_", "")
        
        try:
            analytics = await self.forest_analytics_manager.get_forest_analytics(forest_id)
            if analytics:
                stats_text = self.forest_analytics_manager.format_analytics_report(analytics)
                await query.edit_message_text(stats_text, parse_mode='Markdown')
            else:
                await query.answer("❌ Нет данных для анализа")
        except Exception as e:
            logger.error(f"Ошибка в callback статистики леса: {e}")
            await query.answer("❌ Ошибка при получении статистики")
    
    async def handle_forest_analytics_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для аналитики леса"""
        query = update.callback_query
        forest_id = query.data.replace("forest_analytics_", "")
        
        try:
            analytics = await self.forest_analytics_manager.get_forest_analytics(forest_id)
            if analytics:
                analytics_text = self.forest_analytics_manager.format_analytics_report(analytics)
                await query.edit_message_text(analytics_text, parse_mode='Markdown')
            else:
                await query.answer("❌ Нет данных для анализа")
        except Exception as e:
            logger.error(f"Ошибка в callback аналитики леса: {e}")
            await query.answer("❌ Ошибка при получении аналитики")
    
    async def handle_user_profile_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для профиля пользователя"""
        query = update.callback_query
        user = update.effective_user
        
        try:
            profile = await self.user_forest_profile_manager.get_user_forest_profile(user.id)
            if profile:
                profile_text = self.user_forest_profile_manager.format_user_forest_profile(profile)
                await query.edit_message_text(profile_text, parse_mode='Markdown')
            else:
                await query.answer("❌ Профиль не найден")
        except Exception as e:
            logger.error(f"Ошибка в callback профиля пользователя: {e}")
            await query.answer("❌ Ошибка при получении профиля")
    
    async def handle_my_forests_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для моих лесов"""
        query = update.callback_query
        user = update.effective_user
        
        try:
            forests_info = await self.forest_profile_manager.get_user_forests(user.id)
            forests_text = self.forest_profile_manager.format_user_forests(forests_info)
            await query.edit_message_text(forests_text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Ошибка в callback моих лесов: {e}")
            await query.answer("❌ Ошибка при получении лесов")
    
    async def handle_show_all_forests_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для показа всех лесов"""
        query = update.callback_query
        
        try:
            from database import get_db_session, Forest
            session = get_db_session()
            
            try:
                forests = session.query(Forest).all()
                
                if not forests:
                    text = "🌲 Пока нет созданных лесов."
                else:
                    text = "🌲 **Доступные леса:** 🌲\n\n"
                    
                    for i, forest in enumerate(forests, 1):
                        member_count = len(forest.members)
                        max_count = forest.max_size or "∞"
                        
                        text += (
                            f"{i}. **{forest.name}**\n"
                            f"   📝 {forest.description}\n"
                            f"   👥 {member_count}/{max_count} участников\n"
                            f"   🔒 {'Приватный' if forest.privacy == 'private' else 'Публичный'}\n"
                            f"   🆔 ID: `{forest.id}`\n\n"
                        )
                
                await query.edit_message_text(text, parse_mode='Markdown')
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Ошибка в callback всех лесов: {e}")
            await query.answer("❌ Ошибка при получении списка лесов")
    
    async def handle_forest_ranking_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для рейтинга леса"""
        query = update.callback_query
        forest_id = query.data.replace("forest_ranking_", "")
        
        try:
            engagements = await self.forest_analytics_manager.get_member_engagement_ranking(forest_id)
            if engagements:
                ranking_text = self.forest_analytics_manager.format_engagement_ranking(engagements)
                await query.edit_message_text(ranking_text, parse_mode='Markdown')
            else:
                await query.answer("❌ Нет данных для рейтинга")
        except Exception as e:
            logger.error(f"Ошибка в callback рейтинга леса: {e}")
            await query.answer("❌ Ошибка при получении рейтинга")
    
    async def handle_forest_comparison_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для сравнения лесов"""
        query = update.callback_query
        # Здесь можно добавить логику для callback сравнения
        await query.answer("ℹ️ Сравнение лесов через команду /forest_comparison")


# Глобальный экземпляр расширенных обработчиков
extended_forest_profile_handlers: Optional[ExtendedForestProfileHandlers] = None

def init_extended_forest_profile_handlers() -> ExtendedForestProfileHandlers:
    """Инициализирует расширенные обработчики профилей лесов"""
    global extended_forest_profile_handlers
    extended_forest_profile_handlers = ExtendedForestProfileHandlers()
    return extended_forest_profile_handlers

def get_extended_forest_profile_handlers() -> ExtendedForestProfileHandlers:
    """Получает экземпляр расширенных обработчиков профилей лесов"""
    if extended_forest_profile_handlers is None:
        raise RuntimeError("Расширенные обработчики профилей лесов не инициализированы")
    return extended_forest_profile_handlers
