# Outbound call timeout investigation — 2026-11-06

## Provider conversation confirms voicemail delivery — owner evidence — 2026-11-07

Owner supplies ElevenLabs conversation conv_1301m6v4tsejezh9c865k9acxe4t and SIP
call ID otb_9701m6v4tsegfavah0qhm4pse8my, dated18:58Pakistan, matching the latest
attempt window and privately matched recipient. Provider shows SIP Outbound,
Successful, eight seconds and two messages, with received voicemail media and
agent-initiated ending. This establishes call creation/delivery and media for
the attempted destination; it is not human answer/two-way acceptance. No raw
recipient, caller number or transcript is retained here.

Initial admin unknown therefore did not mean no call existed. Its specific
HTTP/network/receipt cause is still unavailable. Backend final state and webhook
correlation require the local-call GET below; provider Successful alone does
not prove signed terminal reconciliation or independent carrier disconnection.
No redial, provider change, verification execution or code change ran by Codex.

## New dial attempt unknown; later webhook accepted — 2026-11-07

Owner supplies request UUID d422be38-2c87-434d-a996-74fdf62e809b and local call
UUID de077055-9585-46b2-9ef8-d034aef39c8b, created2026-11-07T13:58:06.519421Z.
Admin response is HTTP200, status unknown, terminal false, transfer not_requested.
Matching Render warning identifies dial failed with outcome_unknown true. Thus
preflight returned successfully and provider dial was attempted. It does not
establish carrier acceptance or rejection. A later outbound-webhook POST returns
HTTP200; access logs do not identify its event or call, so current state must be
read from this call's record before drawing a final-outcome conclusion.

Source classifies dial HTTPX errors, unexpected HTTP statuses, invalid response
JSON and missing/invalid receipt fields as unknown. It requires success true and
both provider IDs. The official endpoint documents IDs as optional; absent IDs
are therefore a possible classification path, not proof of this incident's cause:
https://elevenlabs.io/docs/eleven-agents/api-reference/sip-trunk/outbound-call.
Provider response/error detail is not retained by the current warning. No logging
or timeout change, Codex live query, test, deployment or call has run.

Owner-run read-only status GET, supplied unexecuted:

```sh
.venv/bin/python - <<'PY'
import getpass
import httpx

token = getpass.getpass('Render DEMO_ADMIN_TOKEN: ').strip()
if not token:
    raise SystemExit('Admin token is required.')
response = httpx.get(
    'https://api.hvacline.online/api/v1/outbound-demo/admin/calls/'
    'de077055-9585-46b2-9ef8-d034aef39c8b',
    headers={'X-Demo-Admin-Token': token},
    timeout=20,
    follow_redirects=False,
)
print(response.status_code, response.text)
PY
```

Share status and whether the recipient actually rang. If still unknown, inspect
existing ElevenLabs initiation/history/webhook deliveries and Telnyx call records
around13:58:06UTC (18:58:06Pakistan), privately matching the destination/agent.
Do not submit/replay another call or clear its active slot by guesswork.

The original investigation made no application changes, POST replay, calls, SMS,
hosted configuration changes, database queries, tests, services or readiness checks.
The commands below are for the owner and were not executed by Codex. Subsequent
owner-run SQL evidence and the authorized source change are recorded below.

## Authorized workflow/tool support — 2026-11-07 — UNVERIFIED

Owner now requests agents with workflows and tools. Local backend source removes
the workflow-node, external-tool-ID and MCP-reference bans, and allows additional
inline/native tools. Native End call remains required; the main agent's native
phone-transfer configuration retains its enabled/fixed-destination/SIP REFER gates.
The updated diagnostic no longer prints the removed presence restrictions as FAIL.
Workflow routing/overrides and external tool behavior are managed in ElevenLabs
and are not validated by these backend gates. Other base-agent, SIP, consent,
destination and quota checks are unchanged.

The workflow rejection described below is historical for c42a8b8 and remains in
effect on Render until the new backend is deployed. No tests, diagnostic execution,
hosted settings, deployment or call ran for this change. Owner commands and manual
acceptance: [Outbound runbook](outbound-demo-calling.md).

## Findings and evidence

**The timeout's root cause is unconfirmed. A separate destination configuration
blocker was confirmed by the owner and subsequently corrected by them.** At the
start of investigation, Render had `OUTBOUND_DEMO_NUMBER_POLICY=allowlist`, and
the supplied allowlist contained only the previous non-US destination, not the
attempted Sonetel US destination.

