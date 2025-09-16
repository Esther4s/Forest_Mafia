-- Схема базы данных для режима "Дуэль 1v1"

-- Таблица для хранения дуэлей
CREATE TABLE IF NOT EXISTS duels (
    duel_id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    player1_id BIGINT NOT NULL,
    player2_id BIGINT NOT NULL,
    player1_role VARCHAR(20) NOT NULL,
    player2_role VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'waiting', -- waiting, active, finished, cancelled
    winner_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    rounds_count INTEGER DEFAULT 0
);

-- Таблица для хранения раундов дуэли
CREATE TABLE IF NOT EXISTS duel_rounds (
    round_id SERIAL PRIMARY KEY,
    duel_id INTEGER REFERENCES duels(duel_id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    phase VARCHAR(20) NOT NULL, -- night, day, casino, final
    player1_action VARCHAR(20), -- attack, defense, trick
    player2_action VARCHAR(20),
    player1_lives INTEGER DEFAULT 3,
    player2_lives INTEGER DEFAULT 3,
    round_result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для статистики дуэлей игроков
CREATE TABLE IF NOT EXISTS duel_stats (
    user_id BIGINT PRIMARY KEY,
    total_duels INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    favorite_role VARCHAR(20),
    longest_win_streak INTEGER DEFAULT 0,
    current_win_streak INTEGER DEFAULT 0,
    total_coins_earned INTEGER DEFAULT 0,
    last_duel_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_duels_chat_id ON duels(chat_id);
CREATE INDEX IF NOT EXISTS idx_duels_players ON duels(player1_id, player2_id);
CREATE INDEX IF NOT EXISTS idx_duels_status ON duels(status);
CREATE INDEX IF NOT EXISTS idx_duel_rounds_duel_id ON duel_rounds(duel_id);
CREATE INDEX IF NOT EXISTS idx_duel_stats_user_id ON duel_stats(user_id);
