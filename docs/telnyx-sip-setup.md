# Telnyx SIP inbound calling

Status: implementation and regression specifications are **UNVERIFIED**. Provider
account setup, deployed configuration, audio/security negotiation and real
telephone acceptance are **UNVERIFIED**. No tests, migrations, services, provider
calls, account changes, purchases or deployments were executed for this feature.

The October 30 inbound 422 investigation, boundary normalization and privacy-safe
diagnostics are recorded in [the webhook repair handoff](inbound-phone-webhook-repair.md).
That handoff includes passing automated checks, read-only provider evidence,
remaining uncertainty and exact checks; hosted runtime acceptance remains pending.

## Implemented path

Customer → assigned Telnyx number → ElevenLabs SIP/private phone agent →
authenticated FastAPI tools → existing PostgreSQL records → Operations.

FastAPI owns routing, policy, consent, confirmation, availability, booking,
idempotency and audit. There is no Telnyx REST client, API-key requirement, new
voice engine, media relay, audio storage or new database table/migration.
Twilio's existing signature, register-call and active-call transfer path remains
selected by `TELEPHONY_PROVIDER=twilio`.

## Account and number prerequisites — UNVERIFIED

- Owner-approved Telnyx account with inbound SIP trunking access, an authorized
  US telephone number and administrator access to its routing. Obtain explicit
  owner approval before buying a number or enabling paid services.
- ElevenLabs account with Agents/SIP import access and the existing private
  HVACLine telephone agent, separate from the browser/WhatsApp agents.
- Public HTTPS API, existing Neon schema and an active development operator with
  exactly one active business membership. The established development identity
  gate remains; this feature does not implement production tenant onboarding.
- Configure that business's receptionist settings, approved FAQs and call policy
  in Operations. Add the exact E.164 number under inbound numbers and mark it
  ACTIVE. The number must belong to the configured operator's business; the
  webhook cannot choose a tenant. Enable inbound policy and select concurrent/
  daily limits and callback fallback deliberately.
- Configure actual schedule, service ZIPs, timezone, technician teams and opening
  hours. Availability comes from this configuration and existing appointments;
  no telephone setup creates appointment slots. Retain existing Google Calendar
  and email/job settings independently where those integrations are enabled.

## Telnyx Mission Control — UNVERIFIED

1. Open Voice → SIP Trunking and create a SIP Connection of type **FQDN**.
2. Enter destination FQDN `sip.rtc.elevenlabs.io`. Select **+E.164** destination
   formatting, the appropriate SIP region and **TCP** for the initial documented
   compatibility setup. Assign the owner-authorized number to this connection.
3. Ensure the generated SIP INVITE includes the dialed number as its identifier.
   TCP destination: `sip.rtc.elevenlabs.io:5060`; complete URI:
   `sip:{TELNYX_E164_NUMBER}@sip.rtc.elevenlabs.io:5060;transport=tcp`.
   Replace the placeholder with the assigned number, including its leading `+`.
4. Telnyx inbound trunks do **not** use digest authentication in the ElevenLabs
   Telnyx integration guide. Do not add invented inbound usernames/passwords.
   Use provider-supported source restrictions where available and verified.
5. Outbound authentication/termination routing is outside this inbound milestone.
   If the dashboard requires outbound details, copy the actual Telnyx-provided
   termination hostname and credentials. Do not invent a hostname or enable
   outbound campaigns/call-control services to make inbound calling work.

