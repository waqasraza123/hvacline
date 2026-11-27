# Operations dashboard

## Business staff workspace — November 26, 2026 — UNVERIFIED

The header now links Staff sign in to `/workspace`. Owner-created businesses,
private staff invitations, password/authenticator sign-in and selected-business
roles use independent staff sessions. Existing public demo/development actor and
customer login remain separate. Migration0030 after pending0029 is UNAPPLIED;
portal defaults off. Setup, limits and exact owner checks:
[Business onboarding](business-onboarding.md). No checks, services, migrations or
sends ran; publication is requested separately from runtime acceptance.

## Staff follow-up and Resend alerts — November 26, 2026 — UNVERIFIED

Connected Follow-up now supports explicit, versioned acknowledge/complete/cancel
controls, owned contact context, loaded-queue filters/search and age. Demo stays
read-only. Staff email settings/history use Resend through a separate disabled
runtime flag and a prospective transactional outbox. Migration0029 is UNAPPLIED;
combined API/job/web deployment requires it. No checks, services, sends, activation
or publication ran. Commands and manual acceptance:
[Follow-up controls](staff-follow-up.md), [Resend staff alerts](staff-email-alerts.md).

## Local redesign — November 25, 2026 — UNVERIFIED

The shared neutral/orange theme, grouped navigation, loaded-queue metrics,
recent-call panel, settings tabs and Recovery layout are implemented locally.
No execution checks, formatters, services, provider operations, publication or
deployment ran. Exact commands and responsive/keyboard/draft checks:
[Web design system](web-design-system.md). This is a presentation change;
existing access and backend behavior remain.

## AI Lead Recovery — source UNVERIFIED

AI Lead Recovery now has dedicated header/sidebar access, a prominent overview
card and a public `/ai-lead-recovery` demo. The overview's prominent **Try
Yourself** link opens this dedicated page in the dashboard shell; connected
workspaces retain their in-place recovery action. The homepage recovery teaser
was removed at the owner’s request; shared navigation still links to the demo. Legacy `/lead-recovery` URLs redirect
to the new route, retaining the setup option. Its 24 fictional opportunities and
interactive follow-up/booking simulation stay separate from authenticated live
data. AI Provider Settings store encrypted text-model credentials; recovery SMS
and dedicated ElevenLabs voice delivery now have consent-gated source adapters,
signed callbacks, scoped booking continuation, expiry/history and protected
provider reconciliation. All flags remain off; configured status is not live
acceptance. Migration0027 (after0026) must precede API/job deployment. No checks,
new migration or provider requests ran for this follow-up.
Exact source manifest, setup, owner commands, limits and acceptance:
[AI Lead Recovery](ai-lead-recovery.md).

Implementation and runtime acceptance are **unverified**. The owner requested
coding and publication only; no execution checks or services are authorized.

`/dashboard` opens a sample-data demo for all visitors without sign-in. The
shared desktop navbar and mobile menu offer Dashboard, Try Stripe Checkout and AI Recovery; Calling has
been removed from both. The dashboard's initial
render uses local fictional fixtures and makes no backend or provider request.
The example schedule is November 12, 2026 in America/New_York; upcoming visits
are evaluated relative to that example day. Ordinary demo booking mutations are disabled,
and API dispatch rejects demo actions. Recovery uses only its separate local simulation.
Connected editors, calendar integrations,
maintenance labor and browser voice are not mounted in demo mode.

The shared top navigation marks only the current pathname with a still orange dot and
active styling. Home and other unmatched routes have no selected destination.
Desktop/mobile and browser back/forward follow the router. The dot has no pulse animation.

GoHighLevel and AI Lead Recovery follow the overview metrics and queue panels.
GoHighLevel retains its own named
sidebar entry with a CRM badge. The underlying section key remains `integrations`;
older setup guides referring to Integrations mean this GoHighLevel entry.
The feature card highlights contact/opportunity sync, GHL calendar booking and
contact summaries, with direct actions to explore or manage the connection.
Demo visitors can open the existing read-only demo or enter the administrator
connection flow; the latter returns to GoHighLevel after authentication.

The overview card makes no requests in demo mode. In a connected workspace it
reads the existing administrator-protected GHL status endpoint on mount and when
workspace data refreshes. Loading, unavailable, disabled, not-connected, paused,
error and active states remain distinct. Active describes saved connection
configuration, not a newly verified provider call or an enabled calendar/note
feature. No backend, credentials, provider settings or permissions change.

