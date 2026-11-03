# Simplified homepage and voice AI hero — UNVERIFIED

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
