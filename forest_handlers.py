#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчики команд для системы лесов
Команды управления лесами, участниками и созыва
"""

import logging
from typing import Optional, List
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from forest_system import ForestManager, ForestConfig, ForestPrivacy, get_forest_manager
from database import get_db_session, Forest, ForestMember

logger = logging.getLogger(__name__)

# Глобальный экземпляр менеджера лесов
_forest_manager = None

def get_forest_manager_instance():
    """Получает глобальный экземпляр менеджера лесов"""
    global _forest_manager
    if _forest_manager is None:
        _forest_manager = get_forest_manager()
    return _forest_manager


# Функции-обработчики команд для прямого использования
async def handle_create_forest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды создания леса"""
    logger.info(f"🌲 handle_create_forest: Команда /create_forest от пользователя {update.effective_user.id}")
    try:
        forest_manager = get_forest_manager_instance()
        handlers = ForestCommandHandlers(forest_manager)
        await handlers.handle_create_forest(update, context)
    except Exception as e:
        logger.error(f"❌ handle_create_forest: Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при создании леса. Попробуйте позже.")

async def handle_join_forest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды присоединения к лесу"""
    logger.info(f"🌲 handle_join_forest: Команда от пользователя {update.effective_user.id}")
    try:
        forest_manager = get_forest_manager_instance()
        handlers = ForestCommandHandlers(forest_manager)
        await handlers.handle_join_forest(update, context)
    except Exception as e:
        logger.error(f"❌ handle_join_forest: Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при присоединении к лесу. Попробуйте позже.")

async def handle_leave_forest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды выхода из леса"""
    logger.info(f"🌲 handle_leave_forest: Команда от пользователя {update.effective_user.id}")
    try:
        forest_manager = get_forest_manager_instance()
        handlers = ForestCommandHandlers(forest_manager)
        await handlers.handle_leave_forest(update, context)
    except Exception as e:
        logger.error(f"❌ handle_leave_forest: Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при выходе из леса. Попробуйте позже.")

async def handle_forests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды списка лесов"""
    logger.info(f"🌲 handle_forests: Команда /forests от пользователя {update.effective_user.id}")
    try:
        forest_manager = get_forest_manager_instance()
        handlers = ForestCommandHandlers(forest_manager)
        await handlers.handle_forests(update, context)
    except Exception as e:
        logger.error(f"❌ handle_forests: Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при получении списка лесов. Попробуйте позже.")

async def handle_my_forests_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды профиля моих лесов"""
    logger.info(f"🌲 handle_my_forests_profile: Команда /my_forests_profile от пользователя {update.effective_user.id}")
    try:
        forest_manager = get_forest_manager_instance()
        handlers = ForestCommandHandlers(forest_manager)
        await handlers.handle_my_forests_profile(update, context)
    except Exception as e:
        logger.error(f"❌ handle_my_forests_profile: Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при получении профиля лесов. Попробуйте позже.")

async def handle_forest_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды профиля леса"""
    logger.info(f"🌲 handle_forest_profile: Команда /forest_profile от пользователя {update.effective_user.id}")
    try:
        forest_manager = get_forest_manager_instance()
        handlers = ForestCommandHandlers(forest_manager)
        await handlers.handle_forest_profile(update, context)
    except Exception as e:
        logger.error(f"❌ handle_forest_profile: Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при получении профиля леса. Попробуйте позже.")

async def handle_forest_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды аналитики леса"""
    logger.info(f"🌲 handle_forest_analytics: Команда /forest_analytics от пользователя {update.effective_user.id}")
    try:
        forest_manager = get_forest_manager_instance()
        handlers = ForestCommandHandlers(forest_manager)
        await handlers.handle_forest_analytics(update, context)
    except Exception as e:
        logger.error(f"❌ handle_forest_analytics: Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при получении аналитики леса. Попробуйте позже.")

async def handle_top_forests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды топа лесов"""
    logger.info(f"🌲 handle_top_forests: Команда /top_forests от пользователя {update.effective_user.id}")
    try:
        forest_manager = get_forest_manager_instance()
        handlers = ForestCommandHandlers(forest_manager)
        await handlers.handle_top_forests(update, context)
    except Exception as e:
        logger.error(f"❌ handle_top_forests: Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при получении топа лесов. Попробуйте позже.")

async def handle_help_forests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды справки по лесам"""
    logger.info(f"🌲 handle_help_forests: Команда /help_forests от пользователя {update.effective_user.id}")
    try:
        forest_manager = get_forest_manager_instance()
        handlers = ForestCommandHandlers(forest_manager)
        await handlers.handle_help_forests(update, context)
    except Exception as e:
        logger.error(f"❌ handle_help_forests: Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при получении справки. Попробуйте позже.")

