# AI Lead Recovery

Source implementation; **UNVERIFIED**. No tests, builds, linters, formatters,
type checks, migrations, browser checks, services, model requests, messages,
calls, hosted settings, deployments, commits or pushes were executed.

## Product experience

The homepage places recovery immediately after the hero, with an interactive
preview and **Try Live Demo** / **Set Up AI Recovery** links. `/lead-recovery`
opens the recovery workspace in Demo Mode; `/lead-recovery?setup=1` opens the
existing administrator connection gate. Shared navigation, the Operations
sidebar and the first overview feature card expose the same feature.

Demo Mode uses a deterministic client-only cohort of 24 fictional opportunities:
eight recovered, six scheduled, five awaiting responses, three needing review
and two closed. Records, conversations, activity and booking receipts are marked
**DEMO DATA**. Initial conversion is 8/24 (33.3%); the initial fictional estimate
is eight jobs at $650 ($5,200). The editable job value changes only that estimate.
There is no actual revenue calculation in Live Mode.

Select a scheduled case, start the simulated follow-up, simulate YES, select a
fictional slot and explicitly confirm a simulated booking. The cohort, activity
and metrics update in local React state. STOP closes the fictional case. Used
slots cannot be selected twice; review/closed cases cannot be contacted. Reset
Demo restores all records, slots, activity and the fictional job value. State is
ephemeral and never written to storage, customer tables or recovery jobs.
Homepage and dashboard simulations are independent sessions; dashboard overview
and recovery share their state while navigating within that workspace.

Demo recovery components make no backend or provider requests. Other pre-existing
homepage features retain their own behavior. A database outage or missing AI key
does not change the recovery simulation. Live Mode never substitutes demo data
for missing or failed live responses.
The dedicated recovery route also supports an unset NEXT_PUBLIC_API_BASE_URL:
the simulation remains available and Live setup explains the missing backend
origin instead of inventing an endpoint or attempting customer API fallback.

## Implemented phases and boundaries

1. Migration0026 adds business-owned policies, cases, attempts, explicit contact
   permissions, AI connections and provider-event deduplication. Source/request
   identities are unique; composite foreign keys protect request, lead,
   appointment, attempt and staff membership ownership. PostgreSQL triggers
   enforce version increments and terminal case/attempt transitions.
2. New persisted confirmed HVAC requests create prospective cases. Browser end,
   normalized call events and signed phone post-call reconciliation update the
   existing request's case. Unknown callers and unconfirmed transcript drafts do
   not manufacture customers. There is no historical scan or enrollment job.
   An immutable policy capture watermark excludes requests confirmed before
   installation even if an old signed terminal webhook arrives later. The
   migration creates disabled policy defaults for existing agencies only;
   agencies created later lazily get a watermark at their creation time.
   Current routine requests require configured service-area scheduling; hazards,
   high urgency, staff handoffs, unsupported requests and bookings block contact.
   Terminal-event delay is at least ten minutes; request/booking activity delay
   is at least thirty minutes. New reservation activity postpones recovery.
3. The existing worker and protected booking-job runner collect bounded recovery
   work. Schedule/case/attempt locks, immutable attempt keys, a committed STARTED
   checkpoint before provider I/O, and final authorization checks protect writes.
   A second transaction holds the existing schedule/case locks through sending;
   process loss leaves STARTED for UNKNOWN review. Unknown or queued outcomes
   cannot be manually retried. No detached task or second scheduler is added.
   The policy caps two total attempt records in seven days, at least24 hours
   apart, within09:00–18:00 in the configured agency timezone. Administrators can
   narrow these bounds. Cancelled records conservatively consume attempt budget.
4. Existing confirmed-appointment notification entrypoints stop recovery for
   internal, Google and GHL booking paths without replacing those booking engines.
   Independent bookings close cases as BOOKED_INDEPENDENTLY, without increasing
   recovered counts. The trusted domain attribution boundary requires a sent
   attempt, provider reference and confirmed appointment for the same request;
   it cancels remaining scheduled attempts and audits only resource/status data.
   **No live customer/voice continuation currently supplies this attribution.**
