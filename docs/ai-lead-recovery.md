# AI Lead Recovery

## Local presentation refresh — November 25, 2026 — UNVERIFIED

Recovery demo/live/overview metrics share application cards and theme tokens.
Tables expose keyboard scrolling and selected leads; the demo detail panel adds
a selected-case timeline and distinct fictional confirmation. Existing request,
permission and provider behavior stays in place. The homepage teaser was removed
at the owner's request; shared navigation still exposes the dedicated demo.
No checks, formatters, services, providers, publication or deployment ran.
Current design commands/manual checks: [Web design system](web-design-system.md).

Shared [Multilingual AI Voice settings](multilingual-voice.md) do not activate
multilingual recovery. Recovery additional languages are unsupported: confirmed
contact-language preference is not part of the existing permission contract,
and the exact hosted-agent preflight rejects multilingual presets/tools and a
non-English primary language. Never infer outreach language or permission from
an enabled language, browser/native selection or transcript. All suppression,
channel-specific permission and outbound activation gates remain intact.
Multilingual/recovery runtime acceptance remains **UNVERIFIED**.

Delivery/continuation source implementation; **UNVERIFIED**. This follow-up ran
no tests, builds, linters, formatters, type checks, migrations, browser checks,
services, model/provider requests, messages, calls, hosted changes or deployments.
Migrations0026 and0027 were applied to the configured Neon development target
at the owner's explicit request. Migration0027 revision/schema readback succeeded
on2026-11-20; zero recovery policies are enabled and activation flags remain off.
Application/provider acceptance remains unverified. The owner separately
authorized source publication to main with [skip ci] [skip render]; publication
runs no local hooks and establishes no runtime or provider acceptance.

## Product experience

The shared homepage navigation links to `/ai-lead-recovery`. The homepage
recovery card, simulation, metrics and setup controls are absent. The dedicated
page opens recovery in the dashboard shell in Demo Mode;
`/ai-lead-recovery?setup=1` opens the existing administrator connection gate.
The dashboard overview's demo card also links to that page as **Try Yourself**;
connected workspaces retain their in-place recovery action and authentication.
Shared desktop/mobile navigation and the Operations sidebar expose the feature.
Legacy `/lead-recovery` links permanently redirect to the new route, preserving
`?setup=1` when present.

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
Dashboard overview and recovery share their state while navigating within that
workspace. Opening the dedicated page starts a new demo session.

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
   Request-scoped SMS and voice continuations now supply attribution only after
   durable explicit approval of the same held appointment. A delivery receipt,
   provisional hold or independent booking cannot receive recovery credit.
5. Protected case pages, counts, settings, versioned staff actions, permission
   evidence and encrypted AI configuration back the Live UI. Filters, pagination,
   loading/errors, setup guidance and empty/provider-unavailable states are real.
   Conversion is attributed recovered cases divided by all agency recovery cases;
   recoverable excludes RECOVERED, CLOSED and SUPPRESSED. Live revenue is omitted.

## Implemented delivery and continuation — runtime UNVERIFIED

`ConfiguredRecoveryProvider` supplies Twilio Programmable Messaging and a
separate ElevenLabs SIP recovery agent. Telnyx Verify and public demo calling
remain separate and unchanged. Delivery is opt-in at three levels: server kill
switch, server channel configuration, and agency administrator policy. Every
attempt also requires channel-specific recovery permission, current request
eligibility, a valid U.S. recipient, rate/contact-window checks and no suppression.
Configured means configuration present, not provider acceptance or live success.

A transport is bound to one explicitly configured agency per API/job deployment;
other agencies cannot borrow its sender or voice credentials. All activation
flags default false. Development/test identity restrictions remain in force;
this does not add production authentication or authorize real-customer use.

Twilio sends the deterministic service-only message using the persisted business
identity. Status and inbound callbacks use existing SDK signature verification
against the exact configured HTTPS callback URL and all received form values,
plus account, sender and destination ownership. Empty TwiML acknowledges incoming
messages; a durable job sends any requested response. QUEUED, SENT, DELIVERED,
FAILED and UNKNOWN remain distinct; receipts never count as customer engagement.

