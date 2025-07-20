-- users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    telegram_id BIGINT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- channels
CREATE TABLE IF NOT EXISTS channels (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    title VARCHAR,
    is_private BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- posts
CREATE TABLE IF NOT EXISTS posts (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    published_at TIMESTAMPTZ NOT NULL,
    content TEXT,
    views INTEGER,
    forwards INTEGER,
    score FLOAT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(telegram_id, channel_id)
);

-- tags
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL
);

-- post_tags (many-to-many)
CREATE TABLE IF NOT EXISTS post_tags (
    post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, tag_id)
);

-- channel_tags (many-to-many)
CREATE TABLE IF NOT EXISTS channel_tags (
    channel_id BIGINT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (channel_id, tag_id)
);

-- verified_access (users allowed to see private channels)
CREATE TABLE IF NOT EXISTS verified_access (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_id BIGINT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, channel_id)
);

-- subscriptions (users subscribed to channels)
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_id BIGINT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,

    policy JSONB DEFAULT NULL,

    PRIMARY KEY (user_id, channel_id)
);