#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Система управления лесами для бота "Лес и Волки"
Позволяет создавать леса, управлять участниками и созывать их
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from database import get_db_session, Forest, ForestMember, ForestInvite, ForestSetting

logger = logging.getLogger(__name__)


class ForestPrivacy(Enum):
    """Типы приватности леса"""
    PUBLIC = "public"
    PRIVATE = "private"


class InviteStatus(Enum):
    """Статусы приглашений"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


@dataclass
class ForestConfig:
    """Конфигурация леса"""
    forest_id: str
    name: str
    creator_id: int
    description: str
    privacy: ForestPrivacy
    max_size: Optional[int]
    created_at: datetime
    batch_size: int = 6
    cooldown_minutes: int = 30
    allowed_invokers: str = "admins"
    include_invite_phrase: bool = True
    default_cta: str = "Играть"
    tone: str = "mystic"
    max_length: int = 400


# Модели лесов импортированы из database.py


class ForestManager:
    """Менеджер лесов"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.cooldowns: Dict[Tuple[int, str], datetime] = {}  # (user_id, forest_id) -> last_call_time
    
    def _generate_forest_id(self, name: str) -> str:
        """Генерирует ID леса из названия"""
        # Убираем все кроме букв, цифр и пробелов
        clean_name = re.sub(r'[^\w\s]', '', name.lower())
        # Заменяем пробелы на подчеркивания
        return re.sub(r'\s+', '_', clean_name.strip())
    
    def _escape_html(self, text: str) -> str:
        """Экранирует HTML-небезопасные символы"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;'))
    
    async def create_forest(self, creator_id: int, name: str, description: str, 
                          privacy: str = "public", max_size: Optional[int] = None,
                          **kwargs) -> ForestConfig:
        """Создает новый лес"""
        forest_id = self._generate_forest_id(name)
        
        # Проверяем, не существует ли уже лес с таким ID
        session = get_db_session()
        try:
            existing_forest = session.query(Forest).filter(Forest.id == forest_id).first()
            if existing_forest:
                # Добавляем суффикс если лес уже существует
                counter = 1
                while session.query(Forest).filter(Forest.id == f"{forest_id}_{counter}").first():
                    counter += 1
                forest_id = f"{forest_id}_{counter}"
            
            # Создаем лес
            forest = Forest(
                id=forest_id,
                name=self._escape_html(name),
                creator_id=creator_id,
                description=self._escape_html(description),
                privacy=privacy,
                max_size=max_size
            )
            
            session.add(forest)
            session.commit()
            
            # Создаем конфигурацию
            config = ForestConfig(
                forest_id=forest_id,
                name=name,
                creator_id=creator_id,
                description=description,
                privacy=ForestPrivacy(privacy),
                max_size=max_size,
                created_at=forest.created_at,
                **kwargs
            )
            
            logger.info(f"Создан лес '{name}' (ID: {forest_id}) пользователем {creator_id}")
            return config
            
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при создании леса: {e}")
            raise
        finally:
            session.close()
    
    async def join_forest(self, forest_id: str, user_id: int, username: str = None, 
                         first_name: str = None) -> bool:
        """Присоединяет пользователя к лесу"""
        session = get_db_session()
        try:
            # Проверяем существование леса
            forest = session.query(Forest).filter(Forest.id == forest_id).first()
            if not forest:
                return False
            
            # Проверяем лимит участников
            if forest.max_size and len(forest.members) >= forest.max_size:
                return False
            
            # Проверяем, не состоит ли уже пользователь в лесу
            existing_member = session.query(ForestMember).filter(
                ForestMember.forest_id == forest_id,
                ForestMember.user_id == user_id
            ).first()
            
            if existing_member:
                return False
            
            # Добавляем участника
            member = ForestMember(
                forest_id=forest_id,
                user_id=user_id,
                username=username,
                first_name=first_name
            )
            
            session.add(member)
            session.commit()
            
            logger.info(f"Пользователь {user_id} присоединился к лесу {forest_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при присоединении к лесу: {e}")
            return False
        finally:
            session.close()
    
    async def leave_forest(self, forest_id: str, user_id: int) -> bool:
        """Покидает лес"""
        session = get_db_session()
        try:
            member = session.query(ForestMember).filter(
                ForestMember.forest_id == forest_id,
                ForestMember.user_id == user_id
            ).first()
            
            if not member:
                return False
            
            session.delete(member)
            session.commit()
            
            logger.info(f"Пользователь {user_id} покинул лес {forest_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при покидании леса: {e}")
            return False
        finally:
            session.close()
    
    async def get_forest_members(self, forest_id: str) -> List[ForestMember]:
        """Получает список участников леса"""
        session = get_db_session()
        try:
            members = session.query(ForestMember).filter(
                ForestMember.forest_id == forest_id
            ).all()
            return members
        except Exception as e:
            logger.error(f"Ошибка при получении участников леса: {e}")
            return []
        finally:
            session.close()
    
    async def get_forest_info(self, forest_id: str) -> Optional[Forest]:
        """Получает информацию о лесе"""
        session = get_db_session()
        try:
            forest = session.query(Forest).filter(Forest.id == forest_id).first()
            return forest
        except Exception as e:
            logger.error(f"Ошибка при получении информации о лесе: {e}")
            return None
        finally:
            session.close()
    
    def _check_cooldown(self, user_id: int, forest_id: str, cooldown_minutes: int) -> bool:
        """Проверяет cooldown для пользователя"""
        key = (user_id, forest_id)
        if key in self.cooldowns:
            last_call = self.cooldowns[key]
            if datetime.utcnow() - last_call < timedelta(minutes=cooldown_minutes):
                return False
        
        self.cooldowns[key] = datetime.utcnow()
        return True
    
    async def summon_forest_members(self, forest_id: str, invoker_id: int, 
                                  chat_id: int, config: ForestConfig) -> Dict[str, Any]:
        """Созывает участников леса"""
        # Проверяем права
        if config.allowed_invokers == "admins":
            # Здесь нужно проверить права администратора
            # Пока пропускаем проверку
            pass
        
        # Проверяем cooldown
        if not self._check_cooldown(invoker_id, forest_id, config.cooldown_minutes):
            return {"success": False, "error": "cooldown", "message": "Слишком частые вызовы"}
        
        # Получаем участников леса
        members = await self.get_forest_members(forest_id)
        if not members:
            return {"success": False, "error": "no_members", "message": "В лесу нет участников"}
        
        # Фильтруем по cooldown и opt-in
        now = datetime.utcnow()
        available_members = []
        
        for member in members:
            # Проверяем opt-in
            if not member.is_opt_in:
                continue
            
            # Проверяем cooldown участника
            if member.last_called:
                time_since_last_call = now - member.last_called
                if time_since_last_call < timedelta(minutes=config.cooldown_minutes):
                    continue
            
            available_members.append(member)
        
        if not available_members:
            return {"success": False, "error": "no_available", "message": "Нет доступных участников"}
        
        # Разбиваем на батчи
        batches = []
        for i in range(0, len(available_members), config.batch_size):
            batch = available_members[i:i + config.batch_size]
            batches.append(batch)
        
        # Отправляем сообщения
        results = {
            "success": True,
            "total_members": len(available_members),
            "batches_sent": 0,
            "members_notified": 0,
            "errors": []
        }
        
        for batch in batches:
            try:
                # Формируем упоминания
                mentions = []
                for member in batch:
                    name = member.first_name or member.username or f"User{member.user_id}"
                    mentions.append(f'<a href="tg://user?id={member.user_id}">{self._escape_html(name)}</a>')
                
                # Формируем сообщение
                message_text = self._format_summon_message(config, mentions)
                
                # Отправляем сообщение
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode='HTML'
                )
                
                # Обновляем last_called для участников
                session = get_db_session()
                try:
                    for member in batch:
                        member.last_called = now
                    session.commit()
                except Exception as e:
                    logger.error(f"Ошибка при обновлении last_called: {e}")
                finally:
                    session.close()
                
                results["batches_sent"] += 1
                results["members_notified"] += len(batch)
                
                # Пауза между батчами
                if len(batches) > 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Ошибка при отправке батча: {e}")
                results["errors"].append(str(e))
        
        return results
    
    def _format_summon_message(self, config: ForestConfig, mentions: List[str]) -> str:
        """Форматирует сообщение созыва"""
        if config.tone == "mystic":
            if config.include_invite_phrase:
                message = (
                    f"🌲 **СОБРАНИЕ В ЛЕСУ!** 🌲\n\n"
                    f"Мастер призывает вас в свой лес! я приглашаю тебя в свой лес\n\n"
                    f"{' '.join(mentions)}\n\n"
                    f"⏰ Время: {{GAME_TIME}}\n"
                    f"📍 Место: {{LOCATION}}\n\n"
                    f"{config.default_cta}"
                )
            else:
                message = (
                    f"🌲 **СОБРАНИЕ В ЛЕСУ!** 🌲\n\n"
                    f"Мастер призывает вас в свой лес!\n\n"
                    f"{' '.join(mentions)}\n\n"
                    f"⏰ Время: {{GAME_TIME}}\n"
                    f"📍 Место: {{LOCATION}}\n\n"
                    f"{config.default_cta}"
                )
        else:
            # Другие тона можно добавить позже
            message = f"🌲 **СОБРАНИЕ В ЛЕСУ!** 🌲\n\n{' '.join(mentions)}\n\n{config.default_cta}"
        
        return message
    
    async def send_private_invite(self, forest_id: str, from_user_id: int, 
                                to_user_id: int, config: ForestConfig) -> bool:
        """Отправляет персональное приглашение"""
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
                invite = ForestInvite(
                    forest_id=forest_id,
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    expires_at=datetime.utcnow() + timedelta(hours=24)  # Приглашение действует 24 часа
                )
                session.add(invite)
                session.commit()
            finally:
                session.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке персонального приглашения: {e}")
            return False


# Глобальный экземпляр менеджера лесов
forest_manager: Optional[ForestManager] = None

def init_forest_manager(bot: Bot) -> ForestManager:
    """Инициализирует менеджер лесов"""
    global forest_manager
    forest_manager = ForestManager(bot)
    return forest_manager

def get_forest_manager() -> ForestManager:
    """Получает экземпляр менеджера лесов"""
    if forest_manager is None:
        raise RuntimeError("Менеджер лесов не инициализирован")
    return forest_manager
