# Business onboarding and staff access — Step 3

Source implemented November 26, 2026. **UNVERIFIED**. Owner requested the next
feature and publication to main. This release uses owner-created businesses with
invited staff, the assumption stated when implementation began. No checks,
formatters, migrations, services, email sends or provider changes ran.

## User flow

- `/workspace/setup` lets the deployment's platform operator create a business
  and initial owner invitation. It requires the separate platform-owner key.
  Business names, identifiers and owner emails are supplied by the operator;
  there are no seeded customers, schedules, telephone numbers or agents.
- The private invitation is displayed once for manual secure sharing. It expires
  after48hours and is not automatically emailed. Its token travels in the URL
  fragment, is removed from browser history on opening, and is submitted only in
  request bodies. The database stores only its digest. Replacing an unaccepted
  initial owner invitation revokes earlier initial links. Once an owner joins,
  platform setup cannot use that replacement action to bypass their sign-in.
- New staff choose a password of at least15characters and enroll an authenticator.
  Only a verified current code creates their account, membership and session.
  Existing staff sign in and explicitly accept the invitation with the matching
  staff email; an invitation cannot reset an existing staff password or factor.
- `/workspace` provides business selection, owned queue metrics, requests,
  appointments and follow-up controls. Owners/admins also manage team invitations,
  membership status/roles, the business profile and scheduling. The existing
  operations demo links to Staff sign in; customer account routes remain separate.

| Role | Business queues and follow-up | Profile/scheduling | Team access |
| --- | --- | --- | --- |
| Owner | Yes | Yes | Invite/manage all roles |
| Administrator | Yes | Yes | Invite/manage staff only |
| Staff | Yes | No | No |

Team writes serialize on the business record, check current permission and require
the loaded membership/invitation version. At least one active owner must remain;
an outstanding owner invitation does not count. Pending grants are checked against
the inviter's current authority on acceptance. Deactivation or role changes affect
new requests, including requests from an already signed-in browser.

Business creation has a client creation key and payload fingerprint. A retry with
the same key/details returns the original business without returning the secret
invitation again. Changed details with the same key fail. A lost result requires
reviewing saved businesses; the platform operator can replace the initial link
while no owner has joined. Mutations are not automatically retried by the web UI.

## Access and integration boundaries

The new `/api/v1/workspace` routes use a dedicated server-to-server portal key and
independent staff credentials/session resolution. They never fall back to a
configured development actor, customer cookie or client-supplied role/business
membership. Every selected business is checked against current active membership
and the new business registry. There is no automatic claim of legacy agencies.

Passwords reuse the existing scrypt implementation. Authenticator secrets reuse
the existing context-bound encryption and replay-resistant TOTP primitives with
a separate workspace encryption key. Incomplete enrollment stores an encrypted
pending secret and password hash on the invitation; neither grants staff access.
Five failed enrollment codes exhaust that invitation. Sign-in permits at most10
attempts per normalized email per15-minute window, including successful attempts.
A shared persistent budget also limits sign-in requests across emails to120 per
minute by default (`WORKSPACE_LOGIN_PER_MINUTE`,10–1000). Both checks run before
password verification. No password-only session or MFA-disable path is provided.

Staff sessions expire after8hours. Only their digests are stored. Next.js places
the session token in a separate HttpOnly, SameSite=Strict cookie, with Secure and
the `__Host-` prefix in production. Verified session tokens are removed from
browser JSON. Mutations require the same website origin, JSON/body bounds and an
explicit route allowlist; browser-provided Authorization/access-key headers are
not forwarded as staff identity. Backend redirects are rejected. Sign-out revokes
the backend session before clearing its cookie; failure asks the user to retry.

Business profile, scheduling and follow-up reuse existing services with the
membership-resolved agency. Existing customer and development endpoints retain
their gates. Workspace keys must be distinct from customer/development keys.
API and browser responses containing account/invitation data are uncached.
Audits contain references/roles and exclude tokens, passwords, setup secrets and
message contents.

This feature does not provision carrier numbers, hosted agents, Google OAuth,
CRM credentials or customer routing for new businesses. Their existing provider
and production activation gates remain. Profile/schedule saves do not certify
those integrations. Automatic invitation email, self-service business signup,
staff password/lost-factor recovery and automatic identity-retention cleanup are
outside this step. Recovery needs a deliberate later implementation; there is no
support bypass. No production/security/provider acceptance is claimed.

## Migration and owner setup — not performed

Forward migration `20261126_0030` follows pending0029. It adds role to
`agency_memberships` with a conservative STAFF default for existing memberships,
plus `workspace_businesses`, `workspace_credentials`, `workspace_sessions`,
`workspace_invitations` and `workspace_login_limits`. It does not enroll legacy
users or confer owner/admin authority on existing rows. Downgrade refuses while
business/credential/invitation history remains.

