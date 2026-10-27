# Google Calendar and booking messages

Implementation is **unverified**. No tests, builds, linters, type checks, migrations, services, live authorizations, emails, bookings or deployment ran for this change. Continue using fictional customer data and test calendars. The existing development identity is not production authorization.

## Implemented behavior

- Operations → Scheduling connects one writable Google calendar per team. Authorization uses offline OAuth, PKCE, an expiring single-use state record and a browser-bound HttpOnly cookie. The authorization tab starts through a POST from the configured web origin. Refresh tokens and PKCE verifiers are encrypted; credentials never appear in API projections or audits. Reconnecting to the same calendar preserves bookings. Changing calendars requires clearing active bookings and pending cleanup. Disconnecting clears the local credential and pauses that team's booking until reconnecting; it does not revoke other teams' Google grants.
- Unconnected teams keep internal scheduling. Connected teams fail closed when Google cannot be verified. Each availability check reads every event page in the requested interval, expands recurring events, honors calendar-local all-day events and skips transparent/cancelled events. This deliberately uses bounded live reads rather than a stored event mirror or sync token. No external titles, descriptions, attendees or customer content are retained.
- Reservations persist a calendar binding before any event write. Confirmation rechecks external conflicts, inserts a deterministic event, verifies its identity and times, then checks conflicts again before committing the booking and its notification records. A lost response or database rollback leaves the durable hold available for retry with the same event ID. Expired/released holds are cleaned by the worker. A reschedule first persists its replacement hold, then confirms the replacement and cancels the old booking in one local transaction; failure preserves the original booking. Old external events are cleaned asynchronously.
- The worker reconciles bookings and cancellations. It deletes only events matching the appointment's ownership marker, original times and current ETag. External deletion, edits or overlap enter staff attention rather than overwriting Google or silently cancelling local bookings. Pending messages wait for a clean sync. Completed appointments keep their historical Google events.
- Confirmation, cancellation and reschedule emails are queued in the booking transaction. Reminders default to 24 hours before the visit; bookings made within that interval receive only their confirmation. Emails require the email address in the explicitly confirmed service request. Missing email/sender configuration creates a visible skipped record. Account email addresses and telephone numbers are not guessed as notification destinations. SMS is not implemented because the current intake has no separate SMS permission.
- Every queued message freezes its recipient, sender, subject and text. Retries use the same provider idempotency key and payload. The first attempt timestamp commits before contacting the provider. After 23 hours, uncertain outcomes stop as `UNKNOWN` for operator review, keeping retries inside Resend's documented 24-hour deduplication window. Permanent errors remain visible as `FAILED`; they are not silently resent under new keys.
- Signed Resend webhooks retain only provider event ID, message reference, status and time. Duplicate receipts are ignored. Receipts arriving before the send transaction commits are applied later. Failure/complaint states take precedence over delayed or out-of-order success events. `ACCEPTED` means the provider accepted the API request; `DELIVERED` means the receiving mail server accepted it. Neither proves the customer read the message. Reminders wait for confirmation delivery and stop after a bounce, complaint or cancellation.

Google Calendar does not offer an atomic “insert only if free” operation. Concurrent external writers can still overlap after the last check. Pre/post checks reduce that window; worker reconciliation and staff attention handle subsequent changes. Do not describe this as a global no-overlap guarantee. A worker outage delays cleanup, reconciliation and messages; new bookings still require live Google checks. The operator must monitor the status queue.

## Owner setup

1. Review and apply forward migration `20261027_0012` to the intended database before deploying the new backend. It adds calendar connections/authorizations, durable event bindings, notification jobs and minimal email delivery receipts. It does not backfill or email historical appointments. Install the updated Python dependencies, including `cryptography`.
2. In a Google Cloud project, enable Calendar API and create a Web application OAuth client. Configure its consent screen and test users. Register the exact callback `<API origin>/api/v1/development/hvac/integrations/google/callback`. Testing-mode grants may expire and require reconnecting; production Google verification remains a separate launch gate.
3. Set the following on both API and worker, using secret storage rather than files committed to git:

   | Setting                         | Value                                                                                      |
   | ------------------------------- | ------------------------------------------------------------------------------------------ |
   | `GOOGLE_CALENDAR_ENABLED`       | `true`                                                                                     |
   | `GOOGLE_CLIENT_ID`              | OAuth web client ID                                                                        |
   | `GOOGLE_CLIENT_SECRET`          | OAuth client secret                                                                        |
   | `GOOGLE_REDIRECT_URI`           | Exact registered callback; HTTPS except localhost/127.0.0.1                                |
   | `CALENDAR_TOKEN_ENCRYPTION_KEY` | One securely generated Fernet key, identical across API/worker and retained across deploys |

   Back up the encryption key in secret storage. Replacing it without re-encrypting stored credentials requires reconnection. Do not print or copy it into issues, logs, code or session notes. The runtime does not provide key rotation automation.

