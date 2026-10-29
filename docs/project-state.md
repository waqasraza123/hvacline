# Project State

## Main publication authorized; release handoff completed — 2026-10-29

The owner requested finishing and publishing pending work to `main`, superseding
the earlier feature-branch-only publication scope. The active Telnyx SIP and
gated homepage phone CTA commits extend published main `d85ff6d`. Static source
review and the release handoff are complete; implementation/runtime remain
**UNVERIFIED**. No execution checks, migrations, services, provider configuration
or deployment commands ran. The older dirty original checkout is preserved.

`docs/telnyx-sip-setup.md` now records the release delta from owner-reported Render
source `54e6603`, schema/dependency prerequisites, Blueprint seed/default-provider
differences, exact owner commands and live acceptance. Publication does not
activate Telnyx or the public phone CTA. Hosted revision/configuration, migration
`0017`, agent updates and real-call acceptance remain pending.

## Homepage phone CTA — disabled, owner verification pending — 2026-10-29

The existing hero now includes an optional phone-icon booking call panel. A
server-rendered configuration parser formats the configured US E.164 number and
derives its `tel:` link. Web-only `HOMEPAGE_PHONE_NUMBER_E164` holds the number;
`TELNYX_INBOUND_CALLING_VERIFIED` defaults false and suppresses the public panel
until the owner records real-call acceptance. Existing hero layout, typography,
booking/chat paths and Telnyx backend changes are preserved. The web environment
example carries the owner-supplied public business number, not application code.

Source, focused release-gate specifications and responsive acceptance remain
**UNVERIFIED**. No tests, builds, linters, type checks, services, provider calls or
deployments ran. Exact owner commands and desktop/mobile/focus checks:
`docs/telnyx-sip-setup.md`, homepage CTA section. Public activation requires live
Telnyx acceptance, explicit verified configuration and an authorized frontend
rebuild/deployment; no environment value was enabled by this implementation.

## Alternative Telnyx inbound SIP — implementation UNVERIFIED — 2026-10-29

Feature branch `feat/telnyx-sip-inbound` adds explicit disabled/Twilio/Telnyx SIP
selection behind the existing telephone enable flag. Telnyx routes directly to
the existing private ElevenLabs phone agent, with a separate authenticated,
size-bounded initiation endpoint, backend-owned active-number routing and existing
policy quotas. Call and conversation identity persist together in existing call
metadata; policy/advisory locks protect duplicate/quota decisions. Shared consent,
FAQ/intake/HVAC booking tools and HMAC/replay-protected post-call finalization are
reused. SIP handoff records backend authorization/audit and uses callback fallback;
native SIP REFER remains disabled without verified result handling. No Twilio
client/register-call, Telnyx REST dependency, new schema or frontend feature is
needed for this path. Historical Twilio finalization fingerprints are preserved.

Source and added unit/database specifications remain **UNVERIFIED**. Source
formatting only; no tests, builds, linters, type checks, migrations, services,
provider calls, purchases, account changes or deployments ran. Exact API settings,
Telnyx FQDN/ElevenLabs import and webhook setup, transfer design, owner commands
and live acceptance: `docs/telnyx-sip-setup.md`. Provider-dashboard setup and real
carrier acceptance remain **UNVERIFIED**. Existing development identity/privacy,
business confirmation and production onboarding gates remain; completed bookings
must survive disconnect and be checked in Operations during owner acceptance.

## Homepage guest chat — owner-approved behavior, acceptance pending — 2026-10-29

Owner selected one live text message/reply on the homepage, a dismissible sign-in popup on the second attempt, a 30-day browser allowance and same-tab continuation through existing authentication/MFA. The existing browser Line agent is reused with a guest-mode variable; a protected server-side bridge permits only approved FAQ lookup. Source adds atomic guest quotas separate from signed-in application quotas, no application transcript/customer/booking persistence, and bounded browser-only context handoff outside confirmation transcripts.

