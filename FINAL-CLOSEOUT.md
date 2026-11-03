# HVACLine AI portfolio closeout — November 3, 2026

Publication scope: owner authorized only the closeout fixes, regression tests and
documentation for `main`. Earlier inbound-investigation edits are excluded.
Publication does not authorize deployment, feature activation or live calls.

**Authorized follow-up:** `.venv/bin/python -m pytest tests/test_outbound_demo.py`
passed **39 tests in 1.64s**. Shell `python` was unavailable. This is unit-suite
evidence only. The separately authorized `npm run test:web --
src/app/api/outbound-demo/route.test.ts` also passed **15 tests**, one file, 556ms,
with a non-failing future Vite config-loading warning. The authorized focused
inbound/webhook run also passed **73 tests in 2.32s** across
`test_telnyx_sip_provider.py`, `test_phone_webhook_validation.py`,
`test_phone_conversation_provider.py` and `test_phone_post_call_ingress.py`, using
the documented environment and `.venv/bin/python`. Other checks below remain
unexecuted and live calling unverified.

**Implementation remains UNVERIFIED for this release.** Static review covered
browser Voice/Chat and HVAC booking, inbound SIP initialization/signed
finalization, outbound calling/configuration/transfer gates/migration 0018, and
homepage claims/feature flags. No new feature or architecture change was added.

## Implemented

- Browser Voice and silent text Chat, explicit AI/microphone permissions,
  authenticated session recovery, approved FAQs and separate intake/appointment
  readbacks. Scheduling persists holds and confirmed appointments with tenant
  ownership, idempotency, capacity and hazard gates.
- Telnyx SIP initialization with separate bearer authentication, active
  business-owned number routing, persisted call UUID and quotas. Signed,
  agent-bound post-call events finalize intake/calls with replay protection.
- Separate outbound fictional HVAC demo agent adapter, admin authentication,
  consented exact-number allowlist, durable request recovery, serialized quotas,
  signed lifecycle events and conservative unknown/transfer outcomes. No real
  appointments are booked by outbound demos.
- Gated homepage calling form and November 5 announcement. The date is a release
  plan; it never activates calling. Browser Voice opens the signed-in workspace;
  guest text chat requires its own enabled/configured backend.

## Evidence and fixes

- **Verified now:** after explicit migration authorization, the configured
  development database reported `20261101_0018` before and after the targeted
  Alembic upgrade. It was already current; no schema change was needed. This
  establishes that database's revision only, not application/schema acceptance
  or the database used by hosting.
- **Historical evidence:** October 30 notes record 76 focused phone tests,
  214 non-database tests and 23 isolated phone database tests passing. Owner
  previously reported working browser voice and full booking. These results do
  not verify this release or current provider/hosting configuration.
- **Confirmed source fixes, regression tests passed:** reject non-hex signatures and oversized
  timestamps without an unhandled exception; bound the inbound post-call body
  while streaming; run synchronous finalization outside the async request loop.
  Focused inbound/webhook tests passed as recorded above. Existing HMAC, tenant and replay
  restrictions remain required.
- **Unverified:** remaining release checks, database regressions, browser/mobile
  behavior, hosted revisions/settings, fresh inbound initialization/audio/booking
  and signed finalization, outbound calls and human transfer. Only the specifically
  authorized test runs above executed after static closeout. No builds, lint,
  formatting, type checks, services, provider edits, deployments or calls ran.
  Publication is a separate authorized step above. Private environment values
  were not changed.

## Exact owner-run verification commands

Run from the repository root using Python 3.13 and Node 24. Except for the
separate outbound Python/route and focused inbound/webhook runs above, these
checks remain unexecuted:

```sh
DEMO_SANDBOX_ENABLED=false PYTHONPATH=apps/backend/src .venv/bin/python -m pytest --import-mode=importlib tests/test_browser_spoken_confirmation.py tests/test_conversation_provider.py tests/test_settings.py tests/test_telnyx_sip_provider.py tests/test_phone_webhook_validation.py tests/test_phone_conversation_provider.py tests/test_phone_post_call_ingress.py tests/test_outbound_demo.py
.venv/bin/python -m ruff format --check apps/backend/src/insurance_operations/telephony/ingress.py apps/backend/src/insurance_operations/telephony/providers/elevenlabs.py tests/test_phone_conversation_provider.py tests/test_phone_post_call_ingress.py
.venv/bin/python -m ruff check apps/backend/src/insurance_operations/telephony/ingress.py apps/backend/src/insurance_operations/telephony/providers/elevenlabs.py tests/test_phone_conversation_provider.py tests/test_phone_post_call_ingress.py
.venv/bin/python -m mypy --explicit-package-bases apps/backend/src/insurance_operations/telephony/ingress.py apps/backend/src/insurance_operations/telephony/providers/elevenlabs.py tests/test_phone_conversation_provider.py tests/test_phone_post_call_ingress.py
npm run verify:web
```

Only after privately exporting and confirming an **isolated disposable**
`TEST_DATABASE_URL`, distinct from runtime/direct targets: the fixtures
truncate/downgrade/rebuild their database. Never point them at retained data.

