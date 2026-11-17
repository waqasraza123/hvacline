# GHL voice booking and inbound demo

Source implementation/runtime is **UNVERIFIED**. On2026-11-18, the owner authorized
applying migration0025 to the configured direct development database. Upgrade
0024 →0025 succeeded; revision, columns, booking table and ownership foreign keys
were read back. No tests, builds, linters, type checks, hosted configuration,
provider activation or telephone calls ran. The first three requested
priorities are covered in source: GHL calendar booking, contact summaries and the
existing inbound-phone tool flow. A callable demo still requires owner-controlled
deployment, phone/agent setup and live acceptance below.

## Booking behavior

Operations → Integrations → GoHighLevel → Voice booking and contact summaries
maps existing Scheduling teams to GHL calendar IDs. Mappings default empty and
contact notes default off. Teams without a mapping retain their current behavior.
Service ZIPs, local business/team hours, holidays, duration, notice, booking limits,
hazard rules and explicit confirmation remain enforced. Returned times are the
intersection of local candidates, local capacity and GHL free slots.

A HELD result reserves local capacity for five minutes; it does **not** hold a GHL
slot. Confirmation rechecks GHL and creates an appointment with provider slot/date
validation enabled, confirmed status, and `toNotify=false`. This slice does not
start GHL messaging automations. The backend verifies the saved event's location,
calendar, contact, stable appointment title, start/end and confirmed status before
committing its local CONFIRMED result. Existing HVACLine booking notifications,
when enabled, retain their normal behavior.

Each attempt is bound to its original business, connection, calendar and local
appointment. Contact and appointment creation checkpoints commit before provider
writes. Repeated confirmation returns the existing receipt. A timed-out create,
process interruption or uncertain response never automatically creates another
GHL appointment. Unresolved attempts continue blocking local capacity even after
the ordinary hold expires. Provider 429 responses apply a shared connection delay.

Admin booking history supports two deliberate recovery actions:

- Link the exact existing GHL appointment ID. Ownership/times/confirmed status and
  current local eligibility must pass before recovering local confirmation.
- After checking GHL and confirming no appointment exists, release the unresolved
  local reservation. This does not automatically retry creation or delete contacts.

Do not declare an appointment absent while an original request may still be in
flight. A known linked event cannot be cleared through absence review. If a remote
event exists but local validation fails, retain it for staff review; no confirmation
or automatic replacement is promised.

GHL cancellation/rescheduling and continuous reconciliation of external edits are
outside this slice. Local change actions for linked/uncertain GHL bookings return
a staff-review error rather than changing only the local record. Staff must handle
those changes in GHL; do not advertise self-service changes for this demo. A team
cannot change provider/calendar while it has active appointments, unexpired holds
or unresolved attempts. Disconnecting the GHL connection has the same guard.

## Contact summaries

Enable contact summaries and supply the note author's GHL user ID from this
sub-account. After a confirmed intake becomes a persisted lead, the existing CRM
job writes one note on its matched contact. It includes the stable request
reference, confirmed name, callback number, source, urgency and request summary.
Telephone leads finalize through the existing signed post-call webhook, so their
summary delivery follows that finalization and the next job run.

This is the confirmed intake summary, not a new generated full-call transcript
summary or an audio recording. Each new request has its own note. Existing notes,
contact identities and communication preferences are preserved. Subsequent
booking-stage updates reuse the note; they do not overwrite its original summary.
Enabling notes does not backfill already synchronized historical requests.

The job uses the current `/notes` API with a contact relation and reads back the
note. Unknown note creation requires linking the matching note ID or explicit
absence review in Delivery history before another creation. The API supplies no
cross-system transaction; this review path avoids blindly repeating uncertain
writes.

## Owner setup

1. Review migration `20261118_0025` following `20261113_0024`. It adds optional voice
   configuration/version, note delivery state and `ghl_calendar_bookings` with
   composite business ownership constraints. Apply it to the intended database
   **before deploying this backend**. The configured development database already
   reached0025 on2026-11-18; do not rerun solely for this handoff. Other deployment
   targets require their own reviewed migration operation.
2. Keep the existing API/jobs `GHL_ENABLED` and shared `GHL_TOKEN_ENCRYPTION_KEY`
   configuration. Use an authorized fictional-data test sub-account. No new
   environment variables, dependencies or public credentials are needed.
3. Extend its Private Integration Token with `calendars.readonly`,
   `calendars/events.readonly`, `calendars/events.write`, `notes.readonly` and
   `notes.write`, in addition to the existing CRM scopes in [the GHL guide](gohighlevel.md).
   Replace the stored token through Integrations, then validate and resume.
4. Configure the team's schedule and service area. Use an active personal,
   round-robin or event GHL calendar with a fixed default duration matching
   Scheduling. Multi-duration, collective, class and service-booking calendars are
   not supported by this first adapter. Disconnect Google for this team before
   adding its GHL route; retained disconnected Google history is preserved.
5. Save the team/calendar mapping. Enable contact summaries with an authorized
   note-author user ID belonging to this sub-account. A bad author/permission is
   reported through delivery history; it must be corrected before acceptance.
6. Deploy the migrated backend/web and keep the existing bounded job scheduler
   running with the same database and GHL settings. The UI does not start jobs.
