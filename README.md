# AI_MAIZE_DISEASE_SYSTEM

## Farmer Web Push setup

Web Push is optional and disabled until the backend receives all three VAPID
environment variables documented in [.env.example](./.env.example):
`WEB_PUSH_VAPID_PUBLIC_KEY`, `WEB_PUSH_VAPID_PRIVATE_KEY`, and
`WEB_PUSH_VAPID_SUBJECT`. Generate a P-256 key pair as shown there, mount the
private PEM file securely for the backend and set `WEB_PUSH_VAPID_PRIVATE_KEY`
to its path, and run the new migration
[`20261105_farmer_web_push.sql`](./backend/migrations/20261105_farmer_web_push.sql)
against PostgreSQL. Install backend requirements after deployment; the pinned
`pywebpush` package implements Web Push encryption and VAPID.

Farmers enable push explicitly in Profile → notification preferences. Push
requires HTTPS, a supported browser with the existing MaizeCare service worker,
and notification permission. Push payloads contain only a generic update and
open the authenticated farmer dashboard. Delivery is not considered verified
until tested with a real browser subscription and valid deployment VAPID keys.

## Extension-agent onboarding

Extension agents are created by an administrator in the Admin Dashboard and
must be assigned to exactly one woreda. Before deploying the onboarding code,
apply [`20261107_extension_agent_onboarding.sql`](./backend/migrations/20261107_extension_agent_onboarding.sql)
to PostgreSQL, then run `python -m backend.scripts.import_geography` from the
repository root to populate the local region/zone/woreda hierarchy and resolve
legacy agent assignments. Unmatched legacy assignments remain suspended until
an administrator assigns them.

Email activation requires the backend SMTP settings in
[.env.example](./.env.example); SMS activation uses the existing SMS provider
configuration. Do not enable email as an administrator-selected method until
SMTP delivery has been configured and tested.