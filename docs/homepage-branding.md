# Homepage branding handoff

## Hero platform badges — 2026-11-09 — UNVERIFIED

Added compact hero badges below the phone link for WebRTC real-time browser
voice, Protected by Google Authenticator, and Secure payments with a Stripe text
wordmark. The payment badge explicitly says Sandbox to match the test-only
checkout. Authenticator wording refers to existing TOTP account protection;
the badge does not change authentication or payment behavior. Shared icons,
theme colors and flexible wrapping support light/dark and narrow screens.

Implementation is local/unpublished and **unverified**. No checks, preview,
services, provider operations or deployment ran. Owner command:
`npm run verify:web`. Manually inspect hero placement, badge wrapping/readability
at desktop/tablet/320px mobile, light/dark contrast, accessible list/icon behavior,
Stripe wordmark and visible Sandbox wording. Existing hero actions and phone
link must remain usable.

## Light/dark theme switch — 2026-11-09 — UNVERIFIED

Added a shared animated sun/moon switch to the homepage, pricing, billing,
booking, sign-in/signup and MFA headers. Customer surfaces use white/charcoal
palettes with the existing orange accents. Pricing cards, account balances,
notices, customer panels, dialogs and billing/pricing loading states use shared
theme colors. Existing charcoal feature panels remain charcoal with readable
light text; the MFA QR code keeps its white background.

The initial theme follows the system preference unless a valid light/dark choice
is saved as `hvacline-theme` in browser local storage. A small static script sets
the root theme before content renders. Switches share the current state, observe
system changes until an explicit choice is made, and synchronize stored changes
between tabs. Storage failures keep the control usable for the current page.
The switch has an accessible Dark mode name/state, a keyboard focus ring, a
44px minimum touch target and disabled animation with reduced motion.
Customer theme styles are scoped to product/customer surfaces.

Implementation is local/unpublished and **unverified**. No tests, builds, lint,
type checks, previews, services or deployment ran. No dependency, backend setting
or migration is needed. Owner command from the repository root:

```sh
npm run verify:web
```

Owner manual checks: switch both directions using mouse/touch/Space/Enter;
confirm the screen reader reports Dark mode on/off. Check desktop/tablet/320px
header spacing and all existing provider/navigation links. Reload directly into
both saved themes and navigate among `/`, `/pricing`, `/billing`, `/book`,
`/login`, `/signup` and `/mfa` without a light-background flash. Inspect cards,
inputs, native selects, loading screens, warnings/errors, dialogs, focus rings,
MFA QR contrast and reduced motion in both themes. With no saved choice, change
the OS preference; then explicitly choose a theme and confirm OS changes no
longer override it. Check another tab, blocked local storage and theme switching
during an existing conversation without losing its state.

## Header pricing label and providers — 2026-11-09 — UNVERIFIED

The homepage navigation label is now Stripe Pricing, still linking to `/pricing`.
Restored the Twilio header SVG at the owner's request; ElevenLabs, Twilio, Telnyx
and WhatsApp are displayed. Changes are local and visual acceptance is pending.
Owner command: `npm run verify:web`. Manually check the label/link, provider
alignment, keyboard focus and absence of header overflow at desktop, tablet and
320px mobile widths; confirm the Twilio symbol has its accessible name.

## ElevenLabs wordmark — 2026-11-09 — UNVERIFIED

The homepage header now displays ElevenLabs as a bold text wordmark in place of
the two-bar symbol, using the existing muted provider color. Implementation is
local; no verification commands, previews or deployment ran. Owner command:
`npm run verify:web`. Manually inspect `/` at desktop, tablet and 320px mobile
widths for readable text, aligned provider symbols, header wrapping and horizontal
overflow; confirm assistive technology reads ElevenLabs once.

The homepage presents HVACLine with the Line AI voice-receptionist identity, electric blue/navy colors, responsive layouts, a matching favicon, and keyboard/reduced-motion support. The October 27 copy update targets HVAC business owners with missed-call/job loss, live appointment availability and caller-confirmed booking. Sections follow hero, three-step workflow, services, FAQ and final CTA. Demo entry points reuse the existing customer booking route. Full copy, three ranked hero options and current owner checks are in `docs/homepage-copy.md`. No performance metrics, reviews or customer counts are invented.

Booking/sign-in links target `/book`, `/login` and `/signup`. These customer routes and their draft authentication remain development-only and owner-unverified; they require the private portal configuration and customer-access migration before use. `/operations` remains a separate protected administrator workspace. Do not give customers the administrator token or treat the customer draft as production authentication.

No tests, builds, linters, type checks, services, browser previews or live checks were run. Source formatting only was applied. The owner should run:

```bash
npm ci
npm run verify:web
```

Manual checks: open `/` at desktop and mobile sizes; follow every navigation/booking link; confirm customer routes require authentication and `/operations` remains separately gated; check keyboard focus, native FAQ expansion, reduced motion, text contrast, fixed-launcher placement and absence of horizontal overflow. Verify the new favicon and page/share titles. No runtime or deployment success is claimed.