7. Keep the existing private inbound phone agent, authenticated tools, signed
   post-call webhook and owner-controlled test number. Apply the demo prompt below
   alongside the eight-tool contract in [live validation](hvacline-live-validation.md#phone-agent-instruction-contract).
   Carrier setup remains in [Telnyx SIP setup](telnyx-sip-setup.md), or use the
   existing Twilio adapter. This task does not purchase or assign a number.

For the deliberately selected development database, the deferred migration command
is:

```sh
APP_ENVIRONMENT=development .venv/bin/alembic upgrade head
```

Do not downgrade while booking attempts or summary references remain. The migration
refuses to discard unresolved/confirmed booking state or delivered note references.

## Inbound demo prompt additions

Use the existing fictional Harborline Heating & Air business and approved FAQs.
Set the agent's business name through its existing configuration, not an invented
provider/account identifier. Preserve its private authentication, disclosure,
consent, privacy, call-duration and spend controls. Apply this behavior:

> After the caller accepts AI disclosure and voice processing, ask whether this
> is an emergency or a routine service request. For danger, prioritize the
> business-approved emergency wording and human assistance; do not offer a routine
> booking or promise a live transfer. For routine requests, collect the confirmed
> name, callback number, full service address, service kind, equipment issue and
> preferred time. Put a concise factual issue summary in the confirmed intake.
> Read back the details and obtain explicit agreement before confirm-intake and
> service-request. Use availability and offer only its returned times. Reserve
> the selected time with a stable booking key. Explain that it is not booked yet.
> Read back its date, time and business timezone and obtain a separate yes before
> confirm-appointment. Say booked only when that tool returns CONFIRMED. Keep the
> original reservation ID on errors. For an unresolved GHL result, request staff
> review; do not create a replacement or claim that nothing was booked. Allow
> callers to interrupt, correct details and decline. Never treat an interruption
> or a correction as confirmation.

The eight tool URLs/payloads remain unchanged. GHL credentials stay on the backend.
Telnyx live emergency transfer remains unavailable; its callback fallback is
unchanged. Outbound lead reactivation and cloning/onboarding are not implemented
by this first-three-priorities slice.

## Deferred checks — owner execution only

Run unit/API checks when specifically authorized:

```sh
APP_ENVIRONMENT=test .venv/bin/python -m pytest tests/test_ghl.py tests/test_ghl_voice_booking.py tests/test_ghl_routes.py
npm run test:web -- src/features/conversation/booking-progress.test.ts src/features/conversation/voice-booking.test.ts
npm run verify:web
.venv/bin/ruff check apps/backend/src/insurance_operations/ghl apps/backend/src/insurance_operations/hvac apps/backend/src/insurance_operations/customer_access/bookings.py apps/backend/src/insurance_operations/database/models/ghl.py migrations/versions/20261118_0025_ghl_voice_booking.py tests/test_ghl_voice_booking.py tests/database/test_ghl_voice_booking.py
.venv/bin/mypy apps/backend/src
```

Database fixtures downgrade/rebuild their database. Select an isolated disposable
`TEST_DATABASE_URL`, never the configured development or production database:

```sh
APP_ENVIRONMENT=test .venv/bin/python -m pytest tests/database/test_ghl_voice_booking.py tests/database/test_ghl.py tests/database/test_hvac_scheduling.py tests/database/test_phone_receptionist_flow.py tests/database/test_booking_jobs.py tests/database/test_migrations.py tests/database/test_table_ownership.py
APP_ENVIRONMENT=test .venv/bin/alembic check
```

After separately authorized deployment/provider setup, manually:

1. Open connected Integrations on desktop/mobile and both themes. Save calendar
   routes and notes, reload, and verify stale-version/invalid-calendar errors.
   Signed-out/customer access must not expose settings, history or recovery.
2. Call the owner-controlled demo number using fictional details. Answer routine,
   interrupt/correct the agent, confirm intake, choose an offered slot and confirm
   the appointment. Verify exactly one event on the selected GHL calendar, matching
   business/contact/times and one local CONFIRMED receipt.
3. End the call; after signed post-call finalization and the scheduled delivery,
   verify name/phone and the request summary on the GHL contact, plus the existing
   opportunity/stage. A second request reuses the contact with a separate note/deal.
4. Test a reported emergency, declined consent/confirmation, out-of-area ZIP,
   unavailable time, provider permission/rate failures and an expired hold. None
   may produce a false confirmed appointment or an unsupported transfer promise.
5. With controlled provider mocks or a supervised test environment, interrupt
   create responses/local finalization; repeat the same confirmation, confirm no
   duplicate, and recover the original event/note. Test foreign/mismatched IDs,
   absence review, unresolved capacity and provider/mapping/disconnect guards.
6. Give the client the accepted callable number and a Loom walkthrough of the
   GHL event/contact and Operations history. Share fictional data only. Do not
   claim the number or deployment was accepted before these steps pass.

Provider references:
[free slots](https://marketplace.gohighlevel.com/docs/ghl/calendars/get-slots/index.html),
[create appointment](https://marketplace.gohighlevel.com/docs/ghl/calendars/create-appointment/index.html),
[get appointment](https://marketplace.gohighlevel.com/docs/ghl/calendars/get-appointment/index.html),
[calendar configuration](https://marketplace.gohighlevel.com/docs/ghl/calendars/get-calendar/index.html),
[create note](https://marketplace.gohighlevel.com/docs/ghl/objects/create-note/index.html),
[get note](https://marketplace.gohighlevel.com/docs/ghl/objects/get-note/index.html).
