# Project State

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

## Configured database billing schema at0020 — verified — 2026-11-09

Owner-authorized bounded operation using published6b2bbad migration source and
existing confirmed configuration finds20261108_0020 before and after, matching
source head. Runtime/direct targets and roles match. All five billing tables and
customer-account ownership uniqueness exist. No upgrade was needed; no pending
migration remains for this configured database. Approved network escalation
completed readback after sandbox connection failure. No schema/data mutation,
seed, downgrade or customer-row access occurred. Payment/application runtime,
Stripe configuration and deployment acceptance remain separate/pending.

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

## Automatic billing business resolution — implementation UNVERIFIED — 2026-11-09

Billing derives ownership from the authenticated customer's persisted account;
administrator labor uses the existing authenticated actor's business. Removed
BILLING_MERCHANT_AGENCY_ID from settings/startup/readiness and added account/business
matching when locking billing rows. Existing customer/MFA, admin authentication,
appointment ownership, composite foreign keys, saved Stripe customer binding and
sandbox-only restrictions remain. No additional migration or dependency beyond
the original billing feature. Regression specifications are unexecuted.

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
