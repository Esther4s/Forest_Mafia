-- =====================================================
-- Новые таблицы для расширенной функциональности
-- PostgreSQL схема
-- =====================================================

-- Включаем расширения PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- НОВЫЕ ТАБЛИЦЫ
-- =====================================================

-- 1. Таблица пользователей (id, user_id, username, balance, created_at)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    balance DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Таблица игр пользователей (id, user_id, game_type, status, created_at, updated_at)
CREATE TABLE IF NOT EXISTS user_games (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    game_type VARCHAR(50) NOT NULL DEFAULT 'forest_mafia',
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Таблица статистики (id, user_id, games_played, games_won, games_lost, last_played)
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

-- 4. Таблица магазина (id, item_name, price)
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

-- 5. Таблица покупок (id, user_id, item_id, purchased_at)
CREATE TABLE IF NOT EXISTS purchases (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES shop(id) ON DELETE CASCADE,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quantity INTEGER DEFAULT 1,
    total_price DECIMAL(10,2) NOT NULL
);

-- =====================================================
-- ИНДЕКСЫ ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ
-- =====================================================

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_user_games_user_id ON user_games(user_id);
CREATE INDEX IF NOT EXISTS idx_user_games_status ON user_games(status);
CREATE INDEX IF NOT EXISTS idx_stats_user_id ON stats(user_id);
CREATE INDEX IF NOT EXISTS idx_shop_category ON shop(category);
CREATE INDEX IF NOT EXISTS idx_shop_active ON shop(is_active);
CREATE INDEX IF NOT EXISTS idx_purchases_user_id ON purchases(user_id);
CREATE INDEX IF NOT EXISTS idx_purchases_item_id ON purchases(item_id);
CREATE INDEX IF NOT EXISTS idx_purchases_date ON purchases(purchased_at);

-- Уникальные индексы
CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_user_unique ON stats(user_id);

-- =====================================================
-- ТРИГГЕРЫ ДЛЯ АВТОМАТИЧЕСКОГО ОБНОВЛЕНИЯ TIMESTAMP
-- =====================================================

-- Функция для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для автоматического обновления updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_games_updated_at BEFORE UPDATE ON user_games
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stats_updated_at BEFORE UPDATE ON stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_shop_updated_at BEFORE UPDATE ON shop
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- НАЧАЛЬНЫЕ ДАННЫЕ ДЛЯ МАГАЗИНА
-- =====================================================

-- Вставляем базовые товары в магазин
INSERT INTO shop (item_name, price, description, category) VALUES
('🎭 Маска волка', 100.00, 'Специальная маска для роли волка', 'cosmetics'),
('🦊 Хвост лисы', 150.00, 'Пушистый хвост лисы', 'cosmetics'),
('🐰 Уши зайца', 80.00, 'Мягкие уши зайца', 'cosmetics'),
('🕳️ Лопата крота', 200.00, 'Инструмент для рытья туннелей', 'tools'),
('🦫 Бобровый хвост', 120.00, 'Плоский хвост бобра', 'cosmetics'),
('⭐ Звезда удачи', 500.00, 'Повышает шансы на получение желаемой роли', 'special'),
('🎯 Точный выстрел', 300.00, 'Гарантированное попадание в цель', 'special'),
('🛡️ Защита', 400.00, 'Защита от одного убийства', 'special')
ON CONFLICT (item_name) DO NOTHING;

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
COMMENT ON TABLE user_games IS 'Игры пользователей для расширенной статистики';
COMMENT ON TABLE stats IS 'Расширенная статистика игроков';
COMMENT ON TABLE shop IS 'Магазин товаров и предметов';
COMMENT ON TABLE purchases IS 'История покупок пользователей';

-- =====================================================
-- ЗАВЕРШЕНИЕ
-- =====================================================

-- Выводим информацию о созданных таблицах
DO $$
BEGIN
    RAISE NOTICE '✅ Новые таблицы для ForestMafia Bot созданы успешно!';
    RAISE NOTICE '📊 Создано новых таблиц: 5';
    RAISE NOTICE '🔍 Создано индексов: 10';
    RAISE NOTICE '🎯 Создано представлений: 2';
    RAISE NOTICE '⚡ Создано триггеров: 4';
    RAISE NOTICE '🛍️ Добавлено товаров в магазин: 8';
END $$;
