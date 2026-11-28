## Shared external provider notifications — source UNVERIFIED — 2026-11-28

Owner requested completing and pushing the pending notification work. Source adds
request-local, bounded provider/category collection for existing external adapters,
safe HTTP/header/proxy propagation and shared Sonner notifications for interactive
web requests and supported saved job/status failures. Handled upstream API errors
use HTTP424; ordinary application errors without provider evidence retain their
status. Approved ElevenLabs account copy remains separate from other categories.
Server rendering skips notifications; JSON inspection is bounded and response
bodies remain readable. SDK asynchronous connection rejection is handled; normal
endings/microphone errors do not generate provider toasts. Existing unknown-outcome,
retry/idempotency/no-redial/ownership controls and feature gates remain in place.

No new schema/configuration, live balance queries or background browser delivery.
Added unexecuted regressions and owner guide: docs/external-provider-notifications.md.
No tests/builds/linters/type checks/migrations/services/providers/deployment ran.
Runtime/security/visual acceptance remains UNVERIFIED. Publish source/docs normally
to main, preserving history/tags, disabling hooks and retaining [skip ci] [skip render].
Publication outcome is recorded in local session memory.

## External ElevenLabs failure notification decision — UNVERIFIED — 2026-11-27

Owner requested Sonner-backed toast presentation for external ElevenLabs billing,
credit and account-access restrictions, with supplied credit/refill wording and
explicit separation from application server errors. Source carries a sanitized
provider marker and uses HTTP424 for known interactive provider restrictions;
SDK error/connection/disconnect boundaries also notify. Generic application/auth/
network/rate errors retain their own handling. No live balance query or migration.
Dependency metadata and unexecuted regressions are added; no checks, services,
provider calls or publication/deployment ran. Owner commands/manual acceptance,
exact copy, supported web flows and background-notification boundary:
docs/elevenlabs-error-toasts.md. Outcome remains local and UNVERIFIED.

## Canonical dashboard route decision — source UNVERIFIED — 2026-11-27

Owner selected /dashboard as the canonical dashboard route, including all nested
section and settings URLs. Source now mounts its validated catch-all page under
app/dashboard. Public links, route mapping, breadcrumbs, current guides and
regression expectations use /dashboard. Next configuration permanently redirects
legacy /operations and descendant URLs to the matching /dashboard path. Backend
operations endpoints and internal feature-module names retain their contracts.
No execution checks/services/publication/deployment ran. Runtime, redirect and
visual acceptance remain UNVERIFIED. Exact owner commands/manual checks:
docs/operations-dashboard.md. Source outcome/handoff is in local session notes.

## Telephone account access — source UNVERIFIED — 2026-11-26

Owner requested the next feature. Implemented /phone-access with fixed MFA login
continuation, explicit masked call review/approval, optional memory consent and
revocation/history. Four provider tools bind one active PHONE conversation to the
approving customer session. Shared identity resolution rechecks session/MFA/user/
business state for each read. Caller ID/email matching grants no account access;
queries return only owned upcoming confirmed appointments and separately allowed
bounded memory. Existing browser booking changes remain separate.

Migration20261126_0031 after pending0030/0029 adds customer_phone_access and
composite ownership constraints; UNAPPLIED. API and Next server flags default off;
existing development-only customer/provider gates remain. No hosted tools changed,
no tests/builds/linters/type checks/migrations/services/providers/sends/deployments
ran. Added unexecuted isolation/revocation/expiry/replay/concurrent-approval/schema/
proxy regressions. Runtime/security/provider/visual acceptance UNVERIFIED. Owner
setup, exact commands and manual checks: docs/telephone-account-access.md.
Closing tabs/local cookie clearance do not prove server session revocation; use
explicit call revocation. No production customer identity or telephone booking
mutations are introduced. Owner subsequently requested publication to main. Push
the scoped source/docs without hooks or force, retaining [skip ci] [skip render].
No execution checks or activation are authorized. Outcome: local handoff.

## Business onboarding and staff access — source UNVERIFIED — 2026-11-26

Owner requested the next feature and push to main. Implemented owner-created
businesses with invited staff as the stated default: /workspace/setup and
/workspace, an independent portal proxy/HttpOnly cookie and password plus required
TOTP sign-in. Single-use/expiring invitations, membership-derived tenant access,
Owner/Admin/Staff permissions, last-owner protection and versioned team writes
reuse existing identity/crypto/profile/scheduling/follow-up conventions. Existing
customer/development actors are not staff sessions; legacy agencies are not
claimed. Invitations are manually shared; no automatic email/provider activation.

Migration20261126_0030 after pending0029 adds five workspace tables and a STAFF
membership-role default; UNAPPLIED. Apply before combined API deployment because
membership reads include the new role column. Portal defaults off. Added
unexecuted access/tenant/concurrency/replay/proxy regressions, schema/ownership
specs and disposable-test cleanup. No tests/builds/linters/formatters/type checks/
migrations/services/sends/providers/deployments ran. Security/runtime/visual
acceptance is UNVERIFIED. Commands/setup/manual scenarios:
docs/business-onboarding.md. Publish scoped source/docs without hooks or force,
retaining [skip ci] [skip render]. Publication result belongs in local handoff.

## Follow-up and Resend staff alert publication authorized — 2026-11-26

Owner requests pushing the completed Steps1–2 source to main. Local/remote main
start atc47aa7881195203b9a013bfecffb8080f825faea. Publish scoped backend/web,
migration0029, unexecuted tests and guides with hooks disabled and existing
[skip ci] [skip render] markers. Preserve history/tags and use a non-force push.
No checks, services, migrations, sends, activation or deployment commands are
authorized. Migration0029 remains UNAPPLIED and staff email defaults off.
Acceptance remains UNVERIFIED; exact owner commands/manual scenarios:
docs/staff-follow-up.md and docs/staff-email-alerts.md. Outcome: local handoff.

## Receptionist sequence Steps 1–2 — local source, UNVERIFIED — 2026-11-26

Owner requested implementing the reviewed gaps one by one and selected Resend
email for staff alerts. Step1 adds connected Operations follow-up status controls,
contact context and queue filters/age using existing tenant-scoped audited/versioned
transitions; demo stays read-only. Step2 adds per-business staff recipient settings,
prospective transactional handoff/hazard capture, immutable email outbox, bounded
same-key job delivery and signed Resend receipt projection. Staff email runtime
flag defaults off and existing development identity gates remain.

Forward migration20261126_0029 after0028 is UNAPPLIED. New sources/tests/docs,
metadata expectations and disposable-test cleanup are implemented locally. No
tests/builds/linters/formatters/type checks/migrations/services/providers/sends/
activation/commits/pushes/deployments ran. Runtime/security/provider/visual
acceptance is UNVERIFIED. Exact owner commands/manual checks:
docs/staff-follow-up.md and docs/staff-email-alerts.md. Later onboarding/caller
verification/reporting/account-recovery work is not implemented by these slices.
Business-onboarding model selection remains pending before Step3.

## Web redesign publication authorized — UNVERIFIED — 2026-11-25

Owner explicitly requests pushing the completed web redesign to main. Local and
remote main both start at1a7c4a13f64f08ee5ef6a9dd683cc3a4c5b1f79b. Publication
includes the frontend source, unexecuted regression source and design/feature
notes. Preserve existing history and tags; use a normal non-force push with
[skip ci] [skip render] and hooks disabled. No execution checks, services,
providers, migrations or deployment commands are authorized. Runtime/visual/
accessibility acceptance remains UNVERIFIED; owner commands/manual checks:
docs/web-design-system.md. Publication outcome is recorded in local handoff.

## Shared web redesign — local source, UNVERIFIED — 2026-11-25

Resumed the owner's frontend-only redesign. Root-loaded design tokens and scoped
control styles unify neutral/orange light/dark application shells. Operations
keeps existing section keys/access gates with grouped navigation, loaded-queue
metrics, upcoming/attention panels and five latest received calls. General/Voice
settings tabs retain mounted drafts and expose cancellation to saved values.
Recovery uses shared metrics/loading states, selected-case styling and a strictly
fictional selected-lead timeline/confirmation. Homepage/navigation/customer forms,
appointments/memory/MFA/details share typography and theme-aware status surfaces.
Published website templates retain their scoped styling; backend/native/provider/
booking/authentication contracts and activation flags are unchanged.

Added unexecuted regression source for navigation gates, loaded records/order,
empty queues, tab-panel retention and recovery rendering. Static source review
only; no tests/builds/linters/formatters/type checks/browser checks/services/
installs/migrations/providers/commits/pushes/deployments ran. Runtime, visual and
accessibility acceptance remain UNVERIFIED. Source is local only. Owner commands
and exact responsive/theme/keyboard/draft/manual checks: docs/web-design-system.md.

## Three homepage sections removed — UNVERIFIED — 2026-11-24

Owner requested removal of HVAC PHONE EXAMPLE, HOW THE HVAC EXAMPLE WORKS and
the AI LEAD RECOVERY teaser. Removed their homepage markup/component imports;
hero/badges now lead directly into the closing CTA. Hero calling links/dialog
and dedicated recovery page remain available. Updated homepage copy guide.
No verification commands or services ran; implementation/visual acceptance
remain UNVERIFIED. Owner command: `npm run test:web -- src/app/page.test.ts`.
Manual: inspect `/` on phone/desktop in both themes, confirm the three sections
are absent, spacing flows into the closing CTA and hero calling actions remain.

## Full staged snapshot committed; history merge prepared — 2026-11-21

Owner ran git add . and requested commit/push of every staged file. Committed
the exact428-file snapshot asd7058ea8997844945562e3083d34b6291bcb88bc on local
main, parent1297b0a. Message covers mobile, multilingual voice, lead recovery
and platform refinements; retains [skip ci] [skip render]. No hooks/checks ran.
Most staged content already matches published mainb956ac8. Merge preserves both
commit histories and the owner's staged application source. Six overlap conflicts
are resolved with staged source/guides, retaining recorded public-demo test
evidence and correcting the navigation guide to the already-implemented pathname
behavior. Current migration readbacks in staged guides supersede older pending
notes. No tests/builds/linters/type checks/services/migrations/provider/deployment
commands ran; broader runtime/security/visual acceptance remains UNVERIFIED.
Publication result is recorded separately. Never force-push the old local history.

## Professional homepage presentation published — UNVERIFIED — 2026-11-21

Publishedb956ac8c895c68719a8a1b6cbc949e4fa4e20eea on canonical main from
8655d8d9b32a17a6485505e4ee0df34417ba20be via expected-head non-force Git-data
update; remote main readback matches. Commit comparison confirms exactly nine
scoped paths (one new CSS module) and one descendant commit. Unrelated remote
source/historical notes, local branch/index/divergent history and tags remain
preserved. Retained [skip ci] [skip render]. No tests/builds/linters/formatters/
type checks/browser checks/services/providers/deployment commands ran. Visual/
runtime acceptance remains UNVERIFIED. Owner commands: `npm run test:web -- src/app/page.test.ts`,
`npm run verify:web`; exact manual checks: docs/homepage-branding.md.

## Homepage polish publication authorized — UNVERIFIED — 2026-11-21

Owner requests push of the professional homepage presentation. Scope is five
source paths (one new CSS module), three homepage guides and durable memory.
Publish from canonical main8655d8d while preserving unrelated remote/local source,
remote historical notes and divergent local branch/index/history. Retain
[skip ci] [skip render]. No execution checks/services/deployment authorized.
Implementation and visual/runtime acceptance remain UNVERIFIED; publication
result is recorded separately.

## Professional homepage presentation — local, UNVERIFIED — 2026-11-21

Owner requested further homepage beautification. Added a route-scoped CSS module
and wrapper for system typography, quieter navigation, softer buttons, framed
demo, full-width six-tag feature strip and consistent section/footer spacing.
Retained orange/charcoal/full-width identity and all Preview/Sandbox labels.
Added a concise explanation of the existing HVAC describe/select/confirm flow
and secondary dashboard link. Homepage-only conversation/recovery styles have
larger text and a refined teaser. Closing CTA has a fixed dark surface in both
themes; mobile theme remains in the drawer while duplicate header toggle hides
at480px. Existing authentication/consent/booking/provider behavior is retained.

Five source paths: apps/web/src/app/page.tsx, new homepage.module.css,
features/homepage-chat/homepage-chat.module.css, features/recovery/homepage.tsx
and features/recovery/recovery.module.css; plus three homepage guides and notes.
No tests/builds/linters/formatters/type checks/browser checks/services/providers/
dependencies/publication/deployment ran. Implementation and visual/runtime
acceptance remain UNVERIFIED. Owner commands: `npm run test:web -- src/app/page.test.ts`,
`npm run verify:web`; exact responsive/theme/interaction checks:
docs/homepage-branding.md. Source is local only; preserve unrelated edits,
index and divergent history. Latest published main remains8655d8d.

## Homepage UI published — runtime UNVERIFIED — 2026-11-21

Published8655d8d9b32a17a6485505e4ee0df34417ba20be on canonical main from
2ed275a905b132536f8a934e10fb5a5cf658cac1 through expected-head non-force
Git-data update; remote main readback matches. Commit comparison confirms exactly
eight scoped source/test/guide/memory paths and one new descendant commit.
Unrelated remote source/historical notes, local branch/index/history and tags
remain preserved. Commit retains [skip ci] [skip render]. No tests/builds/linters/
formatters/type checks/browser checks/services/provider/deployment commands ran.
Implementation and visual/runtime acceptance remain UNVERIFIED. Owner commands:
`npm run test:web -- src/app/page.test.ts`, `npm run verify:web`; responsive,
theme and navigation manual checks: docs/homepage-branding.md.

## Homepage UI publication authorized — UNVERIFIED — 2026-11-21

Owner requests push to main. Publish the homepage hierarchy pass in eight scoped
source/test/guide/memory paths from canonical main, preserving unrelated source,
remote historical notes and divergent local branch/index/history. Retain
[skip ci] [skip render]. No tests/builds/linters/type checks/browser checks/services
or deployment commands are authorized by this publication. Runtime and visual
acceptance remain UNVERIFIED; publication result is recorded separately.

## Homepage hierarchy pass — local source, UNVERIFIED — 2026-11-21

Owner authorized simplified homepage header, improved hero spacing, compact
badges and corrected navigation selection. Home keeps provider/GitHub branding
in the existing footer; header retains brand/navigation, theme/account and Voice
CTA. Hero copy is shorter, columns use zero minimum widths and stack at850px.
Secondary call links are quieter; six badges retain their feature/Preview/Sandbox
labels with reduced chrome and larger captions. Existing orange/charcoal theme,
full-width gutters and authentication/consent/provider behavior remain.

Shared HeaderNavigation now derives the active destination from Next pathname,
with aria-current=page on matching routes only; home has no selected destination.
Added unexecuted matched/unmatched route cases to the existing homepage suite.
No tests/builds/linters/formatters/type checks/browser checks/services/publication/
deployment ran. Implementation and visual/runtime acceptance are UNVERIFIED.
Owner commands: `npm run test:web -- src/app/page.test.ts`, `npm run verify:web`.
Manual responsive/theme/navigation checks: docs/homepage-branding.md. Changes
are local only; preserve existing unrelated edits, index and divergent history.

## Multilingual homepage hero badge published — UNVERIFIED — 2026-11-21

Owner requests a hero tag instead of the separate multilingual homepage card.
Homepage now adds Multilingual after WebRTC with a shared language/translation
SVG and Language support · Preview caption, reusing the current responsive badge
style and theme. Removed the unused card component/teaser CSS; dedicated demo,
Operations entry and README link remain. Existing hero aria-label expectation
and homepage/multilingual guides are updated. No backend/provider/schema change.

No tests/builds/linters/formatters/type checks/browser checks/services ran.
Owner commands: `npm run test:web -- src/app/page.test.ts`, `npm run verify:web`.
Manual: absent card, aligned icon/tag, mobile/desktop wrapping, both themes and
Operations demo access. Published 2ed275a905b132536f8a934e10fb5a5cf658cac1 on
canonical main from d62e390 via expected-head non-force update; remote readback
matches. Eight scoped paths include the deleted card component and current guide
status for the previously applied migration0028. Retained [skip ci] [skip render],
local index/history, unrelated source and tags. No deployment command ran.
Visual/runtime acceptance remains UNVERIFIED.

## Multilingual demo reducer correction — owner-confirmed — 2026-11-21

Owner reports a Vercel TypeScript failure for comparing booked after the reducer's
early terminal guard. Source removes both redundant later booked checks; Reset
still precedes the terminal guard and conversation transitions are unchanged.
No checks/services/migrations/deployment commands ran. Owner commands:
`npm run typecheck:web`, focused multilingual-demo.test.ts and `npm run build:web`.
Published the one-file correction as d62e390be6dfffbaf455cbdc75c7012e7ecf2c04
on canonical main from a897702 via expected-head non-force update; remote
readback matches. Retained [skip ci] [skip render], unrelated source/index/history
and tags. Owner subsequently reports “it worked,” confirming resolution of the
reported build issue. Specific command results were not supplied; no additional
checks ran here. Broader multilingual/provider/native/runtime acceptance remains
UNVERIFIED.

## Configured Neon upgraded through multilingual0028 — 2026-11-21

Owner explicitly requested migrations. The configured direct Neon development
target matches the application database and is distinct from the disposable
test target. Initial sole revision20261120_0027; applied20261121_0028 successfully.
Post-migration readback confirms sole0028, non-null JSONB voice_languages with
empty-object default and the validated object-type constraint. No non-default
language configuration exists. Do not rerun this completed migration on the
same target; other database targets require deliberate selection.

Only migration preflight, the authorized upgrade and necessary schema/configuration
readback ran. Initial sandbox connection failed; approved network access completed
the operation. No customer records, tests/builds/linters/type checks/services,
providers/calls, credentials/activation changes, publication or deployment commands.
Application/provider/native/security/visual/language acceptance remains UNVERIFIED.
Owner acceptance and external provider setup: docs/multilingual-voice.md.

## Multilingual AI Voice published — runtime UNVERIFIED — 2026-11-21

Published a8977021a2380b1648ee9c5718c2694a083af590 on canonical
waqasraza123/hvacline main from c84d3022c31450fca0069a0f152d9e0a325d7847
through an expected-head non-force Git-data update; remote ref readback matches.
Exactly60 scoped files (17 new) match prepared blob identities; unrelated remote
source/historical notes and local branch/index/divergent history are preserved.
README includes the multilingual demo link and en/es/fr/ar/hi/zh, conditional ur,
channel/setup limits and UNVERIFIED status. Existing tags remain unchanged.