Implementation/runtime are **UNVERIFIED**. Source formatting only; no tests, builds, linters, type checks, installs, migrations, services, hosted agent edits or deployments ran for this feature. Migration `20261029_0017` and pinned `websockets==17.3` are new; feature defaults off. Owner setup, exact commands and manual acceptance: `docs/homepage-chat.md`. Apply schema/dependencies and shared agent guest-mode/completion-event settings before enabling API `HOMEPAGE_CHAT_ENABLED`; the database was previously confirmed at `0016`, not `0017`.

## Owner decision: remove demo wording and fictional-data requirements — 2026-10-29

The owner explicitly requested neutral product wording and removal of fictional-data requirements. This supersedes earlier synthetic-only instructions in this memory. Source removes the signup and browser/phone/WhatsApp consent requirements and demo/early-access presentation; AI/provider disclosure, microphone consent, authentication/MFA and readback confirmations remain required. New migration `20261029_0016` permits empty historical synthetic-acknowledgement timestamps without changing existing evidence. No runtime environment or development-actor configuration was changed.

On October 29, the owner explicitly authorized applying migrations. Alembic successfully upgraded the configured development Neon database from `20261028_0015` to `20261029_0016`; the subsequent revision readback reported `20261029_0016 (head)`. No tests, builds, linters, type checks, seeds, provider changes or deployments ran. Application/runtime acceptance remains **UNVERIFIED**; hosted agent prompts/tools and existing stored greeting/FAQs need separate owner updates. Exact owner commands/manual acceptance: `docs/customer-data-requirements.md`.

## Customer appointments dashboard refresh — owner acceptance pending

My appointments now has a responsive next-confirmed-visit card, date/time/status cards, Upcoming/History/All filters and stored-count/booking-limit sidebar. Display distinguishes holds, expired/cancelled records, past appointments and current scheduled windows without implying service completion. Existing details/rescheduling modal and APIs remain authoritative; no backend/schema/environment/dependency change. Source formatting and unexecuted presentation/expiry/timezone specifications only; runtime **UNVERIFIED**. Exact owner commands/manual checks: `docs/customer-appointments-design.md`.

## Customer memory dashboard refresh — owner acceptance pending

The Memory tab now has responsive orange/charcoal status/count/retention cards, saved details with source/update/expiry, a selected-detail consent editor, dated authorized-summary suggestions, WhatsApp pairing and privacy controls. Suggestions go through review before save; destructive actions use native confirmation dialogs. Booking limits stay on booking/history tabs. Existing backend options/revisions/APIs remain authoritative; no backend/schema/environment/dependency change. Source formatting only; no verification or deployments ran. Implementation/runtime **UNVERIFIED**; exact owner commands and manual checks: `docs/customer-memory.md`.

## Customer MFA QR and page refresh — owner acceptance pending

The owner reports that the QR code works. This is owner-reported scanning acceptance; Codex did not run a scan, and full MFA/recovery/security verification remains pending.

The customer MFA page adds browser-local SVG QR enrollment using the existing backend provisioning URI, with a manual-key fallback. Pinned `qrcode.react@4.2.0` and lockfile metadata added without installation; URI/key/TOTP consistency is validated before rendering. Orange/charcoal responsive layout now covers setup, verification, recovery and backup codes. No backend/schema/environment change. Source and focused specifications remain **UNVERIFIED**; no installs, tests, builds, linters, type checks, services, scans or deployments ran. Exact owner commands and desktop/mobile/privacy/scan acceptance: `docs/customer-mfa.md`.

## Render and Vercel deployment failures — owner acceptance pending

The subsequent owner-supplied Render traceback reaches router creation and fails because memory's `{key}` path parameter collides with the customer portal dependency argument `key`, an optional header. Renamed that internal argument to `portal_key`, preserving the header alias, routes and access gates. Added an unexecuted mocked-database regression specification for full app/router registration and OpenAPI parameter binding. No migrations, environment changes or frontend changes are required for this repair. Owner command: `python -m pytest tests/test_api.py`; manual API startup, readiness and authenticated/unauthorized memory-deletion checks remain pending. No verification commands ran.

