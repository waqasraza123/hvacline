# Outbound AI demo calling with human transfer

Implementation and all runtime behavior are **UNVERIFIED**. No tests, builds,
migrations, services, provider edits, deployments or telephone calls were run.
Do not enable the website until an authorized real outbound call and a real
human transfer pass the acceptance procedure below. Existing inbound SIP,
browser Voice/Chat and booking use their existing agents and routes.

## November 5 website announcement and completion — November 2, 2026

The owner requested the public announcement **Inbound & outbound calling —
coming November 5, 2026**. The homepage now carries it in the hero, Calling
navigation, a dedicated section and the FAQ. The date is shared through
`apps/web/src/features/outbound-demo/contracts.ts` and uses a semantic `time`
element. The announcement is visible with every calling flag disabled and needs
no API configuration or migration to render. It does not enable calling on the
date automatically. With calling unavailable, visitors see the two upcoming
calling options and a browser Voice link; no phone/consent form is displayed.
An existing request still exposes its status recovery controls when new calls
are disabled. The approved-number form appears only after the existing frontend
and backend activation gates pass.

Completion repairs preserve uncertain transfer evidence across later final
events and refreshes. A late dial error cannot overwrite lifecycle evidence
already delivered by a signed webhook. Invalid nested transcript/tool shapes
return a bounded 422 before changing a call. Frontend status reads do not overlap.
The bridge explicitly marks requests rejected before creation, so a visitor can
correct an unauthorized number or quota-rejected form and renew consent.
Ambiguous failures keep the request locked and its recovery key intact; no
automatic retry or redial was added. Focused regression cases are written but
unexecuted.

This work is local and **UNVERIFIED**; no commit, push, hosting deployment,
verification command, migration, provider edit or telephone call was performed.
Source formatters were applied to the changed source files only. The provider,
migration and real-call prerequisites below still apply to live activation.
The public November 5 announcement is the requested release plan, not recorded
live-call acceptance. Outbound API and conversation status contracts were
rechecked against the linked official documentation on November 2.

Owner commands for this completion (not run):

```sh
python -m pytest tests/test_outbound_demo.py
npm run test:web -- src/app/api/outbound-demo/route.test.ts
npm run typecheck:web
npm run build:web
python -m ruff check apps/backend/src/insurance_operations/telephony/outbound tests/test_outbound_demo.py tests/database/test_outbound_demo_calls.py
python -m mypy --explicit-package-bases apps/backend/src/insurance_operations/telephony/outbound
```

After independently confirming a disposable isolated `TEST_DATABASE_URL`:

```sh
APP_ENVIRONMENT=test python -m pytest tests/database/test_outbound_demo_calls.py tests/database/test_migrations.py tests/database/test_table_ownership.py
```

Manual website checks: with gates false, confirm the hero, calling section and
FAQ show November 5, 2026 at mobile and desktop widths. Follow the hero and
navigation anchors with keyboard focus; confirm the browser Voice link retains
the existing sign-in/microphone-consent flow. Confirm no phone number or inactive
form appears. With an approved private preview, reject an unapproved recipient,
correct the form and renew consent; confirm double-clicks produce one call.
Simulate a lost response using mocked requests: the same saved request remains
locked with status recovery after reload, including when new calling is disabled.
Confirm status reads never submit calls. For actual calling, follow the explicitly
authorized acceptance sequence below, including transfer carrier-leg controls.

## Provider contract and unresolved capability

Official sources inspected November 1, 2026:

- [ElevenLabs outbound SIP API](https://elevenlabs.io/docs/api-reference/sip-trunk/outbound-call)
  and [public OpenAPI](https://api.elevenlabs.io/openapi.json):
  `POST /v1/convai/sip-trunk/outbound-call`, `xi-api-key`, `agent_id`,
  `agent_phone_number_id`, `to_number`, initiation dynamic variables and
  `telephony_call_config.ringing_timeout_secs`. A successful response contains
  `success`, `conversation_id` and `sip_call_id`; it does not establish an answer.
- [ElevenLabs SIP configuration](https://elevenlabs.io/docs/eleven-agents/phone-numbers/sip-trunking)
  documents `sip.telnyx.com` as an outbound hostname, digest authentication,
  TCP/TLS and codec/encryption configuration.
- [ElevenLabs transfer tool](https://elevenlabs.io/docs/eleven-agents/customization/tools/system-tools/transfer-to-number)
  supports fixed destinations with `transfer_type: sip_refer`; the trunk must
  accept REFER. SIP REFER has no warm introduction.
- [Telnyx outbound profiles](https://developers.telnyx.com/docs/voice/sip-trunking/configuration/outbound-voice-profiles)
  define permitted destinations, channels, maximum destination rate and daily spend.
- [Telnyx external transfers](https://developers.telnyx.com/docs/voice/sip-trunking/features/external-transfers)
  describe active **inbound** matching and a Diversion header. That flow does not
  establish that REFER on an ElevenLabs-originated outbound dialog will work.
- [ElevenLabs signed post-call events](https://elevenlabs.io/docs/eleven-agents/workflows/post-call-webhooks)
  include transcription and SIP initiation failures. The adapter reuses the
  existing timestamped HMAC-SHA256 verification, five-minute tolerance and agent binding.

The agent's real `conversation_config.conversation.max_duration_seconds` is
checked before every dial and must be at most the configured limit, never above
180. **This does not prove that a transferred carrier leg ends at that deadline.**
No documented Telnyx trunk control establishing that guarantee was found.
`OUTBOUND_DEMO_CARRIER_LIMIT_CONFIRMED` is an owner attestation, not a timer or a
Telnyx API feature. Leave it false until Telnyx confirms and acceptance proves a
carrier-enforced total duration limit, including transferred legs. Transfer is
blocked without this prerequisite. A prompt, website timer, SIP session refresh
timer or daily spending cap is not a replacement for that limit.

## Telnyx dashboard

1. Open **Voice → SIP Trunking → SIP Connections**. Inspect the existing inbound
   connection and assigned number first. Preserve its number association, inbound
   FQDN, routing, source allowlist and transport. Do not replace it with Call Control.
2. Use an outbound credential-authenticated SIP connection in the **same account**
   if the existing FQDN connection cannot authenticate outbound requests. This is
   an additional connection configuration, not another telephony provider or number.
   Set a unique SIP username/password and enable TLS. Keep credentials only in
   the Telnyx/ElevenLabs dashboards or an approved secret manager.
3. Open **Voice → Outbound Voice Profiles**, create/select a restricted profile,
   attach the outbound connection, and enable only countries needed for the
   consented recipient and human. Confirm account verification/trial restrictions
   permit both destinations. Caller ID must be the account-owned Telnyx number.
4. Set a low **daily spend limit**, **maximum destination rate**, and outbound
   **channel limit**. Start with one channel for AI-only testing. A transfer may
   need a second channel; permit at most two for that controlled test. Choose the
   monetary caps from the actual rate deck and your approved test budget. Disable
   recording, forwarding, failover/redial routes and unrestricted destinations.
5. Before transfer testing, confirm with Telnyx support that **outbound-originated
   SIP REFER** is supported on this exact connection and account; confirm any
   REFER permission, caller-ID and Diversion requirements. Do not assume their
   inbound external-transfer tutorial applies. The initial transfer template uses
   no custom headers; unsupported requirements must remain a blocker until the
   provider adapter is deliberately updated and reviewed.
6. Establish a carrier-enforced <=180-second total call limit that survives REFER.
   Obtain the exact supported configuration from Telnyx; there is deliberately no
   invented dashboard switch here. If unavailable, keep transfer/website disabled
   and report this limitation. End controlled calls manually as an additional precaution.
7. Use **Debugging → SIP Call Flow** and **Reporting → Calls / call detail records**
   to inspect the outbound INVITE, authentication challenge/success, answer,
   REFER, NOTIFY and BYE, plus the human leg. Voice API webhooks alone do not prove
   SIP-trunk call completion. Do not paste raw SIP traces/phone numbers into notes.

## ElevenLabs dashboard

1. Create a **separate private agent**, “Line outbound HVAC demo.” Reuse the
   existing voice/model selection. Do not edit the inbound or browser agents.
2. Apply the configuration fields in `docs/elevenlabs-outbound-agent.json` in the
   agent JSON editor or corresponding dashboard sections. Retain the selected
   voice/model fields. The prompt and first message must match
   `telephony/outbound/prompt.py` exactly; configuration drift blocks dialing.
   Keep maximum duration <=180, concurrency 1, daily limit <= the API limit,
   bursting off, recording off and retention 0. This fictional demo does not
   establish production privacy readiness.
3. Use only native **End call** initially. Remove copied booking, webhook/client,
   MCP and other tools; no external tool IDs, workflows, procedures, knowledge
   base or language presets. Native tools are read from `built_in_tools` (or the
   legacy inline `tools` array), not external tool IDs. Keep first-message
   interruptions allowed. Declare the prompt variables `demo_scenario`,
   `demo_transfer_enabled`, `demo_max_duration_seconds`; backend initiation data
   supplies them and `outbound_demo_call_id`. No client configuration overrides
   are needed.
4. Disable **Fetch conversation initiation client data from webhook** on this
   outbound agent. It must not call the inbound SIP initialization URL. The API
   already supplies its call identity; the existing inbound initialization remains unchanged.
5. In **Settings → Webhooks**, create a dedicated signed post-call webhook at
   `https://YOUR_API/api/v1/outbound-demo/webhook`. Store its generated signing
   secret as `OUTBOUND_DEMO_WEBHOOK_SECRET`. Set this webhook as this agent's
   override, replacing the template webhook ID. Enable **transcript** and
   **call_initiation_failure**, disable audio delivery. Preserve all other agents'
   webhook assignments. Provider transcript delivery is processed in memory;
   this demo never saves it or raw failure messages.
6. Open **Phone Numbers**, select the existing imported Telnyx SIP number, and add
   its **outbound** trunk settings: address `sip.telnyx.com` (hostname only), TLS,
   the dedicated Telnyx SIP digest username/password, PCMU/PCMA as supported,
   and compatible media encryption (prefer Required after carrier confirmation).
   Preserve its inbound configuration and assigned inbound agent. Outbound calls
   explicitly select the separate agent via the API, so do not reassign inbound.
   Save the imported resource's ID as `OUTBOUND_DEMO_PHONE_NUMBER_ID`, not its E.164
   number or Telnyx connection ID. Current preflight requires TLS + digest.
7. After the AI-only call and carrier prerequisites pass, add native **Transfer
   to Human / transfer_to_number** using `docs/elevenlabs-outbound-transfer.json`.
   Replace only `REPLACE_WITH_AUTHORIZED_HUMAN_E164` with the agreed human number.
   Use exactly one static phone destination, SIP REFER, and the supplied consent
   condition. Do not enable dynamic destinations or additional transfer rules.
   Set the same destination in the API environment. No arbitrary destination can
   enter through the website. The human must differ from all demo recipients and
   the Telnyx caller number, preventing simple forwarding loops.

## Environment

All variables below are backend-only unless explicitly marked. Keep real phone
numbers and secrets out of source, notes, screenshots, shell history and git.

| Variable | Purpose / initial value |
| --- | --- |
| `APP_ENVIRONMENT` | `development`; retains existing development actor boundaries |
| `DEVELOPMENT_ACTOR_USER_ID` | Existing active development business operator |
| `DEMO_ADMIN_TOKEN` | Existing strong (>=32 character) admin token; always checked here |
| `ELEVENLABS_API_KEY` | Existing account key; server only |
| `OUTBOUND_DEMO_ENABLED` | `false`; enable only for approved admin tests |
| `OUTBOUND_DEMO_AGENT_ID` | Dedicated private demo agent ID |
| `OUTBOUND_DEMO_PHONE_NUMBER_ID` | Existing ElevenLabs imported Telnyx SIP resource ID |
| `OUTBOUND_DEMO_ALLOWED_NUMBERS` | Comma-separated exact E.164 recipients; owner verifies control and obtains consent out of band |
| `OUTBOUND_DEMO_HUMAN_NUMBER` | One authorized E.164 human destination |
| `OUTBOUND_DEMO_SECRET` | Dedicated stable >=32-character secret; API and Next server only; keyed state hashes + bridge authentication |
| `OUTBOUND_DEMO_WEBHOOK_SECRET` | Dedicated ElevenLabs HMAC secret; must differ from bridge secret |
| `OUTBOUND_DEMO_DAILY_LIMIT` | `5`, maximum 10 attempts/business/UTC day, including failures |
| `OUTBOUND_DEMO_NUMBER_DAILY_LIMIT` | `1`, maximum 2 attempts/number/rolling 24 hours |
| `OUTBOUND_DEMO_COOLDOWN_SECONDS` | `300`, minimum 180 between all business attempts |
| `OUTBOUND_DEMO_MAX_DURATION_SECONDS` | `180`, hard maximum for the AI agent |
| `OUTBOUND_DEMO_RINGING_SECONDS` | `25`, allowed 10–30 |
| `OUTBOUND_DEMO_TRANSFER_ENABLED` | `false` until fixed human, tool and carrier controls are configured |
| `OUTBOUND_DEMO_CARRIER_LIMIT_CONFIRMED` | `false`; only attest after verifying all transferred-leg duration controls |
| `OUTBOUND_DEMO_LIVE_VERIFIED` | `false`; true only after actual outbound acceptance |
| `OUTBOUND_DEMO_TRANSFER_VERIFIED` | `false`; true only after human answers and two-way audio is verified |
| `OUTBOUND_DEMO_WEBSITE_ENABLED` | `false`; requires both live acceptance flags and enabled transfer |
| `OUTBOUND_DEMO_FORM_ENABLED` | **Next server only**, `false`; website activation gate |
| `NEXT_PUBLIC_API_BASE_URL` | Existing API base URL, reused by Next server proxy |

No Telnyx REST key is required for dialing through ElevenLabs SIP. Dashboard/trace
access is required for actual carrier acceptance. Do not rotate the state/bridge
secret while records exist: their ownership/destination hashes support durable
idempotency and rate limits. Existing `TELEPHONY_PROVIDER*` settings control
inbound only and do not activate this feature.

## Approved execution sequence

These are instructions for the owner, **not executed commands**. Apply migration
`20261101_0018` only after confirming the target database/branch. No reseed or
destructive runtime operation is needed. It adds one table to the existing Neon
database. Downgrade refuses to delete any call/consent evidence.

```sh
python -m pytest tests/test_outbound_demo.py
npm run test:web -- src/app/api/outbound-demo/route.test.ts
npm run typecheck:web
npm run build:web
python -m ruff check apps/backend/src/insurance_operations/telephony/outbound tests/test_outbound_demo.py tests/database/test_outbound_demo_calls.py
python -m mypy --explicit-package-bases apps/backend/src/insurance_operations/telephony/outbound
```

After confirming the database environment, review and apply the forward migration:

```sh
python -m alembic current
python -m alembic upgrade head
python -m alembic current
```

Database specifications use the repository's existing `migrated_database` fixture,
which downgrades/truncates its target. **Run them only on a separately confirmed
disposable test database**, never the runtime Neon branch. `TEST_DATABASE_URL`
must differ from both runtime and migration targets. After that explicit confirmation:

```sh
APP_ENVIRONMENT=test python -m pytest tests/database/test_outbound_demo_calls.py tests/database/test_migrations.py tests/database/test_table_ownership.py
```

Use the existing approved deployment/start procedures to make the new API and
webhook available; this implementation does not deploy them. Leave website and
transfer flags false for the first AI-only test.

### Place exactly one authorized admin test call

Only after approving an actual telephone call, run this from the project virtual
environment with `HVACLINE_API_BASE_URL` set to the intended HTTPS API. The token
and approved recipient are read privately, never included in history or output.
Save the printed request key and response call ID securely for status/recovery.
**Executing the POST places a real, potentially billable call.**

```sh
python - <<'PY'
import getpass
import os
import uuid
import httpx

base = os.environ['HVACLINE_API_BASE_URL'].rstrip('/')
if not base.startswith('https://'):
    raise SystemExit('Set the intended HTTPS API origin first')
token = getpass.getpass('Demo admin token: ')
number = getpass.getpass('Consented allowlisted E.164 recipient: ')
request_id = str(uuid.uuid4())
print('Request key:', request_id, flush=True)
response = httpx.post(
    base + '/api/v1/outbound-demo/admin/calls',
    headers={'X-Demo-Admin-Token': token},
    json={'request_id': request_id, 'phone_number': number, 'scenario': 'cooling',
          'consent': True, 'consent_version': 'outbound-demo-v1'},
    timeout=40, follow_redirects=False,
)
print(response.status_code, response.json())
PY
```

Do not rerun that snippet with a fresh key after a timeout. Reuse the same key,
number and scenario for an idempotent retry or inspect the stored call through
the admin status endpoint. Unknown/preflight-crash reservations intentionally
block another call. There is no automatic retry, expiry or redial.

Admin API (all require `X-Demo-Admin-Token`, even when the general sandbox is off):

- `POST /api/v1/outbound-demo/admin/calls`: request above.
- `GET /api/v1/outbound-demo/admin/calls/{call_id}`: durable status only.
- `POST /api/v1/outbound-demo/admin/calls/{call_id}/refresh`: read authenticated
  ElevenLabs conversation status and reconcile it; does not dial.
- `POST /api/v1/outbound-demo/admin/calls/{call_id}/carrier-ended` with
  `{"all_carrier_legs_ended":true}`: **only after** checking Telnyx that all original
  and transfer legs ended and no submission is still pending. Audits the operator
  attestation and releases an uncertain slot; does not hang up a call or establish
  transfer success. Never use it merely to bypass limits. Idempotent replays do not dial.

### Real-call acceptance, in order

1. Confirm recipient ownership and explicit one-time consent with the owner.
   Call only a configured recipient. Answer: check correct caller ID, AI/fictional
   disclosure, permission to continue, natural cooling/heating/maintenance turns,
   interruptions, no price/availability/booking inventions, and immediate stop.
2. Keep an AI-only call open: prove it disconnects at <=180 seconds from actual
   conversation start. Check Telnyx CDR duration and ElevenLabs final status;
   ringing time may be additional and must stay within its configured timeout.
   Check post-call webhook signature acceptance and the same bound conversation.
3. On a separately approved attempt within quotas, reject, leave unanswered,
   hang up mid-conversation and force a provider failure. Expect rejected,
   unanswered, disconnected/completed-as-reported, and failed respectively.
   Normal carrier hangup can be reported by ElevenLabs as a completed conversation;
   the UI says it ended, never that service or a transfer succeeded.
   Check repeated signed delivery does not regress a terminal state.
4. For transfer, have the authorized human ready on a **different** number.
   Establish carrier duration control first, configure the fixed native tool and
   enable the backend transfer flag. Ask for a human, decline the proposed attempt:
   no REFER should occur. Ask again and explicitly agree in the next turn. Check
   an explanatory message, one REFER/NOTIFY sequence, ringing on the human phone,
   the human answering, and two-way caller/human audio after Line leaves.
5. Verify the carrier limit also terminates the transferred call at the original
   total deadline. A successful REFER/tool result or ringing human phone alone
   fails this acceptance. Inspect costs and all leg endings; the backend retains
   the slot for `refer_accepted`/unconfirmed transfer until the owner confirms
   all carrier legs ended.
6. On another authorized attempt, make the human unavailable/decline. Check the
   actual carrier behavior. If the AI retains the call, it must acknowledge tool
   failure and offer to continue/end without promising a callback. A blind REFER
   can detach the AI before the human answers: do not promise AI recovery. If that
   carrier behavior cannot provide acceptable failure handling, leave website and
   transfer disabled and report unsupported behavior.
7. Set live verification flags only after these results are recorded without
   personal data. Do not mark transfer verified from a transcript or tool's word
   “success.” This repository does not currently prove an answered human transfer
   from an authenticated carrier event; the UI always says human answer unconfirmed.

## Website acceptance and operational limits

Only after the above, enable the backend website gate and Next form gate with
matching server-only bridge secrets. The form stays allowlist-only; this is
**not** unrestricted public dialing and no OTP or SMS verification is implemented.
Owner approval must establish number control out of band. Do not add numbers from
anonymous requests. Public requests to new numbers require a separate ownership
verification, anti-abuse and budget design before removing the allowlist.

Manually check desktop/mobile layout, keyboard/focus, labels, readable disabled
states, explicit unchecked consent, all three scenarios, incorrect international
format, missing consent, non-allowlisted rejection, double-click/replay, lost POST
response, page reload/status recovery, foreign visitor denial, cross-origin
rejection, quotas across new cookies/keys, and disabled gates. Status polling is
read-only every ten seconds for up to four minutes; it cannot dial. A new-tab or
cookie reset cannot bypass persistent number/global quotas. No phone number is
stored in browser storage. A request key may remain in tab session storage for
recovery; consent/control are still rechecked by the backend for every new call.

Use the existing inbound, browser Voice/Chat and booking acceptance procedures as
regression checks. No existing agent or booking tool is reused by the fictional
demo, so it cannot create a real appointment.

Kill switches: set API `OUTBOUND_DEMO_ENABLED=false` to reject new calls, website
gates false to hide activation, and disable the outbound SIP connection/profile
to stop carrier access if needed. Keep credentials/webhook routing for in-flight
reconciliation. These switches do not terminate existing calls; end them in the
carrier dashboard. Keep retention of minimal consent/hash records bounded through
an owner-approved policy; no automated purge is added because it could defeat
the durable limits/idempotency evidence.

Remaining blockers: unapplied migration and unchecked implementation; dedicated
agent/webhook/outbound trunk setup; real-call acceptance; outbound REFER support;
carrier-enforced transferred-leg duration and acceptable unavailable-human behavior.
The native transfer consent check is guided by the dedicated agent prompt and
tool condition; it is not a separate deterministic backend transcript gate.
Do not describe this feature as working end to end until those pass.
