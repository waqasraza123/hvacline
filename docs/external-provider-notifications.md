# External provider notifications — UNVERIFIED

Interactive web requests show shared Sonner error toasts for identified provider
failures. Provider names and failure categories come from allowlisted metadata;
application authentication errors, input validation and browser-to-app network
errors do not imply an upstream provider failure. Existing inline errors remain.

Supported outgoing adapters cover ElevenLabs, Stripe, Google Calendar,
GoHighLevel, Resend, Telnyx, Twilio and OpenAI/compatible text models. Ollama HTTP
requests are observed when a collector is active; local voice WebSockets do not
have a browser toast delivery channel. Provider setup and activation flags are
unchanged. No new migration or environment variable is required.

## Behavior and boundaries

- Backend HTTP requests collect at most eight distinct provider/category pairs in
  request-local context, including synchronous handler threads and nested calls.
  Only provider/category metadata is exposed in `X-External-Failures`, CORS or
  handled API error details. Raw provider bodies, messages and credentials are
  never copied into this metadata.
- Categories are billing, access, rate limit, timeout, unavailable and rejected.
  Buffered HTTP responses may refine the category using known structured error
  codes. Streaming responses use available status/metadata without reading an
  unbounded error body. No balance lookup occurs.
- A handled API error with status 5xx and an observed upstream failure returns
  HTTP 424. Existing error codes and details are preserved. Application errors
  without observed provider failures retain their status. Success responses may
  carry metadata for an upstream failure that the application already handled.
- Customer/website/billing/workspace/recovery proxies preserve only allowlisted
  notification headers. Homepage chat and outbound-demo proxies additionally
  preserve the approved ElevenLabs account marker in their bounded responses.
- Shared browser fetch handling inspects a clone of JSON responses, bounded to
  1 MiB even without Content-Length, and leaves the original response readable.
  Server-side calls bypass client notifications. Notification failures do not
  change request outcomes or cause retries.
- Stable toast IDs collapse repeated reports for a provider/category into one
  visible toast. Precise metadata takes precedence over a legacy generic code
  for the same provider. Toasts are dismissible, theme-aware and last ten seconds.
- ElevenLabs account restrictions retain the owner's exact credit/refill wording
  and toast ID, with no second generic billing/access toast. See
  [ElevenLabs copy and detection](elevenlabs-error-toasts.md). Other categories
  explain the provider failure without asserting a measured balance. SDK normal
  endings and microphone-permission errors do not generate provider toasts.
- Workers do not push browser notifications. Calendar reconciliation, recovery
  delivery, AI model requests and Resend delivery save safe provider failure codes
  where existing status fields support them. Loading supported dashboard history
  or settings can show those saved failures. Older generic failures are only
  mapped when their existing code identifies a provider.
- Booking/delivery state, unknown outcomes, idempotency keys, retry windows,
  authorization and no-redial controls retain their existing rules. A toast
  never authorizes repeating a call, purchase, booking or message.

## Owner commands

Implementation and runtime/visual acceptance remain **UNVERIFIED**. No tests,
builds, linters, type checks, services, migrations or live provider requests were
run for this completion. Deploy both backend and frontend together after owner
acceptance; install the updated lockfile using the repository's Node 24.

From the repository root and the existing Python development environment:

```sh
npm ci --ignore-scripts
npm run test:web -- src/lib/external-failures.test.ts src/lib/elevenlabs-errors.test.ts src/features/customer/proxy.test.ts src/features/conversation/api.test.ts src/features/conversation/elevenlabs-adapter.test.tsx src/app/api/homepage-chat/route.test.ts src/app/api/outbound-demo/route.test.ts
npm run typecheck:web
npm run lint:web
npm run build:web
APP_ENVIRONMENT=test python -m pytest tests/test_external_failures.py tests/test_elevenlabs_errors.py tests/test_conversation_provider.py tests/test_homepage_chat_provider.py tests/test_outbound_demo.py tests/test_booking_integrations.py tests/test_staff_alerts.py tests/test_recovery_delivery.py tests/test_billing.py tests/test_ghl.py
python -m ruff check apps/backend/src/insurance_operations tests
python -m mypy apps/backend/src/insurance_operations
```

Database regression commands and their disposable-database requirement are listed
in [the ElevenLabs guide](elevenlabs-error-toasts.md#owner-commands). Never run them
against an application database.

## Manual checks

1. Mock provider failures on the owner's running app: Stripe billing, Calendar
   access/rate limiting, GHL access, Resend timeout, Telnyx verification, Twilio
   recovery and OpenAI quota. Confirm one correctly named toast per category,
   readable inline errors and unchanged saved operation status. Use synthetic
   data and mock responses; paid calls and sends are unnecessary.
2. Exercise direct dashboard API access and same-origin customer, website,
   billing, workspace, recovery, homepage-chat and outbound-demo proxies. Confirm
   the safe metadata survives and bodies, correlation/ownership controls and
   idempotency behavior remain usable.
3. Load saved Calendar/email/recovery/AI failures, refresh, then load a successful
   response. Confirm stable IDs prevent simultaneous duplicate toasts; legacy
   generic codes do not add a second toast beside precise metadata.
4. Mock application 401/403/500, validation errors, trial exhaustion, browser
   network failure, microphone denial and ordinary conversation endings. Confirm
   no incorrect provider or credit toast. Repeat the ElevenLabs-specific cases
   and approved wording checks in its guide.
5. Inspect desktop/mobile and both themes, including an open dialog: text wraps,
   toast is announced, dismissal works by keyboard, no horizontal overflow and
   automatic dismissal occurs. Inspect network output for safe metadata only.
6. Confirm unknown call/purchase/message outcomes still require reviewing saved
   status; the notification never redials, resends, rebooks or creates a new key.
