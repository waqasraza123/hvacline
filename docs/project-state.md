# Project State

## Product and scope

HVACLine AI is an AI phone receptionist and appointment-booking product for U.S. HVAC service businesses only. The October 24, 2026 owner mission supersedes the insurance roadmap, frontend freeze, and earlier restrictions against running the named verification commands. Development remains synthetic-only; live carrier success and production readiness must not be claimed without evidence.

## Architecture

GitHub redirected the authorized feature-branch push to `waqasraza123/hvacline` on October 25, 2026; the former `insurance-operations-ai` URL still redirected successfully at that time. Render's repository binding and deployed revision have not been verified.

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

## Homepage branding — owner verification pending

The public homepage uses a navy/electric-blue visual system and introduces Line as the AI booking assistant. Marketing copy focuses on HVAC appointment booking, with prominent entry points, responsive service/process sections, native FAQs and a fixed booking launcher. Metadata, brand mark and favicon match. Booking/sign-in links target the customer `/book`, `/login` and `/signup` routes; `/operations` remains a separately protected administrator workspace. The customer routes and draft authentication remain development-only and owner-unverified, not production identity. No tests, builds, linters, type checks, services, browser previews or live checks ran. Owner commands and manual checks are in `docs/homepage-branding.md`.

## Browser HVAC implementation — owner verification pending

The protected operations workspace embeds existing WebRTC with the in-memory admin header propagated to authorization, FAQ, end and confirmation requests. Browser drafts include HVAC address, category, preference and hazard fields. Explicit review confirms customer, lead, transcript, HVAC request and audit in the existing idempotent transaction; its replay response includes the same service request ID. No new migration is needed. On-screen booking reuses the scheduling backend after review and preserves a reservation key across identical retries. Hazardous requests enter human attention and cannot self-book.

Demo phone numbers are optional; empty values normalize to absent, nonempty invalid numbers still fail. The seed skips telephone setup without an inbound number and disables transfer when its destination is absent. Existing telephone configuration is not disabled by browser-only seeding. Production identity/customer access and live browser verification remain incomplete. No tests, builds, lint, type checks, migrations or live checks ran for this slice, per owner instruction. Use docs/elevenlabs-agent-setup.md for exact setup and deferred verification.

## Spoken browser booking — implemented, owner verification pending

The browser adapter now registers eight blocking client tools for draft updates, approved FAQs, intake readback/confirmation, actual availability, reservation, appointment confirmation and hold release. Backend-generated readbacks must match the latest agent transcript and be followed by an unambiguous affirmative user turn; an agent-supplied boolean alone cannot save or book. Spoken intake confirmation reuses the existing idempotent customer/lead/intake/HVAC transaction while keeping the voice session live. Booking resolves the confirmed request through its persisted idempotency response and verifies live browser session, actor, tenant and appointment ownership. No migration or second database is added.

Confirmed intakes retain their live concurrency slot until disconnect/expiry; FAQ lookup remains available during the live confirmed session. Disconnect preserves saved requests and appointments. Explicitly released holds use a separate operation that cannot cancel confirmed appointments. Hazard reports block new self-booking and release unconfirmed holds; existing confirmed appointments require human handling. The browser keeps exact save retry payloads and reservation keys in memory and displays backend-confirmed booking receipts. Connection startup now waits for the pinned ElevenLabs SDK's onConnect callback rather than awaiting its void startSession return.

Focused Python, browser-controller and database/API test specifications were added. Source formatting was applied to changed TypeScript/JSON only. No tests, builds, linters, type checks, migrations, seeds, readiness checks, services or live provider calls were run. Provider dashboard setup, effective Render/frontend configuration and successful live browser booking remain unverified. Deployment is left to the owner because main automatically triggers Render builds. Public customer authentication and tenant provisioning remain unfinished; development/privacy gates remain required.

## Provisioned browser agent — website acceptance pending

