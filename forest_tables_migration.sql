-- Миграция для добавления таблиц системы лесов
-- Создание таблиц для управления лесами и участниками

-- Таблица лесов
CREATE TABLE IF NOT EXISTS forests (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    creator_id BIGINT NOT NULL,
    description TEXT,
    privacy VARCHAR(20) DEFAULT 'public',
    max_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица участников лесов
CREATE TABLE IF NOT EXISTS forest_members (
    forest_id VARCHAR(50) REFERENCES forests(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_called TIMESTAMP,
    is_opt_in BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (forest_id, user_id)
);

-- Таблица приглашений в леса
CREATE TABLE IF NOT EXISTS forest_invites (
    id VARCHAR(50) PRIMARY KEY,
    forest_id VARCHAR(50) REFERENCES forests(id) ON DELETE CASCADE,
    from_user_id BIGINT NOT NULL,
    to_user_id BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Таблица настроек лесов
CREATE TABLE IF NOT EXISTS forest_settings (
    forest_id VARCHAR(50) REFERENCES forests(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,
    value TEXT,
    PRIMARY KEY (forest_id, key)
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_forest_members_user ON forest_members(user_id);
CREATE INDEX IF NOT EXISTS idx_forest_members_forest ON forest_members(forest_id);
CREATE INDEX IF NOT EXISTS idx_forest_invites_to_user ON forest_invites(to_user_id);
CREATE INDEX IF NOT EXISTS idx_forest_invites_from_user ON forest_invites(from_user_id);
CREATE INDEX IF NOT EXISTS idx_forest_invites_status ON forest_invites(status);
CREATE INDEX IF NOT EXISTS idx_forest_members_last_called ON forest_members(last_called);
CREATE INDEX IF NOT EXISTS idx_forests_creator ON forests(creator_id);

-- Комментарии к таблицам
COMMENT ON TABLE forests IS 'Таблица лесов - групп участников для игры';
COMMENT ON TABLE forest_members IS 'Участники лесов с настройками уведомлений';
COMMENT ON TABLE forest_invites IS 'Приглашения в леса с отслеживанием статуса';
COMMENT ON TABLE forest_settings IS 'Настройки лесов (размер батчей, cooldown и т.д.)';

-- Комментарии к полям
COMMENT ON COLUMN forests.privacy IS 'Тип приватности: public или private';
COMMENT ON COLUMN forests.max_size IS 'Максимальное количество участников (NULL = без лимита)';
COMMENT ON COLUMN forest_members.is_opt_in IS 'Согласие на упоминания в сообщениях созыва';
COMMENT ON COLUMN forest_members.last_called IS 'Время последнего созыва для cooldown';
COMMENT ON COLUMN forest_invites.status IS 'Статус приглашения: pending, accepted, declined, expired';
COMMENT ON COLUMN forest_invites.expires_at IS 'Время истечения приглашения';
