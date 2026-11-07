# Outbound AI demo calling with human transfer

## Workflows and additional tools — November 7, 2026 — UNVERIFIED

Owner authorizes outbound agents with workflows and additional tools. Backend
preflight now allows workflow graphs, external tool IDs, MCP server references,
inline client/webhook tools and additional native tools. It still requires the
base prompt/first message, native End call, private agent authentication,
recording off, retention zero, bounded duration and assigned signed-event webhook.
Base knowledge bases, language presets, procedures and initiation webhooks remain
rejected. SIP TLS/digest, caller loop protection, consent, destination policy,
quotas and saved-request handling are unchanged.

The existing fixed-destination/SIP REFER checks still apply to the main agent's
native phone-transfer tool. Workflow routing, subagent overrides and external
tool behavior are controlled by the hosted ElevenLabs configuration; the backend
does not validate them or enforce its transfer flag on those paths. Review those
paths in the outbound agent, including their effects when transfer is disabled.

No migration or new environment setting is needed. Deploy the updated backend
to Render for this change to affect hosted calls. No tests, diagnostic requests,
hosted changes or calls were executed by Codex. Implementation remains unverified.
Owner commands, supplied unexecuted, from the repository root:

```sh
.venv/bin/python -m pytest tests/test_outbound_demo.py
PYTHONPATH=apps/backend/src .venv/bin/python scripts/diagnose-outbound-preflight.py
```

Manually confirm Render uses this backend revision, the diagnostic no longer
reports workflow/tool presence as a failure, and all remaining comparisons pass.
Inspect workflow routing and tool permissions; retain native End call. Supervised
call acceptance still requires two-way audio, actual disconnection and signed
terminal backend status. This source change does not establish carrier acceptance
or resolve the older timed-out request.

## Mobile-only hardening — November5,2026 — UNVERIFIED

The production-readiness follow-up requires a verified US mobile number for every
website call, separately from authenticator sign-in. New SMS proof/account limits
need API-only Telnyx Verify configuration and forward migration0019. Older no-SMS,
mobile/landline and no-new-migration descriptions below do not apply to this
revision. It is untested; no hosting/provider settings changed. Exact
release blockers, settings, commands and acceptance:
[Public demo release](public-demo-production-readiness.md).

## Public callback policy — November 5, 2026 — UNVERIFIED

Owner authorizes website callbacks with sign-in and authenticator MFA required.
`consented_us` now permits website requests; transfer stays disabled. Website
activation requires real outbound acceptance; transfer acceptance applies only
when transfer is enabled. This supersedes older admin-only US and mandatory
website-transfer instructions below. Hosted flags were not changed and successful
end-to-end US calling remains unverified. Exact settings, owner commands and
manual checks: [Public callbacks](public-callbacks.md).

## Callback sign-in gate — November 4, 2026 — UNVERIFIED

Owner now requires sign-in before callback requests. The modal shows a sign-in
prompt before phone/consent fields; the existing customer session/MFA flow returns
to the callback modal using a fixed continuation intent. The website bridge checks
the current customer session for availability, status and submission, rejecting
missing/expired or unverified sessions before outbound access. Existing browser
recovery keys/locks and calling policy gates remain; no admin credential is exposed
or used to turn customer sign-in into admin dialing. No feature flag, provider
setting or backend schema changes. Exact unrun checks and manual acceptance:
`docs/homepage-hero.md`. Live activation still requires hosting/TLS acceptance and
a deliberate customer-calling policy; `consented_us` remains admin-only.

## Rollout handoff and date removal — November 4, 2026

Owner requests removing the November5 announcement and rolling out outbound
calling. Source removes the dated promotion and obsolete shared date/component;
unavailable form/bridge messages now reflect availability. This supersedes the
historical date-announcement instructions below. The existing call gates remain
enforced pending hosted configuration and the owner’s admin/visitor rollout scope.
Policy/modal implementation is pushed as048ff2f. Render/Vercel integrations are
not connected and no local deployment credentials are configured; no hosted
deployment/configuration or real-call acceptance is established by that push.
The earlier failed Render deployment and reported TCP versus mandatory TLS still
need inspection. Preserve the existing provider resources and do not weaken TLS
or route visitors through admin credentials to bypass the admin-only policy.

