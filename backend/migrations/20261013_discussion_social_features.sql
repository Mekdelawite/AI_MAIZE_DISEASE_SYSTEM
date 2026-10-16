-- Additive migration for persistent discussion likes.
-- Existing posts and replies are preserved.

CREATE TABLE IF NOT EXISTS discussion_post_likes (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL
        REFERENCES discussion_posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL
        REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_discussion_post_like_user UNIQUE (post_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_discussion_post_likes_post_id
    ON discussion_post_likes(post_id);

CREATE INDEX IF NOT EXISTS ix_discussion_post_likes_user_id
    ON discussion_post_likes(user_id);
