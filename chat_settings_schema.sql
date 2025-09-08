-- Таблица настроек чата для игры "Лес и Волки"
CREATE TABLE IF NOT EXISTS chat_settings (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL UNIQUE,
    test_mode BOOLEAN DEFAULT FALSE,
    min_players INTEGER DEFAULT 4,
    max_players INTEGER DEFAULT 12,
    night_duration INTEGER DEFAULT 60,
    day_duration INTEGER DEFAULT 300,
    vote_duration INTEGER DEFAULT 120,
    fox_death_threshold INTEGER DEFAULT 2,
    beaver_protection BOOLEAN DEFAULT TRUE,
    mole_reveal_threshold INTEGER DEFAULT 3,
    herbivore_survival_threshold INTEGER DEFAULT 1,
    max_rounds INTEGER DEFAULT 20,
    max_time INTEGER DEFAULT 3600,
    min_alive INTEGER DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индекс для быстрого поиска по chat_id
CREATE INDEX IF NOT EXISTS idx_chat_settings_chat_id ON chat_settings(chat_id);

-- Триггер для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_chat_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_chat_settings_updated_at
    BEFORE UPDATE ON chat_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_settings_updated_at();

-- Комментарии к полям
COMMENT ON TABLE chat_settings IS 'Настройки игры для каждого чата';
COMMENT ON COLUMN chat_settings.chat_id IS 'ID чата в Telegram';
COMMENT ON COLUMN chat_settings.test_mode IS 'Тестовый режим (все роли видны)';
COMMENT ON COLUMN chat_settings.min_players IS 'Минимальное количество игроков';
COMMENT ON COLUMN chat_settings.max_players IS 'Максимальное количество игроков';
COMMENT ON COLUMN chat_settings.night_duration IS 'Длительность ночи в секундах';
COMMENT ON COLUMN chat_settings.day_duration IS 'Длительность дня в секундах';
COMMENT ON COLUMN chat_settings.vote_duration IS 'Длительность голосования в секундах';
COMMENT ON COLUMN chat_settings.fox_death_threshold IS 'Порог смерти лисы (количество ночей)';
COMMENT ON COLUMN chat_settings.beaver_protection IS 'Защита бобра (не может быть съеден в первую ночь)';
COMMENT ON COLUMN chat_settings.mole_reveal_threshold IS 'Порог раскрытия крота (количество ночей)';
COMMENT ON COLUMN chat_settings.herbivore_survival_threshold IS 'Порог выживания травоядных (количество игроков)';
COMMENT ON COLUMN chat_settings.max_rounds IS 'Максимальное количество раундов';
COMMENT ON COLUMN chat_settings.max_time IS 'Максимальное время игры в секундах';
COMMENT ON COLUMN chat_settings.min_alive IS 'Минимальное количество живых игроков для продолжения игры';
