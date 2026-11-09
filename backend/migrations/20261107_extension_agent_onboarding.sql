-- Add local Ethiopian administrative divisions and admin-provisioned
-- extension-agent onboarding. Run the geography importer after this migration.

CREATE TABLE IF NOT EXISTS geography_regions (
    id VARCHAR(32) PRIMARY KEY,
    name_en VARCHAR(120) NOT NULL UNIQUE,
    name_local VARCHAR(120)
);

CREATE TABLE IF NOT EXISTS geography_zones (
    id VARCHAR(32) PRIMARY KEY,
    region_id VARCHAR(32) NOT NULL REFERENCES geography_regions(id) ON DELETE RESTRICT,
    name_en VARCHAR(120) NOT NULL,
    name_local VARCHAR(120),
    CONSTRAINT uq_geography_zone_region_name UNIQUE (region_id, name_en),
    CONSTRAINT uq_geography_zone_id_region UNIQUE (id, region_id)
);

CREATE INDEX IF NOT EXISTS ix_geography_zones_region_id
    ON geography_zones(region_id);

CREATE TABLE IF NOT EXISTS geography_woredas (
    id VARCHAR(32) PRIMARY KEY,
    zone_id VARCHAR(32) NOT NULL REFERENCES geography_zones(id) ON DELETE RESTRICT,
    name_en VARCHAR(120) NOT NULL,
    name_local VARCHAR(120),
    CONSTRAINT uq_geography_woreda_zone_name UNIQUE (zone_id, name_en),
    CONSTRAINT uq_geography_woreda_id_zone UNIQUE (id, zone_id)
);

CREATE INDEX IF NOT EXISTS ix_geography_woredas_zone_id
    ON geography_woredas(zone_id);

ALTER TABLE extension_agents
    ADD COLUMN zone VARCHAR(100),
    ADD COLUMN region_id VARCHAR(32),
    ADD COLUMN zone_id VARCHAR(32),
    ADD COLUMN woreda_id VARCHAR(32),
    ADD COLUMN email VARCHAR(254),
    ADD COLUMN employee_id VARCHAR(80),
    ADD COLUMN organization VARCHAR(150),
    ADD COLUMN professional_info_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN professional_info_verified_by_id INTEGER,
    ADD COLUMN professional_info_verified_at TIMESTAMPTZ,
    ADD COLUMN account_status VARCHAR(30) NOT NULL DEFAULT 'active';

ALTER TABLE extension_agents
    ADD CONSTRAINT fk_extension_agent_region
        FOREIGN KEY (region_id) REFERENCES geography_regions(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_extension_agent_zone
        FOREIGN KEY (zone_id) REFERENCES geography_zones(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_extension_agent_woreda
        FOREIGN KEY (woreda_id) REFERENCES geography_woredas(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_extension_agent_verified_by
        FOREIGN KEY (professional_info_verified_by_id) REFERENCES users(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_extension_agent_zone_region
        FOREIGN KEY (zone_id, region_id)
        REFERENCES geography_zones(id, region_id),
    ADD CONSTRAINT fk_extension_agent_woreda_zone
        FOREIGN KEY (woreda_id, zone_id)
        REFERENCES geography_woredas(id, zone_id),
    ADD CONSTRAINT ck_extension_agent_active_woreda
        CHECK (
            account_status <> 'active'
            OR (region_id IS NOT NULL AND zone_id IS NOT NULL AND woreda_id IS NOT NULL)
        ) NOT VALID,
    ADD CONSTRAINT ck_extension_agent_account_status
        CHECK (account_status IN ('pending_activation', 'active', 'suspended')) NOT VALID,
    ADD CONSTRAINT ck_extension_agent_professional_verification
        CHECK (
            (professional_info_verified = FALSE
                AND professional_info_verified_by_id IS NULL
                AND professional_info_verified_at IS NULL)
            OR (professional_info_verified = TRUE
                AND professional_info_verified_by_id IS NOT NULL
                AND professional_info_verified_at IS NOT NULL)
        ) NOT VALID;

CREATE UNIQUE INDEX IF NOT EXISTS uq_extension_agents_email
    ON extension_agents(email)
    WHERE email IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_extension_agents_employee_id
    ON extension_agents(employee_id)
    WHERE employee_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_extension_agents_region_id
    ON extension_agents(region_id);
CREATE INDEX IF NOT EXISTS ix_extension_agents_zone_id
    ON extension_agents(zone_id);
CREATE INDEX IF NOT EXISTS ix_extension_agents_woreda_id
    ON extension_agents(woreda_id);
CREATE INDEX IF NOT EXISTS ix_extension_agents_account_status
    ON extension_agents(account_status);

CREATE TABLE IF NOT EXISTS extension_agent_activations (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    verification_method VARCHAR(10) NOT NULL
        CHECK (verification_method IN ('email', 'sms')),
    otp_hash VARCHAR(64),
    otp_expires_at TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 5 CHECK (max_attempts > 0),
    last_sent_at TIMESTAMPTZ,
    resend_window_started_at TIMESTAMPTZ,
    resend_count INTEGER NOT NULL DEFAULT 0 CHECK (resend_count >= 0),
    activation_token_hash VARCHAR(64),
    activation_token_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS extension_agent_assignment_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    previous_woreda_id VARCHAR(32)
        REFERENCES geography_woredas(id) ON DELETE RESTRICT,
    new_woreda_id VARCHAR(32) NOT NULL
        REFERENCES geography_woredas(id) ON DELETE RESTRICT,
    changed_by_admin_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_extension_agent_assignment_history_user_id
    ON extension_agent_assignment_history(user_id);

-- Existing profile location strings are retained. The importer resolves
-- matching assignments and suspends unmatched legacy agents instead of
-- allowing them regional-wide access.