Verified STOP suppresses all automated recovery channels for the agency's
confirmed destination. A pending durable STOP blocks both sending and booking
continuation before the inbox is processed. Verified YES for exactly one recent
eligible SMS request pauses follow-ups and schedules one customer-requested
booking-link reply, with the same contact window and current permission checks.
This requested reply is separate from the maximum two unsolicited attempts;
only one reply grant exists per attempt. Repeated YES never resends an unknown
or expired link. Ambiguous or other replies require staff review. YES grants no
voice permission and never automatically places a call.

`/recover` exchanges a short-lived capability from a URL fragment for a scoped
HttpOnly, SameSite=Strict cookie through a same-origin proxy. No token enters a
query string or API projection. The customer can access only the original saved
request, actual availability, one reservation and exact readback/confirmation.
No account session is created. Missing/wrong details require staff assistance.
SMS links expire 30 minutes after their permitted delivery window begins; voice
grants expire after the bounded call duration plus a two-minute callback margin.
Expired unapproved grants release only the continuation's automatic pause;
manual staff pauses stay paused, and a new YES cannot override them. Links are bearer capabilities: protect the SMS
recipient and device; do not forward them.

A dedicated voice workflow introduces the business, identifies itself as AI and
asks to continue before revealing saved details. Eight authenticated webhook
tools reuse existing scheduling, holds, readback and explicit confirmation.
Header-only secret dynamic variables bind the attempt to the actual provider
conversation. The backend reads provider transcript evidence before accepting
continuation or appointment confirmation; an agent-supplied boolean is
insufficient. Transcript lag or an unsupported provider contract fails closed.
Raw recovery transcripts and secret initiation variables are never persisted.
Signed post-call evidence also recognizes explicit customer stop phrases when a
finish tool failed; unrelated phrases such as equipment that stopped working do
not imply an opt-out. Staff and hazard finish actions use existing handoffs.

Every voice send preflights the dedicated agent's exact prompt/first message,
private authentication, audio/retention controls, bounded duration, eight owned
tool URLs/secret headers, end-call tool, signed post-call webhook and dedicated
SIP/TLS/authenticated outbound number. Shared browser, inbound or public-demo
agents are rejected. Missing capabilities fail before initiating a call. No
hosted agent was created, edited or activated by this implementation.

Migration0027 adds an agency-owned durable webhook inbox, request/attempt-scoped
booking grants, owned-scope/immutable-approval guards, immutable dispatch/provider
references and reply-transition guards, plus non-secret dispatch snapshots,
recipient digests and read-reconciliation checkpoints. Existing booking jobs
process inbox events, requested replies, expiry, authoritative reads and due
attempts in bounded interleaved batches. Early callbacks are durably accepted
without acquiring a schedule lock held by sending. No second scheduler or
in-memory queue is added.

STARTED is committed before every outbound POST. Timeouts, lost create receipts
and interrupted sends become UNKNOWN; neither worker nor administrator retries
them blindly. Authoritative GET reconciliation requires the exact account,
recipient, original body and creation-time window for SMS, or owned agent and
attempt dynamic variable for voice. A protected administrator can supply a lost
original reference for the same verification. An unknown voice call without a
reference retains its concurrency slot until the owner independently attests
that every carrier leg ended; this releases concurrency only, leaving the
original attempt UNKNOWN and ineligible for retry.

Actual booking remains entirely in `SchedulingService`, including Google/GHL
conflict handling, confirmation notifications and existing CRM workflows.
Recovery authorization is rechecked inside confirmation/release transactions.
Durable approval preserves the same appointment/nonce across uncertain writes;
it cannot release or switch that selection. Existing GHL staff reconciliation
can finalize the original approved booking even after link expiry. Expired or
uncertain customer sessions require staff help; never create another appointment
to work around an unknown external write. No external API offers atomicity with
PostgreSQL: a provider call can finish after an opt-out arrives; suppression
blocks subsequent work and final attribution checks remain conservative.

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
Existing ElevenLabs browser/inbound voice remains separately configured. Recovery
voice uses its separately provisioned ElevenLabs-managed language/speech stack;
custom text models cannot be attached to that live agent through these settings.
Voice-only recovery does not require a separate text-model connection. SMS
activation requires a tested text connection, but sends use the fixed reviewed
service message, not unconstrained model output.

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

