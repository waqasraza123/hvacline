# Multi-product Voice AI websites

## Phase 1 source implementation

Implementation, compilation, runtime and visual acceptance are **unverified**.
The owner policy prohibits verification execution without separate specific
authorization. Tests were written but not executed. No tests, builds, linting,
type checks, formatters, services, browser previews, provider requests, hosted
settings, database changes, commits, pushes or deployments ran for this feature.

The existing HVACLine homepage retains its hero, account header, Voice/Text
entry, call controls, billing and dashboard links. A gallery after the hero adds
three local-illustration previews and normal links to:

- `/demos/hvac`: industrial layout with an equipment-led split hero, numbered
  service rows, orange process strip and the existing HVACLine account entry.
- `/demos/real-estate`: fictional Alder & Stone, warm serif editorial layout,
  asymmetric illustrated property collection, brand story and inquiry example.
- `/demos/appointments`: fictional Morrow Studio, sage studio welcome, session
  cards, vertical appointment process and a written receptionist example.

All demos show sample-content notices. Property illustrations are original SVG
artwork, not listings or third-party screenshots. No testimonials, revenue,
invented appointments or successful calls are presented. The appointment
example is a creative consultation studio, not a medical or regulated service.

## Contracts and rendering

Source is grouped in `apps/web/src/features/websites`:

- `contracts.ts`, `validation.ts`, `templates.ts`: template IDs/layout families,
  supported/required sections, color tokens, fonts, spacing and component
  variants; website branding/content/navigation/actions/contact/SEO; and the
  separate agent contract. Unknown keys, invalid IDs, duplicate/unsupported
  sections, missing CTA targets, unsafe URLs, CSS values and unknown assets fail
  validation. No arbitrary HTML, JavaScript, React or CSS is accepted.
- `catalog.ts`: three validated, recursively frozen demo configurations. Each
  has independent parsed content and appearance. Sections are ordered data;
  layout-specific renderers compose them rather than using a slug switch.
- `assets.ts` and `public/demo-assets`: approved local artwork and brand marks.
  Configuration selects manifest IDs, not arbitrary remote/upload URLs. SVGs
  are trusted repository artwork. This is not an upload acceptance mechanism.
- `agents.server.ts`: server-only allowlisted site-to-agent aliases, business
  references, approved-knowledge references, authentication/memory requirements
  and tool capabilities. References contain no actual provider agent IDs or
  secrets. A website cannot select another registered website's binding.
- `registry.server.ts`: shared async `WebsiteConfigurationSource.findBySlug`
  boundary. It validates stored configuration and template compatibility before
  returning a frozen resolved site. Phase 2 can replace the static source with a
  Neon-backed implementation without replacing the visual renderer. Demo routes
  accept only `demo` records and fail unknown slugs closed.
- `renderer.tsx`, `layouts`, `primitives.tsx`: component registry and genuinely
  separate industrial, editorial and calm compositions. Low-level header,
  actions, FAQ, written conversation and footer are shared. Colors/font choices
  map to validated CSS variables inside a scoped root; no global template reset.
- `demo-gallery.tsx`, `gallery.module.css`: responsive collection with semantic
  links, named artwork, image sizing, keyboard focus and reduced-motion handling.
- `app/demos/[slug]`: App Router entry, static params, per-site absolute title,
  description/favicon/Open Graph text, no-index demo metadata, 404, loading and
  error presentation. Direct URL opening/refresh uses the same resolver.

Approved action URLs allow safe local paths without query parameters or HTTPS
URLs without credentials/custom ports. Section actions must target an enabled
section. Voice actions cannot carry a URL, provider ID or business ID. Plain
text is escaped by React. Fonts are local system stacks selected from an
allowlist; no remote font request or arbitrary CSS font declaration is required.

The Vitest-only `server-only` alias points to an empty test module so server
registry logic can be unit tested. Next.js retains its actual server-only
compiler boundary; no production alias or framework configuration is changed.

## Current voice and ownership boundaries

Source inspection, not hosted verification, establishes these current behaviors:

- FastAPI `application.py` constructs one browser conversation provider from
  server settings. `conversations/providers/elevenlabs.py` holds the private
  API key/agent ID and obtains short-lived WebRTC or signed WebSocket grants.
  The browser adapter receives a grant, rather than choosing an agent ID.