## Hero request form — November 4, 2026 — UNVERIFIED

The hero and Calling section now open a shared Radix Dialog phone/scenario/consent
form. Fields remain editable for preview with gates off, but submission remains
disabled; the UI does not enable website calling or route visitors through admin
credentials. Existing request/status/idempotency handling is reused and stays
mounted while the dialog closes, preserving pending-call recovery. This does not
change the admin-only `consented_us` policy or activate transfer/public calling.
Dependency setup, exact owner commands and keyboard/mobile/manual acceptance:
`docs/homepage-hero.md`. Rendering and runtime remain unverified; no checks or
calls ran for this UI change.

## Consented US admin calls — November 4, 2026 — UNVERIFIED

`OUTBOUND_DEMO_NUMBER_POLICY` selects `allowlist` (default, existing exact E.164
approval) or `consented_us` (no preconfigured recipients). The new policy is
restricted to the existing authenticated admin endpoint. It rejects configuration
with website calling or transfer enabled; the website route also refuses this
policy. Keep `OUTBOUND_DEMO_TRANSFER_ENABLED=false`,
`OUTBOUND_DEMO_WEBSITE_ENABLED=false` and Next server
`OUTBOUND_DEMO_FORM_ENABLED=false`. This supersedes the allowlist-only admin
instructions below when `consented_us` is selected; it does not enable public calls.

Inputs accept full US national numbers with area code or international numbers
with `+`, spaces, parentheses, dots and hyphens. The shared request model normalizes
them to E.164 before eligibility, request fingerprints, recipient quotas or dialing.
Existing E.164 allowlist requests and stored fingerprints retain their format.
Extensions, SIP URIs, vanity strings, dialing instructions and short codes reject.