```sh
APP_ENVIRONMENT=test GOOGLE_CALENDAR_ENABLED=false BOOKING_EMAIL_ENABLED=false DEMO_SANDBOX_ENABLED=false PYTHONPATH=apps/backend/src .venv/bin/python -m pytest --import-mode=importlib tests/database/test_conversation_api.py tests/database/test_hvac_scheduling.py tests/database/test_telnyx_sip_ingress.py tests/database/test_phone_receptionist_flow.py tests/database/test_outbound_demo_calls.py tests/database/test_migrations.py tests/database/test_table_ownership.py
```

Historical broad Python formatting/lint/type failures remain recorded in
`docs/inbound-phone-webhook-repair.md`; they were not rerun or mass-cleaned here.

## Safe migration and deployment

1. Confirm the hosting database/branch and snapshot/backup before any further
   migration. The locally configured development target is already at 0018.
   For a different approved target, inspect its revision first:

   ```sh
   APP_ENVIRONMENT=development .venv/bin/python -m alembic current
   APP_ENVIRONMENT=development .venv/bin/python -m alembic upgrade 20261101_0018
   APP_ENVIRONMENT=development .venv/bin/python -m alembic current
   ```

   From 0016, 0017 adds guest-chat tables; 0018 adds outbound call/consent evidence.
   Both upgrades are additive. Stop for an unexpected revision. Do not reseed,
   truncate, downgrade or stamp retained data. Migration 0018 refuses downgrade
   when outbound evidence exists; prefer application rollback with schema retained.
2. After owner-run checks and separate deployment approval, deploy compatible API
   code, then web. Preserve existing agents, inbound routing, appointments and
   stable secrets. Review effective hosting commands: `render.yaml` still defaults
   to Twilio and includes a seed; use a migration-only release command instead
   of blindly applying its seed. Set Telnyx selection explicitly when intended.
3. Configure the dedicated private outbound agent and signed webhook using
   `docs/elevenlabs-outbound-agent.json` and `docs/outbound-demo-calling.md`.
   Add authenticated TLS outbound settings to the existing imported SIP resource
   while preserving inbound routing. Start with End call only and transfer off.
4. Privately supply `OUTBOUND_DEMO_AGENT_ID`, `OUTBOUND_DEMO_PHONE_NUMBER_ID`,
   consented `OUTBOUND_DEMO_ALLOWED_NUMBERS`, stable `OUTBOUND_DEMO_SECRET`, and
   provider-generated `OUTBOUND_DEMO_WEBHOOK_SECRET`. These are missing locally;
   hosting values were not inspected. Reuse any existing state secret rather
   than rotating it: hashes protect ownership, retries and recipient limits.
   Copy the same bridge secret only to the Next server. Existing API key and
   operator/admin identity still require correct hosted configuration.

## Remaining acceptance and disabled features

- Browser: silent Chat with microphone denied; explicit Voice consent; typing,
  disconnect/retry/session release; two complete readbacks; exactly one stored
  confirmed appointment; expiry/conflict/hazard refusal; saved booking survives
  disconnect and agrees with customer history/Operations. Check keyboard/mobile.
- Inbound: one newly authorized real call must produce initialization 200 with
  its actual persisted UUID, two-way audio/tools, confirmed booking and signed
  terminal 200. Exercise refusal, callback fallback, replay and disconnect after
  confirmation. Never fabricate identities for earlier failed calls.
- Outbound: authorize one admin AI-only call after configuration/deployment;
  check consent/decline/wrong-number/voicemail, interruptions, <=180-second AI
  duration, signed end/failure, busy/unanswered and status recovery. An uncertain
  outcome blocks new dialing; inspect carrier legs before audited end attestation.
  No automatic redial. Follow the existing runbook for the actual call command.
- Keep `OUTBOUND_DEMO_ENABLED=false` until approved admin testing is configured;
  keep `OUTBOUND_DEMO_WEBSITE_ENABLED`, `OUTBOUND_DEMO_FORM_ENABLED`,
  `OUTBOUND_DEMO_TRANSFER_ENABLED`, `OUTBOUND_DEMO_LIVE_VERIFIED`,
  `OUTBOUND_DEMO_TRANSFER_VERIFIED` and `OUTBOUND_DEMO_CARRIER_LIMIT_CONFIRMED`
  false pending their actual prerequisites. Acceptance flags are evidence
  attestations, not implementations of missing carrier controls.
- **Transfer/public-calling blockers:** outbound-originated REFER support,
  unavailable-human behavior, and a carrier-enforced <=180-second limit covering
  transferred legs remain unresolved. A REFER acceptance never proves a human
  answered. Require an authorized fixed human, separate-turn agreement, actual
  two-way audio and carrier-leg termination before transfer/website acceptance.
- Leave optional guest chat, Calendar/email, WhatsApp, memory and local voice off
  wherever their configuration/acceptance is incomplete; preserve existing
  accepted settings. Production staff identity, onboarding and caller identity
  verification remain outside this portfolio release. Development gates stay.

**Next manual action:** run the focused owner checks above and configure the
dedicated outbound provider/private values. Migration 0018 is not a blocker on
the inspected target. Public calling and production readiness cannot be claimed.
