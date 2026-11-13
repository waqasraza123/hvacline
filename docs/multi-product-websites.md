# Multi-product Voice AI templates

The public demo showcase is disabled. Its homepage gallery, hero link and shared
navigation entry are removed; `/demos/[slug]` returns not-found. Templates and
approved artwork remain available to the administrator website editor.

Templates share typed configuration, registry, scoped primitives and approved
local artwork under `apps/web/src/features/websites`. Layout-level compositions
remain separate; no slug switch or duplicated voice backend is used.
Unconfigured voice panels show written previews rather than simulated successful
interactions.

Persisted configurations use the shared renderer at `/sites/[slug]`. The connected
administrator workspace edits structured content, previews drafts, publishes
immutable versions, restores history and unpublishes. Provider routing and
business authorization remain server-managed.

Showcase removal remains **unverified**. Owner command: `npm run verify:web`.
Manually confirm no showcase or collection links on the homepage, desktop/mobile
navigation or published websites; former demo URLs return 404; booking, calling,
pricing, website editing and published websites still work.

The current platform implementation, restrictions, migration details, verification
results, owner deployment commands and acceptance checklist are consolidated in
[the website platform guide](website-platform-phase2.md). This is not public
self-service SaaS.
