-- Web Push subscriptions belong to an authenticated farmer. Delivery rows are
-- receipts for existing farmer_notifications, not a second notification feed.
CREATE TABLE IF NOT EXISTS farmer_push_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL UNIQUE,
    p256dh VARCHAR(200) NOT NULL,
    auth VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_farmer_push_subscriptions_user_id
    ON farmer_push_subscriptions (user_id);

CREATE TABLE IF NOT EXISTS farmer_push_deliveries (
    id SERIAL PRIMARY KEY,
    notification_id INTEGER NOT NULL REFERENCES farmer_notifications(id) ON DELETE CASCADE,
    subscription_id INTEGER NOT NULL REFERENCES farmer_push_subscriptions(id) ON DELETE CASCADE,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    last_error VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_farmer_push_delivery_notification_subscription
        UNIQUE (notification_id, subscription_id)
);

CREATE INDEX IF NOT EXISTS ix_farmer_push_delivery_due
    ON farmer_push_deliveries (status, next_attempt_at);