Commit retains [skip ci] [skip render]. No tests/builds/linters/formatters/type
checks/services/simulators/migrations/providers/paid AI/calls/deployment commands
ran. Migration0028 remains unapplied; hosted agents, credentials and activation
flags remain unchanged. Runtime/security/provider/native/visual/language quality
acceptance is UNVERIFIED. Exact owner commands/manual scenarios:
docs/multilingual-voice.md. Publication is complete; owner setup and acceptance
remain separate. Do not reset or blindly push the older local main.

## Multilingual publication authorized — UNVERIFIED — 2026-11-21

Owner requests push to main and README multilingual/language coverage. README now
links the fictional demo and lists en/es/fr/ar/hi/zh, conditional ur, verified
browser/mobile setup requirements and unsupported additional phone/recovery
languages. Publication is scoped to the multilingual manifest plus README and
notes, using canonical remote main as parent while preserving unrelated work
and divergent local history. Retain [skip ci] [skip render]. No execution checks,
schema/provider/activation changes or deployment commands are authorized by this
publication request. Migration0028 remains unapplied and runtime UNVERIFIED.
Publication result is recorded separately.

## Multilingual AI Voice — source implemented, UNVERIFIED — 2026-11-21

Added a central agency/channel language registry with separate saved intent and
server-only owner capability evidence. Forward migration20261121_0028 after0027
adds only agency_receptionist_settings.voice_languages JSONB; UNAPPLIED. Existing
profile ownership/version triggers and administrator-token checks protect writes.
Customer web/native proxies permit authenticated configuration reads only.

Browser/native use shared customer-core language contracts, initial overrides,
strict localized readback/affirmative gates and native provider result handling.
English remains the existing effective default without additional evidence.
Additional en/es/fr/ar/hi/zh and conditional ur require exact agency/agent/channel
evidence; runtime source reads hosted languages/presets/detection/events before
additional-language grants. No hosted agent writes or alternate speech engine.
Native system-tool requests and interruptions invalidate pending readbacks;
complete successful authorized results alone establish observed active language.
Drafts, saved requests, original sessions, held slots and uncertain retry payloads
are preserved. Server switch/fluency metrics remain explicitly unavailable.

Operations Receptionist contains Languages & Voice settings, compatibility/setup
states and existing session/appointment outcome diagnostics without customer text.
Homepage preview and /multilingual-ai-voice use the dashboard shell with a purely
fictional interactive text simulation. Phone/recovery additional languages remain
unsupported by their existing consent/finalization/preflight contracts. Recovery
also rejects non-English primary language; no contact-language inference or
outbound activation is added. Production identity/onboarding gates remain.

Added unexecuted regression source and docs/multilingual-voice.md with the exact
source manifest, provider setup/evidence schema, owner commands and fictional
acceptance checklist. No tests/builds/linters/formatters/type checks/browser checks,
services/simulators/migrations/provider requests/paid AI/calls/deployments/commits/
pushes ran. Public provider documentation and pinned SDK declarations were read;
no dependencies/lockfile or credentials changed by this task. All runtime, security,
language quality, provider, native and visual acceptance is **UNVERIFIED**.
Preserve unrelated working changes, index and divergent local/remote history.

## Broader homepage positioning published — runtime UNVERIFIED — 2026-11-20

Published c84d3022c31450fca0069a0f152d9e0a325d7847 on canonical main from
98c1c8efcc2f2583ef2a33f046c91514da193098 via expected-head non-force Git-data
update; remote ref readback matches. Eight scoped copy/test/docs files; unrelated
remote source/memory and divergent local branch/index/history preserved. Commit
retains [skip ci] [skip render]. Existing tags unchanged. No tests/builds/linters/
type checks/services/browser acceptance or deployment commands ran. Runtime and
visual acceptance remain UNVERIFIED. Owner command: `npm run verify:web`;
manual copy/layout/theme/CTA/metadata checks: docs/homepage-copy.md.

## Broader homepage positioning — source UNVERIFIED — 2026-11-20

Owner selects business owners and homepage-wide messaging while retaining
HVACLine. Hero now reads “AI voice agents, built around your business.” and
describes customizable voice/knowledge/workflows. Card and phone section label
the HVAC example; closing CTA/footer/launcher/default and Open Graph metadata
align with the broader positioning. All primary actions retain Try Voice Chat
at /book; existing layout and behavior remain. Geographic/language coverage,
industry implementations, self-service and backend booking/safety gates do not
expand. README/mobile branding remain outside this slice.

Updated existing headline expectations and current homepage copy/hero guides.
No tests/builds/linters/type checks/services/browser checks/publication/deployment
ran. Runtime/visual acceptance remains UNVERIFIED. Owner command:
`npm run verify:web`; exact manual checks: docs/homepage-copy.md. Preserve
unrelated local/remote source and divergent history. Latest published main/tag
remain the Expo publication recorded below; this copy change is local only.

## Expo mobile app and React Native branding published — UNVERIFIED — 2026-11-20

Published98c1c8efcc2f2583ef2a33f046c91514da193098 on canonical main from
fa59bac8fe671c7ff70880e0e491dab6e8d055cc through expected-head non-force
Git-data update; remote readback matches. Exactly57 scoped files (40 new) include
Expo app/core/web adapters/gateway/config/lockfile/docs, README React Native/Expo
badges/mobile Preview and official SVG logo. Prepared blob identities match;
unrelated remote files/memory and divergent local source/index/history preserved.
Annotated v0.1.0-beta.2 resolves to that commit; existing beta.1 remains595994f.
Commit retains [skip ci] [skip render]. No tests/builds/linters/type checks,
services/simulators/migrations/providers/deployment commands ran. Runtime/native/
security/visual acceptance remains UNVERIFIED. Owner setup/commands/manual checks:
docs/mobile-app.md and docs/repository-presentation.md. Publication alone does not
activate the disabled mobile gateway or create an app-store binary/release.

## Expo mobile publication authorized — UNVERIFIED — 2026-11-20

Owner requests publishing the Expo customer app to main, updating README and
adding a tag/React Native logo. README adds the official SVG logo, React Native/
Expo badges and a customer-app Preview feature. Intended new tag is
v0.1.0-beta.2; existing beta.1 remains pinned. Publication uses the current remote
main as parent and preserves unrelated local/remote source and divergent history.
Commit retains [skip ci] [skip render]; no execution checks/deployment authorized.
App/native/provider/security/visual acceptance remains UNVERIFIED. Owner setup,
exact checks and device acceptance: docs/mobile-app.md; README/logo/tag manual
review: docs/repository-presentation.md. Publication result is recorded separately.

## Expo customer app — source implemented, UNVERIFIED — 2026-11-20

Owner requests an Expo mobile app using the latest stable stack. Added apps/mobile
with Expo58.0.26, React Native0.88.1, Expo-supported React19.3.0, Router58.0.32
and TypeScript6.0.3. Native customer screens cover signup/login, mandatory MFA/
recovery, voice/silent Chat booking, appointments/details and explicit rescheduling.
SecureStore holds origin-bound expiring sessions and account/appointment-scoped
reschedule retry references. Disclosure, microphone consent, backend ownership,
readback confirmation, scheduling/provider guards and development gates remain.

Extracted the existing portable booking controller/contracts/transcript/text/
appointment helpers into packages/customer-core; web modules retain adapters.
Disabled-by-default Next.js /api/mobile allowlist injects the existing portal key
server-side and forwards scoped native bearers, without browser cookie reuse or
admin routes. Native ElevenLabs1.2.42 uses its supported LiveKit2.12/WebRTC144
peers; silent Chat uses documented text-only WebSocket events. Persistent customer
memory and process-restored active conversations/intake retries are outside this
version. Production identity/onboarding remains incomplete.

Resolved the workspace lockfile with scripts disabled and applied source
formatting only. Resolver Node26 emitted warnings against retained Node24.x
requirements. No dependency installation, tests, builds, linters, type checks,
simulators, services, migrations, provider calls, hosted changes, publication or
deployment. Added unexecuted gateway/contracts/text/reschedule regressions.
Runtime/security/provider/native/visual behavior remains UNVERIFIED. Exact setup,
owner commands and iOS/Android acceptance: docs/mobile-app.md. No mobile/server
secret or activation setting was changed; preserve unrelated source/history/index.

## Compact recovery homepage and dedicated route — published, runtime UNVERIFIED — 2026-11-20

Published fa59bac8fe671c7ff70880e0e491dab6e8d055cc on canonical main from
c21ced66079c76a2d25ac64d46ed7d130034961e via expected-head non-force update;
remote ref readback matches. Eleven scoped paths (one new route); unrelated
remote files and divergent local branch/index/history preserved. Commit retains
[skip ci] [skip render]. No checks or deployment commands ran.

Owner requests a shorter Lead Recovery homepage section, prominent dashboard
access, README refresh and publication to main; final CTA text is Try Yourself
and destination is /ai-lead-recovery. Homepage now renders a static compact card
without the recovery demo/reducer/metrics/setup controls. The dedicated route
retains the dashboard shell, fictional demo and existing protected setup gate;
legacy /lead-recovery permanently redirects, preserving setup=1. Header/mobile
navigation and demo overview link to the new route. Connected overview retains
its in-place authenticated action. README remains product-only, adds dashboard/
recovery links and a preview bullet, and updates GHL calendar/summary wording.

No backend/schema/provider/dependency/configuration change. No tests, builds,
linters, formatters, type checks, browser checks or services ran. Runtime and
visual acceptance remain UNVERIFIED. Owner command: npm run verify:web;
manual homepage/link/redirect/setup/dashboard/demo/mobile/theme/README checks:
docs/ai-lead-recovery.md, docs/operations-dashboard.md and
docs/repository-presentation.md. Existing unrelated source/index/history preserved.

## Configured Neon upgraded through recovery 0027 — 2026-11-20

Owner explicitly requested applying the migration. The configured direct Neon
development target matches the runtime database and is distinct from the test
target. Initial sole revision was 20261120_0026; Alembic upgraded explicitly to
20261120_0027 successfully. Narrow readback confirms sole revision 0027, both
new tables, five attempt columns, four indexes, three triggers and two new guard
functions. Zero recovery policies are enabled; server/channel/compliance flags
remain off. Do not rerun this completed migration on this target.

Only migration preflight, the requested upgrade and necessary schema/policy
readback ran. No customer records were read, secrets changed, tests/builds/lints/
type checks/services/providers/deployments/publication performed. Application,
provider, security and visual acceptance remain UNVERIFIED. Next: compatible
deployment, provider provisioning and separately authorized acceptance using
docs/ai-lead-recovery.md. Other database targets need deliberate selection.

## Recovery delivery published — 2026-11-20

Owner-authorized publication c21ced66079c76a2d25ac64d46ed7d130034961e extends canonical main from 0314b3db5f2f3a9a6ca5865c07e6912884350834. Expected-head non-force Git-data update and remote ref readback confirm publication of43 recovery-scoped files (18 new); unrelated remote files and local branch/index/history were preserved. Commit retains [skip ci] [skip render]. No execution checks, migration0027, provider actions or deployment commands ran. All outbound flags remain off; runtime/provider/security/visual acceptance is UNVERIFIED. Setup and owner commands: docs/ai-lead-recovery.md.

## Recovery delivery and attributed continuation — source UNVERIFIED — 2026-11-20

The recovery runtime now selects a configured, agency-bound Twilio Programmable Messaging adapter or a separate ElevenLabs SIP recovery agent. New migration20261120_0027 adds durable provider ingress, scoped booking grants, dispatch snapshots, receipt/expiry indexes and guards for owned scope, approved selection, immutable references and reply transitions. It follows the previously owner-applied0026 and has NOT been applied. All delivery/automation flags remain off; no hosted agent, provider or local secret configuration was changed.

Signed callbacks feed the existing booking-job runner; YES requests one short-lived SMS booking continuation, STOP suppresses all recovery channels, and ambiguous replies/staff pauses block automatic continuation. Voice tools require static secret headers, a per-call capability, provider conversation binding and actual transcript confirmation. Provider POST outcomes are checkpointed before I/O; unknown outcomes permit authoritative reads, never blind resend. Existing SchedulingService handles availability, reservation/release, exact selection confirmation and notifications/Google/GHL. Durable approved selection supplies attribution; independent bookings stop recovery without credit. Custom text-model settings still support staff drafts, while live voice uses the dedicated hosted agent's model.

Added /recover with fragment exchange and a scoped HttpOnly cookie, sanitized administrator continuation history and read-only outcome reconciliation, provider setup artifact, focused regression source and runbook. Existing public demo/header/sidebar/spotlight remain separate and unchanged by this follow-up. No tests, builds, linters, formatters, type checks, new migrations, services, live provider requests, calls/messages, deployments, commits or pushes ran. Runtime, security, provider compatibility and visual acceptance remain **UNVERIFIED**; production identity/onboarding remains blocked by the existing development gates. Exact files, disabled configuration, external prerequisites, owner commands and fictional acceptance checklist: docs/ai-lead-recovery.md.

# Project State

## Configured Neon upgraded through recovery0026 — 2026-11-20

Owner explicitly requested migrations. Selected the existing configured direct
Neon development database; its pooled/direct URLs match the same branch/database
and the disposable test target is distinct. Initial revision0025; applied
20261118_0025 →20261120_0026 successfully. Narrow readback confirms sole0026,
six recovery tables, seven triggers, three guard functions and zero enabled
recovery policies. No historical recovery candidates or customer data were read
for acceptance. Do not rerun the completed migration on this target.

Generated a dedicated Fernet key in ignored local.env without displaying it;
kept RECOVERY_ENABLED=false and RECOVERY_AI_ALLOWED_ORIGINS=[]. Reuse that same
key privately on the API and existing job runner; no hosted configuration changed.
No key values, database credentials or account identifiers belong in notes.

Only the requested migration and necessary revision/schema/configuration readback
ran. No tests/builds/linters/type checks/services/provider requests/calls/messages,
new publication or deployment. Application/runtime/visual acceptance remains
UNVERIFIED. Other targets require deliberate migration selection; provider delivery
remains unavailable and activation blocked. Acceptance: docs/ai-lead-recovery.md.

## AI Lead Recovery — published, runtime UNVERIFIED — 2026-11-20

Published 0314b3db5f2f3a9a6ca5865c07e6912884350834 on canonical main from cc733b4147d95ce87e3088e9e7e501fe1dab2857
via expected-head non-force update; remote readback matches. Exactly 46 scoped
paths; unrelated remote documentation and local source/index/history preserved.
Commit retains [skip ci] [skip render]; no checks or deployment commands ran.

Source adds prospective recovery cases/attempts/policy/explicit permission and
encrypted text-model connections through forward migration 20261120_0026 after 0025.
New persisted confirmed requests and normalized browser/phone terminal events
identify cases without a historical scan; a persisted capture watermark excludes
pre-installation requests arriving through delayed events. Existing booking jobs own scheduling;
existing confirmed-booking notification hooks stop recovery without independent
booking credit. Consent, suppression, versioning, idempotent case actions and
unknown-outcome review remain backend gates. No migration or runtime check ran.

Homepage preview, /lead-recovery, header/sidebar links and overview spotlight
use a client-only 24-record fictional demo. Simulated conversation, explicit slot
confirmation, STOP, reset and fictional estimates stay separate from protected
live records. Administrator model save/test/revoke uses Fernet context binding,
public HTTPS origin allowlisting, validated DNS and pinned TLS destinations.
OpenAI/compatible models support staff-reviewed text drafts only; custom-model
live voice is unsupported. Existing ElevenLabs agents/demo calling are unchanged.

SMS Verify is not general messaging; runtime recovery delivery has no configured
SMS adapter or dedicated voice-agent/tool binding. Both channels are reported
unavailable, automation defaults off and enabling is rejected. Trusted receipt/
reply processing is an internal adapter boundary, not a public unsigned webhook.
Live attributed customer continuation and provider reconciliation need concrete
adapters before activation. Existing development/admin identity gates remain;
this is not a production-readiness or operational recovery claim.

Focused regression sources, schema/ownership expectations and disposable fixture
cleanup are added but unexecuted. No tests/builds/linters/formatters/type checks,
browser checks, services, migrations, provider requests, calls/messages, hosted
changes or deployment ran. Publication is recorded above. No subagents. Existing unrelated source
is preserved. Exact manifest, configuration, owner commands, acceptance and
remaining boundaries: docs/ai-lead-recovery.md.


## Clock-based automatic day/night theme — published, runtime UNVERIFIED — 2026-11-20

Publishedcc733b4147d95ce87e3088e9e7e501fe1dab2857 on canonical main from9bc5b12
via expected-head non-force update; remote readback matches. Eight scoped paths
add local-clock light07:00–19:00/dark overnight, shared root minute/focus/visibility
refresh and temporary manual choices expiring at the next local boundary.
Legacy permanent preferences return to automatic; regression sources unexecuted.
No backend/schema/dependency change. Unrelated source/history/index preserved;
retained [skip ci] [skip render]. No tests/builds/linters/type checks/services,
browser acceptance or deployment ran. Runtime UNVERIFIED. Owner commands:
`npm run test:web -- src/components/theme-preference.test.ts`, then
`npm run verify:web`; manual checks: docs/homepage-branding.md.

## Shared route loader and navigation — published, runtime UNVERIFIED — 2026-11-20

Published9bc5b12457ff6abc4b8f9b8324d0fcfa4615ebf3 to canonical main from7b6a42f
through an expected-head non-force update; remote readback matches. Eleven scoped
paths add the centered, themed LoadingScreen to root/Pricing/Billing/published-site
fallbacks, remove Calling from desktop/mobile navigation and document acceptance.
Existing Brand and inline spinners remain; no backend/schema/dependency change.
Unrelated divergent source/history preserved; retained [skip ci] [skip render].
No tests/builds/linters/type checks/services/browser acceptance or deployment ran.
Runtime UNVERIFIED. Owner command: `npm run verify:web`; manual checks:
docs/loading-screens.md. Owner manages deployment and validation.

## Public browser origin configuration — 2026-11-18

Source CORS permits only settings.web_origin; WEB_ORIGIN is a single exact
origin also used by OAuth/WebSocket guards. Owner browser log uses the www
public origin and reports demo GET200 blocked for a missing CORS header. Hosted
value is uninspected. Environment handoff now shows https://www.hvacline.online;
public-demo guide documents Render Save and deploy plus deferred header/browser
acceptance. No runtime change, hosted configuration or verification ran. Owner
reports demo token and location already set in Render; no re-entry requested.

