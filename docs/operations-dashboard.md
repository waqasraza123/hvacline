# Operations dashboard

## AI Lead Recovery — source UNVERIFIED

AI Lead Recovery now has dedicated header/sidebar access, a prominent overview
card and a public `/ai-lead-recovery` demo. The overview's prominent **Try
Yourself** link opens this dedicated page in the dashboard shell; connected
workspaces retain their in-place recovery action. The homepage shows only a
compact introduction and the same link. Legacy `/lead-recovery` URLs redirect
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

`/operations` opens a sample-data demo for all visitors without sign-in. The
shared desktop navbar and mobile menu offer Dashboard, Pricing and AI Recovery; Calling has
been removed from both. The dashboard's initial
render uses local fictional fixtures and makes no backend or provider request.
The example schedule is November 12, 2026 in America/New_York; upcoming visits
are evaluated relative to that example day. Ordinary demo booking mutations are disabled,
and API dispatch rejects demo actions. Recovery uses only its separate local simulation.
Connected editors, calendar integrations,
maintenance labor and browser voice are not mounted in demo mode.

The shared top navigation initially marks Dashboard with a green dot and a short
pulse. Selecting another item moves the dot and active styling to that item;
desktop and mobile share the selection. Browser back/forward and hash navigation
update the selection. Reduced-motion preferences keep a still green dot.

GoHighLevel is featured below AI Lead Recovery and above the overview queue cards, with its own named
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
[GoHighLevel public demo](gohighlevel-public-demo.md). This follow-up remains
unverified and is disabled until its dedicated demo credentials are configured.

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

Overview shows loaded calls, service requests, upcoming confirmed appointments,
and open follow-up. Upcoming appointments are sorted by start time as of the
last refresh; only five appear on Overview. Needs attention shows up to two
hazard handoff requests and four open callbacks/transfers, with navigation to the
full loaded queues. Counts are explicitly capped by the existing API's latest
100 records per queue; they are not historical analytics or unique-customer
counts. Missing customer joins use a neutral label. No sample revenue or growth
charts are added. Follow-up completion is not implemented by this UI slice.

Owner command for later execution, only when authorized:

```bash
npm run verify:web
```

Manual acceptance:

1. While signed out, open Dashboard from the top navbar and mobile menu;
   confirm `/operations` opens without sign-in. Repeat while signed in.
   Visit every visible section without
   connecting; confirm sample labels and no backend/provider/microphone activity
   outside the optional read-only GoHighLevel Integrations section.
   Confirm booking and labor changes cannot be made from the demo.
   Follow the recovery overview's **Try Yourself** link and confirm the URL is
   `/ai-lead-recovery` with the dashboard sidebar and full fictional recovery
   demo. In a connected workspace, confirm Open AI Lead Recovery keeps the
   authenticated workspace and opens its recovery section.
   Confirm the GoHighLevel feature appears above overview metrics and the named
   sidebar item opens the same section. Test Explore GoHighLevel and Connect your
   workspace; the latter must require the admin token and open GHL after sign-in.
   The overview feature itself must make no public-demo or administrator requests
   in demo mode; the public read-only fetch occurs only on entering GoHighLevel.
   The top-right Phone receptionist link must open the homepage Calling section
   (`/#call-me`), rather than the sandbox-gated `/phone-demo` route.
2. Inspect 320/768/1440px and both themes. Verify readable cards, statuses,
   horizontally scrollable tables, wrapped request details and no page overflow.
   On a fresh homepage load, confirm Dashboard shows the green pulsing dot before
   any interaction. Confirm Calling is absent. Select Pricing and Dashboard;
   confirm the active marker moves
   on navigation. Repeat with the mobile menu and keyboard, check browser back/
   forward, and enable reduced motion to confirm the dot stays visible and still.
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
6. Confirm customer-facing home, booking, authentication, pricing and billing
   styles remain intact. No global Tailwind reset or template dependency is added.
