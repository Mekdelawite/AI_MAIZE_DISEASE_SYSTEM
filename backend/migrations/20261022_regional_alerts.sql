-- Persistent in-app notifications for regional broadcasts.
CREATE TABLE IF NOT EXISTS farmer_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title_en VARCHAR(200) NOT NULL,
    title_am VARCHAR(200) NOT NULL,
    message_en TEXT NOT NULL,
    message_am TEXT NOT NULL,
    region VARCHAR(100) NOT NULL,
    discussion_post_id INTEGER REFERENCES discussion_posts(id) ON DELETE SET NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_farmer_notifications_user_id ON farmer_notifications(user_id);
CREATE INDEX IF NOT EXISTS ix_farmer_notifications_region ON farmer_notifications(region);
CREATE INDEX IF NOT EXISTS ix_farmer_notifications_is_read ON farmer_notifications(is_read);
CREATE INDEX IF NOT EXISTS ix_farmer_notifications_created_at ON farmer_notifications(created_at);