## Public live GHL demo published — activation pending — 2026-11-18

Owner authorizes publishing/deploying the read-only public pipeline view,
configuring hosted server-only GHL_DEMO_* settings and performing focused mock
checks plus live read-only acceptance. Dedicated sub-account is fictional-only.
Python test_ghl_demo/test_ghl_routes/test_ghl:37 passed; frontend demo-contracts:
6 passed. No database tests, broad verification, local services or migrations ran.

Source adds the public aggregate API, strict enabled-config validation, bounded
cached GET-only provider reads, credential-free UI and honest empty/error/previous
snapshot states. The live card precedes the static workflow preview. No package
or schema change. Hosted endpoint currently404; local private demo token absent,
activation off. Hosting connections/private credential setup remain pending;
no GHL reads/writes or deployment completed yet. Published14 scoped paths as
7b6a42f on canonical main fromf81299f via expected-head non-force ref update;
remote readback matches. [skip ci] [skip render] retained pending hosted access.
Next: finish authorized hosted configuration/deployment and read-only acceptance
once private token and Render/Vercel access are supplied. Setup guide:
docs/gohighlevel-public-demo.md. No secret values or account IDs retained.

## Prominent GoHighLevel dashboard feature — source UNVERIFIED — 2026-11-18

Overview leads with a GHL feature card covering CRM sync, calendar booking and
contact summaries. Named GoHighLevel sidebar entry/CRM badge and direct actions
reuse the existing integrations section. Demo connect flow retains that target
through administrator authentication. Demo overview adds no requests; connected
overview reads existing protected saved connection status, not live provider
health. No backend, schema, provider, permission or dependency changes.
Source formatting only; no checks/services/provider calls/publication/deployment.
Owner command: `npm run verify:web`; exact UI/status/auth/demo/mobile/theme
acceptance in docs/operations-dashboard.md. Implementation remains UNVERIFIED.
Publishedf81299f to canonical main froma6b9a47 without force. Eight scoped paths
include the static public workflow preview; unpublished live-demo dependencies
and unrelated source remain separate. [skip ci] [skip render] retained; no checks
or deployment ran during publication.

## Navbar active dot — source UNVERIFIED — 2026-11-18

Shared desktop/mobile top navigation initially marks Dashboard with a green dot
and short pulse. Client navigation moves the dot and active styling to the chosen
item; browser/hash history updates the selection. Reduced motion disables the
pulse while retaining the dot. No verification, services or publication ran.
Owner command: `npm run verify:web`; fresh-load/click/mobile/keyboard/history,
theme and reduced-motion acceptance: docs/operations-dashboard.md.
Publisheda6b9a47 to canonical main fromcc24fc5 without force; retained
[skip ci] [skip render]. No verification or deployment ran during publication.

## Configured development database upgraded through0025 — 2026-11-18

Owner explicitly requests applying the published GHL voice migration. Selected
the existing configured direct development migration database, excluding the
disposable test target. Initial revision0024; applied0024 →20261118_0025
successfully. Readback confirms sole revision0025, new connection/delivery
columns, ghl_calendar_bookings and its business/connection/appointment foreign
keys. No customer rows were queried for acceptance.

Only the requested migration and narrow revision/schema readback ran. No tests,
builds, lints, type checks, seeds, services, provider actions, hosted configuration,
calls, deployments or new publication. Runtime/visual acceptance remains
UNVERIFIED. Do not rerun the migration after this completed handoff. Next:
deploy the compatible source, configure GHL scopes/calendar routes/note author
and separately authorize acceptance using docs/gohighlevel-voice-demo.md.

## GHL voice priorities — published source UNVERIFIED — 2026-11-18

Owner selects only the first three priorities: direct GHL calendar booking,
contact-level request summaries and an inbound fictional-business demo flow.
Optional team/calendar routes reuse existing scheduling and phone/browser tools.
Mapped teams intersect local rules/capacity with GHL availability; confirmation
creates and verifies a GHL event before local CONFIRMED. Durable attempt state,
original-destination bindings and explicit owner recovery guard uncertain writes.
Unresolved attempts retain capacity after ordinary hold expiry. Existing routes
remain the default; Google/GHL routing cannot overlap on a team.

Optional contact notes use confirmed persisted lead data and the current notes
API, one note per request, with independent unknown-create recovery. Existing
notes/identities are preserved. Administrator UI adds mapping, note setup and
booking history/recovery; customer booking failures preserve staff-review state.
Migration20261118_0025 follows0024 and must precede backend deployment; applied
to the configured development database on2026-11-18 as recorded above.
GHL cancellation/rescheduling, continuous external-edit reconciliation, emergency
live transfer, lead reactivation and agency onboarding remain outside this slice.

Inbound demo uses the existing authenticated eight-tool phone flow plus documented
emergency/routine prompt additions. No number/agent/provider was configured or
activated, no call made, and no migration or deployment performed. Source
formatting only; all regression sources and runtime/visual behavior UNVERIFIED.
Owner setup, exact deferred commands and manual acceptance:
docs/gohighlevel-voice-demo.md. Existing execution stop and unrelated work preserved.
Publishedcc24fc5 to canonical main from901fdf5 via expected-head non-force update;
30 scoped paths, [skip ci] [skip render]. No checks/migrations/deployment ran.

## Public Dashboard navigation — source UNVERIFIED — 2026-11-17

Shared desktop/mobile navigation labels the existing `/operations` link
Dashboard, with demo wording in the mobile menu. All visitors can open the
existing sample-data dashboard without sign-in; live workspace access retains
the admin-token gate. No authentication/backend change is required.
Owner requests commit/push to main. No checks or services ran. Owner command:
`npm run verify:web`; manually open Dashboard signed out and signed in from
desktop/mobile navigation and confirm live workspace access remains protected.
Published901fdf5 to canonical main via non-force ref update; retained
[skip ci] [skip render]. Unrelated divergent source preserved; no deployment ran.

## Public read-only GHL demo — source UNVERIFIED — 2026-11-16

Owner requests environment configuration and public proof of GHL reads, and
confirms the selected sub-account contains only fictional demo records. Added
server-only GHL_DEMO_ENABLED/FICTIONAL_DATA_ONLY/LOCATION_ID/PRIVATE_INTEGRATION_TOKEN
settings and a public GET-only aggregate endpoint. Existing managed CRM delivery
and administrator authentication remain separate; no tenant/token bootstrap or
provider writes are introduced. No dependency or database migration is required.

Operations demo → Integrations now shows live-read timestamps, pipeline/stage
counts for up to100 latest opportunities and explicit disabled/empty/error/previous
snapshot states. Public projection excludes contact details, opportunity titles,
custom fields, values and all provider IDs. Fixed location/origin, v3 read-only
scope, bounded responses/deadlines and one-minute per-process cache/cooldown
protect provider access. Unknown/foreign/duplicate data fails closed.

Local gitignored .env now has the supplied location and blank private-token field;
activation remains off pending secure owner token entry. Never retain credential
or account identifiers in notes. Hosted environment/deployment remains separate.
No live GHL pull, tests/builds/linters/type checks/formatters/services/migrations,
publication or deployment ran. Source/runtime/visual acceptance UNVERIFIED.
Focused mock regression sources added, unexecuted. Exact owner commands and
manual checks: docs/gohighlevel-public-demo.md. Existing unrelated work preserved.

## Short product-only README — 2026-11-14

Owner requests a very short, feature-focused README without development or
deployment information. README now contains the existing banner, short product
introduction, website/license links, ten concise feature bullets and a brief
written-permission notice. Setup, architecture, status reports, CI/release/star
badges and the documentation directory are removed from README. Preview labels
remain for websites/GHL; Stripe stays explicitly sandbox. LICENSE is unchanged.
Repository-presentation handoff reflects the new layout and owner manual checks.
Published three scoped files as2af28ff on canonical main via non-force update;
retained [skip ci] [skip render]. Unrelated divergent source remains preserved.

No tests/builds/linters/type checks/formatters/services/browser rendering or
deployment ran. Rendering remains UNVERIFIED. No automated command is needed for
this text-only edit. Owner manual check: open GitHub README at desktop/mobile
widths; inspect banner, feature text, website/license links, and absence of
setup/development/deployment sections. Other source work and release preserved.

## GitHub presentation and proprietary licensing — 2026-11-14

Owner requests polished GitHub presentation and no usage without prior written
permission. Root LICENSE reserves first-party rights for all uses, with GitHub
platform/lawful-rights exceptions and preserved third-party licenses/prior grants.
No legal entity, assignment, fee or software paywall is invented. npm declares
UNLICENSED; Python declares LicenseRef-Proprietary and includes LICENSE.

Repository About now describes the product and permission requirement; twenty
relevant topics retain earlier tags. Existing website link is preserved. Private
vulnerability reporting is enabled. README adds original SVG banner, real CI/star
badges, existing beta link, capabilities and documentation. Community files add
issue forms, PR template, contributor/security guidance and release-note categories.
Existing v0.1.0-beta.1 remains at its original commit; no new release is created.

Published17 scoped repository/licensing files as3392a75 on canonical main,
preserving unrelated divergent local work through an expected-head non-force
ref update. Retained [skip ci] [skip render]. No tests, builds,
linters, type checks, formatters, migrations, services, provider actions or
deployment commands ran. GitHub rendering, packaging and application runtime
remain UNVERIFIED. Exact deferred commands/manual checks:
docs/repository-presentation.md. Application code/dependency versions are unchanged.

## Configured Neon upgraded through GHL0024 — 2026-11-13

Owner explicitly requests applying the migration, authorizing the configured
Neon migration and necessary revision/schema readback. Loaded existing direct
migration settings with APP_ENVIRONMENT=development; test URL was not selected.
Initial revision0021 required prerequisites0022 (website foundation) and0023
(immutable publications). Applied0021 →0022 →0023 →0024 successfully. Readback
confirms sole revision20261113_0024, both GHL tables and all five enabled capture
triggers. No migration rerun is needed after the interrupted/resumed handoff.

No tests/builds/lints/type checks/seeds/services/provider actions, feature flag
changes, deployment or publication ran for this operation. No customer rows were
read for acceptance. The schema is applied; application/GHL runtime remains
unverified. Next: configure API/jobs key/flags and test sub-account, then separately
authorize controlled acceptance using docs/gohighlevel.md. Checks remain stopped.

## GHL hero and all-work publication authorized — 2026-11-13

Owner requests GoHighLevel in the hero, commit/push of all pending work to main,
and the next step/integration. Hero adds CRM sync · Preview using existing
responsive badge styles; current source remains runtime-unverified. Publication
is authorized without tests/builds/checks or deployment. Preserve original local
history/edits, publish from canonical main without force, disable hooks and retain
[skip ci] [skip render]. Compare all pending source paths before publication.

Owner next: reviewed0024 migration, API/job flags/key, client-owned test GHL
sub-account and controlled acceptance. Then implement separate n8n event delivery
with authenticated/signed events, receiver deduplication and visible retry/replay;
that follow-up is documented, not implemented. Exact commands/manual checks and
next slice: docs/gohighlevel.md; hero checks: docs/homepage-hero.md.

## GoHighLevel integration — source implemented, UNVERIFIED — 2026-11-13

Owner selects private-token GHL integration first: contact matching/creation,
separate opportunity per confirmed lead and booking/handoff stage synchronization.
Connected Operations → Integrations adds setup, mappings, health/history,
pause/resume, token replacement, disconnect and guarded recovery. Existing
HVACLine scheduling remains authoritative; OAuth/GHL booking/two-way sync,
workflow enrollment and messaging are outside this slice. Public demos stay off.

New backend ghl module and migration20261113_0024 add encrypted business-bound
credentials, composite ownership constraints, transactional capture and versioned
outbox delivery through existing bounded jobs. Only new confirmed leads enroll;
no historical backfill. Partial completion/creation uncertainty survives retries;
ambiguous creation requires reconciliation or deliberate owner review. Closed or
externally moved opportunities are protected. Production identity remains gated.
GHL_ENABLED defaults false; API/jobs require GHL_TOKEN_ENCRYPTION_KEY when enabled.

Owner explicitly keeps execution stopped. Source formatting only was applied;
no tests/builds/lints/type checks/migrations/services/live GHL operations,
publication or deployment ran. Runtime remains unverified. Regression source
covers API authorization, identity conflicts, repeat requests, lost responses,
booking/handoff/reschedule states, concurrent coordinators, token/rate failures,
transactional rollback and business isolation. Exact owner commands, setup,
limitations and manual acceptance: docs/gohighlevel.md. Preserve unrelated work.

## Public Voice AI showcase disabled — implementation UNVERIFIED — 2026-11-13

Owner requests removal of Explore Voice AI Demos and publication to main.
Homepage gallery, hero link, shared desktop/mobile navigation entry, gallery-only
component/styles and demo utility pages are removed. `/demos/[slug]` now always
returns not-found. Dashboard and published-site utility links no longer point
to the removed collection; published-site loading/error states are independent. Shared templates/artwork and the
administrator website editor remain available.

No tests/builds/lints/type checks/services or runtime checks ran. Owner command:
`npm run verify:web`. Manual: no showcase/collection links on home/navigation or
published sites; all three former demo URLs return404; booking/calling/pricing,
website editor and published sites still work. Runtime remains unverified.
Publish from canonical main in an isolated checkout, preserve unrelated local
work, disable hooks and retain `[skip ci] [skip render]`. No deployment requested.

## Final builder publication authorized — 2026-11-13

Owner explicitly requests push to main after the coding-only handoff, authorizing
commit/publication while keeping tests/builds/checks stopped. Prepared from
canonical `a109bbf` in `/private/tmp/hvacline-final-publish-20261113`.
All253 pending source paths were compared:131 already match main,122 contain
the final builder, homepage removals, stabilization and documentation changes.
Original divergent source/history and unrelated work remain preserved. Publish
without force or hooks and retain `[skip ci] [skip render]`. Final source remains
unverified; deployment, target migrations and provider operations remain separate.

## Final local builder/stabilization work — verification stopped — 2026-11-13

Owner authorizes local completion, then explicitly stops tests/builds/checks and
requests a quick coding-only conclusion. No further verification may run without
new specific authorization. No commit/push/deploy, configured database/provider
operation, real call or SMS is authorized for this task.

Source adds structured content/typography/section/action editing, private drafts,
immutable publications/history, atomic publish/rollback/unpublish and share links.
Revision20261113_0023 adds version snapshots/pointers and conversation version
context; migrations ran only on newly created local disposable
hvacline_final_test_20261113. Website tools use the published snapshot; draft
bindings do not affect live sessions. Administrator-token management is mandatory
even outside the optional sandbox gate. Customer sign-in does not confer ownership.

Before the stop, aggregate verify:web passed (256 tests, full web formatting/lint,
TypeScript and production build); focused backend39 passed; full Ruff lint reached
passing. Broader pytest completed596 passed/9 failed; related source/fixture fixes
are unverified. Full mypy reported81 errors; three production typing corrections
were made afterward, while strict test typing remains unresolved. Final changes
have not been rerun. No live browser/provider/visual acceptance was performed.
Documentation is consolidated in website-platform-phase2.md with exact commands,
owner deployment/agent setup and acceptance, without another implementation phase.
Production onboarding remains insufficient; restricted development/test gates stay.

## Homepage section cleanup — source implemented, runtime unverified — 2026-11-13

Owner removes the homepage HVAC-owner FAQ and three-step booking walkthrough.
Root page omits both sections; desktop/mobile navigation drops How it works and
the hero secondary link targets the demo gallery. Packages remain only on the
separate `/pricing` page; their homepage block was already removed in `a109bbf`.
No tests/builds/services or deployment ran for this follow-up. Owner checks:
`npm run verify:web`; manually confirm absent sections, gallery links and mobile
navigation on the homepage, and packages on `/pricing`. This source change is
unverified. The prior publication retained `[skip render]`; it did not request a
deployment, and the hosted page has not been inspected.

## Phase 2 publication authorized — 2026-11-13

Owner explicitly requests push to main, authorizing the Phase 2 and homepage
commit/publication. Prepared from canonical main `ac0c860` in isolated checkout
`/private/tmp/hvacline-phase2-publish-20261113`; original divergent source and
unrelated work remain intact. Compared all175 pending paths:87 already match
canonical main,88 contain current changes. Hooks remain disabled and publication
retains `[skip ci] [skip render]`. No deployment, configured database migration,
provider/settings operation or live call is authorized by this publication.
Existing local test results and live-acceptance limits are recorded below.

## Configurable websites — local checks passed, live acceptance pending — 2026-11-13

Phase 2 source adds agency-owned `websites` and private `website_agent_bindings`,
validated content, optimistic owner updates and dynamic `/sites/[slug]` rendering
through the three existing templates. Static `/demos/...` remains independent.
The connected dashboard has a structured website editor and safe draft preview.
Migration `20261112_0022` follows `20261109_0021`; schema must precede backend
deployment because conversation ORM queries include the new nullable context.

Backend-resolved bindings reuse existing signed ElevenLabs grants, consent/MFA,
session ownership and agency quotas. Composite agency foreign keys and tool
guards bind conversations to sites/agents. Selected active FAQs are scoped to the
site; generic inquiries require explicit confirmation and reuse transactional
lead persistence. Website booking and account-memory access are denied, including
legacy routes. Missing agents never fall back to HVAC. The platform defaults off
and remains development/test gated; production identity/customer realms, provider
provisioning and dedicated credential isolation are still incomplete.

Owner-authorized local results: 256 web tests/38 files, TypeScript and production
Next build passed; website/navigation scoped ESLint passed. The listed backend
suite passed all102 tests, including actual concurrent edits and existing HVAC
booking/memory; new backend Ruff/mypy passed. Migration round trips ran only in
new disposable local `hvacline_websites_test_20261112`. Process-local optional
flags and UTC database connections isolate legacy fixtures from local defaults.
`npm run verify:web` remains failed at15 preexisting formatting paths. Separate
full lint reports11 older errors/three warnings; those unrelated files were
preserved. No visual or live-provider acceptance is established by these checks.

Homepage changes remove compact pricing, Services and footer My package; retain
`/pricing`, booking/calling and gallery. Shared header/footer provider logos have
short captions; desktop pill navigation and a mobile drawer are implemented.
No configured Neon migration, agent registration, hosted change, live session,
real call, service startup, commit, push or deployment was performed. A separate
non-HVAC agent/binding and authorized live browser test are required before the
Phase 2 end-to-end completion criterion can be claimed. Exact setup, changed
source, results, commands/manual checks and Phase 3 slice:
[website-platform-phase2.md](website-platform-phase2.md).