Owner-supplied October 28 logs show Render completed migrations through `20261028_0015` but API startup rejected the enabled portal without `CUSTOMER_MFA_ENCRYPTION_KEY`. The Blueprint now declares a secret placeholder; the owner must set a stable dedicated Fernet key on the API and redeploy. Vercel rejected memory parsing because the `Fact` guard narrowed away saved provenance fields. Saved facts now validate all fields directly from an unknown record, preserving runtime validation. No application/schema/MFA-policy changes. No tests, builds, linters, type checks, migrations, services or hosting changes ran; repairs remain **UNVERIFIED**. Exact owner commands and deployment/manual checks: `docs/environment-handoff.md` and `docs/customer-mfa.md`.

## Publication authorized — UNVERIFIED

The owner requested committing and pushing all current work to `main`: direct inbound WhatsApp voice, optional customer memory, customer-only authenticator MFA and the icon-only GitHub header link. Publication includes forward migrations `0013`–`0015`; migration execution, provider configuration, MFA key setup and runtime acceptance remain owner-managed. Existing remote header changes must be retained. CI/Render skip markers accompany publication; no tests, builds, linters, formatters, type checks, migrations, services or provider calls were authorized or run. Exact owner checks remain in `docs/whatsapp-inbound-calling.md`, `docs/customer-memory.md` and `docs/customer-mfa.md`; header acceptance requires `npm run verify:web` and desktop/mobile link/focus checks.

## Mandatory customer MFA — UNVERIFIED

Owner narrowed scope to customer accounts only; Operations/staff access is unchanged. Local branch `feat/mandatory-authenticator-mfa` adds password-bound, short-lived enrollment/verification challenges, required authenticator proof before any customer session, encrypted tenant/account-bound TOTP seeds, replay protection, persistent lockouts and one-use recovery codes requiring verified replacement. The MFA patterns were adapted from the owner's `stealth-trails` repository to Python/FastAPI/Neon. No read-only pre-MFA or email/password fallback is provided.

Forward migration `20261028_0015` follows pending memory `0014`, adds three MFA tables and session evidence, revokes existing customer sessions and requires MFA-authenticated reapproval of WhatsApp memory links. API-only `CUSTOMER_MFA_ENCRYPTION_KEY` is required when the customer portal is enabled; retain a stable protected backup. Existing development/fictional-data gates and customer booking/Chat/Voice workflows remain. Recovery/reset invalidates earlier session and memory-link versions.

Source and focused specifications are **UNVERIFIED**; no tests, formatters, checks, migrations, services, provider calls, installs, commits, pushes or deployments ran for MFA. Configuration, reference provenance, exact owner commands and new/existing-customer/recovery acceptance: `docs/customer-mfa.md`. Production onboarding, email verification, password recovery, key rotation and managed lost-factor recovery remain outside scope. Prior memory work and unrelated homepage/style changes are preserved.

## Account-scoped customer memory — UNVERIFIED

Local branch `feat/customer-memory`, based on WhatsApp foundation `7ece835`, adds optional Neon memory scoped to verified customer account and agency. New forward migration `20261028_0014` adds policy, categorical fact, authorized-intake summary, WhatsApp identity and pairing tables plus verified account provenance on WhatsApp bindings. Customer controls support opt-in, corrections, forgetting, erasure and unlinking. No contact matching authorizes memory. WhatsApp requires approval from the existing signed-in browser account; opaque caller digests/BSUIDs are not phone numbers.

Memory references existing immutable confirmed intakes without transcript copies. Suggestions use customer-word evidence and facts require explicit selection/readback consent; no LLM extraction or free-text storage. Context is bounded; service/appointment references are read from owned authoritative records and never substitute for live availability/pricing/status. Consent revisions/erasure cutoffs prevent stale writes and old-history regeneration. Configurable expiry hides stale content immediately; a separate bounded owner-scheduled purge physically removes optional records. Booking, Calendar and notification transactions are unchanged; memory is independent of booking success.

