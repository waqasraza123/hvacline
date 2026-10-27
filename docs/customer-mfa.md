# Mandatory customer authenticator MFA — UNVERIFIED

Scope is customer accounts only. Operations/staff access is unchanged. Source is in `/private/tmp/hvacline-browser-demo` on branch `feat/mandatory-authenticator-mfa`; the owner authorized committing and publishing all pending work to `main`. No tests, formatters, checks, migrations, services, provider calls, dependency installation or deployments were run for MFA. Publication does not establish runtime/security acceptance, which remains **UNVERIFIED**.

## Authentication and recovery

Signup creates the account and a ten-minute enrollment challenge, never a customer session. Password login returns enrollment for existing accounts without MFA, or verification for enrolled accounts. The challenge authorizes only MFA status/setup/verification/recovery/cancel. Every existing customer API still requires a full session, now stamped with verified MFA and the current factor version. There is no password-only, email-only, optional-MFA or disable endpoint.

The browser stores the challenge in a separate HttpOnly, SameSite=Strict cookie (`__Host-hvacline-mfa` over production HTTPS). Session and challenge cookies are never interchangeable; bearer values are stripped from frontend JSON. POSTs require the existing same-origin checks. Setup keys, OTPs and recovery codes stay out of URLs, local storage, audit details and application notes. MFA responses use `Cache-Control: no-store`. Gateways must not record Authorization headers, request/response bodies or browser security-page contents.

