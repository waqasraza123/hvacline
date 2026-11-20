# Operations dashboard

Implementation and runtime acceptance are **unverified**. The owner requested
coding and publication only; no execution checks or services are authorized.

`/operations` opens a sample-data demo for all visitors without sign-in. The
shared desktop navbar and mobile menu offer Dashboard and Pricing; Calling has
been removed from both. The dashboard's initial
render uses local fictional fixtures and makes no backend or provider request.
The example schedule is November 12, 2026 in America/New_York; upcoming visits
are evaluated relative to that example day. Demo booking mutations are disabled,
and API dispatch rejects demo actions. Connected editors, calendar integrations,
maintenance labor and browser voice are not mounted in demo mode.

GoHighLevel is featured above the overview queue cards and has its own named
sidebar entry with a CRM badge. The underlying section key remains `integrations`;
older setup guides referring to Integrations mean this GoHighLevel entry.
The feature card highlights contact/opportunity sync, GHL calendar booking and
contact summaries, with direct actions to explore or manage the connection.
Demo visitors can open a static workflow preview or enter the administrator
connection flow; the latter returns to GoHighLevel after authentication.

The overview and static workflow preview make no requests in demo mode. In a
connected workspace the overview reads the existing administrator-protected GHL
status endpoint on mount and workspace refresh. Loading, unavailable, disabled,
not-connected, paused, error and active states remain distinct. Active describes
saved connection configuration, not newly verified provider health or enabled
calendar/note features. No backend, credentials or permissions change.

The shared top navigation initially marks Dashboard with a green dot and a short
pulse. Selecting another item moves the dot and active styling to that item;
desktop and mobile share the selection. Browser back/forward and hash navigation
update the selection. Reduced-motion preferences keep a still green dot.

The public GoHighLevel section also reads the optional live aggregate projection
from a dedicated fictional-data sub-account. It shows pipeline/stage names,
opportunity counts and the successful-read timestamp above the static workflow
preview. Credentials and record IDs remain server-side; no admin sign-in is
required to view the aggregate demo. Disabled/error/empty states remain explicit.
Setup and43 passing focused checks: [public demo guide](gohighlevel-public-demo.md).

Connect your workspace replaces the demo with the existing in-memory admin-token
gate. Returning to the demo clears that token. Connected mode retains the
existing development endpoints, controls and ownership checks. No new production
identity, backend API, schema, environment variable or dependency is introduced.

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
   connecting; confirm sample labels and no backend/provider/microphone activity.
   Confirm booking and labor changes cannot be made from the demo.
   Confirm the GHL feature leads the overview without requests in demo mode.
   Its named sidebar entry opens the public aggregate data card and static
   workflow preview. Only the credential-free public demo endpoint is fetched;
   private/admin status endpoints must not be requested by demo visitors.
   Connect your workspace must require the admin token and return to GoHighLevel.
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
   Review GHL loading/unavailable/disabled/disconnected/paused/error/active states
   and workspace refresh. Check the card/sidebar on mobile, desktop, collapsed
   navigation, keyboard and both themes. Status reads must remain admin-protected
   and must not perform a provider request.
5. With authorized sample records, check existing availability/reservation/
   confirmation/cancellation flows, editor updates, scheduling/calendar controls,
   maintenance labor and conditional browser voice. Hazardous requests must
   remain ineligible for automatic booking.
6. Confirm customer-facing home, booking, authentication, pricing and billing
   styles remain intact. No global Tailwind reset or template dependency is added.
