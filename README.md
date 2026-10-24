# HVACLine AI

**AI Phone Receptionist & Appointment Booking for U.S. HVAC Businesses.**

An HVAC company should receive a useful service request when it cannot answer the phone. HVACLine AI connects Twilio telephone calls to an ElevenLabs receptionist, with FastAPI controlling approved information, service intake, technician availability, reservations, and confirmed appointments. Next.js provides the service workspace. Neon PostgreSQL remains the only application database.

**Development implementation, not a production launch.** Real carrier calling has not been verified. Production sign-in, tenant onboarding, billing, notification delivery, retention automation, and external calendar synchronization remain launch blockers. Use fictional data only. No raw audio is stored by the application.

## Implemented workflow

1. A configured Twilio number routes a signed inbound webhook to the backend.
2. The existing ElevenLabs register-call adapter starts a two-way telephone conversation.
3. The caller accepts AI disclosure, the existing development consent gates, and explicit readback of their details.
4. Authenticated tools save an HVAC service request, including contact, service address, equipment issue, requested service, preferred window, and hazard flag.
5. The backend checks the business's configured ZIP codes, timezone, opening hours, technician schedules, time off, notice period, and existing appointments.
6. A five-minute reservation holds capacity. An explicit confirmation commits the appointment before the tool returns `CONFIRMED`.
7. The operations workspace shows persistent requests, appointments, calls, callbacks, and handoffs. A signed post-call event finalizes the existing confirmed customer/intake/lead flow; structured HVAC addresses are retained in that customer.

Unconfigured scheduling returns no slots. Hazardous conditions require human attention and cannot be self-booked. The agent must not diagnose equipment hazards, provide repair instructions, invent pricing, or promise an emergency response time.

## Stack and compatibility

Next.js / React / TypeScript; FastAPI / Python 3.13; SQLAlchemy 2 / psycopg 3 / Alembic; Neon PostgreSQL; Twilio; ElevenLabs. No Supabase or second runtime database.

Internal `insurance_operations`, `@insurance-operations/web`, CLI names, existing migration revisions, and `agency_id` ownership are retained to protect deployment and schema compatibility. The database's legacy `supported_insurance_categories` column is mapped to the HVAC API field `supported_service_categories`. These identifiers do not define the public product.

## Setup

Requires Node.js 26 and Python 3.13.

```bash
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local
npm ci
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Configure a development Neon branch with a pooled `DATABASE_URL` and a direct `DIRECT_DATABASE_URL`. Keep `TEST_DATABASE_URL` separate and disposable. See [database setup](docs/database-setup.md). Never commit credentials.

```bash
set -a
source .env
set +a
alembic upgrade head
insurance-operations-seed-development
```

For hosted development, enable `DEMO_SANDBOX_ENABLED` and configure a strong `DEMO_ADMIN_TOKEN` plus the existing demo telephone fields. The `/operations` workspace accepts the admin token in page memory. This is development access, not production authentication. Do not expose an unprotected development API publicly.

```bash
npm run dev:web
uvicorn insurance_operations.api:app --host "$API_HOST" --port "$API_PORT"
```

Open `/operations`, connect to the development workspace, and configure **Scheduling**. Add business hours, ZIP codes, a timezone, and real technician capacity for the fictional test scenario. Add each team's hours and unavailable dates. Scheduling starts disabled and is never seeded with pretend appointments.

The internal calendar is authoritative only for teams whose availability is maintained here. Google Calendar's HTTP adapter and provider-neutral contract are implemented and testable, but OAuth account connection, runtime synchronization, external-event reconciliation, and live provider authorization are not complete. The UI does not offer Google Calendar as connected.

## Telephone setup and live validation

Follow [the HVAC live-validation runbook](docs/hvacline-live-validation.md), [Twilio provider setup](docs/telephony-provider-setup.md), and [ElevenLabs phone setup](docs/elevenlabs-phone-agent-setup.md). Provider feature flags stay disabled until credentials, privacy settings, tool configuration, and routing are verified. Do not purchase numbers or activate billing as part of setup without owner approval.

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

See [architecture](docs/hvacline-architecture.md), [current project state](docs/project-state.md), and [remaining product work](docs/ai-receptionist-product-plan.md). Historical insurance-era continuation notes are archived; they are not current requirements.
