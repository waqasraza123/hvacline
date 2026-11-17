# Public GoHighLevel demo

On2026-11-18 the owner authorizes publication, API/web deployment, hosted demo
configuration, focused tests and a read-only GHL acceptance check. The intended
sub-account is confirmed fictional-only. Focused checks passed:37 Python tests
across test_ghl_demo.py/test_ghl_routes.py/test_ghl.py and6 frontend projection tests.
No broader checks, database migration or package installation is required by this
slice. Runtime/visual and live-provider acceptance remain **UNVERIFIED**.

The hosted public endpoint currently returns404 before this publication. The
local demo token is absent and demo activation remains off. Render/Vercel account
access and private credential configuration are required to complete deployment
and acceptance; no secret value is recorded here.

## What visitors see

Open `/operations` → GoHighLevel without connecting an administrator workspace.
The GoHighLevel card reads a public projection of the configured demo sub-account:
pipeline/stage names and counts for up to 100 latest opportunities, broken down
by open, won, lost and abandoned status. A timestamp records the successful read.
Empty responses remain empty; disabled/error states never substitute fake CRM
records. A failed refresh labels any previous snapshot explicitly as previous.

Other dashboard sections retain their existing local fictional records. This
does not import GHL contacts into HVACLine, enroll leads, start jobs, or prove
the administrator integration's end-to-end write/sync flow. That connection's
token, ownership, encryption and mapping controls remain separate.

## Server configuration

The root gitignored `.env` has placeholders for this setup. The owner-supplied
location ID was entered only there; the private token remains blank until the
owner supplies it securely. No ID or credential is recorded in documentation.

```dotenv
GHL_DEMO_ENABLED=false
GHL_DEMO_FICTIONAL_DATA_ONLY=true
GHL_DEMO_LOCATION_ID=
GHL_DEMO_PRIVATE_INTEGRATION_TOKEN=
```

1. Use a dedicated GHL sub-account containing only fictional data. Do not add
   customer records to it while this demo is public. Pipeline/stage names are
   publicly visible; keep those labels fictional too.
2. Create a sub-account Private Integration Token with `opportunities.readonly`.
   That is sufficient for pipeline discovery and opportunity search; this
   read-only demo does not require contact or write permissions.
3. Fill in the two credential fields on the API server. Set
   `GHL_DEMO_FICTIONAL_DATA_ONLY=true` to acknowledge the public data scope, then
   `GHL_DEMO_ENABLED=true`. Startup rejects enabled configuration without the
   acknowledgement or valid nonempty credentials. No encryption key is required
   for this read-only environment credential; the token is never written to the
   application database.
4. Local `.env` applies to the local API process only. For the public website,
   configure the same four variables in the hosted API's secret/environment
   settings and deploy the changed API/web source deliberately. The browser uses
   the existing `NEXT_PUBLIC_API_BASE_URL`; no GHL credential belongs in any
   `NEXT_PUBLIC_` variable or frontend environment file.
5. Restart/redeploy through the owner's normal process after changing server
   credentials or flags. Setting `GHL_DEMO_ENABLED=false` disables subsequent
   server reads. Do not enable `GHL_ENABLED` merely to run this showcase; that
   setting controls the separate managed CRM delivery workflow.

## Request and data boundaries

`GET /api/v1/public/ghl-demo` has no customer/admin credential requirement. Its
destination comes exclusively from server settings; request parameters cannot
choose a token, account or provider URL. Only GET requests go to the fixed GHL
origin, using API v3 and the configured location ID. Notes/tasks/calendar-event
expansion is disabled. Responses are bounded through the existing provider
client, which also supplies time/size limits and blocks redirects.

The public projection excludes contact names, emails, phone numbers, addresses,
opportunity titles/values, custom fields, tokens and all provider record IDs.
Foreign locations, unknown stages/statuses, duplicate IDs and oversized responses
are rejected rather than counted. The demo accepts at most 20 pipelines, 50
stages per pipeline and 100 opportunities; use a small dedicated demo sub-account.
The counts always describe the loaded sample, not complete business totals.

Successful snapshots are shared in API process memory for 60 seconds. A
nonblocking lock coalesces concurrent refreshes; errors back off at least 60
seconds and honor GHL Retry-After when longer. Multiple API processes each have
their own cache. No new background service, polling loop, database or dependency
is introduced. Public HTTP responses use no-store. Browser refreshes never bypass
the server's cooldown. Cached snapshots contain only the public projection.

## Focused checks and remaining acceptance

The first two commands ran successfully under the owner's authorization:

```bash
PYTHONPATH=apps/backend/src .venv/bin/python -m pytest tests/test_ghl_demo.py tests/test_ghl_routes.py tests/test_ghl.py
npm run test:web -- src/features/ghl/demo-contracts.test.ts
```

Focused backend specifications use mock HTTP providers and no database. They
cover token/data exclusion, fixed destinations, read-only methods, contactless
opportunities, foreign/stale/malformed data, empty responses, cooldown/cache,
concurrent refresh suppression and provider deadlines. Frontend specifications
cover projection validation and honest failure states. All43 focused tests passed.
The broader `npm run verify:web` remains deferred; it was not executed.

After owner-authorized service startup, the read-only local request is:

```bash
curl --fail-with-body http://127.0.0.1:8000/api/v1/public/ghl-demo
```

Use the configured API host/port if different. This command performs live GHL
reads when enabled; no write or test-data creation is performed.

Manual acceptance:

1. With the flag off, open Integrations anonymously; expect the not-connected
   state, no GHL call and no admin-token prompt for the public card.
2. With valid demo credentials, compare stage labels/counts with the dedicated
   GHL account, considering the 100-opportunity sample limit. Empty accounts show
   actual zeros and empty-state copy. Check the successful-read timestamp.
3. Inspect browser network/HTML/storage: no token, location/record IDs, contact
   details, opportunity titles/values or provider response bodies are exposed.
   Public projection requests contain no administrator credential.
4. Refresh within one minute; the snapshot may be reused. After the cooldown,
   a newly authorized fictional GHL change should be reflected on refresh.
   Demonstrating an upstream change is separate from creating it through code.
5. Use mocked/revoked credentials or a provider failure only when authorized.
   Confirm unavailable copy, clearly labeled previous data, no fabricated
   success/zero metrics and no rapid provider retries. Exercise deadline/rate
   limits through the focused mock specifications first.
6. Inspect light/dark themes, keyboard focus, loading/empty/error states and
   horizontal table scrolling at 320/768/1440px. Switch sections during a request;
   no stale result should reappear after unmount.
7. Connect an authorized administrator workspace; existing token/mapping controls
   remain required, and sample dashboard booking/payment mutations stay disabled.

Provider references: [Pipeline discovery](https://marketplace.gohighlevel.com/docs/ghl/opportunities/get-pipelines/)
and [Opportunity search](https://marketplace.gohighlevel.com/docs/ghl/opportunities/search-opportunity/)
document the v3 read-only scope and location-bound query contract.
