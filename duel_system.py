"""
Система дуэлей 1v1 для Forest Mafia Bot
Реализует режим "Ежики" с 7 ролями и 4 этапами
"""

import asyncio
import random
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

class DuelRole(Enum):
    """Роли в дуэли"""
    WOLF = "wolf"        # 🐺 Волк — атакует ночью
    HARE = "hare"        # 🐇 Заяц — защита/уклон
    FOX = "fox"          # 🦊 Лиса — может поменяться ролями
    BEAVER = "beaver"    # 🦫 Бобр — двойной щит
    OWL = "owl"          # 🦉 Сова — угадывает ход соперника
    BOAR = "boar"        # 🐗 Кабан — атака пробивает защиту
    HEDGEHOG = "hedgehog" # 🦔 Ёж — при атаке оба теряют жизнь

class DuelPhase(Enum):
    """Фазы дуэли"""
    WAITING = "waiting"      # Ожидание подтверждения
    NIGHT = "night"          # 🌑 Ночь — выбор карт
    DAY = "day"              # ☀️ День — викторина
    CASINO = "casino"        # 🎰 Казино — бросок кубика
    FINAL = "final"          # 🔮 Финал — угадайка
    FINISHED = "finished"    # Завершена

class DuelAction(Enum):
    """Действия в дуэли"""
    ATTACK = "attack"        # 🗡 Атака
    DEFENSE = "defense"      # 🛡 Защита
    TRICK = "trick"          # 🎭 Обман

@dataclass
class DuelPlayer:
    """Игрок в дуэли"""
    user_id: int
    username: str
    role: DuelRole
    lives: int = 3
    special_used: bool = False
    last_action: Optional[DuelAction] = None

@dataclass
class Duel:
    """Дуэль"""
    duel_id: int
    chat_id: int
    player1: DuelPlayer
    player2: DuelPlayer
    phase: DuelPhase = DuelPhase.WAITING
    current_round: int = 0
    winner: Optional[int] = None
    created_at: datetime = None

