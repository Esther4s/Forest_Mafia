-- =====================================================
-- ИСПРАВЛЕННАЯ СХЕМА БАЗЫ ДАННЫХ ДЛЯ FORESTMAFIA BOT
-- PostgreSQL совместимая схема
-- =====================================================

-- Включаем расширения PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- ФУНКЦИЯ ДЛЯ ОБНОВЛЕНИЯ TIMESTAMP
-- =====================================================

-- Функция для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- ОСНОВНЫЕ ТАБЛИЦЫ
-- =====================================================

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    balance DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица игр
CREATE TABLE IF NOT EXISTS games (
    id VARCHAR PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    thread_id INTEGER,
    status VARCHAR DEFAULT 'waiting',
    current_phase VARCHAR,
    round_number INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    winner_team VARCHAR,
    settings JSONB DEFAULT '{}'::jsonb
);

-- Таблица игроков
CREATE TABLE IF NOT EXISTS players (
    id VARCHAR PRIMARY KEY,
    game_id VARCHAR NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    username VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    role VARCHAR,
    team VARCHAR,
    is_alive BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица событий игры
CREATE TABLE IF NOT EXISTS game_events (
    id VARCHAR PRIMARY KEY,
    game_id VARCHAR NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    event_type VARCHAR NOT NULL,
    description TEXT,
    data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица действий игроков
CREATE TABLE IF NOT EXISTS player_actions (
    id VARCHAR PRIMARY KEY,
    game_id VARCHAR NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    player_id VARCHAR NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    action_type VARCHAR NOT NULL,
    target_id VARCHAR,
    data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица голосований
CREATE TABLE IF NOT EXISTS votes (
    id VARCHAR PRIMARY KEY,
    game_id VARCHAR NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    voter_id VARCHAR NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    target_id VARCHAR REFERENCES players(id) ON DELETE CASCADE,
    vote_type VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица статистики игроков
CREATE TABLE IF NOT EXISTS player_stats (
    id VARCHAR PRIMARY KEY,
    user_id INTEGER NOT NULL,
    username VARCHAR,
    total_games INTEGER DEFAULT 0,
    games_won INTEGER DEFAULT 0,
    games_lost INTEGER DEFAULT 0,
    times_wolf INTEGER DEFAULT 0,
    times_fox INTEGER DEFAULT 0,
    times_hare INTEGER DEFAULT 0,
    times_mole INTEGER DEFAULT 0,
    times_beaver INTEGER DEFAULT 0,
    kills_made INTEGER DEFAULT 0,
    votes_received INTEGER DEFAULT 0,
    last_played TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица настроек бота
CREATE TABLE IF NOT EXISTS bot_settings (
    id VARCHAR PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    thread_id INTEGER,
    setting_key VARCHAR NOT NULL,
    setting_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица настроек чата
CREATE TABLE IF NOT EXISTS chat_settings (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL UNIQUE,
    thread_id INTEGER,
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
    loser_rewards_enabled BOOLEAN DEFAULT TRUE,
    dead_rewards_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица магазина
CREATE TABLE IF NOT EXISTS shop (
    id SERIAL PRIMARY KEY,
    item_name VARCHAR(255) NOT NULL UNIQUE,
    price DECIMAL(10,2) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица покупок
CREATE TABLE IF NOT EXISTS purchases (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES shop(id) ON DELETE CASCADE,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quantity INTEGER DEFAULT 1,
    total_price DECIMAL(10,2) NOT NULL
);

-- Таблица расширенной статистики
CREATE TABLE IF NOT EXISTS stats (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    games_played INTEGER DEFAULT 0,
    games_won INTEGER DEFAULT 0,
    games_lost INTEGER DEFAULT 0,
    last_played TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- ИНДЕКСЫ ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ
-- =====================================================

-- Индексы для основных таблиц
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_games_chat_id ON games(chat_id);
CREATE INDEX IF NOT EXISTS idx_games_status ON games(status);
CREATE INDEX IF NOT EXISTS idx_players_game_id ON players(game_id);
CREATE INDEX IF NOT EXISTS idx_players_user_id ON players(user_id);
CREATE INDEX IF NOT EXISTS idx_game_events_game_id ON game_events(game_id);
CREATE INDEX IF NOT EXISTS idx_player_actions_game_id ON player_actions(game_id);
CREATE INDEX IF NOT EXISTS idx_player_actions_player_id ON player_actions(player_id);
CREATE INDEX IF NOT EXISTS idx_votes_game_id ON votes(game_id);
CREATE INDEX IF NOT EXISTS idx_votes_voter_id ON votes(voter_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_user_id ON player_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_settings_chat_id ON bot_settings(chat_id);
CREATE INDEX IF NOT EXISTS idx_chat_settings_chat_id ON chat_settings(chat_id);
CREATE INDEX IF NOT EXISTS idx_shop_category ON shop(category);
CREATE INDEX IF NOT EXISTS idx_shop_active ON shop(is_active);
CREATE INDEX IF NOT EXISTS idx_purchases_user_id ON purchases(user_id);
CREATE INDEX IF NOT EXISTS idx_purchases_item_id ON purchases(item_id);
CREATE INDEX IF NOT EXISTS idx_purchases_date ON purchases(purchased_at);
CREATE INDEX IF NOT EXISTS idx_stats_user_id ON stats(user_id);

-- =====================================================
-- УНИКАЛЬНЫЕ ИНДЕКСЫ
-- =====================================================

CREATE UNIQUE INDEX IF NOT EXISTS idx_players_game_user ON players(game_id, user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_player_stats_user ON player_stats(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_bot_settings_chat_key ON bot_settings(chat_id, thread_id, setting_key);
CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_user_unique ON stats(user_id);

-- =====================================================
-- ТРИГГЕРЫ ДЛЯ АВТОМАТИЧЕСКОГО ОБНОВЛЕНИЯ TIMESTAMP
-- =====================================================

-- Триггеры для автоматического обновления updated_at
DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_players_updated_at ON players;
CREATE TRIGGER trigger_players_updated_at
    BEFORE UPDATE ON players
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_player_stats_updated_at ON player_stats;
CREATE TRIGGER trigger_player_stats_updated_at
    BEFORE UPDATE ON player_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_bot_settings_updated_at ON bot_settings;
CREATE TRIGGER trigger_bot_settings_updated_at
    BEFORE UPDATE ON bot_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_chat_settings_updated_at ON chat_settings;
CREATE TRIGGER trigger_chat_settings_updated_at
    BEFORE UPDATE ON chat_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_shop_updated_at ON shop;
CREATE TRIGGER trigger_shop_updated_at
    BEFORE UPDATE ON shop
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_stats_updated_at ON stats;
CREATE TRIGGER trigger_stats_updated_at
    BEFORE UPDATE ON stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- НАЧАЛЬНЫЕ ДАННЫЕ ДЛЯ МАГАЗИНА
-- =====================================================

-- Вставляем лесные товары в магазин
INSERT INTO shop (item_name, price, description, category) VALUES
('🌿 Лесная маскировка', 100.00, 'Скрывает твою роль от проверки крота один раз', 'protection'),
('🛡️ Защита бобра', 150.00, 'Один раз может спасти тебе жизнь от волков', 'protection'),
('🎭 Активная роль', 1.00, 'Даёт 99% шанс выпадения активной роли (волк, лиса, крот, бобёр)', 'special'),
('🌰 Золотой орешек', 200.00, 'Удваивает орешки за следующую игру', 'special'),
('🔍 Острый нюх', 300.00, 'Показывает роли всех игроков в следующей игре', 'special'),
('🌙 Ночное зрение', 250.00, 'Видишь действия других игроков в ночной фазе', 'special'),
('🍄 Лесной эликсир', 400.00, 'Воскрешает тебя один раз, если тебя убьют', 'special'),
('🌲 Древо жизни', 500.00, 'Даёт дополнительную жизнь на всю игру', 'special')
ON CONFLICT (item_name) DO NOTHING;

-- =====================================================
-- КОММЕНТАРИИ К КОЛОНКАМ
-- =====================================================

COMMENT ON COLUMN chat_settings.loser_rewards_enabled IS 'Начисление орешков проигравшим игрокам';
COMMENT ON COLUMN chat_settings.dead_rewards_enabled IS 'Начисление орешков умершим игрокам';

-- =====================================================
-- ПРЕДСТАВЛЕНИЯ (VIEWS) ДЛЯ УДОБСТВА
-- =====================================================

-- Представление для полной статистики пользователя
CREATE OR REPLACE VIEW user_full_stats AS
SELECT 
    u.id,
    u.user_id,
    u.username,
    u.balance,
    COALESCE(s.games_played, 0) as games_played,
    COALESCE(s.games_won, 0) as games_won,
    COALESCE(s.games_lost, 0) as games_lost,
    CASE 
        WHEN COALESCE(s.games_played, 0) > 0 
        THEN ROUND((COALESCE(s.games_won, 0)::DECIMAL / s.games_played::DECIMAL) * 100, 2)
        ELSE 0 
    END as win_rate,
    s.last_played,
    u.created_at
FROM users u
LEFT JOIN stats s ON u.user_id = s.user_id;

-- Представление для топ игроков
CREATE OR REPLACE VIEW top_players AS
SELECT 
    u.user_id,
    u.username,
    COALESCE(s.games_won, 0) as games_won,
    COALESCE(s.games_played, 0) as games_played,
    CASE 
        WHEN COALESCE(s.games_played, 0) > 0 
        THEN ROUND((COALESCE(s.games_won, 0)::DECIMAL / s.games_played::DECIMAL) * 100, 2)
        ELSE 0 
    END as win_rate
FROM users u
LEFT JOIN stats s ON u.user_id = s.user_id
WHERE COALESCE(s.games_played, 0) > 0
ORDER BY games_won DESC, win_rate DESC;

-- =====================================================
-- КОММЕНТАРИИ К ТАБЛИЦАМ
-- =====================================================

COMMENT ON TABLE users IS 'Основная таблица пользователей бота';
COMMENT ON TABLE games IS 'Активные и завершенные игры';
COMMENT ON TABLE players IS 'Игроки в конкретных играх';
COMMENT ON TABLE game_events IS 'События, происходящие в играх';
COMMENT ON TABLE player_actions IS 'Действия игроков в играх';
COMMENT ON TABLE votes IS 'Голосования в играх';
COMMENT ON TABLE player_stats IS 'Статистика игроков (legacy)';
COMMENT ON TABLE bot_settings IS 'Настройки бота для чатов';
COMMENT ON TABLE chat_settings IS 'Настройки чатов';
COMMENT ON TABLE shop IS 'Магазин товаров и предметов';
COMMENT ON TABLE purchases IS 'История покупок пользователей';
COMMENT ON TABLE stats IS 'Расширенная статистика игроков';

-- =====================================================
-- ЗАВЕРШЕНИЕ
-- =====================================================

-- Выводим информацию о созданных таблицах
DO $$
BEGIN
    RAISE NOTICE '✅ Исправленная схема базы данных ForestMafia Bot создана успешно!';
    RAISE NOTICE '📊 Создано таблиц: 12';
    RAISE NOTICE '🔍 Создано индексов: 20+';
    RAISE NOTICE '🎯 Создано представлений: 2';
    RAISE NOTICE '⚡ Создано триггеров: 7';
    RAISE NOTICE '🛍️ Добавлено товаров в магазин: 8';
    RAISE NOTICE '🔧 Все ошибки исправлены!';
END $$;
