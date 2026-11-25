# Web design system

Local frontend implementation, November 25, 2026. **UNVERIFIED**: no tests,
builds, linters, formatters, type checks, browser checks or services ran. No
dependencies, providers, backend, native app, publication or deployment changed.

## Shared presentation

`apps/web/src/app/design-tokens.css` supplies neutral light/dark colors, orange
accents, status colors, typography, spacing dimensions and radii. Existing
`--customer-*` and internal aliases map to those tokens within application
shells. `interface.css` styles existing controls, focus rings and internal forms.
Both are loaded by the root layout. Color scheme and application styling are
scoped to the product, customer, operations, settings, voice and phone shells;
published website templates retain their separate theme variables and styling.

Primary actions use charcoal/light foreground inversion; orange identifies
selection and supporting accents. The homepage closing action remains orange
on its fixed dark panel. Error, warning and confirmed states retain distinct
text and semantic colors. Customer booking receipts and warnings use theme-aware
colors; the QR code retains its existing white background.

`components/ui` contains page headers, panels, metrics, badges, empty/loading
states and settings tabs. Settings panels stay mounted when hidden, preserving
drafts while moving between General and Voice & Languages. Tabs use a single
tab stop with Left/Right/Home/End keyboard selection and linked panel IDs.
Cancel changes restores the latest loaded/saved values without a request.
Leaving Agent settings still follows the existing workspace mounting behavior;
this change does not add draft storage across sections, navigation or reloads.

## Surfaces

- Operations keeps its existing section keys and controls, grouped into Workspace,
  AI Configuration and Business. Desktop collapse and the mobile Radix drawer
  share navigation definitions; browser voice remains conditional. The header
  links My account to `/book` and keeps theme and live/demo state visible.
- Overview places loaded-queue metrics before upcoming visits, attention items,
  recent calls and Recovery/GHL entries. Confirmed bookings counts all confirmed
  records in the loaded queue; upcoming visits additionally filter by refresh
  time. Recent calls sorts only loaded received calls and shows at most five.
  Counts are not all-time analytics; no transcript or browser history is added.
- Recovery uses shared metric cards, horizontally scrollable tables, filters,
  selected-case highlighting and a fictional lead timeline. Simulated booking
  confirmation has a distinct status announcement. Live metrics, permission,
  assignment, retry and provider controls retain their existing request logic.
- Homepage/guest chat and shared marketing navigation use the same colors and
  controls. The six feature captions, preview/sandbox labels, hero actions and
  existing removal of the phone/workflow/recovery sections are retained.
- Customer authentication, booking navigation, appointments, memory, MFA and
  details use consistent typography and surfaces. Authentication, MFA, consent,
  active-conversation navigation guards, booking confirmation and retry behavior
  retain their existing implementation.

## Owner commands

Run from `/Users/mc/development/hvacline` when ready. None ran here.

Focused new/related regression source:

```sh
npm run test:web -- src/components/ui/settings-tabs.test.tsx src/features/operations/dashboard.test.tsx src/features/recovery/demo-panel.test.tsx src/features/recovery/demo.test.ts src/features/receptionist/settings-form.test.ts src/app/page.test.ts
```

Full existing web checks, including formatting, lint, types, tests and build:

```sh
npm run verify:web
```

There are no migrations or installation requirements for this redesign.

## Owner manual acceptance

1. Inspect `/`, `/operations`, `/ai-lead-recovery`, `/multilingual-ai-voice`,
   `/pricing`, `/login`, `/signup`, `/mfa`, `/book` and `/billing` at 320, 390,
   640, 768, 1024, 1280 and 1920px, with 200% zoom, both themes and reduced
   motion. Check text contrast, control boundaries, readable badges, focus rings,
   wrapping, dialog clearance and absence of page overflow. Tables may scroll
   horizontally within their labeled regions. Visual/contrast acceptance has
   not been measured.
2. Use keyboard only: skip link, sidebar collapse, every navigation destination,
   mobile drawer containment/Escape/dismissal/trigger focus return, then resize
   an open drawer to desktop. Confirm pathname-based marketing selection; home
   has no active destination. The indicator is a still orange dot.
3. In the public dashboard, confirm demo labeling and existing disabled mutations.
   Overview counts must match loaded records; past confirmed bookings count in
   the metric but not upcoming visits. Recent calls must show the latest five
   loaded calls, and empty queues must not receive invented samples. Recovery
   and GHL entries follow those queues; account links open `/book`.
4. In Recovery Demo Mode, filter/select leads and confirm the selected row/details
   agree. Follow a scheduled case through simulated follow-up, YES, slot choice
   and explicit confirmation. Confirm the selected timeline excludes other cases,
   the receipt says fictional, metrics update locally, STOP suppresses the case
   and Reset restores the demo. Repeat with keyboard and a narrow viewport.
   Demo actions must not contact providers or persist bookings.
5. With an approved administrator workspace, inspect live loading/error/empty
   states and selected-case details. Confirm actual records never fall back to
   demo data. Inspect saved status and provider availability without sending
   contact or enabling automation. Provider/write acceptance belongs to the
   separate feature runbooks and needs its own authorization.
6. In Agent settings, edit General, switch to Voice & Languages, edit a voice
   draft, then return to each tab. Both drafts must remain. Test Left/Right and
   Home/End, panel labels and focus. Cancel changes must restore that panel's
   last saved values without a request. With authorized sample writes, confirm
   saved values, version conflicts and error recovery; language settings must
   still distinguish configuration from provider availability.
7. Confirm homepage badges/calling links, callback dialog, Voice/Text selection,
   guest drafts and sign-in continuation remain usable. Check customer password
   visibility, MFA/QR, appointment filters/details, memory controls and booking
   status colors. Inspect existing active-conversation navigation guards and
   draft/retry behavior without initiating a paid session just for visual review.
8. Inspect one existing published website template in both themes to confirm its
   layout/theme are retained. Native app acceptance is outside this web slice.

Record owner results before changing the **UNVERIFIED** status. Publication and
deployment are separate from this local implementation.
