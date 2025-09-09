"""
Улучшенная логика завершения игры для Лесной Мафии
Включает специальные условия победы и детальные сообщения о результатах
"""

from typing import Optional, Dict, List
from datetime import datetime
from game_logic import Game, Team, Role, Player

class GameEndLogic:
    def __init__(self, game: Game):
        self.game = game
    
    def check_all_win_conditions(self) -> Optional[Dict]:
        """
        Проверяет все возможные условия победы
        Возвращает словарь с результатом или None
        """
        # Стандартные условия победы
        standard_result = self._check_standard_win_conditions()
        if standard_result:
            return standard_result
        
        # Специальные условия победы для лесной мафии
        special_result = self._check_special_win_conditions()
        if special_result:
            return special_result
        
        # Автоматическое завершение
        auto_result = self._check_auto_game_end()
        if auto_result:
            return auto_result
        
        return None
    
    def _check_standard_win_conditions(self) -> Optional[Dict]:
        """Проверяет стандартные условия победы"""
        alive = self.game.get_alive_players()
        total_alive = len(alive)
        wolves = [p for p in alive if p.role == Role.WOLF]
        wolves_count = len(wolves)

        if total_alive == 0:
            return {
                "winner": Team.HERBIVORES, 
                "reason": "Нет выживших — по умолчанию травоядные.",
                "type": "standard"
            }

        if wolves_count > 0 and wolves_count >= (total_alive - wolves_count):
            return {
                "winner": Team.PREDATORS,
                "reason": "🐺 Победа хищников: волки сравнялись или превысили остальных.",
                "type": "standard"
            }

        if wolves_count == 0:
            return {
                "winner": Team.HERBIVORES,
                "reason": "🌿 Победа травоядных: волков нет.",
                "type": "standard"
            }

        return None
    
    def _check_special_win_conditions(self) -> Optional[Dict]:
        """Проверяет специальные условия победы для лесной мафии"""
        # Специальные условия победы удалены согласно правилам Лесной Возни
        # Теперь используются только стандартные условия победы
        return None
    
    def _check_auto_game_end(self) -> Optional[Dict]:
        """Проверяет условия автоматического завершения игры"""
        alive_players = self.game.get_alive_players()
        
        # 1. Слишком мало игроков осталось
        if len(alive_players) < 3:
            predators = self.game.get_players_by_team(Team.PREDATORS)
            herbivores = self.game.get_players_by_team(Team.HERBIVORES)
            
            if len(predators) > len(herbivores):
                winner = Team.PREDATORS
                reason = f"🌲 Автоматическое завершение: осталось слишком мало игроков ({len(alive_players)})"
            elif len(herbivores) > len(predators):
                winner = Team.HERBIVORES
                reason = f"🌲 Автоматическое завершение: осталось слишком мало игроков ({len(alive_players)})"
            else:
                winner = Team.HERBIVORES
                reason = f"🌲 Автоматическое завершение: ничья при малом количестве игроков ({len(alive_players)})"
            
            return {
                "winner": winner,
                "reason": reason,
                "type": "auto",
                "details": f"Осталось игроков: {len(alive_players)}"
            }
        
        # 2. Игра длится слишком долго
        if self.game.game_start_time:
            from datetime import datetime
            game_duration = datetime.now() - self.game.game_start_time
            if game_duration.total_seconds() > 10800:  # 3 часа
                hours = int(game_duration.total_seconds() // 3600)
                minutes = int((game_duration.total_seconds() % 3600) // 60)
                
                # Определяем победителя по статистике
                if self.game.game_stats.predator_kills > self.game.game_stats.herbivore_survivals:
                    winner = Team.PREDATORS
                    reason = f"🌲 Автоматическое завершение: игра длится слишком долго ({hours}ч {minutes}м)"
                else:
                    winner = Team.HERBIVORES
                    reason = f"🌲 Автоматическое завершение: игра длится слишком долго ({hours}ч {minutes}м)"
                
                return {
                    "winner": winner,
                    "reason": reason,
                    "type": "auto",
                    "details": f"Время игры: {hours}ч {minutes}м"
                }
        
        # 3. Слишком много раундов
        if self.game.current_round > 25:
            if self.game.game_stats.predator_kills > self.game.game_stats.herbivore_survivals:
                winner = Team.PREDATORS
            else:
                winner = Team.HERBIVORES
            
            return {
                "winner": winner,
                "reason": f"🌲 Автоматическое завершение: превышен лимит раундов ({self.game.current_round})",
                "type": "auto",
                "details": f"Максимальный раунд: {self.game.current_round}"
            }
        
        # 4. Ничья при финальном противостоянии
        predators = self.game.get_players_by_team(Team.PREDATORS)
        herbivores = self.game.get_players_by_team(Team.HERBIVORES)
        
        if len(alive_players) == 2 and len(predators) == len(herbivores):
            return {
                "winner": Team.HERBIVORES,
                "reason": "🌲 Автоматическое завершение: ничья при финальном противостоянии (1 vs 1)",
                "type": "auto",
                "details": "Финальное противостояние 1 на 1"
            }
        
        return None
    
    def get_detailed_game_summary(self) -> Dict:
        """Возвращает детальную сводку игры"""
        alive_players = self.game.get_alive_players()
        predators = self.game.get_players_by_team(Team.PREDATORS)
        herbivores = self.game.get_players_by_team(Team.HERBIVORES)
        
        # Статистика по ролям
        role_stats = {}
        for role in Role:
            # Получаем русское название роли
            from role_translator import get_role_name_russian
            role_name = get_role_name_russian(role)
            role_stats[role_name] = len([p for p in alive_players if p.role == role])
        
        # Статистика выживания
        survival_stats = {
            "longest_survivor": 0,
            "average_survival": 0
        }
        
        if alive_players:
            survival_nights = [p.consecutive_nights_survived for p in alive_players]
            survival_stats["longest_survivor"] = max(survival_nights)
            survival_stats["average_survival"] = sum(survival_nights) / len(survival_nights)
        
        return {
            "current_round": self.game.current_round,
            "alive_players": len(alive_players),
            "predators": len(predators),
            "herbivores": len(herbivores),
            "role_distribution": role_stats,
            "predator_kills": self.game.game_stats.predator_kills,
            "herbivore_survivals": self.game.game_stats.herbivore_survivals,
            "fox_thefts": self.game.game_stats.fox_thefts,
            "beaver_protections": self.game.game_stats.beaver_protections,
            "survival_stats": survival_stats,
            "game_duration": (datetime.now() - self.game.game_start_time).total_seconds() if self.game.game_start_time else 0
        }
    
    def get_winner_celebration_message(self, result: Dict) -> str:
        """Формирует праздничное сообщение о победе"""
        winner = result["winner"]
        reason = result["reason"]
        details = result.get("details", "")
        win_type = result.get("type", "unknown")
        
        if winner == Team.PREDATORS:
            emoji = "🐺"
            team_name = "ХИЩНИКИ"
            victory_msg = "Лес теперь принадлежит хищникам! 🦁"
        else:
            emoji = "🌿"
            team_name = "ТРАВОЯДНЫЕ"
            victory_msg = "Лес спасен от хищников! 🦌"
        
        message = f"""
🎉 {emoji} ПОБЕДА {team_name}! {emoji}

{reason}

{details}

{victory_msg}

🏆 Игра завершена!
📊 Тип победы: {win_type}
🎮 Раунд: {self.game.current_round}
        """.strip()
        
        return message
    
    def get_game_over_message(self, result: Dict, nuts_info: str = "") -> str:
        """Формирует сообщение об окончании игры"""
        winner = result["winner"]
        reason = result["reason"]
        details = result.get("details", "")
        
        # Получаем детальную статистику
        stats = self.get_detailed_game_summary()
        final_summary = self.game.get_final_game_summary()
        
        if winner == Team.PREDATORS:
            emoji = "🐺"
            team_name = "ХИЩНИКИ"
        else:
            emoji = "🌿"
            team_name = "ТРАВОЯДНЫЕ"
        
        # Формируем список всех участников с ролями
        players_list = ""
        for player in final_summary["all_players"]:
            status = "🟢" if player.is_alive else "🔴"
            role_emoji = self._get_role_emoji(player.role)
            team_emoji = "🐺" if player.team == Team.PREDATORS else "🌿"
            role_name = self._get_role_name_ru(player.role)
            players_list += f"{status} {role_emoji} {player.username} ({role_name}) {team_emoji}\n"
        
        # Формируем статистику по ролям
        role_stats = ""
        for role_name, players in final_summary["role_distribution"].items():
            if players:
                role_emoji = self._get_role_emoji(players[0].role)
                role_name_ru = self._get_role_name_ru(players[0].role)
                alive_count = len([p for p in players if p.is_alive])
                total_count = len(players)
                role_stats += f"{role_emoji} {role_name_ru}: {alive_count}/{total_count}\n"
        
        if winner == Team.PREDATORS:
            victory_message = "**На Лес опустилась тьма… Хищники похитили всех зверей и победили.**"
        else:
            victory_message = "**Лесные жители ликуют! Наконец-то им удалось изгнать всех хищников из их уютного Леса! Победа!**"
        
        message = f"""
🌲 *ИГРА ЗАВЕРШЕНА!* 🌲

{emoji} *Победители: {team_name}* {emoji}

{victory_message}

📝 *Причина:* {reason}

📊 *Статистика игры:*
🎮 Раундов сыграно: {stats['current_round']}
👥 Игроков осталось: {stats['alive_players']}
🐺 Хищников: {stats['predators']}
🌿 Травоядных: {stats['herbivores']}
💀 Убийств хищников: {stats['predator_kills']}
🦊 Краж лисы: {stats['fox_thefts']}
🦦 Защит бобра: {stats['beaver_protections']}

🎭 *Распределение ролей:*
{role_stats}
👥 *Все участники:*
{players_list}
{details}

{nuts_info}

---
🎮 *Хотите сыграть ещё?*
Используйте команду `/join` чтобы присоединиться к новой игре!
        """.strip()
        
        return message
    
    def _get_role_emoji(self, role: Role) -> str:
        """Возвращает эмодзи для роли"""
        role_emojis = {
            Role.WOLF: "🐺",
            Role.FOX: "🦊",
            Role.HARE: "🐰",
            Role.MOLE: "🦫",
            Role.BEAVER: "🦦"
        }
        return role_emojis.get(role, "❓")
    
    def _get_role_name_ru(self, role: Role) -> str:
        """Возвращает русское название роли"""
        role_names = {
            Role.WOLF: "Волк",
            Role.FOX: "Лиса",
            Role.HARE: "Заяц",
            Role.MOLE: "Крот",
            Role.BEAVER: "Бобер"
        }
        return role_names.get(role, "Неизвестно")
