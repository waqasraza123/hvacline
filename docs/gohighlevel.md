# GoHighLevel integration

Implementation is **unverified**. The owner requested coding only. No tests,
builds, lint/type checks, migrations, services, live GHL requests, customer calls,
or deployment ran for this feature. The owner subsequently authorized committing
and pushing all pending work to main; that does not authorize verification or
deployment. Source formatting is an edit, not evidence of correctness.

## First version

Connected Operations → Integrations → GoHighLevel connects one GHL sub-account
per business using a Private Integration Token. Tokens are encrypted with a
dedicated server key and bound to the connection/business. The API never returns
them, and the browser holds input only in component memory until success/unmount.
Management always requires `X-Demo-Admin-Token`, even if the optional sandbox gate
is disabled. Production identity is still incomplete: retain development/test
gates and fictional data. This is not public multi-tenant onboarding.

New, customer-confirmed intakes with persisted leads are enrolled after connection
activation. Browser Voice/Text, inbound phone, WhatsApp and published-website
inquiries use the same persisted boundary. Unsaved conversations, anonymous
homepage chat, outbound callback demonstrations and the local dashboard fixtures
do not enroll contacts. Connecting/reconnecting does not backfill older leads.

The flow is confirmed intake → match/create contact → separate opportunity per
lead. Matching normalizes email and phone and scopes both lookups to the location.
Phone normalization uses the customer's saved country; invalid/ambiguous numbers
require review. No identifiers are invented. More than one match, or email and
phone matching different contacts, blocks delivery. Existing contacts are reused
without modifying identity fields, tags, DND or communication preferences.

Each opportunity has a stable `hvacline:<lead UUID>` name/reference, confirmed
summary/source/urgency and booking details. Returning callers reuse their matched
GHL contact but receive separate opportunities. The connection owns only its
mapped custom fields and pipeline stages, never value, ownership or won/lost
decisions. Closed opportunities, changes to the last managed stage, changed
contact/reference and movement outside the managed pipeline require review.
Lost responses to HVACLine's own stage updates allow reconciliation of the
previous or pending stage. GHL does not provide a cross-system transaction for
concurrent user edits; these checks detect observed edits, not every possible
race between the read and write. Reserve the dedicated pipeline for this workflow.

Stage precedence:

1. Hazard, outstanding human handoff or calendar reconciliation error → Needs attention.
2. Active confirmed appointment → Booked.
3. Previously confirmed appointment cancelled without replacement → Cancelled.
4. Otherwise → New request.

Holds and released/expired holds are not bookings or booking cancellations.
Rescheduling updates the original opportunity with the replacement appointment.
Appointment ID, start/end, configured timezone and team are written to the booking
field. Cancelling an appointment does not automatically mark the deal lost.
HVACLine/internal Google scheduling remains authoritative; no GHL calendar writes.

## Owner setup — perform separately

1. Review forward migration `20261113_0024` after `20261113_0023`. It adds
   `ghl_connections`, `ghl_deliveries`, an agency/lead uniqueness constraint and
   transactional capture triggers. Apply to the intended database before enabling
   the integration. There is no historical data export or provider call in the
   migration. Downgrade removes local connection/delivery history; it does not
   remove GHL records. Disable/drain execution before any downgrade.
2. Generate a dedicated Fernet key in your secret manager. Configure the identical
   `GHL_TOKEN_ENCRYPTION_KEY` on API and existing worker/scheduled job function.
   Set `GHL_ENABLED=true` only on those development/test runtimes. No `NEXT_PUBLIC`
   credential/key is needed. Keep the key stable; replacing it without re-encrypting
   stored credentials requires replacing each private token through the UI.
3. In a client-owned GHL **test sub-account**, create a Private Integration Token
   with `contacts.readonly`, `contacts.write`, `opportunities.readonly`,
   `opportunities.write`, and `locations/customFields.readonly`. Use the sub-account
   token, not a legacy API key or agency-wide token. No notes/tasks/calendar/workflow
   permission is needed. Setup checks pipeline/field read access and mappings;
   contact access and write permissions are exercised only during explicitly
   authorized delivery.
4. Create/select a dedicated pipeline with four separate stages for new, booked,
   cancelled and needs-attention requests. Enable multiple opportunities per
   contact in the sub-account. Disable duplicate contacts to avoid a race with
   unrelated contact creators. The connector never changes these settings.
5. Create three dedicated **opportunity** text fields: request reference, summary,
   booking details. Use LARGE_TEXT for summary/booking. Ordinary contact fields,
   numeric fields and fields from another location are rejected. The connector
   validates configured fields before delivery and reads back its writes; ignored
   or changed fields stop delivery rather than reporting success.