Implementation and all test specifications remain **UNVERIFIED**. No tests, builds, linters, formatters, type checks, migrations, seeds, services, provider calls, installs, commits, pushes or deployments ran. Exact tools, environment names, owner commands, retention scheduling and cross-session acceptance: `docs/customer-memory.md`. Existing development/fictional-data identity/privacy gates remain. Unrelated header/title/style edits are preserved.


## Direct inbound WhatsApp voice — UNVERIFIED

Feature branch `feat/whatsapp-inbound-calling` implements direct ElevenLabs WhatsApp initialization, call-scoped authenticated tools and signed post-call finalization without Twilio credentials/IDs. The new forward migration `20261028_0013` adds agency-owned WhatsApp bindings and a WHATSAPP conversation channel. Initialization uses the documented empty call_sid, configured agent/Meta-number allowlist and opaque caller digest; consent creates the actual session. FAQs, confirmed intake/lead persistence, booking holds/readbacks, Google Calendar, notifications, audit and Operations reuse existing services. Callback-only contacts require a separate spoken readback; native transfer is not used. No messaging, outbound calls, voice notes or campaigns are implemented.

Existing development/fictional-data, privacy, 180-second and quota gates remain. One configured agency/agent/number per deployment; broader onboarding and real-customer production identity remain deferred. Focused adapter/API/database specifications are added but unexecuted. No tests, builds, lint/checks, type checks, migrations, provider calls, installs or deployment ran; source formatting only. Setup, environment names, exact owner commands and manual acceptance: `docs/whatsapp-inbound-calling.md`. Migration, provider setup and runtime remain **UNVERIFIED**.


## Customer palette — owner verification pending

The owner selected orange/charcoal across the homepage, login/signup and customer booking experience, using light backgrounds and dark feature panels. Shared customer theme variables now cover branding, voice graphics, controls, chat, booking progress/history, quotas, countdown and details dialogs; shared internal components retain prior colors through fallbacks. The site-wide favicon also uses orange/charcoal. Status colors remain semantic. No backend, schema or provider change. Source formatting only; implementation and browser/contrast acceptance remain unverified. Exact owner commands and manual checks: `docs/customer-color-refresh.md`.

## Customer booking quotas — owner verification pending

Deployment variable names, locations and values are consolidated in `docs/environment-handoff.md`; it contains no credential values. The latest customer limits need only the two API quota variables, defaulting to 1, while the frontend reads their effective values.

The account-scoped booking flow defaults to one active appointment and one successful date/time change per service-request booking history, configurable through API `CUSTOMER_MAX_ACTIVE_APPOINTMENTS` and `CUSTOMER_MAX_BOOKING_CHANGES`. The scheduling lock protects reservation/confirmation checks and both reschedule phases; completed retries bypass quota consumption. Active holds count, ended/cancelled bookings free capacity, and replacement IDs retain prior change usage through immutable existing reschedule audits. Authenticated API counts populate both booking/history pages and the details modal. No new migration or provider configuration change is included; phone/staff flows without verified customer-account linkage retain their existing behavior. Source formatting and unexecuted regression specifications only; runtime remains unverified. Exact setup, owner commands and acceptance: `docs/customer-booking-limits.md`.

## Booking details and three-minute timer — owner verification pending

The customer booking receipt and history now open an owned-booking details modal. Date/time edits reuse the existing reschedule transaction, Google conflict/ownership checks, notice rules and notification outbox, with explicit confirmation and retained browser-memory retry keys after uncertain responses. The customer proxy exposes only scoped details/availability/reschedule routes. Contact/service snapshots remain displayed reference data. The owner retained the 180-second cap; a prominent countdown uses the server authorization expiry, warns in the final minute and explains local timer expiry. Interrupted ten-minute changes and the unexecuted migration were discarded; no new migration or provider configuration change is included. Source formatting and unexecuted regression specifications only; runtime remains unverified. Exact owner commands, deployment order and acceptance: `docs/booking-details-and-timer.md`.

## Node 24 hosting compatibility — owner verification pending

