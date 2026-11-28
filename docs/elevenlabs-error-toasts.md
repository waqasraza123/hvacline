# ElevenLabs account error toast — UNVERIFIED

Shared multi-provider behavior, status/history notifications and completion
checks: [External provider notifications](external-provider-notifications.md).

The requested message is:

> Our agents were about to respond, but we detected that your ElevenLabs credits are 0. Refill your balance to try again.

Sonner 2.0.8 supplies a shared, theme-aware, dismissible error toast. It remains
visible for ten seconds; a stable ID prevents multiple simultaneous copies when
SDK callbacks report the same failure. Its message is fixed application copy,
not a live credit-balance lookup. Account-access failures use this same copy at
the owner's request.

Only identified **external ElevenLabs** billing, credit or access restrictions
trigger this specific message. Other identified provider failures use category-
specific toasts. Application authentication/authorization failures, browser network
errors and unrelated server errors retain their existing handling. In particular,
an application 401/403 or the homepage visitor's
remaining allowance of zero never implies an ElevenLabs credit failure.

## Error flow

- Upstream ElevenLabs HTTP 402/403 and recognized legacy/current account error
  codes carry only `provider_error_code: ELEVENLABS_ACCOUNT_RESTRICTED` to the web
  client. Raw provider bodies and credentials are not returned.
- Conversation authorization (including website voice and multilingual checks)
  and homepage chat return HTTP **424 Failed Dependency** for this restriction,
  preserving existing cleanup, outcome codes and visitor allowance accounting.
  These handled failures do not produce an application server error page.
- SDK error callbacks, connection failures and disconnect reasons are inspected
  at the ElevenLabs adapter boundary. Other providers and application errors do
  not use SDK message matching. SDK and authorization error text also uses the
  requested wording where an existing inline error is displayed.
- Demo-call preflight/dial failures preserve existing no-redial and unknown-outcome
  rules and add an optional safe marker to the immediate call response. It is a
  notification for that response, not persisted billing state. The toast does not
  authorize another call. Provider refresh errors also use handled HTTP 424.
- The homepage and outbound web proxies forward only the allowlisted marker.
  Background recovery jobs and incoming phone/webhook processing have no live
  browser toast channel; this slice covers interactive web conversation/demo
  entry points and their external provider errors.

Sonner was added to the web manifest and root lockfile with a metadata-only,
script-disabled npm install. No tests, builds, linters, type checks, migrations,
services or live provider calls ran. Implementation,
external-provider acceptance and visual/accessibility behavior are **UNVERIFIED**.
Both backend and frontend changes are needed for failures previously hidden behind
generic responses. There is no new migration or provider setting.

## Owner commands

Use the repository's Node 24 and existing Python development environment.
From the repository root:

```sh
npm ci --ignore-scripts
npm run test:web -- src/lib/elevenlabs-errors.test.ts src/features/conversation/api.test.ts src/features/conversation/elevenlabs-adapter.test.tsx src/app/api/homepage-chat/route.test.ts src/app/api/outbound-demo/route.test.ts
npm run typecheck:web
npm run lint:web
npm run build:web
APP_ENVIRONMENT=test pytest tests/test_elevenlabs_errors.py tests/test_conversation_provider.py tests/test_homepage_chat_provider.py tests/test_outbound_demo.py
```

Only with an isolated, disposable `TEST_DATABASE_URL` configured (database fixtures
rebuild their database), run the new service-level regressions:

```sh
APP_ENVIRONMENT=test pytest tests/database/test_conversation_api.py -k external_account_restriction
APP_ENVIRONMENT=test pytest tests/database/test_homepage_chat.py -k provider_restriction
APP_ENVIRONMENT=test pytest tests/database/test_outbound_demo_calls.py -k provider_account_restriction
```

## Manual checks

1. On the owner's running development app, simulate the safe marker on HTTP 424
   conversation authorization for Chat/Voice and a published website conversation.
   Confirm the full requested message appears in one toast and the page stays
   usable, with the existing retry/cleanup behavior and unsent draft preserved.
2. Simulate SDK `quota_exceeded`, `insufficient_credits`, payment failure and an
   account-restricted disconnect. Confirm one visible toast even when error and
   disconnect callbacks both fire. No live paid provider request is necessary.
3. Simulate an external billing/access refusal in homepage chat and demo-call
   preflight/dial. Confirm their proxies retain the safe marker, homepage allowance
   accounting remains correct and demo-call outcomes never automatically redial.
4. Simulate application 401/403/500, ordinary upstream 500, timeout, invalid API key,
   429 rate/concurrency limits, microphone denial and trial allowance exhaustion.
   Confirm none incorrectly shows the credit toast. Identified provider failures
   can show their category-specific toast. Successful sessions show none.
5. Inspect desktop/mobile, both themes and an open demo-call dialog. Check readable
   wrapping, no horizontal overflow, screen-reader announcement, dismiss button,
   keyboard access and automatic dismissal. Inspect response bodies and URLs to
   confirm only the safe marker is exposed, without provider secrets or raw bodies.

Implementation references: [Sonner setup](https://sonner.emilkowal.ski/getting-started),
[ElevenLabs errors](https://elevenlabs.io/docs/eleven-api/resources/errors),
[legacy ElevenLabs errors](https://elevenlabs.io/docs/help-center/technical/api-error-code-400-or-401).
