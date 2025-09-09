#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Менеджер баланса пользователей для ForestMafia Bot
Исправляет проблемы с сохранением и обновлением баланса
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from database_psycopg2 import (
    create_user, get_user_by_telegram_id, update_user_balance, get_user_balance,
    execute_query, fetch_one
)

logger = logging.getLogger(__name__)


class BalanceManager:
    """Менеджер баланса пользователей"""
    
    def __init__(self):
        self.logger = logger
    
    def get_user_balance(self, user_id: int) -> float:
        """
        Получает баланс пользователя с созданием записи если не существует
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            float: Баланс пользователя (0 если пользователь не найден)
        """
        try:
            # Проверяем, существует ли пользователь
            user = get_user_by_telegram_id(user_id)
            
            if not user:
                # Создаем пользователя с нулевым балансом
                self.create_user_if_not_exists(user_id, f"User_{user_id}")
                return 0.0
            
            # Получаем баланс
            balance = get_user_balance(user_id)
            return float(balance) if balance is not None else 0.0
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения баланса пользователя {user_id}: {e}")
            return 0.0
    
    def create_user_if_not_exists(self, user_id: int, username: str) -> bool:
        """
        Создает пользователя если он не существует
        
        Args:
            user_id: ID пользователя Telegram
            username: Имя пользователя
            
        Returns:
            bool: True если пользователь создан или уже существует
        """
        try:
            # Проверяем, существует ли пользователь
            existing_user = get_user_by_telegram_id(user_id)
            if existing_user:
                return True
            
            # Создаем пользователя
            success = create_user(user_id, username)
            if success:
                self.logger.info(f"✅ Создан пользователь {user_id} с балансом 0")
                return True
            else:
                self.logger.error(f"❌ Не удалось создать пользователя {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания пользователя {user_id}: {e}")
            return False
    
    def update_user_balance(self, user_id: int, new_balance: float) -> bool:
        """
        Обновляет баланс пользователя с проверками
        
        Args:
            user_id: ID пользователя Telegram
            new_balance: Новый баланс
            
        Returns:
            bool: True если обновление успешно
        """
        try:
            # Убеждаемся, что пользователь существует
            if not self.create_user_if_not_exists(user_id, f"User_{user_id}"):
                return False
            
            # Проверяем, что баланс не отрицательный
            if new_balance < 0:
                self.logger.warning(f"⚠️ Попытка установить отрицательный баланс для пользователя {user_id}: {new_balance}")
                new_balance = 0.0
            
            # Обновляем баланс
            success = update_user_balance(user_id, new_balance)
            
            if success:
                self.logger.info(f"✅ Баланс пользователя {user_id} обновлен: {new_balance}")
                return True
            else:
                self.logger.error(f"❌ Не удалось обновить баланс пользователя {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления баланса пользователя {user_id}: {e}")
            return False
    
    def add_to_balance(self, user_id: int, amount: float) -> bool:
        """
        Добавляет сумму к балансу пользователя
        
        Args:
            user_id: ID пользователя Telegram
            amount: Сумма для добавления
            
        Returns:
            bool: True если операция успешна
        """
        try:
            if amount <= 0:
                self.logger.warning(f"⚠️ Попытка добавить неположительную сумму {amount} пользователю {user_id}")
                return False
            
            # Получаем текущий баланс
            current_balance = self.get_user_balance(user_id)
            
            # Вычисляем новый баланс
            new_balance = current_balance + amount
            
            # Обновляем баланс
            return self.update_user_balance(user_id, new_balance)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка добавления к балансу пользователя {user_id}: {e}")
            return False
    
    def subtract_from_balance(self, user_id: int, amount: float) -> bool:
        """
        Вычитает сумму из баланса пользователя
        
        Args:
            user_id: ID пользователя Telegram
            amount: Сумма для вычитания
            
        Returns:
            bool: True если операция успешна
        """
        try:
            if amount <= 0:
                self.logger.warning(f"⚠️ Попытка вычесть неположительную сумму {amount} у пользователя {user_id}")
                return False
            
            # Получаем текущий баланс
            current_balance = self.get_user_balance(user_id)
            
            # Проверяем, достаточно ли средств
            if current_balance < amount:
                self.logger.warning(f"⚠️ Недостаточно средств у пользователя {user_id}: {current_balance} < {amount}")
                return False
            
            # Вычисляем новый баланс
            new_balance = current_balance - amount
            
            # Обновляем баланс
            return self.update_user_balance(user_id, new_balance)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка вычитания из баланса пользователя {user_id}: {e}")
            return False
    
    def transfer_balance(self, from_user_id: int, to_user_id: int, amount: float) -> bool:
        """
        Переводит средства между пользователями
        
        Args:
            from_user_id: ID отправителя
            to_user_id: ID получателя
            amount: Сумма перевода
            
        Returns:
            bool: True если перевод успешен
        """
        try:
            if amount <= 0:
                self.logger.warning(f"⚠️ Попытка перевода неположительной суммы {amount}")
                return False
            
            if from_user_id == to_user_id:
                self.logger.warning(f"⚠️ Попытка перевода самому себе")
                return False
            
            # Проверяем баланс отправителя
            from_balance = self.get_user_balance(from_user_id)
            if from_balance < amount:
                self.logger.warning(f"⚠️ Недостаточно средств для перевода: {from_balance} < {amount}")
                return False
            
            # Выполняем перевод
            if self.subtract_from_balance(from_user_id, amount):
                if self.add_to_balance(to_user_id, amount):
                    self.logger.info(f"✅ Перевод {amount} от {from_user_id} к {to_user_id} выполнен успешно")
                    return True
                else:
                    # Возвращаем средства отправителю при ошибке
                    self.add_to_balance(from_user_id, amount)
                    self.logger.error(f"❌ Ошибка зачисления средств получателю {to_user_id}")
                    return False
            else:
                self.logger.error(f"❌ Ошибка списания средств с отправителя {from_user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка перевода средств: {e}")
            return False
    
    def get_user_balance_info(self, user_id: int) -> Dict[str, Any]:
        """
        Получает полную информацию о балансе пользователя
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            Dict с информацией о балансе
        """
        try:
            user = get_user_by_telegram_id(user_id)
            if not user:
                return {
                    "user_id": user_id,
                    "balance": 0.0,
                    "exists": False,
                    "created_at": None,
                    "updated_at": None
                }
            
            balance = self.get_user_balance(user_id)
            
            return {
                "user_id": user_id,
                "balance": balance,
                "exists": True,
                "created_at": user.get('created_at'),
                "updated_at": user.get('updated_at')
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения информации о балансе пользователя {user_id}: {e}")
            return {
                "user_id": user_id,
                "balance": 0.0,
                "exists": False,
                "error": str(e)
            }


# Глобальный экземпляр менеджера баланса
balance_manager = BalanceManager()