async def handle_summon_forest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды созыва леса"""
    logger.info(f"🌲 handle_summon_forest: Команда от пользователя {update.effective_user.id}")
    try:
        forest_manager = get_forest_manager_instance()
        handlers = ForestCommandHandlers(forest_manager)
        await handlers.handle_summon_forest(update, context)
    except Exception as e:
        logger.error(f"❌ handle_summon_forest: Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при созыве леса. Попробуйте позже.")


class ForestCommandHandlers:
    """Обработчики команд для системы лесов"""
    
    def __init__(self, forest_manager: ForestManager):
        self.forest_manager = forest_manager
    
    async def handle_create_forest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды создания леса"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Проверяем аргументы команды
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "🌲 <b>Создание леса</b> 🌲\n\n"
                "Использование: /create_forest <название> <описание>\n"
                "Пример: /create_forest Лес Волков Еженедельные игры в мафию\n\n"
                "Дополнительные параметры:\n"
                "• --private - приватный лес (только по приглашениям)\n"
                "• --max <число> - максимальное количество участников\n"
                "• --batch <число> - размер батча для созыва (по умолчанию 6)\n"
                "• --cooldown <минуты> - cooldown между вызовами (по умолчанию 30)"
            )
            return
        
        # Парсим аргументы
        args = context.args
        forest_name = args[0]
        description = " ".join(args[1:])
        
        # Парсим дополнительные параметры
        privacy = "public"
        max_size = None
        batch_size = 6
        cooldown_minutes = 30
        
        i = 0
        while i < len(args):
            if args[i] == "--private":
                privacy = "private"
            elif args[i] == "--max" and i + 1 < len(args):
                try:
                    max_size = int(args[i + 1])
                    i += 1
                except ValueError:
                    await update.message.reply_text("❌ Неверное значение для --max")
                    return
            elif args[i] == "--batch" and i + 1 < len(args):
                try:
                    batch_size = int(args[i + 1])
                    i += 1
                except ValueError:
                    await update.message.reply_text("❌ Неверное значение для --batch")
                    return
            elif args[i] == "--cooldown" and i + 1 < len(args):
                try:
                    cooldown_minutes = int(args[i + 1])
                    i += 1
                except ValueError:
                    await update.message.reply_text("❌ Неверное значение для --cooldown")
                    return
            i += 1
        
        try:
            # Создаем лес
            config = await self.forest_manager.create_forest(
                creator_id=user.id,
                name=forest_name,
                description=description,
                privacy=privacy,
                max_size=max_size,
                batch_size=batch_size,
                cooldown_minutes=cooldown_minutes,
                allowed_invokers="admins",
                include_invite_phrase=True,
                default_cta="Играть",
                tone="mystic",
                max_length=400
            )
            
            # Создаем клавиатуру
            keyboard = [
                [
                    InlineKeyboardButton("🌲 Присоединиться", callback_data=f"join_forest_{config.forest_id}"),
                    InlineKeyboardButton("ℹ️ Информация", callback_data=f"forest_info_{config.forest_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение о создании
            message = (
                f"🌲 <b>Лес создан!</b> 🌲\n\n"
                f"<b>Название:</b> {config.name}\n"
                f"<b>Описание:</b> {config.description}\n"
                f"<b>Приватность:</b> {'Приватный' if config.privacy == ForestPrivacy.PRIVATE else 'Публичный'}\n"
                f"<b>Максимум участников:</b> {config.max_size or 'Без лимита'}\n"
                f"<b>Размер батча:</b> {config.batch_size}\n"
                f"<b>Cooldown:</b> {config.cooldown_minutes} мин\n\n"
                f"<b>Команды леса:</b>\n"
                f"• /join_forest_{config.forest_id} - присоединиться\n"
                f"• /summon_forest_{config.forest_id} - созвать участников\n"
                f"• /list_forest_{config.forest_id} - список участников\n"
                f"• /invite_forest_{config.forest_id} @username - пригласить"
            )
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Ошибка при создании леса: {e}")
            await update.message.reply_text("❌ Ошибка при создании леса. Попробуйте позже.")
    
    async def handle_join_forest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды присоединения к лесу"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Получаем ID леса из команды
        command = update.message.text
        if not command.startswith('/join_forest_'):
            await update.message.reply_text("❌ Неверная команда")
            return
        
        forest_id_str = command.replace('/join_forest_', '')
        
        try:
            # Преобразуем ID в число
            forest_id = int(forest_id_str)
            
            # Присоединяемся к лесу
            success = await self.forest_manager.join_forest(
                forest_id=forest_id,
                user_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            
            if success:
                # Получаем информацию о лесе
                forest = await self.forest_manager.get_forest_info(forest_id)
                if forest:
                    members = await self.forest_manager.get_forest_members(forest_id)
                    member_count = len(members)
                    max_count = forest.max_size or "∞"
                    
                    message = (
                        f"🌲 <b>Добро пожаловать в лес!</b> 🌲\n\n"
                        f"<b>Лес:</b> {forest.name}\n"
                        f"<b>Описание:</b> {forest.description}\n"
                        f"<b>Участников:</b> {member_count}/{max_count}\n\n"
                        f"Теперь вы будете получать уведомления о созывах!"
                    )
                else:
                    message = "✅ Вы успешно присоединились к лесу!"
                
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                await update.message.reply_text("❌ Не удалось присоединиться к лесу. Возможно, лес не существует или достиг лимита участников.")
                
        except Exception as e:
            logger.error(f"Ошибка при присоединении к лесу: {e}")
            await update.message.reply_text("❌ Ошибка при присоединении к лесу.")
    
    async def handle_leave_forest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды покидания леса"""
        user = update.effective_user
        
        # Получаем ID леса из команды
        command = update.message.text
        if not command.startswith('/leave_forest_'):
            await update.message.reply_text("❌ Неверная команда")
            return
        
        forest_id_str = command.replace('/leave_forest_', '')
        
        try:
            # Преобразуем ID в число
            forest_id = int(forest_id_str)
            success = await self.forest_manager.leave_forest(forest_id, user.id)
            
            if success:
                await update.message.reply_text("👋 Вы покинули лес. Больше не будете получать уведомления о созывах.")
            else:
                await update.message.reply_text("❌ Вы не состоите в этом лесу.")
                
        except Exception as e:
            logger.error(f"Ошибка при покидании леса: {e}")
            await update.message.reply_text("❌ Ошибка при покидании леса.")
    
    async def handle_summon_forest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды созыва участников леса"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Получаем ID леса из команды
        command = update.message.text
        if not command.startswith('/summon_forest_'):
            await update.message.reply_text("❌ Неверная команда")
            return
        
        forest_id_str = command.replace('/summon_forest_', '')
        
        try:
            # Преобразуем ID в число
            forest_id = int(forest_id_str)
            
            # Получаем информацию о лесе
            forest = await self.forest_manager.get_forest_info(forest_id)
            if not forest:
                await update.message.reply_text("❌ Лес не найден.")
                return
            
            # Создаем конфигурацию леса
            config = ForestConfig(
                forest_id=forest_id,
                name=forest.name,
                creator_id=forest.creator_id,
                description=forest.description,
                privacy=ForestPrivacy(forest.privacy),
                max_size=forest.max_size,
                created_at=forest.created_at,
                batch_size=6,
                cooldown_minutes=30,
                allowed_invokers="admins",
                include_invite_phrase=True,
                default_cta="Играть",
                tone="mystic",
                max_length=400
            )
            
            # Созываем участников
            result = await self.forest_manager.summon_forest_members(
                forest_id=forest_id,
                invoker_id=user.id,
                chat_id=chat_id,
                config=config
            )
            
            if result["success"]:
                message = (
                    f"🌲 <b>Созыв завершен!</b> 🌲\n\n"
                    f"<b>Уведомлено участников:</b> {result['members_notified']}\n"
                    f"<b>Отправлено батчей:</b> {result['batches_sent']}\n"
                    f"<b>Всего участников в лесу:</b> {result['total_members']}"
                )
                
                if result["errors"]:
                    message += f"\n\n<b>Ошибки:</b> {len(result['errors'])}"
                
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                error_messages = {
                    "cooldown": "⏰ Слишком частые вызовы. Подождите перед следующим созывом.",
                    "no_members": "❌ В лесу нет участников.",
                    "no_available": "❌ Нет доступных участников для созыва (все на cooldown)."
                }
                
                error_msg = error_messages.get(result.get("error", "unknown"), "❌ Ошибка при созыве участников.")
                await update.message.reply_text(error_msg)
                
        except ValueError:
            logger.error(f"❌ handle_summon_forest: Неверный ID леса: {forest_id_str}")
            await update.message.reply_text("❌ Неверный ID леса. Используйте числовой ID.")
        except Exception as e:
            logger.error(f"Ошибка при созыве участников: {e}")
            await update.message.reply_text("❌ Ошибка при созыве участников.")
    
    async def handle_list_forest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды показа списка участников леса"""
        # Получаем ID леса из команды
        command = update.message.text
        if not command.startswith('/list_forest_'):
            await update.message.reply_text("❌ Неверная команда")
            return
        
        forest_id_str = command.replace('/list_forest_', '')
        
        try:
            # Преобразуем ID в число
            forest_id = int(forest_id_str)
            # Получаем информацию о лесе
            forest = await self.forest_manager.get_forest_info(forest_id)
            if not forest:
                await update.message.reply_text("❌ Лес не найден.")
                return
            
            # Получаем участников
            members = await self.forest_manager.get_forest_members(forest_id)
            
            if not members:
                await update.message.reply_text("🌲 В лесу пока нет участников.")
                return
            
            # Формируем список участников
            member_list = []
            for i, member in enumerate(members, 1):
                name = member.first_name or member.username or f"User{member.user_id}"
                status = "🟢" if member.is_opt_in else "🔴"
                member_list.append(f"{i}. {status} {name}")
            
            message = (
                f"🌲 <b>Участники леса \"{forest.name}\"</b> 🌲\n\n"
                f"<b>Описание:</b> {forest.description}\n"
                f"<b>Участников:</b> {len(members)}/{forest.max_size or '∞'}\n"
                f"<b>Приватность:</b> {'Приватный' if forest.privacy == 'private' else 'Публичный'}\n\n"
                f"<b>Список участников:</b>\n" + "\n".join(member_list) + "\n\n"
                f"🟢 - получает уведомления\n"
                f"🔴 - не получает уведомления"
            )
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка участников: {e}")
            await update.message.reply_text("❌ Ошибка при получении списка участников.")
    
    async def handle_invite_forest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды приглашения в лес"""
        user = update.effective_user
        
        # Получаем ID леса из команды
        command = update.message.text
        if not command.startswith('/invite_forest_'):
            await update.message.reply_text("❌ Неверная команда")
            return
        
        forest_id_str = command.replace('/invite_forest_', '')
        
        try:
            # Преобразуем ID в число
            forest_id = int(forest_id_str)
        except ValueError:
            await update.message.reply_text("❌ Неверный ID леса. Используйте числовой ID.")
            return
        
        # Проверяем аргументы
        if not context.args:
            await update.message.reply_text(
                "🌲 <b>Приглашение в лес</b> 🌲\n\n"
                "Использование: /invite_forest_<id> @username\n"
                "Пример: /invite_forest_les_i_volki @username"
            )
            return
        
        # Получаем username
        username = context.args[0]
        if not username.startswith('@'):
            username = f"@{username}"
        
        try:
            # Получаем информацию о лесе
            forest = await self.forest_manager.get_forest_info(forest_id)
            if not forest:
                await update.message.reply_text("❌ Лес не найден.")
                return
            
            # Создаем конфигурацию
            config = ForestConfig(
                forest_id=forest_id,
                name=forest.name,
                creator_id=forest.creator_id,
                description=forest.description,
                privacy=ForestPrivacy(forest.privacy),
                max_size=forest.max_size,
                created_at=forest.created_at,
                include_invite_phrase=True,
                tone="mystic"
            )
            
            # Отправляем приглашение (здесь нужно получить user_id по username)
            # Пока просто показываем сообщение
            message = (
                f"🌲 <b>Приглашение отправлено!</b> 🌲\n\n"
                f"Пользователю {username} отправлено приглашение в лес \"{forest.name}\""
            )
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Ошибка при отправке приглашения: {e}")
            await update.message.reply_text("❌ Ошибка при отправке приглашения.")