The owner supplied a Vercel failure rejecting the root Node engine `>=26 <27` before the Python job build. Root/web manifests, npm lockfile engine metadata, `.nvmrc` and web CI now select Node 24 (`24.x` engines), matching Vercel's supported version. No dependency versions changed. Source/build compatibility and deployment remain unverified; no installs, tests, builds, linters or type checks ran. Owner commands and deployment checks: `docs/vercel-booking-jobs.md`.

## Vercel booking job runner — owner verification pending

The owner declined paid Render workers and selected Vercel. A separate root-level FastAPI Vercel project now exposes a bearer-protected POST batch runner, using the same database/integration configuration and a dedicated `BOOKING_JOBS_SECRET`. The frontend remains rooted at `apps/web`; the API remains on Render. Shared PostgreSQL transaction advisory locking coordinates function invocations and the retained standalone worker. Batches interleave notifications/calendar work, use a cooperative 20-second deadline with bounded database/provider waits, and preserve durable retries and provider idempotency. No new migration is required. Vercel Hobby cron is daily, so frequent invocations require an external scheduler. Source implementation and regression specifications are unverified; no tests, builds, linters, type checks, services or deployments ran. Exact setup, commands and manual checks: `docs/vercel-booking-jobs.md`.

## Migration settings repair — owner verification pending

The owner supplied a Render build failure after package installation: Alembic loaded enabled Google Calendar runtime settings with incomplete OAuth/encryption configuration. Alembic now uses `DatabaseConnectionSettings`, retaining PostgreSQL URL, test-isolation and production SSL validation without loading integration settings. API/worker retain strict enabled-integration validation through `DatabaseSettings`. Incomplete integrations must remain disabled in the service environment until configured. Regression specifications and deployment instructions were added; no tests, builds, linters, type checks or migrations ran for this repair. Exact owner commands and manual acceptance are in `docs/calendar-and-booking-messages.md`.

## Google Calendar and booking messages — implementation unverified

The October 27 implementation adds per-team Google OAuth/PKCE with encrypted offline credentials and browser-bound single-use state, live paginated conflict checks, deterministic event writes with durable reservation bindings, and worker reconciliation/owned-event cleanup. External edits/overlaps enter staff attention; they do not silently rewrite or cancel local bookings. Google has no atomic insert-if-free, so concurrent external writers remain a reconciled risk.

Confirmation/cancellation/reschedule emails and reminders use a transactional outbox with frozen payloads, bounded idempotent Resend retries, conservative unknown-outcome handling and signed delivery receipts. Missing confirmed email addresses are skipped; SMS is not implemented. Operations exposes connection, sync and delivery status. Migration `20261027_0012`, Google/Resend settings and scheduled job execution (Vercel function or persistent worker) are required before use. Features default off and retain development-only gates. No tests, builds, linters, type checks, migrations, services, provider calls or deployment ran. Exact owner setup, commands and acceptance: `docs/calendar-and-booking-messages.md`.

## Browser booking progress — owner verification pending

The owner reports successful full appointment booking as of October 27, 2026; this is owner evidence, not an independently repeated acceptance run. A subsequent frontend slice adds tool-driven booking stages, pending operations, confirmation guidance, hold countdown/expiry, stage-local failures and persistent CONFIRMED receipts to customer/operator browser conversations and the on-screen fallback. Activity labels respect connection and mute state. Unknown write results preserve retry context; the fallback can recheck an earlier confirmation after the displayed hold deadline. No backend API, migration or provider configuration changed. Regression specifications were added; no tests or hosted deployment ran. Exact owner commands and manual acceptance are in `docs/booking-progress.md`; implementation/runtime remain unverified.

## Product and scope

HVACLine AI is an AI phone receptionist and appointment-booking product for U.S. HVAC service businesses only. The October 24, 2026 owner mission supersedes the insurance roadmap, frontend freeze, and earlier restrictions against running the named verification commands. Development remains synthetic-only; live carrier success and production readiness must not be claimed without evidence.

## Architecture

GitHub redirected the authorized feature-branch push to `waqasraza123/hvacline` on October 25, 2026; the former `insurance-operations-ai` URL still redirected successfully at that time. Render's repository binding and deployed revision have not been verified.

