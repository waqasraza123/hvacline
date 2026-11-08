# Public SMS-verified demo release — UNVERIFIED

Scope updated November 7, 2026: real visitors request a fictional HVAC demo
call on a US number that can receive SMS, including VoIP and landline numbers.
Sign-in with authenticator MFA remains mandatory.
SMS verification proves control of the callback number; it never replaces MFA.
No real appointment or human transfer is part of launch. The owner authorizes
relaxing the earlier mobile-only policy; [implementation and owner checks](sms-capable-demo-numbers.md)
remain unverified.

**Not production ready yet.** The earlier website implementation is published as
`05da57e`. The owner authorizes publishing this hardening; implementation and
runtime remain unverified. No tests, builds, lint, type checks, migrations, SMS,
live calls or deployment commands ran for this work.

## Implemented in source

- The Next bridge derives an opaque owner token from the validated account and
  stable outbound secret. Changing browsers/cookies retains account call limits;
  another account using the same browser cannot read the first account's call.
  A separate browser cookie still guards request/recovery initialization.
- Website callers must explicitly request a verification text, pass live Telnyx
  lookup identity/US-region/carrier-error checks, and prove their provider-generated
  six-digit code. Carrier line type no longer restricts SMS requests; delivery and
  code acceptance are required for mobile, landline and VoIP numbers alike.
  US numbering-plan/region validation remains an earlier check and includes VoIP.
- Phone proofs bind tenant, account and destination, expire from initial send
  time, allow at most five verification attempts and are consumed atomically with
  call reservation. Replaying the same call key returns its saved result; a new
  key cannot reuse a consumed proof. Changing the phone clears proof and consent.
- SMS reservations commit before external requests. Failed/uncertain sends count
  toward persistent budgets and are never automatically retried. Verification
  timeouts consume an attempt. Raw phones, codes and provider bodies are excluded
  from the new table and application errors; only keyed hashes, receipt ID, versioned
  SMS consent, timing and minimal proof state persist.
- Default limits: one call/account/rolling24h, one call/number/rolling24h,
  five total calls/business/UTC day, one active/unknown call,300-second call
  cooldown. SMS limits are20 attempts/business, three/account and three/number
  per rolling24h, with60-second account/number send cooldown. Provider failures
  still count. None of these limits is raised automatically for public traffic.
- Live acceptance and configured SMS credentials are required for website
  availability. Admin test calling keeps its existing separate authentication and
  policy. Transfer remains off under `consented_us`; provider TLS, prompt/privacy
  checks, signed webhooks and the180-second AI cap remain enforced.
- New migration0019 adds `outbound_phone_verifications` with tenant ownership and
  unique provider receipt binding. Old call fingerprints remain unchanged. The
  deployment template now migrates without automatically running development
  seeds. Customer request bodies are bounded while streaming. Frontend headers
  add framing/base/object restrictions, nosniff, referrer policy and production
  HTTPS HSTS; this is not a complete resource-restricting CSP.
- Outbound failure logs expose only preflight/dial phase, unknown-outcome flag
  and opaque call ID. They do not log exception bodies, recipients or credentials.

## Required before public activation

1. **Provider setup.** Create a dedicated Telnyx Verify profile for this demo:
   SMS only, six-digit provider-generated codes, supported US destinations only,
   matching timeout and branded verification text. Complete any provider-required
   messaging approval and enable Number Lookup access. Set spending/destination
   controls and alerts on Verify, Telnyx voice and ElevenLabs; application attempt
   quotas do not establish a dollar cap. Keep Telnyx recording off. The existing
   caller ID, outbound SIP/TLS/digest, prompt and signed callback must be accepted.
2. **Verification and release.** Run the commands below, resolve failures, confirm
   database backups and migration target, apply0019, deploy API then web and
   complete actual SMS/call acceptance. Do not mark live acceptance from a GET-only
   diagnostic. Review rollback against a retained schema; never fabricate proof
   rows for visitors or set acceptance flags merely to unlock the form.