The Integrations section now has a separate optional read-only GoHighLevel demo.
It requests the API's public aggregate projection when that section opens;
credentials remain on the API server. The other sections still use local samples.
Setup, limits, exact owner commands and manual acceptance:
[GoHighLevel public demo](gohighlevel-public-demo.md). Previously recorded focused
public-demo checks passed43 cases; no checks were rerun during the staged-source
history merge. Hosted setup and live acceptance remain unverified; the demo is
disabled until its dedicated credentials are configured.

Connect your workspace replaces the demo with the existing in-memory admin-token
gate. Returning to the demo clears that token. Connected mode retains the
existing development endpoints, controls and ownership checks. No new production
identity or dependency is introduced by the original dashboard layout. The
GoHighLevel follow-up adds its own opt-in public read endpoint and environment
configuration without a schema change.

The TailAdmin AppSidebar, AppHeader, EcommerceMetrics and RecentOrders patterns
are adapted into local typed navigation, cards and semantic tables. Their MIT
notice is retained beside the dashboard source. Styling uses CSS Modules and
HVACLine's orange/charcoal palette; the existing theme preference controls both
the dashboard and its portaled mobile drawer. Radix Dialog provides modal focus
containment, Escape/outside dismissal and focus restoration. Responsive sidebar
collapse and the mobile drawer share the same section definitions.

Overview shows loaded calls, service requests, all loaded confirmed bookings,
and open follow-up. Upcoming appointments are sorted by start time as of the
last refresh; only five appear on Overview. Recent conversations shows the five
latest loaded received calls, not browser conversation history. Needs attention shows up to two
hazard handoff requests and four open callbacks/transfers, with navigation to the
full loaded queues. Counts are explicitly capped by the existing API's latest
100 records per queue; they are not historical analytics or unique-customer
counts. Missing customer joins use a neutral label. No sample revenue or growth
charts are added. Follow-up completion now uses the existing audited backend
transitions; see the current follow-up guide above.

Owner command for later execution, only when authorized:

```bash
npm run verify:web
```

Manual acceptance:

1. While signed out, open Dashboard from the top navbar and mobile menu;
   confirm `/dashboard` opens without sign-in. Repeat while signed in.
   Visit every visible section without
   connecting; confirm sample labels and no backend/provider/microphone activity
   outside the optional read-only GoHighLevel Integrations section.
   Confirm booking and labor changes cannot be made from the demo.
   Follow the recovery overview's **Try Yourself** link and confirm the URL is
   `/ai-lead-recovery` with the dashboard sidebar and full fictional recovery
   demo. In a connected workspace, confirm Open AI Lead Recovery keeps the
   authenticated workspace and opens its recovery section.
   Confirm the GoHighLevel feature appears after overview metrics/queue panels and the named
   sidebar item opens the same section. Test Explore GoHighLevel and Connect your
   workspace; the latter must require the admin token and open GHL after sign-in.
   The overview feature itself must make no public-demo or administrator requests
   in demo mode; the public read-only fetch occurs only on entering GoHighLevel.
   The top-right Staff sign in link must open `/workspace`.
2. Inspect 320/768/1440px and both themes. Verify readable cards, statuses,
   horizontally scrollable tables, wrapped request details and no page overflow.
   On the homepage, confirm no navigation destination is selected. Confirm
   Calling is absent. Open Try Stripe Checkout and Dashboard; the still orange
   marker must follow the current pathname. Repeat in the mobile menu, with
   keyboard navigation, browser back/forward and reduced motion.
3. Use keyboard-only navigation: skip link, desktop collapse/expand, mobile drawer
   focus containment, Escape/outside dismissal and trigger focus restoration.
   Resize from an open mobile drawer to desktop; navigation must remain usable.
4. Connect an approved workspace. Confirm invalid-token/network failures have
   clear errors; retry succeeds without losing the entered token. Check actual
   timestamps/timezone, last refresh, empty queues and correctly labeled counts.
   Check the GHL feature's loading/unavailable/disabled/disconnected/paused/error/
   active states. Its status request must use the existing admin protection and
   never trigger a provider call. Check the feature card and sidebar badge on
   mobile, desktop, collapsed navigation and both themes.
5. With authorized sample records, check existing availability/reservation/
   confirmation/cancellation flows, editor updates, scheduling/calendar controls,
   maintenance labor and conditional browser voice. Hazardous requests must
   remain ineligible for automatic booking.
6. Review customer-facing home, booking, authentication, pricing and billing
   against the shared design guide and confirm existing interactions remain. No global Tailwind reset or template dependency is added.

## Canonical Dashboard route — November 27, 2026 — UNVERIFIED

