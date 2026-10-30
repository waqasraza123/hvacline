# Inbound phone webhook repair — 2026-10-30

Focused automated checks have passed; **live Render acceptance remains
UNVERIFIED**. The owner authorized executing the checks and treating the current
database as disposable. An existing isolated test target was reachable, so the
current runtime database was preserved. No deployment, outbound call or provider
setting change was performed. The owner reports Render revision `ab69756`, successful
Telnyx → ElevenLabs SIP routing, enabled/registered phone routes, repaired
initiation authorization, and 422 on both webhooks. The owner dials with `+`;
ElevenLabs displays caller/receiver numbers without it. Neither observation proves
the exact webhook JSON. No real request body or validation field report was
available during the initial repair. Subsequent read-only ElevenLabs inspection
confirmed that initiation fetch is enabled with an Authorization header, recent
failed calls lack `phone_inbound_call_id`, and the system called-number variable
has no `+`. An initiation reconstructed from the latest call's metadata passes
the repaired schema and fails the legacy E.164 called-number check. Reconstructing
its transcription event reproduces the missing-UUID post-call 422. No raw payload,
phone number, secret, transcript or provider error text was logged or saved.
These reconstructions do not prove the exact original HTTP request bodies.

## Executed checks

- Focused adapter/provider/post-call suite: **76 passed**.
- Full non-database suite with explicit test sandbox configuration: **214 passed**,
  with two existing duplicate OpenAPI operation-ID warnings.
- All eight changed Python files pass Ruff format/lint and targeted mypy using
  `--explicit-package-bases`. Formatting/Unicode-test spelling and the dynamic
  settings test-helper annotation were corrected during execution.
- All four phone database suites: **23 passed together in 17.44 seconds** on a
  freshly created local PostgreSQL database, dropped afterward. This exercised
  200 initialization with the persisted UUID, canonical replay, tenant rejection,
  quotas, signed finalization/failure events, audit and diagnostic privacy.
- The first remote database run passed 21 cases and exposed disabled diagnostic
  logging plus the local sandbox setting. Preserving existing loggers in
  Alembic's `fileConfig` fixed the logging case. The two corrected cases passed
  remotely after an intervening SSL socket timeout during migration setup.
  Current application data was not erased or migrated.
- All 13 post-call validation tests also pass after applying Alembic's logging
  configuration to an already-imported validation logger.
- Broader repository checks remain red outside this repair: 30 untouched Python
  files need formatting, 335 Ruff findings span 46 untouched files, and full
  mypy with explicit package bases reports 47 errors in six untouched files.
  Plain mypy collection first fails on duplicate test module names. These were
  not hidden or expanded into unrelated source changes.

The existing editable environment pointed at an old checkout and lacked the
already-pinned websockets dependency. Installing the repository's existing
`.[dev]` dependencies corrected the environment without changing manifests.
The private local dotenv's invalid sandbox boolean affected broader API tests;
an explicit `DEMO_SANDBOX_ENABLED=false` isolates those tests without editing
runtime configuration.

## Findings and contract comparison

