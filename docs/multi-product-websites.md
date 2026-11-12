# Multi-product Voice AI templates

The homepage gallery presents three distinct, fictional template examples:

- `/demos/hvac`: industrial charcoal/orange, equipment hero and service rows.
- `/demos/real-estate`: Alder & Stone, warm serif editorial property composition.
- `/demos/appointments`: Morrow Studio, sage minimal appointment presentation.

Templates share typed configuration, registry, scoped primitives and approved
local artwork under `apps/web/src/features/websites`. Layout-level compositions
remain separate; no slug switch or duplicated voice backend is used. Static demos
remain independent from persisted customer/business data. Unconfigured voice
panels show written previews rather than simulated successful interactions.

Persisted configurations use the same renderer at `/sites/[slug]`. The connected
administrator workspace edits structured content, previews drafts, publishes
immutable versions, restores history and unpublishes. Provider routing and
business authorization remain server-managed.

The current implementation, restrictions, migration details, verification results,
owner deployment commands and single acceptance checklist are consolidated in
[the website platform guide](website-platform-phase2.md). Final source remains
unverified after the owner stopped checks. This is not public self-service SaaS.
