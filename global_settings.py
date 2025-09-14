
import json
import os
from typing import Dict, Any

class GlobalSettings:
    def __init__(self, settings_file: str = "bot_settings.json"):
        self.settings_file = settings_file
        self.default_settings = {
            "test_mode": False,
            "min_players_normal": 3,  # Изменено с 6 на 3
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
            },
            "auto_end_conditions": {
                "max_rounds": 25,
                "max_game_duration_hours": 3,
                "min_alive_players": 3
            },
            "forest_wolves_features": {
                "fox_death_threshold": 2,
                "beaver_protection_enabled": True,
                "mole_revelation_threshold": 0.8,
                "herbivore_survival_threshold": 0.7
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
        # Принудительно устанавливаем 3 игрока для всех режимов
        return 3
    
    def update_role_distribution(self, role: str, percentage: float) -> bool:
        """Обновляет распределение ролей"""
        role_dist = self.get("role_distribution", {})
        role_dist[role] = percentage
        return self.set("role_distribution", role_dist)
    
    def update_timer(self, timer_type: str, duration: int) -> bool:
        """Обновляет длительность таймера"""
        timer_key = f"{timer_type}_duration"
        return self.set(timer_key, duration)
    
    def update_auto_end_condition(self, condition: str, value: Any) -> bool:
        """Обновляет условие автоматического завершения"""
        auto_end = self.get("auto_end_conditions", {})
        auto_end[condition] = value
        return self.set("auto_end_conditions", auto_end)
    
    def update_forest_feature(self, feature: str, value: Any) -> bool:
        """Обновляет настройку лесной мафии"""
        features = self.get("forest_wolves_features", {})
        features[feature] = value
        return self.set("forest_wolves_features", features)
    
    def get_settings_summary(self) -> str:
        """Возвращает краткую информацию о текущих настройках"""
        test_mode = "ВКЛ" if self.is_test_mode() else "ВЫКЛ"
        min_players = self.get_min_players()
        max_players = self.get("max_players", 12)
        
        auto_end = self.get("auto_end_conditions", {})
        forest_features = self.get("forest_wolves_features", {})
        
        return (
            f"⚙️ Глобальные настройки бота:\n\n"
            f"🧪 Тестовый режим: {test_mode}\n"
            f"👥 Минимум игроков: {min_players}\n"
            f"👥 Максимум игроков: {max_players}\n"
            f"🌙 Длительность ночи: {self.get('night_duration', 60)}с\n"
            f"☀️ Длительность дня: {self.get('day_duration', 300)}с\n"
            f"🗳️ Длительность голосования: {self.get('voting_duration', 120)}с\n\n"
            f"🌲 Лес и Волки:\n"
            f"🦊 Порог смерти лисы: {forest_features.get('fox_death_threshold', 2)}\n"
            f"🦦 Защита бобра: {'ВКЛ' if forest_features.get('beaver_protection_enabled', True) else 'ВЫКЛ'}\n"
            f"🦫 Порог раскрытия крота: {int(forest_features.get('mole_revelation_threshold', 0.8) * 100)}%\n"
            f"🌿 Порог выживания травоядных: {int(forest_features.get('herbivore_survival_threshold', 0.7) * 100)}%\n\n"
            f"⏰ Автозавершение:\n"
            f"🎮 Максимум раундов: {auto_end.get('max_rounds', 25)}\n"
            f"⏱️ Максимум времени: {auto_end.get('max_game_duration_hours', 3)}ч\n"
            f"👥 Минимум живых: {auto_end.get('min_alive_players', 3)}"
        )
    
    def reset_to_defaults(self) -> bool:
        """Сбрасывает настройки к значениям по умолчанию"""
        self.settings = self.default_settings.copy()
        return self.save_settings()
    
    def export_settings(self) -> str:
        """Экспортирует настройки в JSON строку"""
        return json.dumps(self.settings, ensure_ascii=False, indent=2)
    
    def import_settings(self, settings_json: str) -> bool:
        """Импортирует настройки из JSON строки"""
        try:
            imported_settings = json.loads(settings_json)
            # Проверяем, что все ключи корректны
            for key in imported_settings:
                if key in self.default_settings:
                    self.settings[key] = imported_settings[key]
            return self.save_settings()
        except (json.JSONDecodeError, KeyError):
            return False
