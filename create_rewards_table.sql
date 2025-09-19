-- Создание таблицы наград пользователей
CREATE TABLE IF NOT EXISTS user_rewards (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    reward_type VARCHAR(50) NOT NULL,
    reason VARCHAR(100) NOT NULL,
    amount INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_user_rewards_user_id ON user_rewards(user_id);
CREATE INDEX IF NOT EXISTS idx_user_rewards_reward_type ON user_rewards(reward_type);
CREATE INDEX IF NOT EXISTS idx_user_rewards_reason ON user_rewards(reason);
CREATE INDEX IF NOT EXISTS idx_user_rewards_created_at ON user_rewards(created_at);

-- Создание триггера для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_rewards_updated_at 
    BEFORE UPDATE ON user_rewards 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Добавление комментариев к таблице и колонкам
COMMENT ON TABLE user_rewards IS 'Таблица наград пользователей';
COMMENT ON COLUMN user_rewards.user_id IS 'ID пользователя Telegram';
COMMENT ON COLUMN user_rewards.reward_type IS 'Тип награды (game_win, role_specific, achievement, etc.)';
COMMENT ON COLUMN user_rewards.reason IS 'Причина награды (predator_win, successful_kill, etc.)';
COMMENT ON COLUMN user_rewards.amount IS 'Количество орешков';
COMMENT ON COLUMN user_rewards.description IS 'Описание награды';
COMMENT ON COLUMN user_rewards.metadata IS 'Дополнительные данные в формате JSON';
COMMENT ON COLUMN user_rewards.created_at IS 'Дата и время создания награды';
COMMENT ON COLUMN user_rewards.updated_at IS 'Дата и время последнего обновления';