Apply0030 before deploying the combined API source, even when the workspace flag
is off: the membership ORM now selects the role column. Deliberately select the
target first; do not point database tests at the shared target. Upgrading to0030
also applies the pending0029 staff-alert prerequisite.

On the API configure distinct, securely generated values for
`WORKSPACE_PORTAL_SECRET` (at least32characters),
`WORKSPACE_MFA_ENCRYPTION_KEY` (Fernet), and the optional
`WORKSPACE_BOOTSTRAP_TOKEN` (at least32characters). Keep the encryption key stable
and backed up; replacing it without re-encryption makes existing factors
unreadable. Provisioning is unavailable while the bootstrap key is unset.

The Next.js server needs the matching `WORKSPACE_PORTAL_SECRET` and the existing
HTTPS `NEXT_PUBLIC_API_BASE_URL`. Neither bootstrap nor MFA keys belong on the
web server or in public variables. The platform operator enters their bootstrap
key only in the protected setup form; it stays in page memory. Set API
`WORKSPACE_PORTAL_ENABLED=true` only after migration/configuration review. The
default and environment examples remain disabled. There are no new dependencies.

## Owner commands

From `/Users/mc/development/hvacline`, when specifically ready to execute:

```sh
npm run test:web -- src/features/workspace/api.test.ts src/features/workspace/proxy.test.ts src/features/operations/follow-up.test.tsx src/features/operations/dashboard.test.tsx
APP_ENVIRONMENT=test python -m pytest tests/test_workspace_access.py tests/test_settings.py
npm run verify:web
python -m ruff check apps/backend/src tests migrations
python -m mypy apps/backend/src
```

Only on an explicitly selected isolated disposable `TEST_DATABASE_URL`:

```sh
APP_ENVIRONMENT=test python -m pytest tests/database/test_workspace_onboarding.py tests/database/test_migrations.py tests/database/test_table_ownership.py tests/database/test_conversation_api.py
```

These fixtures rebuild/downgrade their test target and clear disposable workspace
identity/provisioning rows so history-preserving downgrade guards can run. The
cleanup is test-only. Never use a shared development or production database.

For the separately reviewed intended development database:

```sh
APP_ENVIRONMENT=development python -m alembic upgrade 20261126_0030
```

No command above ran here. Publication alone does not apply this migration,
configure keys, enable the portal or establish runtime acceptance.

## Owner manual checks

1. Verify disabled/misconfigured portal errors, missing/incorrect platform key,
   absent staff identity and expired/revoked sessions. Customer cookies and the
   development administrator token must not become staff sessions.
2. Create two approved sample businesses. Check creation replay/different-payload
   conflict, no automatic data/provider activation, one-time link display and
   initial invitation replacement. Observe no outbound email or provider request.
3. Accept an invitation through its fragment link. Confirm its token disappears
   from the address bar, stays out of HTTP URLs and cannot grant access before
   password plus authenticator verification. Test wrong/expired codes, five failed
   attempts, QR/manual enrollment, cancellation, consumed/revoked links and a
   fresh sign-in after enrollment. An already consumed TOTP code must fail.
4. With existing staff, require sign-in and explicit acceptance. Wrong-email
   accounts must be rejected. Confirm an invitation cannot replace their password
   or factor. Revoke/demote the inviter before acceptance and check the grant fails.
5. Compare Owner/Admin/Staff controls and call the same APIs directly with approved
   test sessions. Staff cannot manage the team/profile/schedule; admins cannot
   grant or modify owner/admin access. Cross-business IDs must fail, including
   follow-up and scheduling requests. Data from another business must never appear.
6. Use two owner sessions to demote/deactivate concurrently. Exactly one active
   owner must remain. A pending invitation cannot replace that requirement. Stale
   member/invitation versions must fail and require reloading saved state.
7. Deactivate a member or change their role while their session remains open.
   Confirm new requests use the updated access. Check sign-out revocation, blocked
   backend/network sign-out, account switching, cookies and no session token in
   browser JSON/storage. Sign-in rate limits must survive failed requests.
8. Save each business's reviewed profile/schedule and inspect the other business's
   values. Test version conflict and lost-response recovery, empty queues, owned
   follow-up actions and unchanged hazard/readback booking behavior. Confirm phone
   and agent setup remains a separate prerequisite.
9. Check320/390/768/1440px, both themes, keyboard focus, form labels, invitation
   copy feedback and business switching without stale data/drafts. Regression-check
   existing customer MFA/booking, public demo, staff alerts and development routes.

Record owner results before removing **UNVERIFIED**. The next source slice,
[telephone account access](telephone-account-access.md), adds call-bound browser
approval for existing customer information. Telephone appointment changes remain
separate; existing browser booking changes are retained.
