# Vercel booking jobs

Implementation and hosting are **unverified**. No tests, builds, linters, type checks, migrations, services, provider requests or deployment ran for this change. Use fictional customers and test calendars. The API remains on Render; job execution can use a separate Vercel Python project, with the existing PostgreSQL queue and no new migration. The standalone worker remains supported.

## Deploy the job function

1. Create a separate Vercel project from this repository and `main`. Name it `hvacline-jobs` or another available name. Set Root Directory to the repository root, leave it blank, and choose the FastAPI framework preset. The root `vercel.json` sets dependency installation to `python -m pip install .`; `app.py` is the Python entrypoint. There is no persistent start command. Python 3.13 is selected by the existing project files. Do not change the existing frontend project's `apps/web` root.
2. Set `APP_ENVIRONMENT=development`, `WORKER_NAME=vercel-booking-jobs`, `DATABASE_URL` to the same Neon database as the Render API, and `DATABASE_SSL_MODE=require`. Use the pooled URL for runtime. Migrations remain on the API deployment; the job project does not seed or migrate. Ensure that database already has migration `20261027_0012` before invoking jobs.
3. Copy the enabled Google/email integration configuration from the API: `GOOGLE_CALENDAR_ENABLED`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `CALENDAR_TOKEN_ENCRYPTION_KEY`, `BOOKING_EMAIL_ENABLED`, `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `BOOKING_EMAIL_FROM` and `BOOKING_REMINDER_HOURS`. Keep the exact same encryption key. The Google callback and Resend webhook stay on `https://api.hvacline.online`, not the job function. Incomplete integrations must stay disabled on both projects.
4. Add `BOOKING_JOBS_SECRET`, a separate randomly generated secret with at least 32 characters and no whitespace, using secret storage. Missing/invalid configuration stops startup. Never put it in a URL, repository, frontend variable or notes. The scheduler needs this secret, not database/provider credentials.
5. Deploy this project to its stable production URL. Vercel's Production environment label does not change the application's development-only identity gates. If Vercel Deployment Protection blocks the scheduler, use the project's supported automation-bypass mechanism and keep bearer authentication enabled. Do not weaken the frontend or API's protections. Review Vercel's current plan eligibility and included usage for this account.

Vercel validates the repository's Node engine before the Python build. Root/web manifests, lockfile metadata, `.nvmrc` and CI now select Node 24, replacing the unsupported Node 26 requirement. Set Node.js Version to `24.x` in the Vercel project's Build and Deployment settings if needed, and deploy the latest commit instead of retrying `7dbd5aa`. This repair is unverified. Owner commands: `nvm install`, `nvm use`, `npm ci`, `npm run verify:web`. Manually confirm the job deployment passes Node version selection, installs the Python package and reaches function startup.

The function exposes only `POST /api/v1/internal/booking-jobs/run`. It does not expose the customer API, provider webhooks, documentation or a public job-status endpoint.

## Schedule free invocations

Vercel Hobby cron runs at most once per day and is unsuitable for frequent booking jobs. Use a free external scheduler such as cron-job.org:

| Scheduler setting | Value |
| --- | --- |
| URL | `https://<job-project-host>/api/v1/internal/booking-jobs/run` |
| Method | `POST` |
| Schedule | Every five minutes (`*/5 * * * *`, UTC) |
| Header | `Authorization: Bearer <BOOKING_JOBS_SECRET>` |
| Body | Empty |

Enable failure notifications. cron-job.org documents a 30-second HTTP timeout; the application uses a cooperative 20-second budget, checks the deadline before subsequent work/provider calls and while reading provider bodies, and bounds connection/statement/lock waits. Vercel's configured function maximum is 60 seconds. Network/platform stalls and cold starts can still exceed the scheduler timeout; a disconnected caller is not proof that the invocation stopped. The next authenticated request checks the database lock and retries durable work safely. Neither the free scheduler nor this implementation guarantees exact reminder times or immediate confirmations.

Successful responses contain only `status`, `processed` and `failed`. `completed` means the selected batch finished, not that the entire queue is empty or an email was delivered. `busy` means another batch holds the lock. `deferred` means the budget expired and remaining work awaits a later invocation. `processed` counts handlers that returned; provider-level failures/retries remain visible in Operations. Monitor repeated `busy`/`deferred`, nonzero failures, pending jobs and provider delivery states. The scheduler may need re-enabling after repeated failures.

PostgreSQL transaction advisory locking coordinates both the job function and updated standalone worker; transaction end releases the lock, including rollback or connection loss. Notifications and calendar work are interleaved so a normal backlog in one category does not consume every selected position. Existing booking transactions, frozen email payloads, first-attempt timestamps, provider idempotency keys, delivery receipts and ownership checks remain authoritative. Interrupted work rolls back its current local transaction; external unknown outcomes retain the existing recovery behavior. The runner does not spawn detached tasks or an in-memory queue.

## Owner checks — not executed

From the active source with Python 3.13 and development dependencies installed:

```sh
python -m pytest tests/test_booking_jobs.py tests/test_worker.py tests/test_booking_integrations.py tests/test_settings.py
ruff format --check .
ruff check .
mypy apps/backend/src tests app.py
```

Only with an explicitly isolated, disposable `TEST_DATABASE_URL` and the existing database test configuration:

```sh
APP_ENVIRONMENT=test python -m pytest tests/database/test_booking_jobs.py tests/database/test_hvac_scheduling.py
```

The database fixture downgrades/rebuilds its target. Never point it at a shared or hosted development/production database.

Manual acceptance: deploy the job project, send a request without authorization (401), then an authenticated POST (200 and sanitized counts). Confirm an ordinary GET is rejected. Trigger overlapping invocations and confirm only one batch executes. On synthetic data, book with a confirmed test email, verify one message per immutable key across repeated ticks, replay signed delivery receipts, and check a due reminder. Repeat cancellation/rescheduling and external-calendar conflict recovery. Interrupt a provider attempt and retry; check database state, provider references and Operations agree. Check deadline deferral leaves unfinished work recoverable and scheduler failure notifications arrive. Full calendar/email acceptance remains in `docs/calendar-and-booking-messages.md`.

## References

- [Vercel Python functions](https://vercel.com/docs/functions/runtimes/python)
- [Vercel cron limits](https://vercel.com/docs/cron-jobs/usage-and-pricing)
- [Vercel function limits](https://vercel.com/docs/functions/limitations)
- [cron-job.org scheduling](https://cron-job.org/en/)
- [cron-job.org execution limits](https://cron-job.org/en/faq/)
