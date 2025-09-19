#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Value Objects для доменной модели
Неизменяемые объекты, представляющие концепции предметной области
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime, timedelta


class GamePhase(Enum):
    """Фазы игры"""
    WAITING = "waiting"
    NIGHT = "night"
    DAY = "day"
    VOTING = "voting"
    GAME_OVER = "game_over"


class Team(Enum):
    """Команды в игре"""
    PREDATORS = "predators"  # Хищники
    HERBIVORES = "herbivores"  # Травоядные


class Role(Enum):
    """Роли игроков"""
    WOLF = "wolf"        # Волк
    FOX = "fox"          # Лиса
    HARE = "hare"        # Заяц
    MOLE = "mole"        # Крот
    BEAVER = "beaver"    # Бобёр


@dataclass(frozen=True)
class UserId:
    """Идентификатор пользователя"""
    value: int
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("User ID должен быть положительным числом")


@dataclass(frozen=True)
class ChatId:
    """Идентификатор чата"""
    value: int
    
    def __post_init__(self):
        if self.value == 0:
            raise ValueError("Chat ID не может быть равен 0")


@dataclass(frozen=True)
class GameId:
    """Идентификатор игры"""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Game ID не может быть пустым")


@dataclass(frozen=True)
class Username:
    """Имя пользователя"""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Username не может быть пустым")


@dataclass(frozen=True)
class Supplies:
    """Припасы игрока"""
    current: int
    maximum: int
    
    def __post_init__(self):
        if self.current < 0:
            raise ValueError("Количество припасов не может быть отрицательным")
        if self.maximum < 1:
            raise ValueError("Максимальное количество припасов должно быть больше 0")
        if self.current > self.maximum:
            raise ValueError("Текущие припасы не могут превышать максимум")
    
    @property
    def is_critical(self) -> bool:
        """Проверяет, критично ли мало припасов"""
        return self.current <= 1
    
    def can_consume(self, amount: int = 1) -> bool:
        """Проверяет, можно ли потребить указанное количество припасов"""
        return self.current >= amount
    
    def consume(self, amount: int = 1) -> 'Supplies':
        """Потребляет припасы, возвращает новый объект"""
        if not self.can_consume(amount):
            raise ValueError(f"Недостаточно припасов для потребления {amount}")
        return Supplies(self.current - amount, self.maximum)
    
    def add(self, amount: int) -> 'Supplies':
        """Добавляет припасы, возвращает новый объект"""
        if amount <= 0:
            return self
        new_current = min(self.current + amount, self.maximum)
        return Supplies(new_current, self.maximum)


@dataclass(frozen=True)
class GameDuration:
    """Длительность игры"""
    start_time: datetime
    end_time: Optional[datetime] = None
    
    @property
    def is_finished(self) -> bool:
        """Проверяет, завершена ли игра"""
        return self.end_time is not None
    
    @property
    def total_seconds(self) -> float:
        """Возвращает общую длительность в секундах"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def finish(self) -> 'GameDuration':
        """Завершает игру, возвращает новый объект"""
        if self.is_finished:
            return self
        return GameDuration(self.start_time, datetime.now())


@dataclass(frozen=True)
class PhaseDuration:
    """Длительность фазы"""
    start_time: datetime
    duration_seconds: int
    
    @property
    def end_time(self) -> datetime:
        """Время окончания фазы"""
        return self.start_time + timedelta(seconds=self.duration_seconds)
    
    @property
    def is_finished(self) -> bool:
        """Проверяет, закончилась ли фаза"""
        return datetime.now() >= self.end_time
    
    @property
    def remaining_seconds(self) -> int:
        """Оставшееся время в секундах"""
        remaining = (self.end_time - datetime.now()).total_seconds()
        return max(0, int(remaining))