class DuelSystem:
    """Система управления дуэлями"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.active_duels: Dict[int, Duel] = {}
        self.duel_invitations: Dict[int, Dict] = {}  # chat_id -> invitation_data
        
        # Роли и их описания
        self.roles_info = {
            DuelRole.WOLF: {
                "name": "🐺 Волк",
                "description": "Атакует ночью с удвоенной силой",
                "special": "Ночная атака: +1 урон в фазе ночи"
            },
            DuelRole.HARE: {
                "name": "🐇 Заяц", 
                "description": "Мастер защиты и уклонения",
                "special": "Уклонение: 50% шанс избежать атаки"
            },
            DuelRole.FOX: {
                "name": "🦊 Лиса",
                "description": "Хитрая, может поменяться ролями",
                "special": "Обмен ролями: один раз за дуэль"
            },
            DuelRole.BEAVER: {
                "name": "🦫 Бобр",
                "description": "Строитель, ставит двойной щит",
                "special": "Двойной щит: блокирует 2 атаки"
            },
            DuelRole.OWL: {
                "name": "🦉 Сова",
                "description": "Мудрая, угадывает ходы соперника",
                "special": "Предсказание: угадывает действие соперника"
            },
            DuelRole.BOAR: {
                "name": "🐗 Кабан",
                "description": "Пробивает защиту, но слаб против обмана",
                "special": "Пробивание: атака проходит через защиту"
            },
            DuelRole.HEDGEHOG: {
                "name": "🦔 Ёж",
                "description": "При атаке ранит и себя, и соперника",
                "special": "Шипы: при атаке оба теряют жизнь"
            }
        }
        
        # Викторина для фазы дня
        self.quiz_questions = [
            {
                "question": "Сколько игроков нужно для обычной игры в Лесную Мафию?",
                "options": ["3", "4", "5", "6"],
                "correct": 2
            },
            {
                "question": "Какая команда у Волков в обычной игре?",
                "options": ["Хищники", "Травоядные", "Всеядные", "Ночные"],
                "correct": 0
            },
            {
                "question": "Что делает Лиса в обычной игре?",
                "options": ["Ворует еду", "Копает норы", "Защищает", "Голосует"],
                "correct": 0
            },
            {
                "question": "Сколько жизней у игроков в дуэли?",
                "options": ["1", "2", "3", "4"],
                "correct": 2
            },
            {
                "question": "Какое действие НЕ доступно в дуэли?",
                "options": ["Атака", "Защита", "Обман", "Лечение"],
                "correct": 3
            }
        ]

    def get_role_info(self, role: DuelRole) -> Dict[str, str]:
        """Получить информацию о роли"""
        return self.roles_info.get(role, {})

    def create_duel_invitation(self, chat_id: int, inviter_id: int, inviter_name: str) -> Dict:
        """Создать приглашение на дуэль"""
        invitation = {
            "chat_id": chat_id,
            "inviter_id": inviter_id,
            "inviter_name": inviter_name,
            "created_at": datetime.now(),
            "expires_at": datetime.now().timestamp() + 300  # 5 минут
        }
        self.duel_invitations[chat_id] = invitation
        return invitation

    def get_available_players(self, chat_id: int, exclude_user_id: int = None) -> List[Dict]:
        """Получить список доступных игроков для дуэли"""
        # Здесь должна быть логика получения активных пользователей из чата
        # Пока возвращаем заглушку
        return [
            {"user_id": 123, "username": "Player1", "display_name": "Игрок 1"},
            {"user_id": 456, "username": "Player2", "display_name": "Игрок 2"},
            {"user_id": 789, "username": "Player3", "display_name": "Игрок 3"}
        ]

    def start_duel(self, chat_id: int, player1_id: int, player1_name: str, 
                   player2_id: int, player2_name: str) -> Duel:
        """Начать дуэль между двумя игроками"""
        
        # Случайно выбираем роли
        roles = list(DuelRole)
        random.shuffle(roles)
        
        player1_role = roles[0]
        player2_role = roles[1]
        
        # Создаем игроков
        player1 = DuelPlayer(
            user_id=player1_id,
            username=player1_name,
            role=player1_role
        )
        
        player2 = DuelPlayer(
            user_id=player2_id,
            username=player2_name,
            role=player2_role
        )
        
        # Создаем дуэль
        duel_id = len(self.active_duels) + 1
        duel = Duel(
            duel_id=duel_id,
            chat_id=chat_id,
            player1=player1,
            player2=player2,
            created_at=datetime.now()
        )
        
        self.active_duels[duel_id] = duel
        
        # Удаляем приглашение
        if chat_id in self.duel_invitations:
            del self.duel_invitations[chat_id]
        
        return duel

    def get_duel(self, duel_id: int) -> Optional[Duel]:
        """Получить дуэль по ID"""
        return self.active_duels.get(duel_id)

    def get_duel_by_chat(self, chat_id: int) -> Optional[Duel]:
        """Получить активную дуэль в чате"""
        for duel in self.active_duels.values():
            if duel.chat_id == chat_id and duel.phase != DuelPhase.FINISHED:
                return duel
        return None

    def process_night_phase(self, duel: Duel, player1_action: DuelAction, 
                           player2_action: DuelAction) -> Dict[str, Any]:
        """Обработать фазу ночи"""
        result = {
            "phase": "night",
            "player1_action": player1_action.value,
            "player2_action": player2_action.value,
            "damage": {"player1": 0, "player2": 0},
            "special_effects": [],
            "round_result": ""
        }
        
        # Обновляем последние действия
        duel.player1.last_action = player1_action
        duel.player2.last_action = player2_action
        
        # Логика боя
        if player1_action == DuelAction.ATTACK and player2_action == DuelAction.DEFENSE:
            # Атака против защиты
            if duel.player1.role == DuelRole.BOAR:
                # Кабан пробивает защиту
                result["damage"]["player2"] = 1
                result["special_effects"].append("🐗 Кабан пробил защиту!")
            else:
                result["round_result"] = "🛡 Защита заблокировала атаку!"
                
        elif player1_action == DuelAction.ATTACK and player2_action == DuelAction.ATTACK:
            # Атака против атаки
            if duel.player1.role == DuelRole.HEDGEHOG or duel.player2.role == DuelRole.HEDGEHOG:
                # Ёж ранит обоих
                result["damage"]["player1"] = 1
                result["damage"]["player2"] = 1
                result["special_effects"].append("🦔 Ёж ранил обоих игроков!")
            else:
                # Обычная атака - оба получают урон
                result["damage"]["player1"] = 1
                result["damage"]["player2"] = 1
                result["round_result"] = "⚔️ Оба игрока атаковали!"
                
        elif player1_action == DuelAction.DEFENSE and player2_action == DuelAction.DEFENSE:
            result["round_result"] = "🛡 Оба игрока защищались - ничья!"
            
        elif player1_action == DuelAction.TRICK and player2_action == DuelAction.ATTACK:
            # Обман против атаки - обман выигрывает
            result["damage"]["player2"] = 1
            result["round_result"] = "🎭 Обман перехитрил атаку!"
            
        elif player1_action == DuelAction.ATTACK and player2_action == DuelAction.TRICK:
            # Атака против обмана - обман выигрывает
            result["damage"]["player1"] = 1
            result["round_result"] = "🎭 Обман перехитрил атаку!"
            
        elif player1_action == DuelAction.TRICK and player2_action == DuelAction.DEFENSE:
            # Обман против защиты - обман выигрывает
            result["damage"]["player2"] = 1
            result["round_result"] = "🎭 Обман обманул защиту!"
            
        elif player1_action == DuelAction.DEFENSE and player2_action == DuelAction.TRICK:
            # Защита против обмана - обман выигрывает
            result["damage"]["player1"] = 1
            result["round_result"] = "🎭 Обман обманул защиту!"
            
        elif player1_action == DuelAction.TRICK and player2_action == DuelAction.TRICK:
            result["round_result"] = "🎭 Оба игрока обманывали - ничья!"
        
        # Применяем урон
        duel.player1.lives -= result["damage"]["player1"]
        duel.player2.lives -= result["damage"]["player2"]
        
        # Проверяем победу
        if duel.player1.lives <= 0 and duel.player2.lives <= 0:
            duel.winner = None  # Ничья
            duel.phase = DuelPhase.FINISHED
        elif duel.player1.lives <= 0:
            duel.winner = duel.player2.user_id
            duel.phase = DuelPhase.FINISHED
        elif duel.player2.lives <= 0:
            duel.winner = duel.player1.user_id
            duel.phase = DuelPhase.FINISHED
        
        return result

    def process_day_phase(self, duel: Duel) -> Dict[str, Any]:
        """Обработать фазу дня (викторина)"""
        # Выбираем случайный вопрос
        question = random.choice(self.quiz_questions)
        
        result = {
            "phase": "day",
            "question": question["question"],
            "options": question["options"],
            "correct_answer": question["correct"],
            "damage": {"player1": 0, "player2": 0}
        }
        
        return result

    def process_casino_phase(self, duel: Duel) -> Dict[str, Any]:
        """Обработать фазу казино (бросок кубика)"""
        dice_result = random.randint(1, 6)
        
        result = {
            "phase": "casino",
            "dice_result": dice_result,
            "bonus": {"player1": 0, "player2": 0},
            "bonus_type": ""
        }
        
        if dice_result <= 3:  # Ночь
            result["bonus_type"] = "🌙 Ночь"
            # Хищники получают бонус
            if duel.player1.role in [DuelRole.WOLF, DuelRole.FOX, DuelRole.BOAR]:
                result["bonus"]["player1"] = 1
            if duel.player2.role in [DuelRole.WOLF, DuelRole.FOX, DuelRole.BOAR]:
                result["bonus"]["player2"] = 1
        else:  # День
            result["bonus_type"] = "☀️ День"
            # Мирные получают бонус
            if duel.player1.role in [DuelRole.HARE, DuelRole.BEAVER, DuelRole.OWL, DuelRole.HEDGEHOG]:
                result["bonus"]["player1"] = 1
            if duel.player2.role in [DuelRole.HARE, DuelRole.BEAVER, DuelRole.OWL, DuelRole.HEDGEHOG]:
                result["bonus"]["player2"] = 1
        
        # Применяем бонусы (восстанавливаем жизни)
        duel.player1.lives = min(3, duel.player1.lives + result["bonus"]["player1"])
        duel.player2.lives = min(3, duel.player2.lives + result["bonus"]["player2"])
        
        return result

    def process_final_phase(self, duel: Duel, player1_guess: str, player2_guess: str) -> Dict[str, Any]:
        """Обработать финальную фазу (угадайка)"""
        # Генерируем случайное число от 1 до 100
        secret_number = random.randint(1, 100)
        
        result = {
            "phase": "final",
            "secret_number": secret_number,
            "player1_guess": player1_guess,
            "player2_guess": player2_guess,
            "winner": None
        }
        
        # Проверяем угадывания
        try:
            p1_guess = int(player1_guess)
            p2_guess = int(player2_guess)
            
            p1_diff = abs(p1_guess - secret_number)
            p2_diff = abs(p2_guess - secret_number)
            
            if p1_diff < p2_diff:
                result["winner"] = duel.player1.user_id
            elif p2_diff < p1_diff:
                result["winner"] = duel.player2.user_id
            else:
                result["winner"] = None  # Ничья
                
        except ValueError:
            # Если кто-то ввел не число, он проигрывает
            result["winner"] = duel.player2.user_id if player1_guess.isdigit() else duel.player1.user_id
        
        duel.winner = result["winner"]
        duel.phase = DuelPhase.FINISHED
        
        return result

    def get_duel_status_text(self, duel: Duel) -> str:
        """Получить текст статуса дуэли"""
        if duel.phase == DuelPhase.WAITING:
            return f"⚔️ **Дуэль**\n\n🔄 Ожидание подтверждения от {duel.player2.username}..."
        
        status = f"⚔️ **Дуэль** - Раунд {duel.current_round}\n\n"
        status += f"🐺 {duel.player1.username}: {duel.player1.lives} ❤️\n"
        status += f"🐺 {duel.player2.username}: {duel.player2.lives} ❤️\n\n"
        
        if duel.phase == DuelPhase.NIGHT:
            status += "🌑 **Фаза ночи**\nВыберите действие:"
        elif duel.phase == DuelPhase.DAY:
            status += "☀️ **Фаза дня**\nОтветьте на вопрос викторины:"
        elif duel.phase == DuelPhase.CASINO:
            status += "🎰 **Фаза казино**\nБросок кубика..."
        elif duel.phase == DuelPhase.FINAL:
            status += "🔮 **Финальная фаза**\nУгадайте число от 1 до 100:"
        elif duel.phase == DuelPhase.FINISHED:
            if duel.winner:
                winner = duel.player1 if duel.winner == duel.player1.user_id else duel.player2
                status += f"🏆 **Победитель: {winner.username}**\n"
                status += f"Роль: {self.get_role_info(winner.role)['name']}"
            else:
                status += "🤝 **Ничья!**"
        
        return status

    def cleanup_duel(self, duel_id: int):
        """Очистить завершенную дуэль"""
        if duel_id in self.active_duels:
            del self.active_duels[duel_id]
