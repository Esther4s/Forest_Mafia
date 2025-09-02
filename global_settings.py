
import json
import os
from typing import Dict, Any

class GlobalSettings:
    def __init__(self, settings_file: str = "bot_settings.json"):
        self.settings_file = settings_file
        self.default_settings = {
            "test_mode": True,
            "min_players_normal": 6,
            "min_players_test": 3,
            "max_players": 12,
            "night_duration": 60,
            "day_duration": 300,
            "voting_duration": 120,
            "role_distribution": {
                "wolves": 0.25,
                "fox": 0.15,
                "hares": 0.35,
                "mole": 0.15,
                "beaver": 0.10
            }
        }
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Загружает настройки из файла или создает файл с настройками по умолчанию"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                # Обновляем настройки по умолчанию загруженными значениями
                settings = self.default_settings.copy()
                settings.update(loaded_settings)
                return settings
            except (json.JSONDecodeError, IOError):
                return self.default_settings.copy()
        else:
            # Создаем файл с настройками по умолчанию
            self.save_settings(self.default_settings)
            return self.default_settings.copy()
    
    def save_settings(self, settings: Dict[str, Any] = None) -> bool:
        """Сохраняет настройки в файл"""
        try:
            settings_to_save = settings or self.settings
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_to_save, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False
    
    def get(self, key: str, default=None):
        """Получает значение настройки"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """Устанавливает значение настройки и сохраняет в файл"""
        self.settings[key] = value
        return self.save_settings()
    
    def toggle_test_mode(self) -> bool:
        """Переключает тестовый режим"""
        current = self.get("test_mode", True)
        return self.set("test_mode", not current)
    
    def is_test_mode(self) -> bool:
        """Проверяет, включен ли тестовый режим"""
        return self.get("test_mode", True)
    
    def get_min_players(self) -> int:
        """Возвращает минимальное количество игроков в зависимости от режима"""
        if self.is_test_mode():
            return self.get("min_players_test", 3)
        else:
            return self.get("min_players_normal", 6)
    
    def update_role_distribution(self, role: str, percentage: float) -> bool:
        """Обновляет распределение ролей"""
        role_dist = self.get("role_distribution", {})
        role_dist[role] = percentage
        return self.set("role_distribution", role_dist)
    
    def update_timer(self, timer_type: str, duration: int) -> bool:
        """Обновляет длительность таймера"""
        timer_key = f"{timer_type}_duration"
        return self.set(timer_key, duration)
    
    def get_settings_summary(self) -> str:
        """Возвращает краткую информацию о текущих настройках"""
        test_mode = "ВКЛ" if self.is_test_mode() else "ВЫКЛ"
        min_players = self.get_min_players()
        max_players = self.get("max_players", 12)
        
        return (
            f"⚙️ Глобальные настройки бота:\n\n"
            f"🧪 Тестовый режим: {test_mode}\n"
            f"👥 Минимум игроков: {min_players}\n"
            f"👥 Максимум игроков: {max_players}\n"
            f"🌙 Длительность ночи: {self.get('night_duration', 60)}с\n"
            f"☀️ Длительность дня: {self.get('day_duration', 300)}с\n"
            f"🗳️ Длительность голосования: {self.get('voting_duration', 120)}с"
        )
class GlobalSettings:
    def __init__(self):
        self._test_mode = True
        self._min_players_normal = 6
        self._min_players_test = 3
        self._night_duration = 60
        self._day_duration = 300
        self._voting_duration = 120
        
    def is_test_mode(self):
        return self._test_mode
    
    def toggle_test_mode(self):
        self._test_mode = not self._test_mode
        return self._test_mode
    
    def get_min_players(self):
        return self._min_players_test if self._test_mode else self._min_players_normal
    
    def get_settings_summary(self):
        mode_text = "🧪 Тестовый режим" if self._test_mode else "🎮 Обычный режим"
        return (
            f"📊 Текущие настройки:\n\n"
            f"🎯 Режим: {mode_text}\n"
            f"👥 Минимум игроков: {self.get_min_players()}\n"
            f"🌙 Ночь: {self._night_duration} сек\n"
            f"☀️ День: {self._day_duration // 60} мин\n"
            f"🗳️ Голосование: {self._voting_duration // 60} мин"
        )
