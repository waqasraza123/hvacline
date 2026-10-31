# Homepage chat and sign-in continuation — UNVERIFIED

The owner selected one live text message/reply on the homepage, a sign-in popup on the second attempt, a once-per-browser allowance remembered for 30 days, and preservation of the exchange and unsent second message through authentication. The same existing Line browser agent serves guests and authenticated customers; no separate agent, provider key or public signed URL is introduced.

## Experience

The orange/charcoal hero card opens on Voice AI, linking to the existing signed-in booking workspace. Selecting Text chat exposes suggested questions, an editable composer, explicit Send & agree processing disclosure, real loading/error states and a dismissible native sign-in dialog. Suggested questions fill the field without sending. The first completed answer remains readable, with an inline continuation invitation; the dialog opens only when the visitor chooses to continue. Header Try Line and the floating launcher focus the card's current action. Voice requires sign-in, selecting Voice in the workspace and explicit microphone consent. See [homepage hero](homepage-hero.md) for the October 31 presentation change and owner checks.

Already-authenticated visitors carry their typed question directly into `/book` without spending a guest allowance. Earlier text is shown separately, and the pending message is prefilled when Chat starts. The SDK receives the earlier exchange as untrusted contextual background, outside the active confirmation transcript. The pending message is not sent automatically; ordinary disclosure, MFA, intake and booking confirmations remain required. Start fresh discards the handoff.

The browser stores the exchange/draft only in same-tab sessionStorage, with a validated 30-minute expiry; expired records are discarded on access. Navigating in a different tab, closing the tab, storage restrictions or waiting beyond expiry can prevent continuation. There is no text in URL parameters, quota records or audit payloads. The agent/provider still processes the text under the disclosed provider configuration.

## Backend and interfaces

- Next.js `GET /api/homepage-chat` checks existing account status, privately issues/reuses an HttpOnly/SameSite 30-day visitor cookie, and returns `ready`, `used`, `busy`, `authenticated` or `unavailable` with remaining allowance. Cookie lifetime is not extended on refresh.
- Next.js `POST /api/homepage-chat` checks same origin, cookie presence, message length and explicit processing acceptance. It accepts `message`, UUID `request_id`, and `ai_disclosure_accepted=true`. An authenticated visitor receives `state=authenticated` without a guest request. Other requests are proxied server-side with the existing portal secret and opaque visitor token.
- Protected FastAPI `GET/POST /api/v1/homepage-chat` resolves the configured business, not a user-supplied tenant. The POST returns `{reply, remaining: 0}`. Only approved FAQ lookup is dispatched; all other client tools return a sign-in requirement without executing. The upstream connection closes after the one completed response; the initial agent greeting is ignored and does not consume the visitor's message.
- Migration `20261029_0017` follows `0016` and adds visitor quota metadata plus daily counters. Tokens/messages are keyed hashes; raw messages, replies, customer identities and IP addresses are not stored there. A short agency-row lock atomically reserves allowance/concurrency, then releases before provider I/O. No guest customer, intake, conversation-session, appointment or memory record is created.
- One accepted generation attempt per business is active by default. Failed connection attempts count toward the daily provider-attempt budget but restore a visitor's allowance if their message was definitely not submitted. Failure after submission or an expired processing lease is treated as ambiguous/used to prevent duplicate generation. Lost replies are not regenerated automatically; the draft is preserved and sign-in remains available. No provider-result text is cached in the database.
- Visitor rows expire after 30 days. Reservation opportunistically removes up to 100 expired visitors for that business and daily counters older than 31 days. No new worker is required. Clearing cookies or changing browsers creates a new identity; shared daily/concurrency budgets bound usage without fingerprinting. Existing agent/account provider limits are still shared with signed-in calls even though application guest quotas are separate.

## Configuration and rollout

No verification, dependency installation, migration, live service, provider change or deployment was run. Source formatting only; all implementation/runtime behavior is **UNVERIFIED**.

1. Install the updated backend dependencies in the intended environment (`websockets==17.3` is added). Apply the new migration before launching the updated backend:

   ```sh
   python -m pip install -e '.[dev]'
   APP_ENVIRONMENT=development python -m alembic upgrade 20261029_0017
   ```

