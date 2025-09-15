#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Менеджер этапов игры для Лес и волки Bot
Исправляет логику работы этапов и их корректные переходы
"""

import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from game_logic import Game, GamePhase, Role, Team
from config import config

logger = logging.getLogger(__name__)


class PhaseTransition(Enum):
    """Переходы между этапами"""
    WAITING_TO_NIGHT = "waiting_to_night"
    NIGHT_TO_DAY = "night_to_day"
    DAY_TO_VOTING = "day_to_voting"
    VOTING_TO_NIGHT = "voting_to_night"
    ANY_TO_GAME_OVER = "any_to_game_over"


class GamePhaseManager:
    """Менеджер этапов игры"""
    
    def __init__(self):
        self.logger = logger
        self.phase_timers: Dict[int, asyncio.Task] = {}  # chat_id -> timer_task
        self.phase_callbacks: Dict[PhaseTransition, Callable] = {}
        self._setup_default_callbacks()
    
    def _setup_default_callbacks(self):
        """Настраивает стандартные обработчики переходов"""
        self.phase_callbacks = {
            PhaseTransition.WAITING_TO_NIGHT: self._handle_waiting_to_night,
            PhaseTransition.NIGHT_TO_DAY: self._handle_night_to_day,
            PhaseTransition.DAY_TO_VOTING: self._handle_day_to_voting,
            PhaseTransition.VOTING_TO_NIGHT: self._handle_voting_to_night,
            PhaseTransition.ANY_TO_GAME_OVER: self._handle_game_over
        }
    
    async def start_phase(self, game: Game, phase: GamePhase, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Запускает этап игры
        
        Args:
            game: Объект игры
            phase: Этап для запуска
            context: Контекст бота
            
        Returns:
            bool: True если этап запущен успешно
        """
        try:
            # Отменяем предыдущий таймер если есть
            await self._cancel_phase_timer(game.chat_id)
            
            # Устанавливаем фазу
            game.phase = phase
            
            # Вычисляем время окончания этапа
            duration = self._get_phase_duration(phase)
            game.phase_end_time = datetime.now() + timedelta(seconds=duration)
            
            # Запускаем обработчик этапа
            success = await self._execute_phase_handler(game, phase, context)
            
            if success:
                # Запускаем таймер этапа
                await self._start_phase_timer(game, context)
                self.logger.info(f"✅ Этап {phase.value} запущен для игры {game.chat_id}")
                return True
            else:
                self.logger.error(f"❌ Не удалось запустить этап {phase.value} для игры {game.chat_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка запуска этапа {phase.value}: {e}")
            return False
    
    def _get_phase_duration(self, phase: GamePhase) -> int:
        """Получает длительность этапа в секундах"""
        durations = {
            GamePhase.WAITING: 0,  # Без ограничения по времени
            GamePhase.NIGHT: config.night_duration,
            GamePhase.DAY: config.day_duration,
            GamePhase.VOTING: config.voting_duration,
            GamePhase.GAME_OVER: 0  # Без ограничения по времени
        }
        return durations.get(phase, 60)
    
    async def _execute_phase_handler(self, game: Game, phase: GamePhase, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Выполняет обработчик этапа"""
        try:
            if phase == GamePhase.NIGHT:
                return await self._handle_night_phase(game, context)
            elif phase == GamePhase.DAY:
                return await self._handle_day_phase(game, context)
            elif phase == GamePhase.VOTING:
                return await self._handle_voting_phase(game, context)
            elif phase == GamePhase.GAME_OVER:
                return await self._handle_game_over_phase(game, context)
            else:
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка выполнения обработчика этапа {phase.value}: {e}")
            return False
    
    async def _handle_waiting_to_night(self, game: Game, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обрабатывает переход от ожидания к ночной фазе"""
        try:
            # Переводим игру в ночную фазу
            game.phase = GamePhase.NIGHT
            game.current_round += 1
            
            # Сохраняем состояние игры
            from bot import ForestWolvesBot
            bot = ForestWolvesBot.get_instance()
            if bot:
                bot.save_game_state(game.chat_id)
            
            self.logger.info(f"🌙 Игра {game.chat_id} переведена в ночную фазу (раунд {game.current_round})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка перехода к ночной фазе: {e}")
            return False
    
    async def _handle_night_to_day(self, game: Game, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обрабатывает переход от ночи к дню"""
        try:
            # Переводим игру в дневную фазу
            game.phase = GamePhase.DAY
            
            # Сохраняем состояние игры
            from bot import ForestWolvesBot
            bot = ForestWolvesBot.get_instance()
            if bot:
                bot.save_game_state(game.chat_id)
            
            self.logger.info(f"☀️ Игра {game.chat_id} переведена в дневную фазу")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка перехода к дневной фазе: {e}")
            return False
    
    async def _handle_day_to_voting(self, game: Game, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обрабатывает переход от дня к голосованию"""
        try:
            # Переводим игру в фазу голосования
            game.phase = GamePhase.VOTING
            
            # Сохраняем состояние игры
            from bot import ForestWolvesBot
            bot = ForestWolvesBot.get_instance()
            if bot:
                bot.save_game_state(game.chat_id)
            
            self.logger.info(f"🗳️ Игра {game.chat_id} переведена в фазу голосования")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка перехода к голосованию: {e}")
            return False
    
    async def _handle_voting_to_night(self, game: Game, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обрабатывает переход от голосования к ночи"""
        try:
            # Переводим игру в ночную фазу
            game.phase = GamePhase.NIGHT
            game.current_round += 1
            
            # Сохраняем состояние игры
            from bot import ForestWolvesBot
            bot = ForestWolvesBot.get_instance()
            if bot:
                bot.save_game_state(game.chat_id)
            
            self.logger.info(f"🌙 Игра {game.chat_id} переведена в ночную фазу (раунд {game.current_round})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка перехода к ночной фазе: {e}")
            return False
    
    async def _handle_game_over(self, game: Game, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обрабатывает окончание игры"""
        try:
            # Переводим игру в фазу окончания
            game.phase = GamePhase.GAME_OVER
            
            # Сохраняем состояние игры
            from bot import ForestWolvesBot
            bot = ForestWolvesBot.get_instance()
            if bot:
                bot.save_game_state(game.chat_id)
            
            self.logger.info(f"🏁 Игра {game.chat_id} завершена")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка завершения игры: {e}")
            return False
    
    async def _handle_night_phase(self, game: Game, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обрабатывает ночную фазу"""
        try:
            # Отправляем сообщение о начале ночи
            night_message = await self._send_night_message(game, context)
            
            if night_message:
                # Закрепляем сообщение
                await self._pin_stage_message(context, game, "night", night_message.message_id)
                
                # Отправляем роли игрокам
                await self._send_roles_to_players(game, context)
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки ночной фазы: {e}")
            return False
    
    async def _handle_day_phase(self, game: Game, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обрабатывает дневную фазу"""
        try:
            # Отправляем сообщение о начале дня
            day_message = await self._send_day_message(game, context)
            
            if day_message:
                # Закрепляем сообщение
                await self._pin_stage_message(context, game, "day", day_message.message_id)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки дневной фазы: {e}")
            return False
    
    async def _handle_voting_phase(self, game: Game, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обрабатывает фазу голосования"""
        try:
            # Отправляем сообщение о начале голосования
            voting_message = await self._send_voting_message(game, context)
            
            if voting_message:
                # Закрепляем сообщение
                await self._pin_stage_message(context, game, "voting", voting_message.message_id)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки фазы голосования: {e}")
            return False
    
    async def _handle_game_over_phase(self, game: Game, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обрабатывает завершение игры"""
        try:
            # Отправляем сообщение о завершении игры
            await self._send_game_over_message(game, context)
            
            # Очищаем таймеры
            await self._cancel_phase_timer(game.chat_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки завершения игры: {e}")
            return False
    
    async def _send_night_message(self, game: Game, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет сообщение о начале ночи"""
        try:
            # Создаем кнопки
            keyboard = [
                [InlineKeyboardButton("🎭 Посмотреть свою роль", callback_data="view_my_role")],
                [InlineKeyboardButton("💌 Написать боту", url="https://t.me/Forest_fuss_bot")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Формируем сообщение
            night_text = (
                "🌙 **Наступает ночь** 🌙\n\n"
                "🌲 Все зверушки засыпают в своих укрытиях...\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых игроков: {len(game.get_alive_players())}\n\n"
                "🐺 Хищники выходят на охоту...\n"
                "🦫 Травоядные спят беспокойно...\n\n"
                "🎭 Распределение ролей завершено!"
            )
            
            # Отправляем сообщение
            message = await context.bot.send_message(
                chat_id=game.chat_id,
                text=night_text,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                message_thread_id=game.thread_id
            )
            
            return message
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки сообщения о ночи: {e}")
            return None
    
    async def _send_day_message(self, game: Game, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет сообщение о начале дня"""
        try:
            # Создаем кнопки
            keyboard = [
                [InlineKeyboardButton("🏁 Завершить обсуждение", callback_data="day_end_discussion")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Формируем сообщение
            day_text = (
                "☀️ **Наступило утро** ☀️\n\n"
                "🌲 Все зверушки проснулись и собрались на лесной поляне для обсуждения.\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Живых игроков: {len(game.get_alive_players())}\n\n"
                "💬 Обсуждайте, кого подозреваете в хищничестве!\n"
                "🕐 У вас есть время для размышлений..."
            )
            
            # Отправляем сообщение
            message = await context.bot.send_message(
                chat_id=game.chat_id,
                text=day_text,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                message_thread_id=game.thread_id
            )
            
            return message
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки сообщения о дне: {e}")
            return None
    
    async def _send_voting_message(self, game: Game, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет сообщение о начале голосования"""
        try:
            # Формируем сообщение
            voting_text = (
                "🗳️ **Начинается голосование** 🗳️\n\n"
                f"👥 Живых игроков: {len(game.get_alive_players())}\n"
                f"⏰ У вас есть {config.voting_duration // 60} минут на голосование за изгнание!\n\n"
                "**Правила голосования:**\n"
                "• Требуется большинство голосов для изгнания\n"
                "• Можно проголосовать за пропуск\n"
                "• Голосование за себя запрещено"
            )
            
            # Отправляем сообщение
            message = await context.bot.send_message(
                chat_id=game.chat_id,
                text=voting_text,
                parse_mode='Markdown',
                message_thread_id=game.thread_id
            )
            
            return message
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки сообщения о голосовании: {e}")
            return None
    
    async def _send_game_over_message(self, game: Game, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет сообщение о завершении игры"""
        try:
            # Определяем победителя
            winner = game.check_game_end()
            winner_name = "🦁 Хищники" if winner == Team.PREDATORS else "🌿 Травоядные"
            
            # Формируем сообщение
            game_over_text = (
                "🌲 **ИГРА ЗАВЕРШЕНА** 🌲\n\n"
                f"🏆 Победители: {winner_name}\n"
                f"🎮 Раундов: {game.current_round}\n"
                f"👥 Участников: {len(game.players)}\n\n"
                "🌲 Спасибо за игру! 🌲"
            )
            
            # Отправляем сообщение
            await context.bot.send_message(
                chat_id=game.chat_id,
                text=game_over_text,
                parse_mode='Markdown',
                message_thread_id=game.thread_id
            )
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки сообщения о завершении игры: {e}")
    
    async def _send_roles_to_players(self, game: Game, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет роли игрокам в личные сообщения"""
        try:
            for player in game.players.values():
                try:
                    role_info = self._get_role_info(player.role)
                    team_name = "🦁 Хищники" if player.team == Team.PREDATORS else "🌿 Травоядные"
                    
                    role_message = (
                        f"🎭 **Ваша роль в игре:**\n\n"
                        f"👤 {role_info['name']}\n"
                        f"🏴 Команда: {team_name}\n\n"
                        f"📝 **Описание:**\n{role_info['description']}\n\n"
                        f"🌲 Удачной игры! 🌲"
                    )
                    
                    await context.bot.send_message(
                        chat_id=player.user_id,
                        text=role_message,
                        parse_mode='Markdown'
                    )
                    
                except Exception as e:
                    self.logger.error(f"❌ Не удалось отправить роль игроку {player.user_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки ролей игрокам: {e}")
    
    def _get_role_info(self, role: Role) -> Dict[str, str]:
        """Получает информацию о роли"""
        role_info = {
            Role.WOLF: {
                "name": "🐺 Волк",
                "description": "Вы хищник! Вместе с другими волками вы охотитесь по ночам."
            },
            Role.FOX: {
                "name": "🦊 Лиса",
                "description": "Вы хищник! Каждую ночь вы воруете запасы еды у других зверей."
            },
            Role.HARE: {
                "name": "🐰 Заяц",
                "description": "Вы травоядный! Вы спите всю ночь и участвуете только в дневных обсуждениях."
            },
            Role.MOLE: {
                "name": "🦫 Крот",
                "description": "Вы травоядный! По ночам вы роете норки и узнаёте команды других зверей."
            },
            Role.BEAVER: {
                "name": "🦦 Бобёр",
                "description": "Вы травоядный! Вы можете возвращать украденные запасы другим зверям."
            }
        }
        return role_info.get(role, {"name": "Неизвестно", "description": "Роль не определена"})
    
    async def _start_phase_timer(self, game: Game, context: ContextTypes.DEFAULT_TYPE):
        """Запускает таймер этапа"""
        try:
            duration = self._get_phase_duration(game.phase)
            
            if duration > 0:
                # Создаем задачу таймера
                timer_task = asyncio.create_task(
                    self._phase_timer_task(game, context, duration)
                )
                
                # Сохраняем задачу
                self.phase_timers[game.chat_id] = timer_task
                
                self.logger.info(f"⏰ Таймер этапа {game.phase.value} запущен на {duration} секунд")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка запуска таймера этапа: {e}")
    
    async def _phase_timer_task(self, game: Game, context: ContextTypes.DEFAULT_TYPE, duration: int):
        """Задача таймера этапа"""
        try:
            # Ждем окончания этапа
            await asyncio.sleep(duration)
            
            # Проверяем, что игра еще активна
            if game.phase != GamePhase.GAME_OVER:
                # Переходим к следующему этапу
                await self._transition_to_next_phase(game, context)
            
        except asyncio.CancelledError:
            self.logger.info(f"⏰ Таймер этапа {game.phase.value} отменен")
        except Exception as e:
            self.logger.error(f"❌ Ошибка в таймере этапа: {e}")
        finally:
            # Удаляем задачу из списка
            self.phase_timers.pop(game.chat_id, None)
    
    async def _transition_to_next_phase(self, game: Game, context: ContextTypes.DEFAULT_TYPE):
        """Переходит к следующему этапу"""
        try:
            current_phase = game.phase
            
            if current_phase == GamePhase.NIGHT:
                # Ночь -> День
                await self.start_phase(game, GamePhase.DAY, context)
            elif current_phase == GamePhase.DAY:
                # День -> Голосование
                await self.start_phase(game, GamePhase.VOTING, context)
            elif current_phase == GamePhase.VOTING:
                # Голосование -> Следующая ночь
                game.current_round += 1
                await self.start_phase(game, GamePhase.NIGHT, context)
            
            self.logger.info(f"✅ Переход от {current_phase.value} к {game.phase.value}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка перехода к следующему этапу: {e}")
    
    async def _cancel_phase_timer(self, chat_id: int):
        """Отменяет таймер этапа"""
        try:
            if chat_id in self.phase_timers:
                timer_task = self.phase_timers[chat_id]
                if not timer_task.done():
                    timer_task.cancel()
                    try:
                        await timer_task
                    except asyncio.CancelledError:
                        pass
                
                del self.phase_timers[chat_id]
                self.logger.info(f"⏰ Таймер этапа для чата {chat_id} отменен")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка отмены таймера этапа: {e}")
    
    async def _pin_stage_message(self, context: ContextTypes.DEFAULT_TYPE, game: Game, stage: str, message_id: int):
        """Закрепляет сообщение этапа"""
        try:
            # Открепляем предыдущее сообщение этапа
            await self._unpin_previous_stage_message(context, game, stage)
            
            # Закрепляем новое сообщение
            await context.bot.pin_chat_message(
                chat_id=game.chat_id,
                message_id=message_id
            )
            
            # Сохраняем ID сообщения
            game.set_stage_pinned_message(stage, message_id)
            
            self.logger.info(f"📌 Сообщение этапа {stage} закреплено: {message_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка закрепления сообщения этапа: {e}")
    
    async def _unpin_previous_stage_message(self, context: ContextTypes.DEFAULT_TYPE, game: Game, current_stage: str):
        """Открепляет предыдущее сообщение этапа"""
        try:
            # Открепляем все предыдущие сообщения этапов
            for stage, message_id in game.stage_pinned_messages.items():
                if stage != current_stage:
                    try:
                        await context.bot.unpin_chat_message(
                            chat_id=game.chat_id,
                            message_id=message_id
                        )
                        self.logger.info(f"📌 Сообщение этапа {stage} откреплено: {message_id}")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Не удалось открепить сообщение этапа {stage}: {e}")
            
            # Очищаем сохраненные ID
            game.clear_all_stage_pinned_messages()
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка открепления сообщений этапов: {e}")
    
    async def repeat_current_phase(self, game: Game, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Повторяет текущий этап
        
        Args:
            game: Объект игры
            context: Контекст бота
            
        Returns:
            bool: True если этап повторен успешно
        """
        try:
            if game.phase == GamePhase.WAITING:
                return False
            
            # Повторяем текущий этап
            success = await self.start_phase(game, game.phase, context)
            
            if success:
                self.logger.info(f"🔄 Этап {game.phase.value} повторен для игры {game.chat_id}")
                return True
            else:
                self.logger.error(f"❌ Не удалось повторить этап {game.phase.value}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка повторения этапа: {e}")
            return False
    
    async def cleanup_game(self, chat_id: int):
        """Очищает ресурсы игры"""
        try:
            await self._cancel_phase_timer(chat_id)
            self.logger.info(f"🧹 Ресурсы игры {chat_id} очищены")
        except Exception as e:
            self.logger.error(f"❌ Ошибка очистки ресурсов игры {chat_id}: {e}")


# Глобальный экземпляр менеджера этапов
phase_manager = GamePhaseManager()