- `customer_access/service.py` resolves the configured development actor's
  single active agency membership. Customer login/MFA/session identity is bound
  to that business. This is not production multi-business authentication.
- `/api/v1/customer/conversation-sessions` uses the authenticated customer actor.
  The Next customer proxy keeps its portal secret server-side. Existing session
  consent, mode checks, limits, ownership and confirmation remain authoritative.
- Approved FAQ lookup uses the authorized conversation and agency. HVAC
  scheduling uses agency-owned schedules, requests, reservations and explicit
  confirmation. Existing HVAC intake schemas cannot be treated as generic
  property or studio booking schemas.
- Memory operations bind account and agency and check conversation ownership.
  None of the new demo pages reads customer identity, production FAQs, memory,
  schedules or provider state. Public example content comes from the catalog.

HVAC's binding is only an alias for continuing to the existing `/book` flow.
When the existing public browser-voice flag is enabled, the demo offers the
account-workspace entry with explicit availability/consent qualifications.
When disabled, its voice panel remains a written preview; an existing booking
link is retained separately. The flag is not proof of provider configuration or
runtime readiness. Availability is checked again by the existing backend.

The other bindings have no provider reference, no modes, no memory and no live
scheduling/lead capture. Even with HVAC voice enabled, they remain written
previews with no chat input, form submission, microphone access or provider
connection. Their CTAs scroll to the clearly labeled preview. A slug supplies
public presentation only; it never establishes an authenticated actor.

## Owner verification — not executed

From the repository root, only after execution is authorized:

```bash
npm run test --workspace @insurance-operations/web -- src/features/websites/validation.test.ts src/features/websites/registry.test.ts src/features/websites/rendering.test.tsx 'src/app/demos/[slug]/page.test.tsx' src/app/page.test.ts
npm run verify:web
```

The focused tests specify valid/invalid contracts, unsafe links/assets/fonts,
section compatibility, route lookup/404, direct-route metadata, immutable
configuration isolation, denied cross-site/arbitrary agent selection,
preview-only capability enforcement, distinct rendered content, absence of
backend requests during rendering, gallery accessibility and existing homepage
CTA compatibility. No unexecuted check is claimed to pass. Prior project notes
record existing web verification failures; their current state was not rerun.

Manual acceptance against an owner-managed deployment:

1. At 320, 390, 768 and 1440px, inspect the homepage gallery and each demo in
   light/dark modes. Confirm three distinct compositions, readable text/artwork,
   no horizontal page overflow and clear demo notices. Check mobile navigation
   wrapping and sensible image crops. This visual/responsive check has no
   automated browser result yet.
2. Tab through gallery cards, demo return links, site navigation, CTAs, theme
   switch and FAQ disclosures. Confirm visible focus, Enter activation, skip
   links, reduced-motion behavior and normal back/forward/scroll navigation.
3. Open and refresh each `/demos/...` URL directly. Confirm independent browser
   titles/favicons and original image content. Open `/demos/not-a-site`; expect
   404. Trigger an owner-controlled loading/error case if applicable.
4. Use the network panel while browsing fictional demos. Confirm local asset
   requests only, no customer/API/provider fetches and no microphone prompt.
   Inquiries/viewing/session CTAs must open the written preview without saving
   any data. Confirm no `/book` link appears on either fictional business.
5. On HVAC, check the enabled/disabled voice-flag presentations with owner-managed
   settings. The account-workspace entry must not connect automatically. Existing
   sign-in, MFA, consent and unavailable-service behavior must remain intact.
   Live conversations/calls require a separate explicit authorization.
6. Inspect the original homepage `/book`, `/pricing`, `/billing` and `/operations`
   navigation/styles. Existing hero and functional CTAs should be intact. Do not
   place a call, submit a payment or create a booking solely to inspect design.

## Phase 2 — configurable Voice AI websites

Goal: authenticated businesses manage persisted site configuration and every
configured site starts sessions against its own approved server-side binding.

1. Establish production business identity, roles and active memberships. Replace
   the fixed-development-business lookup with authenticated, authorized business
   resolution. Scope customer sign-in/MFA sessions to the resolved business;
   selecting a website must not move an existing customer session to another
   agency. Preserve the development gates until this exists.
