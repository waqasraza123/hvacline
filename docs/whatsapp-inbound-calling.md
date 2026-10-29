# Inbound WhatsApp voice calling — UNVERIFIED

Direct ElevenLabs → HVACLine backend → Neon/Google Calendar. Inbound voice only. No outbound call, messaging, voice-note, campaign or native-transfer implementation. No provider calls, live settings, dependency installation, verification or deployment performed. Source formatting only was applied.

The repository's development identity gates and 180-second maximum remain. The owner removed fictional-data requirements on October 29; AI disclosure, voice-processing consent and exact readbacks remain required. One deployment binds one configured WhatsApp agent/Meta number to one verified agency membership. Existing browser Voice/Chat and optional Twilio paths remain available. See [deployment and owner checks](customer-data-requirements.md); the hosted agent must receive the updated exact disclosure before using the new backend.

## Verified documentation contracts

Read on 2026-10-28:

- [WhatsApp](https://elevenlabs.io/docs/eleven-agents/whatsapp), [getting started](https://elevenlabs.io/docs/eleven-agents/whatsapp/getting-started), [troubleshooting](https://elevenlabs.io/docs/eleven-agents/whatsapp/troubleshooting).
- [Initiation webhook](https://elevenlabs.io/docs/eleven-agents/customization/personalization): authenticated POST, including `agent_id`, `conversation_id`, `caller_id`, `called_number`, `call_sid`. WhatsApp uses an empty `call_sid`; caller is a WhatsApp user ID/BSUID, destination is a Meta phone-number ID. Response is `conversation_initiation_client_data` with `dynamic_variables`.
- [Post-call webhook](https://elevenlabs.io/docs/eleven-agents/workflows/post-call-webhooks): raw-body HMAC via `ElevenLabs-Signature`, `t=…,v0=…`, event type/time and `data.agent_id`/`data.conversation_id`. The adapter accepts transcription and initiation-failure events. It ignores transcript/analysis/dynamic-variable contents and never derives a booking from them.
- [System/secret dynamic variables](https://elevenlabs.io/docs/eleven-agents/customization/personalization/dynamic-variables): history uses a JSON string containing `entries` with user/agent messages and optional tool-only entries. Secret variables belong only in tool headers; post-call payloads can contain their original values, so never log webhook bodies.

No caller identifier authorizes access. Initialization requires a dedicated secret plus configured agent and destination. Every tool additionally requires its own secret, an expiring call-bound token, matching provider conversation ID, voice mode, active agency membership and session ownership. Only a keyed digest of the WhatsApp caller ID is retained. Contact numbers must be spoken and separately confirmed.

## Backend configuration

Set these on the API only; never use `NEXT_PUBLIC_` names:

| Variable | Required setting |
| --- | --- |
| `WHATSAPP_ENABLED` | `true` only after owner setup/verification |
| `WHATSAPP_AGENCY_ID` | Existing development agency UUID |
| `WHATSAPP_ACTOR_USER_ID` | Existing active user with exactly one active development membership in that agency |
| `ELEVENLABS_WHATSAPP_AGENT_ID` | Dedicated WhatsApp agent ID |
| `ELEVENLABS_WHATSAPP_PHONE_NUMBER_ID` | Meta phone-number ID copied from ElevenLabs; not E.164 |
| `ELEVENLABS_WHATSAPP_INIT_SECRET` | Random secret, at least 32 characters; initiation header |
| `ELEVENLABS_WHATSAPP_TOOL_SECRET` | Different random secret, at least 32 characters; tool bearer header |
| `ELEVENLABS_WHATSAPP_SESSION_SECRET` | Different random secret, at least 32 characters; backend-only signing key |
| `ELEVENLABS_WHATSAPP_POST_CALL_SECRET` | ElevenLabs-generated HMAC secret, at least 32 characters |
| `ELEVENLABS_WHATSAPP_PRIVACY_CONFIRMED` | `true` after reviewing provider retention/privacy for fictional testing |

All four secrets must differ. Rotating the session key invalidates active calls; drain calls first. Retain `APP_ENVIRONMENT=development`, existing database/API settings and `CONVERSATION_MAX_DURATION_SECONDS`/`CONVERSATION_DAILY_SESSION_LIMIT`. Defaults remain 180 seconds, one concurrent conversation, ten daily authorizations. WhatsApp pending initialization attempts are also limited, including declined-consent calls. No consent timestamps are fabricated during initialization.

For a WhatsApp-only telephone setup, keep `TELEPHONY_PROVIDER_ENABLED=false`; no Twilio credentials, inbound-number row or Twilio call SID is required. Keep existing browser settings unchanged. WhatsApp itself requires no ElevenLabs REST API key: media is provider-managed and backend requests are authenticated webhooks/tools.

Retain existing Calendar/notification configuration: `GOOGLE_CALENDAR_ENABLED`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `CALENDAR_TOKEN_ENCRYPTION_KEY`, `BOOKING_EMAIL_ENABLED`, `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `BOOKING_EMAIL_FROM`, `BOOKING_REMINDER_HOURS`, and existing job/worker settings including `BOOKING_JOBS_SECRET` or `WORKER_POLL_SECONDS`. These are not new WhatsApp settings. See [Calendar and messages](calendar-and-booking-messages.md) and [booking jobs](vercel-booking-jobs.md). A writable team calendar must actually be connected in Operations → Scheduling; an unconnected team uses the existing internal calendar.

Migration `20261028_0013` adds `whatsapp_conversations` and permits `WHATSAPP` sessions without `inbound_call_id`. Prior revisions are unchanged. Downgrade refuses to discard WhatsApp records. Apply the forward migration before enabling the feature. The backend needs an owner-managed release; Operations uses its existing projections and requires no WhatsApp-specific frontend release.

## Exact Meta and ElevenLabs setup

1. Use a Meta business portfolio you administer and an eligible number. In Meta Business Settings → WhatsApp accounts, check ownership/Partners first. The documented import excludes numbers already registered to another provider or the WhatsApp Business app, and WABAs created under a developer app. Do not disconnect an existing production number just to test; use an eligible dedicated number.
2. Create a dedicated ElevenLabs agent; keep the browser and Twilio agents unchanged. In ElevenLabs → WhatsApp → Import account, complete Meta authorization, select the business account/number and grant the requested permissions. Copy its phone-number ID into `ELEVENLABS_WHATSAPP_PHONE_NUMBER_ID` and assign this agent to the account.
3. Turn **Enable messaging off** on this imported account. In Meta WhatsApp Manager → Phone numbers → select number → Call settings, enable voice calls. Complete any Meta eligibility/payment requirements shown for the account. Do not create outbound templates, campaigns, outbound-call jobs, messaging tools or transfer tools.
4. Choose the voice/model intentionally, set maximum conversation duration to the same backend maximum (default 180 seconds), disable audio recording and audio webhooks, and review transcript retention/deletion and privacy. Use test data for owner acceptance. Configure the End call system tool so refusal, unsupported requests and expired sessions can terminate safely.
5. In ElevenAgents settings, configure the initiation webhook URL as `https://YOUR_API_ORIGIN/api/v1/providers/elevenlabs/whatsapp/initialize`. Add an `Authorization` header secret containing `Bearer ` followed by `ELEVENLABS_WHATSAPP_INIT_SECRET`. On the dedicated agent's Security tab enable **Fetch initiation client data from a webhook**. Scope routing to this agent; preserve other agents' existing initiation configuration. If the workspace exposes only a shared webhook, use an owner-managed dispatcher that preserves those routes rather than replacing them. Do not enable prompt/voice overrides to make initialization work.
6. Configure a dedicated agent post-call webhook/override at `https://YOUR_API_ORIGIN/api/v1/providers/elevenlabs/whatsapp/post-call`, with HMAC authentication, transcription events, initiation failures if offered, retries on, **Send audio data off**. Copy its generated signing secret to `ELEVENLABS_WHATSAPP_POST_CALL_SECRET`. Preserve the current Twilio webhook. If your account cannot scope these settings, a dispatcher preserving existing routes is required before activation.
7. Define exactly these custom dynamic variables: `whatsapp_binding_id`, `whatsapp_session_id`, `secret__whatsapp_session_token`. Initialization supplies all three, with session ID initially empty. Never place the secret variable in a prompt, first message, URL or body, and never let a tool assignment overwrite the binding/token. Do not require any other custom variable unless the backend initialization contract is deliberately extended.
8. Add Webhook tools below. Give the consent tool a dynamic-variable assignment from response path `session_id` to `whatsapp_session_id`. Set each `{session_id}` path parameter from that dynamic variable. An `{appointment_id}` must come from an actual reservation response. Use **Dynamic variable**, not **LLM Prompt**, for history and system-derived authentication fields.
9. Set the first message to the exact disclosure below and use the agent procedure below. Finish owner verification before accepting inbound calls. If initiation does not arrive authenticated with the documented identifiers, or system-history/secret-header configuration is unavailable, stop activation; do not add an unauthenticated tool or infer identifiers.

Exact first message:

```text
I am HVACLine's AI receptionist. ElevenLabs processes this WhatsApp voice call. May I process your voice and, after a separate readback confirmation, save the confirmed details and transcript? Reply yes to continue, or no to end the call.
```

### Tool configuration

All tools use POST, JSON bodies and the same API origin. The base path is `/api/v1/providers/elevenlabs/whatsapp`. All require:

| Header | Value source |
| --- | --- |
| `Authorization` | Secret: `Bearer ` + `ELEVENLABS_WHATSAPP_TOOL_SECRET` |
| `X-HVACLine-Binding-ID` | Dynamic variable `whatsapp_binding_id` |
| `X-HVACLine-Session-Token` | Dynamic variable `secret__whatsapp_session_token` |
| `X-ElevenLabs-Conversation-ID` | System dynamic variable `system__conversation_id` |
| `X-ElevenLabs-Text-Only` | System dynamic variable `system__is_text_only`, serialized as lowercase `false` for voice |
| `Content-Type` | `application/json` |

For every `provider_history` body field below use the string value of system dynamic variable `system__conversation_history`. Never generate/summarize it with the LLM. It is parsed in memory; only explicitly confirmed intake history is retained. Do not configure a `transcript` body field for WhatsApp.

| Tool name | Path after base | JSON body |
| --- | --- | --- |
| `whatsapp_consent` | `/consent` | `ai_disclosure_accepted`, `voice_processing_accepted`: booleans; `provider_history`: system history string |
| `whatsapp_faq` | `/sessions/{session_id}/faq` | `query`: string, 1–500 characters |
| `whatsapp_intake_readback` | `/sessions/{session_id}/booking/intake-readback` | `customer`, `service` objects described below |
| `whatsapp_confirm_intake` | `/sessions/{session_id}/confirm-intake` | Identical `customer`, `service`; `provider_history` |
| `whatsapp_availability` | `/sessions/{session_id}/booking/availability` | `day`: `YYYY-MM-DD` in business timezone |
| `whatsapp_reserve` | `/sessions/{session_id}/booking/reservations` | `team_key`, `starts_at`: exactly from availability; `idempotency_key`: stable 8–128-character key using letters, digits, `_ . : -` |
| `whatsapp_confirm_appointment` | `/sessions/{session_id}/booking/appointments/{appointment_id}/confirm` | `explicit_confirmation`: boolean; `provider_history` |
| `whatsapp_release_hold` | `/sessions/{session_id}/booking/appointments/{appointment_id}/release` | Empty object |
| `whatsapp_hazard` | `/sessions/{session_id}/booking/hazard` | Empty object |
| `whatsapp_callback_readback` | `/sessions/{session_id}/callback-readback` | `customer`: caller-supplied name, callback phone, optional email |
| `whatsapp_callback` | `/sessions/{session_id}/callback` | Same `customer`; `reason`: 1–1000 characters; optional `availability`: 1–500 characters; `provider_history` |

`customer`: `full_name` (1–200 characters), `phone` (a valid caller-supplied telephone number), optional `email` (valid email), and `address` for HVAC intake: `line1`, optional `line2`, `city`, two-letter `state_code`, five-digit `postal_code`, `country_code="US"`. Phone/name/contact are mandatory for callbacks; address/service are not. Callback after an existing saved intake must use its exact confirmed contact details.

`service`: `kind` in `AC_REPAIR`, `HEATING_REPAIR`, `INSTALLATION`, `MAINTENANCE`; `equipment_issue` (1–2000 characters), `preferred_window` (1–300 characters), `hazardous_condition` boolean. Shorten descriptions when instructed by the backend readback length bound; never omit required facts from a readback.

Agent procedure:

1. Read the exact disclosure, wait for explicit acceptance, then call consent. A no/refusal ends the call; never authorize consent from silence or a tool-generated boolean alone. Do not call business tools before successful consent.
2. Answer only matched agency FAQs; unknown answers require callback/human attention. Qualify the HVAC issue, service location, requested window and hazards. Never infer a callback number from caller ID or BSUID.
3. For a booking, collect complete intake, call intake-readback, read its entire `readback` verbatim and wait for a new clear yes. Corrections require a fresh readback. Call confirm-intake with the current system history; continue only after success.
4. Query real availability. Speak slots in the returned timezone; use business date/time from intake-readback. Reserve exactly a returned slot. Keep the same reservation key/payload for uncertain retries; release the previous hold before deliberately choosing a different slot.
5. Read the reservation's entire `readback` verbatim and wait for a separate clear yes. Call confirm-appointment. Say “booked” only if the backend returns `appointment.status=CONFIRMED`. HELD is temporary. On a failure/expiry, do not claim success; explain recovery or offer callback. Calendar errors do not justify inventing availability.
6. For hazards: give the existing immediate-danger guidance, avoid booking, save only explicitly confirmed details, then flag-hazard and offer callback. If full intake is unavailable, callback-only can still record separately confirmed contact without an appointment. Never attempt native WhatsApp transfer.
7. For human help, collect name/callback phone and optional email, call callback-readback, read it verbatim and wait for a new clear yes; call callback with identical contact and current history. Only a successful backend response means a callback request was saved. If the caller declines contact storage, end without saving it.
8. On expiry/end do not resume using old IDs/tokens; begin a new inbound call. Never expose headers, secret variables, provider identifiers, tool payloads or database internals to the caller.

## Owner-run verification

All implementation and runtime behavior remain **UNVERIFIED**. Commands below were not executed. Run from the feature checkout with your existing Python environment. Database tests downgrade/rebuild their database: `TEST_DATABASE_URL` must be explicitly isolated, disposable and different from all runtime/direct URLs.

```sh
python -m pytest tests/test_whatsapp_provider.py tests/test_browser_spoken_confirmation.py tests/test_phone_conversation_provider.py tests/test_telephony_provider.py
APP_ENVIRONMENT=test python -m pytest tests/database/test_whatsapp_calling.py tests/database/test_conversation_api.py tests/database/test_phone_receptionist_flow.py tests/database/test_hvac_scheduling.py tests/database/test_booking_jobs.py tests/database/test_migrations.py tests/database/test_table_ownership.py
ruff format --check apps/backend/src/insurance_operations/whatsapp apps/backend/src/insurance_operations/conversations apps/backend/src/insurance_operations/database/models tests/test_whatsapp_provider.py tests/database/test_whatsapp_calling.py migrations/versions/20261028_0013_whatsapp_conversations.py
ruff check .
mypy apps/backend/src tests
npm run verify:web
```

For a separate disposable migration/drift check, after the database-test fixture has finished:

```sh
APP_ENVIRONMENT=test alembic upgrade head
APP_ENVIRONMENT=test alembic current
APP_ENVIRONMENT=test alembic check
```

Only after reviewing those results, the owner can apply the new forward migration to the intended development Neon database and release the backend. Neither migration nor release has been performed here.

## Complete manual call-to-booking scenario

1. Use fictional data, a connected writable test Google calendar, a configured service ZIP/team and a future available working-day slot. Keep Twilio disabled and its credentials absent. Ensure the existing notification job is configured if testing email delivery.
2. From personal WhatsApp, **voice call** the imported business number. Confirm the exact AI/voice-processing disclosure, then explicitly accept. Verify initialization produced one binding and consent one WHATSAPP session with no Twilio call ID. Declining in a separate call must save no intake/appointment.
3. Ask an approved HVAC FAQ. Then request fictional AC repair at a complete test address in the configured ZIP, give a caller-supplied callback number and a controlled test email address. State there is no hazardous condition.
4. Hear the full intake/address/contact/storage readback and reply yes. Ask for an available future slot. After the agent holds it, confirm it says it is not yet booked; check Operations shows no confirmed appointment at this point.
5. Hear the full appointment date/time/timezone readback and reply yes again. The agent must wait for backend CONFIRMED before announcing success. End the call.
6. In Operations verify one saved request, one CONFIRMED appointment, matching contact/time/team, lead/audit history and no duplicate after webhook retries. In Neon confirm the agency-owned WHATSAPP linkage and ended session. Verify one matching Google event, notification outbox state, eventual confirmation email and no raw audio storage. The WhatsApp user identifier must never become the callback number automatically.
7. Regression acceptance: browser Voice and Chat still book normally; existing Twilio handling remains unchanged when separately enabled. Additional calls: decline appointment consent, correct contact details, choose an unavailable slot, lose/retry a tool response, exceed quotas, pass an expired/wrong-session token, report a hazard, request callback before full intake and request callback after saved intake. No unauthorized or duplicate booking may result. Text messages/voice notes must produce no response with messaging disabled.

## Remaining activation blockers

Owner execution, migration, Meta eligibility/import/calling permissions, HTTPS webhook access, agent tool/header/history/assignment setup, privacy approval, connected Google calendar and notification job acceptance remain pending. Real-customer production operation remains blocked by the existing development identity/consent/privacy gates. The documented secure initialization path is supported; no contract workaround was introduced. If your account delivers a different initiation/history contract or lacks scoped webhook routing, keep this integration disabled and resolve that with ElevenLabs before activation.
