# Project State

## Product and scope

HVACLine AI is an AI phone receptionist and appointment-booking product for U.S. HVAC service businesses only. The October 24, 2026 owner mission supersedes the insurance roadmap, frontend freeze, and earlier restrictions against running the named verification commands. Development remains synthetic-only; live carrier success and production readiness must not be claimed without evidence.

## Architecture

Next.js/TypeScript web, FastAPI/Python 3.13 backend, separate worker, SQLAlchemy 2/psycopg 3/Alembic, and Neon PostgreSQL only. Keep established Python/workspace/CLI names, agency ownership keys, and migration history for compatibility. Public receptionist categories are exposed as `supported_service_categories`, mapped to the legacy storage column.

Existing signed Twilio ingress, ElevenLabs register-call voice connection, secret-authenticated tools, HMAC post-call verification, consent/readback receipts, approved FAQs, leads, callbacks, transfer commands, quotas, and audits are reused. No raw audio is stored. Transcript/customer/lead finalization stays in the signed post-call flow.

## HVAC implementation

Forward migration `20261024_0009` adds business schedules, confirmed HVAC service requests, and appointments. Scheduling uses per-business ZIP codes, IANA timezone, hours, team calendars/time off, duration, notice and horizon. Mutations lock the tenant schedule row; payload-bound booking keys prevent conflicting retries; appointments have a composite tenant/request foreign key. Reservations expire after five minutes. Confirmation, cancellation, and atomic rescheduling persist before returning success.

Authenticated phone tools verify active session/call ownership and expiry. HVAC service intake requires the existing contact-readback receipt and explicit structured confirmation. Hazardous requests enter human attention and cannot self-book. The operations projection excludes transcripts and shows real stored requests, bookings, calls and open handoffs. Existing receptionist and knowledge editors are reused inside the protected workspace, forwarding the in-memory admin token in headers. `/operations` uses existing development identity and hosted-sandbox token gates; this is not production login.

The Google Calendar HTTP adapter and provider-neutral contract are implemented with failure-closed availability and deterministic event verification. OAuth, runtime calendar connection/sync and reconciliation are incomplete; Google is not exposed as connected. The current calendar is explicitly internal and requires accurate operator-maintained availability.

## Verification during this execution

GitHub CI at implementation commit `0cbbe8f` passed both jobs: 83 Python tests, 24 web tests, Ruff format/lint, mypy, the production web build, migration upgrade/current/no-drift checks at `20261024_0009`, and worker readiness. Database tests used CI's isolated PostgreSQL 17 service. No shared or production Neon database was touched. All 177 tracked branch files were compared against local source and matched before the final reservation-notice fix; that fix also passed CI.

The local host cannot complete Next build because its OS memory-statistics interface is unavailable (`uv_resident_set_memory` ENOENT); the GitHub production build independently passed. No live carrier call, provider dashboard/privacy validation, or Google authorization has been verified. See `docs/verification.md` for evidence.

## Remaining launch blockers

- Live synthetic Twilio → ElevenLabs → backend → database → dashboard call and transfer validation.
- Production identity, roles, account onboarding, tenant/provider credential and agent provisioning.
- Google OAuth, token vault, runtime sync, external conflict and failure reconciliation.
- Caller verification before existing-customer lookup or telephone appointment changes.
- Durable notifications, reminders, callback completion workflows and urgent alert delivery.
- Billing, detailed usage/cost tracking, production limits, observability/recovery, and retention automation.
- Production deployment and acceptance tests. Current development-only gates remain intentional.

## Guidance

Use README, `docs/hvacline-architecture.md`, and `docs/hvacline-live-validation.md`. Insurance continuation documents are archived as history, not current requirements. Update this note only with verified implementation and results; never store secrets, caller content, or credentials.

## Browser HVAC implementation — owner verification pending

The protected operations workspace embeds existing WebRTC with the in-memory admin header propagated to authorization, FAQ, end and confirmation requests. Browser drafts include HVAC address, category, preference and hazard fields. Explicit review confirms customer, lead, transcript, HVAC request and audit in the existing idempotent transaction; its replay response includes the same service request ID. No new migration is needed. On-screen booking reuses the scheduling backend after review and preserves a reservation key across identical retries. Hazardous requests enter human attention and cannot self-book.

Demo phone numbers are optional; empty values normalize to absent, nonempty invalid numbers still fail. The seed skips telephone setup without an inbound number and disables transfer when its destination is absent. Existing telephone configuration is not disabled by browser-only seeding. Production identity/customer access and live browser verification remain incomplete. No tests, builds, lint, type checks, migrations or live checks ran for this slice, per owner instruction. Use docs/elevenlabs-agent-setup.md for exact setup and deferred verification.

## Spoken browser booking — implemented, owner verification pending

The browser adapter now registers eight blocking client tools for draft updates, approved FAQs, intake readback/confirmation, actual availability, reservation, appointment confirmation and hold release. Backend-generated readbacks must match the latest agent transcript and be followed by an unambiguous affirmative user turn; an agent-supplied boolean alone cannot save or book. Spoken intake confirmation reuses the existing idempotent customer/lead/intake/HVAC transaction while keeping the voice session live. Booking resolves the confirmed request through its persisted idempotency response and verifies live browser session, actor, tenant and appointment ownership. No migration or second database is added.

Confirmed intakes retain their live concurrency slot until disconnect/expiry; FAQ lookup remains available during the live confirmed session. Disconnect preserves saved requests and appointments. Explicitly released holds use a separate operation that cannot cancel confirmed appointments. Hazard reports block new self-booking and release unconfirmed holds; existing confirmed appointments require human handling. The browser keeps exact save retry payloads and reservation keys in memory and displays backend-confirmed booking receipts. Connection startup now waits for the pinned ElevenLabs SDK's onConnect callback rather than awaiting its void startSession return.

Focused Python, browser-controller and database/API test specifications were added. Source formatting was applied to changed TypeScript/JSON only. No tests, builds, linters, type checks, migrations, seeds, readiness checks, services or live provider calls were run. Provider dashboard setup, effective Render/frontend configuration and successful live browser booking remain unverified. Deployment is left to the owner because main automatically triggers Render builds. Public customer authentication and tenant provisioning remain unfinished; development/privacy gates remain required.
