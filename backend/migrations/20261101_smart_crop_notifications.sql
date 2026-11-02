-- Idempotency protection for automatic crop activity and advisory reminders.
-- Nullable keys preserve existing regional/manual notification behavior.
ALTER TABLE farmer_notifications
    ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(180);

CREATE UNIQUE INDEX IF NOT EXISTS uq_farmer_notification_user_dedupe_key
    ON farmer_notifications (user_id, dedupe_key)
    WHERE dedupe_key IS NOT NULL;
