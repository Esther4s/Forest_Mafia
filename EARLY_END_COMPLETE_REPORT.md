# ⚡ Отчет об исправлении досрочного завершения голосования и ночной фазы

## 🎯 Проблема

**Нужно было добавить автоматическое досрочное завершение:**
- **Голосования** - если все участники проголосовали (включая пропуски)
- **Ночной фазы** - если все игроки выполнили ночные действия (включая пропуски)

## ✅ Исправления

### 1. 🔧 **Досрочное завершение голосования**

#### **Проблема:** 
Пропуск голосования не учитывался в подсчете голосов, поэтому голосование не завершалось досрочно.

#### **Исправление:**
```python
# В bot.py - handle_vote
if query.data == "vote_skip":
    # Добавляем голос "пропустить" в игру
    success, already_voted = game.vote(user_id, None)  # None означает пропуск
    if success:
        await query.edit_message_text("⏭️ Вы пропустили голосование!")
        
        # Проверяем, все ли проголосовали (включая пропуски)
        if hasattr(game, 'total_voters') and len(game.votes) >= game.total_voters:
            # Все проголосовали - завершаем досрочно
            asyncio.create_task(self.complete_exile_voting_early(context, game))
```

#### **Также исправлено в `game_logic.py`:**
```python
def vote(self, voter_id: int, target_id: Optional[int]) -> tuple[bool, bool]:
    """
    target_id может быть None для пропуска голосования
    """
    # Если target_id не None, проверяем цель
    if target_id is not None:
        target = self.players.get(target_id)
        if not target or not target.is_alive:
            return False, False
        # Защита от голосования за себя
        if voter_id == target_id:
            return False, False
    
    self.votes[voter_id] = target_id
    return True, already_voted
```

### 2. 🌙 **Досрочное завершение ночной фазы**

#### **Проблема:**
Ночная фаза ждала полные 60 секунд, даже если все игроки уже выполнили действия.

#### **Исправление в `night_actions.py`:**
```python
def skip_action(self, player_id: int) -> bool:
    """Пропускает ночное действие для игрока"""
    player = self.game.players.get(player_id)
    if not player or not player.is_alive:
        return False
    
    # Добавляем в список пропустивших
    self.skipped_actions.add(player_id)
    
    # Удаляем из всех списков целей (если был)
    self.wolf_targets.pop(player_id, None)
    self.fox_targets.pop(player_id, None)
    self.beaver_targets.pop(player_id, None)
    self.mole_targets.pop(player_id, None)
    
    return True

def are_all_actions_completed(self) -> bool:
    """Проверяет, все ли игроки выполнили ночные действия"""
    alive_players = [p for p in self.game.players.values() if p.is_alive]
    
    for player in alive_players:
        if player.role == Role.WOLF:
            # Волк должен выбрать цель или пропустить
            if player.user_id not in self.wolf_targets and player.user_id not in self.skipped_actions:
                return False
        elif player.role == Role.FOX:
            # Лиса должна выбрать цель или пропустить
            if player.user_id not in self.fox_targets and player.user_id not in self.skipped_actions:
                return False
        # ... аналогично для других ролей
    
    return True
```

#### **Исправление в `night_interface.py`:**
```python
if action_type == "wolf" and player.role == Role.WOLF:
    if target_id == "skip":
        success = self.night_actions.skip_action(user_id)  # Используем новый метод
        message = "⏭️ Вы пропустили ход"
    else:
        success = self.night_actions.set_wolf_target(user_id, int(target_id))
        # ... остальная логика
```

#### **Исправление в `bot.py`:**
```python
async def night_phase_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, game: Game):
    """Таймер для ночной фазы с проверкой досрочного завершения"""
    for i in range(60):  # Проверяем каждую секунду в течение 60 секунд
        await asyncio.sleep(1)
        
        # Проверяем, все ли игроки выполнили ночные действия
        if game.phase == GamePhase.NIGHT and game.chat_id in self.night_actions:
            night_actions = self.night_actions[game.chat_id]
            if night_actions.are_all_actions_completed():
                logger.info("Все игроки выполнили ночные действия! Завершаем ночь досрочно.")
                await context.bot.send_message(
                    chat_id=game.chat_id, 
                    text="⚡ Все игроки выполнили ночные действия! Ночь завершена досрочно.",
                    message_thread_id=game.thread_id
                )
                await self.process_night_phase(update, context, game)
                await self.start_day_phase(update, context, game)
                return
```

## 🧪 Протестированные функции

### ✅ **Голосование:**
- **Голосование за игрока** - работает ✅
- **Пропуск голосования** - работает ✅
- **Изменение голоса** - работает ✅
- **Досрочное завершение** - работает ✅

### ✅ **Ночные действия:**
- **Установка целей** - работает ✅
- **Пропуск действий** - работает ✅
- **Проверка завершения** - работает ✅
- **Досрочное завершение ночи** - работает ✅

### ✅ **Смешанные сценарии:**
- **Часть игроков выбирает цели, часть пропускает** - работает ✅
- **Очистка действий** - работает ✅
- **Повторные действия** - работают ✅

## 🎮 Как теперь работает

### **Голосование:**
1. **Игроки голосуют** за других игроков или пропускают
2. **Система отслеживает** все голоса (включая пропуски)
3. **Когда все проголосовали** - голосование завершается досрочно
4. **Отображается сообщение** "⚡ Все игроки проголосовали! Голосование завершено досрочно."

### **Ночная фаза:**
1. **Игроки выполняют ночные действия** или пропускают ход
2. **Система отслеживает** все действия (включая пропуски)
3. **Когда все выполнили действия** - ночь завершается досрочно
4. **Отображается сообщение** "⚡ Все игроки выполнили ночные действия! Ночь завершена досрочно."

## 🔧 Технические детали

### **Новые методы:**
- `NightActions.skip_action(player_id)` - пропуск ночного действия
- `NightActions.are_all_actions_completed()` - проверка завершения всех действий
- `Game.vote(voter_id, target_id)` - теперь принимает `None` для пропуска

### **Новые атрибуты:**
- `NightActions.skipped_actions` - множество игроков, пропустивших ход

### **Обновленные таймеры:**
- `voting_timer()` - проверяет досрочное завершение каждую секунду
- `night_phase_timer()` - проверяет досрочное завершение каждую секунду
- `wolf_voting_timer()` - уже имел проверку досрочного завершения

## 📊 Результаты тестирования

**Тест показал отличные результаты:**
- ✅ **Голосование** - все функции работают корректно
- ✅ **Ночные действия** - все функции работают корректно
- ✅ **Пропуски** - учитываются правильно
- ✅ **Досрочное завершение** - работает для обеих фаз

## 🎉 Результат

**Досрочное завершение голосования и ночной фазы теперь работает идеально!**

### ✅ **Что исправлено:**
- **Голосование завершается досрочно** когда все проголосовали (включая пропуски)
- **Ночная фаза завершается досрочно** когда все выполнили действия (включая пропуски)
- **Пропуски учитываются** в подсчете завершения
- **Система отслеживает** все действия и голоса в реальном времени
- **Улучшен пользовательский опыт** - нет лишнего ожидания

### 🎮 **Преимущества:**
- **Быстрее игра** - нет лишнего ожидания
- **Лучший UX** - игроки не ждут зря
- **Автоматизация** - система сама определяет когда завершать
- **Гибкость** - поддерживает как действия, так и пропуски

**Теперь игра работает максимально эффективно и удобно для игроков!** 🎉

---
*Отчет создан после успешного исправления и тестирования всех функций*