6. Connect the authorized Operations workspace, open Integrations and enter the
   location ID/private token. Validate, select the pipeline and field/stage mappings,
   acknowledge multiple opportunities and connect. Do not paste credentials into
   repository notes, issue bodies, chat transcripts or screenshots.
7. Use the existing bounded job runner or standalone worker with the same flags,
   key and database. `/api/v1/internal/booking-jobs/run` retains its existing job
   authorization and 20-second batch budget. GHL jobs are interleaved after
   calendar/notification work. No new background service is needed. A deployment
   and scheduler are separate owner operations; this implementation starts neither.

Existing GHL workflows can react to contact/opportunity creation or stage changes.
Use a test location with outbound sends disabled for acceptance. HVACLine itself
does not send GHL messages or enroll contacts in workflows.

## Delivery, failure and recovery

Database triggers coalesce relevant committed changes into one versioned outbox
row per connection/lead. Rollback rolls back enrollment. Business ownership is
enforced by composite foreign keys. Holds and repeated no-change updates do not
produce booking sync events; calendar polling timestamps alone do not re-export.
Payloads are constructed from current records at execution, not duplicated as raw
transcripts in an integration table. Contact/opportunity IDs and completed versions
survive interrupted jobs. Changes arriving during delivery remain pending.

Business-scoped advisory coordination excludes simultaneous workers, rotation,
disconnect and recovery. A separate coordinator transaction holds only the mutex;
provider calls occur outside transactions that modify business/outbox records.
API discovery/delivery calls use bounded provider budgets, fixed HTTPS origin,
API `Version: v3`, no redirects and limited response sizes. HTTPX URL logging for
this host is suppressed; do not enable transport/body debug logging.

Transient failures use up to eight automatic attempts, exponential delay from
30 seconds up to one hour, and `Retry-After` when longer (bounded to a day).
Rate limits pause every delivery for that connection until its delay passes.
Invalid/revoked credentials and invalid mappings pause the connection in ERROR.
Other permanent failures and exhausted attempts become NEEDS_REVIEW. The history
shows sanitized error codes, remote IDs, prior/pending stage IDs and sync progress;
job batch counts describe processing, not successful CRM delivery.

Creation intent is committed **before** a provider create call. A timeout, dropped
response or crash cannot silently reset it. Contact creation reconciles by exact
identity lookup; opportunity creation reconciles by exact request-reference field
using bounded paginated search. Zero/ambiguous matches stop for review rather than
blindly creating another record. There is no claim of globally exactly-once writes.

- Refresh status before retrying after an interrupted browser request.
- For a revoked token, replace it (connection becomes PAUSED), then validate/resume.
- For missing stages/fields, restore their original IDs. Changing mappings or
  destination requires disconnect/reconnect; existing history stays with the old
  connection and is not automatically exported to the new destination.
- For contact conflicts, resolve the identity/duplicates in GHL, then retry.
- For an unknown opportunity creation, supply the matching opportunity ID. Its
  location, pipeline, contact and exact request reference must agree before binding.
  A renamed opportunity can be recovered by ID even if name-based search misses it.
- Confirm absence only after checking GHL. The server reconciles again before
  clearing the creation marker; a unique existing match is reused. Stale search
  results and simultaneous external creators cannot be eliminated by this attestation.
- For externally edited opportunities, deliberately restore the prior managed
  stage/reference/contact if HVACLine should manage them again. Retry does not
  override closed deals or take over unrelated opportunities.
- Pause retains queued/new confirmed changes. Disconnect removes stored credentials
  and stops old deliveries, preserving GHL records and local history. An already
  completed external operation cannot be undone by disabling a feature flag.

## API and source

Administrator-only prefix: `/api/v1/development/integrations/ghl`.

| Method/path suffix | Behavior |
| --- | --- |
| `GET /` | Enabled state and latest sanitized connection |
| `POST /discover` | Read-only token/location/pipeline/field discovery |
| `POST /connection` | Validate and activate a new connection |
| `POST /connection/action` | Pause, validate/resume or disconnect |
| `POST /connection/token` | Validate replacement token; preserve destination and pause |
| `GET /deliveries?offset=0&limit=25` | Business-scoped paginated delivery/history |
| `POST /deliveries/{id}/retry` | Reconcile/retry; optional matching opportunity ID or absence attestation |

New source is in backend `ghl/`, `database/models/ghl.py` and frontend
`features/ghl/`. Existing scheduler collection, application routing, settings,
dashboard navigation and schema/ownership specifications are extended. No new
dependencies. Customer proxies and voice tools expose no CRM-management operation.

## Owner verification — not executed

Run only when explicitly authorized. Existing unrelated verification failures may
still require attention; implementation is not verified by this checklist.

