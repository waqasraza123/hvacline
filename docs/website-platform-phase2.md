# Phase 2 website platform

Local implementation; live provider, hosted database and visual acceptance remain
pending. No commit, push, deployment, production/shared migration, hosted agent
change, real call or provider authorization request was performed.

## Behavior and architecture

- `/demos/hvac`, `/demos/real-estate` and `/demos/appointments` retain safe static
  defaults. `/sites/[slug]` renders persisted published configurations using the
  same distinct templates. It is dynamic/no-store: ordinary content saves need
  no rebuild. Unknown/draft/disabled sites404; unavailable agents never fall back.
- `/operations` → connect workspace → **Websites** provides create/edit, template,
  branding, approved logos/artwork, colors, hero/CTA/services/contact/SEO, agent/
  knowledge selection, Voice/Text toggle, confirmed inquiries, visibility and
  preview. Version conflicts require reload. Draft previews never start agents.
- `websites` stores stable UUID/agency, unique immutable slug, template/content,
  binding/knowledge selections, capabilities, status, timestamps and row version.
  `website_agent_bindings` holds private provider references and enablement/tool
  review flags. Keys remain in existing backend settings, never website JSON.
- Conversations persist website/binding IDs and a capability snapshot. Composite
  foreign keys enforce shared agency ownership. Grant creation and tools recheck
  site/binding state. Quotas remain shared per agency; new sites cannot reset them.
- The existing `ConversationService`, provider grants, password/MFA/customer
  identity, proxy, ElevenLabs adapter, authorization parser, composer and timer
  are reused. Server-side lookup selects the agent; browsers cannot select
  provider or business IDs. The customer must explicitly start Voice or Text.
- Inquiries reuse transactional customer/intake/lead confirmation and idempotent
  recovery. Explicit confirmation is required in the shared service, including
  attempts through legacy routes. They create no appointments. Website booking
  and memory remain disabled client/server, including attempts through legacy endpoints. Existing
  HVAC account booking and optional account memory are preserved separately.
- FAQ retrieval uses the existing matcher but restricts website sessions to the
  selected active records in their agency. An empty selection exposes none.
  Public configuration and owner agent options contain no provider IDs/secrets.
- TS/Pydantic validate content, supported sections, navigation, safe URLs, hex
  colors, allowlisted fonts/assets and capability selections. No arbitrary
  HTML/JS/CSS or remote/uploaded asset URL is accepted. No dependencies added.
- Homepage steering removes compact pricing, Services and footer My package.
  `/pricing` remains. Desktop pills/Radix mobile navigation and shared footer
  logos with short captions replace the old navigation arrangement.

Source: backend `websites/`, `database/models/website.py`, conversation context
and guards in conversation/FAQ/memory/booking code; frontend `features/websites/`,
`app/sites/[slug]`, `api/websites/[slug]/[...path]`, dashboard integration and shared
conversation/auth components. Homepage navigation/provider components and tests
are updated alongside the feature.

API: public `GET /api/v1/websites/{slug}`; owner `GET/POST
/api/v1/development/websites`, `PUT /api/v1/development/websites/{id}`; customer
`/api/v1/customer/websites/{slug}/conversation-sessions`, session `/end` and
`/approved-faq-lookup`, plus `/conversation-intakes`. Save requires the expected
row version (zero for creation); unauthorized references and stale edits fail
without partial updates. Site selection supplies presentation, never authority.

Identity is still the configured development business/admin gate, not production
business onboarding. Multiple sites/agents work within that authorized business;
service/database tests cover foreign-agency denial. Customers cannot select a
different business simply by changing a slug. Existing manual memory settings
remain account/business scoped; new website conversations cannot read/write it.
Future site memory sharing needs an explicit policy. Existing provider connections
may persist until their bounded timeout after revocation, while new grants and
backend tools are immediately denied.

## Migration and external setup

Forward revision `20261112_0022_website_platform`, parent `20261109_0021`, creates
the two ownership tables and adds nullable website/binding context plus capability
JSON to conversations. No user/business/website/agent/content is automatically
seeded. Migrate before deploying the backend, even while the feature is disabled:
ORM conversation queries include the new columns. Upgrade/downgrade was exercised
only in the dedicated disposable local database; configured Neon was untouched.

After separate target/operation authorization, the owner migration command is:

```bash
APP_ENVIRONMENT=development .venv/bin/python -m alembic upgrade head
```

`WEBSITE_PLATFORM_ENABLED=false` defaults on both services. Enable the server-side
flag separately in FastAPI and Next only after schema/setup review. Next uses its
existing `NEXT_PUBLIC_API_BASE_URL`; FastAPI remains development/test gated.