At the inspected revision, with calling enabled, `_reserve` returns HTTP403
`DEMO_NUMBER_NOT_AUTHORIZED` for that Sonetel destination before opening a database
session or contacting ElevenLabs (`service.py:148–155`). If this configuration
also applied during the incident, the request could not have created a call
through this endpoint. It does not explain a 40-second read timeout after the
route starts executing. Startup/routing/thread-pool delay could precede that
rejection. We do not have the incident's exact request time or configuration
history, so the original outcome remains unconfirmed.

**Subsequent owner evidence:** a single SELECT aggregate for the incident request
returns zero matching reservations and zero provider/SIP IDs in the selected Neon
database. This supports rejection before reservation. If this branch is the
incident's Render runtime database, with no deletion/restore, the inspected
implementation did not dial for that request because reservation commit precedes
provider work. It does not identify what caused the client to wait40seconds.

The owner subsequently suspects another database was used. The zero-row result
therefore remains inconclusive for the incident. Identify the incident's runtime
DATABASE_URL target and its environment history before drawing a no-call
conclusion. In development runtime, settings.py:104–116 selects DATABASE_URL;
DIRECT_DATABASE_URL is used for migrations and TEST_DATABASE_URL only in test.
Do not change database configuration simply to match the branch already queried.

The owner then confirms the database setting changed after the call attempt.
The original database must be queried; absence in the newly selected database
does not resolve the incident. Retain both targets and recover the previous
connection details privately. Do not change Render back or migrate/copy records
as a diagnostic shortcut. Request idempotency and call quotas are database-local,
so switching databases does not carry the previous target's protections forward.

The owner no longer has access to the previous database. Its reservation/audit
evidence is unavailable, so resolution must use retained provider/carrier
history and Render incident logs, or explicitly remain unknown if these cannot
be recovered. Search the original outbound agent/connection, not only resources
selected by the current environment. Match destination privately and actual
attempt timestamps; the supplied server startup timestamp is not itself the
call's start time. No code or new call can reconstruct missing historical facts.

| Finding | Evidence | Incident conclusion |
| --- | --- | --- |
| Current Render deployment is Free and shows main/c42a8b8 Live. | Owner-supplied Render page; local HEAD is c42a8b83951b25570e31b34e7a01af0d76d1931c. | Current source alignment is owner-reported. Incident revision still needs the corresponding Render deployment event. |
| The checked-in deployment template differs from hosting. | `render.yaml:3–10` specifies another service name, Starter, pre-deploy migration, and Uvicorn `--no-access-log`. | Do not treat the Blueprint as the effective hosted settings. Build/start commands and migration execution remain uninspected. |
| Cold start can exceed the client's timeout. | Render documents approximately one minute to wake a Free instance after 15 minutes idle. Supplied startup timestamp is 2026-11-05T20:21:20Z. | Leading hosting explanation if the POST triggered or overlapped that startup; unverified without client timestamps and Render events. Repeated later ready responses do not disprove an earlier cold start. |
| Provider work runs sequentially within the request. | `provider.py:152–184` performs agent GET, then phone-resource GET; `service.py:109–111` then calls `dial`. | Conditional explanation only if the destination passed the incident's policy. |
| Timeout budgets do not compose into a 40-second endpoint deadline. | `_request`, `provider.py:130–150`, creates a new synchronous HTTPX client for each operation with `httpx.Timeout(12)`. | Three reads near their limits can use roughly 36 seconds, plus connections and two database transactions. Twelve seconds is not a whole-request deadline; no overall endpoint deadline is implemented. |
| Database waits are not comprehensively bounded by application settings. | `connection.py:25–50` configures pool checkout/recycle/pre-ping, but no explicit connect, statement or lock timeout. `_reserve`, `service.py:160–262`, takes a tenant row lock. | Connection/lock/commit delay is possible if the request reached the database; no incident evidence establishes it. URL/server/provider settings may impose additional limits and were not inspected. |
| Successful readiness is a narrow signal. | `application.py:347–361`, `connection.py:74–82`: acquire a connection and `SELECT 1`. | Proves database reachability at those check times, not outbound schema, tenant locks, provider availability, or successful call creation. |
| The client exception is not a provider error report. | The supplied exception comes from the caller's HTTPX read. | Does not establish whether FastAPI accepted the body, whether ElevenLabs was contacted, or whether the operation stopped after disconnection. |

