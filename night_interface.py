from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Dict, List
from game_logic import Game, Role
from night_actions import NightActions

class NightInterface:
    def __init__(self, game: Game, night_actions: NightActions):
        self.game = game
        self.night_actions = night_actions
    
    async def send_night_actions_menu(self, context: ContextTypes.DEFAULT_TYPE, player_id: int):
        """Отправляет меню ночных действий для игрока"""
        actions = self.night_actions.get_player_actions(player_id)
        
        if not actions:
            return
        
        player = self.game.players.get(player_id)
        if not player:
            return
        
        # Создаем заголовок в зависимости от роли
        role_headers = {
            "wolf": "🐺 Выберите цель для охоты:",
            "fox": "🦊 Выберите цель для кражи запасов:",
            "beaver": "🦦 Выберите зверя для помощи:",
            "mole": "🦫 Выберите зверя для проверки:"
        }
        
        header = role_headers.get(actions["type"], "Выберите действие:")
        
        # Создаем клавиатуру с целями
        keyboard = []
        for target in actions["targets"]:
            # Добавляем отметку, если это текущая цель
            current_mark = "✅ " if actions.get("current_target") == target.user_id else ""
            button_text = f"{current_mark}{target.username}"
            
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"night_{actions['type']}_{target.user_id}"
            )])
        
        # Добавляем кнопку "Пропустить ход" если это не первая ночь
        if self.game.current_round > 1:
            keyboard.append([InlineKeyboardButton(
                "⏭️ Пропустить ход",
                callback_data=f"night_{actions['type']}_skip"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=header,
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Не удалось отправить меню ночных действий игроку {player_id}: {e}")
    
    async def handle_night_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает выбор ночного действия"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data.split('_')
        
        if len(data) != 3:
            return
        
        action_type = data[1]
        target_id = data[2]
        
        # Проверяем, что игрок действительно в игре
        if user_id not in self.game.players:
            await query.edit_message_text("❌ Вы не участвуете в игре!")
            return
        
        player = self.game.players[user_id]
        if not player.is_alive:
            await query.edit_message_text("❌ Вы мертвы и не можете совершать действия!")
            return
        
        # Обрабатываем действие в зависимости от типа
        success = False
        message = ""
        
        if action_type == "wolf" and player.role == Role.WOLF:
            if target_id == "skip":
                success = True
                message = "⏭️ Вы пропустили ход"
            else:
                success = self.night_actions.set_wolf_target(user_id, int(target_id))
                if success:
                    target = self.game.players[int(target_id)]
                    message = f"🐺 Вы выбрали цель: {target.username}"
                else:
                    message = "❌ Не удалось установить цель"
        
        elif action_type == "fox" and player.role == Role.FOX:
            if target_id == "skip":
                success = True
                message = "⏭️ Вы пропустили ход"
            else:
                success = self.night_actions.set_fox_target(user_id, int(target_id))
                if success:
                    target = self.game.players[int(target_id)]
                    message = f"🦊 Вы выбрали цель для кражи: {target.username}"
                else:
                    message = "❌ Не удалось установить цель"
        
        elif action_type == "beaver" and player.role == Role.BEAVER:
            if target_id == "skip":
                success = True
                message = "⏭️ Вы пропустили ход"
            else:
                success = self.night_actions.set_beaver_target(user_id, int(target_id))
                if success:
                    target = self.game.players[int(target_id)]
                    message = f"🦦 Вы выбрали зверя для помощи: {target.username}"
                else:
                    message = "❌ Не удалось установить цель"
        
        elif action_type == "mole" and player.role == Role.MOLE:
            if target_id == "skip":
                success = True
                message = "⏭️ Вы пропустили ход"
            else:
                success = self.night_actions.set_mole_target(user_id, int(target_id))
                if success:
                    target = self.game.players[int(target_id)]
                    message = f"🦫 Вы выбрали зверя для проверки: {target.username}"
                else:
                    message = "❌ Не удалось установить цель"
        
        else:
            message = "❌ У вас нет прав для этого действия!"
        
        if success:
            # Обновляем сообщение с подтверждением
            await query.edit_message_text(
                f"{message}\n\n"
                "🌙 Ждите окончания ночной фазы..."
            )
        else:
            # Показываем ошибку
            await query.edit_message_text(
                f"{message}\n\n"
                "Попробуйте выбрать другую цель."
            )
    
    async def send_night_results(self, context: ContextTypes.DEFAULT_TYPE, results: Dict[str, List[str]]):
        """Отправляет результаты ночных действий всем игрокам"""
        if not results:
            return
        
        # Формируем сообщение с результатами
        message = "🌙 Результаты ночи:\n\n"
        
        # Добавляем результаты по категориям
        if results["wolves"]:
            message += "🐺 Действия волков:\n"
            for action in results["wolves"]:
                message += f"• {action}\n"
            message += "\n"
        
        if results["fox"]:
            message += "🦊 Действия лисы:\n"
            for action in results["fox"]:
                message += f"• {action}\n"
            message += "\n"
        
        if results["beaver"]:
            message += "🦦 Действия бобра:\n"
            for action in results["beaver"]:
                message += f"• {action}\n"
            message += "\n"
        
        if results["mole"]:
            message += "🦫 Действия крота:\n"
            for action in results["mole"]:
                message += f"• {action}\n"
            message += "\n"
        
        if results["deaths"]:
            message += "💀 Смерти:\n"
            for death in results["deaths"]:
                message += f"• {death}\n"
            message += "\n"
        
        # Отправляем результаты в чат
        try:
            await context.bot.send_message(
                chat_id=self.game.chat_id,
                text=message
            )
        except Exception as e:
            print(f"Не удалось отправить результаты ночи: {e}")
    
    async def send_role_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет напоминания о ролях игрокам с ночными действиями"""
        night_roles = [Role.WOLF, Role.FOX, Role.BEAVER, Role.MOLE]
        
        for player in self.game.players.values():
            if player.is_alive and player.role in night_roles:
                role_info = self.get_role_info(player.role)
                
                reminder_text = (
                    f"🌙 Напоминание о вашей роли:\n\n"
                    f"🎭 {role_info['name']}\n"
                    f"📝 {role_info['description']}\n\n"
                    "Используйте меню ниже для выбора действий:"
                )
                
                try:
                    await context.bot.send_message(
                        chat_id=player.user_id,
                        text=reminder_text
                    )
                    
                    # Отправляем меню действий
                    await self.send_night_actions_menu(context, player.user_id)
                    
                except Exception as e:
                    print(f"Не удалось отправить напоминание игроку {player.user_id}: {e}")
    
    def get_role_info(self, role: Role) -> Dict[str, str]:
        """Возвращает информацию о роли"""
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
                "description": "Вы травоядный! По ночам вы роете норки и узнаете команды других зверей."
            },
            Role.BEAVER: {
                "name": "🦦 Бобёр",
                "description": "Вы травоядный! Вы можете возвращать украденные запасы другим зверям."
            }
        }
        return role_info.get(role, {"name": "Неизвестно", "description": "Роль не определена"})
