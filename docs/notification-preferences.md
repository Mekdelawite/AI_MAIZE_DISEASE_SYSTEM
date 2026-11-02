# Farmer notification preferences

`PUT /api/profile` stores the preferences on the authenticated farmer's existing profile. Existing profile rows with no JSON preference value use the defaults exposed by `GET /api/profile`: all in-app categories enabled, category SMS enabled, crop reminders on the scheduled day, quiet hours disabled, and `Africa/Addis_Ababa`. The existing `sms_opt_in` field remains the master SMS permission; a category preference can narrow consent but cannot grant it.

Crop activity reminders use the selected 0–3 day offset and the farmer's IANA timezone. Quiet hours use local wall-clock time, including periods crossing midnight. The scheduler polls every 15 minutes so a due reminder is released after quiet hours, and activity keys prevent a second in-app or SMS delivery after retries.

Disease and regional outbreak alerts honor the important-alert in-app and SMS category choices and the SMS master opt-in. By default, urgent outbreak SMS may bypass quiet hours. Set `CRITICAL_ALERTS_BYPASS_QUIET_HOURS=false` to persist urgent SMS as deferred records and deliver them when quiet hours end. The scheduler rechecks the farmer's current SMS consent and important-alert SMS preference before delivery. This setting never bypasses category preferences or SMS consent. Reading an in-app notification does not change SMS status.

Apply `20261102_farmer_notification_preferences.sql` once against the application PostgreSQL database before deploying the updated backend. The added columns are nullable for safe compatibility with existing records; application defaults do not rewrite notification history or existing SMS consent.
