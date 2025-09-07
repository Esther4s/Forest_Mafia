
-- Схема базы данных для ForestMafia Bot на Railway
-- PostgreSQL совместимая схема

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

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_games_chat_id ON games(chat_id);
CREATE INDEX IF NOT EXISTS idx_players_game_id ON players(game_id);
CREATE INDEX IF NOT EXISTS idx_players_user_id ON players(user_id);
CREATE INDEX IF NOT EXISTS idx_game_events_game_id ON game_events(game_id);
CREATE INDEX IF NOT EXISTS idx_player_actions_game_id ON player_actions(game_id);
CREATE INDEX IF NOT EXISTS idx_votes_game_id ON votes(game_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_user_id ON player_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_settings_chat_id ON bot_settings(chat_id);

-- Уникальные индексы
CREATE UNIQUE INDEX IF NOT EXISTS idx_players_game_user ON players(game_id, user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_player_stats_user ON player_stats(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_bot_settings_chat_key ON bot_settings(chat_id, thread_id, setting_key);
