> HVACLine AI: read [the current live-validation runbook](hvacline-live-validation.md) first. This adapter reference predates HVAC scheduling; its old product restrictions and status notes are historical.

# ElevenLabs Phone Agent Setup

Create a private phone agent separate from the browser agent. Use controlled test
data for owner acceptance. See [current deployment and owner checks](customer-data-requirements.md)
for the removal of fictional-data requirements and the required schema update.

## Audio and privacy

- Select the owner-approved LLM, STT, TTS, and voice explicitly.
- Set both telephone input and output to μ-law 8000 Hz.
  For direct SIP, negotiate supported G.711 PCMU/PCMA with the trunk; see
  [Telnyx SIP setup](telnyx-sip-setup.md) for audio and security acceptance.
- Set the maximum conversation duration to 180 seconds.
- Disable audio saving, recordings, exports, analysis destinations, and audio
  post-call webhooks.
- Set transcript retention to the shortest available duration, enable ZRM when
  available, opt out of model improvement, disable backup LLM fallback, and set a
  finite billing guard.
- Configure only the signed `post_call_transcription` and
  `call_initiation_failure` webhook events at
  `/api/v1/providers/elevenlabs/post-call`.

## Agent behavior

The first message must disclose that the caller is speaking to AI and that provider
processing occurs. Ask
the caller to explicitly agree before collecting or answering anything.

The system prompt must enforce this sequence:

1. Obtain explicit agreement and call `accept_phone_consent`.
2. Answer agency facts only through `lookup_phone_approved_faq`.
3. Collect a full name, one contact method, and a short intake intent.
4. Read the structured intake back exactly and ask for an explicit spoken yes.
5. Only after yes, call `confirm_phone_intake` once. Explain that finalization
   occurs after the call; do not claim the lead is already saved.
6. Use `request_phone_handoff` for human assistance. Twilio register-call uses
   the backend's active-call transfer API. Telnyx SIP returns callback fallback;
   keep the native `transfer_to_number` tool disabled until trustworthy SIP
   transfer-result handling is implemented and accepted. Never claim a transfer
   succeeded from a request alone.
7. End at 180 seconds or immediately when consent is declined or a prohibited
   action is requested. Do not request payment details, passwords or authentication codes.

The agent must never quote, advise, bind, recommend limits, verify coverage,
determine eligibility, make claims decisions, or improvise an agency answer.

## Webhook tools

Configure every tool with an `Authorization: Bearer <phone-tool-secret>` header
stored in the ElevenLabs secrets manager. Never put the secret in prompts,
parameters, repository files, or dynamic variables.

Use `{{phone_inbound_call_id}}` for `inbound_call_id` and
`{{system__conversation_id}}` for `conversation_id`.
For Telnyx, the authenticated initiation webhook supplies `phone_inbound_call_id`;
never substitute `system__call_sid`. Optionally add `call_id={{system__call_id}}`
to `phone-consent` so the backend can bind the real SIP identifier when it was
absent at initiation. Existing Twilio tool payloads need no change. Configure
the two required custom variables and all eight shared HVAC tools from the live
validation runbook; remove stale/custom variables that this backend does not supply.

- `accept_phone_consent` → `POST /api/v1/providers/elevenlabs/tools/phone-consent`
  with the two identifiers, `ai_disclosure_accepted=true` and
  `microphone_consent_granted=true`, only after explicit caller acceptance.
- `lookup_phone_approved_faq` →
  `POST /api/v1/providers/elevenlabs/tools/approved-faq` with the identifiers and
  the caller's complete `query`.
- `confirm_phone_intake` →
  `POST /api/v1/providers/elevenlabs/tools/confirm-intake` with the identifiers,
  `customer`, `intake_intent`, `urgency`, and
  `explicit_verbal_confirmation=true`.
- `request_phone_handoff` →
  `POST /api/v1/providers/elevenlabs/tools/request-handoff` with the identifiers
  and `kind` set to `LIVE_TRANSFER` or `CALLBACK`.

All tools are blocking. A tool rejection or malformed response must produce a
safe human-follow-up message, never an improvised result.

## Dashboard verification

Confirm the effective audio, privacy, region, model, voice, tool authentication,
post-call HMAC, retention, duration, and billing settings manually. Only then set
`ELEVENLABS_PRIVACY_CONFIRMED=true` and enable the provider in development.
