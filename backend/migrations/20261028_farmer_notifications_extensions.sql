-- Extend farmer_notifications with app alert metadata and read tracking.
-- Existing records are preserved; default values keep old notifications usable.

ALTER TABLE farmer_notifications
    ADD COLUMN IF NOT EXISTS notification_type VARCHAR(50) NOT NULL DEFAULT 'general',
    ADD COLUMN IF NOT EXISTS outbreak_alert_id INTEGER NULL,
    ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_farmer_notifications_outbreak_alert'
          AND conrelid = 'farmer_notifications'::regclass
    ) THEN
        ALTER TABLE farmer_notifications
            ADD CONSTRAINT fk_farmer_notifications_outbreak_alert
            FOREIGN KEY (outbreak_alert_id)
            REFERENCES outbreak_alerts(id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_farmer_notification_user_alert_type'
          AND conrelid = 'farmer_notifications'::regclass
    ) THEN
        ALTER TABLE farmer_notifications
            ADD CONSTRAINT uq_farmer_notification_user_alert_type
            UNIQUE (user_id, notification_type, outbreak_alert_id);
    END IF;
END $$;

UPDATE farmer_notifications
SET notification_type = 'regional_alert'
WHERE notification_type IS NULL OR notification_type = '';

CREATE INDEX IF NOT EXISTS ix_farmer_notifications_notification_type
    ON farmer_notifications(notification_type);

CREATE INDEX IF NOT EXISTS ix_farmer_notifications_outbreak_alert_id
    ON farmer_notifications(outbreak_alert_id);

CREATE INDEX IF NOT EXISTS ix_farmer_notifications_read_at
    ON farmer_notifications(read_at);