ElevenLabs documents an inbound initiation JSON object with `caller_id`,
`called_number`, `agent_id`, `call_sid`, and `conversation_id`; SIP may additionally
send `call_id` and `sip_headers`. The response is a
`conversation_initiation_client_data` object containing the required custom
dynamic variables. The existing SIP schema supports all these documented fields;
there is no evidence for changing their names, making conversation identity
optional, or accepting arbitrary fields. Number examples include `+`, but the docs
do not establish the formatting of this particular failed request.
[Official initiation contract](https://elevenlabs.io/docs/eleven-agents/customization/personalization).

The initiation path is `sip.py` → `TelnyxSipAdapter.verify_initiation` →
`SipConversationInitiation` → `TelephonyService.initialize_phone_call`. Before the
change, a digit-only **called** number fails `validate_e164` and is translated to
`422 PHONE_INITIATION_INVALID`. A digit-only **caller** number passes the request
schema and becomes absent in the adapter; caller formatting alone does not
explain an initiation 422. Missing required fields, null/wrong types, unknown
fields, malformed JSON and excessive field lengths can independently cause the
same 422. The adapter previously hid the validation details. Authentication gives
401, wrong agent 403, missing tenant-owned active route 404, binding/policy
conflicts 409 and quotas 429; those are different failures.

The missing `phone_inbound_call_id` agent error is consistent with initiation
failing before returning the backend-created UUID. It is not evidence that a
placeholder/default dynamic variable should be added. A successful initialization
already persists one call and returns that call's UUID and stored duration.

The post-call path is `ingress.py` →
`ElevenLabsPhoneProvider.verify_post_call_webhook` →
`PhoneReceptionistService.finalize_post_call` → `normalize_post_call`. Size, fresh
HMAC over the original bytes and configured agent are checked before contract
diagnostics. Verification failures give 403. The normalizer supports:

| Event | Required application correlation | Relevant 422 cause |
| --- | --- | --- |
| `post_call_transcription` | `data.conversation_initiation_client_data.dynamic_variables.phone_inbound_call_id` must be a UUID, plus `data.conversation_id` | Missing initiation data/UUID, malformed transcript or existing transcript limits. This can follow a failed initialization. |
| `call_initiation_failure` | For SIP: `data.metadata.type="sip"`, `data.metadata.body.call_sid`, plus `data.conversation_id` | Missing/wrong metadata structure or call reference. It does **not** require the dynamic variable or a transcript. |
| Other types, including audio | Unsupported by this endpoint | Rejected event type; audio remains disabled. |

The documented SIP failure shape is already supported. Its provider phone numbers
and free-text failure reason are not E.164-validated or persisted by this path, so
their display formatting cannot explain a post-call 422. A structurally valid
failure for an initialization that never persisted reaches a **409** context
rejection, not 422. The documented examples discuss provider-specific outbound
failures; an inbound pre-conversation failure must be diagnosed from actual safe
field errors rather than assuming it has the same shape.
[Official post-call contracts](https://elevenlabs.io/docs/eleven-agents/workflows/post-call-webhooks).

## Precise changes and retained boundaries

- `sip_schemas.py`: normalize only an ASCII digit string of 8–15 digits, starting
  with 1–9, by adding `+`, then run the existing E.164 validator. Existing canonical
  numbers pass unchanged. No country code, region, punctuation, SIP URI, integer
  coercion or alternate field name is inferred. Backend routing must still find
  the exact canonical number in the configured actor's active business.
- `providers/telnyx_sip.py`: apply the same normalization to caller contact
  metadata; retain absent/anonymous-caller handling and agent/auth checks. Log
  sanitized schema failure paths/types before the existing 422 response.
- `webhook_validation.py`: bounded diagnostic records with at most 20 field
  path/type entries, no values, messages, context, raw body or exception traceback.
  Unknown JSON keys and SIP-header names become `*`; malformed JSON uses `$`.
- `phone_service.py`: identify existing post-call validation branches with safe
  paths/types, including absent UUIDs and SIP failure metadata. Event acceptance,
  correlation, state transitions, historical fingerprints, replay conflicts,
  consent/readback, transcript limits and audit transactions are preserved.
  A non-string metadata provider type now produces the intended 422 instead of
  failing set membership with an unhashable-value exception.
- `migrations/env.py`: use `disable_existing_loggers=False` when loading logging
  configuration, so migrations in the same process do not silence the validation
  logger. This changes logging setup only, not schema or migration revisions.
- Regression specifications extend `test_telnyx_sip_provider.py` and
  `database/test_telnyx_sip_ingress.py`; `test_phone_webhook_validation.py` covers
  post-call contracts and diagnostic privacy. Existing phone provider,
  receptionist, quota/concurrency, booking-survives-disconnect and tenant tests
  remain relevant.

There is no schema, dependency or environment-variable change. No migration is
required for this repair. The precise production field rejection remains
**unconfirmed** until safe validation diagnostics or the 422 field report is
available. Unknown fields remain forbidden; do not relax validation based on an
unseen payload.

Previously persisted calls with an absent caller retain strict replay comparison;
normalization can expose a caller mismatch on an in-flight retry across rollout.
Use a new inbound call for acceptance and existing audited reconciliation for
old calls; do not rewrite their identity or weaken replay checks.

## Reproducible verification commands

Use the existing Python 3.13 development environment and dependencies, from the
active checkout:

```bash
cd /Users/mc/development/hvacline
.venv/bin/python -m pytest --import-mode=importlib tests/test_telnyx_sip_provider.py tests/test_phone_webhook_validation.py tests/test_phone_conversation_provider.py tests/test_telephony_provider.py --tb=short
DEMO_SANDBOX_ENABLED=false .venv/bin/python -m pytest --import-mode=importlib tests --ignore=tests/database --tb=short

phone_files=(
  migrations/env.py
  apps/backend/src/insurance_operations/telephony/phone_service.py
  apps/backend/src/insurance_operations/telephony/providers/telnyx_sip.py
  apps/backend/src/insurance_operations/telephony/sip_schemas.py
  apps/backend/src/insurance_operations/telephony/webhook_validation.py
  tests/test_telnyx_sip_provider.py
  tests/test_phone_webhook_validation.py
  tests/database/test_telnyx_sip_ingress.py
)
.venv/bin/python -m ruff format --check "${phone_files[@]}"
.venv/bin/python -m ruff check "${phone_files[@]}"
.venv/bin/python -m mypy --explicit-package-bases "${phone_files[@]}"
```

Database fixtures truncate conversations, downgrade/rebuild the target, then
downgrade it again. Export `TEST_DATABASE_URL` using the existing private setup
and confirm it is an **isolated disposable PostgreSQL database**, distinct from
development and production. Only then run:

```bash
APP_ENVIRONMENT=test GOOGLE_CALENDAR_ENABLED=false BOOKING_EMAIL_ENABLED=false DEMO_SANDBOX_ENABLED=false PGCONNECT_TIMEOUT=15 .venv/bin/python -m pytest --import-mode=importlib tests/database/test_telnyx_sip_ingress.py tests/database/test_phone_receptionist_flow.py tests/database/test_telephony_provider_ingress.py tests/database/test_telephony_api.py --tb=short
```

The successful local execution used `.venv/bin/python
/private/tmp/hvacline_phone_local_checks.py`, a temporary credential-free runner
that creates a unique local database, supplies isolated test URLs with SSL
disabled for loopback only, executes the command above, and drops its database in
`finally`. It uses an already-running local PostgreSQL server and starts no new
service. No real credentials or webhook payloads are in that runner. The normal
test configuration continues requiring SSL where configured.

## Owner manual acceptance — NOT RUN

1. After an explicitly authorized backend rollout, confirm the deployed revision
   contains this repair. Keep the existing bearer and HMAC secrets private. No
   Telnyx settings, agent variables or frontend changes are required by this
   patch.
2. Make a new inbound call. Inspect the initialization webhook's status/response
   privately. It must be 200 with `Cache-Control: no-store` and this shape:

   ```json
   {
     "type": "conversation_initiation_client_data",
     "dynamic_variables": {
       "phone_inbound_call_id": "<persisted InboundCall UUID>",
       "phone_max_duration_seconds": 180
     }
   }
   ```

   The duration shown is an example; it must match that call's persisted setting.
   The UUID must come from the stored call in the correct business. Never paste a
   sample UUID into the agent. Confirm the call/receipt in Operations, tools use
   this UUID and the same conversation, and the missing-variable error disappears.
3. If initialization still returns 422, collect only `PHONE_INITIATION_INVALID`
   and the `insurance_operations.telephony.webhook_validation` warning's paths and
   types. `called_number/value_error` identifies number validation; a known
   field/`missing` identifies absence; `*/extra_forbidden` identifies an unknown
   key. Inspect an unknown key privately against the official contract before
   proposing any schema change. Do not share/log its value or a raw payload.
4. Confirm the signed post-call request returns 200 and the call reaches its
   audited terminal state. For 422, collect only the error code and safe path/type
   entries. Distinguish transcription's missing UUID from failure metadata or
   unsupported event type. An unbound failure 409 must not create a synthetic call
   or cross-tenant association.
5. With provider-supported redelivery on a controlled initialized call, confirm
   duplicate signed events return 200 without extra records; changed identity
   remains rejected. Check wrong/missing auth, another business's number and quota
   boundaries remain rejected. Confirm refusal creates no confirmed intake and a
   separately confirmed appointment survives disconnect in Operations.
6. Confirm warnings contain only paths/types, with no phone numbers, caller
   identifiers, secrets, transcript, payload values or tracebacks. Keep evidence
   to statuses, error codes and sanitized validation entries.
