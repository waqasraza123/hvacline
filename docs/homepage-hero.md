# Simplified homepage and voice AI hero — UNVERIFIED

## Try Voice Chat is primary — November 9, 2026 — UNVERIFIED

The hero now clearly offers Try Voice Chat as its primary action and explains
that visitors speak in the browser after sign-in. Header and floating-launcher
actions use the same wording and link directly to `/book`. The homepage card
retains its Voice chat default; the customer workspace now defaults to Voice
chat too, with Text chat still available before starting. Callback and inbound
phone choices remain separate secondary hero actions.

AI disclosure and microphone consent stay unchecked. Navigation does not request
microphone access, start a provider connection or place a phone call. Existing
session mode locks, text handoff/drafts and confirmations remain. No migration,
environment or provider change is required. Source is local/unpublished and
runtime-unverified; no tests/builds/lints/type checks, services or live sessions
ran. Owner command: `npm run verify:web`. Manually check hero/header/launcher
links, sign-in/MFA continuation, Voice default, consent/start/denied-mic behavior,
silent Text chat, preserved drafts, active-session mode lock, callback separation
and desktop/mobile light/dark layouts.

## Mobile verification — November5,2026 — UNVERIFIED

Callback source adds a separate opt-in SMS verification step for a US
mobile number before call consent/submission. Changing the number clears proof
and consent; code expiry and known proof rejection require verification again.
Sign-in still requires authenticator MFA. Hosted activation/migration/provider
setup and all execution checks remain pending. See
[Public demo release](public-demo-production-readiness.md) for exact owner commands
and mobile, keyboard, expiry and recovery checks.

## Public callbacks — November 5, 2026 — UNVERIFIED

Signed-in visitors with completed authenticator MFA can use the website callback
path under `consented_us` once hosted gates and real outbound acceptance are in
place. Transfer is optional and remains off for this policy. UI copy no longer
describes every request as an owner-approved private preview. Known US destination
errors allow correction with renewed consent. Sign-in, callback continuation and
unknown-outcome recovery remain in place. Source/runtime are unverified; hosted
flags have not been changed. Exact activation settings, commands and manual
checks: [Public callbacks](public-callbacks.md).

## Callback sign-in requirement — November 4, 2026 — UNVERIFIED

The callback CTA now asks signed-out visitors to sign in before showing phone,
scenario or consent fields. Existing customer login/signup and required MFA carry
a fixed `demo-call` intent, returning to `/?demo_call=1` to reopen the modal.
Ordinary sign-in still returns to `/book`; arbitrary redirect URLs are ignored.
Returning/opening the modal only checks availability and never submits a call.

The Next callback bridge revalidates the existing customer session on availability,
status and submission. Missing/expired sessions get401 `CALLBACK_SIGN_IN_REQUIRED`;
unavailable session verification fails closed with503. Existing pending request
keys/locks survive sign-in; status denials never claim a call was not created.
This supersedes anonymous form preview. Signed-in previews remain subject to the
existing website/policy gates; no outbound activation or provider setting changed.

Regression specifications added, unexecuted. Owner commands with Node24:

```sh
npm run test:web -- src/app/api/outbound-demo/route.test.ts src/features/customer/auth-continuation.test.ts 'src/app/api/account/[action]/route.test.ts'
npm run typecheck:web
npm run build:web
```

Manual: signed-out hero/Calling buttons show sign-in before phone fields; login,
signup, MFA enrollment/verification/recovery and cancellation retain callback
intent; successful sign-in reopens the form without dialing. Normal login still
goes to `/book`. Check unavailable/expired sessions, Tab/Escape/focus, and saved
call recovery across sign-in. Direct unsigned GET/POST must never reach dialing;
with gates off, signed-in users still cannot submit calls. No checks ran locally.

## Calling announcement removal — November 4, 2026

Owner requests removing the dated calling announcement and proceeding with an
outbound rollout. Source removes the hero banner and all November5/date references
from homepage, Calling section, dialog fallback and disabled bridge responses.
The obsolete shared date/component/styles are removed. The demo CTA/modal remains;
unavailable submission uses current-availability wording without claiming Live
calling. No calling flags or admin-only policy are bypassed. Hosting access and
owner selection of admin-only versus visitor calling remain pending. The earlier
policy/modal commit048ff2f is pushed; this removal is a follow-up.

Use the owner commands and manual checks below; no verification command ran.
Also confirm the removed announcement/date no longer renders, and unavailable
form/bridge responses make no date or successful-call claim.

## Hero demo-call modal — November 4, 2026