## Multi-product website publication authorized — runtime UNVERIFIED — 2026-11-12

Owner explicitly requests push to main, authorizing commit/publication of the
completed Phase1 feature. This supersedes the preceding task's coding-only
publication restriction; tests/builds/lints/type checks/services remain stopped.
Publish from current canonical main using an isolated checkout, preserve original
divergent edits and canonical history, disable hooks and retain [skip ci]
[skip render]. No deployment, migration or provider/data operation is requested.
Runtime/visual acceptance remains unverified; owner checks and Phase2/3 plans
are in docs/multi-product-websites.md.

## Multi-product website foundation — source implemented, UNVERIFIED — 2026-11-12

Owner authorizes Phase1 coding only, superseding prior publication authorization
for this new task. Existing homepage/functional CTAs are preserved; a gallery
adds /demos/hvac, /demos/real-estate and /demos/appointments. Three distinct
industrial/editorial/calm layouts share validated template/website contracts,
scoped primitives, local original SVG artwork and an async configuration-source
boundary. Server-only agent bindings separate presentation from provider/business
configuration; no provider IDs/secrets are placed in website content. Fictional
real estate/studio sites are written previews only. HVAC links into the existing
authenticated account flow; backend availability remains authoritative.

No new API/dependency/database schema/editor/publishing service. Existing backend
still uses development membership/business resolution and one server-configured
browser provider; this is not production multi-tenancy. Focused test source is
added but unexecuted. No tests/builds/lints/type checks/formatters/services/live
provider actions/migrations/commits/pushes/deployments ran. Runtime and visual
acceptance remain unverified. Exact future commands/manual checks and concrete
Phase2/3 dependencies/migrations/slices: docs/multi-product-websites.md.

## TailAdmin operations dashboard demo — implementation UNVERIFIED — 2026-11-12

Owner selects TailAdmin, requests HVACLine colors, demo content, README update
and publication of all pending code to main. `/operations` now defaults to local
fictional sample records; no backend/provider call or microphone access is made
by the demo. Existing admin-token connection switches to stored workspace data.
Demo mutations are disabled and live editors/integrations remain unmounted.
Adapted sidebar/header/cards/tables use scoped CSS Modules, existing Radix Dialog
and existing light/dark preference; TailAdmin MIT notice is retained. Overview
counts explicitly describe capped loaded queues, not business-wide analytics.
No API/schema/dependency/environment change. README and
docs/operations-dashboard.md contain exact deferred commands/manual checks.

No tests, builds, lint/type checks, formatters, services or runtime checks ran.
Implementation/runtime remain unverified. Preserve original divergent source and
pending edits; publish from current canonical main with hooks disabled and
[skip ci] [skip render]. No deployment or provider/data operation is requested.

## Persistent memory and full-width website publication — 2026-11-10

Owner authorizes committing/pushing all pending changes to main. Compared all86
changed/untracked paths against canonical e5cf2c2; previously published changes
already match, leaving19 publication files. Includes persistent-memory startup/
retry/consent/evidence fixes and specifications, prepared ElevenLabs tools/prompt,
Preview hero badge and full-width shared website/pricing containers. Existing
published source/history and original divergent checkout edits are preserved.

Publish from /private/tmp/hvacline-memory-publish-20261110 with hooks disabled
and [skip ci] [skip render]. The latest owner instruction keeps tests/builds/lints
and other execution checks stopped. No new migration, environment/provider/data
operation or deployment. Final source/runtime and hosted memory/Neon/device/
retention scheduling acceptance remain unverified. Existing release/tag remains
unchanged. Future owner commands/manual checks: docs/customer-memory.md and
docs/homepage-branding.md. Publication outcome is recorded in local session notes.

## Knowledge base and account header publication authorized — 2026-11-09

Owner requests commit and push to main. Prepared all remaining source/guide
differences on canonical d2f2d35 from the isolated publication checkout. Includes
knowledge-base alternate questions/retrieval/editor safeguards, migration0021
and specifications, corrected starter-source content and session-aware account
avatars. Existing approved content is preserved; no reseed or provider upload.
The configured database already reached0021 in the prior authorized operation.

Homepage/pricing headers use currentCustomer with the existing verified session;
authenticated visitors receive a reusable circular initials link to /book.
Billing reuses its resolved customer; booking retains its active-conversation
navigation guard. Anonymous visitors see Sign in, pending lookup a neutral
placeholder, and unavailable lookup My account. Names are not cached in browser
storage. Styling follows existing light/dark tokens, focus and reduced motion.

No verification execution, new database/provider action or deployment accompanies
publication. Hooks disabled; [skip ci] [skip render] retained. Existing release
v0.1.0-beta.1 stays pinned to595994f. Owner checks: npm run verify:web and commands/
manual checks in docs/knowledge-base.md and docs/homepage-branding.md. Application
and visual acceptance remain unverified; no Calendly/HubSpot work is active.

## Theme, hero badges and Voice Chat publication authorized — 2026-11-09

Owner requests pushing all remaining changes to main. Prepared all source/guide
differences on canonical595994f in the isolated publication checkout. Includes
animated customer light/dark switching, theme-aware customer/billing surfaces,
WebRTC/authenticator/Stripe sandbox hero badges and Try Voice Chat as primary
action with Voice as the customer workspace default. Text chat and separate
phone/callback options remain; consent and deliberate connection are required.
Current release remains v0.1.0-beta.1 at595994f; do not move its tag.
No migration/dependency/backend setting change. No tests, builds, lint/type
checks, previews, live sessions, provider/database operations or deployment
commands ran. Hooks disabled and [skip ci] [skip render] retained. Runtime remains
unverified; owner command npm run verify:web and manual checks in
docs/homepage-branding.md, docs/homepage-hero.md and docs/customer-chat.md.

## Remaining header changes publication authorized — UNVERIFIED — 2026-11-09

Owner requests pushing all changes to main. Canonical main6b2bbad already contains
the complete Stripe billing implementation, automatic business resolution,
ElevenLabs wordmark and Twilio header logo; earlier SMS/inbound code and guides
are also published. Comparing the original local changed/untracked files with
main finds only the Stripe Pricing navigation label, header guide and release
notes still unpublished. The label retains /pricing and Twilio stays displayed
beside ElevenLabs, Telnyx and WhatsApp. Original branch/edits remain preserved.
No tests, builds, lint/type checks, services, provider operations or deployment
commands ran for this publication; hooks disabled and skip markers retained.
Owner command/manual acceptance: npm run verify:web, then check pricing link,
provider alignment/accessible names and desktop/tablet/320px header overflow.

## Stripe and SMS publication status — 2026-11-09

Canonical main accepted f858404..6b2bbad for full sandbox billing, automatic
business resolution and ElevenLabs wordmark, without force. Earlier SMS/inbound
publication accepted430c16d..f858404. These publications supersede the historical
local-only billing restriction and unpublished-status notes. Runtime remains
unverified; exact setup/checks: docs/maintenance-billing.md,
docs/homepage-branding.md and docs/sms-capable-demo-numbers.md.

## Stripe billing publication authorized — runtime UNVERIFIED — 2026-11-09

Owner requests pushing the current work and explicitly includes Stripe code.
This supersedes the earlier local-only restriction for billing commit1297b0a.
Prepared from canonical main f858404 in an isolated checkout, including the full
billing feature, automatic business resolution and ElevenLabs text wordmark.
Existing published SMS/inbound changes are retained; unrelated original working
edits and historical notes are preserved. Use disabled Git hooks and existing
[skip ci] [skip render] markers. No verification execution, migration, Stripe
setup/payment or hosted deployment is authorized by this publication.

## Sandbox homeowner maintenance billing — implementation UNVERIFIED — 2026-11-09

One editable catalog defines draft3/5/10-hour monthly technician-maintenance
packages and separate extra-hour rates. Initial payment and paid renewal grant
current-period package hours; purchased extras remain until used. Booking alone
does not consume labor. Signed webhook reconciliation, persistent checkout retries,
unknown-write recovery, customer portal period-end cancellation, refund/dispute
holds and administrator completed-labor entries use existing customer/agency
ownership. One Stripe sandbox account is configured; live keys/events/rows are
rejected. This does not add Stripe Connect or production identity support.

Includes /pricing, /billing, homepage packages, billing auth continuation, shared
loading spinners, Stripe dependency and forward migration20261108_0020. No tests,
builds, lint/type checks, migrations, services, Stripe objects/payments or deployment
commands ran. Runtime/sandbox acceptance and existing customer/privacy launch gates
remain pending. Exact setup, owner commands and manual checks:
docs/maintenance-billing.md. Wordmark checks: docs/homepage-branding.md.

## SMS/inbound publication authorized — runtime UNVERIFIED — 2026-11-08

Owner requests publishing the pending US SMS-capability changes and inbound/setup
investigation documents. The publication is isolated on the existing remote main
revision; unrelated local feature commits are excluded. Carrier line-type gating
is relaxed while provider code verification, MFA, consent, US/carrier identity,
quotas and unknown-call recovery remain. Inbound changes here document earlier
provisioning and setup; no new inbound handler is added. No new migration or
setting is required. No checks, services, provider actions or deployment commands
ran. Owner commands/manual checks: docs/sms-capable-demo-numbers.md and
respective inbound/incident guides. Runtime acceptance remains pending.

## Persistent customer memory completed locally; hosted acceptance pending — 2026-11-10

Existing PostgreSQL account/agency memory tables, consent revisions, APIs,
customer controls, verified WhatsApp identity and ElevenLabs1.12.0 are reused.
Browser Voice/Text now request bounded authorized context after connection,
independently of booking. Save retries preserve confirmed payloads and use
canonical fact/source fingerprints. Clear deletes optional data and disables
retention until fresh opt-in; expired evidence cannot refresh facts. Conservative
evidence handling supports weekday mornings and rejects negative/ambiguous
claims; the final explicit-brand refinement remains unverified.

Evidence collected during implementation:47 backend unit/API/provider checks,
52 disposable PostgreSQL channel/booking/ownership checks and204 web tests
passed; production web build passed. Final11 memory tests include committed
preference retrieval by a fresh Python process, new connections and concurrent
retry/conflict handling. Static hero checks passed320/390/1440px in both themes.
These establish local behavior only. Full verify:web remains blocked by16
existing formatting failures; standalone typecheck has2 existing proxy-test
generic errors and broader migration expectations omit prior FAQ0021 changes.
Node24 validation, hosted agent/Neon/device acceptance and retention scheduling
remain pending. Final source has not been fully revalidated: owner subsequently
stopped tests/builds/lints and requested coding only; that stop is honored.

Hero adds customer-controlled Persistent Memory visibly marked Preview, retaining
heading/Voice CTA/styles. No new migration/environment variable/dependency
declaration or lockfile, and no configured Neon/customer data was changed.
No services, live calls/messages, hosted agent changes, deployments, commits or
pushes. Exact prepared private-browser tools/prompt, changed files, future owner
commands and real end-to-end acceptance: docs/customer-memory.md.

## Knowledge base and account avatars published — runtime UNVERIFIED — 2026-11-09

Published e5cf2c2 to canonical hvacline main; push accepted d2f2d35..e5cf2c2
without force. Twenty-seven files include approved-question variations, retrieval/
editor improvements, migration0021/specifications/guide, corrected starter-source
content and session-aware clickable initials avatars in customer headers. All
pending application/guide differences are included; original branch/working
edits are preserved. Configured database already reached0021 in the prior
authorized operation; no new database action occurred. Hooks disabled and skip
markers retained. Existing prerelease stays pinned to595994f. No tests, builds,
lint/type checks, services, provider actions or deployment commands ran. Deploy
backend/frontend deliberately; owner commands/manual checks remain in
docs/knowledge-base.md and docs/homepage-branding.md. Runtime remains unverified.

## Knowledge base improved; migration0021 applied — 2026-11-09

Owner stops the Calendly/HubSpot investigation and explicitly requests finishing
only the knowledge-base task, applying its migration and then stopping. Existing
agency-owned approved FAQs remain the shared source for browser/guest/phone
tools. Local code adds up to eight validated alternate questions per answer,
conservative ambiguity fallback, source/version preservation and legacy-update
compatibility. Operations adds search/status filters/counts, clearer preview,
loading/retry feedback, unsaved-edit activation guards and version-conflict
recovery. Existing ownership, default-inactive creation and audits remain.
Starter source content is corrected for current optional integrations/billing;
existing approved records are preserved and no seed/content rewrite ran.

Authorized bounded operation applies20261108_0020 →20261109_0021 and confirms
head0021, the non-null JSONB variations column/default and validated shape/count
constraint. Runtime/direct configured targets and roles match. Initial sandbox
connection failed; approved network escalation completed migration/readback.
Regression specifications are written but unexecuted; only source formatting ran.
No tests/builds/lints/type checks, services, provider operations, dependency
installation, commit/push or deployment ran. Code remains local/unpublished and
runtime-unverified. Exact owner commands/manual checks: docs/knowledge-base.md.
Work stops here as requested; no Calendly/HubSpot work is active.

## Theme, hero and Voice Chat published — runtime UNVERIFIED — 2026-11-09

Published d2f2d35 to canonical hvacline main; push accepted595994f..d2f2d35
without force. Twenty-nine files publish animated customer light/dark themes,
theme-aware customer/billing surfaces, hero platform/security/Stripe sandbox
badges and direct Try Voice Chat actions with VOICE as the customer default.
Text chat, consent/start gates and separate callback/phone options remain.
All remaining application/guide differences are included; original branch/edits
are preserved. Existing v0.1.0-beta.1 remains pinned to595994f. Hooks disabled and
skip markers retained. No tests, builds, lint/type checks, services, live sessions,
database/provider operations or deployment commands ran. No new migration or
dependency. Owner command npm run verify:web; manual acceptance in
docs/homepage-branding.md, docs/homepage-hero.md and docs/customer-chat.md.

## Voice chat primary/default — implementation UNVERIFIED — 2026-11-09

Owner requests clear Try Voice Chat hero wording and Voice as default. Local
source makes hero/header/launcher link directly to /book with that wording,
retains the homepage Voice preview and changes the customer workspace's initial
mode from TEXT to VOICE. Voice chat is the first mode choice; Text chat remains
available. AI disclosure/microphone consent remain unchecked and explicit Start
Voice Chat is still required; navigation alone does not connect/request audio.
Callback/inbound phone options remain separate. Text handoff/drafts, active-session
mode locks and existing confirmation gates remain. No backend/provider/config or
migration change. No checks, services, live sessions, commits/push or deployment
ran; implementation is local/unverified. Owner command: npm run verify:web.
Exact manual checks: docs/homepage-hero.md and docs/customer-chat.md.

## Customer light/dark switch — implementation UNVERIFIED — 2026-11-09

Owner requests an animated dark/white switch in the top bar. Local source adds
a reusable accessible sun/moon control to product/customer headers, shared
white/charcoal/orange theme variables, and theme-aware billing/cards/dialogs/
customer panels/loading states. A static root initialization script reads a valid
browser preference before content renders; client subscription synchronizes
controls, system preference changes and storage events. Explicit choices persist
when storage is available; blocked storage retains current-page switching.
Reduced-motion styles disable switch animation. Customer styles stay scoped;
existing charcoal feature panels and the white MFA QR background are preserved.

No dependency/configuration/migration change. Changes remain local/unpublished;
no tests, builds, lint/type checks, previews, services, provider/database operations
or deployment ran. Owner command: npm run verify:web. Exact cross-route,
persistence/system/storage, visual, keyboard/accessibility and reduced-motion
manual checks: docs/homepage-branding.md. Runtime remains unverified.

## First GitHub prerelease published — 2026-11-09

Owner requests a release. Published v0.1.0-beta.1 on canonical hvacline, titled
HVACLine v0.1.0-beta.1 — Stripe billing and maintenance packages. Release/tag
readback confirms published (not draft), prerelease=true and exact source
595994f57feb9e01c9ecc0795f8b694012fcc41d. Created with latest=false and no binary
assets. Release notes cover current app/billing/header features, configured0020
confirmation, sandbox-only limits and pending setup/runtime acceptance. No tests,
builds, lint/type checks, new database/provider operations, services or deployment
commands ran. URL:
https://github.com/waqasraza123/hvacline/releases/tag/v0.1.0-beta.1

## All remaining changes published — runtime UNVERIFIED — 2026-11-09

Published595994f to canonical hvacline main; push accepted6b2bbad..595994f
without force. Publishes Stripe Pricing navigation label, header guide and
verified0020/release-status notes. Twilio remains in the header. All other local
application changes already matched main, including Stripe billing, automatic
business resolution, ElevenLabs wordmark and prior SMS/inbound work. Original
branch/working edits are preserved; isolated publication source is committed.
Hooks disabled and skip markers retained. No tests, builds, lint/type checks,
new database/provider operations, services or hosted deployment commands ran.
Owner checks: npm run verify:web and manual header/link/provider/accessibility/
overflow acceptance from docs/homepage-branding.md. Runtime remains unverified.

## Configured database billing schema at0020 — verified — 2026-11-09

Owner authorizes completing pending migrations. Bounded operation using published
6b2bbad migration source and existing owner-confirmed local database configuration
finds20261108_0020 before and after; no upgrade is necessary. Runtime/direct
targets and roles match. Confirms billing_accounts, billing_checkouts,
billing_events, billing_topups and billing_labor exist, plus customer account
ownership uniqueness. Current source head is0020; no pending migration remains
for this configured database. Initial sandbox connection failed; approved network
escalation completed readback. No seed, downgrade, schema/data mutation, customer
row access, tests, service, Stripe operation or deployment ran. Payment/application
runtime and hosted deployment acceptance remain unverified.

## Stripe billing publication completed — runtime UNVERIFIED — 2026-11-09

Published6b2bbad to canonical hvacline main; push accepted f858404..6b2bbad
without force from an isolated checkout. Forty-eight scoped files include the
full sandbox maintenance-billing feature, automatic business resolution and
ElevenLabs text wordmark. Earlier local-only billing restriction is superseded.
Existing published SMS/inbound code remains; original branch/working edits are
preserved. Hooks disabled; [skip ci] [skip render] retained. No tests, builds,
lint/type checks, migrations, services, Stripe setup/payments or hosted deployment
commands ran. Install dependency/apply0020, configure sandbox Stripe, deploy both
apps and perform owner acceptance per docs/maintenance-billing.md and
docs/homepage-branding.md. Runtime remains unverified.