5. Protected case pages, counts, settings, versioned staff actions, permission
   evidence and encrypted AI configuration back the Live UI. Filters, pagination,
   loading/errors, setup guidance and empty/provider-unavailable states are real.
   Conversion is attributed recovered cases divided by all agency recovery cases;
   recoverable excludes RECOVERED, CLOSED and SUPPRESSED. Live revenue is omitted.

## Delivery capability: unavailable, activation blocked

**Automated SMS and AI recovery calling are not operational in this revision.**
All outbound defaults remain off. The existing SMS adapter is Telnyx Verify,
which cannot deliver arbitrary service messages. The public outbound ElevenLabs
demo has a fixed demo agent/security contract; it is not a recovery caller.
Neither integration is repurposed or activated here.

`RecoveryDeliveryProvider` supplies the provider-neutral send boundary and
`UnavailableRecoveryProvider` is the only runtime delivery implementation.
Settings explicitly report both channels unavailable; saving enabled=true is
rejected. Setting RECOVERY_ENABLED alone cannot make a live send possible.
The prompt contract describes disclosure, existing details, actual availability,
explicit selection and existing confirmation tools, but is not a hosted agent.

A future concrete adapter must authenticate provider callbacks against exact raw
bodies and bind the provider account/destination to the owned attempt. The trusted
`apply_verified_event` boundary deduplicates receipts/replies and checks reply
senders; it is deliberately not exposed as an unsigned webhook. Receipts never
imply engagement. STOP suppresses all automated recovery for the same confirmed
agency destination, including other requests. YES pauses automation and requests
existing staff callback continuation when a lead exists; otherwise the case is
actionable in recovery. It does not authorize an automatic AI callback or create
a booking. Early receipts before send-commit and unknown-create reconciliation
need a concrete adapter's durable ingress/reconciliation design before activation.

A dedicated recovery voice agent/tool binding, verified signed callbacks,
telephony restrictions and jurisdictional calling policies, and a supported SMS
messaging account remain implementation/configuration dependencies. These are
not simulated as successful live integrations. The existing public demo quotas
and settings are unchanged. No hosted agent or provider setting was changed.

## AI model settings and security

**Supported:** OpenAI and explicitly allowlisted OpenAI-compatible public HTTPS
endpoints, using non-streaming text Chat Completions with `messages`, `max_tokens`
and a text `choices[0].message.content` result. A small authenticated connection
test validates this response contract; the UI never marks saving as a successful
test. Explicit test/draft actions can incur the configured provider's charges.

This revision uses custom models for **staff-reviewed text drafts only**. The
fixed prompt receives no customer phone, address, name or transcript. It has no
tools, scheduling authority, automatic sending, microphone, speech synthesis or
telephony capability. Reasoning-only models, models rejecting max_tokens, audio,
tool calls and non-compatible response formats fail visibly. A connection test
does not prove voice, tool or booking compatibility. No provider fallback occurs.
Existing ElevenLabs browser/inbound voice remains separately configured; custom
models cannot replace it or power a live recovery call through these settings.

The existing administrator/development actor is reused, plus an unconditional
administrator-token check even when DEMO_SANDBOX_ENABLED=false. Production actor
onboarding remains an existing platform limitation; these APIs do not add a new
production identity mechanism. All reads and writes scope agency IDs from the
authenticated actor, not request-supplied tenant IDs.

API keys stay in backend Fernet ciphertext bound to agency, provider and endpoint.
Only has_credential/status is returned; credentials and model output are excluded
from audits. Save/update resets connection status to UNTESTED; revoke destroys
the stored ciphertext. Tests/drafts checkpoint time/version first and enforce a
30-second cooldown. Configuration changes discard an in-flight old result.
No blind retry follows an unknown API outcome; refresh saved state first.

Custom endpoints require an exact operator allowlist origin, HTTPS, port443,
and the /v1 path. Userinfo, query strings, fragments, IP literals, private names,
nonpublic/mixed DNS answers, multicast and IPv6 transition addresses reject.
Each request resolves and validates all addresses, pins the selected public IP,
and verifies TLS against the original hostname. Redirects, proxy environment
variables and alternate fallback addresses are not followed. Responses are
bounded to64KiB and provider errors are sanitized. System DNS resolution follows
the host resolver's timeout; it is not a guaranteed hard request deadline.