The hero now includes **Request an AI demo call**. This and the Calling section
open one shared Radix Dialog (`@radix-ui/react-dialog`1.2.0), styled with the
existing orange/charcoal palette. Desktop uses an agent introduction beside the
phone/scenario/explicit-consent form; mobile uses a stacked scrollable layout.
Radix supplies the modal behavior; initial phone focus and focus restoration to
the clicked trigger are explicit. Closing preserves in-memory drafts, pending
requests and status recovery. Only the existing request key enters session storage.

The form can be filled while calling is disabled. Submission stays disabled with
an honest coming-soon message; browser Voice remains available. Existing website
activation gates, allowlist requirements and admin-only `consented_us` policy
are unchanged. Opening/filling/dismissing the modal does not initiate a call.
No provider/backend settings or feature flags were changed.

Manifest and lockfile were updated using npm lockfile-only mode with lifecycle
scripts disabled. No tests, builds, linters, type checks, services, browser preview,
deployment or calls ran; implementation/rendering remain **UNVERIFIED**.

Owner commands with Node24, **not run**:

```sh
npm ci
npm run test:web -- src/app/api/outbound-demo/route.test.ts
npm run typecheck:web
npm run build:web
```

Manual: at320px/390px, desktop and200% zoom, open from both triggers; check phone
focus, Tab/Shift+Tab containment, Escape/close/outside dismissal, return focus,
scroll lock, mobile keyboard and no overflow. Fill and close/reopen: draft and
consent stay in memory. With calling disabled, Enter/click must never POST a call.
Using mocked requests, check one POST on double-click, close during submission,
reopen/reload status recovery, unknown lock, and correction/renewed consent after
a certified pre-creation rejection. Closing must never redial or clear recovery.

## Earlier browser Voice homepage work

The October 31 owner request removes the public business phone number and makes
browser voice AI the hero's main action. The hero now has shorter copy, fewer
links and a larger Line card that opens on Voice AI. Text chat remains available
through a separate choice in the same card; its guest allowance, disclosure,
sign-in dialog and conversation handoff are preserved.

Start voice chat opens the existing `/book` flow. Visitors sign in and choose
Voice there; the homepage does not start a session or request microphone access.
The phone-status page no longer receives or renders the configured number or a
dial link. Existing sandbox/configuration gates and backend telephone behavior
remain in place. Customer contact information in authenticated booking and
Operations workflows is outside this public-number presentation change.

The old homepage phone parser and its obsolete release-gate specifications were
removed. `HOMEPAGE_PHONE_NUMBER_E164` and `TELNYX_INBOUND_CALLING_VERIFIED` no longer
affect the homepage and can be removed from the frontend hosting configuration.
No backend, schema, dependency or provider configuration change is required.

Source formatting only. No tests, builds, linters, type checks, services, browser
previews or deployments ran. Implementation and rendering are **UNVERIFIED**.

Owner command, from `/Users/mc/development/hvacline`:

```sh
npm run verify:web
```

Manual checks after the owner starts or deploys the frontend:

1. Inspect `/` at 320px, 390px, tablet and desktop widths, and at 200% zoom.
   Check readable headings, card sizing and no horizontal overflow.
2. Confirm Voice AI is selected initially and Start voice chat is the primary
   action. Header Try Line and the floating launcher should scroll to the card
   and focus its current action. Check visible keyboard focus and reduced motion.
3. Follow Start voice chat through existing login/MFA to `/book`, choose Voice,
   and check that microphone access requires explicit consent. Opening the
   homepage or selecting Voice AI must never start recording or a provider call.
4. Select Text chat, try a suggested question and send once with disclosure.
   Check the reply, second-message sign-in dialog, dismissal/focus and same-tab
   continuation. Switching the card modes must preserve the draft and reply.
5. Confirm no public business number or `tel:` link appears on `/`, including
   with old phone-CTA settings still configured. With the existing sandbox gate
   enabled, check `/phone-demo` also omits the number and dial link and retains
   its status display and browser booking link.

The owner authorized publication to `main` on October 31. Hosting deployment
and runtime acceptance remain unverified; no deployment command was requested.
## GoHighLevel hero badge — 2026-11-13

The hero adds GoHighLevel with the qualifier `CRM sync · Preview`, alongside
existing feature badges. Shared wrapping, theme and responsive styles are reused.
The badge does not claim live acceptance; GHL defaults off pending setup and
owner verification. No tests/builds/browser checks ran. Owner command:
`npm run verify:web`; manually inspect badge wrapping at320/390/768/1440px in
both themes, screen-reader labeling and the existing Voice/calling actions.

