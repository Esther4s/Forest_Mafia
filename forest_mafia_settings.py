"""
Улучшенные настройки для Лесной Мафии
Включает настройки ролей, таймеров и специальных функций
"""

from typing import Dict, Any, List
from global_settings import GlobalSettings
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class ForestWolvesSettings:
    def __init__(self, global_settings: GlobalSettings):
        self.global_settings = global_settings
    
    def get_forest_wolves_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру настроек Лес и Волки"""
        keyboard = [
            [InlineKeyboardButton("🌙 Настройки ночи", callback_data="forest_night_settings")],
            [InlineKeyboardButton("🦊 Настройки лисы", callback_data="forest_fox_settings")],
            [InlineKeyboardButton("🦦 Настройки бобра", callback_data="forest_beaver_settings")],
            [InlineKeyboardButton("🦫 Настройки крота", callback_data="forest_mole_settings")],
            [InlineKeyboardButton("🏆 Настройки наград", callback_data="forest_rewards_settings")],
            [InlineKeyboardButton("💀 Настройки умерших", callback_data="forest_dead_settings")],
            [InlineKeyboardButton("⏰ Автозавершение", callback_data="forest_auto_end_settings")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="settings_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_night_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру настроек ночи"""
        current_duration = self.global_settings.get("night_duration", 60)
        keyboard = [
            [InlineKeyboardButton(f"🌙 30 секунд", callback_data=f"set_night_30")],
            [InlineKeyboardButton(f"🌙 45 секунд", callback_data=f"set_night_45")],
            [InlineKeyboardButton(f"🌙 60 секунд (текущее)", callback_data=f"set_night_60")],
            [InlineKeyboardButton(f"🌙 90 секунд", callback_data=f"set_night_90")],
            [InlineKeyboardButton(f"🌙 120 секунд", callback_data=f"set_night_120")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="forest_settings_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_fox_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру настроек лисы"""
        current_threshold = self.global_settings.get("forest_wolves_features", {}).get("fox_death_threshold", 2)
        keyboard = [
            [InlineKeyboardButton(f"🦊 1 кража = смерть", callback_data="set_fox_threshold_1")],
            [InlineKeyboardButton(f"🦊 2 кражи = смерть (текущее)", callback_data="set_fox_threshold_2")],
            [InlineKeyboardButton(f"🦊 3 кражи = смерть", callback_data="set_fox_threshold_3")],
            [InlineKeyboardButton("🦊 Отключить смерть", callback_data="set_fox_threshold_0")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="forest_settings_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_beaver_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру настроек бобра"""
        current_enabled = self.global_settings.get("forest_wolves_features", {}).get("beaver_protection_enabled", True)
        keyboard = [
            [InlineKeyboardButton("🦦 Включить защиту", callback_data="set_beaver_protection_true")],
            [InlineKeyboardButton("🦦 Отключить защиту", callback_data="set_beaver_protection_false")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="forest_settings_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_mole_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру настроек крота"""
        current_threshold = self.global_settings.get("forest_wolves_features", {}).get("mole_revelation_threshold", 0.8)
        keyboard = [
            [InlineKeyboardButton(f"🦫 60% раскрытых = победа", callback_data="set_mole_threshold_0.6")],
            [InlineKeyboardButton(f"🦫 70% раскрытых = победа", callback_data="set_mole_threshold_0.7")],
            [InlineKeyboardButton(f"🦫 80% раскрытых = победа (текущее)", callback_data="set_mole_threshold_0.8")],
            [InlineKeyboardButton(f"🦫 90% раскрытых = победа", callback_data="set_mole_threshold_0.9")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="forest_settings_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_rewards_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру настроек наград"""
        current_enabled = self.global_settings.get("forest_wolves_features", {}).get("loser_rewards_enabled", True)
        keyboard = [
            [InlineKeyboardButton("🏆 Включить награды проигравшим", callback_data="set_loser_rewards_true")],
            [InlineKeyboardButton("🏆 Отключить награды проигравшим", callback_data="set_loser_rewards_false")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="forest_settings_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_auto_end_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру настроек автозавершения"""
        auto_end = self.global_settings.get("auto_end_conditions", {})
        current_rounds = auto_end.get("max_rounds", 25)
        current_hours = auto_end.get("max_game_duration_hours", 3)
        current_min_players = auto_end.get("min_alive_players", 3)
        
        keyboard = [
            [InlineKeyboardButton(f"🎮 Макс. раундов: {current_rounds}", callback_data="forest_rounds_settings")],
            [InlineKeyboardButton(f"⏱️ Макс. время: {current_hours}ч", callback_data="forest_time_settings")],
            [InlineKeyboardButton(f"👥 Мин. игроков: {current_min_players}", callback_data="forest_players_settings")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="forest_settings_back")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_rounds_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру настроек раундов"""
        current_rounds = self.global_settings.get("auto_end_conditions", {}).get("max_rounds", 25)
        keyboard = [
            [InlineKeyboardButton("🎮 15 раундов", callback_data="set_max_rounds_15")],
            [InlineKeyboardButton("🎮 20 раундов", callback_data="set_max_rounds_20")],
            [InlineKeyboardButton(f"🎮 25 раундов (текущее)", callback_data="set_max_rounds_25")],
            [InlineKeyboardButton("🎮 30 раундов", callback_data="set_max_rounds_30")],
            [InlineKeyboardButton("🎮 40 раундов", callback_data="set_max_rounds_40")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="forest_auto_end_settings")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_time_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру настроек времени"""
        current_hours = self.global_settings.get("auto_end_conditions", {}).get("max_game_duration_hours", 3)
        keyboard = [
            [InlineKeyboardButton("⏱️ 1 час", callback_data="set_max_time_1")],
            [InlineKeyboardButton("⏱️ 2 часа", callback_data="set_max_time_2")],
            [InlineKeyboardButton(f"⏱️ 3 часа (текущее)", callback_data="set_max_time_3")],
            [InlineKeyboardButton("⏱️ 4 часа", callback_data="set_max_time_4")],
            [InlineKeyboardButton("⏱️ 6 часов", callback_data="set_max_time_6")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="forest_auto_end_settings")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_players_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру настроек минимального количества игроков"""
        current_min = self.global_settings.get("auto_end_conditions", {}).get("min_alive_players", 3)
        keyboard = [
            [InlineKeyboardButton("👥 2 игрока", callback_data="set_min_alive_2")],
            [InlineKeyboardButton(f"👥 3 игрока (текущее)", callback_data="set_min_alive_3")],
            [InlineKeyboardButton("👥 4 игрока", callback_data="set_min_alive_4")],
            [InlineKeyboardButton("👥 5 игроков", callback_data="set_min_alive_5")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="forest_auto_end_settings")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_forest_settings_back_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру возврата к настройкам лесной мафии"""
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к настройкам лесной мафии", callback_data="forest_settings")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_forest_auto_end_back_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру возврата к настройкам автозавершения"""
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к автозавершению", callback_data="forest_auto_end_settings")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_dead_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру настроек умерших игроков"""
        current_enabled = self.global_settings.get("forest_wolves_features", {}).get("dead_rewards_enabled", True)
        keyboard = [
            [InlineKeyboardButton("💀 Включить награды умершим", callback_data="set_dead_rewards_true")],
            [InlineKeyboardButton("💀 Отключить награды умершим", callback_data="set_dead_rewards_false")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="forest_settings_back")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_settings_summary(self) -> str:
        """Возвращает сводку настроек лесной мафии"""
        forest_features = self.global_settings.get("forest_wolves_features", {})
        auto_end = self.global_settings.get("auto_end_conditions", {})
        
        return (
            "🌲 *Настройки Лес и Волки* 🌲\n\n"
            f"🦊 Порог смерти лисы: {forest_features.get('fox_death_threshold', 2)} кражи\n"
            f"🦦 Защита бобра: {'ВКЛ' if forest_features.get('beaver_protection_enabled', True) else 'ВЫКЛ'}\n"
            f"🦫 Порог раскрытия крота: {int(forest_features.get('mole_revelation_threshold', 0.8) * 100)}%\n"
            f"🏆 Награды проигравшим: {'ВКЛ' if forest_features.get('loser_rewards_enabled', True) else 'ВЫКЛ'}\n"
            f"💀 Награды умершим: {'ВКЛ' if forest_features.get('dead_rewards_enabled', True) else 'ВЫКЛ'}\n"
            f"🌿 Порог выживания травоядных: {int(forest_features.get('herbivore_survival_threshold', 0.7) * 100)}%\n\n"
            f"⏰ Автозавершение:\n"
            f"🎮 Максимум раундов: {auto_end.get('max_rounds', 25)}\n"
            f"⏱️ Максимум времени: {auto_end.get('max_game_duration_hours', 3)}ч\n"
            f"👥 Минимум живых игроков: {auto_end.get('min_alive_players', 3)}"
        )
    
    def apply_setting(self, setting_type: str, value: Any) -> bool:
        """Применяет настройку и возвращает успех"""
        try:
            if setting_type == "fox_threshold":
                return self.global_settings.update_forest_feature("fox_death_threshold", value)
            elif setting_type == "beaver_protection":
                return self.global_settings.update_forest_feature("beaver_protection_enabled", value)
            elif setting_type == "mole_threshold":
                return self.global_settings.update_forest_feature("mole_revelation_threshold", value)
            elif setting_type == "loser_rewards":
                return self.global_settings.update_forest_feature("loser_rewards_enabled", value)
            elif setting_type == "dead_rewards":
                return self.global_settings.update_forest_feature("dead_rewards_enabled", value)
            elif setting_type == "max_rounds":
                return self.global_settings.update_auto_end_condition("max_rounds", value)
            elif setting_type == "max_time":
                return self.global_settings.update_auto_end_condition("max_game_duration_hours", value)
            elif setting_type == "min_alive":
                return self.global_settings.update_auto_end_condition("min_alive_players", value)
            elif setting_type == "night_duration":
                return self.global_settings.update_timer("night", value)
            else:
                return False
        except Exception:
            return False