Explicit recovery permission records include channel, LEAD_RECOVERY scope,
source, observation time, non-sensitive evidence reference and revocation.
Immutable audit events retain each administrative evidence change. Inbound calls,
MFA, saved numbers and general booking consent never imply this permission.
Destination matching uses agency-bound HMAC, not plaintext phone storage in a
second contact table. Suppression cannot be overridden through retry/resume or
this administrator grant form; a separate reviewed re-permission process would
be needed. Keep the encryption key stable: rotation changes both ciphertext
decryption and permission digests and needs a deliberate migration procedure.

## Migration and configuration

- Review `20261120_0026_lead_recovery.py`, following0025, before changing a database.
  It has not been applied. Both API and job runner must use the upgraded schema
  before this source is released, including when automation is off.
  It inserts disabled policy defaults and capture timestamps, never historical
  customer/case records. Recovery timezone must match existing Scheduling.
- `RECOVERY_ENABLED=false`: server kill switch; keep false.
- `RECOVERY_TOKEN_ENCRYPTION_KEY=`: dedicated Fernet key, shared privately by API
  and existing worker/job runtime. Required to save credentials or permission
  evidence. Never place it in NEXT_PUBLIC variables or notes.
- `RECOVERY_AI_ALLOWED_ORIGINS=[]`: JSON array of exact custom HTTPS origins,
  for example `["https://models.example.invalid"]`. OpenAI's fixed official
  endpoint needs no custom allowlist entry. Self-hosted services must have a
  deliberately allowed public HTTPS endpoint; private-network models are blocked.
- Enter each agency's provider/model/API key through protected settings. No new
  dependency or frontend environment variable is added. Existing database,
  administrator, web-origin, booking-job and voice settings remain authoritative.
- Downgrade refuses while recovery cases exist. Preserve recovery/audit history;
  this is a forward feature migration. Disposable database fixtures explicitly
  clear synthetic recovery cases before their existing destructive rebuild.

## Owner commands — list only, not executed

Use the existing Python3.13 and Node24 environments. Do not run database tests
until TEST_DATABASE_URL is privately confirmed to be an isolated disposable
database distinct from all runtime/direct databases: fixtures downgrade/rebuild
and truncate their target. No actual credentials belong in these commands.

```sh
python -m pytest tests/test_recovery.py tests/test_recovery_routes.py tests/test_booking_jobs.py tests/test_worker.py tests/test_settings.py
npm run test:web -- src/features/recovery/demo.test.ts
python -m ruff check apps/backend/src tests
python -m mypy apps/backend/src tests app.py
npm run lint:web
npm run typecheck:web
npm run build:web
APP_ENVIRONMENT=test python -m alembic upgrade head
APP_ENVIRONMENT=test python -m pytest tests/database/test_recovery.py tests/database/test_migrations.py tests/database/test_table_ownership.py tests/database/test_hvac_scheduling.py tests/database/test_booking_jobs.py tests/database/test_phone_receptionist_flow.py
```

After the disposable database review and explicit owner selection of the intended
development target, the forward migration command is:

```sh
APP_ENVIRONMENT=development python -m alembic upgrade head
```

No formatter was run; formatting and all static/runtime results remain unverified.

## Manual acceptance — fictional customers only

1. Signed out and with backend access unavailable, open the homepage recovery
   preview and `/lead-recovery`. Confirm DEMO MODE / DEMO DATA,24 opportunities,
   eight recovered, six scheduled, five awaiting,33.3% and the$5,200 estimate.
   Confirm no recovery API/provider requests occur in Demo Mode.
2. Select a scheduled fictional missed call; review its reference, routine
   details, fictional permission and reason. Start simulation, simulate YES,
   select and confirm a slot. Expect nine recovered,37.5%, updated fictional
   revenue/activity and a simulated receipt. Repeated confirmation cannot count
   twice. A second case cannot use the same slot. STOP closes without booking.
