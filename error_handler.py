#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчик ошибок для ForestMafia Bot
Заменяет ошибки на алерты вместо изменения сообщений
"""

import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
import traceback

from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Обработчик ошибок"""
    
    def __init__(self):
        self.logger = logger
        self.error_messages = self._load_error_messages()
    
    def _load_error_messages(self) -> Dict[str, str]:
        """Загружает сообщения об ошибках"""
        return {
            "permission_denied": "❌ У вас нет прав для выполнения этого действия",
            "game_not_found": "❌ В этом чате нет активной игры",
            "player_not_found": "❌ Вы не участвуете в игре",
            "invalid_phase": "❌ Это действие недоступно в текущей фазе игры",
            "already_voted": "❌ Вы уже проголосовали",
            "invalid_target": "❌ Неверная цель для действия",
            "insufficient_balance": "❌ Недостаточно средств",
            "database_error": "❌ Ошибка базы данных. Попробуйте позже",
            "network_error": "❌ Ошибка сети. Проверьте подключение",
            "unknown_error": "❌ Произошла неизвестная ошибка",
            "rate_limit": "❌ Слишком много запросов. Подождите немного",
            "maintenance": "❌ Бот находится на техническом обслуживании",
            "feature_disabled": "❌ Эта функция временно отключена",
            "invalid_input": "❌ Неверные данные. Проверьте ввод",
            "game_full": "❌ Игра уже заполнена",
            "game_started": "❌ Игра уже началась",
            "game_ended": "❌ Игра уже завершена",
            "phase_timeout": "❌ Время этапа истекло",
            "action_not_available": "❌ Это действие недоступно",
            "target_protected": "❌ Цель защищена от этого действия"
        }
    
    def get_error_message(self, error_type: str, custom_message: Optional[str] = None) -> str:
        """
        Получает сообщение об ошибке
        
        Args:
            error_type: Тип ошибки
            custom_message: Пользовательское сообщение
            
        Returns:
            str: Сообщение об ошибке
        """
        if custom_message:
            return custom_message
        
        return self.error_messages.get(error_type, self.error_messages["unknown_error"])
    
    async def show_alert(self, query: CallbackQuery, error_type: str, 
                        custom_message: Optional[str] = None, show_alert: bool = True):
        """
        Показывает алерт с ошибкой
        
        Args:
            query: Callback query
            error_type: Тип ошибки
            custom_message: Пользовательское сообщение
            show_alert: Показывать ли алерт
        """
        try:
            message = self.get_error_message(error_type, custom_message)
            await query.answer(message, show_alert=show_alert)
            
            self.logger.warning(f"⚠️ Показан алерт: {error_type} - {message}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка показа алерта: {e}")
            try:
                await query.answer("❌ Произошла ошибка", show_alert=True)
            except:
                pass
    
    async def show_success_alert(self, query: CallbackQuery, message: str, show_alert: bool = True):
        """
        Показывает алерт с успехом
        
        Args:
            query: Callback query
            message: Сообщение об успехе
            show_alert: Показывать ли алерт
        """
        try:
            await query.answer(f"✅ {message}", show_alert=show_alert)
            self.logger.info(f"✅ Показан алерт успеха: {message}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка показа алерта успеха: {e}")
            try:
                await query.answer("✅ Операция выполнена", show_alert=True)
            except:
                pass
    
    async def show_info_alert(self, query: CallbackQuery, message: str, show_alert: bool = True):
        """
        Показывает информационный алерт
        
        Args:
            query: Callback query
            message: Информационное сообщение
            show_alert: Показывать ли алерт
        """
        try:
            await query.answer(f"ℹ️ {message}", show_alert=show_alert)
            self.logger.info(f"ℹ️ Показан информационный алерт: {message}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка показа информационного алерта: {e}")
            try:
                await query.answer("ℹ️ Информация", show_alert=True)
            except:
                pass
    
    def handle_errors(self, error_type: str = "unknown_error", 
                     custom_message: Optional[str] = None,
                     log_error: bool = True):
        """
        Декоратор для обработки ошибок
        
        Args:
            error_type: Тип ошибки по умолчанию
            custom_message: Пользовательское сообщение
            log_error: Логировать ли ошибку
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if log_error:
                        self.logger.error(f"❌ Ошибка в {func.__name__}: {e}")
                        self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
                    
                    # Пытаемся показать алерт если есть query
                    query = None
                    for arg in args:
                        if isinstance(arg, CallbackQuery):
                            query = arg
                            break
                    
                    if query:
                        await self.show_alert(query, error_type, custom_message)
                    
                    return None
            
            return wrapper
        return decorator
    
    def handle_database_errors(self, func: Callable):
        """Декоратор для обработки ошибок базы данных"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"❌ Ошибка БД в {func.__name__}: {e}")
                
                # Пытаемся показать алерт если есть query
                query = None
                for arg in args:
                    if isinstance(arg, CallbackQuery):
                        query = arg
                        break
                
                if query:
                    await self.show_alert(query, "database_error")
                
                return None
        
        return wrapper
    
    def handle_permission_errors(self, func: Callable):
        """Декоратор для обработки ошибок прав доступа"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except PermissionError as e:
                self.logger.warning(f"⚠️ Ошибка прав доступа в {func.__name__}: {e}")
                
                # Пытаемся показать алерт если есть query
                query = None
                for arg in args:
                    if isinstance(arg, CallbackQuery):
                        query = arg
                        break
                
                if query:
                    await self.show_alert(query, "permission_denied")
                
                return None
            except Exception as e:
                self.logger.error(f"❌ Неожиданная ошибка в {func.__name__}: {e}")
                
                # Пытаемся показать алерт если есть query
                query = None
                for arg in args:
                    if isinstance(arg, CallbackQuery):
                        query = arg
                        break
                
                if query:
                    await self.show_alert(query, "unknown_error")
                
                return None
        
        return wrapper
    
    async def handle_callback_error(self, query: CallbackQuery, error: Exception, 
                                   error_type: str = "unknown_error"):
        """
        Обрабатывает ошибку в callback
        
        Args:
            query: Callback query
            error: Ошибка
            error_type: Тип ошибки
        """
        try:
            # Логируем ошибку
            self.logger.error(f"❌ Ошибка в callback {query.data}: {error}")
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            
            # Показываем алерт
            await self.show_alert(query, error_type)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки callback ошибки: {e}")
            try:
                await query.answer("❌ Произошла ошибка", show_alert=True)
            except:
                pass
    
    def log_error(self, error: Exception, context: str = "", additional_info: Optional[Dict] = None):
        """
        Логирует ошибку с дополнительной информацией
        
        Args:
            error: Ошибка
            context: Контекст ошибки
            additional_info: Дополнительная информация
        """
        try:
            error_msg = f"❌ Ошибка в {context}: {error}"
            if additional_info:
                error_msg += f" | Доп. информация: {additional_info}"
            
            self.logger.error(error_msg)
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка логирования: {e}")
    
    async def safe_execute(self, func: Callable, *args, error_type: str = "unknown_error", 
                          **kwargs) -> Optional[Any]:
        """
        Безопасно выполняет функцию с обработкой ошибок
        
        Args:
            func: Функция для выполнения
            *args: Аргументы функции
            error_type: Тип ошибки
            **kwargs: Ключевые аргументы функции
            
        Returns:
            Результат функции или None при ошибке
        """
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            self.log_error(e, f"safe_execute({func.__name__})")
            
            # Пытаемся показать алерт если есть query в аргументах
            query = None
            for arg in args:
                if isinstance(arg, CallbackQuery):
                    query = arg
                    break
            
            if query:
                await self.show_alert(query, error_type)
            
            return None


# Глобальный экземпляр обработчика ошибок
error_handler = ErrorHandler()
