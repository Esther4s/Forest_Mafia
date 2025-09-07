-- Инициализация базы данных ForestMafia
-- Этот файл выполняется при первом запуске PostgreSQL контейнера

-- Создаем расширения если нужно
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- База данных уже создана через переменную окружения POSTGRES_DB
-- Таблицы будут созданы автоматически через SQLAlchemy

-- Можно добавить индексы для оптимизации
-- CREATE INDEX IF NOT EXISTS idx_games_chat_id ON games(chat_id);
-- CREATE INDEX IF NOT EXISTS idx_players_user_id ON players(user_id);
-- CREATE INDEX IF NOT EXISTS idx_players_game_id ON players(game_id);
-- CREATE INDEX IF NOT EXISTS idx_game_events_game_id ON game_events(game_id);
-- CREATE INDEX IF NOT EXISTS idx_player_actions_game_id ON player_actions(game_id);
-- CREATE INDEX IF NOT EXISTS idx_votes_game_id ON votes(game_id);
-- CREATE INDEX IF NOT EXISTS idx_player_stats_user_id ON player_stats(user_id);
