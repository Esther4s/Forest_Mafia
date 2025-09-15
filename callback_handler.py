#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчик callback'ов для Лес и волки Bot
Исправляет механику повторного запуска этапа и заменяет ошибки на алерты
"""

import logging
from typing import Dict, Optional, Callable, Any
from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from game_logic import Game, GamePhase, Role, Team
from game_phase_manager import phase_manager
from error_handler import error_handler
from rewards_system import rewards_system, RewardReason

logger = logging.getLogger(__name__)


class CallbackHandler:
    """Обработчик callback'ов"""
    
    def __init__(self):
        self.logger = logger
        self.callback_handlers: Dict[str, Callable] = {}
        self._setup_handlers()
    
    def get_display_name(self, user_id: int, username: str = None, first_name: str = None) -> str:
        """Получает отображаемое имя пользователя (приоритет: никнейм > username > first_name)"""
        try:
            from database_psycopg2 import get_user_nickname
            nickname = get_user_nickname(user_id)
            if nickname:
                return nickname
            elif username and not username.isdigit():
                return f"@{username}"
            elif first_name:
                return first_name
            else:
                return f"ID:{user_id}"
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка получения никнейма для пользователя {user_id}: {e}")
            if username and not username.isdigit():
                return f"@{username}"
            elif first_name:
                return first_name
            else:
                return f"ID:{user_id}"
    
    def _setup_handlers(self):
        """Настраивает обработчики callback'ов"""
        self.callback_handlers = {
            "view_my_role": self._handle_view_role,
            "repeat_current_phase": self._handle_repeat_phase,
            "day_end_discussion": self._handle_end_discussion,
            "night_end_actions": self._handle_end_night_actions,
            "voting_end": self._handle_end_voting,
            "game_end": self._handle_end_game,
            "admin_panel": self._handle_admin_panel,
            "player_stats": self._handle_player_stats,
            "game_stats": self._handle_game_stats,
            "balance_info": self._handle_balance_info,
            "rewards_info": self._handle_rewards_info,
            "wolf": self._handle_wolf_action,
            "fox": self._handle_fox_action,
            "mole": self._handle_mole_action,
            "beaver": self._handle_beaver_action,
        }
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обрабатывает callback query
        
        Args:
            update: Обновление от Telegram
            context: Контекст бота
        """
        query = update.callback_query
        if not query:
            return
        
        try:
            # Получаем данные callback'а
            callback_data = query.data
            if not callback_data:
                await error_handler.show_alert(query, "invalid_input", "❌ Неверные данные callback'а")
                return
            
            # Разбираем callback data
            parts = callback_data.split("_")
            if not parts:
                await error_handler.show_alert(query, "invalid_input", "❌ Неверный формат callback'а")
                return
            
            # Получаем основной обработчик
            main_handler = parts[0]
            
            # Специальная обработка для wolf_kill, fox_steal, beaver_help, mole_check
            if len(parts) >= 2:
                action_type = f"{parts[0]}_{parts[1]}"
                if action_type in ["wolf_kill", "fox_steal", "beaver_help", "mole_check"]:
                    handler_func = self.callback_handlers.get(parts[0])
                    if handler_func:
                        await handler_func(query, context, parts)
                        return
            
            handler_func = self.callback_handlers.get(main_handler)
            
            if handler_func:
                await handler_func(query, context, parts)
            else:
                await self._handle_unknown_callback(query, context, callback_data)
                
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    async def _handle_view_role(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает просмотр роли"""
        try:
            user_id = query.from_user.id
            
            # Находим игру пользователя
            game = self._find_user_game(user_id)
            if not game:
                await error_handler.show_alert(query, "game_not_found")
                return
            
            # Проверяем, что пользователь в игре
            if user_id not in game.players:
                await error_handler.show_alert(query, "player_not_found")
                return
            
            player = game.players[user_id]
            role_info = self._get_role_info(player.role)
            team_name = "🦁 Хищники" if player.team == Team.PREDATORS else "🌿 Травоядные"
            
            role_text = (
                f"🎭 <b>Ваша роль в игре:</b>\n\n"
                f"👤 {role_info['name']}\n"
                f"🏴 Команда: {team_name}\n\n"
                f"📝 <b>Описание:</b>\n{role_info['description']}\n\n"
                f"🌙 Раунд: {game.current_round}\n"
                f"💚 Статус: {'Живой' if player.is_alive else 'Мертвый'}"
            )
            
            # Отправляем роль в личные сообщения
            try:
                await context.bot.send_message(chat_id=user_id, text=role_text, parse_mode='HTML')
                await error_handler.show_success_alert(query, "Информация о вашей роли отправлена в личные сообщения!")
            except Exception as e:
                await error_handler.show_alert(query, "network_error", "❌ Не удалось отправить сообщение в личку!")
                
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    async def _handle_repeat_phase(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает повторение текущего этапа"""
        try:
            user_id = query.from_user.id
            
            # Находим игру пользователя
            game = self._find_user_game(user_id)
            if not game:
                await error_handler.show_alert(query, "game_not_found")
                return
            
            # Проверяем, что пользователь в игре
            if user_id not in game.players:
                await error_handler.show_alert(query, "player_not_found")
                return
            
            # Проверяем, что игра не в фазе ожидания
            if game.phase == GamePhase.WAITING:
                await error_handler.show_alert(query, "invalid_phase", "❌ Эта функция недоступна в фазе ожидания!")
                return
            
            # Повторяем текущий этап
            success = await phase_manager.repeat_current_phase(game, context)
            
            if success:
                phase_name = self._get_phase_name(game.phase)
                await error_handler.show_success_alert(query, f"Сообщение {phase_name} повторно отправлено!")
            else:
                await error_handler.show_alert(query, "unknown_error", "❌ Не удалось повторить этап")
                
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    async def _handle_end_discussion(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает завершение обсуждения"""
        try:
            user_id = query.from_user.id
            
            # Находим игру пользователя
            game = self._find_user_game(user_id)
            if not game:
                await error_handler.show_alert(query, "game_not_found")
                return
            
            # Проверяем, что игра в дневной фазе
            if game.phase != GamePhase.DAY:
                await error_handler.show_alert(query, "invalid_phase", "❌ Это действие доступно только в дневной фазе!")
                return
            
            # Проверяем права администратора
            if not self._is_admin(query.from_user.id, game.chat_id):
                await error_handler.show_alert(query, "permission_denied", "❌ Только администраторы могут завершать обсуждение!")
                return
            
            # Переходим к голосованию
            success = await phase_manager.start_phase(game, GamePhase.VOTING, context)
            
            if success:
                await error_handler.show_success_alert(query, "Обсуждение завершено, начинается голосование!")
            else:
                await error_handler.show_alert(query, "unknown_error", "❌ Не удалось завершить обсуждение")
                
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    async def _handle_end_night_actions(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает завершение ночных действий"""
        try:
            user_id = query.from_user.id
            
            # Находим игру пользователя
            game = self._find_user_game(user_id)
            if not game:
                await error_handler.show_alert(query, "game_not_found")
                return
            
            # Проверяем, что игра в ночной фазе
            if game.phase != GamePhase.NIGHT:
                await error_handler.show_alert(query, "invalid_phase", "❌ Это действие доступно только в ночной фазе!")
                return
            
            # Проверяем права администратора
            if not self._is_admin(query.from_user.id, game.chat_id):
                await error_handler.show_alert(query, "permission_denied", "❌ Только администраторы могут завершать ночные действия!")
                return
            
            # Переходим к дневной фазе
            success = await phase_manager.start_phase(game, GamePhase.DAY, context)
            
            if success:
                await error_handler.show_success_alert(query, "Ночные действия завершены, начинается день!")
            else:
                await error_handler.show_alert(query, "unknown_error", "❌ Не удалось завершить ночные действия")
                
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    async def _handle_end_voting(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает завершение голосования"""
        try:
            user_id = query.from_user.id
            
            # Находим игру пользователя
            game = self._find_user_game(user_id)
            if not game:
                await error_handler.show_alert(query, "game_not_found")
                return
            
            # Проверяем, что игра в фазе голосования
            if game.phase != GamePhase.VOTING:
                await error_handler.show_alert(query, "invalid_phase", "❌ Это действие доступно только в фазе голосования!")
                return
            
            # Проверяем права администратора
            if not self._is_admin(query.from_user.id, game.chat_id):
                await error_handler.show_alert(query, "permission_denied", "❌ Только администраторы могут завершать голосование!")
                return
            
            # Обрабатываем результаты голосования
            exiled_player = game.process_voting()
            
            # Отправляем результаты
            await self._send_voting_results(game, context, exiled_player)
            
            # Переходим к следующей ночи
            game.current_round += 1
            success = await phase_manager.start_phase(game, GamePhase.NIGHT, context)
            
            if success:
                await error_handler.show_success_alert(query, "Голосование завершено, начинается следующая ночь!")
            else:
                await error_handler.show_alert(query, "unknown_error", "❌ Не удалось завершить голосование")
                
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    async def _handle_end_game(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает завершение игры"""
        try:
            user_id = query.from_user.id
            
            # Находим игру пользователя
            game = self._find_user_game(user_id)
            if not game:
                await error_handler.show_alert(query, "game_not_found")
                return
            
            # Проверяем права администратора
            if not self._is_admin(query.from_user.id, game.chat_id):
                await error_handler.show_alert(query, "permission_denied", "❌ Только администраторы могут завершать игру!")
                return
            
            # Завершаем игру
            game.phase = GamePhase.GAME_OVER
            await phase_manager.start_phase(game, GamePhase.GAME_OVER, context)
            
            await error_handler.show_success_alert(query, "Игра завершена!")
            
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    async def _handle_admin_panel(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает панель администратора"""
        try:
            user_id = query.from_user.id
            
            # Находим игру пользователя
            game = self._find_user_game(user_id)
            if not game:
                await error_handler.show_alert(query, "game_not_found")
                return
            
            # Проверяем права администратора
            if not self._is_admin(query.from_user.id, game.chat_id):
                await error_handler.show_alert(query, "permission_denied")
                return
            
            # Создаем панель администратора
            admin_panel = self._create_admin_panel(game)
            
            await query.edit_message_text(
                text=admin_panel["text"],
                parse_mode='HTML',
                reply_markup=admin_panel["keyboard"]
            )
            
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    async def _handle_player_stats(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает статистику игрока"""
        try:
            user_id = query.from_user.id
            
            # Получаем статистику игрока
            stats = rewards_system.get_user_total_rewards(user_id)
            balance_info = balance_manager.get_user_balance_info(user_id)
            
            stats_text = (
                f"📊 <b>Ваша статистика:</b>\n\n"
                f"💰 Баланс: {balance_info['balance']} орешков\n"
                f"🏆 Всего наград: {stats['total_rewards']}\n"
                f"💎 Общая сумма: {stats['total_amount']} орешков\n"
                f"📈 Средняя награда: {stats['average_amount']:.1f} орешков\n"
                f"🎯 Максимальная награда: {stats['max_reward']} орешков"
            )
            
            await query.edit_message_text(
                text=stats_text,
                parse_mode='HTML'
            )
            
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    async def _handle_game_stats(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает статистику игры"""
        try:
            user_id = query.from_user.id
            
            # Находим игру пользователя
            game = self._find_user_game(user_id)
            if not game:
                await error_handler.show_alert(query, "game_not_found")
                return
            
            # Получаем статистику игры
            game_stats = game.get_game_statistics()
            
            stats_text = (
                f"📊 <b>Статистика игры:</b>\n\n"
                f"🔄 Раунд: {game_stats['current_round']}\n"
                f"👥 Живых игроков: {game_stats['alive_players']}\n"
                f"🦁 Хищников: {game_stats['predators']}\n"
                f"🌿 Травоядных: {game_stats['herbivores']}\n"
                f"⚔️ Убийств хищников: {game_stats['predator_kills']}\n"
                f"🛡️ Выживаний травоядных: {game_stats['herbivore_survivals']}\n"
                f"🦊 Краж лисы: {game_stats['fox_thefts']}\n"
                f"🦦 Защит бобра: {game_stats['beaver_protections']}\n"
                f"⏱️ Длительность: {game_stats['game_duration']:.1f} секунд"
            )
            
            await query.edit_message_text(
                text=stats_text,
                parse_mode='HTML'
            )
            
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    async def _handle_balance_info(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает информацию о балансе"""
        try:
            user_id = query.from_user.id
            
            # Получаем информацию о балансе
            balance_info = balance_manager.get_user_balance_info(user_id)
            
            balance_text = (
                f"💰 <b>Информация о балансе:</b>\n\n"
                f"💎 Текущий баланс: {balance_info['balance']} орешков\n"
                f"👤 Пользователь: {balance_info['user_id']}\n"
                f"📅 Создан: {balance_info.get('created_at', 'Неизвестно')}\n"
                f"🔄 Обновлен: {balance_info.get('updated_at', 'Неизвестно')}"
            )
            
            await query.edit_message_text(
                text=balance_text,
                parse_mode='HTML'
            )
            
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    async def _handle_rewards_info(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает информацию о наградах"""
        try:
            user_id = query.from_user.id
            
            # Получаем информацию о наградах
            rewards = rewards_system.get_user_rewards(user_id, limit=10)
            total_stats = rewards_system.get_user_total_rewards(user_id)
            
            rewards_text = (
                f"🏆 <b>Информация о наградах:</b>\n\n"
                f"📊 Всего наград: {total_stats['total_rewards']}\n"
                f"💎 Общая сумма: {total_stats['total_amount']} орешков\n"
                f"📈 Средняя награда: {total_stats['average_amount']:.1f} орешков\n\n"
                f"🎯 <b>Последние награды:</b>\n"
            )
            
            for reward in rewards[:5]:  # Показываем только последние 5
                rewards_text += f"• {reward['description']}: {reward['amount']} орешков\n"
            
            await query.edit_message_text(
                text=rewards_text,
                parse_mode='HTML'
            )
            
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    async def _handle_unknown_callback(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Обрабатывает неизвестный callback"""
        try:
            self.logger.warning(f"⚠️ Неизвестный callback: {callback_data}")
            await error_handler.show_alert(query, "unknown_error", "❌ Неизвестная команда")
            
        except Exception as e:
            await error_handler.handle_callback_error(query, e)
    
    def _find_user_game(self, user_id: int) -> Optional[Game]:
        """Находит игру пользователя"""
        try:
            # Получаем экземпляр бота
            from bot import ForestWolvesBot
            bot_instance = ForestWolvesBot.get_instance()
            
            if not bot_instance:
                self.logger.error(f"❌ Бот не инициализирован для пользователя {user_id}")
                return None
            
            self.logger.info(f"🔍 Поиск игры для пользователя {user_id}")
            self.logger.info(f"🔍 Всего игр: {len(bot_instance.games)}")
            self.logger.info(f"🔍 player_games: {bot_instance.player_games}")
            
            # Проверяем, участвует ли пользователь в игре
            if user_id not in bot_instance.player_games:
                # Если игрок не зарегистрирован в player_games, ищем по всем играм
                self.logger.info(f"🔍 Пользователь {user_id} не найден в player_games, ищем по всем играм...")
                for chat_id, game in bot_instance.games.items():
                    self.logger.info(f"🔍 Проверяем игру {chat_id}, игроки: {list(game.players.keys())}")
                    if user_id in game.players:
                        self.logger.info(f"✅ Найдена игра {chat_id} для пользователя {user_id}")
                        return game
                self.logger.warning(f"⚠️ Игра не найдена для пользователя {user_id}")
                return None
            
            # Получаем chat_id игры пользователя
            chat_id = bot_instance.player_games[user_id]
            self.logger.info(f"🔍 Ищем игру {chat_id} для пользователя {user_id}")
            
            # Возвращаем игру, если она существует
            game = bot_instance.games.get(chat_id)
            if game:
                self.logger.info(f"✅ Игра {chat_id} найдена для пользователя {user_id}")
            else:
                self.logger.warning(f"⚠️ Игра {chat_id} не найдена в bot_instance.games")
            return game
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска игры пользователя {user_id}: {e}")
            return None
    
    def _is_admin(self, user_id: int, chat_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        # Это упрощенная версия - в реальном боте нужно проверять права в Telegram
        return True  # Временно возвращаем True для тестирования
    
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
    
    def _get_phase_name(self, phase: GamePhase) -> str:
        """Получает название фазы"""
        phase_names = {
            GamePhase.WAITING: "ожидания",
            GamePhase.NIGHT: "ночи",
            GamePhase.DAY: "дня",
            GamePhase.VOTING: "голосования",
            GamePhase.GAME_OVER: "завершения игры"
        }
        return phase_names.get(phase, "неизвестной")
    
    def _create_admin_panel(self, game: Game) -> Dict[str, Any]:
        """Создает панель администратора"""
        try:
            # Формируем текст панели
            panel_text = (
                f"⚙️ <b>Панель администратора</b> ⚙️\n\n"
                f"🎮 Игра: {game.chat_id}\n"
                f"📋 Фаза: {self._get_phase_name(game.phase)}\n"
                f"🔄 Раунд: {game.current_round}\n"
                f"👥 Игроков: {len(game.players)}\n"
                f"💚 Живых: {len(game.get_alive_players())}\n\n"
                f"🛠️ <b>Доступные действия:</b>"
            )
            
            # Создаем клавиатуру
            keyboard = []
            
            if game.phase == GamePhase.DAY:
                keyboard.append([InlineKeyboardButton("🏁 Завершить обсуждение", callback_data="day_end_discussion")])
            elif game.phase == GamePhase.NIGHT:
                keyboard.append([InlineKeyboardButton("🌅 Завершить ночь", callback_data="night_end_actions")])
            elif game.phase == GamePhase.VOTING:
                keyboard.append([InlineKeyboardButton("🗳️ Завершить голосование", callback_data="voting_end")])
            
            keyboard.append([InlineKeyboardButton("🔄 Повторить этап", callback_data="repeat_current_phase")])
            keyboard.append([InlineKeyboardButton("📊 Статистика игры", callback_data="game_stats")])
            keyboard.append([InlineKeyboardButton("🏁 Завершить игру", callback_data="game_end")])
            keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="close_admin_panel")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            return {
                "text": panel_text,
                "keyboard": reply_markup
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания панели администратора: {e}")
            return {
                "text": "❌ Ошибка создания панели администратора",
                "keyboard": InlineKeyboardMarkup([])
            }
    
    async def _send_voting_results(self, game: Game, context: ContextTypes.DEFAULT_TYPE, exiled_player):
        """Отправляет результаты голосования"""
        try:
            if exiled_player:
                display_name = self.get_display_name(exiled_player.user_id, exiled_player.username, None)
                message = f"🗳️ <b>Результаты голосования</b> 🗳️\n\n❌ {display_name} изгнан из леса!"
            else:
                import random
                no_exile_messages = [
                    "🌳 Вечер опустился на лес. Животные спорили и шептались, но так и не решились изгнать кого-то.",
                    "🍂 Голоса разделились, и ни один зверь не оказался изгнан. Лес затаил дыхание.",
                    "🌲 Животные переглядывались с недоверием, но так и не нашли виновного.",
                    "🌙 Никого не изгнали. Лес уснул с нераскрытой загадкой."
                ]
                message = f"🗳️ <b>Результаты голосования</b> 🗳️\n\n{random.choice(no_exile_messages)}"
            
            await context.bot.send_message(
                chat_id=game.chat_id,
                text=message,
                parse_mode='HTML',
                message_thread_id=game.thread_id
            )
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки результатов голосования: {e}")

    async def _handle_wolf_action(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает действия волка"""
        try:
            user_id = query.from_user.id
            
            # Находим игру пользователя
            game = self._find_user_game(user_id)
            if not game:
                await query.answer("❌ Игра не найдена!", show_alert=True)
                return
            
            # Проверяем, что пользователь волк
            player = game.players.get(user_id)
            if not player or player.role != Role.WOLF:
                await query.answer("❌ Вы не волк!", show_alert=True)
                return
            
            # Проверяем фазу игры
            if game.phase != GamePhase.NIGHT:
                await query.answer("❌ Сейчас не ночная фаза!", show_alert=True)
                return
            
            # Обрабатываем действие
            if len(parts) >= 3 and parts[1] == "kill":
                target_id = int(parts[2])
                
                # Получаем ночные действия
                from bot import ForestWolvesBot
                bot_instance = ForestWolvesBot.get_instance()
                if bot_instance and game.chat_id in bot_instance.night_actions:
                    night_actions = bot_instance.night_actions[game.chat_id]
                    success = night_actions.set_wolf_target(user_id, target_id)
                    
                    if success:
                        target = game.players[target_id]
                        display_name = self.get_display_name(target.user_id, target.username, target.first_name)
                        await query.edit_message_text(f"🐺 Вы выбрали цель: {display_name}")
                    else:
                        await query.answer("❌ Не удалось установить цель!", show_alert=True)
                else:
                    await query.answer("❌ Ночные действия недоступны!", show_alert=True)
            
            elif len(parts) >= 2 and parts[1] == "skip":
                # Обрабатываем пропуск хода
                from bot import ForestWolvesBot
                bot_instance = ForestWolvesBot.get_instance()
                if bot_instance and game.chat_id in bot_instance.night_actions:
                    night_actions = bot_instance.night_actions[game.chat_id]
                    success = night_actions.skip_action(user_id)
                    
                    if success:
                        await query.edit_message_text("⏭️ Вы пропустили ход")
                    else:
                        await query.answer("❌ Не удалось пропустить ход!", show_alert=True)
                else:
                    await query.answer("❌ Ночные действия недоступны!", show_alert=True)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки действия волка: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def _handle_fox_action(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает действия лисы"""
        try:
            user_id = query.from_user.id
            
            # Находим игру пользователя
            game = self._find_user_game(user_id)
            if not game:
                await query.answer("❌ Игра не найдена!", show_alert=True)
                return
            
            # Проверяем, что пользователь лиса
            player = game.players.get(user_id)
            if not player or player.role != Role.FOX:
                await query.answer("❌ Вы не лиса!", show_alert=True)
                return
            
            # Проверяем фазу игры
            if game.phase != GamePhase.NIGHT:
                await query.answer("❌ Сейчас не ночная фаза!", show_alert=True)
                return
            
            # Обрабатываем действие
            if len(parts) >= 3 and parts[1] == "steal":
                target_id = int(parts[2])
                
                # Получаем ночные действия
                from bot import ForestWolvesBot
                bot_instance = ForestWolvesBot.get_instance()
                if bot_instance and game.chat_id in bot_instance.night_actions:
                    night_actions = bot_instance.night_actions[game.chat_id]
                    success = night_actions.set_fox_target(user_id, target_id)
                    
                    if success:
                        target = game.players[target_id]
                        display_name = self.get_display_name(target.user_id, target.username, target.first_name)
                        await query.edit_message_text(f"🦊 Вы выбрали цель для кражи: {display_name}")
                    else:
                        await query.answer("❌ Не удалось установить цель!", show_alert=True)
                else:
                    await query.answer("❌ Ночные действия недоступны!", show_alert=True)
            
            elif len(parts) >= 2 and parts[1] == "skip":
                # Обрабатываем пропуск хода
                from bot import ForestWolvesBot
                bot_instance = ForestWolvesBot.get_instance()
                if bot_instance and game.chat_id in bot_instance.night_actions:
                    night_actions = bot_instance.night_actions[game.chat_id]
                    success = night_actions.skip_action(user_id)
                    
                    if success:
                        await query.edit_message_text("⏭️ Вы пропустили ход")
                    else:
                        await query.answer("❌ Не удалось пропустить ход!", show_alert=True)
                else:
                    await query.answer("❌ Ночные действия недоступны!", show_alert=True)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки действия лисы: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def _handle_mole_action(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает действия крота"""
        try:
            user_id = query.from_user.id
            
            # Находим игру пользователя
            game = self._find_user_game(user_id)
            if not game:
                await query.answer("❌ Игра не найдена!", show_alert=True)
                return
            
            # Проверяем, что пользователь крот
            player = game.players.get(user_id)
            if not player or player.role != Role.MOLE:
                await query.answer("❌ Вы не крот!", show_alert=True)
                return
            
            # Проверяем фазу игры
            if game.phase != GamePhase.NIGHT:
                await query.answer("❌ Сейчас не ночная фаза!", show_alert=True)
                return
            
            # Обрабатываем действие
            if len(parts) >= 3 and parts[1] == "check":
                target_id = int(parts[2])
                
                # Получаем ночные действия
                from bot import ForestWolvesBot
                bot_instance = ForestWolvesBot.get_instance()
                if bot_instance and game.chat_id in bot_instance.night_actions:
                    night_actions = bot_instance.night_actions[game.chat_id]
                    success = night_actions.set_mole_target(user_id, target_id)
                    
                    if success:
                        target = game.players[target_id]
                        display_name = self.get_display_name(target.user_id, target.username, target.first_name)
                        await query.edit_message_text(f"🦫 Вы выбрали цель для проверки: {display_name}")
                    else:
                        await query.answer("❌ Не удалось установить цель!", show_alert=True)
                else:
                    await query.answer("❌ Ночные действия недоступны!", show_alert=True)
            
            elif len(parts) >= 2 and parts[1] == "skip":
                # Обрабатываем пропуск хода
                from bot import ForestWolvesBot
                bot_instance = ForestWolvesBot.get_instance()
                if bot_instance and game.chat_id in bot_instance.night_actions:
                    night_actions = bot_instance.night_actions[game.chat_id]
                    success = night_actions.skip_action(user_id)
                    
                    if success:
                        await query.edit_message_text("⏭️ Вы пропустили ход")
                    else:
                        await query.answer("❌ Не удалось пропустить ход!", show_alert=True)
                else:
                    await query.answer("❌ Ночные действия недоступны!", show_alert=True)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки действия крота: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)

    async def _handle_beaver_action(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, parts: list):
        """Обрабатывает действия бобра"""
        try:
            user_id = query.from_user.id
            
            # Находим игру пользователя
            game = self._find_user_game(user_id)
            if not game:
                await query.answer("❌ Игра не найдена!", show_alert=True)
                return
            
            # Проверяем, что пользователь бобр
            player = game.players.get(user_id)
            if not player or player.role != Role.BEAVER:
                await query.answer("❌ Вы не бобр!", show_alert=True)
                return
            
            # Проверяем фазу игры
            if game.phase != GamePhase.NIGHT:
                await query.answer("❌ Сейчас не ночная фаза!", show_alert=True)
                return
            
            # Обрабатываем действие
            if len(parts) >= 3 and parts[1] == "help":
                target_id = int(parts[2])
                
                # Получаем ночные действия
                from bot import ForestWolvesBot
                bot_instance = ForestWolvesBot.get_instance()
                if bot_instance and game.chat_id in bot_instance.night_actions:
                    night_actions = bot_instance.night_actions[game.chat_id]
                    success = night_actions.set_beaver_target(user_id, target_id)
                    
                    if success:
                        target = game.players[target_id]
                        display_name = self.get_display_name(target.user_id, target.username, target.first_name)
                        await query.edit_message_text(f"🦦 Вы выбрали цель для помощи: {display_name}")
                    else:
                        await query.answer("❌ Не удалось установить цель!", show_alert=True)
                else:
                    await query.answer("❌ Ночные действия недоступны!", show_alert=True)
            
            elif len(parts) >= 2 and parts[1] == "skip":
                # Обрабатываем пропуск хода
                from bot import ForestWolvesBot
                bot_instance = ForestWolvesBot.get_instance()
                if bot_instance and game.chat_id in bot_instance.night_actions:
                    night_actions = bot_instance.night_actions[game.chat_id]
                    success = night_actions.skip_action(user_id)
                    
                    if success:
                        await query.edit_message_text("⏭️ Вы пропустили ход")
                    else:
                        await query.answer("❌ Не удалось пропустить ход!", show_alert=True)
                else:
                    await query.answer("❌ Ночные действия недоступны!", show_alert=True)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки действия бобра: {e}")
            await query.answer("❌ Произошла ошибка!", show_alert=True)


# Глобальный экземпляр обработчика callback'ов
callback_handler = CallbackHandler()