On October 25, 2026 the owner-authorized ElevenLabs API setup created a separate private HVACLine browser agent with the repository prompt and eight blocking client tools; saved configuration was read back. It retains the selected GPT-4.1 Mini, voice and speech models, requires authentication, limits conversations to 180 seconds with one concurrent and ten daily, disables backup LLM and audio recording, and requests zero-day scheduled deletion. The existing phone agent was not changed. ElevenLabs rejected Zero Retention Mode for the selected LLM, so ZRM remains disabled under the existing fictional-only development policy; this does not satisfy real-customer requirements. Hosting environment wiring, remaining privacy/billing checks and end-to-end website/voice acceptance are unverified.

## Development calendar defaults — owner verification pending

The owner requested using the suggested fictional calendar automatically without entering settings in the operations workspace. The development seed initializes a missing `business_schedules` row for the deterministic development business with booking enabled, America/New_York, ZIP 10001, Monday–Friday 09:00–17:00, 60-minute visits, 120-minute booking/change notice, a 30-day horizon and one Test Team. Initialization validates the existing schema, locks the business, and inserts calendar/audit together. Existing calendars and their versions are preserved; other businesses get no defaults and no appointments are seeded. No schema migration is added. During the owner's subsequent explicit business-content request, the scoped development seed created and enabled this calendar in the configured Neon development database. Automated tests and hosted voice/booking acceptance remain pending. Commands and checks are in `docs/development-calendar-defaults.md`.

## Applied development business content — voice acceptance pending

The owner explicitly requested adding approved FAQs and needed business content to the database. The scoped seed inserted 25 additional FAQs, leaving 28 active seed FAQs in the configured Neon development business. It also created the missing enabled calendar, reused the existing receptionist profile, and excluded all phone-routing changes. Three new FAQ answers were then clarified through the audited, version-checked FAQ service to scope website account/history and browser-memory claims correctly. No customer accounts, service requests, appointments or conversations were fabricated. Unknown prices, fees, warranties, financing, supported equipment and response promises remain staff-only questions. Edited/inactive FAQs are preserved on reseed, and known legacy fallback promises are replaced only when exact default text remains. No migrations, automated checks or live voice sessions ran. Render's effective database branch and complete voice behavior still require owner acceptance. See `docs/development-business-content.md`.

## Customer UI/account draft — owner verification pending

The source includes a navy/blue customer homepage and prominent Line AI booking entry, plus signup/login before booking, scoped server-side proxies, fictional-only account/session services, owned appointment history and migration `20261025_0010_customer_access`. This remains an unfinished, unverified development draft. The migration and verification have not run; email verification, recovery, MFA, tenant onboarding and production account readiness remain incomplete. All existing privacy/development gates remain required. The owner directed publication without verification; publication does not establish runtime, security or deployment success. See ignored `docs/_local/chatgpt-handoff.md` for the continuation state and checks.

## Customer chat — implementation unverified

On October 25, 2026 the owner reported voice working and explicitly said appointment booking had not been tested. This is an owner report, not independent end-to-end verification. The customer booking UI now defaults to silent Chat, with a separate Voice choice and typed messages available in both. The pinned SDK receives `textOnly` for Chat, skips microphone permission and uses the existing private WebRTC grant. The browser agent's saved configuration now allows the `text_only` override, retains a voice default/private authentication/eight tools, and includes channel-specific confirmation guidance; its saved settings were read back without starting a live conversation.

Migration `20261025_0011_browser_text_sessions` adds explicit VOICE/TEXT mode and nullable microphone consent with consistency constraints. Existing sessions retain VOICE and existing consent; TEXT is browser-only and records no microphone consent. The shared API continues to require disclosure and fictional-data acknowledgement for both modes. Both reuse the existing approved FAQs, internal calendar, quotas, hazard handling, transcript readback gates and persisted outcomes. The legacy `spoken_confirmation` name remains compatible with typed transcript confirmation. The migration refuses downgrade while text sessions exist.

No migration, tests, builds, linters, type checks or live sessions ran for this feature. Updated schema/backend must precede the frontend deployment. Chat and appointment booking remain unverified; owner commands and manual acceptance are in `docs/customer-chat.md`. No new environment variables or OpenAI key are required. Production identity/privacy and real-customer launch gates remain unresolved.
