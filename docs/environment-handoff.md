# Environment handoff

Mandatory customer MFA requires API-only `CUSTOMER_MFA_ENCRYPTION_KEY` and forward migration `20261028_0015` after pending memory `0014`. **UNVERIFIED**. [Customer MFA setup and owner checks](customer-mfa.md) covers stable key generation/backup, existing-session revocation, mandatory enrollment and backup-code replacement. No staff/Operations or provider configuration change. Never expose this key to the frontend.

Optional customer memory adds API-only `CUSTOMER_MEMORY_ENABLED`, `CUSTOMER_MEMORY_RETENTION_DAYS`, `CUSTOMER_MEMORY_CONTEXT_CHARACTERS` and forward migration `20261028_0014`. **UNVERIFIED**. See [customer memory setup and owner checks](customer-memory.md) for agent tools, explicit WhatsApp account linking and bounded retention cleanup. No new provider credentials or external memory service.

Direct inbound WhatsApp voice adds API-only configuration and forward migration `20261028_0013`. Status: **UNVERIFIED**. Follow [WhatsApp setup and owner checks](whatsapp-inbound-calling.md); preserve existing browser, Calendar and notification settings. Twilio remains optional.

The current source is `/private/tmp/hvacline-browser-demo`. Deployment and runtime remain owner-unverified. No environment values, secrets, services, migrations, tests or hosting settings were changed during this handoff.

## New variables for booking limits

Set these in **Render → hvacline API → Environment**:

| Variable                           | Value | Behavior                                                                                      |
| ---------------------------------- | ----- | --------------------------------------------------------------------------------------------- |
| `CUSTOMER_MAX_ACTIVE_APPOINTMENTS` | `1`   | One active appointment place per signed-in customer, including unexpired holds                |
| `CUSTOMER_MAX_BOOKING_CHANGES`     | `1`   | One successful date/time change per booking history; completed retries do not consume another |

Both default to 1 if omitted. Save and restart/redeploy the API after changing values. The Vercel frontend reads the effective values from the authenticated API, so neither variable belongs in its environment or needs a `NEXT_PUBLIC_` equivalent. The separate Vercel job function does not require these quota settings.

## Three-minute conversation — retain existing values

| Location                                                  | Setting                             | Value         |
| --------------------------------------------------------- | ----------------------------------- | ------------- |
| Render API                                                | `CONVERSATION_MAX_DURATION_SECONDS` | `180`         |
| Render API, if telephone is configured                    | `PHONE_MAX_DURATION_SECONDS`        | `180`         |
| ElevenLabs private browser agent → Advanced → Call limits | Maximum conversation duration       | `180` seconds |

The page countdown needs the updated frontend, not another environment variable. No ten-minute migration or setting is part of the current implementation.

## Separate Vercel Python job project

Set these in **Vercel → job project → Settings → Environment Variables → Production**, then redeploy that project:

| Variable              | Value                                                                           |
| --------------------- | ------------------------------------------------------------------------------- |
| `APP_ENVIRONMENT`     | `development`                                                                   |
| `WORKER_NAME`         | `vercel-booking-jobs`                                                           |
| `DATABASE_URL`        | The same existing pooled Neon database URL used by the Render API               |
| `DATABASE_SSL_MODE`   | `require`                                                                       |
| `BOOKING_JOBS_SECRET` | A separate randomly generated secret, at least 32 characters with no whitespace |

Generate the job secret once in a password manager or locally with `python -c 'import secrets; print(secrets.token_urlsafe(32))'`. Enter it directly into the job project's secret configuration and the scheduler's private authorization header. Keep an existing job secret if already configured. No secret value belongs in source, notes, a URL or a `NEXT_PUBLIC_` variable. `BOOKING_JOBS_SECRET` is not required by the Render API or frontend.

For free frequent execution, configure the external scheduler with POST to `https://<job-project-host>/api/v1/internal/booking-jobs/run`, every five minutes, and header `Authorization: Bearer <same BOOKING_JOBS_SECRET>`. Job hosting alone does not schedule execution. See `docs/vercel-booking-jobs.md` for Vercel Hobby scheduling limits and setup. There is no persistent worker start command on Vercel.

## Calendar and email — matching values on API and job project

If not already configured, set the following in **both Render API and Vercel job project**. Preserve existing working credentials and the shared encryption key.

| Variable                        | Value                                                                               |
| ------------------------------- | ----------------------------------------------------------------------------------- |
| `GOOGLE_CALENDAR_ENABLED`       | `true` after all Google values below are configured; otherwise `false`              |
| `GOOGLE_CLIENT_ID`              | Your Google OAuth Web application client ID                                         |
| `GOOGLE_CLIENT_SECRET`          | That OAuth client's secret                                                          |
| `GOOGLE_REDIRECT_URI`           | `https://api.hvacline.online/api/v1/development/hvac/integrations/google/callback`  |
| `CALENDAR_TOKEN_ENCRYPTION_KEY` | The same existing valid Fernet key on both services; retain it across redeployments |
| `BOOKING_EMAIL_ENABLED`         | `true` after the Resend values below are configured; otherwise `false`              |
| `RESEND_API_KEY`                | Your Resend sending API key                                                         |
| `RESEND_WEBHOOK_SECRET`         | The Resend booking webhook's signing secret, beginning `whsec_`                     |
| `BOOKING_EMAIL_FROM`            | A sender email address on your verified Resend domain                               |
| `BOOKING_REMINDER_HOURS`        | `24`                                                                                |

Google's OAuth client must register the redirect URI above exactly. The Resend webhook belongs at `https://api.hvacline.online/api/v1/providers/resend/booking-events`; it stays on Render, not the job project. See `docs/calendar-and-booking-messages.md` for subscribed events and acceptance.

## Existing frontend/API connection — retain

| Location                       | Variable                   | Value                                                                                              |
| ------------------------------ | -------------------------- | -------------------------------------------------------------------------------------------------- |
| Render API                     | `APP_ENVIRONMENT`          | `development`                                                                                      |
| Render API                     | `API_HOST`                 | `0.0.0.0`                                                                                          |
| Render API                     | `API_PORT`                 | `10000`                                                                                            |
| Render API                     | `WEB_ORIGIN`               | `https://hvacline.online`, if this is the exact browser origin; use the actual origin if different |
| Vercel frontend                | `NEXT_PUBLIC_API_BASE_URL` | `https://api.hvacline.online`                                                                      |
| Render API and Vercel frontend | `CUSTOMER_PORTAL_SECRET`   | The same existing server-only customer-portal secret                                               |

Keep the existing database, identity, portal/voice feature flags and ElevenLabs credentials. The new booking limits do not require replacing them. All application environments remain development-only despite hosting dashboards labelling the deployment environment Production.

## Deployment and owner checks

Deploy the updated Render API first, then the Vercel frontend. The latest limits/modal/timer changes require no new migration; the calendar/email slice requires the existing `20261027_0012` schema. The job project only needs redeployment when its source or environment changes. Hosting settings were not changed by Codex.

No checks ran for this handoff. Exact commands and manual acceptance are in `docs/customer-booking-limits.md`, `docs/booking-details-and-timer.md` and `docs/vercel-booking-jobs.md`. For the included test-fixture isolation change, the owner may run `APP_ENVIRONMENT=test python -m pytest tests/database/test_hvac_scheduling.py` only with an explicitly isolated, disposable `TEST_DATABASE_URL`; its fixture downgrades/rebuilds that database.
