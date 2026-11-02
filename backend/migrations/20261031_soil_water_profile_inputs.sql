-- Optional farmer-provided inputs for the FAO-56-inspired soil-water estimate.
-- Apply once to the existing PostgreSQL database before deploying this version.
ALTER TABLE farmer_profiles
    ADD COLUMN IF NOT EXISTS planting_date DATE NULL,
    ADD COLUMN IF NOT EXISTS soil_type VARCHAR(40) NULL,
    ADD COLUMN IF NOT EXISTS available_water_capacity_mm_per_m NUMERIC(7, 2) NULL,
    ADD COLUMN IF NOT EXISTS crop_growth_stage VARCHAR(24) NULL,
    ADD COLUMN IF NOT EXISTS irrigation_status VARCHAR(16) NULL,
    ADD COLUMN IF NOT EXISTS last_irrigation_date DATE NULL,
    ADD COLUMN IF NOT EXISTS last_irrigation_mm NUMERIC(7, 2) NULL;