## Stripe billing publication authorized — 2026-11-09

Owner requests pushing current work and explicitly includes Stripe code. This
supersedes the earlier local-only restriction for billing commit1297b0a. Publish
the complete billing feature, automatic business resolution and ElevenLabs text
wordmark on canonical main from an isolated checkout based on f858404. Preserve
published SMS/inbound behavior, unrelated original working edits and historical
notes. Hooks disabled and [skip ci] [skip render] retained. No verification,
migration, provider action or hosted deployment execution is authorized.

## Automatic billing business resolution — implementation UNVERIFIED — 2026-11-09

Owner requests removing manual BILLING_MERCHANT_AGENCY_ID configuration. Local
source now derives billing ownership from the authenticated customer's persisted
account; administrator labor uses the existing authenticated actor's business.
Removed the setting/startup/readiness requirement and added account/business
matching when locking billing rows. Existing customer/MFA, admin authentication,
appointment ownership, composite foreign keys, saved Stripe customer binding and
sandbox-only restrictions remain. One configured Stripe sandbox account is still
used; this does not add Stripe Connect or production identity support.

Updated environment template, setup guide and unexecuted regression specifications
for configuration, admin authorization and same/other-business account isolation.
No new migration/dependency; original billing migration0020 remains required.
Changes are local/unpublished/undeployed. No tests, builds, lint/type checks,
migrations, services, provider actions or deployment ran. Owner commands and
manual acceptance: docs/maintenance-billing.md. Runtime remains unverified.

## SMS/inbound publication completed — runtime UNVERIFIED — 2026-11-08

Publishedf858404 to canonical hvacline main; push accepted430c16d..f858404 without
force from an isolated checkout. Sixteen scoped files publish SMS-capable US
number support, corresponding specifications and inbound/incident guides/notes.
Local billing commit1297b0a is excluded and remains unpublished. Original local
main and remote main intentionally diverge; preserve the original working edits.
Hooks disabled and skip markers retained. No tests, migration, services, provider
requests or deployment commands ran. Backend/frontend deployment and runtime
acceptance remain pending; owner commands/manual checks are documented in
docs/sms-capable-demo-numbers.md and the corresponding inbound/incident guides.

## Homeowner maintenance billing — implementation UNVERIFIED — 2026-11-08

Owner specifies fixed technician maintenance-hour packages for homeowners, upfront
initial payment and a new separate checkout for additional hours on the existing
account. Website billing is restricted to Stripe sandbox/test; this supersedes the
early AI-voice-time interpretation. Local source adapts DwellCall customer binding,
checkout reservations, gateway, signed receipts and reconciliation to HVACLine's
customer/MFA and agency ownership. Draft 3/5/10-hour monthly packages and extra-hour
rates share one editable catalog. Amounts are editable draft demonstration rates.

Source adds account package/purchased-hour balances, one-time extra-hours checkout,
payment-confirmed credit, current paid-period allowances, completed-labor debits,
portal cancellation at period end, cancellation of unpaid checkouts, unknown-write
recovery and refund/dispute holds.
Purchased hours remain until used; package hours reset per paid monthly period.
Booking itself never consumes labor. New /pricing and /billing pages, homepage
package section, billing auth continuation and shared circular loading states use
the existing charcoal/orange design. Live keys/mode/events/rows are rejected.

Migration20261108_0020 and Stripe dependency are written, unapplied/uninstalled by
Codex. Regression specifications are unexecuted. No tests/builds/lints/type checks,
services, Stripe setup/payment, deployment or publication ran. Existing customer,
privacy, development and launch gates remain. Exact setup, owner commands and
manual checks: docs/maintenance-billing.md. Runtime and sandbox acceptance remain
pending; source does not establish payment success.


Owner requests a local commit only, with no push. Runtime verification, Stripe
setup and deployment remain pending; no execution checks are authorized.

## Hero inbound number publication completed — UNVERIFIED runtime — 2026-11-08

Published430c16d to canonical hvacline main; push accepted ecd8b13..430c16d
without force. Four scoped files restore the hero phone link and document owner
checks. Unrelated SMS and historical inbound edits remain local. Hooks disabled;
[skip ci] [skip render] retained. No checks, deployment or calls ran. Frontend
deployment, visual/dial-link acceptance and live inbound acceptance remain pending.

## Hero inbound number restoration authorized — UNVERIFIED — 2026-11-08

Owner supplies the public business number and requests restoring it in the hero,
superseding the October31 homepage removal. Local source adds a visible phone
link below existing actions using the supplied number and canonical tel target,
shared phone icon and responsive styles. No new setting or backend/provider
change. Unpublished/undeployed; no checks or calls ran. Owner command:
`npm run verify:web`; manual desktop/mobile, keyboard and dial-target checks:
docs/telnyx-sip-setup.md. Live inbound acceptance remains pending.

Owner authorizes publishing this hero change to main with hooks disabled and
[skip ci] [skip render] markers; unrelated SMS/inbound investigation edits remain
local. No verification execution or hosted configuration change is authorized.

## SMS-capable US numbers authorized and implemented — UNVERIFIED — 2026-11-07

Owner explicitly requests easing the check so SMS can reach the receiving number.
This supersedes the earlier mobile-only decision. Source removes the carrier
line-type restriction, retaining lookup identity/US-region/carrier-error checks;
mobile, landline, VoIP and unknown/missing types can attempt provider SMS. Shared
US destination validation includes explicit VoIP classifications. Correct six-digit
provider verification, MFA, consent, proof binding/expiry/single use, quotas and
activation remain required. UI/bridge wording updated; regression specifications
written but unexecuted. No new setting, dependency or migration. Changes are local,
unpublished and undeployed; no tests/builds/provider requests/SMS/calls ran. Delivery
and hosted acceptance remain unverified. Exact owner commands/manual checks:
docs/sms-capable-demo-numbers.md. The historical422 cause remains unknown.

## Hosted website reaches SMS endpoint; rejected request — 2026-11-07

Owner-supplied Render log shows successful build/startup, readiness/auth and
outbound availability HTTP200, followed by SMS-start422 and a retry429 about14
seconds later. Availability response body and exact422 error are absent; no SMS
delivery or app-bound proof acceptance is established. Source rejects invalid/US
ineligible inputs and carrier lookup failures with422; provider HTTP failures map
503. Lookup rejection precedes SMS send. Reservations commit before lookup and
failed attempts count toward cooldown/budgets; default cooldown is60 seconds.
Sonetel/VoIP rejection remains a possible cause, not confirmed by these logs.
No Codex live request, verification command, provider/configuration change or
application-code change ran for this review.

## Existing SMS flow reviewed; provider console acceptance reported — 2026-11-07

Owner reports six-digit delivery/accepted verification through Telnyx Learn &
Build on the existing profile. Static source uses the same SMS-send endpoint
and official saved-verification-ID verify equivalent. Homepage, Next bridge,
backend challenge/verification and proof consumption are connected in source;
hosted application acceptance remains unverified. Mobile carrier lookup is an
additional app gate: SMS-capable VoIP can still be rejected under mobile-only
policy. SMS routes also share website/live-voice activation gates.

New authenticated profile GET HTTP200 matches configured ID/name and reports
code_length6, consistent with earlier authorized PATCH. Earlier null readback
alone did not establish a failure; the app never checks this field. Exact
unset-profile default is not established by available request evidence/docs;
no further profile mutation is justified merely by null. No SMS, call, code
change, test suite or hosted activation ran. Report and remaining requirements:
docs/sms-verification-flow-review.md. Prior0019 confirmation remains valid.

## Existing Verify profile SMS code length6 — verified — 2026-11-07

Owner authorizes updating the existing named HVACLine Public Demo OTP profile.
Authenticated GET/PATCH/GET each returns HTTP200; initial identity/name match,
final sms.code_length is integer6. PATCH copies the current SMS object and changes
only code_length. Before/after comparisons confirm all other SMS settings and
voice/flashcall/WhatsApp/spend configuration unchanged; other profile settings
are identical apart from updated_at metadata. Earlier null code length is resolved.
No SMS, call, new profile, application-code change or public activation occurred.
Local credentials/raw responses are not retained in notes. Live delivery and code
acceptance remain pending a real consented US mobile; database0019 is confirmed.

## Configured database already at0019 — verified — 2026-11-07

Owner updates local database URLs to the current intended Render target and
confirms completion. Local runtime/direct URLs normalize to the same Neon
endpoint/database. Authorized bounded database operation reads revision0019
before and after and confirms outbound_phone_verifications exists. No upgrade
was necessary; no seed, downgrade, data reset or business-row access occurred.
Initial sandbox connection failed; approved network escalation completed the
readback. This establishes the configured target schema, not live SMS acceptance.
Local Verify key/profile remain absent; hosted settings were not inspected.
No SMS/call, tests, public activation or deployment ran. SMS next requires a
six-digit Verify profile and real consented US mobile, with provider delivery/
code validation followed by the gated website flow.

## US outbound reaches voicemail — owner provider evidence — 2026-11-07

Owner supplies an ElevenLabs SIP outbound conversation at18:58Pakistan matching
the latest attempt window/destination. Provider reports Successful, eight seconds,
two messages, a receiving voicemail greeting and agent-initiated ending. This
establishes an actual SIP call with media for that attempt despite the earlier
unknown admin response. Human ringing/answer/two-way acceptance, independent
carrier finalization and backend signed terminal state remain unverified. Next:
owner runs the known-call read-only status GET after the accepted webhook; do
not infer completed solely from provider Successful or retry while unknown.
Opaque provider IDs are in the local investigation report; no recipient or
transcript text retained. No Codex live action, code or flag change ran.

## New outbound attempt reaches dial; outcome unknown — 2026-11-07

Owner supplies admin HTTP200 with unknown/nonterminal status and matching
Render dial-failed/outcome_unknown true warning, created13:58:06Z. This confirms
preflight returned successfully and the dial path was attempted; carrier outcome
is unestablished. Later webhook POST HTTP200 is shown, but access logs alone do
not correlate it to this call or establish finalization. Next is owner read-only
GET of this known local call, plus provider initiation/history and carrier evidence.
No redial or slot clearing. Exact opaque IDs and bounded status GET are recorded
in docs/outbound-call-timeout-investigation.md. Source masks dial HTTP/network/
receipt causes; its receipt requires both provider IDs although official response
schema permits absent IDs. This is a possible classification path, not the
established incident cause. No Codex checks, live requests or code changes ran.

## Workflow/tool support published — UNVERIFIED runtime — 2026-11-07

Published ecd8b13 to canonical hvacline main; push accepted c42a8b8..ecd8b13
without force. Five scoped files include provider, regression specifications,
GET-only diagnostic, runbook and selected current notes. Hooks disabled and
[skip ci] [skip render] markers retained. Earlier inbound/investigation documents
and historical project-note changes remain local. No verification, hosted
configuration change, deployment or call ran. Owner must deploy this backend
revision on Render; no migration or new setting is required for this change.
Other printed agent/SIP checks passed in prior owner diagnostic; quotas,
cooldown, active/unknown reservations, saved failed keys and provider/carrier
availability remain independent blockers. Earlier timeout outcome is unresolved.

## Workflow/tool publication authorized — UNVERIFIED — 2026-11-07

Owner requests pushing the workflow/tool support to main. Publish provider,
regression specifications, GET-only diagnostic, runbook and relevant new notes;
preserve earlier inbound/investigation edits and historical project-note changes.
Use disabled local Git hooks and [skip ci] [skip render]. No checks, hosted
configuration changes or call execution are authorized by this publication.
Static review finds base prompt/first-message and knowledge/preset/procedure/
initiation-hook restrictions remain; all corresponding owner diagnostic results
passed. Old Render revision, saved terminal-failed request replay, quotas,
cooldown or an active/unknown call can still prevent a new dial. Default failed
reservations count toward budgets. No live outcome is established.

## Workflow and additional-tool support — UNVERIFIED — 2026-11-07

Owner authorizes outbound agents with workflows and tools. Local source removes
blanket workflow, external-tool-ID and MCP-reference bans and accepts additional
inline/native tools. Native End call remains mandatory. Main-agent native phone
transfer retains fixed-destination/SIP REFER/enabled checks; workflow routing,
overrides and external-tool effects are trusted hosted configuration and are not
validated by that transfer gate. Other base prompt/privacy/auth/duration/webhook,
SIP, consent, policy, quota and replay checks remain. No new migration or setting.
Diagnostic updated to match; regression specifications written, unexecuted.
No Codex checks, hosted changes, deploy or call ran. Render still needs the new
backend revision; source support does not establish live acceptance or resolve
the earlier timeout. Owner commands/manual checks: docs/outbound-demo-calling.md.

## Current outbound preflight blocker — workflow nodes — 2026-11-07

Owner-run GET-only diagnostic returns agent/phone HTTP200 and all printed
comparisons PASS except agent no_workflow_nodes. Source validate_agent rejects
any truthy top-level workflow.nodes before dialing. This establishes a current
configuration blocker for the supplied inputs; matching incident/runtime values
and historical causation remain unverified. Node contents and edges are unknown.
The guard covers workflows that can override base prompt/tools or route calls;
it also rejects a harmless default start node. Inspect the outbound agent's
workflow before choosing configuration removal or narrowly validated support.
No backend relaxation, hosted change, Codex verification or call ran. Earlier
timed-out request remains separately unresolved.

## Subsequent outbound attempt — owner reports terminal failed — 2026-11-06

Owner supplies a separate admin POST result created2026-11-05T20:47:26Z:
HTTP200 with terminal failed and no transfer requested. This establishes a
recorded application-level failure, not a client timeout or carrier success.
Owner then supplies matching Render preflight-failed warning with unknown=false,
confirming this attempt stopped before provider dial POST. Exact GET/network or
configuration rejection remains masked. Unexecuted owner GET-only comparison
is documented in the investigation report. Earlier timed-out request remains unknown:
owner changed database afterward and cannot access the previous target. No
Codex call/query/verification or code fix ran. Evidence and next read-only
actions: `docs/outbound-call-timeout-investigation.md`.

## Outbound timeout investigation — outcome UNVERIFIED — 2026-11-06

Static trace at c42a8b8 confirms the admin route validates destination before
database reservation; tenant-locked persistent replay protection precedes two
provider preflight GETs and one dial POST. Each provider operation creates an
HTTPX client with a12-second operation timeout; no overall endpoint deadline or
explicit database connect/statement/lock deadline is configured in source.
Provider errors retain only unknown-outcome classification. Admin status GET
requires the local call UUID; there is no admin GET by request UUID. A POST replay
can create a call when the original never reserved, including after a policy fix.

Owner-supplied Render page reports c42a8b8 Live on Free, unlike the Starter
Blueprint. Owner confirms allowlist omitted the US destination, then reports
adding it and redeploying. Incident configuration/timing, reservation/provider
evidence and timeout cause remain unverified. No application changes, call/replay,
hosted changes, database queries or verification execution ran. Report, source
locations, missing evidence and safe owner-run recovery commands:
`docs/outbound-call-timeout-investigation.md`. Recover outcome before redial.

Owner subsequently runs the read-only request lookup in the selected Neon
database: zero matching reservations, provider conversations or SIP IDs. Given
source commit-before-dial behavior, this rules out a dial by that request if the
selected branch matches the incident runtime database and records were retained.
Runtime target matching and the timeout mechanism remain unverified; no Codex
database query or call ran.

Owner then confirms the runtime database setting changed after the call attempt.
The zero-row lookup on the new target cannot resolve the original request;
recover the previous target and inspect it read-only. Persistent request keys,
active-call slots and quotas are database-local and are not carried over merely
by changing DATABASE_URL. Preserve both databases; hold outbound replay.

## Mobile hardening publication completed — UNVERIFIED runtime — 2026-11-05

Published `c42a8b8`; canonical hvacline push accepted `05da57e..c42a8b8` to main
without force. Twenty-nine implementation/migration/specification/guide files
published, with hooks disabled and skip markers. Prior inbound documentation and
historical project-note edits remain local. No verification commands, migration,
provider changes, deployment commands, SMS or calls ran; production acceptance
remains pending as documented in `docs/public-demo-production-readiness.md`.

## Public mobile demo hardening — UNVERIFIED — 2026-11-05

Owner requests production readiness, clarifies real visitors receiving fictional
HVAC demo calls, and selects mobile numbers only. Initial callback implementation
published as `05da57e`; canonical push accepted `8f4f65a..05da57e` on main after
the old origin redirect failed. Hooks disabled and skip markers used; no checks
or hosted activation accompanied that publication.

Source retains authenticator MFA and adds account-derived owner tokens,
per-account call quotas, Telnyx mobile carrier lookup and provider-generated SMS
proof. Proofs bind tenant/account/destination, expire, limit attempts and consume
with call reservation; replayed call keys preserve original fingerprints/outcomes.
SMS sends/verification attempts commit before network operations and failures
count toward persistent budgets. Website configuration now requires SMS credentials.
No voice verification fallback. Raw numbers/codes are excluded from the new table.
Forward migration `20261105_0019` is written, unapplied. Deployment template removes
automatic seeding; customer JSON reads are bounded while streaming; frontend adds
basic security headers. Outbound failure logging contains only phase/unknown flag
and opaque call ID. Existing provider/TLS/webhook/privacy/transfer gates remain.

Regression specifications are written/updated, unexecuted. Owner now authorizes
committing and pushing this hardening to main with hooks disabled and skip markers,
preserving unrelated inbound edits and historical notes. No verification commands,
migrations, provider/hosting edits, SMS, calls or deployment commands ran.
Production acceptance remains unestablished:
Telnyx Verify setup,0019 release, owner checks, real SMS/call acceptance, operations
and published privacy/retention decisions are pending. Demo backend identity stays
development-scoped; no production-environment bypass was added. Exact commands,
settings and manual checks: `docs/public-demo-production-readiness.md`.

## Signed-in public US callbacks — UNVERIFIED — 2026-11-05

Owner authorizes public callback requests and explicitly retains sign-in with
authenticator MFA; no anonymous access. Source extends `consented_us` to the
website path with transfer disabled. Website activation requires real outbound
acceptance; transfer acceptance is conditional on enabled transfer. Availability,
route and service share the website gate. Existing `auth/me` enforces verified
current-factor MFA sessions; callback bridge session checks remain mandatory.
Known US destination rejections unlock correction/renewed consent; uncertain
outcomes retain recovery. All consent, destination, quota, idempotency, provider
preflight and signed-event controls remain. No migration is introduced.