External references: [Render Free instances](https://render.com/docs/free),
[HTTPX timeout semantics](https://www.python-httpx.org/advanced/timeouts/).
The cold-start explanation is an inference from these documents and the supplied
hosting evidence, not an observed incident trace.

GitHub's combined status for c42a8b8 returned successful Vercel frontend/worker
statuses, with no Render status. A Render plugin exists but is not installed;
it was already suggested recently, so no duplicate suggestion was made.
No authenticated Render logs/environment readback or live ElevenLabs/Telnyx
diagnostics were available. Database absence is owner-reported as described above;
the selected branch has not been matched independently to Render's runtime target.

## Subsequent owner-run attempt — terminal failed

The owner supplies a separate POST result with request UUID
`e0b4c6ac-5089-4360-9660-e7e8aab6598d`, local call UUID
`d72bdcf4-503e-4687-82b4-ddef0d3d5b9d`, created_at
`2026-11-05T20:47:26.383853Z`, HTTP200, status failed, terminal true and
transfer_status not_requested. This attempt did not produce a client timeout.
It establishes an application-level recorded failure, not carrier success, and
does not resolve the earlier request in the unavailable database.

At the inspected revision, preflight failure or a classified provider dial
rejection can produce this response (`service.py:103–139`,
`provider.py:152–230`). A signed provider failure arriving before the HTTP
response can also advance the record to failed (`service.py:425–469`). The
response alone cannot distinguish these paths or establish that no provider call
was created. Authentication/destination checks and reservation were passed for
the recorded attempt; a generic API/allowlist rejection would have a different
response contract.

Next owner evidence: Render warning for this local call UUID around the stated
UTC timestamp (`2026-11-06 01:47:26` Pakistan time). `Outbound demo preflight
failed` establishes failure before dial; `Outbound demo dial failed` places the
failure in submission. The warning does not retain the underlying reason, so
provider HTTP diagnostics/configuration readback may still be required. If no
warning exists, inspect the saved record's provider IDs/event digest and the
existing provider initiation-failure/webhook history. No additional POST is
needed to investigate this record. Codex did not execute this attempt.

## Latest evidence — preflight failed before dial

Owner supplies the matching Render warning:
`Outbound demo preflight failed (outcome_unknown=False, call_id=...)`, followed
by the admin POST HTTP200. This identifies the latest attempt's failure phase.
`service.py:107–111` calls dial only after preflight returns, so no dial POST was
issued for this attempt. Its failure is in the provider GET/configuration checks
(`provider.py:152–184`), not Sonetel receiving/SIP termination. The original
timed-out request is a separate unresolved incident.

The precise cause remains unavailable because all preflight HTTP/network/JSON
failures and validator mismatches collapse to the same exception. Next is the
GET-only diagnostic below, not another call or a speculative configuration fix.

### Owner diagnostic result — workflow guard — 2026-11-07

Owner runs the file-based diagnostic successfully: agent and phone GETs both
return HTTP200. All printed comparisons pass except agent no_workflow_nodes.
At that revision, validate_agent rejects any nonempty workflow.nodes. This identifies a
blocker for the supplied settings, consistent with the earlier preflight
failure; incident/runtime input equivalence and historical causation are not
independently established.

The output does not disclose node types, settings or edges. Even a default
start-only graph fails that blanket check. Owner subsequently authorizes workflow
and tool support as recorded above. Workflows can override base-agent configuration
and introduce tools or transfer routing; their behavior is now managed in the
hosted configuration:
https://elevenlabs.io/docs/eleven-agents/customization/agent-workflows.
The diagnostic itself made no hosted change or call.

### Owner-run GET-only preflight comparison

Run from the repository at the same revision as Render. This command sends
only two GET requests to ElevenLabs and never invokes the call service. Enter
the current Render values privately. It prints HTTP status/timing and check
names only; no returned configuration, credentials or recipient values.
It compares the configuration with the main agent's native phone transfer disabled:
Render OUTBOUND_DEMO_TRANSFER_ENABLED must be false. Workflow and external-tool
transfer behavior is not covered by this comparison. For enabled transfer, stop and
inspect the existing transfer validator instead of interpreting this comparison.
Use the actual Render maximum-duration value, or180 only if that setting is
unset. A local successful GET does not prove Render had the same network
connectivity at the failure time. This diagnostic is supplied unexecuted.

```sh
PYTHONPATH=apps/backend/src .venv/bin/python scripts/diagnose-outbound-preflight.py
```

Run the command above as one line from the repository root. The script prompts
for current Render values; hidden inputs do not echo. Keep the diagnostic in a
file: pasting a fragment into zsh causes shell syntax errors, while running an
interactive Python script through a stdin heredoc prevents `input()` from
reading answers. This script has not been executed by Codex.

Share HTTP status/timing and FAIL check names only. Do not share prompts,
response bodies, exception text or credential inputs. If all checks pass, compare
the entered values/revision with the incident's Render configuration and inspect
Render-to-ElevenLabs network/HTTP diagnostics; do not treat a passing local
comparison as a successful call or a reason to bypass preflight.

## Exact request path at c42a8b8

Paths below are relative to `apps/backend/src/insurance_operations/`, except
where stated otherwise. Line ranges describe the inspected source.

| Stage | File, function and lines | Behavior |
| --- | --- | --- |
| Application registration | `api.py:9–14`; `application.py:create_app:133–138,195–202` | Creates synchronous SQLAlchemy sessions and registers the outbound router. Settings load from environment/.env via `settings.py:36–42`. |
| HTTP correlation and errors | `application.py:add_correlation_id:260–273`; `handle_api_error:233–237`; `request_validation_error_handler:239–258`; `errors.py:38–52` | Sets a UUID correlation response header; serializes ApiError and validation errors. Middleware does not log acceptance, elapsed time, completion or disconnect. |
| Admin authentication | `telephony/outbound/routes.py:admin:63–80`; `create_admin_call:110–114` | Requires strong `X-Demo-Admin-Token` and constant-time comparison, independently of the general sandbox gate. No customer MFA/SMS flow is used by this admin route. |
| Input validation | `telephony/outbound/schemas.py:DemoCallInput:42–65`; `destinations.py:11–24` | UUID request key, normalized E.164 destination, bounded scenario including cooling, literal boolean true consent and exact outbound-demo-v1 version. Unknown fields reject. |
| Calling gates | `telephony/outbound/service.py:_reserve:144–155`; `settings.py:87–142` in the outbound directory | Checks enabled state and destination policy. Enabled configuration requires development environment, dedicated agent, SIP resource, API key and separate strong state/webhook secrets. |
| Tenant resolution | `telephony/outbound/service.py:_agency:74–82`; `actors.py:resolve_development_actor:30–59` | Resolves one active development actor/membership/business. |
| Persistent reservation | `telephony/outbound/service.py:_reserve:157–262`; `database/models/outbound_demo.py:17–49` | HMAC payload/owner/destination, tenant FOR UPDATE lock, replay/conflict checks, active slot, daily/rolling quotas/cooldown, reservation and audit in one committed transaction. Raw destination is not saved in this table. |
| Provider preflight | `telephony/outbound/provider.py:validate_agent:40–120`; `preflight:152–184` | Reads and validates agent, prompt, end-call tool, privacy, maximum duration, webhook assignment and SIP caller/resource/Telnyx TLS/digest settings before dialing. No direct Sonetel or Telnyx API call occurs here. |
| Provider creation | `telephony/outbound/provider.py:dial:186–230` | POSTs to ElevenLabs /v1/convai/sip-trunk/outbound-call. Sends local call ID as outbound_demo_call_id dynamic variable; expects success plus conversation_id/sip_call_id. No retry loop. |
| Result persistence | `telephony/outbound/service.py:create:103–139` | Known pre-creation failure becomes failed; ambiguous dial failure becomes unknown. Successful receipt binds provider IDs and changes reserved to dialing, unless a webhook already advanced it. A second transaction must commit before the response returns. |
| Response | `telephony/outbound/service.py:_response:497–518`; `schemas.py:68–88`; `routes.py:110–114` | Default HTTP200 with durable status, local call UUID, terminal flag and generic message; provider failure can also return HTTP200 with failed/unknown status. |
| Reconciliation | `telephony/outbound/service.py:webhook:324–340`; `apply_provider_data:342–495`; `routes.py:160–179` | Signed events can bind by provider conversation ID or local dynamic variable and finalize a reservation even before the dial HTTP receipt is persisted. |

The synchronous route uses FastAPI's thread pool; synchronous HTTPX/SQLAlchemy
therefore occupy a request worker, rather than directly blocking the async event
loop. Worker exhaustion could queue requests, but no evidence establishes it.
See [FastAPI execution behavior](https://fastapi.tiangolo.com/async/).
Database transactions end before provider network calls, so the tenant lock is
not held throughout dialing. The endpoint waits for preflight and the provider
creation receipt, not the full conversation. No unnecessary conversation polling
loop was found. The provider's precise response timing relative to ringing is
not established by this source. The 25-second default ringing timeout
(`outbound/settings.py:40`, `provider.py:195–197`) is a carrier-call parameter,
not the API read timeout or the 180-second conversation ceiling.

## Original outcome and replay protection

If the incident used the current allowlist without the Sonetel destination,
there should be no reservation or dial from this request. Otherwise, a client
timeout can occur after reservation, after provider creation, or before the
receipt transaction commits. The call may have been created in those cases.

| Stored evidence | What can safely be concluded |
| --- | --- |
| No row for the request in the actual incident database/business | No committed reservation found. This implementation commits before dialing, so absent deletion/restore/wrong target or different deployed behavior, it did not dial. Still confirm original execution is no longer pending before considering any new request. |
| reserved, no provider IDs | Reservation exists; could be preflight/crash, in-flight dial, lost receipt or failed receipt persistence. Does not prove no call. |
| unknown | Dial outcome is deliberately unresolved. Do not redial or release the active slot based on age alone. |
| dialing or provider IDs present | Provider creation/binding evidence exists, not proof the recipient answered. |
| failed/rejected/unanswered | Inspect provider history: a preflight failure is failed without dialing, while provider lifecycle failures can also produce failed. Status alone cannot distinguish them. |
| completed/disconnected and signed event digest | Stronger lifecycle evidence, but carrier records remain the evidence of actual ringing/answer and ended legs. |

Existing protection: unique `(agency_id, request_id)` plus a tenant lock and
payload/owner fingerprint (`service.py:160–181`, model lines20,46–47). Matching
persisted replays return existing status before any new provider operation;
changed payload/owner returns409. Failed reservations still consume quotas;
reserved/unknown slots do not automatically expire or redial.

Limits: there is no provider idempotency header/key in the dial request. The
dynamic variable is correlation evidence, not provider deduplication. Reservation
commit before dialing plus no retry protects the local flow, but a crash between
provider creation and receipt persistence needs reconciliation. The code does
not catch database failures in either transaction; provider error classification
does not cover them. Safe production error handling must preserve the uncertain
outcome after a possible dial.

**Do not use the runbook's POST retry as a status lookup.**
`docs/outbound-demo-calling.md:454–457` suggests rerunning after timeout. If the
first request never reserved, that POST can create the first call, particularly
after fixing this allowlist. Destination/enabled gates also run before replay
lookup. The admin GET requires the local call UUID, not the request UUID
(`routes.py:116–118`). The existing request-UUID lookup (`routes.py:156–158`)
requires website authentication/ownership and is not an admin recovery route.

## Smallest fix and missing protections

For the confirmed destination blocker, keep `OUTBOUND_DEMO_NUMBER_POLICY=allowlist`
and replace the allowlist with the consented Sonetel destination in canonical
`+1…` format, or append it with a comma if both destinations should remain
approved. No code change or quota increase is required. Do not save/deploy an
environment change until incident evidence is captured if a request could still
be pending. The change does not authorize another call or replay.

For a private admin test, confirm `OUTBOUND_DEMO_ENABLED=true`,
`OUTBOUND_DEMO_WEBSITE_ENABLED=false`, `OUTBOUND_DEMO_TRANSFER_ENABLED=false`,
and `APP_ENVIRONMENT=development`. Preserve existing dedicated agent/resource
IDs, API key, admin token, state secret and webhook secret. The Sonetel recipient
is a destination, not OUTBOUND_DEMO_PHONE_NUMBER_ID or the caller identity.
The latter must remain the existing ElevenLabs SIP resource. Public mobile/SMS
variables are not required for the admin route. Telnyx US destination permission,
credit, outbound profile and Sonetel receiving configuration need separate
confirmation; an allowlist entry does not prove carrier reachability.

During this investigation the owner reports adding the Sonetel destination and
completing the Render deployment. That change has not been inspected
or independently verified. It does not resolve the original request's outcome;
a replay after this change can create a call if the original never reserved.

For the timeout, choose a fix only after locating the stalled phase:

- Confirmed Free-instance wake delay: use an always-on paid web-service instance
  for production calling. This reuses the existing application. Changing
  render.yaml alone does not establish the hosted plan changed. Increasing the
  client timeout alone does not establish reliable production behavior.
- Confirmed database delay: bound connection, statement and lock waits using the
  existing engine/session configuration. Bound and classify pre-dial failure
  separately from persistence failure after a possible dial. Do not blindly
  increase the pool or hold database locks across provider requests.
- Confirmed provider delay: define an explicit measured request budget for the
  existing preflight/create flow and finite operation timeouts. Never retry an
  ambiguous dial. Do not remove required preflight controls or assume the
  provider's 12-second setting is a total deadline. An in-process background
  task would not provide durable call delivery; no queue redesign is justified
  by current evidence.

Small diagnostic/recovery improvements are warranted independently of the
eventual latency fix, but are proposals only:

- Authenticated admin GET by request UUID, reusing tenant-scoped lookup; update
  the runbook to GET before any replay, with404 explicitly meaning unresolved
  until original processing has stopped.
- Sanitized request acceptance/rejection, reservation commit, each provider
  operation start/end, result commit/failure and HTTP completion logs. Include
  request/local call/correlation IDs, deployment revision, elapsed time,
  allowlisted reason code, HTTP status and exception class, without headers,
  destination, bodies, transcript or exception text. Configure an appropriate
  application logger so informational events are emitted.
- Preserve provider HTTP status/safe reason/phase instead of collapsing all
  failures. `OutboundProviderError` holds only outcome_unknown
  (`provider.py:24–27`); `create:113–116` logs only phase/unknown/local call ID.
  No success/start log exists. The audit's correlation UUID is newly generated,
  not the HTTP correlation (`service.py:307–321`). No durable failure phase,
  elapsed time or provider error code is retained.

No speculative fix was implemented. Runtime acceptance remains unverified.

## Owner-run diagnosis commands and manual checks

First preserve Render Events/logs before applying an environment change. Record
the client POST start/end in UTC (including the original timezone), the deployment
serving it, and its spin-down/spin-up/restart/OOM events. Inspect the window from
several minutes before that POST through at least five minutes afterward,
including request/proxy logs for the exact path and instance. Search for
`Outbound demo`, Python tracebacks, SQLAlchemy/psycopg failures and webhook
`DEMO_EVENT_UNBOUND`/401/422/503 responses. Existing logs may not contain the
request UUID because it was not logged. Confirm Settings' actual build/start
commands and the incident's environment revision; current masked variable names
do not reveal their values.

From the repository, the following owner-run command performs bounded,
read-only SELECTs against the incident's actual database. Enter Render's runtime
DATABASE_URL privately in standard postgresql:// form, not a test database URL.
Use an authorized read-only database credential if available. Do not paste the
connection string into chat or shell arguments. No application module is imported.

```sh
.venv/bin/python - <<'PY'
import getpass
import json
from uuid import UUID
import psycopg
from psycopg.rows import dict_row

request_id = UUID('c3695634-8ef0-4c4a-bd9b-6a71f0bdf107')
dsn = getpass.getpass('Incident runtime PostgreSQL URL (hidden): ')
try:
    with psycopg.connect(dsn, connect_timeout=10, sslmode='require',
                         row_factory=dict_row,
                         application_name='hvacline-incident-readonly') as connection:
        connection.read_only = True
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '5s'")
            cursor.execute("SET LOCAL lock_timeout = '3s'")
            cursor.execute('''
                SELECT id, status, transfer_status, created_at, finalized_at,
                       conversation_id, sip_call_id,
                       last_event_hash IS NOT NULL AS has_event_digest
                FROM outbound_demo_calls WHERE request_id = %s
                ORDER BY created_at LIMIT 10
            ''', (request_id,))
            print('calls:', json.dumps(cursor.fetchall(), default=str))
            cursor.execute('''
                SELECT a.event_type, a.occurred_at
                FROM audit_events a
                JOIN outbound_demo_calls c
                  ON a.agency_id = c.agency_id
                 AND a.details->>'outbound_demo_call_id' = c.id::text
                WHERE c.request_id = %s
                ORDER BY a.occurred_at LIMIT 20
            ''', (request_id,))
            print('audit:', json.dumps(cursor.fetchall(), default=str))
        connection.rollback()
except psycopg.Error as error:
    raise SystemExit(f'Read-only lookup failed: {type(error).__name__}; '
                     f'SQLSTATE={error.sqlstate or "unavailable"}') from None
PY
```

Keep returned opaque IDs private and verify the result belongs to the configured
business. This query deliberately excludes destinations, customer data, hashes,
audit bodies and transcript contents. Empty results in a different database
branch do not resolve the incident.

If a local call UUID is recovered, the owner may read durable status with this
GET-only command. It makes no provider request and performs no reconciliation.
The request UUID above must not be substituted for the local call UUID.

```sh
.venv/bin/python - <<'PY'
import getpass
from uuid import UUID
import httpx

call_id = UUID(getpass.getpass('Recovered local call UUID: '))
token = getpass.getpass('Demo admin token: ')
try:
    with httpx.Client(timeout=httpx.Timeout(90, connect=10),
                      follow_redirects=False) as client:
        response = client.get(
            f'https://api.hvacline.online/api/v1/outbound-demo/admin/calls/{call_id}',
            headers={'X-Demo-Admin-Token': token},
        )
    print('HTTP', response.status_code)
    if response.status_code == 200:
        data = response.json()
        print({key: data.get(key) for key in
               ('id', 'status', 'transfer_status', 'created_at', 'terminal')})
except httpx.HTTPError as error:
    raise SystemExit(f'Status GET failed: {type(error).__name__}') from None
PY
```

In ElevenLabs, inspect the existing outbound agent's call history and initiation
failures in the exact UTC window. Correlate returned conversation_id/sip_call_id
or dynamic variable outbound_demo_call_id; the original request UUID itself is
not sent to the provider. Inspect latency/status/request ID for the two preflight
GETs and outbound POST if provider request diagnostics/support can supply them.
Check signed webhook delivery attempts/statuses. Zero-day retention is required
by source, so later absence from history alone cannot prove no call occurred.

In Telnyx, inspect existing outbound connection CDRs and SIP Call Flow for the
same window: INVITE time, SIP response, ringing/answer/end and any active leg.
Use the Sonetel destination privately to narrow the search, then correlate with
provider call IDs and timestamps. Inspect Sonetel incoming history as supporting
receipt evidence. No matching Telnyx record alone cannot distinguish an earlier
preflight failure from a provider request that never reached the carrier.
Do not use refresh/carrier-ended POSTs during this read-only diagnosis.

For an approved later implementation, existing mocked unit specifications can be
run without placing calls:

```sh
DEMO_SANDBOX_ENABLED=false PYTHONPATH=apps/backend/src .venv/bin/python -m pytest --import-mode=importlib tests/test_outbound_demo.py
```

After separately confirming an isolated disposable TEST_DATABASE_URL, the
existing database replay/concurrency/unknown/webhook specifications are:

```sh
APP_ENVIRONMENT=test DEMO_SANDBOX_ENABLED=false PYTHONPATH=apps/backend/src .venv/bin/python -m pytest --import-mode=importlib tests/database/test_outbound_demo_calls.py
```

Database fixtures downgrade/rebuild the target (`tests/database/conftest.py:30–45`);
never run that command against runtime data. Existing test coverage includes
provider timeout without retry (`tests/test_outbound_demo.py:286–301`), persistent
unknown/replay and preflight failure (`tests/database/test_outbound_demo_calls.py:
430–446`), and webhook-before-receipt binding (lines754–763). No tests ran here.
A later fix also needs mocked delayed preflight/receipt, pre/post-dial database
failure, admin request-ID recovery and sanitized timing-log cases as appropriate.

The missing incident evidence is specifically: client UTC timestamps; Render
incident deployment/environment/start command and request routing/spin-up logs;
the reservation/audit lookup above; database connection/lock/commit timing at
that time; ElevenLabs request latency/status/IDs and webhook delivery history;
and Telnyx CDR/SIP evidence. Without those, a definitive timeout root cause or
original-call outcome would be invented.