4. Set `WEB_ORIGIN` on the API to the exact frontend origin. Allow the authorization popup, complete consent and refresh the connections panel. Select separate calendars with write access for separate teams. Existing active internal bookings must finish or be cancelled before connecting their team; the application does not silently copy existing bookings.
5. For email, verify a sender domain in Resend. Configure a webhook at `<API origin>/api/v1/providers/resend/booking-events` for `email.sent`, `email.delivered`, `email.delivery_delayed`, `email.bounced`, `email.complained`, `email.failed` and `email.suppressed`. Set `BOOKING_EMAIL_ENABLED=true`, `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET` and `BOOKING_EMAIL_FROM` on API/worker. `BOOKING_EMAIL_FROM` must be an email address. Keep `BOOKING_REMINDER_HOURS=24` or deliberately choose 1–168 hours. Email addresses in demo requests must be fictional/test destinations under your control.
6. Update the private browser agent from `docs/elevenlabs-agent-setup.md` if it should offer the optional booking-email destination. This source change does not update hosted agent configuration. Phone service requests now reject email addresses that differ from the existing verbal-confirmation receipt.
7. Deploy a persistent worker using the same database and integration configuration, `WORKER_NAME` and `insurance-operations-worker`. `WORKER_POLL_SECONDS` defaults to 30. The worker processes bounded batches and uses database locks plus provider idempotency to coordinate multiple instances. This document does not provision or start a hosting service.
8. Disable query-string access logging for the OAuth callback at the API and reverse proxy so authorization codes are not retained in logs. The Render start-command example adds `--no-access-log`; use the same flag for owner-started Uvicorn. Do not enable HTTP debug-body logging.

## Owner commands — not executed

From the active worktree `/private/tmp/hvacline-browser-demo`, install dependencies using the project's Python 3.13 environment:

```sh
python -m pip install -e '.[dev]'
```

Focused non-database regression specifications:

```sh
APP_ENVIRONMENT=test pytest tests/test_booking_integrations.py tests/test_hvac_calendar.py tests/test_hvac_availability.py tests/test_worker.py
```

Use an explicitly isolated, disposable `TEST_DATABASE_URL` for the next commands. The database fixture downgrades/rebuilds its target. Never point it at a shared, development or production database.

```sh
APP_ENVIRONMENT=test alembic upgrade head
APP_ENVIRONMENT=test alembic current
APP_ENVIRONMENT=test alembic check
APP_ENVIRONMENT=test pytest tests/database/test_hvac_scheduling.py tests/database/test_migrations.py tests/database/test_table_ownership.py
```

The database fixture tears down its schema on exit. If inspecting the disposable database afterward, upgrade it again before running `alembic current` or `alembic check`.

Static/frontend/full regression commands:

```sh
ruff format --check .
ruff check .
mypy apps/backend/src tests
npm run verify:web
APP_ENVIRONMENT=test pytest
```

Only after reviewing the target database and its backups, the owner may apply the deployment migration:

```sh
alembic upgrade head
```

After deployment configuration is reviewed, the owner may run readiness and start the managed worker:

```sh
insurance-operations-worker --check
insurance-operations-worker
```

## Manual acceptance — not executed

1. Connect a test calendar with write access; deny consent; retry; reject a callback without the originating cookie; reject replay/expired state; verify another tenant cannot inspect or mutate the connection. No token, verifier or authorization code should appear in stored projections/audits/logs.
2. Add timed, all-day, recurring, transparent and cancelled events around a DST boundary. Check offered slots and booking attempts. Revoke Google access and verify booking stops and the worker reports reconnection required.
3. Reserve a slot, add a conflicting Google event, then confirm. It must not return `CONFIRMED`. Repeat an identical successful confirmation and a lost-response retry: one local appointment, one Google event and one confirmation/reminder pair must result.
4. Interrupt a confirmation after Google creates an event but before its local transaction commits. Retry with the same reservation, then separately let another such hold expire. The first should recover; the second should be cleaned by the worker without deleting an unrelated event.
5. Reschedule with an injected provider failure: retain the original confirmed appointment and the durable replacement hold. Retry the same key successfully, then check old-event cleanup and cancellation of old pending reminders. Concurrent reschedules must not create two confirmed replacements. Check ordinary hold release and hazardous requests too.
6. Edit/delete a confirmed event externally or add a later conflict. Refresh Scheduling after a worker tick: staff attention, local booking preserved and no new confirmation/reminder while unsafe. Restore the intended event and check reconciliation recovers. Race an external edit against cancellation to exercise ETag failure handling.
7. Book with and without a confirmed test email. Check visible skipped states, provider acceptance and signed delivery receipts. Stop the worker across an email attempt/restart, return 429/5xx, replay a webhook and deliver a receipt before the send transaction commits. Check one provider message per immutable key. A bounce/complaint must remain visible even after an older delivered receipt arrives.
8. Move a test reminder's due time on the disposable database or use a controlled clock. It must wait for delivered confirmation, stay suppressed for cancelled/rescheduled/hazardous bookings and not send after the visit starts. A notification with a first attempt older than 23 hours must stop for review without another provider call.
9. Check Voice, Chat, on-screen fallback, customer history and the operations calendar still agree with persisted bookings. Confirm the new controls and status messages work on mobile and with keyboard navigation.

## Provider references

- [Google server-side OAuth](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google event listing and recurrence expansion](https://developers.google.com/workspace/calendar/api/v3/reference/events/list)
- [Google deterministic event creation](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert)
- [Resend idempotency window and conflict responses](https://resend.com/docs/dashboard/emails/idempotency-keys)
- [Resend delivery event meanings](https://resend.com/docs/webhooks/event-types)
- [Svix signature verification](https://docs.svix.com/receiving/verifying-payloads/how-manual)