This supersedes older admin-only US and mandatory-transfer website decisions.
Regression specifications added/updated, unexecuted. No checks, services, calls,
provider/hosted edits, deployment, commit or push ran. Hosted activation remains
pending; no successful end-to-end US call is recorded. Do not fabricate live
acceptance. Exact hosted settings, owner commands and manual checks:
`docs/public-callbacks.md`. Existing unrelated inbound edits are preserved.

Owner subsequently requests publishing the current callback implementation before
the production-readiness review. Publish this feature, its regression specifications
and guide to main with hooks disabled and skip markers. This does not authorize
verification commands, hosted activation or calls; production readiness remains
unestablished.

## Telnyx Pakistan destination blocked — owner screenshot — 2026-11-05

Owner screenshot shows Paid account and explicit upgrade-required restriction for
PK in the outbound profile. Pakistan carrier access is blocked at that account
level; the earlier diagnostic PASS does not establish Telnyx destination access
or explain the previous failed attempt. Source also rejects Pakistani destinations
under `consented_us`; allowlist mode separately requires exact owner approval.
The dedicated outbound connection has no assigned numbers while inbound retains
one, consistent with the documented split: number assignment controls inbound
routing, outbound uses digest authentication/profile and the account-owned caller ID.
Profile screenshot appears to select Record All Outbound Calls; saved state is
unverified. Owner must select Do Not Record and save before further calling.
Next: resolve carrier destination/account access and backend destination policy,
then inspect existing failure evidence before another authorized call. No provider
changes, verification commands or calls ran.

## Outbound diagnostic checks pass — owner evidence — 2026-11-05

Latest owner-run GET-only diagnostic reports agent/phone HTTP200 and PASS for
all printed checks: local first-message/system-prompt match, auth, recording off,
zero-day retention, <=180-second duration, webhook assignment/events, native End
call and SIP resource/provider/Telnyx address/TLS/digest. This supersedes the
earlier first-message/privacy mismatches. The diagnostic covers selected checks,
not full deployed preflight or live acceptance. Next is one owner-run consented
admin AI-only call if configured cooldown/quotas allow it. Previous failed attempt
counts toward limits and its terminal request key cannot redial. No Codex check,
provider edit or call ran; deployed alignment and carrier acceptance remain unverified.

## Outbound prompt publication authorized — UNVERIFIED — 2026-11-04

Owner requests pushing the synchronized outbound prompt/agent JSON and related
outbound notes to main. Preserve unrelated inbound documentation/provisioning
edits. Publish with local hooks disabled and [skip ci] [skip render] markers;
no tests/builds/checks, hosted agent change, deployment or call is authorized.
Runtime and hosted/deployed text alignment remain unverified.

## Outbound prompt synchronized to owner-supplied text — UNVERIFIED — 2026-11-04

Copied the owner's exact latest system prompt, including CRITICAL — CALL
TERMINATION, into outbound `prompt.py` and the agent JSON prompt field. Existing
first message, identity, native End call definition and all security/privacy,
TLS, webhook and transfer controls are preserved. Source inspection confirms
preflight already accepts native system end_call in `built_in_tools` or `tools`
and rejects its absence; no validator change is needed. Owner reports enabling
the dashboard tool fixed termination; this is not independent carrier evidence.

Hosted agent and deployed backend were not inspected or changed. Their exact
text alignment with this revision remains unverified; preflight still requires
matching prompt text (apart from leading/trailing whitespace). No research,
tests/builds/checks, deployment, commit, push or calls ran. Deferred owner command:
`.venv/bin/python -m pytest tests/test_outbound_demo.py`. Before separately
authorized calling, manually compare hosted/deployed prompt and first message,
confirm native End conversation is enabled and retain existing TLS, signed
webhook, auth, privacy and disabled public/transfer controls.

## Outbound live-test prerequisites — owner reports resolved — 2026-11-04

Owner confirms the remaining prerequisites in the readiness handoff are resolved:
Render backend is Live, outbound TLS/digest is configured, and hosted prompt/first
message match the deployed backend with native End call enabled. This supersedes
earlier deployment/TCP/alignment blockers as owner-reported evidence, not an
independent inspection. Next is one consented private admin AI-only outbound
test using the existing runbook; actual carrier termination and signed terminal
receipt remain unverified. Website and human-transfer acceptance remain pending.
No call, configuration change, deployment or verification command was executed.

## Native end call — disabled hosted tool corrected by owner — 2026-11-04

Owner identifies the cause of the outbound dashboard failure: native End call
was disabled in the ElevenLabs settings. Owner enabled it and reports end-call
behavior now works. The hosted tool was unavailable despite the system prompt
requesting it and the repository JSON defining it. This is owner-reported
configuration/acceptance evidence; hosted configuration, tool arguments and
actual session termination were not independently inspected.
Official documentation confirms native end_call takes a required reason and an
optional message; Tool Call Testing supports end_call parameter assertions.
Read-only hosted lookup failed sandbox networking and escalation was canceled.
Codex made no implementation, regression, hosted configuration or permission
changes during this investigation; existing preflight is preserved. No tests,
builds, lint, formatting/type checks, calls, deployment, commit or push ran.

## Outbound conversation refinement — UNVERIFIED — 2026-11-04

Owner requests concise American HVAC receptionist behavior, one introduction,
one useful question per turn, correction/pause handling, disabled-transfer silence
and native call termination without spoken tool names or emotion tags. Owner
confirms the ending artifact was audible. Source updates FIRST_MESSAGE/DEMO_PROMPT
and synchronizes the existing agent JSON; native tool configuration, privacy,
hazard handling, consent and all calling controls are preserved. Duration remains
a <=180-second ceiling, not a pacing target.

Hosted agent was not updated. Read-only network inspection failed in the sandbox;
owner aborted the escalation and requested manual dashboard work. No hosted
configuration or audio inspection completed; the exact audible-leak cause remains
unverified. Existing preflight still requires exact hosted/backend prompt and
first-message matches. Owner must apply the JSON's two text fields to the existing
outbound agent and coordinate the same backend version before enabling calls.
No tests/builds/lint/format/type checks, live calls, deployment, commit or push ran.

## Callback sign-in gate — UNVERIFIED — 2026-11-04

Owner requires sign-in before callback requests. Source gates the Radix form on
existing customer session validation, with structured401/503 failures in the Next
availability/status/submission bridge. The existing login/signup/MFA flow carries
only a fixed demo-call intent and returns to the homepage modal; normal account
navigation remains `/book`. Pending request key/lock recovery is retained and
returning never submits a call. This supersedes anonymous form preview; it does
not remove current calling/policy/TLS gates or authorize customer-to-admin bypass.

Focused auth/bridge regression specifications are written, unexecuted. No local
tests/builds/lint/type checks, provider/config changes, migrations or calls ran.
Owner checks/manual acceptance: `docs/homepage-hero.md`. Earlier frontend removal
commit9867717 has successful Vercel frontend/worker statuses; backend rollout and
live calling remain unverified. Publish this gate under the ongoing main rollout
authorization, preserving older unrelated inbound documentation/provisioning.

## Calling date removed; outbound rollout pending — 2026-11-04

Owner requests removing the November5 calling announcement and rolling out
outbound calling. Source removes the hero banner and obsolete date references
from homepage/Calling section/FAQ and disabled dialog/bridge messages. Existing
call eligibility and activation gates are retained. Owner clarification of
admin-only versus visitor rollout is pending. Render/Vercel are not connected
and no local deployment credentials are configured; hosted rollout remains
unverified. No tests/builds/lint/type checks, provider changes or calls ran.

The earlier consented-US policy and hero modal were committed/pushed as048ff2f;
remote accepted1667e5f..048ff2f to main. The new wording is a separate follow-up.
GitHub reports successful Vercel frontend/worker deployment statuses for048ff2f;
this does not establish Render backend readiness or live-call acceptance.
Preserve old inbound-investigation/provisioning edits outside this publication.

## Outbound policy and hero publication authorized — 2026-11-04

Owner requests pushing the pending consented-US admin policy and hero demo-call
modal to main. Scope includes both features, dependency manifests/lockfile,
unexecuted regression specifications and their documentation. Static source and
credential review found no exposed secrets in that scope. Preserve older inbound
investigation documents and the inbound-provisioning note below outside this
publication. No tests/builds/lint/type checks, migrations, deployment commands or
calls are authorized by this push request. Use existing skip markers and disable
local Git hooks; runtime remains UNVERIFIED and public/transfer gates stay off.

## Hero demo-call modal — UNVERIFIED — 2026-11-04

Owner requests a hero phone-demo CTA and polished modal using an established
library. Source adds Radix Dialog1.2.0 and a shared dialog opened from the hero
and Calling section, with responsive orange/charcoal layout, explicit consent,
phone focus and clicked-trigger focus restoration. Existing outbound controller,
single-request lock, status polling and session-key recovery move into the dialog
owner so closing preserves state. Preview fields are editable with gates off;
submission still requires availability. Website/transfer flags and admin-only
consented_us policy are unchanged. No backend/provider/agent/webhook edits.

Dependency manifests/lockfile updated in npm lockfile-only mode with scripts
disabled. No tests/builds/lint/type checks, services/browser preview, deployment,
calls, commit or push ran. Implementation/rendering UNVERIFIED. Owner setup,
exact commands and manual acceptance: `docs/homepage-hero.md`.

## Consented US outbound admin policy — UNVERIFIED — 2026-11-04

Owner requests `OUTBOUND_DEMO_NUMBER_POLICY=allowlist|consented_us`, defaulting
to existing allowlist behavior. Source adds pinned phonenumbers9.0.42 metadata
validation for US states/DC/territory mobile and landline ranges, canonical E.164
normalization before fingerprints/quotas, and structured destination errors.
Consented US mode permits an empty allowlist, requires the existing authenticated
admin path and rejects enabled website/transfer configuration. Website routes
also reject that policy. Preflight preserves TLS/digest and requires a canonical
provider caller number distinct from the actual destination to preserve loop
protection without an allowlist. Existing consent, tenant quotas/locking,
idempotency, signed events and unknown-outcome handling are reused unchanged.

Focused unit/API/database regression specifications are added but unexecuted.
No migration, provider/agent/webhook/environment change, install, verification,
deployment, call, commit or push ran. Implementation/runtime remain UNVERIFIED.
Owner setup, exact commands and manual acceptance: `docs/outbound-demo-calling.md`.
Metadata establishes numbering-range eligibility, not subscriber assignment,
ownership or reachability; fresh out-of-band consent remains required. Existing
Render deployment and reported TCP versus mandatory TLS blockers remain pending.

## Owner-corrected outbound rollout status — 2026-11-04

Owner reports the dedicated ElevenLabs outbound agent/webhook and Telnyx
outbound SIP connection/spending/destination limits are configured, Render
agent/phone resource IDs are set, Neon migration0018 is applied, 127 focused
tests passed and frontend typecheck/build passed. These owner-reported results
supersede older pending-setup/check notes; they were not rerun by Codex.

Owner reports Render deployment1667e5f failed after a successful build. Priority
is inspecting that deployment's Events/runtime logs or confirming a newer Live
commit, then checking remaining private configuration/authorized recipient and
webhook secret. Last reported ElevenLabs trunk transport was TCP; source preflight
requires TLS. Preserve the existing agent/connection; no new implementation is
requested. Live outbound remains untested and human transfer disabled. Only
after backend/configuration acceptance, proceed to one restricted admin test
call, keeping public calling and transfer disabled.

## Final closeout publication authorized — 2026-11-03

Owner explicitly requests committing/pushing only closeout fixes, regression
specifications and documentation to main after static diff/secret review. Scope
is the phone ingress/provider, two regression files, outbound guide, this note's
November 3 closeout evidence and `FINAL-CLOSEOUT.md`. Older inbound-investigation
documentation and the provisioning section below remain excluded/preserved.
No tests, builds, lint, type checks, migrations, deployment or calls are authorized
for publication. Earlier recorded test results remain the evidence; calling and
transfer gates stay disabled and live acceptance remains pending.

## Authorized inbound/webhook regressions — 2026-11-03

Owner explicitly requested the focused inbound/webhook tests from the closeout.
`DEMO_SANDBOX_ENABLED=false PYTHONPATH=apps/backend/src .venv/bin/python -m
pytest --import-mode=importlib tests/test_telnyx_sip_provider.py
tests/test_phone_webhook_validation.py tests/test_phone_conversation_provider.py
tests/test_phone_post_call_ingress.py` passed **73 tests in 2.32s**. This includes
the new malformed-signature/large-timestamp and streaming-body regressions.
No database tests, other checks, migrations, services, provider edits or calls
ran. Hosted/live calling and broader release acceptance remain unverified.

## Authorized outbound unit verification — 2026-11-03

Owner then explicitly requested `npm run test:web --
src/app/api/outbound-demo/route.test.ts`: **15 tests passed**, one file, 556ms.
Vitest emitted a non-failing warning about future Vite native config loading.
No configuration change or additional checks were made.

Owner explicitly requested `python -m pytest tests/test_outbound_demo.py`.
Shell `python` was unavailable; equivalent `.venv/bin/python -m pytest
tests/test_outbound_demo.py` passed **39 tests in 1.64s**. This verifies only that
unit suite; database, new webhook regressions, hosted calling and transfer remain
unverified. No other checks, migrations, services, provider edits or calls ran.

## Portfolio closeout and migration authorization — 2026-11-03

Focused static review covered browser Voice/Chat/booking, SIP initialization and
signed finalization, outbound/configuration/transfer gates/migration0018, and
homepage claims/flags. Source fixes reject malformed signatures/oversized
timestamps cleanly, bound inbound post-call bodies while streaming and move
synchronous finalization off the async request loop. Regression specifications
are written but unexecuted; current implementation/runtime remain **UNVERIFIED**.

Owner subsequently explicitly requested completing migrations. The configured
development database reported `20261101_0018` before and after the targeted
Alembic upgrade; it was already current and no schema change was needed. This
supersedes pending0018 notes for that inspected target only, not hosting/schema
acceptance. No seed, downgrade, tests, build, lint, formatting, type checks,
services, provider edits, deployment, commit, push or call ran in this closeout.

Private local outbound agent/resource/recipient/state/signing configuration is
missing; local execution/acceptance flags default false. Hosted values were not
inspected and no private environment was changed. Outbound REFER support,
unavailable-human behavior and carrier-enforced transferred-leg duration remain
public/transfer blockers. Development identity boundaries remain intentional.
Current evidence, exact owner commands and deployment/live-call handoff:
`FINAL-CLOSEOUT.md`; detailed setup: `docs/outbound-demo-calling.md`.

## Calling publication authorized — UNVERIFIED — 2026-11-02

Owner explicitly requests pushing the outbound implementation and November 5
announcement to main. Publication includes the dedicated outbound adapter,
disabled website form, unapplied forward migration0018, configuration templates,
unexecuted regression specifications and setup/acceptance handoff. Earlier
uncommitted inbound-investigation documentation is excluded from this publication.
No tests, builds, linters, type checks, migrations, services, calls, provider edits
or hosting deployment commands are authorized by this push request. Calling
remains disabled and implementation/runtime **UNVERIFIED**. Owner setup and exact
checks: `docs/outbound-demo-calling.md`; hosted revision and activation are pending.

## Calling completion and November 5 announcement — UNVERIFIED — 2026-11-02

Owner requests inbound/outbound calling advertised as coming November 5, 2026.
Homepage source now shows the shared release date in the hero, calling section
and FAQ, plus Calling navigation. Disabled calling renders two upcoming options
and a browser Voice link; existing-request status recovery stays accessible.
The date never enables provider or website gates automatically.

Outbound source repairs allow form correction only for certified pre-creation
rejections, serialize browser status reads and preserve uncertain transfer
evidence across later lifecycle events and late dial errors. Malformed nested
transcript/tool collections reject before state changes. Regression specifications
are written, unexecuted. Existing provider, migration and real-call prerequisites
remain; calling is disabled and no end-to-end acceptance is claimed.

Local/unpublished and **UNVERIFIED**. Source formatting only; no verification,
migrations, services, calls, provider edits, commits, pushes or deployments ran.
Exact owner commands and manual checks: `docs/outbound-demo-calling.md`.

## Outbound AI demo calling — disabled, UNVERIFIED — 2026-11-01

Source adds a separate ElevenLabs outbound SIP adapter and dedicated fictional
HVAC demo prompt, using the existing FastAPI/Next/Neon architecture. Admin dialing
always requires the existing strong admin token; website dialing remains disabled
until owner-recorded real outbound and human-transfer acceptance. Exact E.164
allowlist, explicit versioned consent, tenant-serialized reservations, persistent
idempotency, one active/unknown slot, cooldown/global/number limits and existing
HMAC webhook verification protect attempts. No raw phone numbers, audio or
transcripts enter the new call table; keyed hashes and minimal consent/receipt
metadata persist. New forward migration `20261101_0018` is unapplied.

Native transfer configuration permits one fixed authorized human via SIP REFER,
with separate-turn agreement in the prompt/tool condition. REFER acceptance never
claims a human answer; missing/uncertain results retain the slot until an audited
operator attests that every carrier leg ended. AI duration is checked at <=180
seconds before dialing. Telnyx's documented external-transfer flow requires inbound
matching; outbound-originated REFER, acceptable unavailable-human behavior and a
carrier-enforced transferred-leg duration limit remain unresolved prerequisites.
The carrier-limit flag is an owner attestation, not an implemented timer. Keep
transfer and website disabled until these are established and tested.

Homepage form, same-origin server bridge, focused specifications and exact agent
JSON/dashboard/environment/manual-call instructions are staged. Admin-controlled
out-of-band number approval is the only ownership-verification mode; no unrestricted
public dialing, OTP service or new platform is added. Existing inbound/browser/booking
routes and provider settings were preserved. Source formatting only; no tests,
builds, linters, type checks, migrations, services, live calls, provider edits,
commits, pushes or deployments ran. Implementation/runtime remain **UNVERIFIED**.
Owner commands and real-call procedure: `docs/outbound-demo-calling.md`.

## Simplified homepage with prominent voice AI — UNVERIFIED — 2026-10-31

The owner requested hiding the public business phone number and simplifying the
hero around voice AI. Source removes the homepage phone panel/parser and public
phone-status number/dial link. A larger Line card defaults to Voice AI, with
existing guest text chat available as a secondary choice. Voice links to the
existing signed-in booking workspace; selecting Voice and microphone consent
remain explicit there. Old homepage phone-CTA variables no longer affect rendering.
Backend routing and customer contact workflows are unchanged.