For one non-HVAC business:

1. Configure a separate private ElevenLabs agent with approved domain content,
   signed browser authorization, Voice and Text-only override support. Review
   audio retention/privacy before setting the existing confirmation flag. Do not
   copy the HVAC agent just to make a button work.
2. Review hosted tools. Supported browser callbacks are `lookup_approved_faq` and
   `submit_intake_draft`; the customer confirms inquiries in the form. Disable
   inherited phone/server-side mutations, booking and memory tools. No hosted
   tools were configured or independently attested in this task.
3. Backend prerequisites are the existing API key/privacy confirmation, portal
   key, MFA encryption key, sandbox/admin gate and active development membership.
   With this platform enabled, customer identity no longer requires a default
   HVAC agent. Provider keys must stay out of client config and command arguments.
4. After explicit database-write authorization, register the existing agent:

```bash
.venv/bin/python -m insurance_operations.websites.register_agent \
  --agency-id "OWNED_AGENCY_UUID" --agent-id "EXISTING_NON_HVAC_AGENT_ID" \
  --label "Property inquiries" --confirm-browser-tools-only
```

This command was **not executed**. It writes a trusted binding, enforces unique
provider-agent ownership and prints its UUID without changing ElevenLabs. This
slice shares the existing backend provider account/key; independent credential
vaults and production onboarding remain future work.

5. Create a site in Websites, replace example content, select its authorized
   agent and approved FAQ subset, enable the intended capabilities and publish.
   Visit `/sites/slug` using the current business's customer login/MFA realm.

No non-HVAC binding was registered in the configured database and no live browser
session was started. The live end-to-end completion criterion remains open;
mocked calls and successful compilation do not satisfy it.

## Verification and manual acceptance

Session results are recorded in project-state/current-session notes. Initially
`npm run verify:web` stopped on49 formatting warnings. Phase1/touched files were
formatted; the next attempt stops on15 older files outside this slice. The
aggregate command is not claimed to pass. Results on November 13, 2026:

| Check | Result |
| --- | --- |
| Full web tests | 256 passed across 38 files |
| Web typecheck and production build | Passed, including demos and dynamic site route |
| Website/navigation scoped ESLint | Passed |
| Backend suite listed below | 102 passed; one existing Starlette/httpx deprecation warning |
| New backend Ruff and mypy | Passed; mypy checked seven source files |
| Aggregate `verify:web` | Stopped at 15 preexisting formatting warnings |
| Full `lint:web` separately | 11 errors and three warnings in older code |
| Hosted provider/browser, visual and configured Neon acceptance | Not run |

The remaining formatting paths are account/outbound/development API proxies and
their tests, root layout, MFA page, brand/theme toggle, billing CSS, customer proxy/
server test and outbound demo components. Full lint errors are in billing dashboard,
browser booking/configured adapter, customer appointments, homepage chat, calendar
connections, dashboard demo and outbound dialog. Those unrelated implementations
were preserved. Full logs were inspected; no failed aggregate check is reported
as passing. The backend run covers website contracts/persistence/HTTP/MFA,
cross-business references, distinct agents, FAQ isolation, memory/capability
denial, real concurrent edits, migration round trips and existing HVAC booking.

```bash
npm run verify:web
npm run typecheck:web
npm run test:web
npm run build:web
npm exec --workspace @insurance-operations/web -- eslint src/features/websites src/app/sites src/app/api/websites src/components/header-navigation.tsx src/components/provider-logos.tsx src/features/customer/auth-continuation.ts
```

Only the newly created local `hvacline_websites_test_20261112` is disposable.
Its fixtures rebuild/downgrade it. Never substitute shared/production URLs. Legacy
conversation fixtures inherit optional flags from local env; these process-local
overrides isolate their defaults while explicit test constructor settings win.
`PGOPTIONS` makes disposable connections use UTC, matching existing booking
serialization assertions independently of the local PostgreSQL timezone:

```bash
APP_ENVIRONMENT=test \
DATABASE_URL=postgresql://127.0.0.1/unconfigured_runtime \
DIRECT_DATABASE_URL=postgresql://127.0.0.1/unconfigured_runtime \
TEST_DATABASE_URL=postgresql://127.0.0.1/hvacline_websites_test_20261112 \
DATABASE_SSL_MODE=disable CUSTOMER_PORTAL_ENABLED=false DEMO_SANDBOX_ENABLED=false \
PGOPTIONS='-c timezone=UTC' \
.venv/bin/python -m pytest tests/test_website_contracts.py tests/database/test_websites.py tests/database/test_migrations.py tests/database/test_table_ownership.py tests/database/test_conversation_api.py tests/database/test_hvac_scheduling.py tests/database/test_customer_memory.py tests/test_conversation_provider.py tests/test_conversation_provider_selection.py tests/test_customer_mfa_settings.py
```