2. In the existing private browser agent, add boolean dynamic variable `homepage_guest` with default **false**. Update the guest-mode paragraph from [browser setup](elevenlabs-agent-setup.md). Preserve the existing nonempty first message; enable `agent_response` and `agent_response_complete` client events. Retain text-only overrides, current model, eight blocking client tools, authentication and privacy settings. Do not add public tools or a new agent. The backend waits for the initial greeting to finish before submitting the visitor's message, so the completion event is mandatory.
3. Deploy backend and frontend with `HOMEPAGE_CHAT_ENABLED=false`. This flag is API-only; the Next.js route discovers availability from the backend. Keep the existing `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`, `CUSTOMER_PORTAL_SECRET`, protected customer configuration and API base URL. No new frontend environment variable is required.
4. Validate in the intended staging environment, then set API-only `HOMEPAGE_CHAT_ENABLED=true`. Defaults are `HOMEPAGE_CHAT_DAILY_LIMIT=20` (attempts per UTC day) and `HOMEPAGE_CHAT_CONCURRENT_LIMIT=1`; settings validate their ranges. Disabling the flag stops guest access and leaves a working sign-in action. Do not deploy the new API against the old schema.
5. Monitor aggregate guest status/errors, exhausted daily allowance and provider usage without logging message content, cookies or signed connection URLs. Repeated busy/unavailable results should prompt review of actual provider limits and hosting response times. Adjust budgets deliberately.

## Owner-run checks

From `/private/tmp/hvacline-browser-demo`, with dependencies installed for this checkout:

```sh
npm run test --workspace @insurance-operations/web -- src/features/homepage-chat/handoff.test.ts src/app/api/homepage-chat/route.test.ts
npm run verify:web
python -m pytest tests/test_homepage_chat_provider.py tests/test_api.py tests/test_settings.py
ruff format --check apps/backend/src/insurance_operations/homepage_chat apps/backend/src/insurance_operations/database/models/homepage_chat.py migrations/versions/20261029_0017_homepage_chat.py tests/test_homepage_chat_provider.py tests/database/test_homepage_chat.py
ruff check apps/backend/src migrations tests
mypy apps/backend/src tests
```

Database checks below require a confirmed isolated, disposable `TEST_DATABASE_URL`; the fixture truncates conversation dependencies and downgrades/rebuilds that database. Never use retained development/customer data:

```sh
APP_ENVIRONMENT=test python -m pytest tests/database/test_homepage_chat.py tests/database/test_migrations.py tests/database/test_table_ownership.py
APP_ENVIRONMENT=test python -m alembic upgrade head
APP_ENVIRONMENT=test python -m alembic check
```

Manual acceptance:

1. On desktop and 320px/mobile widths, check hero/card wrapping, keyboard visibility, scroll/focus behavior, suggested prompts and reduced motion. The page must not autofocus or request microphone access.
2. Agree by sending one question. Observe a real reply, no automatic popup, and no customer/booking side effects. Type a second question and send: the popup opens, the draft stays, and no second provider request occurs. Escape, outside dismissal and the close button restore useful focus.
3. Refresh/open another same-browser tab: the server allowance remains used. Race two sends after cookie issuance: only one generation can reserve the allowance. Check another visitor during an active generation, the daily budget, blocked cookies, duplicate request IDs and expired processing leases.
4. Interrupt before connection and after submission separately. Known pre-submit failures allow retry; ambiguous submissions never trigger duplicate generation. Every failure keeps the draft and offers sign-in/availability recovery.
5. Continue through existing-account login and new-account signup/MFA in the same tab. Check the earlier exchange, prefilled second message, explicit Chat start and one explicit send. Neither guest text nor an earlier yes may confirm a request or appointment. Verify Start fresh, expired/malformed handoffs, unavailable storage and already-authenticated homepage use.
6. Ask for pricing, an unknown policy, an immediate hazard, account history, booking or memory writes. Only approved business information may be answered; forbidden tools must have no effects. The signed-in agent must retain full booking behavior and return `homepage_guest=false` at initiation.
7. With the feature disabled, the backend unavailable or account status uncertain, confirm truthful fallback and working sign-in. Confirm secrets, signed URLs and conversation text are absent from logs and database quota rows.
