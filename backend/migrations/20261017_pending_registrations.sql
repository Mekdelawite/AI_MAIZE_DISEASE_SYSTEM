-- Additive migration for phone-verified farmer registration.
-- Creates only the pending-registration table and its unique phone index.
-- The model declares no schema, so PostgreSQL resolves this table through
-- the connection's search_path (normally public). IF NOT EXISTS does not
-- validate or repair a table that already exists with a different definition.

CREATE TABLE IF NOT EXISTS pending_registrations (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL,
    otp_hash VARCHAR(64),
    otp_expires_at TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    last_sent_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    registration_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_pending_registrations_phone_number
    ON pending_registrations(phone_number);