Reference: [official Telnyx integration](https://elevenlabs.io/docs/eleven-agents/phone-numbers/telephony/telnyx).

## ElevenLabs SIP import and agent — UNVERIFIED

1. Phone Numbers → Import Number → From SIP Trunk. Import the **same E.164
   number**, configure the inbound trunk and assign the private HVACLine phone
   agent matching `ELEVENLABS_PHONE_AGENT_ID`.
2. Keep agent authentication/private access and the existing AI/provider
   disclosure, consent, FAQ, readback and booking instructions. Never let the
   agent infer availability or say a booking succeeded before the confirmation
   tool returns `CONFIRMED`.
3. In Agents settings, configure the Conversation Initiation Client Data webhook:
   `POST https://{API_HOST}/api/v1/providers/elevenlabs/sip/initialize`.
   Add secret header `Authorization: Bearer {ELEVENLABS_PHONE_INITIATION_SECRET}`.
   On the agent's Security tab enable **Fetch initiation client data from a
   webhook**. This is separate from tools and the signed post-call webhook.
   Do not configure caller-editable tenant identifiers or prompt overrides.
4. Define exactly the required custom dynamic variables:
   `phone_inbound_call_id` and `phone_max_duration_seconds`. Remove obsolete
   required custom variables or deliberately extend the backend contract before
   adding others. The webhook returns the `conversation_initiation_client_data`
   object with these two variables; it supplies no credentials or tenant details.
5. Attach the existing eight blocking HTTP tools under
   `/api/v1/providers/elevenlabs/tools/`: `phone-consent`, `approved-faq`,
   `confirm-intake`, `request-handoff`, `service-request`, `availability`,
   `reserve-appointment`, `confirm-appointment`. Each uses the separate secret
   `Authorization: Bearer {ELEVENLABS_PHONE_TOOL_SECRET}`.
6. Every tool gets `inbound_call_id={{phone_inbound_call_id}}` and
   `conversation_id={{system__conversation_id}}`. Do not use
   `system__call_sid` for SIP. Optionally include
   `call_id={{system__call_id}}` in `phone-consent` to bind the actual SIP call ID
   if initiation omitted it; omit/null the field when unavailable. Do not pass
   that field to unrelated tools. Existing Twilio payloads remain valid.
7. Configure signed `post_call_transcription` and `call_initiation_failure` at
   `POST https://{API_HOST}/api/v1/providers/elevenlabs/post-call`, using the
   separate `ELEVENLABS_POST_CALL_WEBHOOK_SECRET` HMAC secret. Disable audio
   webhooks and audio retention. Keep privacy, retention, model, STT, TTS, voice,
   region and spending controls explicitly selected and manually reviewed.
8. Set the actual provider maximum conversation duration equal to
   `PHONE_MAX_DURATION_SECONDS` (at most 180). A returned dynamic variable does
   not itself disconnect the carrier. API tool authorization for SIP expires
   from the persisted initiation time; consent and retries never extend it.

Tool payloads and behavioral instructions:
[current phone/HVAC contract](hvacline-live-validation.md#phone-agent-instruction-contract),
[phone-agent configuration](elevenlabs-phone-agent-setup.md).
Provider contracts:
[initiation webhooks](https://elevenlabs.io/docs/eleven-agents/customization/personalization),
[system identifiers](https://elevenlabs.io/docs/eleven-agents/customization/personalization/dynamic-variables).

## API environment and deployment — UNVERIFIED

### Main publication and hosted release handoff — 2026-10-29

The owner has authorized completing and publishing the pending Telnyx/phone-CTA
work to `main`. The five feature commits extend main's `d85ff6d` without a
conflicting branch history. Publication does not establish runtime acceptance;
the execution commands below remain unrun and activation stays gated.

The last reported Render source was `54e6603`; this is owner-reported evidence,
not a fresh hosting inspection. A release from that revision includes earlier
main changes as well as Telnyx:

| Area | Included change | Release requirement |
| --- | --- | --- |
| Schema | `20261029_0016` removes the fictional-data acknowledgement requirement; `20261029_0017` adds guest-chat quota tables | Apply forward migrations to the intended database before starting the API. The configured development database was previously confirmed at `0016`; hosted revision is unverified. |
| Backend dependencies | `websockets==17.3` for homepage guest chat | Install from the current Python manifest during the authorized release. |
| Frontend dependencies | `qrcode.react@4.2.0` for MFA enrollment | Use the current npm lockfile and Node 24 when rebuilding the frontend. |
| Agent contracts | Updated disclosure/confirmation wording and shared browser guest mode | Follow [customer wording](customer-data-requirements.md) and [homepage chat](homepage-chat.md) before enabling their respective paths. |
| Telnyx | SIP initialization, shared tools/finalization and callback fallback | Complete this guide's account/configuration and live acceptance steps. Telnyx itself adds no schema migration or dependency. |
| Public phone CTA | Server-rendered number and verification flag | Keep `TELNYX_INBOUND_CALLING_VERIFIED=false` until real-call acceptance, then explicitly authorize frontend activation/rebuild. |

Before any separately authorized deployment, review the actual Render service's
branch, auto-deploy setting and build/pre-deploy commands. The checked-in
Blueprint defaults to Twilio and its pre-deploy command runs both migrations and
the development seed. It is not evidence of the existing service configuration;
publishing source does not authorize reseeding. Existing business settings and
content must be preserved. The owner's previously reported Free service uses a
different migration/build arrangement; retain the established environment
handoff rather than applying the Blueprint blindly.

For rollout, keep homepage chat disabled and telephone ingress disabled until
schema/dependencies and private agent/webhook configuration are ready. Deploy the
API before the frontend, complete the owner-run automated checks and live call
checklist, then enable each feature deliberately. Provider switching must drain
the old carrier path as described below. Withdrawing the public phone button
also requires a frontend rebuild; switching a flag alone cannot validate or
disconnect an existing carrier call. No deployment/provider action is performed
by this publication.

Set on the API service only, after review; no `NEXT_PUBLIC_` setting is needed:

```dotenv
APP_ENVIRONMENT=development
TELEPHONY_PROVIDER_ENABLED=true
TELEPHONY_PROVIDER=telnyx_sip
DEVELOPMENT_ACTOR_USER_ID=<existing-active-operator-uuid>
ELEVENLABS_PHONE_AGENT_ID=<existing-private-phone-agent-id>
ELEVENLABS_PHONE_INITIATION_SECRET=<separate-random-32-to-512-character-secret>
ELEVENLABS_PHONE_TOOL_SECRET=<existing-phone-tool-secret>
ELEVENLABS_POST_CALL_WEBHOOK_SECRET=<existing-signed-post-call-secret>
ELEVENLABS_PRIVACY_CONFIRMED=true
PHONE_MAX_DURATION_SECONDS=180
PHONE_CONFIRMATION_WINDOW_MINUTES=30
```

Generate/store secrets in a password manager or secret manager. Copy the initiation
secret directly into the provider's private webhook header settings. It must
differ from the tool and HMAC secrets. Never put secrets in prompts, SIP headers,
URLs, dynamic variables, notes or frontend configuration. This initiation path
does not need `ELEVENLABS_API_KEY`; preserve that key if browser voice uses it.
Omit all four `TWILIO_*` values for Telnyx. For the shared Render Blueprint,
select `telnyx_sip` and omit its unused Twilio placeholders; preserve independent
browser settings. The Blueprint is an example, not a deployment action.

The existing enable flag remains an execution gate. Explicit provider `disabled`
or a false gate registers no telephone ingress. An omitted provider preserves
legacy Twilio selection. Switching back to Twilio requires its existing account,
signature URLs, auth token and ElevenLabs REST key. Disable/drain the old carrier
route before switching and retain webhook availability until its active calls
finalize. Existing calls and booked appointments are never deleted by selection.

No Telnyx migration or dependency installation is required beyond this repository's
existing dependencies/schema. Review any unrelated pending migrations in the
release before deployment. Deploy only after owner authorization; update the
API first, configure provider dashboards, then enable the execution gate. The
frontend already reads these call/appointment tables and needs no Telnyx changes.
Hosting deployment and provider configuration remain separate from the
owner-authorized main publication.

## Public phone number hidden — 2026-10-31

The owner requested removing the public business phone number. The homepage no
longer renders a phone panel or dial link, regardless of earlier configuration.
`HOMEPAGE_PHONE_NUMBER_E164` and `TELNYX_INBOUND_CALLING_VERIFIED` are no longer
used and can be removed from the frontend project. The sandbox phone-status page
also omits the number and dial link, while retaining its existing access gates.
Backend inbound-number routing and provider configuration are unchanged.

The simplified hero emphasizes browser voice AI with text chat as a secondary
choice. Voice still uses the existing signed-in booking workspace and explicit
microphone consent. Implementation/rendering are **UNVERIFIED**; owner commands
and manual acceptance are in [homepage hero](homepage-hero.md).

## Identity, replay and finalization

Initiation requires bearer authentication, the expected agent and a currently
active number in the operator's business. JSON bodies are capped at 16 KiB with
bounded fields/headers. SIP headers are ignored for authentication and routing
and never stored. Non-E.164 caller IDs become unknown callers; collect/confirm a
callback number rather than guessing one.

The call and its ElevenLabs conversation are persisted in one transaction under
the existing call-policy lock. A transaction advisory lock also prevents the same
provider conversation being claimed simultaneously across businesses. `call_id`,
when supplied, is stored as the SIP
source reference and provider ID. Empty/unsuitable initiation `call_sid` is ignored.
When `call_id` is absent, `source_call_reference` is explicitly
`conversation:{conversation_id}` until the real SIP ID is available in metadata;
this is a conversation identity, not a fabricated SIP/Twilio ID. Optional consent
`call_id` binds that real identifier without rewriting history. Duplicate accepted
initiation returns the same application UUID; mismatched identities, changed
caller/number, inactive/disabled routes, ended calls and expired initiation fail
closed. A missing real SIP ID does not stop UUID/conversation-bound tools or
signed transcript finalization.

Post-call transcript events must carry `phone_inbound_call_id` in initiation
dynamic variables and match the stored conversation. SIP initiation failures use
documented `metadata.type="sip"`, `metadata.body.call_sid` and the existing
conversation binding; failures before any accepted initialization cannot create
a business call. Unknown/mismatched events are rejected, not mapped by caller
number. HMAC freshness and event fingerprints protect finalization/replays.
[Official failure metadata](https://elevenlabs.io/docs/eleven-agents/workflows/post-call-webhooks).

Consent creates the existing PHONE session. Explicit readback creates the immutable
receipt. Confirmed HVAC requests/bookings use the existing immediate database
transactions; signed post-call finalization separately creates confirmed intake,
customer, lead and callback records. Unconfirmed call endings discard transcript
content; confirmed intake still requires a valid two-speaker transcript. Confirmed
appointments survive disconnect and post-call retries. No raw audio is saved.

## Audio and transport acceptance — UNVERIFIED

Start with documented TCP compatibility unless the owner's security policy
requires encryption from the outset. Check common G.711 PCMU/PCMA negotiation,
telephone sample rates and bidirectional RTP against both dashboards. SIP codec
negotiation is independent of direct WebSocket audio configuration. No custom
transcoding is implemented.

For the preferred secure setup, validate TLS to `sip.rtc.elevenlabs.io:5061` and
SRTP/media encryption on both ends, including certificates, region, firewall and
follow-up BYE behavior. Set encryption **Required** when mandated. An encryption
failure must stop setup; do not downgrade to TCP or unencrypted media to mask it.
[Official SIP transport/audio settings](https://elevenlabs.io/docs/eleven-agents/phone-numbers/sip-trunking).

## Human handoff

SIP live transfer is deliberately disabled: initialized call policy snapshots
record `live_transfer_supported=false`. `request-handoff` still authorizes and
audits the request through the existing policy/state machine. With callback
fallback enabled it returns `COLLECT_CALLBACK`; with fallback disabled it returns
`CONTINUE_AI` with the configured unavailability message. Neither result claims
that a human answered. Callback persistence still requires confirmed contact
details and signed finalization; no callback deadline or delivery is promised.
The Telnyx adapter rejects direct transfer execution and has no Twilio API path.

The documented future mechanism is ElevenLabs `transfer_to_number` with
`transfer_type="sip_refer"`, a SIP conversation and a trunk that permits REFER.
It must remain disabled in this release. Enabling it later requires backend
policy authorization of an allowlisted destination, call/conversation correlation,
configured agent/trunk permissions, and authenticated reliable terminal transfer
result handling before recording success. A tool request or REFER acceptance
alone does not prove that the receiving person answered. No unverified callback
schema or carrier endpoint is implemented. See
[official transfer behavior](https://elevenlabs.io/docs/eleven-agents/customization/tools/system-tools/transfer-to-number).

## Exact owner-run commands — NOT RUN

From the implementation worktree with Python 3.13 and the existing development
dependencies available:

```bash
cd /private/tmp/hvacline-browser-demo
python -m pytest tests/test_telnyx_sip_provider.py tests/test_telephony_provider.py tests/test_phone_conversation_provider.py
python -m ruff format --check apps/backend/src tests
python -m ruff check apps/backend/src tests
python -m mypy apps/backend/src tests
```

The database fixture **downgrades/rebuilds and finally downgrades** its target.
First explicitly confirm that exported `TEST_DATABASE_URL` names an isolated,
disposable PostgreSQL/Neon database, never the shared development/production
database. Retain the repository's SSL/isolation settings. Then:

```bash
APP_ENVIRONMENT=test python -m pytest tests/database/test_telnyx_sip_ingress.py tests/database/test_phone_receptionist_flow.py tests/database/test_telephony_provider_ingress.py tests/database/test_telephony_api.py tests/database/test_hvac_scheduling.py tests/database/test_whatsapp_calling.py
```

For release review on that same disposable target, after the fixture finishes:

```bash
APP_ENVIRONMENT=test python -m alembic upgrade head
APP_ENVIRONMENT=test python -m alembic current
APP_ENVIRONMENT=test python -m alembic check
```

These are owner commands, not executed results. The specs cover provider
selection/Twilio regression, auth/length/number/agent/tenant rejection, identity
binding, simultaneous duplicates and quota limits, shared tools, confirmed booking
surviving signed disconnect, replay/conflict handling, unconfirmed endings and
callback-only handoff without Twilio invocation. Automated success cannot prove
carrier connectivity or call quality.

## Live acceptance checklist — UNVERIFIED

- [ ] Owner approves the existing number, account use and any charges; no purchase
  or paid-service activation is implicit in this implementation.
- [ ] Confirm deployed revision, database schema, actor/number ownership, call
  policy, privacy/retention, region, audio, duration and spend controls.
- [ ] Dial the assigned Telnyx number externally. Confirm it reaches the existing
  HVAC receptionist and authenticated initiation succeeds with one stored call.
- [ ] Verify two-way audio, clear AI/provider disclosure, consent acceptance and
  refusal. Refusal/disconnect before readback must create no confirmed intake.
- [ ] Describe a service issue, correct the contact/address details, perform the
  complete readback, and confirm the service request. Verify FAQ answers use the
  business's approved facts; hazards escalate without an ordinary booking.
- [ ] Hear actual returned availability in the business timezone. Check outside
  service ZIPs, disabled schedules, occupied slots, expired holds and retries.
- [ ] Confirm an appointment separately. The agent says booked only after the
  tool returns CONFIRMED. Hang up immediately afterward and confirm the same
  request, appointment and call are visible in Operations after signed finalization.
- [ ] Repeat signed delivery and tool retries without extra leads/appointments;
  changed conversation bindings and another business's resources are rejected.
- [ ] Request a person with business transfer enabled: hear callback fallback,
  confirm contact, and inspect the callback record after signed finalization.
  There must be no Twilio command or false successful-transfer event.
- [ ] Verify the configured maximum stops the provider conversation, expiry
  rejects further tools, simultaneous calls obey limits and daily quota persists.
- [ ] Check missing/invalid webhook secrets, failed SIP initiation and declined
  consent; inspect reference/status-only logs and confirm no stored raw audio or
  unconfirmed transcript. Do not copy caller contents or secrets into evidence.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| SIP never connects | Number assigned to the right Telnyx FQDN connection; exact E.164 identifier; TCP/5060 or verified TLS/5061; region, firewall, ElevenLabs number import/agent assignment and source restrictions. Check provider error codes without logging caller content. Do not introduce inbound digest credentials. |
| Agent has no call context | Enable Security's initiation-webhook option, use `/sip/initialize`, include all required custom variables, and verify its successful response before any tool call. Dashboard Preview does not establish this inbound SIP path. |
| 401 initiation | Private Authorization bearer header must match the dedicated initiation secret, not the tool/HMAC secret. SIP headers do not authenticate this endpoint. |
| 403 initiation | Assigned agent must exactly match the API's configured private phone agent. |
| 404 routing | Number must be E.164, ACTIVE and owned by the configured operator's single active business. No caller-provided tenant may select it. |
| 409 binding/eligibility | Check number/policy state, actual conversation ID, terminated/expired call and changed call identity on replay. Do not replace the stored UUID or bypass ownership checks. |
| 429 initiation | Review concurrent/daily limits. Duplicate accepted initiation does not consume another slot. A missing signed terminal event can leave a call active: restore webhook delivery and use audited operator reconciliation; do not blindly release a carrier call that may still be live. |
| 413/422 | Body exceeds 16 KiB or fields fail the contract. Inspect safe validation paths/types using [the repair handoff](inbound-phone-webhook-repair.md); do not log payloads or assume which field failed. Digit-only international numbers are canonicalized at the SIP boundary; other number formats remain rejected. |
| One-way or distorted audio | Compare SDP codec offer/answer, PCMU/PCMA, RTP reachability/NAT and SRTP requirements on both sides; signaling success alone is insufficient. Do not add a custom audio gateway as a first fix. |
| Signed finalization fails | Correct per-agent destination and HMAC secret, fresh signature, persisted UUID dynamic variable, real conversation binding and documented SIP failure metadata. Replay a genuine signed event through provider-supported delivery; never synthesize confirmation from an ended call. |
| TLS/BYE failure | Check trust chain, matching remote domains and follow-up connection certificates. Preserve required encryption. |
| No confirmed appointment | Check real availability and explicit booking-tool result. A HELD reservation, intake receipt or ended call is not a confirmed booking; inspect the saved authoritative result before retrying. |
| Human transfer requested | Callback fallback is expected for Telnyx in this release. Keep the native transfer tool off; enabling it alone bypasses backend authorization/result accounting. |

Production tenant onboarding/identity, operational recovery, provider privacy and
real-call acceptance remain separate release gates. See the current project state
and existing integration runbooks; do not present this unverified implementation
as a proven live carrier deployment.