3. Filter all outcomes, inspect baseline recovered visits, try blocked review/
   closed cases, change the fictional job value and Reset Demo. Move between
   recovery and overview; the same dashboard simulation metrics should remain.
   Check keyboard/focus, narrow/mobile widths, table scrolling and both themes.
4. Switch to Live Mode: require administrator authentication. Incorrect/customer
   credentials must fail. With no setup, show the checklist and unavailable
   channels; no sample rows or fabricated live metrics may appear. Backend
   outage must produce an error, and returning to Demo must clear the token.
5. On a disposable agency, save a fictional provider configuration without a
   real key. Confirm encrypted database storage and credential-free API/audit
   projections. Mock provider success/failure, stale version, request timeout,
   cooldown, revoke and concurrent credential change. Unapproved/internal/
   metadata/redirect/mixed-DNS destinations must fail before credential delivery.
   Live model acceptance requires separate deliberate owner authorization; do
   not use real AI requests as part of default demo acceptance.
6. With mock delivery adapters only, create new persisted fictional routine
   requests. Replay normalized browser/phone terminal events; expect one case
   and original references. Confirm ten/thirty-minute delays, new hold activity,
   missing permission, opt-out, unsupported area, emergency/handoff and existing
   booking blocks. Exercise overlapping job ticks, stale writes, action-key
   replay, same-destination suppression, UNKNOWN no-retry, two-attempt/24-hour/
   seven-day bounds and local/DST windows.
7. Confirm through the existing booking engine; recovery must stop and existing
   notifications/calendar/GHL behavior must remain intact. Independent bookings
   close without recovery credit. A trusted attributable confirmed booking must
   link once and cancel remaining scheduled attempts. Receipt-only events must
   never increase recovered counts; verified YES requires staff continuation.

## Exact source manifest for this task

New backend paths (under `apps/backend/src/insurance_operations/`):

- `database/models/recovery.py`
- `recovery/__init__.py`
- `recovery/schemas.py`
- `recovery/domain.py`
- `recovery/providers.py`
- `recovery/jobs.py`
- `recovery/ai.py`
- `recovery/service.py`
- `recovery/routes.py`
- `recovery/events.py`

Modified backend paths (same prefix):

- `application.py`
- `settings.py`
- `booking_jobs.py`
- `database/models/__init__.py`
- `hvac/service.py`
- `conversations/service.py`
- `notifications/booking.py`
- `telephony/service.py`
- `telephony/phone_service.py`

New frontend paths (under `apps/web/src/`):

- `app/lead-recovery/page.tsx`
- `features/recovery/api.ts`
- `features/recovery/demo.ts`
- `features/recovery/demo.test.ts`
- `features/recovery/demo-panel.tsx`
- `features/recovery/homepage.tsx`
- `features/recovery/spotlight.tsx`
- `features/recovery/live.tsx`
- `features/recovery/ai-settings.tsx`
- `features/recovery/recovery.module.css`

Modified frontend paths (same prefix):

- `app/page.tsx`
- `components/header-navigation.tsx`
- `features/operations/api.ts`
- `features/operations/dashboard-shell.tsx`
- `features/operations/workspace.tsx`

Other new paths:

- `migrations/versions/20261120_0026_lead_recovery.py`
- `tests/test_recovery.py`
- `tests/test_recovery_routes.py`
- `tests/database/test_recovery.py`
- `docs/ai-lead-recovery.md`

Other modified paths:

- `.env.example`
- `tests/database/conftest.py`
- `tests/database/test_migrations.py`
- `tests/database/test_table_ownership.py`
- `docs/operations-dashboard.md`
- `docs/vercel-booking-jobs.md`
- `docs/project-state.md`
- `docs/_local/current-session.md` (local working memory)

The checkout contains extensive unrelated pre-existing edits/untracked files.
They were preserved. This manifest identifies this task's touched paths; it is
not a claim that every pending change in those shared files belongs to this task.

Suggested commit message (not committed):
`Add AI lead recovery demo, consent-gated workflow and secure model settings`
