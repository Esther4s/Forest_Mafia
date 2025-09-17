#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Система созыва участников леса с батчингом
Продвинутая система уведомлений с управлением cooldown и батчингом
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError, BadRequest

from forest_system import ForestManager, ForestConfig, ForestPrivacy, get_forest_manager
from database import get_db_session, Forest, ForestMember

logger = logging.getLogger(__name__)


class SummonStatus(Enum):
    """Статусы созыва"""
    SUCCESS = "success"
    COOLDOWN = "cooldown"
    NO_MEMBERS = "no_members"
    NO_AVAILABLE = "no_available"
    PERMISSION_DENIED = "permission_denied"
    FOREST_NOT_FOUND = "forest_not_found"
    ERROR = "error"


@dataclass
class SummonResult:
    """Результат созыва"""
    status: SummonStatus
    message: str
    total_members: int = 0
    notified_members: int = 0
    batches_sent: int = 0
    errors: List[str] = None
    cooldown_remaining: int = 0  # минуты до следующего созыва


class SummonSystem:
    """Система созыва участников леса"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.forest_manager = get_forest_manager()
        self.cooldowns: Dict[Tuple[int, str], datetime] = {}  # (user_id, forest_id) -> last_call_time
        self.member_cooldowns: Dict[Tuple[int, str], datetime] = {}  # (user_id, forest_id) -> last_notified_time
    
    def _check_invoker_permissions(self, invoker_id: int, forest_id: str, config: ForestConfig) -> bool:
        """Проверяет права вызывающего на созыв"""
        if config.allowed_invokers == "admins":
            # Здесь нужно проверить права администратора
            # Пока разрешаем всем создателям лесов
            session = get_db_session()
            try:
                forest = session.query(Forest).filter(Forest.id == forest_id).first()
                return forest and forest.creator_id == invoker_id
            finally:
                session.close()
        elif config.allowed_invokers == "all":
            return True
        return False
    
    def _check_cooldown(self, invoker_id: int, forest_id: str, cooldown_minutes: int) -> Tuple[bool, int]:
        """Проверяет cooldown для вызывающего"""
        key = (invoker_id, forest_id)
        if key in self.cooldowns:
            last_call = self.cooldowns[key]
            time_since_last_call = datetime.utcnow() - last_call
            cooldown_duration = timedelta(minutes=cooldown_minutes)
            
            if time_since_last_call < cooldown_duration:
                remaining_minutes = int((cooldown_duration - time_since_last_call).total_seconds() / 60)
                return False, remaining_minutes
        
        self.cooldowns[key] = datetime.utcnow()
        return True, 0
    
    def _check_member_cooldown(self, member_id: int, forest_id: str, cooldown_minutes: int) -> bool:
        """Проверяет cooldown для участника"""
        key = (member_id, forest_id)
        if key in self.member_cooldowns:
            last_notified = self.member_cooldowns[key]
            time_since_last_notification = datetime.utcnow() - last_notified
            cooldown_duration = timedelta(minutes=cooldown_minutes)
            
            if time_since_last_notification < cooldown_duration:
                return False
        
        self.member_cooldowns[key] = datetime.utcnow()
        return True
    
    def _format_mentions(self, members: List[ForestMember]) -> List[str]:
        """Форматирует упоминания участников"""
        mentions = []
        for member in members:
            name = member.first_name or member.username or f"User{member.user_id}"
            # Экранируем HTML-небезопасные символы в имени
            escaped_name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            mentions.append(f'<a href="tg://user?id={member.user_id}">{escaped_name}</a>')
        return mentions
    
    def _format_summon_message(self, config: ForestConfig, mentions: List[str], 
                              game_time: str = "20:00", location: str = "Голосовой канал") -> str:
        """Форматирует сообщение созыва"""
        if config.tone == "mystic":
            if config.include_invite_phrase:
                message = (
                    f"🌲 **СОБРАНИЕ В ЛЕСУ!** 🌲\n\n"
                    f"Мастер призывает вас в свой лес! я приглашаю тебя в свой лес\n\n"
                    f"{' '.join(mentions)}\n\n"
                    f"⏰ Время: {game_time}\n"
                    f"📍 Место: {location}\n\n"
                    f"{config.default_cta}"
                )
            else:
                message = (
                    f"🌲 **СОБРАНИЕ В ЛЕСУ!** 🌲\n\n"
                    f"Мастер призывает вас в свой лес!\n\n"
                    f"{' '.join(mentions)}\n\n"
                    f"⏰ Время: {game_time}\n"
                    f"📍 Место: {location}\n\n"
                    f"{config.default_cta}"
                )
        elif config.tone == "thematic":
            message = (
                f"🌲 **СОБРАНИЕ В ЛЕСУ!** 🌲\n\n"
                f"Время для игры в Лес и Волки!\n\n"
                f"{' '.join(mentions)}\n\n"
                f"⏰ Время: {game_time}\n"
                f"📍 Место: {location}\n\n"
                f"{config.default_cta}"
            )
        elif config.tone == "mob":
            message = (
                f"🌲 **СОБРАНИЕ!** 🌲\n\n"
                f"Все в лес! Играем!\n\n"
                f"{' '.join(mentions)}\n\n"
                f"⏰ {game_time} | 📍 {location}\n\n"
                f"{config.default_cta}"
            )
        else:  # neutral
            message = (
                f"🌲 **Созыв участников** 🌲\n\n"
                f"Приглашаем к игре:\n\n"
                f"{' '.join(mentions)}\n\n"
                f"⏰ Время: {game_time}\n"
                f"📍 Место: {location}\n\n"
                f"{config.default_cta}"
            )
        
        return message
    
    async def summon_forest_members(self, forest_id: str, invoker_id: int, chat_id: int, 
                                  config: ForestConfig, game_time: str = "20:00", 
                                  location: str = "Голосовой канал") -> SummonResult:
        """Созывает участников леса с батчингом"""
        try:
            # Проверяем права вызывающего
            if not self._check_invoker_permissions(invoker_id, forest_id, config):
                return SummonResult(
                    status=SummonStatus.PERMISSION_DENIED,
                    message="❌ У вас нет прав для созыва участников этого леса."
                )
            
            # Проверяем cooldown вызывающего
            can_summon, cooldown_remaining = self._check_cooldown(
                invoker_id, forest_id, config.cooldown_minutes
            )
            if not can_summon:
                return SummonResult(
                    status=SummonStatus.COOLDOWN,
                    message=f"⏰ Слишком частые вызовы. Подождите {cooldown_remaining} минут.",
                    cooldown_remaining=cooldown_remaining
                )
            
            # Получаем участников леса
            members = await self.forest_manager.get_forest_members(forest_id)
            if not members:
                return SummonResult(
                    status=SummonStatus.NO_MEMBERS,
                    message="❌ В лесу нет участников."
                )
            
            # Фильтруем участников по cooldown и opt-in
            now = datetime.utcnow()
            available_members = []
            
            for member in members:
                # Проверяем opt-in
                if not member.is_opt_in:
                    continue
                
                # Проверяем cooldown участника
                if not self._check_member_cooldown(member.user_id, forest_id, config.cooldown_minutes):
                    continue
                
                available_members.append(member)
            
            if not available_members:
                return SummonResult(
                    status=SummonStatus.NO_AVAILABLE,
                    message="❌ Нет доступных участников для созыва (все на cooldown)."
                )
            
            # Разбиваем на батчи
            batches = []
            for i in range(0, len(available_members), config.batch_size):
                batch = available_members[i:i + config.batch_size]
                batches.append(batch)
            
            # Отправляем сообщения
            results = {
                "total_members": len(available_members),
                "notified_members": 0,
                "batches_sent": 0,
                "errors": []
            }
            
            for batch in batches:
                try:
                    # Формируем упоминания
                    mentions = self._format_mentions(batch)
                    
                    # Формируем сообщение
                    message_text = self._format_summon_message(config, mentions, game_time, location)
                    
                    # Создаем клавиатуру
                    keyboard = [
                        [
                            InlineKeyboardButton("🌲 Присоединиться", callback_data=f"join_forest_{forest_id}"),
                            InlineKeyboardButton("❌ Отказаться", callback_data=f"decline_forest_{forest_id}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Отправляем сообщение
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=message_text,
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
                    
                    # Обновляем last_called для участников в БД
                    session = get_db_session()
                    try:
                        for member in batch:
                            member.last_called = now
                        session.commit()
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении last_called: {e}")
                        results["errors"].append(f"Ошибка обновления БД: {e}")
                    finally:
                        session.close()
                    
                    results["batches_sent"] += 1
                    results["notified_members"] += len(batch)
                    
                    # Пауза между батчами (500ms)
                    if len(batches) > 1:
                        await asyncio.sleep(0.5)
                        
                except TelegramError as e:
                    error_msg = f"Ошибка Telegram при отправке батча: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                except Exception as e:
                    error_msg = f"Ошибка при отправке батча: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            # Формируем сообщение о результате
            if results["errors"]:
                message = (
                    f"🌲 **Созыв завершен с ошибками** 🌲\n\n"
                    f"**Уведомлено участников:** {results['notified_members']}\n"
                    f"**Отправлено батчей:** {results['batches_sent']}\n"
                    f"**Всего участников в лесу:** {results['total_members']}\n"
                    f"**Ошибок:** {len(results['errors'])}"
                )
            else:
                message = (
                    f"🌲 **Созыв завершен успешно!** 🌲\n\n"
                    f"**Уведомлено участников:** {results['notified_members']}\n"
                    f"**Отправлено батчей:** {results['batches_sent']}\n"
                    f"**Всего участников в лесу:** {results['total_members']}"
                )
            
            return SummonResult(
                status=SummonStatus.SUCCESS,
                message=message,
                total_members=results["total_members"],
                notified_members=results["notified_members"],
                batches_sent=results["batches_sent"],
                errors=results["errors"]
            )
            
        except Exception as e:
            logger.error(f"Критическая ошибка при созыве участников: {e}")
            return SummonResult(
                status=SummonStatus.ERROR,
                message=f"❌ Критическая ошибка при созыве: {e}",
                errors=[str(e)]
            )
    
    async def send_private_invite(self, forest_id: str, from_user_id: int, to_user_id: int, 
                                config: ForestConfig) -> bool:
        """Отправляет персональное приглашение в лес"""
        try:
            # Получаем информацию о приглашающем
            session = get_db_session()
            try:
                from_member = session.query(ForestMember).filter(
                    ForestMember.forest_id == forest_id,
                    ForestMember.user_id == from_user_id
                ).first()
                
                if not from_member:
                    return False
                
                from_name = from_member.first_name or from_member.username or "Неизвестный"
                
            finally:
                session.close()
            
            # Формируем сообщение приглашения
            if config.include_invite_phrase:
                message = (
                    f"🌲 Привет, {{TARGET}}!\n\n"
                    f"{from_name} я приглашаю тебя в свой лес - {config.name}. "
                    f"Готов к мистическим испытаниям?"
                )
            else:
                message = (
                    f"🌲 Привет, {{TARGET}}!\n\n"
                    f"{from_name} приглашает тебя в лес - {config.name}. "
                    f"Готов к мистическим испытаниям?"
                )
            
            # Создаем клавиатуру
            keyboard = [
                [
                    InlineKeyboardButton("✅ Принять приглашение", callback_data=f"accept_invite_{forest_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_invite_{forest_id}")
                ],
                [InlineKeyboardButton("ℹ️ Узнать больше", callback_data=f"ask_info_{forest_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение
            await self.bot.send_message(
                chat_id=to_user_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            # Сохраняем приглашение в БД
            session = get_db_session()
            try:
                from database import ForestInvite
                invite = ForestInvite(
                    forest_id=forest_id,
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    expires_at=datetime.utcnow() + timedelta(hours=24)
                )
                session.add(invite)
                session.commit()
            finally:
                session.close()
            
            return True
            
        except TelegramError as e:
            logger.error(f"Ошибка Telegram при отправке приглашения: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при отправке персонального приглашения: {e}")
            return False
    
    def get_cooldown_status(self, user_id: int, forest_id: str, cooldown_minutes: int) -> Tuple[bool, int]:
        """Получает статус cooldown для пользователя"""
        return self._check_cooldown(user_id, forest_id, cooldown_minutes)
    
    def get_member_cooldown_status(self, member_id: int, forest_id: str, cooldown_minutes: int) -> bool:
        """Получает статус cooldown для участника"""
        return self._check_member_cooldown(member_id, forest_id, cooldown_minutes)


# Глобальный экземпляр системы созыва
summon_system: Optional[SummonSystem] = None

def init_summon_system(bot: Bot) -> SummonSystem:
    """Инициализирует систему созыва"""
    global summon_system
    summon_system = SummonSystem(bot)
    return summon_system

def get_summon_system() -> SummonSystem:
    """Получает экземпляр системы созыва"""
    if summon_system is None:
        raise RuntimeError("Система созыва не инициализирована")
    return summon_system