Next.js/TypeScript web, FastAPI/Python 3.13 backend, separate worker, SQLAlchemy 2/psycopg 3/Alembic, and Neon PostgreSQL only. Keep established Python/workspace/CLI names, agency ownership keys, and migration history for compatibility. Public receptionist categories are exposed as `supported_service_categories`, mapped to the legacy storage column.

Existing signed Twilio ingress, ElevenLabs register-call voice connection, secret-authenticated tools, HMAC post-call verification, consent/readback receipts, approved FAQs, leads, callbacks, transfer commands, quotas, and audits are reused. No raw audio is stored. Transcript/customer/lead finalization stays in the signed post-call flow.

## HVAC implementation

Forward migration `20261024_0009` adds business schedules, confirmed HVAC service requests, and appointments. Scheduling uses per-business ZIP codes, IANA timezone, hours, team calendars/time off, duration, notice and horizon. Mutations lock the tenant schedule row; payload-bound booking keys prevent conflicting retries; appointments have a composite tenant/request foreign key. Reservations expire after five minutes. Confirmation, cancellation, and atomic rescheduling persist before returning success.

Authenticated phone tools verify active session/call ownership and expiry. HVAC service intake requires the existing contact-readback receipt and explicit structured confirmation. Hazardous requests enter human attention and cannot self-book. The operations projection excludes transcripts and shows real stored requests, bookings, calls and open handoffs. Existing receptionist and knowledge editors are reused inside the protected workspace, forwarding the in-memory admin token in headers. `/operations` uses existing development identity and hosted-sandbox token gates; this is not production login.

The opt-in Google Calendar connection/sync and booking-email slice is implemented but unverified; see the current section above. Unconnected teams retain operator-maintained internal scheduling.

## Verification during this execution

GitHub CI at implementation commit `0cbbe8f` passed both jobs: 83 Python tests, 24 web tests, Ruff format/lint, mypy, the production web build, migration upgrade/current/no-drift checks at `20261024_0009`, and worker readiness. Database tests used CI's isolated PostgreSQL 17 service. No shared or production Neon database was touched. All 177 tracked branch files were compared against local source and matched before the final reservation-notice fix; that fix also passed CI.

The local host cannot complete Next build because its OS memory-statistics interface is unavailable (`uv_resident_set_memory` ENOENT); the GitHub production build independently passed. No live carrier call, provider dashboard/privacy validation, or Google authorization has been verified. See `docs/verification.md` for evidence.

## Remaining launch blockers

- Live synthetic Twilio → ElevenLabs → backend → database → dashboard call and transfer validation.
- Production identity, roles, account onboarding, tenant/provider credential and agent provisioning.
- Owner acceptance of Google authorization, encrypted credentials, external conflict recovery and worker reconciliation.
- Caller verification before existing-customer lookup or telephone appointment changes.
- Owner acceptance of booking email/reminder delivery; callback completion workflows and urgent alert delivery remain incomplete.
- Billing, detailed usage/cost tracking, production limits, observability/recovery, and retention automation.
- Production deployment and acceptance tests. Current development-only gates remain intentional.

## Guidance

Use README, `docs/hvacline-architecture.md`, and `docs/hvacline-live-validation.md`. Insurance continuation documents are archived as history, not current requirements. Update this note only with verified implementation and results; never store secrets, caller content, or credentials.

## Homepage branding — owner verification pending

The public homepage uses a navy/electric-blue visual system and introduces Line as the AI voice receptionist for HVAC businesses. The October 27 copy update leads with missed-call/job loss, explains live availability and explicit caller confirmation, and uses demo CTAs. Sections follow hero, three-step workflow, services, FAQ and final CTA; metadata targets the same business-owner audience. No performance metrics are asserted. Booking/sign-in links target the customer `/book`, `/login` and `/signup` routes; `/operations` remains a separately protected administrator workspace. The customer routes and draft authentication remain development-only and owner-unverified, not production identity. No tests, builds, linters, type checks, services, browser previews or live checks ran. Full copy, ranked hero options and owner checks are in `docs/homepage-copy.md`; visual-system handoff is in `docs/homepage-branding.md`.

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

