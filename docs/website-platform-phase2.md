# HVACLine website platform — final local handoff

The latest owner instruction stops all verification. Final edits are **unverified**.
No commit, push, deployment, shared/production migration, hosted agent change,
SMS or real call was performed for this task.

## Implemented

- Three distinct templates remain available to the website editor. The public
  showcase is disabled and `/demos/[slug]` returns not-found. Published
  configurations render dynamically at `/sites/[slug]`; content changes do not
  need a frontend rebuild.
- Connected Operations → Websites has a website gallery, creation/template flow,
  permanent unique slug, branding/logo/favicon, both color palettes, fonts,
  spacing, hero/images, supported sections/order, navigation, services/process,
  property showcase/story, FAQs, CTA destinations, contact details and SEO.
- Preview validates structured content and never starts an agent. Images are
  approved repository assets; remote images/uploads and custom domains are not
  exposed as unfinished controls.
- Save draft preserves the live publication and its agent/knowledge/capabilities.
  Publish creates an immutable version and atomically switches the public pointer.
  Version history supports confirmed rollback as a new publication; rollback
  leaves the saved draft unchanged. Unpublish disables public resolution and new
  sessions without deleting content/history. Every mutation checks row version.
- Published links use the existing frontend origin and `/sites/slug`; copy-link
  and open-link controls work after publication. Hosting must be deployed first.
- Homepage packages, Services, booking walkthrough and HVAC-owner FAQ are removed.
  The demo gallery and its hero/navigation links are also removed. Pricing
  remains at `/pricing`; header/footer logos, mobile navigation, calling and
  booking entry remain. Published-site utility links return to HVACLine home.

## Authorization and conversation boundaries

Management is intentionally **restricted administrator mode**, using the existing
configured business membership and administrator workspace token. Customer
login/MFA alone grants no website-management access. Management requires a token
even when the broader local sandbox gate is off. The platform remains gated to
`development`/`test`; public self-service SaaS onboarding is not production-ready.

Provider keys stay in backend settings. Browser requests cannot select business
or provider agent IDs. Public responses contain published content and capability
availability, never provider references, owner drafts or selected FAQ IDs.
Authorized site sessions reuse existing ElevenLabs signed grants, consent/MFA,
limits, session ownership, adapters and cleanup. Missing agents show unavailable;
there is no HVAC fallback. Actual live agent behavior is not verified.

Composite foreign keys scope sites, versions, bindings and conversations to the
same business. Sessions capture the published version; publishing/rebinding or
unpublishing invalidates their backend tools, while owned cleanup remains usable.
Approved FAQ lookup reads only the published version's selected active business
records. Draft changes cannot expand live knowledge. Queries still enforce
session ownership, active state and expiry. Quotas remain shared per business.

Customer-confirmed inquiries reuse transactional lead/intake persistence and
idempotency. Website booking and account memory are denied client/server,
including legacy routes; existing HVAC booking/memory remain on their established
paths. Unsupported business actions never report a successful appointment.
Existing connected provider sessions can persist until disconnect/bounded timeout
following revocation; backend tools and new grants fail closed.

Content is escaped, typed and validated in TS/Pydantic. URLs allow validated
local paths or HTTPS without credentials; assets/fonts/colors/sections are
allowlisted. No uploaded code, arbitrary CSS/HTML, executable content or secret
configuration is accepted. Owner audits store references/state, not content.

## Schema and source

- Existing `20261112_0022` introduces websites/bindings and conversation context.
- New forward revision `20261113_0023` adds `website_versions`, the publication
  pointer and conversation version binding. A trigger rejects version updates
  and deletes. Existing website records are copied into initial snapshots;
  published pointers and existing website sessions are backfilled. No existing
  business/customer/appointment/knowledge/memory/billing rows are deleted.
- Migration round trips ran only in local disposable
  `hvacline_final_test_20261113`. Production rollback uses published versions,
  not schema downgrades. Migration files were mechanically formatted; earlier
  migration SQL/string values were preserved.
- Core backend files: `websites/{schemas,service,guards,routes}.py`,
  `database/models/{website,conversation,__init__}.py`, shared conversation/FAQ
  guards and the new migration. Core web files: `features/websites/`
  (`website-manager`, `content-editor`, shared templates/renderer), `app/sites/`,
  website proxy and dashboard integration. Homepage/navigation removals remain.
- Existing web lint failures were corrected in billing loading, booking state,
  adapter cleanup, appointments, homepage restore, outbound dialog and dashboard
  links. Python formatting/import/string wrapping and narrow typing fixes span
  existing source/tests/migrations. No lint rules were disabled or dependencies
  added. Test package markers resolve duplicate module collection.

## Verification record

Before the stop instruction:

- `npm run verify:web` completed successfully: formatting, full ESLint,
  TypeScript, 256 tests/38 files and production Next build.
- Focused website/contracts/migration/ownership suite: **39 passed**, including
  draft isolation, publish/rollback/unpublish, immutable versions, agent routing,
  tenant isolation and concurrent edits.
- Full Ruff source/test/migration lint reached a passing run.
- Broader pytest completed **596 passed, 9 failed**, with three warnings.
  Failures were two stale billing error-code assertions, five reserved-domain
  MFA test emails, a production SSL fixture expectation, and exact prompt-text
  matching. Corresponding source/fixture corrections were made but not rerun.
