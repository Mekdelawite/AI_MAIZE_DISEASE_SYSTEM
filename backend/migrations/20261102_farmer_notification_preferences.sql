-- Persist farmer notification delivery and timing preferences on the existing profile.
-- Existing rows remain NULL and use API/scheduler defaults that preserve prior behavior.
ALTER TABLE farmer_profiles
    ADD COLUMN IF NOT EXISTS notification_preferences JSONB;

-- SMS idempotency also works when farmers disable in-app delivery.
ALTER TABLE sms_records
    ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(180);

CREATE UNIQUE INDEX IF NOT EXISTS uq_sms_user_dedupe_key
    ON sms_records (user_id, dedupe_key)
    WHERE dedupe_key IS NOT NULL;
