# Development setup

[Back to HVACLine AI](../README.md)

Setup and verification instructions moved from the product README. Development remains fictional-data only; runtime acceptance is pending. For the latest account, MFA, memory and WhatsApp configuration, start with the [environment handoff](environment-handoff.md).

## Stack and compatibility

Next.js / React / TypeScript; FastAPI / Python 3.13; SQLAlchemy 2 / psycopg 3 / Alembic; Neon PostgreSQL; Twilio; ElevenLabs. No Supabase or second runtime database.

Internal `insurance_operations`, `@insurance-operations/web`, CLI names, existing migration revisions, and `agency_id` ownership are retained to protect deployment and schema compatibility. The database's legacy `supported_insurance_categories` column is mapped to the HVAC API field `supported_service_categories`. These identifiers do not define the public product.

## Setup

Requires Node.js 24 and Python 3.13.

```bash
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local
npm ci
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Configure a development Neon branch with a pooled `DATABASE_URL` and a direct `DIRECT_DATABASE_URL`. Keep `TEST_DATABASE_URL` separate and disposable. See [database setup](database-setup.md). Never commit credentials.

```bash
set -a
source .env
set +a
alembic upgrade head
insurance-operations-seed-development
```

For hosted development, enable `DEMO_SANDBOX_ENABLED` and configure a strong `DEMO_ADMIN_TOKEN` and no telephone fields for browser-only use. The `/operations` workspace accepts the admin token in page memory. This is development access, not production authentication. Do not expose an unprotected development API publicly.

```bash
npm run dev:web
uvicorn insurance_operations.api:app --host "$API_HOST" --port "$API_PORT"
```

The development seed initializes a missing fictional-business calendar in `business_schedules`: booking enabled, America/New_York, ZIP 10001, Monday–Friday 09:00–17:00, 60-minute visits, 120-minute booking/change notice, and one Test Team. It preserves existing calendars, including deliberately disabled ones, and creates no appointments. Open `/operations` → **Scheduling** to review or edit the persisted values. Other businesses require their own configuration. See [development calendar defaults](development-calendar-defaults.md) for owner commands and checks; this change is unverified.

Teams without an external connection use the maintained internal schedule. Google Calendar connection, live conflict checks, durable event recovery/reconciliation and queued booking emails/reminders are now implemented behind opt-in development settings, but remain owner-unverified. Migration `20261027_0012`, OAuth/Resend setup and scheduled job execution are required. Jobs can use a [Vercel Python function with a free external scheduler](vercel-booking-jobs.md), or the standalone worker. See [calendar and booking messages](calendar-and-booking-messages.md) for behavior, limitations, exact commands and manual acceptance.

The development seed also supplies 28 approved fictional-business FAQs and missing receptionist settings. To initialize this content without changing phone routing, use `insurance-operations-seed-development --skip-telephony` in the reviewed development environment. Existing edited or inactive FAQs and calendars are preserved. No prices, warranties, financing terms or callback promises are invented. See [development business content](development-business-content.md) for scope, exact owner checks and application instructions.

## Browser chat and voice without phone numbers

Enable the browser feature flags and reuse the private ElevenLabs browser agent using [browser setup](elevenlabs-agent-setup.md) and all eight [client tools](elevenlabs-browser-tools.json). Customer `/book` defaults to silent **Chat**, with **Voice** available separately. Customers can also type during Voice; replies in that mode can still be spoken. Both modes use the same approved FAQs, actual available slots and two explicit readback confirmations for saving and booking. The existing on-screen review and booking flow remains available. Saved requests and bookings appear in the same workspace. The owner reports voice works; chat and appointment booking remain unverified. See [customer chat](customer-chat.md) for migration `20261025_0011`, deployment steps and exact owner checks. No new environment variables or OpenAI key are needed.

Phone numbers and human transfers are optional for this path. Keep telephone provider routing disabled without numbers. Public production customer access remains blocked by unfinished identity and tenant provisioning; never share the development admin token with customers. This new flow is implemented but unverified.

## Optional local browser conversations

A separate development workspace can select local Chat/Voice using whisper.cpp,
Ollama and Piper. ElevenLabs stays the default for the customer account flow.
See [local browser setup](local-browser-voice.md) for the optional dependency,
configuration, compatibility limits and exact owner checks. Implementation and
runtime remain unverified.

## Telephone setup and live validation

Follow [the HVAC live-validation runbook](hvacline-live-validation.md), [Twilio provider setup](telephony-provider-setup.md), and [ElevenLabs phone setup](elevenlabs-phone-agent-setup.md). Provider feature flags stay disabled until credentials, privacy settings, tool configuration, and routing are verified. Do not purchase numbers or activate billing as part of setup without owner approval.

## Verification

```bash
npm run verify:web
ruff format --check .
ruff check .
mypy apps/backend/src tests
APP_ENVIRONMENT=test pytest tests --ignore=tests/database
insurance-operations-worker --check
```

Database tests rebuild the selected database. Run them only when `TEST_DATABASE_URL` is confirmed isolated and disposable. CI provisions its own PostgreSQL service.

```bash
APP_ENVIRONMENT=test pytest tests/database
APP_ENVIRONMENT=test alembic upgrade head
APP_ENVIRONMENT=test alembic current
APP_ENVIRONMENT=test alembic check
```

Automated provider fixtures do not prove a live telephone call. The first live acceptance gate is a synthetic caller reaching the configured number, completing consent and intake, receiving a database-confirmed appointment, and the operator seeing the request and booking in `/operations`.

See [architecture](hvacline-architecture.md), [current project state](project-state.md), and [remaining product work](ai-receptionist-product-plan.md). Historical insurance-era continuation notes are archived; they are not current requirements.
