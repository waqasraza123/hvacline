# HVACLine AI Live Validation

Status: synthetic development only. A real carrier call is not yet verified. This runbook does not authorize purchasing a telephone number, enabling paid billing, or using real customer data.

For the new alternative carrier, follow [Telnyx SIP setup](telnyx-sip-setup.md).
Telnyx requires neither Twilio credentials nor register-call. Its initiation
webhook and existing signed ElevenLabs finalizer share the same booking path.
Telnyx implementation, provider configuration and real-call acceptance remain
**UNVERIFIED**. The current owner decision in `customer-data-requirements.md`
supersedes the historical fictional-data requirement here; existing development
identity, consent and confirmation gates remain.

## Prepare the backend and workspace

1. Apply migrations through `20261024_0009` on an owner-selected development Neon branch. Do not downgrade a shared database.
2. Run the development seed. Existing fixture data must be reviewed for old insurance wording before showing the agent; never overwrite customer configuration automatically.
3. Configure the public HTTPS API origin and `WEB_ORIGIN`. For hosted development, enable the sandbox and set a strong server-only demo admin token. Keep public status sanitized.
4. Open `/operations`; enter the admin token. Configure timezone, ZIP codes, opening hours, named technician teams and hours, time off, visit duration, notice, and cancellation notice. Explicitly enable the internal booking calendar. No availability is seeded.
5. Configure approved business FAQs and the receptionist profile for Harborline Heating & Air. Never enter unsupported prices or response-time commitments.

## Configure an already authorized test number

Supply the existing server-only settings: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_INBOUND_WEBHOOK_URL`, `TWILIO_TRANSFER_CALLBACK_URL`, `ELEVENLABS_API_KEY`, `ELEVENLABS_PHONE_AGENT_ID`, `ELEVENLABS_PHONE_TOOL_SECRET`, and `ELEVENLABS_POST_CALL_WEBHOOK_SECRET`. Set the demo inbound and transfer destination numbers only to owner-authorized test numbers.

These carrier settings apply to `TELEPHONY_PROVIDER=twilio`. The Telnyx setup
guide lists the separate configuration for `TELEPHONY_PROVIDER=telnyx_sip`.

Twilio inbound webhook: `POST /api/v1/providers/twilio/inbound`.
Twilio transfer result: `POST /api/v1/providers/twilio/transfer-result`.
ElevenLabs signed post-call webhook: `POST /api/v1/providers/elevenlabs/post-call`.

Configure the separate private ElevenLabs phone agent. Preserve shortest supported retention, no saved raw audio, no model-improvement use, explicit model/STT/TTS/voice selection, privacy attestation, and provider spend controls. Real-data and production use remain blocked. Only after dashboard validation, enable `TELEPHONY_PROVIDER_ENABLED` in development and set `ELEVENLABS_PRIVACY_CONFIRMED`.

## Phone-agent instruction contract

You are Harborline Heating & Air's AI receptionist. Say that you are AI. Disclose provider voice processing and obtain AI disclosure and microphone consent with `phone-consent`. Do not proceed after refusal. Do not ask callers to use fictional details.

Handle AC repair, heating repair, installation inquiries, and maintenance. Ask for name, callback number, complete U.S. service address, equipment issue, requested service, and preferred appointment window. Accept corrections before readback. Never invent prices, facts, appointment slots, service-area coverage, diagnosis, or response commitments. Never give equipment repair instructions. If the caller reports gas odor, smoke, a carbon monoxide alarm, electrical danger, or another hazard, prioritize human/emergency escalation and do not book an ordinary appointment. Use approved safety wording reviewed by the business; never suggest trying repairs.

Use the backend tools in this order:

1. `phone-consent`: existing consent contract, including `inbound_call_id` from `phone_inbound_call_id` and the real provider `conversation_id` from the provider's system conversation variable. These identifiers must not be user-entered.
2. `approved-faq`: answer business questions only from a successful source-backed result.
3. `confirm-intake`: read the caller's contact details and request back, obtain explicit verbal confirmation, and save the existing receipt.
4. `service-request`: send call context, customer `{full_name, phone, email?, address:{line1, line2?, city, state_code, postal_code, country_code:"US"}}`, service `{kind, equipment_issue, preferred_window, hazardous_condition}`, and `explicit_confirmation:true` only after readback of all service details. `kind` is AC_REPAIR, HEATING_REPAIR, INSTALLATION, or MAINTENANCE. Use the saved `service_request_id` from the tool result.
5. `availability`: send call context, five-digit `postal_code`, and ISO `day`. Offer only returned slots. `configured:false`, out-of-area, empty slots, or errors require another date or a callback offer.
6. `reserve-appointment`: send call context, saved service request ID, the returned `team_key` and timezone-aware `starts_at`, and a stable `idempotency_key` (8–128 ASCII letters, digits, underscore, dot, colon, hyphen). Retry the same request with the same key. A HELD result is a five-minute reservation, not a confirmed booking.
7. `confirm-appointment`: read the actual returned date/time in the business timezone, obtain agreement, then send call context, `appointment_id`, and `explicit_confirmation:true`. Say the appointment is booked only after the tool returns CONFIRMED. On uncertainty, say it could not be confirmed and request human follow-up.
8. `request-handoff`: existing CALLBACK or LIVE_TRANSFER contract. Never say a person answered merely because a transfer was requested. No promised callback deadline.

All tool URLs share `/api/v1/providers/elevenlabs/tools/`. Use POST JSON and a secret `Authorization: Bearer <ELEVENLABS_PHONE_TOOL_SECRET>` header configured in the provider; never expose that secret in model prompts or dynamic variables.

Service request persistence occurs after explicit consent and structured readback, without transcript storage. Signed post-call finalization still controls the existing customer/intake/lead transcript transaction. If a call ends before booking, the request can remain OPEN; if no explicit service readback happened, no new HVAC request is saved. Unconfirmed holds expire automatically for capacity calculations. Confirmed appointments survive a later disconnect and must be checked in the workspace if the caller did not hear the response.

## Acceptance calls

Use fictional contact and address details. Verify happy path, caller correction, out-of-area ZIP, disabled scheduling, fully occupied technician, expired hold, repeated tool request, provider timeout, disconnect before confirmation, disconnect after confirmation, declined consent, urgent hazard, successful transfer, failed transfer, callback request, and signed post-call replay.

For each successful booking, inspect the persisted request, appointment, audit events, and post-call customer/lead in the same business. Verify a second business cannot read or change them. Confirm no raw audio or unconfirmed transcript was retained. Record call time, source version, result, and failures without logging caller content or credentials.

## Still blocked for real clients

Production authentication and tenant onboarding; per-business provider credential/agent provisioning; externally connected calendars and OAuth; caller verification for existing-customer changes; durable confirmations and urgent notifications; billing and detailed usage; automatic retention; production deployment/recovery validation. These are required before removing the development-only gates.
