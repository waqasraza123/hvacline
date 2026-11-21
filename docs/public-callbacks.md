# Public callback requests — UNVERIFIED

## SMS-capable numbers — November7,2026 — UNVERIFIED

Owner now authorizes SMS verification for US mobile, landline and VoIP numbers.
The adapter retains lookup identity/region/carrier-error checks but removes its
line-type restriction; correct code verification remains mandatory. This
supersedes the mobile-only policy below. No new migration or setting. Deploy
both backend and frontend after publication; checks and runtime remain unverified.
Owner commands/manual checks: [SMS-capable numbers](sms-capable-demo-numbers.md).

## Mobile-only production hardening — November5,2026 — UNVERIFIED

Owner clarifies public fictional demo calls, with mobile numbers only. New
source requires live mobile carrier lookup and SMS proof before every website
call, independently of mandatory authenticator sign-in. Account-bound ownership,
account call quotas and bounded SMS budgets replace cookie-only ownership. New
migration0019 and API-only Telnyx Verify configuration are required. The earlier
no-new-migration and mobile/landline activation instructions below describe
`05da57e`; they do not cover this hardening. Keep public flags off until the new
release is configured and accepted. Exact deployment, remaining blockers, owner
commands and manual checks: [Public demo release](public-demo-production-readiness.md).

The owner authorizes website callbacks for signed-in customers, with authenticator
MFA required. `consented_us` now supports the existing website route without a
recipient allowlist. Transfer remains disabled under this policy. `allowlist`
continues to require exact approved recipients. These changes supersede the older
admin-only US policy and mandatory-transfer website instructions.

The callback bridge revalidates `auth/me` for availability, submission and status.
That backend identity check requires a nonexpired, unrevoked session with an
authenticator verification timestamp and the current enabled factor version.
Password login/signup issue only a limited MFA challenge; recovery requires
replacement-authenticator verification before a full session. No anonymous
callback path or password-only session is introduced.

Website availability requires enabled calling, the website flag and real outbound
acceptance. Transfer acceptance is required only when transfer is enabled. The
service enforces the same website gate before reserving a visitor request.
US number validation, unchecked versioned consent, per-number/global limits,
cooldown, one active/unknown call, idempotency, signed receipts and provider
preflight remain enforced. Known destination rejections let the form unlock for
correction and renewed consent; uncertain outcomes retain recovery locks.

## Hosted activation

Deploy the changed backend and frontend. This task has no connected Render/Vercel
tools; no hosted environment or provider configuration was changed. Keep existing
agent/phone IDs, stable bridge secret, distinct webhook secret and customer portal
configuration, including the MFA encryption key. No migration is added.

For the Render backend:

```dotenv
OUTBOUND_DEMO_ENABLED=true
OUTBOUND_DEMO_NUMBER_POLICY=consented_us
OUTBOUND_DEMO_WEBSITE_ENABLED=true
OUTBOUND_DEMO_TRANSFER_ENABLED=false
OUTBOUND_DEMO_TRANSFER_VERIFIED=false
```

`OUTBOUND_DEMO_LIVE_VERIFIED=true` is also required, but set it only after an
actual authorized US call passes the existing outbound acceptance procedure:
ringing, disclosure/two-way audio, actual disconnection and signed finalization.
Recorded evidence still lacks a successful end-to-end US call. Until that result
exists, keep `OUTBOUND_DEMO_WEBSITE_ENABLED=false` and the Next form flag false;
otherwise backend startup rejects the unverified website configuration. Do not
set acceptance flags merely to enable the form. Carrier recording must be off.

For the Vercel Next server, after acceptance:

```dotenv
OUTBOUND_DEMO_FORM_ENABLED=true
```

Retain the existing HTTPS `NEXT_PUBLIC_API_BASE_URL`, server-only
`OUTBOUND_DEMO_SECRET` matching the backend and working customer portal settings.
No outbound secret may use a `NEXT_PUBLIC_` prefix. Existing quota settings are
unchanged. A US number alone does not guarantee carrier completion.

## Owner verification — not run

From `/Users/mc/development/hvacline`, with the existing environment and Node24:

```sh
DEMO_SANDBOX_ENABLED=false PYTHONPATH=apps/backend/src .venv/bin/python -m pytest --import-mode=importlib tests/test_outbound_demo.py tests/test_customer_mfa.py tests/test_customer_mfa_settings.py
npm run test:web -- src/app/api/outbound-demo/route.test.ts src/features/customer/auth-continuation.test.ts 'src/app/api/account/[action]/route.test.ts'
npm run typecheck:web
npm run build:web
```

Only with a privately configured isolated disposable `TEST_DATABASE_URL`, distinct
from runtime/direct targets; database fixtures rebuild/truncate their target:

```sh
APP_ENVIRONMENT=test GOOGLE_CALENDAR_ENABLED=false BOOKING_EMAIL_ENABLED=false DEMO_SANDBOX_ENABLED=false PYTHONPATH=apps/backend/src .venv/bin/python -m pytest --import-mode=importlib tests/database/test_outbound_demo_calls.py tests/database/test_customer_mfa.py
```

Manual checks:

1. Signed-out requests to availability, submission and saved status return401.
   Opening the homepage/modal never dials. Password-only login, a pending MFA
   challenge, canceled/failed MFA and expired/revoked sessions cannot access calls.
2. Signup requires authenticator enrollment and a valid code. Existing users must
   verify their authenticator. Recovery requires enrolling/verifying a replacement.
   Callback intent survives login/MFA and returns to the modal without submitting.
3. With gates enabled after acceptance, a signed-in visitor can request one
   consented US mobile/landline call without an allowlist entry. Check actual
   ringing/audio/disconnection and terminal provider/carrier/backend evidence.
4. Missing consent and unsupported/invalid destinations reject before dialing.
   Known number errors permit correction with fresh consent. Double-click/replay
   dials once; reload/closed modal/uncertain POST preserves status recovery.
5. Another visitor cannot read the request. Cross-origin requests, direct backend
   requests without the bridge secret, quotas and disabled gates reject. Transfer
   stays unavailable. Check mobile layout, keyboard focus and modal dismissal.

No tests, builds, linters, type checks, services, provider edits, deployments or
calls ran. Implementation and hosted activation remain **UNVERIFIED**.