2. Add reviewed forward migrations for `websites` (agency-owned identity, unique
   slug, template ID, configuration JSON, schema/row version, status),
   `website_agent_bindings` (agency/site ownership, provider/agent/vault references,
   approved capabilities and knowledge scope) and approved website knowledge
   associations. Use composite agency/site foreign keys and optimistic updates.
   Provider keys stay in an encrypted server-managed vault, not configuration
   JSON. Backfill only explicitly authorized business records; no automatic
   re-assignment of current customers/data.
3. Add authenticated website read/save endpoints with strict parsing and owner
   authorization. Add a Neon configuration source behind the existing source
   interface. Revalidate stored JSON; never compile or execute submitted code.
   Slug lookup resolves a public site, then authorization resolves the business.
4. Add site-scoped session authorization under the existing customer proxy. The
   backend resolves the enabled site/agency/agent and authorized customer; it
   does not accept provider/business IDs from the browser. Persist immutable
   `website_id`/`agent_binding_id` context on a conversation session using
   tenant-safe foreign keys. Dispatch provider grants from that server binding.
5. Bind FAQ/retrieval, callbacks, provider tools and signed webhooks to the saved
   conversation/site/business context and verified provider session reference.
   Add domain-appropriate inquiry/appointment contracts for non-HVAC businesses;
   reuse the durable scheduling/idempotency machinery only behind approved
   capabilities. Do not run real estate requests through HVAC intake validation.
6. Keep memory under verified account/agency ownership and opt-in policy. Define
   explicit same-business cross-site sharing rules before enabling it. Deny
   cross-agency account, memory, knowledge, booking and tool access regardless of
   URL/body/header hints. Carry forward quotas, consent, confirmation, expiry,
   rate limits and unknown-write recovery; test negative cross-tenant cases.

External setup: production identity provider/session strategy, vault encryption
keys, separately configured agents/tools/approved knowledge, provider privacy
settings and business calendars/CRM permissions. Nothing is provisioned by
Phase 1. Enable each site only after its real binding and acceptance gates pass.

Smallest next slice: authenticated agency-owned config read/save with version
conflicts and a Neon source for one preview-only website. Keep its voice disabled
until site/session binding and cross-agency denial tests are implemented. Then
connect one separately configured agent with inquiries before general booking.

## Phase 3 — website builder and publishing

Goal: create, customize, preview and publish independent websites from templates
inside the shared dashboard, with reversible content versions.

1. Build a structured editor for the existing contracts: template, sections/order,
   branding, approved fonts/colors/assets, hero/services/FAQs/CTAs, contact/SEO,
   and approved capability selections. Show only template-supported sections.
   Reuse the renderer for an authenticated, draft-bound live preview; accept no
   arbitrary HTML/JS/CSS/React. Preview URLs are access-controlled and no-index.
2. Add reviewed migrations for immutable `website_versions`, draft/published
   version pointers, approved asset records, verified domains and publication
   audits. Publish validates a complete snapshot and authorized agent binding,
   then atomically swaps the pointer. Rollback swaps to a previously authorized
   immutable version. Keep provider/credential lifecycle separate from content
   rollback; a version cannot restore revoked provider access.
3. Add authenticated asset upload to owned storage. Enforce byte/dimension/MIME
   limits, decode/re-encode raster images, malware/content policy and ownership
   checks. Reject uploaded SVG/HTML by default. Only approved, processed asset IDs
   may be published; prevent arbitrary server-side URL fetching/SSRF. Define
   retention for unreferenced drafts and keep rollback assets available.
4. Add ownership-verified custom domains: globally unique normalized hostname,
   explicit DNS verification, certificate/hosting setup and deterministic
   server-side lookup from a trusted host boundary. Unknown/unverified hosts fail
   closed. Do not trust arbitrary forwarded-host or body tenant hints. A domain
   maps to a site, which maps to an agency; authorization still checks identity.
5. Add website management in the dashboard: create from template, save draft,
   preview, publish, history/rollback, domain/asset status and provisioning state.
   Use resumable idempotent jobs for agent/provider/calendar setup, per-business
   secrets, audit trails, failure recovery and explicit enablement. Do not clone
   applications or production customer databases for every site.

External setup: owned storage/CDN, upload scanning/processing, DNS/TLS/hosting
integration, production business identity and reliable provisioning jobs.
Smallest useful builder slice: create an owned draft from a template, edit
brand/hero/services in a structured form, preview with the same renderer and
publish/rollback one version on a platform-owned subpath. Custom domains and
provider provisioning follow after that end-to-end slice is accepted.