The configured Neon development target was upgraded from0025 to0026 and then
from0026 to0027 on2026-11-20 at the owner's explicit requests. Latest readback
confirmed sole revision0027, both new delivery tables, five attempt columns,
four indexes, three new triggers, two new guards and zero enabled policies.
Do not rerun these completed migrations on the same target. Other targets still
need deliberate migration selection; application/provider behavior is unverified.
A dedicated key is saved in ignored local.env; copy it privately to the hosted
API and job runner without generating different keys. Hosted settings are unchanged.

- Review `20261120_0026_lead_recovery.py`, following0025, before changing a database.
  It is applied only to the configured development target above. API and job runner must use the upgraded schema
  before this source is released, including when automation is off.
  It inserts disabled policy defaults and capture timestamps, never historical
  customer/case records. Recovery timezone must match existing Scheduling.
- `RECOVERY_ENABLED=false`: server kill switch. Keep false during schema/provider
  setup and unverified acceptance. Setting true permits explicitly enabled
  agency policies; it does not turn on either channel or supply consent.
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

## Transport setup — provider provisioning pending

Review and apply forward `20261120_0027_recovery_delivery.py` after0026 before
releasing the updated API or job runner, even when recovery is disabled.
This is complete only for the configured development target above. It
adds two tables and five attempt columns/indexes, without enrolling historical
leads. Downgrade0027 refuses while grant/inbox history exists.

Use the same server-only configuration on the API and existing job runtime:

- `RECOVERY_AGENCY_ID`: the actual intended agency UUID; not a customer or agent ID.
- `RECOVERY_PUBLIC_API_ORIGIN`: exact public HTTPS API origin, port443, no path.
- `RECOVERY_WEB_ORIGIN`: exact public HTTPS web origin; must equal API WEB_ORIGIN.
  The web app's existing NEXT_PUBLIC_API_BASE_URL must target that API.
- `RECOVERY_SMS_ENABLED=false`, `RECOVERY_SMS_COMPLIANCE_CONFIRMED=false`.
  After owner review only: dedicated `RECOVERY_TWILIO_ACCOUNT_SID`, server-secret
  `RECOVERY_TWILIO_AUTH_TOKEN`, owned E.164 `RECOVERY_SMS_FROM_NUMBER` and
  `RECOVERY_SMS_DAILY_LIMIT` (default50, maximum100 initial attempts/day).
- `RECOVERY_VOICE_ENABLED=false`, `RECOVERY_VOICE_COMPLIANCE_CONFIRMED=false`.
  Dedicated server-secret `RECOVERY_VOICE_API_KEY`, `RECOVERY_VOICE_AGENT_ID`,
  `RECOVERY_VOICE_PHONE_NUMBER_ID`, E.164 `RECOVERY_VOICE_FROM_NUMBER`, distinct
  >=32-character `RECOVERY_VOICE_TOOL_SECRET` / `RECOVERY_VOICE_WEBHOOK_SECRET`,
  and `RECOVERY_VOICE_WEBHOOK_ID`. `RECOVERY_VOICE_DAILY_LIMIT` defaults5/max10;
  `RECOVERY_VOICE_MAX_SECONDS` defaults180/max180. One active voice leg at a time
  per configured agency. Retain legacy agent IDs in jobs too for isolation checks.

Twilio setup requires an actual Programmable Messaging sender/account permitted
for this service use case and the owner's applicable registration, destination,
consent and calling-policy review. A Telnyx Verify profile is insufficient.
Configure that sender's incoming POST URL to
`/api/v1/providers/recovery/twilio/incoming` at the configured API origin.
Status callbacks are set per message to `/twilio/status/{attempt_id}` or
`/twilio/reply-status/{grant_id}` beneath `/api/v1/providers/recovery`.
Preserve exact paths/no query strings behind HTTPS proxies for signatures.

