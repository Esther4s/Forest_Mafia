from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Dict, List
from game_logic import Game, Role
from night_actions import NightActions

class NightInterface:
    def __init__(self, game: Game, night_actions: NightActions, get_display_name_func=None):
        self.game = game
        self.night_actions = night_actions
        self.get_display_name = get_display_name_func

    async def send_night_actions_menu(self, context: ContextTypes.DEFAULT_TYPE, player_id: int):
        """Отправляет меню ночных действий для игрока"""
        print(f"🌙 send_night_actions_menu вызван для игрока {player_id}")
        actions = self.night_actions.get_player_actions(player_id)
        print(f"🌙 Действия для игрока {player_id}: {actions}")

        if not actions:
            print(f"❌ Нет действий для игрока {player_id}")
            return

        player = self.game.players.get(player_id)
        if not player:
            print(f"❌ Игрок {player_id} не найден в игре")
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
            if self.get_display_name:
                display_name = self.get_display_name(target.user_id, target.username, target.first_name)
            else:
                display_name = target.username or target.first_name or f"ID:{target.user_id}"
            button_text = f"{current_mark}{display_name}"

            # Создаем правильный формат callback_data для каждой роли
            if actions['type'] == 'wolf':
                callback_data = f"wolf_kill_{target.user_id}"
            elif actions['type'] == 'fox':
                callback_data = f"fox_steal_{target.user_id}"
            elif actions['type'] == 'beaver':
                callback_data = f"beaver_help_{target.user_id}"
            elif actions['type'] == 'mole':
                callback_data = f"mole_check_{target.user_id}"
            else:
                callback_data = f"night_{actions['type']}_{target.user_id}"

            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=callback_data
            )])

        # Всегда добавляем кнопку "Пропустить ход"
        if actions['type'] == 'wolf':
            skip_callback = "wolf_skip"
        elif actions['type'] == 'fox':
            skip_callback = "fox_skip"
        elif actions['type'] == 'beaver':
            skip_callback = "beaver_skip"
        elif actions['type'] == 'mole':
            skip_callback = "mole_skip"
        else:
            skip_callback = f"night_{actions['type']}_skip"

        keyboard.append([InlineKeyboardButton(
            "⏭️ Пропустить ход",
            callback_data=skip_callback
        )])


        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            print(f"🌙 Отправка меню игроку {player_id}: {header}")
            print(f"🌙 Клавиатура: {len(keyboard)} кнопок")
            await context.bot.send_message(
                chat_id=player_id,
                text=header,
                reply_markup=reply_markup
            )
            print(f"✅ Меню успешно отправлено игроку {player_id}")
        except Exception as e:
            print(f"❌ Не удалось отправить меню ночных действий игроку {player_id}: {e}")

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


        # Проверяем возврат к действиям
        if len(data) >= 4 and data[1] == "back" and data[2] == "to" and data[3] == "actions":
            await self.send_night_actions_menu(context, user_id)
            return

        if len(data) < 2 or len(data) > 3:
            return

        # Обрабатываем разные форматы callback_data
        if len(data) == 2 and data[1] == 'skip':
            # Формат для пропуска: wolf_skip, fox_skip, etc.
            action_type = data[0]  # wolf, fox, beaver, mole
            target_id = "skip"
        elif len(data) == 3 and data[1] in ['kill', 'steal', 'help', 'check']:
            # Новый формат: wolf_kill_123, fox_steal_123, etc.
            action_type = data[0]  # wolf, fox, beaver, mole
            target_id = data[2]
        else:
            # Старый формат: wolf_123, fox_123, etc.
            action_type = data[1]
            target_id = data[2]

        # Обрабатываем действие в зависимости от типа
        success = False
        message = ""
        
        # Отладочная информация
        print(f"DEBUG: action_type = {action_type}, player.role = {player.role}")
        print(f"DEBUG: target_id = {target_id}")
        print(f"DEBUG: night_actions = {self.night_actions}")
        print(f"DEBUG: game = {self.game}")

        if action_type == "wolf" and player.role == Role.WOLF:
            if target_id == "skip":
                if self.night_actions:
                    success = self.night_actions.skip_action(user_id)
                    message = "⏭️ Вы пропустили ход"
                else:
                    success = False
                    message = "❌ Ошибка: ночные действия не инициализированы"
            else:
                if self.night_actions:
                    success = self.night_actions.set_wolf_target(user_id, int(target_id))
                else:
                    success = False
                    message = "❌ Ошибка: ночные действия не инициализированы"
                if success:
                    target = self.game.players[int(target_id)]
                    # Получаем отображаемое имя через get_display_name
                    if self.get_display_name:
                        display_name = self.get_display_name(target.user_id, target.username, None)
                    else:
                        display_name = target.username or f"ID:{target.user_id}"
                    message = f"🐺 Вы выбрали цель: {display_name}"
                else:
                    message = "❌ Не удалось установить цель"

        elif action_type == "fox" and player.role == Role.FOX:
            if target_id == "skip":
                if self.night_actions:
                    success = self.night_actions.skip_action(user_id)
                    message = "⏭️ Вы пропустили ход"
                else:
                    success = False
                    message = "❌ Ошибка: ночные действия не инициализированы"
            else:
                if self.night_actions:
                    success = self.night_actions.set_fox_target(user_id, int(target_id))
                else:
                    success = False
                    message = "❌ Ошибка: ночные действия не инициализированы"
                if success:
                    target = self.game.players[int(target_id)]
                    # Получаем отображаемое имя через get_display_name
                    if self.get_display_name:
                        display_name = self.get_display_name(target.user_id, target.username, None)
                    else:
                        display_name = target.username or f"ID:{target.user_id}"
                    message = f"🦊 Вы выбрали цель для кражи: {display_name}"
                else:
                    message = "❌ Не удалось установить цель"

        elif action_type == "beaver" and player.role == Role.BEAVER:
            if target_id == "skip":
                if self.night_actions:
                    success = self.night_actions.skip_action(user_id)
                    message = "⏭️ Вы пропустили ход"
                else:
                    success = False
                    message = "❌ Ошибка: ночные действия не инициализированы"
            else:
                if self.night_actions:
                    success = self.night_actions.set_beaver_target(user_id, int(target_id))
                else:
                    success = False
                    message = "❌ Ошибка: ночные действия не инициализированы"
                if success:
                    target = self.game.players[int(target_id)]
                    # Получаем отображаемое имя через get_display_name
                    if self.get_display_name:
                        display_name = self.get_display_name(target.user_id, target.username, None)
                    else:
                        display_name = target.username or f"ID:{target.user_id}"
                    message = f"🦦 Вы выбрали зверя для помощи: {display_name}"
                else:
                    message = "❌ Не удалось установить цель"

        elif action_type == "mole" and player.role == Role.MOLE:
            if target_id == "skip":
                if self.night_actions:
                    success = self.night_actions.skip_action(user_id)
                    message = "⏭️ Вы пропустили ход"
                else:
                    success = False
                    message = "❌ Ошибка: ночные действия не инициализированы"
            else:
                if self.night_actions:
                    success = self.night_actions.set_mole_target(user_id, int(target_id))
                else:
                    success = False
                    message = "❌ Ошибка: ночные действия не инициализированы"
                if success:
                    target = self.game.players[int(target_id)]
                    # Получаем отображаемое имя через get_display_name
                    if self.get_display_name:
                        display_name = self.get_display_name(target.user_id, target.username, None)
                    else:
                        display_name = target.username or f"ID:{target.user_id}"
                    message = f"🦫 Вы выбрали зверя для проверки: {display_name}"
                else:
                    message = "❌ Не удалось установить цель"

        else:
            print(f"DEBUG: Попадание в else - action_type: {action_type}, player.role: {player.role}")
            print(f"DEBUG: Условия не выполнены:")
            print(f"  - wolf: {action_type == 'wolf' and player.role == Role.WOLF}")
            print(f"  - fox: {action_type == 'fox' and player.role == Role.FOX}")
            print(f"  - beaver: {action_type == 'beaver' and player.role == Role.BEAVER}")
            print(f"  - mole: {action_type == 'mole' and player.role == Role.MOLE}")
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
        else:
            # Если никто не умер, добавляем случайное сообщение
            import random
            no_kill_messages = [
                "🌌 Волки выли на луну, но так и не нашли добычи. Утром все проснулись целыми и невредимыми. Но сколько ещё продлится эта удача?",
                "🌲 Ночь прошла тихо. Волчьи лапы бродили по лесу, но никто не был тронут. Животные встречали рассвет с облегчением — пока.",
                "🍃 Волки кружили по поляне, но их пасти остались голодными. Утро настало без потерь, и лес зашептал: «Что это значит?..»",
                "🌙 Звёзды наблюдали, как волки искали жертву, но этой ночью зубы остались пустыми. Животные обняли рассвет с радостью и страхом."
            ]
            random_message = random.choice(no_kill_messages)
            message += f"🌙 {random_message}\n\n"

        # Отправляем результаты в чат
        try:
            await context.bot.send_message(
                chat_id=self.game.chat_id,
                text=message,
                message_thread_id=self.game.thread_id
            )
        except Exception as e:
            print(f"Не удалось отправить результаты ночи: {e}")
        
        # Сообщения белочки отправляются только при изгнании (голосовании)
        # При смерти от волка отправляется специальное сообщение через send_wolf_victim_pm

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
            if self.get_display_name:
                player_name = self.get_display_name(player.user_id, player.username, player.first_name)
            else:
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
        # Теперь роли отправляются с кнопками в send_roles_to_players
        # Этот метод больше не нужен, так как роли отправляются сразу с кнопками
        pass

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