Use Google Authenticator, Microsoft Authenticator, 1Password or another compatible TOTP app: choose manual setup, enter the displayed Base32 key, select time-based six-digit codes and enter a current code. No Google sign-in, SMS, email factor, third-party QR service or new dependency is used. TOTP follows [RFC 6238](https://www.rfc-editor.org/rfc/rfc6238), SHA-1/six digits/30-second periods with one interval of clock tolerance. Accepted counters cannot be reused. Synchronize API and authenticator clocks.

Seeds use authenticated Fernet encryption bound to tenant/account/factor version or pending challenge; challenge tokens are SHA-256 hashes in PostgreSQL. Factor-row locking serializes proof/recovery and replay counters. Five wrong codes lock the account's MFA attempts for fifteen minutes; counters survive new password challenges. Challenges expire, are consumed once, and new password challenges replace older ones. Failures commit before an API error is raised, preserving attempt limits.

Successful initial enrollment or replacement returns ten independent 128-bit recovery codes once. Save them privately. Only account-scoped keyed hashes are stored. To recover: log in with the password, choose **Use a recovery code**, enter an unused code, enroll a replacement authenticator, verify its current code and save the new backup set. Backup proof revokes all existing customer sessions and changes the factor version immediately; the replacement challenge cannot access customer data. The previous authenticator remains valid for a fresh password-plus-TOTP login until replacement is verified atomically. Completion retires the previous authenticator and all remaining old backup codes. Losing both the authenticator and backup codes has no self-service bypass. Password reset, verified email recovery and managed support recovery are outside this change.

The new forward migration `20261028_0015` follows customer memory `0014`. It adds factor/challenge/recovery tables, nullable MFA evidence on existing sessions and a factor version on WhatsApp identity links. It revokes all existing customer sessions without deleting customer/history/booking records. Users without MFA must enroll on their next password login. Existing WhatsApp memory links start at version zero and require fresh browser approval after MFA. Recovery/replacement invalidates earlier links; no private memory is returned until relinking. Inbound anonymous WhatsApp booking, Twilio, Calendar and notification behavior are unchanged. A WhatsApp call itself is not a customer browser login and does not collect account passwords, setup keys, OTPs or recovery codes.

The application retains its existing development/fictional-data restrictions. This feature does not establish production tenant onboarding or email ownership verification. Tests use disposable database transactions; downgrade refuses to discard populated MFA security records and never restores revoked sessions.

## Reference adaptation

Read from the owner's [stealth-trails repository](https://github.com/waqasraza123/stealth-trails):

- `apps/api/src/auth/customer-mfa.util.ts`, blob `6583764b9ac3c4017383845246173e604d66f80b`: TOTP generation, provisioning and accepted-counter replay protection.
- `apps/api/src/auth/auth.service.ts`, blob `04109c54af98c7f6cb5247fb5f2a3ad4c6f3bec3`: encrypted pending/enrolled secrets, lockouts and session-version revocation.
- `docs/architecture/customer-mfa-enforcement-plan.md`, blob `102b9eef46235f99b06574a2f0a252a59bccd2a9`: reviewed source policy.

Adapted to this repository's Python/FastAPI/Neon architecture. The source system's read-only pre-MFA access and email fallback were not adopted: HVACLine customer access requires MFA throughout. Recovery/enrollment choices also follow the [OWASP MFA guidance](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html).

## Owner configuration and rollout

1. Keep the portal unavailable during the schema/API/frontend transition. Take the normal database backup; migration revokes existing customer sessions.
2. Generate a dedicated Fernet key in your secure environment using the command below. Set API-only `CUSTOMER_MFA_ENCRYPTION_KEY`; store a protected backup and use the same stable key on every API instance. Never place it in `NEXT_PUBLIC_*`, frontend hosting, logs or the repository. Losing/changing it prevents decryption and recovery; restore the original key rather than disabling MFA. Key rotation is not implemented.
3. Preserve API `CUSTOMER_PORTAL_ENABLED`, `CUSTOMER_PORTAL_SECRET`, `DEVELOPMENT_ACTOR_USER_ID` and existing development/voice configuration. The Next server still needs `CUSTOMER_PORTAL_SECRET` and `NEXT_PUBLIC_API_BASE_URL`. No extra ElevenLabs/Meta/Twilio configuration is required for MFA. Reapprove optional WhatsApp memory links from an MFA-authenticated browser.
4. Owner applies migrations through `0015`, then updates API and frontend together before reopening the portal. Keep customer pages on HTTPS; API startup fails closed if the portal is enabled without a valid MFA encryption key.

Owner-only key generation; the output is a secret, do not paste it into chat:

```sh
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

## Owner-run verification — none executed

### Render startup failure: missing MFA encryption key

If the build and migrations succeed but Uvicorn exits with `CUSTOMER_MFA_ENCRYPTION_KEY is required for customer accounts`, the enabled customer portal is missing its API encryption key. Package installation and database migration do not configure this secret.

In the Render API service's **Environment** settings, add `CUSTOMER_MFA_ENCRYPTION_KEY` with the dedicated Fernet key generated using the command above, then select **Save and deploy**. See [Render environment-variable instructions](https://render.com/docs/configure-environment-variables). Restore the original key if MFA was previously configured; generate one only for initial setup. Keep a protected backup and retain the same value across API instances and redeployments. The Blueprint declares a secret placeholder; it does not generate a Fernet key or populate an existing service automatically. The key belongs only on the API.

The owner's October 28 deployment log reports upgrades through `20261028_0015` before this startup failure. No extra migration is introduced by the configuration repair. After redeployment, manually confirm Uvicorn reaches application startup, `/ready` succeeds, and customer login requires authenticator enrollment or verification. Runtime remains **UNVERIFIED** until owner acceptance.

### Commands and acceptance

From the active source and existing Python 3.13/Node 24 environments, configure **isolated disposable** `TEST_DATABASE_URL`, distinct from runtime/direct database URLs. Database fixtures downgrade and rebuild their target. Do not point these tests at shared Neon data.

```sh
cd /private/tmp/hvacline-browser-demo
python -m pytest tests/test_customer_mfa.py tests/test_customer_mfa_settings.py tests/test_settings.py
APP_ENVIRONMENT=test python -m pytest tests/database/test_customer_mfa.py tests/database/test_customer_memory.py tests/database/test_conversation_api.py tests/database/test_migrations.py tests/database/test_table_ownership.py
npm run test --workspace @insurance-operations/web -- 'src/app/api/account/[action]/route.test.ts' src/features/customer/server.test.ts
ruff format --check apps/backend/src tests migrations
ruff check .
mypy apps/backend/src tests
npm run verify:web
APP_ENVIRONMENT=test alembic upgrade head
APP_ENVIRONMENT=test alembic current
APP_ENVIRONMENT=test alembic check
```

After acceptance, owner-only forward migration against the intended backed-up development database:

```sh
APP_ENVIRONMENT=development alembic upgrade head
APP_ENVIRONMENT=development alembic current
```

Manual acceptance:

1. Create a fictional customer account. Confirm immediate `/mfa` setup; opening `/book`, history, memory, appointments or conversation APIs before proof must redirect/reject. Enrollment must not create a full customer session.
2. Add the manual key to Google or another TOTP authenticator, enter the current code, save the once-shown backup codes and continue. Confirm Chat/Voice and owned booking/history still work.
3. Log out, then password-login again: require a fresh authenticator code before any account access. A wrong code must fail; a successfully used code must not work again in another challenge. Test five invalid codes and verify the fifteen-minute lock survives another password login.
4. On an isolated database upgraded from `0014`, confirm an old session is rejected immediately and an existing customer without a factor is routed to mandatory setup. The original account/history/appointments must remain.
5. With another browser already signed in, recover using the password plus one backup code. Existing sessions must stop working; the recovery challenge must not access data. Complete replacement, then confirm old authenticator codes and old backups fail, new codes work, and optional WhatsApp memory requires fresh browser approval.
6. Try expired/cancelled challenges and cross-origin POSTs; they must fail. Review secure/HttpOnly/Strict challenge-cookie flags and no-store responses. Check desktop/mobile keyboard navigation and setup/recovery text wrapping. Confirm Operations continues using its existing access flow.