Review [the dedicated agent JSON contract](elevenlabs-recovery-agent.json), then
provision a separate private agent only under deliberate owner authorization.
Replace YOUR_API_HOST, YOUR_BEARER_SECRET_ID and YOUR_RECOVERY_WEBHOOK_ID; the
provider secret referenced by Authorization must contain the full
`Bearer <RECOVERY_VOICE_TOOL_SECRET>` value. Do not put actual secret values in
this artifact. Choose supported hosted model/speech settings in ElevenLabs;
the artifact deliberately does not invent a model/voice entitlement. Keep exact
prompt/first-message, the eight webhook tools and native end_call. Dynamic
headers use provider variable references, including secret__recovery_context;
never put that secret variable in a prompt. Configure signed transcript and
call-initiation-failure POST events to
`/api/v1/providers/recovery/voice/webhook` with the dedicated webhook secret.
Recording must be false, retention_days0, private auth enabled, no additional
tools/workflows/knowledge sources or initiation webhook. The dedicated owned SIP
number needs TLS and authenticated outbound credentials. Provider account,
privacy, speech/model entitlement and telephony acceptance remain external.

Administrator enablement requires server/channel gates, selected configured
channels, matching Scheduling timezone and SMS text-model connection if chosen.
Then record genuine explicit per-channel evidence for each intended fictional
acceptance contact before enabling the agency policy. Configuration is not
proof of provider acceptance. Nothing here changes hosted settings automatically.

## Owner commands — checks unexecuted; development migration complete

Use the existing Python3.13 and Node24 environments. Do not run database tests
until TEST_DATABASE_URL is privately confirmed to be an isolated disposable
database distinct from all runtime/direct databases: fixtures downgrade/rebuild
and truncate their target. No actual credentials belong in these commands.

```sh
.venv/bin/python -m pytest tests/test_recovery.py tests/test_recovery_routes.py tests/test_recovery_delivery.py tests/test_booking_jobs.py tests/test_worker.py tests/test_settings.py
npm run test:web -- src/features/recovery/demo.test.ts 'src/app/api/recovery/[[...path]]/route.test.ts'
.venv/bin/python -m ruff check apps/backend/src tests
.venv/bin/python -m mypy apps/backend/src tests app.py
npm run lint:web
npm run typecheck:web
npm run build:web
APP_ENVIRONMENT=test .venv/bin/python -m alembic upgrade head
APP_ENVIRONMENT=test .venv/bin/python -m alembic check
APP_ENVIRONMENT=test .venv/bin/python -m pytest tests/database/test_recovery.py tests/database/test_recovery_delivery.py tests/database/test_migrations.py tests/database/test_table_ownership.py tests/database/test_hvac_scheduling.py tests/database/test_booking_jobs.py tests/database/test_phone_receptionist_flow.py
```

The configured development target is already at0027; do not rerun its completed
migration. For a different target, after deliberate owner selection and review,
the forward migration command is:

```sh
APP_ENVIRONMENT=development .venv/bin/python -m alembic upgrade head
```

No formatter was run; formatting and all static/runtime results remain unverified.
Optional owner formatting checks (also not executed):

```sh
.venv/bin/python -m ruff format --check apps/backend/src tests migrations
npm run format:check:web
```


## Manual acceptance — fictional customers only

1. Signed out, confirm the homepage has a compact recovery card, one **Try
   Yourself** link and no embedded recovery table, metrics or simulation.
   Follow that link, the dashboard overview's **Try Yourself** link and the
   desktop/mobile AI Recovery navigation to `/ai-lead-recovery`. With backend
   access unavailable, confirm the dedicated page still opens in the dashboard
   shell. Check legacy `/lead-recovery` redirects to the new route and preserves
   `?setup=1`; the new setup route must retain the administrator gate when the
   backend origin is configured. Confirm DEMO MODE / DEMO DATA,24 opportunities,
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
   never increase recovered counts. Verify signed YES creates exactly one scoped
   booking-link reply; the customer explicitly selects a real slot and confirms
   the full readback before recovery credit. Repeat confirmation returns the
   same appointment. Pending STOP, staff closure, changed consent or changed
   recipient blocks both new contact and confirmation.