The canonical dashboard URL is `/dashboard`, including every nested destination.
Homepage/header links, navigation state, breadcrumbs, titles, public README links,
current guides and regression expectations use this path. The actual Next page
lives under `app/dashboard/[[...path]]`. The Next configuration permanently
redirects `/operations` and `/operations/:path*` to the matching Dashboard path,
retaining query parameters. Existing backend operations endpoints and internal
feature-module paths keep their established names and contracts.

No execution checks ran. In addition to the checks below, manually open
`/operations`, `/operations/calls` and
`/operations/scheduling/rules?example=1`; confirm they redirect to `/dashboard`,
`/dashboard/calls` and `/dashboard/scheduling/rules?example=1`. Check that the
public header selects Dashboard on nested dashboard pages and remains unselected
on unrelated routes. Deployment or a restart of the owner's existing web process
is needed to load the changed Next configuration.

## URL navigation — November 27, 2026 — UNVERIFIED

Dashboard destinations now use shareable `/dashboard/...` paths. A validated
optional catch-all page serves direct visits and refreshes; unknown paths and
flag-disabled browser voice paths return not found. The central navigation module
maps existing section keys to paths and labels. Sidebar links, overview metrics,
queue shortcuts and feature actions update the URL. Native History navigation
integrates with Next pathname updates and preserves the mounted workspace's
in-memory connection and loaded records during section changes. Back/Forward
selects the matching section. Ordinary anchors retain new-tab/modifier-click
behavior. Credentials are never serialized into URLs or browser storage.

| Destination | URL |
| --- | --- |
| Overview | `/dashboard` |
| Calls | `/dashboard/calls` |
| Leads and requests | `/dashboard/requests` |
| Appointments | `/dashboard/appointments` |
| Follow-up overview | `/dashboard/follow-up` |
| Follow-up queue / email alerts | `/dashboard/follow-up/queue`, `/dashboard/follow-up/alerts` |
| Recovery | `/dashboard/recovery` |
| Multilingual voice | `/dashboard/voice-languages` |
| Knowledge | `/dashboard/knowledge` |
| Agent settings | `/dashboard/agent-settings` |
| General / voice settings | `/dashboard/agent-settings/general`, `/dashboard/agent-settings/voice` |
| Browser voice (feature gated) | `/dashboard/browser-voice` |
| Scheduling overview | `/dashboard/scheduling` |
| Calendar connections / availability and teams | `/dashboard/scheduling/calendars`, `/dashboard/scheduling/rules` |
| GoHighLevel | `/dashboard/integrations/gohighlevel` |
| Maintenance / websites | `/dashboard/maintenance-hours`, `/dashboard/websites` |

Active sections reveal nested sidebar links and a horizontal section navigation.
Breadcrumbs link back to the dashboard and current section, with the current page
marked accessibly. General/Voice settings and scheduling panels stay mounted
between their subpages to retain drafts. Demo subpages remain read-only and show
setup guidance where live configuration is required. Public `/ai-lead-recovery`
and `/multilingual-ai-voice` entry points still open their original demos; further
navigation adopts the canonical Dashboard paths. A full reload or new tab still
starts the sample-data demo: connected administrator state remains memory-only.

No tests, builds, linters, type checks, services or other execution checks ran.
Implementation, browser history, accessibility and visual acceptance are
**UNVERIFIED**. Owner commands from the repository root:

```sh
npm run test:web -- src/features/operations/dashboard-navigation.test.ts src/features/operations/dashboard.test.tsx src/components/ui/settings-tabs.test.tsx src/app/page.test.ts src/features/customer/auth-continuation.test.ts
npm run typecheck:web
npm run lint:web
npm run build:web
```

Manual checks on the owner's running application:

1. Visit every URL above directly and refresh it. Check its heading, selected
   navigation and breadcrumbs. Unknown `/dashboard/unknown` must return not found;
   browser voice must remain unavailable when its existing flag is off.
2. Click sidebar links, metric cards, View/Review actions and overview feature
   actions. Confirm each destination changes the address bar. Use Back/Forward
   across sections and nested pages. Open links in new tabs with modifier-click.
3. Open General/Voice settings in a connected development workspace. Edit a draft,
   switch through nested links, settings tabs and Back/Forward, and confirm the
   draft remains. Repeat for availability rules and calendar subpages. Leaving
   the whole section retains the existing editor unmount behavior.
4. Confirm section navigation retains the connected workspace without another
   sign-in; a new tab/full reload must reset to demo. Check no credential enters
   the URL and demo navigation never enables live mutations.
5. At phone and desktop widths, in both themes, inspect nested links, sidebar
   collapse, mobile drawer closing, long breadcrumb wrapping and visible keyboard
   focus. Use Tab/Enter and the settings tabs' arrow/Home/End keys. Click ancestor
   breadcrumbs to return to their section/dashboard.