```sh
npm run verify:web
APP_ENVIRONMENT=test pytest tests/test_ghl.py tests/test_ghl_routes.py
ruff check apps/backend/src/insurance_operations/ghl apps/backend/src/insurance_operations/database/models/ghl.py migrations/versions/20261113_0024_ghl_integration.py tests/test_ghl.py tests/test_ghl_routes.py tests/database/test_ghl.py
mypy apps/backend/src/insurance_operations/ghl
```

For the following, configure `TEST_DATABASE_URL` to an explicitly isolated,
disposable test database. Existing database fixtures **downgrade/rebuild** their
target and tear down its schema afterward; never use a shared/runtime database.

```sh
PGOPTIONS='-c timezone=UTC' APP_ENVIRONMENT=test pytest tests/database/test_ghl.py tests/database/test_booking_jobs.py tests/database/test_table_ownership.py tests/database/test_migrations.py
APP_ENVIRONMENT=test alembic upgrade head
APP_ENVIRONMENT=test alembic check
APP_ENVIRONMENT=test alembic downgrade 20261113_0023
APP_ENVIRONMENT=test alembic upgrade head
```

Manual acceptance after separately authorized deployment/provider setup:

1. At mobile/desktop sizes and in both themes, navigate Integrations with keyboard;
   connect/validate/map, refresh and paginate. Demo mode must make no GHL requests.
   Missing/wrong admin tokens and customer credentials must not authorize management.
2. Confirm a fictional lead; observe one contact/one opportunity and matching fields.
   Confirm another request using the same identity; observe one contact/two deals.
3. Book, reschedule, cancel and request/complete handoff; check stages and appointment
   details. Release a hold and verify it is not represented as cancelled booking.
4. Interrupt create responses and job execution, replay confirmations and run
   concurrent jobs. Completed steps must persist; unknown creates must reconcile or
   require review. Check explicit ID recovery, duplicate references and absence review.
5. Exercise 429, revoked token, missing fields and provider failures. Booking must
   still persist locally, rate delays must apply across the connection, and recovery
   must stay visible. A changed GHL stage/closed deal must not be overwritten.
6. Verify pause/resume/rotation/disconnect, retained history, no automatic backfill
   and no access across businesses or locations. Check logs/projections/storage for
   token leakage. Confirm existing booking/calendar/email/website flows still work.

## Next step and next integration

Immediate next step: owner-controlled GHL acceptance. Review/apply0024, configure
the shared API/job encryption key and enable flag, prepare the dedicated test
sub-account/pipeline/fields, then demonstrate a confirmed lead, repeat request,
booking update and recoverable provider failure. Keep the homepage GoHighLevel
badge labeled **CRM sync · Preview** until live acceptance is reported. Exact
deferred commands and manual scenarios are above; no execution is authorized by
this handoff.

Recommended next integration: **n8n event delivery** after GHL acceptance.

- Emit explicit confirmed-lead, confirmed/rescheduled/cancelled-appointment and
  requested/completed-handoff events. Include a stable event ID, business-scoped
  references, occurrence time and only the approved fields needed by the workflow.
- Deliver through a separate durable outbox with bounded retries, visible failures
  and replay controls. Unlike GHL's coalesced state synchronization, event delivery
  must retain distinct transitions so a follow-up workflow does not miss them.
- Configure one owner-approved HTTPS webhook destination per business. Restrict
  destinations and block private/link-local addresses and redirects; encrypt
  credentials. Authenticate requests with a secret header and sign the raw body
  with an event timestamp for receiver verification and replay limits.
- Start with a staff-only notification or task workflow using fictional data.
  The receiver must deduplicate event IDs before performing side effects; an HTTP
  acknowledgement proves receipt, not successful completion of every workflow step.
- Add customer messaging, marketing enrollment and more destinations only as
  separately scoped work. Do not add another voice provider or native GHL calendar
  adapter to this next slice.

This n8n slice is a documented follow-up, not implemented or enabled here.
n8n's Webhook node provides separate test/production URLs, header authentication
and raw-body handling for this receiver design:
[official Webhook node documentation](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/).

## Provider contracts

- [Private Integration Tokens](https://marketplace.gohighlevel.com/docs/Authorization/PrivateIntegrationsToken/index.html)
- [Exact contact lookup](https://marketplace.gohighlevel.com/docs/ghl/contacts/lookup-contact/index.html)
- [Contact creation and retry limits](https://marketplace.gohighlevel.com/docs/ghl/contacts/create-contact/index.html)
- [Opportunity creation](https://marketplace.gohighlevel.com/docs/ghl/opportunities/create-opportunity/index.html)
- [Opportunity search](https://marketplace.gohighlevel.com/docs/ghl/opportunities/search-opportunity/index.html)
- [Pipeline discovery](https://marketplace.gohighlevel.com/docs/ghl/opportunities/get-pipelines/index.html)
- [Opportunity field discovery](https://marketplace.gohighlevel.com/docs/ghl/locations/get-custom-fields/index.html)