The pinned `phonenumbers==9.0.42` dependency checks numbering-plan validity,
US region assignments and mobile/landline type (including the shared fixed/mobile
category). Scope includes the 50 states, DC and US territories (`US`, `AS`, `GU`,
`MP`, `PR`, `VI`). This is more than a `+1` check: Canada and non-US Caribbean
regions reject, as do international, premium, toll-free, personal-number and other
unsupported types. Carrier restrictions still apply, including territory-specific
rates and destination permissions. Metadata validates assigned
numbering ranges, not an active subscriber, ownership, reachability or current
carrier after porting. The operator must establish control and explicit one-time
recipient consent out of band for every new call. No automated ownership lookup,
OTP service or consent verification is added. Review metadata updates as numbering
plans change. Sources: [library](https://pypi.org/project/phonenumbers/9.0.42/),
[upstream validity limits](https://github.com/google/libphonenumber/blob/master/FAQ.md#what-does-it-mean-for-a-phone-number-to-be-valid).
US jurisdiction scope follows [NANPA](https://www.nanpa.com/sites/default/files/reports/annual-reports/2023_NANPA_AnnualReport_0.pdf).

Errors use the existing API envelope: malformed syntax returns 422
`VALIDATION_FAILED` with field type `phone_number_invalid`; invalid ranges return
422 `DEMO_PHONE_NUMBER_INVALID`; unsupported regions/types return 422
`DEMO_DESTINATION_UNSUPPORTED`. A legacy allowlist miss retains 403
`DEMO_NUMBER_NOT_AUTHORIZED`. Consent/version validation, admin authentication,
tenant locking, quotas, cooldown, idempotency, hashed records, audit, unknown
outcomes, HMAC webhooks and the 180-second AI cap are unchanged. Preflight also
checks the actual normalized destination against the provider caller number so
an empty allowlist cannot remove the existing call-loop protection. TLS and SIP
digest remain mandatory. Telnyx destination/spending restrictions still apply.

Owner-reported completed setup: existing outbound agent/webhook, Telnyx SIP
connection/limits, Render agent/phone IDs, Neon0018, 127 focused tests and frontend
typecheck/build. Preserve these resources. The November 4 changes have not been
executed or tested. No migration is required. Prior Render deployment failure
and reported TCP versus required TLS remain blockers; no provider or environment
setting was changed here.

Render: set `OUTBOUND_DEMO_NUMBER_POLICY=consented_us`; the allowlist may be empty.
Retain existing admin/operator identity, agent/phone IDs, API key, stable state
secret and distinct signing secret. Leave admin calling disabled until the
compatible backend is Live and private configuration/TLS are accepted; only then
temporarily set `OUTBOUND_DEMO_ENABLED=true` for an authorized test. Keep public
and transfer flags false as above. Install the updated backend dependencies as
part of an owner-approved release; this change has not installed them locally.

Owner commands for this change, **not run**:

```sh
.venv/bin/python -m pip install -e '.[dev]'
DEMO_SANDBOX_ENABLED=false PYTHONPATH=apps/backend/src .venv/bin/python -m pytest --import-mode=importlib tests/test_outbound_demo.py
.venv/bin/python -m ruff check apps/backend/src/insurance_operations/telephony/outbound tests/test_outbound_demo.py tests/database/test_outbound_demo_calls.py
.venv/bin/python -m mypy --explicit-package-bases apps/backend/src/insurance_operations/telephony/outbound
```

Only after privately confirming an isolated disposable `TEST_DATABASE_URL`,
distinct from runtime/direct targets (fixtures rebuild/truncate it):

```sh
APP_ENVIRONMENT=test GOOGLE_CALENDAR_ENABLED=false BOOKING_EMAIL_ENABLED=false DEMO_SANDBOX_ENABLED=false PYTHONPATH=apps/backend/src .venv/bin/python -m pytest --import-mode=importlib tests/database/test_outbound_demo_calls.py
```

Manual checks after owner-approved deployment: confirm the Live commit; verify
TLS/digest and US-only carrier restrictions/spend caps on the existing resources;
reject missing/wrong admin credentials, missing/refused/stale consent, non-US `+1`,
international, premium/toll-free and short-code destinations before dialing.
Confirm the website stays unavailable. Use the single-call command below only
with fresh recipient consent. Confirm correct caller ID, AI disclosure, audio,
interruption handling, <=180-second ending and signed terminal receipt. On a
lost response reuse the saved key, same normalized number and same scenario;
never create a fresh key merely to retry an uncertain call. Confirm equivalent
formats share one request/recipient quota. No bulk or automatic redial is added.

Current closeout, November 3: after explicit owner migration authorization, the
configured development database reported `20261101_0018` before and after the
targeted upgrade; no schema change was needed. This supersedes earlier pending
migration notes for that target only. Local outbound provider/recipient/signing
values remain missing and calling flags remain false. The subsequently authorized
`.venv/bin/python -m pytest tests/test_outbound_demo.py` passed 39 tests in 1.64s.
The separately authorized `npm run test:web --
src/app/api/outbound-demo/route.test.ts` passed 15 tests in one file (556ms);
the focused inbound/webhook suite passed 73 tests in 2.32s. Other release checks
remain unexecuted. No provider edits, deployments or calls
ran. See [FINAL-CLOSEOUT.md](../FINAL-CLOSEOUT.md) for
current evidence, owner commands and remaining activation blockers.

Live runtime behavior remains **UNVERIFIED**. No builds, services, provider edits,
deployments or telephone calls were run for this release.
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
calling options and a browser Voice link. The November4 hero/modal update now
allows previewing the phone/consent form with submission disabled. Existing
requests retain status recovery in that shared modal even when new calls are
disabled. Actual submission still requires the existing frontend and backend
activation gates.

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
3. Retain native **End call** in `built_in_tools` or the legacy inline `tools`
   array; an external tool with the same name does not satisfy this requirement.
   Workflows, external tool IDs, MCP references and additional tools are allowed.
   Their behavior is managed in ElevenLabs; the backend validates the base agent
   and its native phone-transfer tool, not workflow/tool side effects. Base-agent
   procedures, knowledge bases and language presets remain unsupported.
   Keep first-message
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
| `OUTBOUND_DEMO_ENABLED` | `false`; execution gate for admin tests and accepted website rollout |
| `OUTBOUND_DEMO_AGENT_ID` | Dedicated private demo agent ID |
| `OUTBOUND_DEMO_PHONE_NUMBER_ID` | Existing ElevenLabs imported Telnyx SIP resource ID |
| `OUTBOUND_DEMO_NUMBER_POLICY` | `allowlist` (default) or `consented_us` (US mobile/landline destinations, admin or enabled website; transfer off) |
| `OUTBOUND_DEMO_ALLOWED_NUMBERS` | Comma-separated exact E.164 recipients; required only in `allowlist` mode. Recipient control and one-time consent remain required in both modes |
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
| `OUTBOUND_DEMO_WEBSITE_ENABLED` | `false`; requires real outbound acceptance and, only if transfer is enabled, transfer acceptance |
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

Only after approving an actual telephone call, run this from the repository root
with `HVACLINE_API_BASE_URL` set to the intended HTTPS API. In `consented_us` mode
the recipient needs no allowlist entry. The token
and approved recipient are read privately, never included in history or output.
Save the printed request key and response call ID securely for status/recovery.
**Executing the POST places a real, potentially billable call.**

```sh
.venv/bin/python - <<'PY'
import getpass
import os
import uuid
import httpx

base = os.environ['HVACLINE_API_BASE_URL'].rstrip('/')
if not base.startswith('https://'):
    raise SystemExit('Set the intended HTTPS API origin first')
token = getpass.getpass('Demo admin token: ')
number = getpass.getpass('Consented recipient (full US number or E.164): ')
if getpass.getpass('Recipient agreed to this one AI demo call? Type YES: ') != 'YES':
    raise SystemExit('Recipient consent is required')
saved_key = getpass.getpass('Saved request key for retry, or Enter for new call: ').strip()
request_id = str(uuid.UUID(saved_key)) if saved_key else str(uuid.uuid4())
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

After a timeout, enter the saved key when rerunning the snippet. Reuse the same key,
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
   Call only an eligible recipient under the configured number policy. Answer:
   check correct caller ID, AI/fictional
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
   carrier behavior cannot provide acceptable failure handling, leave transfer
   disabled and report unsupported behavior. AI-only website calling is separate.
7. Set live verification flags only after these results are recorded without
   personal data. Do not mark transfer verified from a transcript or tool's word
   “success.” This repository does not currently prove an answered human transfer
   from an authenticated carrier event; the UI always says human answer unconfirmed.

## Website acceptance and operational limits

After real AI-only outbound acceptance, enable the backend website and Next form
gates with matching server-only bridge secrets. Sign-in with authenticator MFA
and explicit one-time recipient consent are required. `consented_us` supports US
mobile/landline requests without an allowlist; `allowlist` retains exact approved
recipients. No phone OTP/SMS verification is implemented; authenticator MFA protects
the account and does not prove phone ownership. Transfer acceptance is required
only when transfer is enabled. See [Public callbacks](public-callbacks.md).

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

Remaining blockers: current-change verification, hosted deployment/configuration
and TLS compatibility; real-call acceptance; outbound REFER support;
carrier-enforced transferred-leg duration and acceptable unavailable-human behavior.
The native transfer consent check is guided by the dedicated agent prompt and
tool condition; it is not a separate deterministic backend transcript gate.
Do not describe this feature as working end to end until those pass.