The venv's pytest launcher has a stale interpreter path; use `python -m pytest`.
Focused lint/type commands:

```bash
.venv/bin/ruff check apps/backend/src/insurance_operations/websites apps/backend/src/insurance_operations/database/models/website.py migrations/versions/20261112_0022_website_platform.py tests/conftest.py tests/test_website_contracts.py tests/database/test_websites.py
.venv/bin/python -m mypy apps/backend/src/insurance_operations/websites apps/backend/src/insurance_operations/database/models/website.py
```

Manual checks (live sessions/data writes need separate authorization):

1. At320/390/768/1440px in both themes, inspect homepage/header/footer and demos:
   no page overflow,44px controls, keyboard focus, menu Escape/outside dismissal,
   focus restoration and anchors. Narrow-screen theme control is inside the menu.
2. Check homepage pricing/services/package removals, `/pricing`, gallery, `/book`
   auth/consent and `/operations`. Navigation must not request the microphone.
3. In authorized disposable/staging data, create/edit/save/reload/preview a draft,
   publish and refresh `/sites/slug`. Verify metadata, missing/disabled404,
   validation and a two-tab version conflict. Template changes reset defaults.
4. Inspect network payloads for no provider IDs/keys/private cross-business data.
   Using separate test identities, attempt foreign site/agent/FAQ IDs; expect
   denial. Empty knowledge selection must retrieve no other agency/site records.
5. With an independently configured agent and explicit live authorization, test
   **Text first**, verify the actual provider agent, selected/unselected knowledge,
   finish and then separately test Voice/mic consent/denial/mute/timeouts/retry.
   There must be no fallback, automatic connection or cross-site memory.
6. Explicitly confirm an enabled inquiry. Check one owned customer/intake/lead on
   unknown-response retry and no appointment. Disable/rebind the site; new grants
   and tools must fail, while its owner can still end the existing session.
7. Independently repeat agent/knowledge checks for every other enabled website.
   One successful site's conversation does not verify another site's provider.

## Phase 3

Complete production identity/roles, customer realm onboarding and credential vault
provisioning first. The smallest useful next slice is immutable website versions
and atomic publish/rollback pointers behind existing owner authorization; it needs
a forward migration for versions, publish timestamps and owner audit references.
Reuse this structured editor/renderer for preview and version restoration. Add
owned uploads with MIME/dimension/decode validation and approved processed IDs;
reject uploaded SVG/HTML by default. Custom domains require normalized unique
hostnames, DNS ownership verification, trusted-edge host lookup and TLS; unknown
hosts fail closed. Non-HVAC scheduling requires an approved domain workflow
before lifting the current backend capability denial.

## Changed source map

- Backend: `websites/{schemas,guards,service,routes,register_agent}.py`,
  `database/models/{website,conversation,__init__}.py`, `application.py`,
  `settings.py`, `conversations/{service,booking}.py`,
  `approved_faqs/service.py`, `customer_access/routes.py`,
  `customer_memory/service.py` and `.env.example`.
- Schema: `migrations/versions/20261112_0022_website_platform.py`.
- Web: `features/websites/{published.server,editor,website-manager,website-voice}`
  and related CSS/tests; existing website contracts/primitives/styles;
  `app/sites/[slug]/{page,loading,error,not-found}.tsx`;
  `app/api/websites/[slug]/[...path]/{route,route.test}.ts`;
  `features/conversation/{api,elevenlabs-adapter,chat-composer}` and related tests;
  `features/customer/auth-continuation` and test; dashboard shell/demo/workspace.
- Homepage: `app/{page.tsx,page.test.ts}`, shared
  `components/{header-navigation,provider-logos}` and their CSS. Two existing
  customer proxy test stream annotations were adjusted for TypeScript 6.
- Backend tests: `tests/conftest.py`, `tests/test_website_contracts.py`,
  `tests/database/{test_websites,test_migrations,test_table_ownership}.py`.
- Documentation: README, this guide, `multi-product-websites.md`,
  `project-state.md` and local current-session notes.

The checkout already contained unrelated work. This inventory describes the
Phase 2 changes, not every path shown by Git status.
