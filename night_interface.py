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
            "wolf": "🐺 Придёт серенький волчок и укусит за бочок! 🐺 Кхм... Кому же этот кусь достанется этой ночью?",
            "fox": "🦊 Ну что, хитрая Лиса? 🦊 Кого обворуем этой ночью?",
            "beaver": "🦦 Ну что, дружок Бобёр? Устроим кому-нибудь утром приятный и вкусный сюрприз?",
            "mole": "🦫 Ну что, Крот? К кому в норку ты хочешь заглянуть?"
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

        # Всегда добавляем кнопку "Пропустить ход"
        keyboard.append([InlineKeyboardButton(
            "⏭️ Пропустить ход",
            callback_data=f"night_{actions['type']}_skip"
        )])

        # Добавляем кнопку "Посмотреть роль"
        keyboard.append([InlineKeyboardButton(
            "🎭 Посмотреть мою роль",
            callback_data=f"night_view_role_{player_id}"
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
        
        # Отладочная информация
        print(f"DEBUG: Обработка ночного действия для пользователя {user_id}")
        print(f"DEBUG: Callback data: {query.data}")
        print(f"DEBUG: Разделенные данные: {data}")

        # Проверяем, что игрок действительно в игре
        if user_id not in self.game.players:
            await query.answer("❌ Вы не участвуете в игре!", show_alert=True)
            return

        player = self.game.players[user_id]
        if not player.is_alive:
            await query.answer("❌ Вы мертвы и не можете совершать действия!", show_alert=True)
            return

        # Проверяем, если это просмотр роли
        if len(data) >= 3 and data[1] == "view" and data[2] == "role":
            role_info = self.get_role_info(player.role)
            team_name = "🦁 Хищники" if player.team.name == "PREDATORS" else "🌿 Травоядные"

            role_modal_text = (
                f"🎭 Ваша роль в игре:\n\n"
                f"👤 {role_info['name']}\n"
                f"🏴 Команда: {team_name}\n\n"
                f"📝 Описание:\n{role_info['description']}\n\n"
                f"🌙 Раунд: {self.game.current_round}\n"
                f"💚 Статус: {'Живой' if player.is_alive else 'Мертвый'}"
            )

            # Отправляем роль в личные сообщения вместо замены текущего сообщения
            try:
                await context.bot.send_message(chat_id=user_id, text=role_modal_text)
                await query.answer("✅ Информация о вашей роли отправлена в личные сообщения!", show_alert=True)
            except Exception as e:
                await query.answer("❌ Не удалось отправить сообщение в личку!", show_alert=True)
            return

        # Проверяем возврат к действиям
        if len(data) >= 4 and data[1] == "back" and data[2] == "to" and data[3] == "actions":
            await self.send_night_actions_menu(context, user_id)
            return

        if len(data) != 3:
            return

        action_type = data[1]
        target_id = data[2]

        # Обрабатываем действие в зависимости от типа
        success = False
        message = ""

        if action_type == "wolf" and player.role == Role.WOLF:
            if target_id == "skip":
                success = self.night_actions.skip_action(user_id)
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
                success = self.night_actions.skip_action(user_id)
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
                success = self.night_actions.skip_action(user_id)
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
                success = self.night_actions.skip_action(user_id)
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
            message += "🐺 Лес пронзил далёкий стихающий вой.\n"
            for action in results["wolves"]:
                message += f"• {action}\n"
            message += "\n"

        if results["fox"]:
            message += "🦊 А среди деревьев промелькнуло что-то рыжее и проворное.\n"
            for action in results["fox"]:
                message += f"• {action}\n"
            message += "Это была хитрая Лиса! Что же ей было нужно в этом домике?\n\n"

        if results["beaver"]:
            message += "🦦 А вот Бобру тоже не спится и он шастает по округе с кузовком.\n"
            for action in results["beaver"]:
                message += f"• {action}\n"
            message += "Наверное, Бобёр обрадовал кого-то своими пирожками и ушёл спать.\n\n"

        if results["mole"]:
            message += "🦫 А на работу вышел ночной Крот. Всю ночь он копал тоннель к домику одного из своих соседей…\n"
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
                text=message,
                message_thread_id=self.game.thread_id
            )
        except Exception as e:
            print(f"Не удалось отправить результаты ночи: {e}")
        
        # Отправляем сообщения белочки умершим игрокам
        await self._send_squirrel_messages(context, results)

    async def _send_squirrel_messages(self, context: ContextTypes.DEFAULT_TYPE, results: Dict[str, List[str]]):
        """Отправляет сообщения белочки умершим игрокам"""
        try:
            # Получаем русское название роли
            from role_translator import get_role_name_russian
            
            # Собираем всех умерших игроков
            dead_players = []
            
            # Проверяем результаты волков
            if results.get("wolves"):
                for action in results["wolves"]:
                    # Извлекаем имя игрока из сообщения (например: "🐺 Волки съели Plo337 (Крот)!")
                    if "съели" in action:
                        # Находим имя между "съели" и "("
                        start = action.find("съели") + 6
                        end = action.find("(")
                        if start > 5 and end > start:
                            player_name = action[start:end].strip()
                            # Находим игрока по имени
                            for player in self.game.players.values():
                                if (player.username == player_name or 
                                    player.first_name == player_name or 
                                    f"{player.first_name} {player.last_name}".strip() == player_name):
                                    if not player.is_alive:
                                        dead_players.append(player)
                                    break
            
            # Проверяем результаты лисы (смерти от кражи)
            if results.get("deaths"):
                for death in results["deaths"]:
                    # Извлекаем имя игрока из сообщения
                    if "умер" in death or "погиб" in death:
                        # Находим имя игрока в сообщении
                        for player in self.game.players.values():
                            if (player.username in death or 
                                player.first_name in death or 
                                f"{player.first_name} {player.last_name}".strip() in death):
                                if not player.is_alive and player not in dead_players:
                                    dead_players.append(player)
                                break
            
            # Отправляем сообщения белочки каждому умершему игроку
            for player in dead_players:
                await self._send_squirrel_message_to_player(context, player)
                
        except Exception as e:
            print(f"Ошибка при отправке сообщений белочки: {e}")

    async def _send_squirrel_message_to_player(self, context: ContextTypes.DEFAULT_TYPE, player):
        """Отправляет сообщение белочки конкретному игроку"""
        try:
            # Получаем русское название роли
            from role_translator import get_role_name_russian
            role_name = get_role_name_russian(player.role)
            
            # Формируем имя игрока
            player_name = player.username or player.first_name or "Игрок"
            
            squirrel_message = (
                f"🍂 Осенний лист упал 🍂\n\n"
                f"🐿️ Маленькая белочка с печальными глазками подошла к тебе, {player_name}...\n\n"
                f"💭 \"Лес больше не нуждается в твоих услугах, {player_name},\" - говорит она.\n"
                f"🌅 \"Солнце заходит для тебя в этом мире.\"\n\n"
                f"🎭 Твоя роль: {role_name}\n"
                f"🚫 Твои действия в игре завершены.\n"
                f"🔇 Молчание - твоя новая обязанность.\n\n"
                f"🌌 Белочка бережно забирает твою душу, чтобы отнести её в звёздный лес...\n\n"
                f"⭐️ До свидания, {player_name} ⭐️"
            )
            
            # Отправляем сообщение в личку
            await context.bot.send_message(
                chat_id=player.user_id,
                text=squirrel_message
            )
            
            print(f"Отправлено сообщение белочки игроку {player_name} ({player.user_id})")
            
        except Exception as e:
            print(f"Ошибка при отправке сообщения белочки игроку {player.user_id}: {e}")

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
                "description": "Вы травоядный! По ночам вы роете норки и узнаёте команды других зверей."
            },
            Role.BEAVER: {
                "name": "🦦 Бобер",
                "description": "Вы травоядный! Вы можете возвращать украденные запасы другим зверям."
            }
        }
        return role_info.get(role, {"name": "Неизвестно", "description": "Роль не определена"})