8. With mocked provider responses, exercise early/duplicate/out-of-order status
   events, forged signatures, wrong accounts/destinations, ambiguous YES, expired
   grants, unknown requested-reply sends and provider reference recovery. Reconcile
   with GET only; a wrong destination/body/time/attempt must reject. Verify no
   secret capability or transcript is present in the durable inbox, API/audit
   output, URL query, browser localStorage or generated client bundle.
9. With mocked ElevenLabs agent/phone/conversation records, reject shared agents,
   extra tools, missing secret headers, retention/recording mismatch, insecure SIP
   and transcript lag. Accept only exact AI introduction + customer yes, and the
   full current booking readback + explicit yes. Decline closes; STOP suppresses
   all channels; hazards/staff requests use existing handoffs. A fixed delivery
   receipt never implies the customer accepted an appointment.
10. Any actual messaging/calling/AI connection acceptance requires a separate
    owner-controlled fictional recipient/account, explicit activation and
    authorization. No live acceptance was performed. Verify provider receipts,
    carrier termination, notifications/calendar/GHL outcomes and final saved
    attribution before considering live rollout; keep production identity gates.

## Original recovery/demo source manifest

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

- `app/ai-lead-recovery/page.tsx` and legacy `app/lead-recovery/page.tsx` redirect
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

## Exact source manifest for this delivery follow-up

New backend files under `apps/backend/src/insurance_operations/recovery/`:
`configuration.py`, `continuation.py`, `continuation_routes.py`, `delivery_jobs.py`,
`errors.py`, `grants.py`, `inbox.py`, `transports.py`, `voice.py`, `webhooks.py`.

Modified backend files under `apps/backend/src/insurance_operations/`:
`application.py`, `settings.py`, `database/models/__init__.py`,
`database/models/recovery.py`, `hvac/service.py`, `notifications/booking.py`,
`recovery/ai.py`, `recovery/domain.py`, `recovery/events.py`, `recovery/jobs.py`,
`recovery/providers.py`, `recovery/routes.py`, `recovery/schemas.py`,
`recovery/service.py`.

New web files under `apps/web/src/`:
`app/api/recovery/[[...path]]/route.ts`,
`app/api/recovery/[[...path]]/route.test.ts`, `app/recover/page.tsx`,
`features/recovery/customer-continuation.tsx`.
Modified: `features/recovery/api.ts`, `features/recovery/live.tsx`.

New migration/source tests/setup artifact:
`migrations/versions/20261120_0027_recovery_delivery.py`,
`tests/test_recovery_delivery.py`, `tests/database/test_recovery_delivery.py`,
`docs/elevenlabs-recovery-agent.json`.
Modified: `tests/test_recovery_routes.py`, `tests/database/test_recovery.py`,
`tests/database/test_migrations.py`, `tests/database/test_table_ownership.py`,
`.env.example`, `docs/ai-lead-recovery.md`, `docs/operations-dashboard.md`,
`docs/vercel-booking-jobs.md`, `docs/project-state.md`,
`docs/_local/current-session.md` (ignored local notes).

No dependencies, real environment credentials, README, hosted agents or providers
were changed in this follow-up. The checkout's unrelated source remains intact.
All new automated, schema, provider, security, visual and runtime checks are
**UNVERIFIED**. Suggested commit (not created):
`Add consent-gated recovery SMS, dedicated voice callbacks and attributed booking continuation`

Provider contract references used during source implementation:
[Twilio Message resource](https://www.twilio.com/docs/messaging/api/message-resource),
[Twilio incoming messaging webhooks](https://www.twilio.com/docs/messaging/guides/webhook-request),
[ElevenLabs SIP outbound call](https://elevenlabs.io/docs/api-reference/sip-trunk/outbound-call),
[ElevenLabs webhook tools](https://elevenlabs.io/docs/eleven-agents/customization/tools/webhook-tools),
[ElevenLabs dynamic variables](https://elevenlabs.io/docs/eleven-agents/customization/personalization/dynamic-variables),
[ElevenLabs conversation details](https://elevenlabs.io/docs/api-reference/conversations/get),
[ElevenLabs post-call webhooks](https://elevenlabs.io/docs/eleven-agents/workflows/post-call-webhooks).
Documentation contracts do not establish hosted configuration, real-time transcript
freshness, retention acceptance or successful calls. Those remain owner-unverified.
