# Operations dashboard

Implementation and runtime acceptance are **unverified**. The owner requested
coding and publication only; no execution checks or services are authorized.

`/operations` opens a sample-data demo. The homepage links to it. Its initial
render uses local fictional fixtures and makes no backend or provider request.
The example schedule is November 12, 2026 in America/New_York; upcoming visits
are evaluated relative to that example day. Demo booking mutations are disabled,
and API dispatch rejects demo actions. Connected editors, calendar integrations,
maintenance labor and browser voice are not mounted in demo mode.

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

1. Open the homepage Dashboard demo link. Visit every visible section without
   connecting; confirm sample labels and no backend/provider/microphone activity.
   Confirm booking and labor changes cannot be made from the demo.
2. Inspect 320/768/1440px and both themes. Verify readable cards, statuses,
   horizontally scrollable tables, wrapped request details and no page overflow.
3. Use keyboard-only navigation: skip link, desktop collapse/expand, mobile drawer
   focus containment, Escape/outside dismissal and trigger focus restoration.
   Resize from an open mobile drawer to desktop; navigation must remain usable.
4. Connect an approved workspace. Confirm invalid-token/network failures have
   clear errors; retry succeeds without losing the entered token. Check actual
   timestamps/timezone, last refresh, empty queues and correctly labeled counts.
5. With authorized sample records, check existing availability/reservation/
   confirmation/cancellation flows, editor updates, scheduling/calendar controls,
   maintenance labor and conditional browser voice. Hazardous requests must
   remain ineligible for automatic booking.
6. Confirm customer-facing home, booking, authentication, pricing and billing
   styles remain intact. No global Tailwind reset or template dependency is added.