class ForestCallbackHandlers:
    """Обработчики callback-ов для системы лесов"""
    
    def __init__(self, forest_manager: ForestManager):
        self.forest_manager = forest_manager
    
    async def handle_join_forest_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для присоединения к лесу"""
        query = update.callback_query
        user = update.effective_user
        
        # Получаем ID леса из callback_data
        callback_data = query.data
        if not callback_data.startswith('join_forest_'):
            return
        
        forest_id_str = callback_data.replace('join_forest_', '')
        
        try:
            # Преобразуем ID в число
            forest_id = int(forest_id_str)
            
            # Присоединяемся к лесу
            success = await self.forest_manager.join_forest(
                forest_id=forest_id,
                user_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            
            if success:
                await query.answer("✅ Вы присоединились к лесу!")
                await query.edit_message_text(
                    query.message.text + f"\n\n✅ {user.first_name} присоединился к лесу!"
                )
            else:
                await query.answer("❌ Не удалось присоединиться к лесу")
                
        except ValueError:
            logger.error(f"❌ handle_join_forest_callback: Неверный ID леса: {forest_id_str}")
            await query.answer("❌ Неверный ID леса")
        except Exception as e:
            logger.error(f"Ошибка при обработке callback присоединения: {e}")
            await query.answer("❌ Ошибка при присоединении к лесу")
    
    async def handle_forest_info_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для информации о лесе"""
        query = update.callback_query
        user = update.effective_user
        
        # Получаем ID леса из callback_data
        callback_data = query.data
        if not callback_data.startswith('forest_info_'):
            return
        
        forest_id_str = callback_data.replace('forest_info_', '')
        
        try:
            # Преобразуем ID в число
            forest_id = int(forest_id_str)
            # Получаем информацию о лесе
            forest = await self.forest_manager.get_forest_info(forest_id)
            if not forest:
                await query.answer("❌ Лес не найден")
                return
            
            # Получаем участников
            members = await self.forest_manager.get_forest_members(forest_id)
            
            message = (
                f"🌲 <b>Информация о лесе</b> 🌲\n\n"
                f"<b>Название:</b> {forest.name}\n"
                f"<b>Описание:</b> {forest.description}\n"
                f"<b>Приватность:</b> {'Приватный' if forest.privacy == 'private' else 'Публичный'}\n"
                f"<b>Участников:</b> {len(members)}/{forest.max_size or '∞'}\n"
                f"<b>Создан:</b> {forest.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"<b>Команды:</b>\n"
                f"• /join_forest_{forest_id} - присоединиться\n"
                f"• /summon_forest_{forest_id} - созвать участников\n"
                f"• /list_forest_{forest_id} - список участников"
            )
            
            await query.edit_message_text(message)
            await query.answer()
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о лесе: {e}")
            await query.answer("❌ Ошибка при получении информации")
    
    async def handle_accept_invite_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для принятия приглашения"""
        query = update.callback_query
        user = update.effective_user
        
        # Получаем ID леса из callback_data
        callback_data = query.data
        if not callback_data.startswith('accept_invite_'):
            return
        
        forest_id_str = callback_data.replace('accept_invite_', '')
        
        try:
            # Преобразуем ID в число
            forest_id = int(forest_id_str)
            # Присоединяемся к лесу
            success = await self.forest_manager.join_forest(
                forest_id=forest_id,
                user_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            
            if success:
                await query.answer("✅ Приглашение принято! Добро пожаловать в лес!")
                await query.edit_message_text(
                    "🌲 <b>Приглашение принято!</b> 🌲\n\n"
                    "Вы успешно присоединились к лесу и будете получать уведомления о созывах."
                )
            else:
                await query.answer("❌ Не удалось принять приглашение")
                
        except Exception as e:
            logger.error(f"Ошибка при принятии приглашения: {e}")
            await query.answer("❌ Ошибка при принятии приглашения")
    
    async def handle_decline_invite_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для отклонения приглашения"""
        query = update.callback_query
        
        await query.answer("❌ Приглашение отклонено")
        await query.edit_message_text(
            "🌲 <b>Приглашение отклонено</b> 🌲\n\n"
            "Вы отклонили приглашение в лес."
        )
    
    async def handle_ask_info_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback для запроса информации"""
        query = update.callback_query
        
        await query.answer("ℹ️ Информация о лесе")
        await query.edit_message_text(
            "🌲 <b>Информация о лесе</b> 🌲\n\n"
            "Лес - это группа участников, которые получают уведомления о созывах для игры в мафию.\n\n"
            "<b>Возможности:</b>\n"
            "• Получение уведомлений о созывах\n"
            "• Участие в батчевых призывах\n"
            "• Настройка уведомлений\n"
            "• Приглашение друзей\n\n"
            "<b>Команды:</b>\n"
            "• /join_forest_<id> - присоединиться\n"
            "• /leave_forest_<id> - покинуть лес\n"
            "• /list_forest_<id> - список участников"
        )