- Full mypy reported **81 errors** in production and test files. Three production
  typing issues were subsequently corrected without rerunning; existing strict
  test typing errors remain unresolved. Do not report full mypy as passing.

Latest typing, fixture, prompt-preservation and editor fallback changes happened
without further checks after the owner stopped execution. Therefore the final
source is not verified and a clean release gate is not established. Existing
warnings include Starlette/httpx deprecation and duplicate operation IDs for two
older routes. No live browser/provider/visual acceptance was run.

Owner verification commands (not authorization for the agent to resume):

```bash
npm run verify:web
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/python -m mypy apps/backend/src tests
```

Only the named local database below is disposable; fixtures downgrade/rebuild it.
Never substitute a shared or production URL.

```bash
APP_ENVIRONMENT=test \
DATABASE_URL=postgresql://127.0.0.1/unconfigured_runtime \
DIRECT_DATABASE_URL=postgresql://127.0.0.1/unconfigured_runtime \
TEST_DATABASE_URL=postgresql://127.0.0.1/hvacline_final_test_20261113 \
DATABASE_SSL_MODE=disable CUSTOMER_PORTAL_ENABLED=false DEMO_SANDBOX_ENABLED=false \
PGOPTIONS='-c timezone=UTC' .venv/bin/python -m pytest
```

## Owner deployment and agent setup

1. Complete the owner checks above before release. Back up the intended target,
   verify `DIRECT_DATABASE_URL` is that target and preserve stable MFA/encryption
   keys. Keep the website flags off during the schema/API transition. No target
   migration or deployment is authorized by this handoff.
2. After separately authorizing the target migration, from the repository root:

```bash
APP_ENVIRONMENT=development .venv/bin/python -m alembic current
APP_ENVIRONMENT=development .venv/bin/python -m alembic upgrade head
APP_ENVIRONMENT=development .venv/bin/python -m alembic check
```

3. Deploy the matching FastAPI revision **after migration**, then Next using the
   existing Render/Vercel infrastructure. Render's configured pre-deploy command
   also runs `alembic upgrade head`; review its target before requesting a deploy.
   Next build command: `npm run build:web`. No deployment command was run here.
4. Preserve existing administrator token, development membership, portal secret,
   MFA key, backend API URL, CORS/HTTPS and provider privacy settings. Next needs
   `NEXT_PUBLIC_API_BASE_URL` and server-only `CUSTOMER_PORTAL_SECRET`. Enable
   server-side `WEBSITE_PLATFORM_ENABLED=true` on FastAPI and Next only after
   schema/backend/frontend compatibility is established. Do not expose keys or
   binding IDs through `NEXT_PUBLIC_*`. Existing HVAC flags keep their meaning.
5. Independently configure a private non-HVAC ElevenLabs agent for the business.
   Require authenticated browser connections and Text-only override support.
   Supported tools are the two definitions in `website-agent-tools.json`;
   use `website-agent-instructions.md` with approved business facts. Remove
   inherited phone/server mutation, booking and memory tools. Review actual
   retention/privacy and browser settings before confirming them in backend
   settings. No hosted agent was modified or attested by this task.
6. With separately authorized database writes, register that existing agent:

```bash
.venv/bin/python -m insurance_operations.websites.register_agent \
  --agency-id "OWNED_AGENCY_UUID" --agent-id "EXISTING_NON_HVAC_AGENT_ID" \
  --label "Property inquiries" --confirm-browser-tools-only
```

7. Connect Operations using the authorized administrator token; create a site,
   replace example content, select approved agent/knowledge, save, preview and
   publish. Share the actual frontend origin plus `/sites/slug`. Each enabled
   agent must be independently accepted; one site's success verifies no other.

## One acceptance checklist

- Inspect homepage and all demos at 320/390/768/1440px, keyboard navigation and
  both themes. Removed sections stay absent; pricing/booking/calling links work.
- Unauthorized management requests fail. Create a site, select each template,
  edit supported fields, save/reload and preview. Unsafe URLs/assets and duplicate
  slugs fail clearly. Draft preview starts no microphone/provider session.
- Publish and directly open/refresh its share URL; metadata/content match.
  Save a different draft and confirm live content/agent/knowledge are unchanged.
- Publish the saved draft, inspect version history, restore an older publication,
  verify the draft remains unchanged, then unpublish and verify public404 and
  denied new sessions. Two-tab stale saves/publications fail without lost edits.
- Using separately authorized disposable identities, attempt foreign website,
  agent, version, FAQ and session IDs; expect denial and no private data leak.
- After explicit live-session authorization, test Text and Voice independently
  for each configured agent. Verify actual agent identity, disclosure/MFA, mic
  consent/denial, selected knowledge, empty knowledge, disconnect/timeout/retry.
  Missing agents never fall back. Re-publication/revocation denies stale tools.
- Explicitly confirm one enabled inquiry; retry the same unknown result and
  verify exactly one owned intake/lead, no appointment and no account memory.
  Repeat existing HVAC booking/memory acceptance on its original routes.

External blockers are target migration/deployment authorization, dedicated
non-HVAC agent configuration/binding/privacy review and authorized live/visual
acceptance. Existing production business onboarding is insufficient for public
self-service; restricted management and development/test gates remain enforced.