3. **Hosting and operations.** Confirm persistent API availability, database TLS,
   capacity and backups with an actual restore drill. Apply edge limits for
   signup/login, SMS, status reads and request size; application auth/SMS/call
   quotas already provide independent bounds. Alert on failures, exhausted spend,
   repeated SMS failures, missing terminal webhooks and active/unknown calls.
   Existing admin refresh/carrier-ended tools support supervised reconciliation;
   a dropped receipt can otherwise hold the single call slot indefinitely. Do not
   clear it by elapsed time alone or automatically redial unknown outcomes.
   Disable full HTTPX/HTTPCore request/debug logging and redact provider URLs at
   gateways: the required Number Lookup URL contains the recipient phone number.
4. **Privacy and consent.** Publish operator contact, privacy/terms, data retention
   and deletion/support rules for account data, proof/call metadata and provider
   processing. Confirm actual ElevenLabs/Telnyx Verify/voice retention and logging.
   The repository has no public privacy/terms pages or scheduled callback-evidence
   deletion. Review the SMS/AI-call consent text for this public demonstration.
   The FCC treats AI-generated voice as artificial/prerecorded voice under the
   TCPA; applicable consent requirements need review for the actual use case.
   [FCC24-17](https://docs.fcc.gov/public/attachments/FCC-24-17A1.pdf).

This remains a deliberately isolated fictional-demo tenant using the repository's
development identity boundaries. Keep its database and secrets separate from real
HVAC operations. `APP_ENVIRONMENT=production` still rejects this callback/customer
portal architecture; enabling that mode requires a separate identity/environment
refactor. Do not remove the current checks to make the flag pass. The Next frontend
must use production HTTPS/secure cookies regardless of this demo backend mode.

## Configuration and coordinated deployment

Before deployment, pause new website requests with backend
`OUTBOUND_DEMO_WEBSITE_ENABLED=false` and Next `OUTBOUND_DEMO_FORM_ENABLED=false`.
Reconcile any active/unknown calls. The new account ownership token deliberately
does not fall back to the former cookie owner: old pending website records require
operator recovery. Preserve the stable outbound state secret and all MFA keys.

API-only new settings:

```dotenv
TELNYX_VERIFY_API_KEY=
TELNYX_VERIFY_PROFILE_ID=
OUTBOUND_DEMO_ACCOUNT_DAILY_LIMIT=1
OUTBOUND_DEMO_SMS_DAILY_LIMIT=20
OUTBOUND_DEMO_SMS_ACCOUNT_DAILY_LIMIT=3
OUTBOUND_DEMO_SMS_NUMBER_DAILY_LIMIT=3
OUTBOUND_DEMO_SMS_COOLDOWN_SECONDS=60
OUTBOUND_DEMO_SMS_TTL_SECONDS=300
```

Use the real API key and dedicated profile UUID only in private hosting secrets.
The key is independent of the SIP digest credentials. A blank Verify configuration
is valid while website calling is disabled; enabling website calling without it
fails startup. No new frontend secret or dependency is required. Both servers
still share only `OUTBOUND_DEMO_SECRET`; customer/MFA configuration remains intact.

After owner verification, against the intended backed-up demo database:

```sh
APP_ENVIRONMENT=development .venv/bin/python -m alembic current
APP_ENVIRONMENT=development .venv/bin/python -m alembic upgrade 20261105_0019
APP_ENVIRONMENT=development .venv/bin/python -m alembic current
```

These commands have not run. Existing Free Render services without pre-deploy
support need the existing migration-in-build procedure; do not add a seed to it.
Existing tenants stay intact; a new database still needs deliberate initial
bootstrap outside deployment. Keep all website flags off until acceptance.

Use [public callback activation](public-callbacks.md) only after this checklist.
`consented_us`, `OUTBOUND_DEMO_ENABLED=true`, actual
`OUTBOUND_DEMO_LIVE_VERIFIED=true`, backend website=true and Next form=true are
required; transfer stays false. SMS controls do not override call quotas.

## Owner verification commands — not run

From `/Users/mc/development/hvacline`, using Python3.13 and Node24:

```sh
DEMO_SANDBOX_ENABLED=false PYTHONPATH=apps/backend/src .venv/bin/python -m pytest --import-mode=importlib tests/test_outbound_demo.py tests/test_outbound_sms_provider.py tests/test_customer_mfa.py tests/test_customer_mfa_settings.py
npm run test:web -- src/app/api/outbound-demo/route.test.ts src/features/customer/proxy.test.ts src/features/customer/server.test.ts src/features/customer/auth-continuation.test.ts 'src/app/api/account/[action]/route.test.ts'
npm run typecheck:web
npm run build:web
.venv/bin/python -m ruff check apps/backend/src/insurance_operations/telephony/outbound apps/backend/src/insurance_operations/database/models/outbound_verification.py migrations/versions/20261105_0019_outbound_phone_verification.py tests/test_outbound_demo.py tests/test_outbound_sms_provider.py tests/database/test_outbound_demo_calls.py
.venv/bin/python -m mypy --explicit-package-bases apps/backend/src/insurance_operations/telephony/outbound
```

Only with a privately configured isolated disposable `TEST_DATABASE_URL`, distinct
from runtime/direct targets: these fixtures downgrade/rebuild/truncate their target.

```sh
APP_ENVIRONMENT=test GOOGLE_CALENDAR_ENABLED=false BOOKING_EMAIL_ENABLED=false DEMO_SANDBOX_ENABLED=false PYTHONPATH=apps/backend/src .venv/bin/python -m pytest --import-mode=importlib tests/database/test_outbound_demo_calls.py tests/database/test_customer_mfa.py tests/database/test_migrations.py tests/database/test_table_ownership.py
```

Manual acceptance after the owner starts/deploys the compatible apps:

Plan quota headroom first: earlier admin/failed calls count. Use a fresh consented
SMS-capable US number, wait for limits to reset, or deliberately select an allowed
limit within the existing bounds. Do not erase records or bypass an unknown call. A virtual
receiving number/softphone must actually receive the SMS and verify its code.

1. Signed-out, password-only, MFA-pending/failed, expired and revoked sessions
   cannot send SMS, verify a code, dial or read status. Login/signup/recovery return
   through the authenticator before reopening the modal; returning never dials.
2. One explicit SMS consent/action sends one code. No opening, typing, checkbox,
   modal dismissal or code verification sends a call. Invalid/non-US and
   mismatched/failed carrier lookups reject. SMS-capable landline/VoIP numbers
   can verify; unknown line type alone does not reject. Test no voice-code fallback.
3. Wrong/expired codes and five attempts fail. Provider timeouts/failed sends count
   without automatic retries. Changing phone/account invalidates access; resetting
   cookies does not reset account limits. Another account cannot reuse a proof.
4. A verified, consented recipient receives one fictional AI demo call with the
   correct caller ID, disclosure and two-way audio. Explicit end and180-second
   ceiling disconnect the phone. Confirm terminal carrier/provider/signed backend
   evidence. Double-click/reload/POST timeout/status polling never redial.
5. New request keys cannot reuse a consumed proof; same-key retries return the
   existing outcome. Confirm call/SMS account, number and global quotas, unknown
   slot behavior, disabled gates, secret rejection and cross-origin rejection.
6. Check mobile keyboard, code autofill, code expiry, screen-reader status, Tab,
   Escape and focus return. Review hosted headers and ensure Voice/microphone,
   login/MFA and existing booking pages still work. Confirm bodies, codes, keys and
   raw numbers stay out of application/gateway logs and error responses.

Provider contracts: [mobile carrier lookup](https://developers.telnyx.com/docs/identity/number-lookup/quickstart),
[SMS creation](https://developers.telnyx.com/api-reference/verify/trigger-sms-verification),
[verify saved ID](https://developers.telnyx.com/api-reference/verify/verify-verification-code-by-id).