Source formatting only; no tests, builds, linters, type checks, services, browser
previews or deployments ran. Implementation/rendering remain **UNVERIFIED**.
Exact owner command and responsive, keyboard, consent and chat checks:
`docs/homepage-hero.md`. Earlier phone-CTA activation instructions are superseded.
The owner subsequently authorized committing and pushing this frontend change to
`main`; no test execution or hosting deployment command was requested.

## Live inbound-number provisioning corrected — fresh-call acceptance pending — 2026-10-30

After the owner supplied the existing deployed operator token locally,
authenticated hosted APIs confirmed zero inbound numbers and no call policy for
the configured business. This establishes the provisioning gap behind the new
initialization 404. The existing FastAPI endpoint had already been confirmed by
its unauthenticated 401 response; no endpoint or tenant-validation bypass was
needed.

Registered the provider-confirmed assigned number as ACTIVE using the existing
audited, tenant-scoped API. Created the missing inbound policy using established
development defaults: UTC daily reception windows, two concurrent calls, ten
daily calls, callback fallback and no human transfer destination. Fallback wording
reuses the business's approved stored escalation message. Authenticated readback
confirmed that the exact canonical called number and enabled policy belong to
the same business. No credential, phone number or caller payload is stored here.

No Telnyx/ElevenLabs setting changes, migrations, deployment or simulated call
records were required. A fresh real inbound call must still confirm hosted
initialization 200 with the persisted UUID, audio/tools and signed finalization.
Older failed calls remain unbound; never synthesize their UUIDs or confirmations.

## Inbound phone webhook repair — checks passed, live acceptance pending — 2026-10-30

Owner reports Render `ab69756`, successful Telnyx → ElevenLabs SIP routing,
registered/enabled phone routes, repaired initiation authentication and 422 on
both webhooks. Source confirms digit-only called numbers fail the SIP E.164
validator; caller formatting alone cannot cause initiation 422. Documented
initiation fields and SIP failure metadata already have support. The exact
production rejected field remains unconfirmed without safe field diagnostics.

Local source canonicalizes ASCII international digit strings at the SIP boundary
through the existing E.164 validator and exact tenant-owned active-number route.
Bounded diagnostics log known validation paths/types only, masking unknown keys
and SIP-header names; no values, raw bodies or exception contents. Post-call
transcription still requires the persisted initiation UUID; documented failure
events do not require it, and unbound failures retain 409. Malformed metadata
provider types now reject with 422 instead of an unhashable-value exception.
Auth/HMAC, agent/tenant binding, replay fingerprints, quotas and audit gates remain.

Owner subsequently authorized all needed checks and treating the current database
as disposable. Focused phone suite: 76 passed; full non-database suite: 214 passed
with explicit test configuration; four phone database suites: 23 passed together on
a fresh local database that was dropped afterward. The first remote test run's
two failures were corrected and passed on retry: test sandbox isolation and
Alembic logging setup now preserving existing validation loggers. All eight
changed Python files pass Ruff format/lint and targeted mypy. Full-repository
checks still report unrelated baseline formatting/lint/type failures.

Read-only ElevenLabs inspection confirms enabled initiation fetch and missing UUID
on recent failed calls, with a digit-only system called-number variable. A
metadata reconstruction passes repaired initiation validation and fails the old
number check; reconstructed transcription reproduces missing-UUID 422. Original
HTTP bodies and successful hosted 200 remain unverified. No provider settings,
outbound calls or production writes occurred during testing. The owner explicitly
authorized committing/pushing the tested repair and Render rollout; publication
and hosted acceptance are in progress. Current runtime data was preserved;
existing test migrations ran only on isolated targets. No new
migration/dependency/configuration requirement. Exact results, commands and live
acceptance: `docs/inbound-phone-webhook-repair.md`.

## Original local draft integrated — runtime UNVERIFIED — 2026-10-29

The owner explicitly requested reviewing and publishing the original checkout's
remaining edits. Snapshot `7cb32e4` preserves that draft on local branch
`archive/local-voice-draft-20261029`. Its local browser provider is adapted to the
current Chat/Voice contracts and HVAC fields without restoring obsolete branding
or overwriting customer/MFA/booking work. ElevenLabs remains the default; local
mode is limited to the development workspace and rejects enabled customer portal
configuration. Local models run on the API host, with loopback-only Ollama.

WebSocket grants are hashed, single-use, origin/owner/channel/expiry checked and
revalidated during turns. Review/save, callback and on-screen booking reuse
existing services; local models cannot confirm or book. Phone status polling now
continues after terminal results and identifies the shared latest-call view.
No new migration; Piper remains an optional extra. Source formatting only;
implementation/runtime **UNVERIFIED**. No tests, builds, linters, type checks,
migrations, services or model/provider calls ran. Exact owner setup, commands and
manual acceptance: `docs/local-browser-voice.md` and
`docs/demo-readiness-checklist.md`.

## Main publication authorized; release handoff completed — 2026-10-29

The owner requested finishing and publishing pending work to `main`, superseding
the earlier feature-branch-only publication scope. The active Telnyx SIP and
gated homepage phone CTA commits extend published main `d85ff6d`. Static source
review and the release handoff are complete; implementation/runtime remain
**UNVERIFIED**. No execution checks, migrations, services, provider configuration
or deployment commands ran. The older dirty original checkout is preserved.

`docs/telnyx-sip-setup.md` now records the release delta from owner-reported Render
source `54e6603`, schema/dependency prerequisites, Blueprint seed/default-provider
differences, exact owner commands and live acceptance. Publication does not
activate Telnyx or the public phone CTA. Hosted revision/configuration, migration
`0017`, agent updates and real-call acceptance remain pending.

## Homepage phone CTA — disabled, owner verification pending — 2026-10-29

The existing hero now includes an optional phone-icon booking call panel. A
server-rendered configuration parser formats the configured US E.164 number and
derives its `tel:` link. Web-only `HOMEPAGE_PHONE_NUMBER_E164` holds the number;
`TELNYX_INBOUND_CALLING_VERIFIED` defaults false and suppresses the public panel
until the owner records real-call acceptance. Existing hero layout, typography,
booking/chat paths and Telnyx backend changes are preserved. The web environment
example carries the owner-supplied public business number, not application code.

Source, focused release-gate specifications and responsive acceptance remain
**UNVERIFIED**. No tests, builds, linters, type checks, services, provider calls or
deployments ran. Exact owner commands and desktop/mobile/focus checks:
`docs/telnyx-sip-setup.md`, homepage CTA section. Public activation requires live
Telnyx acceptance, explicit verified configuration and an authorized frontend
rebuild/deployment; no environment value was enabled by this implementation.

## Alternative Telnyx inbound SIP — implementation UNVERIFIED — 2026-10-29

Feature branch `feat/telnyx-sip-inbound` adds explicit disabled/Twilio/Telnyx SIP
selection behind the existing telephone enable flag. Telnyx routes directly to
the existing private ElevenLabs phone agent, with a separate authenticated,
size-bounded initiation endpoint, backend-owned active-number routing and existing
policy quotas. Call and conversation identity persist together in existing call
metadata; policy/advisory locks protect duplicate/quota decisions. Shared consent,
FAQ/intake/HVAC booking tools and HMAC/replay-protected post-call finalization are
reused. SIP handoff records backend authorization/audit and uses callback fallback;
native SIP REFER remains disabled without verified result handling. No Twilio
client/register-call, Telnyx REST dependency, new schema or frontend feature is
needed for this path. Historical Twilio finalization fingerprints are preserved.

Source and added unit/database specifications remain **UNVERIFIED**. Source
formatting only; no tests, builds, linters, type checks, migrations, services,
provider calls, purchases, account changes or deployments ran. Exact API settings,
Telnyx FQDN/ElevenLabs import and webhook setup, transfer design, owner commands
and live acceptance: `docs/telnyx-sip-setup.md`. Provider-dashboard setup and real
carrier acceptance remain **UNVERIFIED**. Existing development identity/privacy,
business confirmation and production onboarding gates remain; completed bookings
must survive disconnect and be checked in Operations during owner acceptance.

## Homepage guest chat — owner-approved behavior, acceptance pending — 2026-10-29

Owner selected one live text message/reply on the homepage, a dismissible sign-in popup on the second attempt, a 30-day browser allowance and same-tab continuation through existing authentication/MFA. The existing browser Line agent is reused with a guest-mode variable; a protected server-side bridge permits only approved FAQ lookup. Source adds atomic guest quotas separate from signed-in application quotas, no application transcript/customer/booking persistence, and bounded browser-only context handoff outside confirmation transcripts.

Implementation/runtime are **UNVERIFIED**. Source formatting only; no tests, builds, linters, type checks, installs, migrations, services, hosted agent edits or deployments ran for this feature. Migration `20261029_0017` and pinned `websockets==17.3` are new; feature defaults off. Owner setup, exact commands and manual acceptance: `docs/homepage-chat.md`. Apply schema/dependencies and shared agent guest-mode/completion-event settings before enabling API `HOMEPAGE_CHAT_ENABLED`; the database was previously confirmed at `0016`, not `0017`.

## Owner decision: remove demo wording and fictional-data requirements — 2026-10-29

The owner explicitly requested neutral product wording and removal of fictional-data requirements. This supersedes earlier synthetic-only instructions in this memory. Source removes the signup and browser/phone/WhatsApp consent requirements and demo/early-access presentation; AI/provider disclosure, microphone consent, authentication/MFA and readback confirmations remain required. New migration `20261029_0016` permits empty historical synthetic-acknowledgement timestamps without changing existing evidence. No runtime environment or development-actor configuration was changed.

On October 29, the owner explicitly authorized applying migrations. Alembic successfully upgraded the configured development Neon database from `20261028_0015` to `20261029_0016`; the subsequent revision readback reported `20261029_0016 (head)`. No tests, builds, linters, type checks, seeds, provider changes or deployments ran. Application/runtime acceptance remains **UNVERIFIED**; hosted agent prompts/tools and existing stored greeting/FAQs need separate owner updates. Exact owner commands/manual acceptance: `docs/customer-data-requirements.md`.

## Customer appointments dashboard refresh — owner acceptance pending

My appointments now has a responsive next-confirmed-visit card, date/time/status cards, Upcoming/History/All filters and stored-count/booking-limit sidebar. Display distinguishes holds, expired/cancelled records, past appointments and current scheduled windows without implying service completion. Existing details/rescheduling modal and APIs remain authoritative; no backend/schema/environment/dependency change. Source formatting and unexecuted presentation/expiry/timezone specifications only; runtime **UNVERIFIED**. Exact owner commands/manual checks: `docs/customer-appointments-design.md`.

## Customer memory dashboard refresh — owner acceptance pending

The Memory tab now has responsive orange/charcoal status/count/retention cards, saved details with source/update/expiry, a selected-detail consent editor, dated authorized-summary suggestions, WhatsApp pairing and privacy controls. Suggestions go through review before save; destructive actions use native confirmation dialogs. Booking limits stay on booking/history tabs. Existing backend options/revisions/APIs remain authoritative; no backend/schema/environment/dependency change. Source formatting only; no verification or deployments ran. Implementation/runtime **UNVERIFIED**; exact owner commands and manual checks: `docs/customer-memory.md`.

## Customer MFA QR and page refresh — owner acceptance pending

The owner reports that the QR code works. This is owner-reported scanning acceptance; Codex did not run a scan, and full MFA/recovery/security verification remains pending.

The customer MFA page adds browser-local SVG QR enrollment using the existing backend provisioning URI, with a manual-key fallback. Pinned `qrcode.react@4.2.0` and lockfile metadata added without installation; URI/key/TOTP consistency is validated before rendering. Orange/charcoal responsive layout now covers setup, verification, recovery and backup codes. No backend/schema/environment change. Source and focused specifications remain **UNVERIFIED**; no installs, tests, builds, linters, type checks, services, scans or deployments ran. Exact owner commands and desktop/mobile/privacy/scan acceptance: `docs/customer-mfa.md`.

## Render and Vercel deployment failures — owner acceptance pending

The subsequent owner-supplied Render traceback reaches router creation and fails because memory's `{key}` path parameter collides with the customer portal dependency argument `key`, an optional header. Renamed that internal argument to `portal_key`, preserving the header alias, routes and access gates. Added an unexecuted mocked-database regression specification for full app/router registration and OpenAPI parameter binding. No migrations, environment changes or frontend changes are required for this repair. Owner command: `python -m pytest tests/test_api.py`; manual API startup, readiness and authenticated/unauthorized memory-deletion checks remain pending. No verification commands ran.

Owner-supplied October 28 logs show Render completed migrations through `20261028_0015` but API startup rejected the enabled portal without `CUSTOMER_MFA_ENCRYPTION_KEY`. The Blueprint now declares a secret placeholder; the owner must set a stable dedicated Fernet key on the API and redeploy. Vercel rejected memory parsing because the `Fact` guard narrowed away saved provenance fields. Saved facts now validate all fields directly from an unknown record, preserving runtime validation. No application/schema/MFA-policy changes. No tests, builds, linters, type checks, migrations, services or hosting changes ran; repairs remain **UNVERIFIED**. Exact owner commands and deployment/manual checks: `docs/environment-handoff.md` and `docs/customer-mfa.md`.

## Publication authorized — UNVERIFIED

The owner requested committing and pushing all current work to `main`: direct inbound WhatsApp voice, optional customer memory, customer-only authenticator MFA and the icon-only GitHub header link. Publication includes forward migrations `0013`–`0015`; migration execution, provider configuration, MFA key setup and runtime acceptance remain owner-managed. Existing remote header changes must be retained. CI/Render skip markers accompany publication; no tests, builds, linters, formatters, type checks, migrations, services or provider calls were authorized or run. Exact owner checks remain in `docs/whatsapp-inbound-calling.md`, `docs/customer-memory.md` and `docs/customer-mfa.md`; header acceptance requires `npm run verify:web` and desktop/mobile link/focus checks.

## Mandatory customer MFA — UNVERIFIED

Owner narrowed scope to customer accounts only; Operations/staff access is unchanged. Local branch `feat/mandatory-authenticator-mfa` adds password-bound, short-lived enrollment/verification challenges, required authenticator proof before any customer session, encrypted tenant/account-bound TOTP seeds, replay protection, persistent lockouts and one-use recovery codes requiring verified replacement. The MFA patterns were adapted from the owner's `stealth-trails` repository to Python/FastAPI/Neon. No read-only pre-MFA or email/password fallback is provided.

Forward migration `20261028_0015` follows pending memory `0014`, adds three MFA tables and session evidence, revokes existing customer sessions and requires MFA-authenticated reapproval of WhatsApp memory links. API-only `CUSTOMER_MFA_ENCRYPTION_KEY` is required when the customer portal is enabled; retain a stable protected backup. Existing development/fictional-data gates and customer booking/Chat/Voice workflows remain. Recovery/reset invalidates earlier session and memory-link versions.

Source and focused specifications are **UNVERIFIED**; no tests, formatters, checks, migrations, services, provider calls, installs, commits, pushes or deployments ran for MFA. Configuration, reference provenance, exact owner commands and new/existing-customer/recovery acceptance: `docs/customer-mfa.md`. Production onboarding, email verification, password recovery, key rotation and managed lost-factor recovery remain outside scope. Prior memory work and unrelated homepage/style changes are preserved.

## Account-scoped customer memory — UNVERIFIED

Local branch `feat/customer-memory`, based on WhatsApp foundation `7ece835`, adds optional Neon memory scoped to verified customer account and agency. New forward migration `20261028_0014` adds policy, categorical fact, authorized-intake summary, WhatsApp identity and pairing tables plus verified account provenance on WhatsApp bindings. Customer controls support opt-in, corrections, forgetting, erasure and unlinking. No contact matching authorizes memory. WhatsApp requires approval from the existing signed-in browser account; opaque caller digests/BSUIDs are not phone numbers.

Memory references existing immutable confirmed intakes without transcript copies. Suggestions use customer-word evidence and facts require explicit selection/readback consent; no LLM extraction or free-text storage. Context is bounded; service/appointment references are read from owned authoritative records and never substitute for live availability/pricing/status. Consent revisions/erasure cutoffs prevent stale writes and old-history regeneration. Configurable expiry hides stale content immediately; a separate bounded owner-scheduled purge physically removes optional records. Booking, Calendar and notification transactions are unchanged; memory is independent of booking success.

Implementation and all test specifications remain **UNVERIFIED**. No tests, builds, linters, formatters, type checks, migrations, seeds, services, provider calls, installs, commits, pushes or deployments ran. Exact tools, environment names, owner commands, retention scheduling and cross-session acceptance: `docs/customer-memory.md`. Existing development/fictional-data identity/privacy gates remain. Unrelated header/title/style edits are preserved.

## Direct inbound WhatsApp voice — UNVERIFIED

Feature branch `feat/whatsapp-inbound-calling` implements direct ElevenLabs WhatsApp initialization, call-scoped authenticated tools and signed post-call finalization without Twilio credentials/IDs. The new forward migration `20261028_0013` adds agency-owned WhatsApp bindings and a WHATSAPP conversation channel. Initialization uses the documented empty call_sid, configured agent/Meta-number allowlist and opaque caller digest; consent creates the actual session. FAQs, confirmed intake/lead persistence, booking holds/readbacks, Google Calendar, notifications, audit and Operations reuse existing services. Callback-only contacts require a separate spoken readback; native transfer is not used. No messaging, outbound calls, voice notes or campaigns are implemented.

Existing development/fictional-data, privacy, 180-second and quota gates remain. One configured agency/agent/number per deployment; broader onboarding and real-customer production identity remain deferred. Focused adapter/API/database specifications are added but unexecuted. No tests, builds, lint/checks, type checks, migrations, provider calls, installs or deployment ran; source formatting only. Setup, environment names, exact owner commands and manual acceptance: `docs/whatsapp-inbound-calling.md`. Migration, provider setup and runtime remain **UNVERIFIED**.

## Customer palette — owner verification pending

The owner selected orange/charcoal across the homepage, login/signup and customer booking experience, using light backgrounds and dark feature panels. Shared customer theme variables now cover branding, voice graphics, controls, chat, booking progress/history, quotas, countdown and details dialogs; shared internal components retain prior colors through fallbacks. The site-wide favicon also uses orange/charcoal. Status colors remain semantic. No backend, schema or provider change. Source formatting only; implementation and browser/contrast acceptance remain unverified. Exact owner commands and manual checks: `docs/customer-color-refresh.md`.

