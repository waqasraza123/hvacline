# Simplified homepage and voice AI hero — UNVERIFIED

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