The source includes a navy/blue customer homepage and prominent Line AI booking entry, plus signup/login before booking, scoped server-side proxies, fictional-only account/session services, owned appointment history and migration `20261025_0010_customer_access`. This remains an unfinished, unverified development draft. Mandatory customer MFA and backup-code replacement are now implemented locally but unverified; see `docs/customer-mfa.md`. Email verification, password recovery, tenant onboarding and production account readiness remain incomplete. All existing privacy/development gates remain required. The owner directed earlier publication without verification; publication does not establish runtime, security or deployment success. See ignored `docs/_local/chatgpt-handoff.md` for the continuation state and checks.

## Customer chat — implementation unverified

On October 25, 2026 the owner reported voice working and explicitly said appointment booking had not been tested. This is an owner report, not independent end-to-end verification. The customer booking UI now defaults to silent Chat, with a separate Voice choice and typed messages available in both. The pinned SDK receives `textOnly` for Chat and skips microphone permission. Chat now uses a private signed WebSocket grant; Voice retains its WebRTC grant. The browser agent's saved configuration allows the `text_only` override, retains a voice default/private authentication/eight tools, and includes channel-specific confirmation guidance; its saved settings were read back without starting a live conversation.

Migration `20261025_0011_browser_text_sessions` adds explicit VOICE/TEXT mode and nullable microphone consent with consistency constraints. Existing sessions retain VOICE and existing consent; TEXT is browser-only and records no microphone consent. The shared API continues to require disclosure and fictional-data acknowledgement for both modes. Both reuse the existing approved FAQs, internal calendar, quotas, hazard handling, transcript readback gates and persisted outcomes. The legacy `spoken_confirmation` name remains compatible with typed transcript confirmation. The migration refuses downgrade while text sessions exist.

No migration, tests, builds, linters, type checks or live sessions ran for this feature. Updated schema/backend must precede the frontend deployment. Chat and appointment booking remain unverified; owner commands and manual acceptance are in `docs/customer-chat.md`. No new environment variables or OpenAI key are required. Production identity/privacy and real-customer launch gates remain unresolved.

The owner subsequently reported Chat disconnecting just after startup and interrupting typing. Static review found Chat forced onto the voice transport, missing typing-activity signals and a composer removed outside the active phase. The repair selects signed WebSocket grants for TEXT, validates mode/transport at both frontend boundaries, sends typing activity, keeps unsent messages editable during failure/retry and avoids resetting parent activity on each phase transition. Signed credentials never enter stored provider metadata; an external reference is saved only when supplied by the provider. No new migration/provider configuration was added. A definitive provider close reason and runtime success have not been independently verified. Owner deployment and focused/manual checks remain pending.

The owner then supplied `CONVERSATION_ALREADY_ACTIVE` while Send stayed disabled. Recovery now retains known sessions for cleanup before retry, exposes an explicit release action only for the current actor's own browser session, and supplies a bounded retry delay for conflicts. The existing end route enforces ownership and accepts repeated failed/interrupted cleanup without changing the first failure reason. Late provider grants cannot revive released/expired sessions. Saved requests/bookings and existing quotas remain intact; other users' identifiers and phone-session identifiers are excluded from recovery details. Closing other tabs is still necessary to close their provider connections. No migration, tests, live sessions or database fixes ran for this repair; owner commands/manual checks are in `docs/customer-chat.md`.

The owner's later transcript demonstrates a connected multi-turn Chat, followed by an intake save failure after a standalone confirmation and then a shortened retry readback. Source review confirmed that `confirm` was excluded from accepted replies and that the full exact readback is required. The allowlist now includes explicit standalone confirm variants while retaining the complete-readback gate and rejection of corrections/refusals. Intake validation rejection returns the exact prepared readback with structured retry guidance. Matching browser-agent recovery guidance was saved and its configuration read back. Appointment confirmation remains separate; no booking success, tests or live sessions have been verified for this repair. No new migration or environment changes are required.
