# SMS-capable US demo numbers — implementation UNVERIFIED

On November 7, 2026, the owner authorizes relaxing the mobile-only restriction
after the website SMS-start endpoint returns422 and a quick retry returns429.
The exact historical422 cause remains unknown. This supersedes the November5
mobile-only policy for website verification and callbacks.

The Telnyx lookup adapter no longer filters by carrier line type. Mobile,
landline, VoIP and unknown/missing type classifications can proceed to SMS when
the lookup returns the requested number, a supported US region and a carrier
object without an error. Number Lookup still runs; lookup HTTP failures, invalid
identity/region and carrier errors still reject. US numbering validation now
also accepts the explicit VoIP classification; invalid, non-US, premium-rate,
toll-free and other unsupported number types remain rejected.

Actual SMS delivery and the provider-generated six-digit code establish control.
A line type does not guarantee delivery. The app does not assume SMS capability
from VoIP/landline classification or create a proof without code verification.
Authenticator sign-in, explicit SMS/call consent, proof ownership/expiry/attempt
limits/single use, website activation, allowlist policy when configured, persistent
SMS/call quotas and unknown-call recovery stay in place. UI and bridge messages
now ask for a US phone number that can receive texts.

No new setting, dependency or migration is required. Publish the source, deploy
the backend on Render and the frontend on Vercel. No publish, deploy, live lookup,
SMS, call or verification command was executed for this implementation.

Owner commands from `/Users/mc/development/hvacline` (not run):

```sh
DEMO_SANDBOX_ENABLED=false PYTHONPATH=apps/backend/src .venv/bin/python -m pytest --import-mode=importlib tests/test_outbound_sms_provider.py tests/test_outbound_demo.py
npm run test:web -- src/app/api/outbound-demo/route.test.ts
npm run typecheck:web
npm run build:web
```

Manual checks after deployment:

1. Confirm both deployments contain this change and the dialog says Your US phone
   number. Sign in with the authenticator and use a controlled US number with SMS
   reception, including the previously rejected VoIP number if appropriate.
2. Allow the configured SMS cooldown to expire before one explicit text request
   (default60 seconds). Earlier failures count toward the rolling24-hour budgets
   (default three/account, three/number and20/business); a daily limit can outlast
   the cooldown. Do not delete reservations to reset quotas.
3. Confirm SMS delivery, enter the six-digit code and verify the number. No call
   should start from sending/verifying SMS. Wrong/expired codes must fail; code
   verification must not change the authenticator requirement.
4. Confirm invalid/non-US numbers and failed/mismatched lookups still reject;
   provider failures do not create a verified proof or automatically retry.
5. Only when deliberately requesting a call with separate consent, confirm the
   verified destination receives it and preserve existing call outcome recovery.

Implementation and hosted acceptance remain unverified until the owner reports
the results. Passing this flow does not resolve the earlier unknown call outcome.