## Customer booking quotas — owner verification pending

Deployment variable names, locations and values are consolidated in `docs/environment-handoff.md`; it contains no credential values. The latest customer limits need only the two API quota variables, defaulting to 1, while the frontend reads their effective values.

The account-scoped booking flow defaults to one active appointment and one successful date/time change per service-request booking history, configurable through API `CUSTOMER_MAX_ACTIVE_APPOINTMENTS` and `CUSTOMER_MAX_BOOKING_CHANGES`. The scheduling lock protects reservation/confirmation checks and both reschedule phases; completed retries bypass quota consumption. Active holds count, ended/cancelled bookings free capacity, and replacement IDs retain prior change usage through immutable existing reschedule audits. Authenticated API counts populate both booking/history pages and the details modal. No new migration or provider configuration change is included; phone/staff flows without verified customer-account linkage retain their existing behavior. Source formatting and unexecuted regression specifications only; runtime remains unverified. Exact setup, owner commands and acceptance: `docs/customer-booking-limits.md`.

## Booking details and three-minute timer — owner verification pending

The customer booking receipt and history now open an owned-booking details modal. Date/time edits reuse the existing reschedule transaction, Google conflict/ownership checks, notice rules and notification outbox, with explicit confirmation and retained browser-memory retry keys after uncertain responses. The customer proxy exposes only scoped details/availability/reschedule routes. Contact/service snapshots remain displayed reference data. The owner retained the 180-second cap; a prominent countdown uses the server authorization expiry, warns in the final minute and explains local timer expiry. Interrupted ten-minute changes and the unexecuted migration were discarded; no new migration or provider configuration change is included. Source formatting and unexecuted regression specifications only; runtime remains unverified. Exact owner commands, deployment order and acceptance: `docs/booking-details-and-timer.md`.

## Node 24 hosting compatibility — owner verification pending

The owner supplied a Vercel failure rejecting the root Node engine `>=26 <27` before the Python job build. Root/web manifests, npm lockfile engine metadata, `.nvmrc` and web CI now select Node 24 (`24.x` engines), matching Vercel's supported version. No dependency versions changed. Source/build compatibility and deployment remain unverified; no installs, tests, builds, linters or type checks ran. Owner commands and deployment checks: `docs/vercel-booking-jobs.md`.

## Vercel booking job runner — owner verification pending

The owner declined paid Render workers and selected Vercel. A separate root-level FastAPI Vercel project now exposes a bearer-protected POST batch runner, using the same database/integration configuration and a dedicated `BOOKING_JOBS_SECRET`. The frontend remains rooted at `apps/web`; the API remains on Render. Shared PostgreSQL transaction advisory locking coordinates function invocations and the retained standalone worker. Batches interleave notifications/calendar work, use a cooperative 20-second deadline with bounded database/provider waits, and preserve durable retries and provider idempotency. No new migration is required. Vercel Hobby cron is daily, so frequent invocations require an external scheduler. Source implementation and regression specifications are unverified; no tests, builds, linters, type checks, services or deployments ran. Exact setup, commands and manual checks: `docs/vercel-booking-jobs.md`.

## Migration settings repair — owner verification pending

The owner supplied a Render build failure after package installation: Alembic loaded enabled Google Calendar runtime settings with incomplete OAuth/encryption configuration. Alembic now uses `DatabaseConnectionSettings`, retaining PostgreSQL URL, test-isolation and production SSL validation without loading integration settings. API/worker retain strict enabled-integration validation through `DatabaseSettings`. Incomplete integrations must remain disabled in the service environment until configured. Regression specifications and deployment instructions were added; no tests, builds, linters, type checks or migrations ran for this repair. Exact owner commands and manual acceptance are in `docs/calendar-and-booking-messages.md`.

## Google Calendar and booking messages — implementation unverified

The October 27 implementation adds per-team Google OAuth/PKCE with encrypted offline credentials and browser-bound single-use state, live paginated conflict checks, deterministic event writes with durable reservation bindings, and worker reconciliation/owned-event cleanup. External edits/overlaps enter staff attention; they do not silently rewrite or cancel local bookings. Google has no atomic insert-if-free, so concurrent external writers remain a reconciled risk.

Confirmation/cancellation/reschedule emails and reminders use a transactional outbox with frozen payloads, bounded idempotent Resend retries, conservative unknown-outcome handling and signed delivery receipts. Missing confirmed email addresses are skipped; SMS is not implemented. Operations exposes connection, sync and delivery status. Migration `20261027_0012`, Google/Resend settings and scheduled job execution (Vercel function or persistent worker) are required before use. Features default off and retain development-only gates. No tests, builds, linters, type checks, migrations, services, provider calls or deployment ran. Exact owner setup, commands and acceptance: `docs/calendar-and-booking-messages.md`.

## Browser booking progress — owner verification pending

The owner reports successful full appointment booking as of October 27, 2026; this is owner evidence, not an independently repeated acceptance run. A subsequent frontend slice adds tool-driven booking stages, pending operations, confirmation guidance, hold countdown/expiry, stage-local failures and persistent CONFIRMED receipts to customer/operator browser conversations and the on-screen fallback. Activity labels respect connection and mute state. Unknown write results preserve retry context; the fallback can recheck an earlier confirmation after the displayed hold deadline. No backend API, migration or provider configuration changed. Regression specifications were added; no tests or hosted deployment ran. Exact owner commands and manual acceptance are in `docs/booking-progress.md`; implementation/runtime remain unverified.

## Product and scope

HVACLine AI is an AI phone receptionist and appointment-booking product for U.S. HVAC service businesses only. The October 24, 2026 owner mission supersedes the insurance roadmap, frontend freeze, and earlier restrictions against running the named verification commands. Development remains synthetic-only; live carrier success and production readiness must not be claimed without evidence.

## Architecture

GitHub redirected the authorized feature-branch push to `waqasraza123/hvacline` on October 25, 2026; the former `insurance-operations-ai` URL still redirected successfully at that time. Render's repository binding and deployed revision have not been verified.

Next.js/TypeScript web, FastAPI/Python 3.13 backend, separate worker, SQLAlchemy 2/psycopg 3/Alembic, and Neon PostgreSQL only. Keep established Python/workspace/CLI names, agency ownership keys, and migration history for compatibility. Public receptionist categories are exposed as `supported_service_categories`, mapped to the legacy storage column.

Existing signed Twilio ingress, ElevenLabs register-call voice connection, secret-authenticated tools, HMAC post-call verification, consent/readback receipts, approved FAQs, leads, callbacks, transfer commands, quotas, and audits are reused. No raw audio is stored. Transcript/customer/lead finalization stays in the signed post-call flow.

## HVAC implementation

Forward migration `20261024_0009` adds business schedules, confirmed HVAC service requests, and appointments. Scheduling uses per-business ZIP codes, IANA timezone, hours, team calendars/time off, duration, notice and horizon. Mutations lock the tenant schedule row; payload-bound booking keys prevent conflicting retries; appointments have a composite tenant/request foreign key. Reservations expire after five minutes. Confirmation, cancellation, and atomic rescheduling persist before returning success.

Authenticated phone tools verify active session/call ownership and expiry. HVAC service intake requires the existing contact-readback receipt and explicit structured confirmation. Hazardous requests enter human attention and cannot self-book. The operations projection excludes transcripts and shows real stored requests, bookings, calls and open handoffs. Existing receptionist and knowledge editors are reused inside the protected workspace, forwarding the in-memory admin token in headers. `/operations` uses existing development identity and hosted-sandbox token gates; this is not production login.

The opt-in Google Calendar connection/sync and booking-email slice is implemented but unverified; see the current section above. Unconnected teams retain operator-maintained internal scheduling.

## Verification during this execution

GitHub CI at implementation commit `0cbbe8f` passed both jobs: 83 Python tests, 24 web tests, Ruff format/lint, mypy, the production web build, migration upgrade/current/no-drift checks at `20261024_0009`, and worker readiness. Database tests used CI's isolated PostgreSQL 17 service. No shared or production Neon database was touched. All 177 tracked branch files were compared against local source and matched before the final reservation-notice fix; that fix also passed CI.

The local host cannot complete Next build because its OS memory-statistics interface is unavailable (`uv_resident_set_memory` ENOENT); the GitHub production build independently passed. No live carrier call, provider dashboard/privacy validation, or Google authorization has been verified. See `docs/verification.md` for evidence.

## Remaining launch blockers

- Live synthetic Twilio → ElevenLabs → backend → database → dashboard call and transfer validation.
- Production identity, roles, account onboarding, tenant/provider credential and agent provisioning.
- Owner acceptance of Google authorization, encrypted credentials, external conflict recovery and worker reconciliation.
- Caller verification before existing-customer lookup or telephone appointment changes.
- Owner acceptance of booking email/reminder delivery; callback completion workflows and urgent alert delivery remain incomplete.
- Billing, detailed usage/cost tracking, production limits, observability/recovery, and retention automation.
- Production deployment and acceptance tests. Current development-only gates remain intentional.

## Guidance

Use README, `docs/hvacline-architecture.md`, and `docs/hvacline-live-validation.md`. Insurance continuation documents are archived as history, not current requirements. Update this note only with verified implementation and results; never store secrets, caller content, or credentials.

## Homepage branding — owner verification pending

The public homepage uses a navy/electric-blue visual system and introduces Line as the AI voice receptionist for HVAC businesses. The October 27 copy update leads with missed-call/job loss, explains live availability and explicit caller confirmation, and uses demo CTAs. Sections follow hero, three-step workflow, services, FAQ and final CTA; metadata targets the same business-owner audience. No performance metrics are asserted. Booking/sign-in links target the customer `/book`, `/login` and `/signup` routes; `/operations` remains a separately protected administrator workspace. The customer routes and draft authentication remain development-only and owner-unverified, not production identity. No tests, builds, linters, type checks, services, browser previews or live checks ran. Full copy, ranked hero options and owner checks are in `docs/homepage-copy.md`; visual-system handoff is in `docs/homepage-branding.md`.

## Browser HVAC implementation — owner verification pending

The protected operations workspace embeds existing WebRTC with the in-memory admin header propagated to authorization, FAQ, end and confirmation requests. Browser drafts include HVAC address, category, preference and hazard fields. Explicit review confirms customer, lead, transcript, HVAC request and audit in the existing idempotent transaction; its replay response includes the same service request ID. No new migration is needed. On-screen booking reuses the scheduling backend after review and preserves a reservation key across identical retries. Hazardous requests enter human attention and cannot self-book.

Demo phone numbers are optional; empty values normalize to absent, nonempty invalid numbers still fail. The seed skips telephone setup without an inbound number and disables transfer when its destination is absent. Existing telephone configuration is not disabled by browser-only seeding. Production identity/customer access and live browser verification remain incomplete. No tests, builds, lint, type checks, migrations or live checks ran for this slice, per owner instruction. Use docs/elevenlabs-agent-setup.md for exact setup and deferred verification.

## Spoken browser booking — implemented, owner verification pending

The browser adapter now registers eight blocking client tools for draft updates, approved FAQs, intake readback/confirmation, actual availability, reservation, appointment confirmation and hold release. Backend-generated readbacks must match the latest agent transcript and be followed by an unambiguous affirmative user turn; an agent-supplied boolean alone cannot save or book. Spoken intake confirmation reuses the existing idempotent customer/lead/intake/HVAC transaction while keeping the voice session live. Booking resolves the confirmed request through its persisted idempotency response and verifies live browser session, actor, tenant and appointment ownership. No migration or second database is added.

Confirmed intakes retain their live concurrency slot until disconnect/expiry; FAQ lookup remains available during the live confirmed session. Disconnect preserves saved requests and appointments. Explicitly released holds use a separate operation that cannot cancel confirmed appointments. Hazard reports block new self-booking and release unconfirmed holds; existing confirmed appointments require human handling. The browser keeps exact save retry payloads and reservation keys in memory and displays backend-confirmed booking receipts. Connection startup now waits for the pinned ElevenLabs SDK's onConnect callback rather than awaiting its void startSession return.

Focused Python, browser-controller and database/API test specifications were added. Source formatting was applied to changed TypeScript/JSON only. No tests, builds, linters, type checks, migrations, seeds, readiness checks, services or live provider calls were run. Provider dashboard setup, effective Render/frontend configuration and successful live browser booking remain unverified. Deployment is left to the owner because main automatically triggers Render builds. Public customer authentication and tenant provisioning remain unfinished; development/privacy gates remain required.

## Provisioned browser agent — website acceptance pending

On October 25, 2026 the owner-authorized ElevenLabs API setup created a separate private HVACLine browser agent with the repository prompt and eight blocking client tools; saved configuration was read back. It retains the selected GPT-4.1 Mini, voice and speech models, requires authentication, limits conversations to 180 seconds with one concurrent and ten daily, disables backup LLM and audio recording, and requests zero-day scheduled deletion. The existing phone agent was not changed. ElevenLabs rejected Zero Retention Mode for the selected LLM, so ZRM remains disabled under the existing fictional-only development policy; this does not satisfy real-customer requirements. Hosting environment wiring, remaining privacy/billing checks and end-to-end website/voice acceptance are unverified.

## Development calendar defaults — owner verification pending

The owner requested using the suggested fictional calendar automatically without entering settings in the operations workspace. The development seed initializes a missing `business_schedules` row for the deterministic development business with booking enabled, America/New_York, ZIP 10001, Monday–Friday 09:00–17:00, 60-minute visits, 120-minute booking/change notice, a 30-day horizon and one Test Team. Initialization validates the existing schema, locks the business, and inserts calendar/audit together. Existing calendars and their versions are preserved; other businesses get no defaults and no appointments are seeded. No schema migration is added. During the owner's subsequent explicit business-content request, the scoped development seed created and enabled this calendar in the configured Neon development database. Automated tests and hosted voice/booking acceptance remain pending. Commands and checks are in `docs/development-calendar-defaults.md`.

## Applied development business content — voice acceptance pending

The owner explicitly requested adding approved FAQs and needed business content to the database. The scoped seed inserted 25 additional FAQs, leaving 28 active seed FAQs in the configured Neon development business. It also created the missing enabled calendar, reused the existing receptionist profile, and excluded all phone-routing changes. Three new FAQ answers were then clarified through the audited, version-checked FAQ service to scope website account/history and browser-memory claims correctly. No customer accounts, service requests, appointments or conversations were fabricated. Unknown prices, fees, warranties, financing, supported equipment and response promises remain staff-only questions. Edited/inactive FAQs are preserved on reseed, and known legacy fallback promises are replaced only when exact default text remains. No migrations, automated checks or live voice sessions ran. Render's effective database branch and complete voice behavior still require owner acceptance. See `docs/development-business-content.md`.

## Customer UI/account draft — owner verification pending

The source includes a navy/blue customer homepage and prominent Line AI booking entry, plus signup/login before booking, scoped server-side proxies, fictional-only account/session services, owned appointment history and migration `20261025_0010_customer_access`. This remains an unfinished, unverified development draft. Mandatory customer MFA and backup-code replacement are now implemented locally but unverified; see `docs/customer-mfa.md`. Email verification, password recovery, tenant onboarding and production account readiness remain incomplete. All existing privacy/development gates remain required. The owner directed earlier publication without verification; publication does not establish runtime, security or deployment success. See ignored `docs/_local/chatgpt-handoff.md` for the continuation state and checks.

## Customer chat — implementation unverified

On October 25, 2026 the owner reported voice working and explicitly said appointment booking had not been tested. This is an owner report, not independent end-to-end verification. The customer booking UI now defaults to silent Chat, with a separate Voice choice and typed messages available in both. The pinned SDK receives `textOnly` for Chat and skips microphone permission. Chat now uses a private signed WebSocket grant; Voice retains its WebRTC grant. The browser agent's saved configuration allows the `text_only` override, retains a voice default/private authentication/eight tools, and includes channel-specific confirmation guidance; its saved settings were read back without starting a live conversation.

Migration `20261025_0011_browser_text_sessions` adds explicit VOICE/TEXT mode and nullable microphone consent with consistency constraints. Existing sessions retain VOICE and existing consent; TEXT is browser-only and records no microphone consent. The shared API continues to require disclosure and fictional-data acknowledgement for both modes. Both reuse the existing approved FAQs, internal calendar, quotas, hazard handling, transcript readback gates and persisted outcomes. The legacy `spoken_confirmation` name remains compatible with typed transcript confirmation. The migration refuses downgrade while text sessions exist.

No migration, tests, builds, linters, type checks or live sessions ran for this feature. Updated schema/backend must precede the frontend deployment. Chat and appointment booking remain unverified; owner commands and manual acceptance are in `docs/customer-chat.md`. No new environment variables or OpenAI key are required. Production identity/privacy and real-customer launch gates remain unresolved.

The owner subsequently reported Chat disconnecting just after startup and interrupting typing. Static review found Chat forced onto the voice transport, missing typing-activity signals and a composer removed outside the active phase. The repair selects signed WebSocket grants for TEXT, validates mode/transport at both frontend boundaries, sends typing activity, keeps unsent messages editable during failure/retry and avoids resetting parent activity on each phase transition. Signed credentials never enter stored provider metadata; an external reference is saved only when supplied by the provider. No new migration/provider configuration was added. A definitive provider close reason and runtime success have not been independently verified. Owner deployment and focused/manual checks remain pending.

The owner then supplied `CONVERSATION_ALREADY_ACTIVE` while Send stayed disabled. Recovery now retains known sessions for cleanup before retry, exposes an explicit release action only for the current actor's own browser session, and supplies a bounded retry delay for conflicts. The existing end route enforces ownership and accepts repeated failed/interrupted cleanup without changing the first failure reason. Late provider grants cannot revive released/expired sessions. Saved requests/bookings and existing quotas remain intact; other users' identifiers and phone-session identifiers are excluded from recovery details. Closing other tabs is still necessary to close their provider connections. No migration, tests, live sessions or database fixes ran for this repair; owner commands/manual checks are in `docs/customer-chat.md`.

The owner's later transcript demonstrates a connected multi-turn Chat, followed by an intake save failure after a standalone confirmation and then a shortened retry readback. Source review confirmed that `confirm` was excluded from accepted replies and that the full exact readback is required. The allowlist now includes explicit standalone confirm variants while retaining the complete-readback gate and rejection of corrections/refusals. Intake validation rejection returns the exact prepared readback with structured retry guidance. Matching browser-agent recovery guidance was saved and its configuration read back. Appointment confirmation remains separate; no booking success, tests or live sessions have been verified for this repair. No new migration or environment changes are required.
