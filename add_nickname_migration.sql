-- =====================================================
-- МИГРАЦИЯ: Добавление поля nickname в таблицу users
-- =====================================================

-- Добавляем поле nickname в таблицу users
ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname VARCHAR(50);

-- Создаем индекс для быстрого поиска по никнейму
CREATE INDEX IF NOT EXISTS idx_users_nickname ON users(nickname);

-- Добавляем комментарий к полю
COMMENT ON COLUMN users.nickname IS 'Пользовательский никнейм для отображения в игре';
