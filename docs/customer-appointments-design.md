# Customer appointments redesign — UNVERIFIED

My appointments now uses the customer orange/charcoal design: a next-confirmed-visit card, date tiles, start/end times, clear status badges, Upcoming/History/All filters and a sidebar for stored booking counts, server-provided limits and guidance. The workspace heading changes with the tab. The existing booking details/rescheduling modal and its ownership, quotas, confirmation and retry rules remain unchanged.

The existing appointments API supplies every booking. The list does not invent service categories, addresses, technician assignments or completion evidence; those supported details stay in the existing modal. Confirmed past visits are labelled “Past appointment,” an ongoing scheduled window is “Scheduled now,” and holds are never counted as confirmed bookings. Hold/visit boundaries update local presentation, while focus/manual refresh reloads stored status. Counts describe the bookings returned for this view, not a claim about lifetime history. Dates use the returned business timezone with the existing UTC fallback for null. Invalid dates/timezones show a load error instead of breaking formatting.

No backend, schema, environment variable, dependency or provider change. Source formatting only; no tests, builds, linters, type checks, services, migrations, installs, browser previews or deployments ran. Implementation/runtime remain **UNVERIFIED**.

Owner commands from the active checkout:

```sh
cd /private/tmp/hvacline-browser-demo
npm run test --workspace @insurance-operations/web -- src/features/customer/appointments-model.test.ts src/features/customer/booking-details.test.ts src/features/customer/booking-limits.test.ts 'src/app/api/v1/development/[...path]/route.test.ts'
npm run verify:web
```

Deploy the frontend after acceptance; this redesign needs no Render deployment. Manually check desktop and 320px mobile widths, keyboard focus and filters; empty/loading/retry/session-expired states; upcoming/in-window/past confirmed visits, active/expired holds, cancelled and unknown statuses. Confirm nearest confirmed visit, sorting, counts, timezone/DST and overnight end dates. Let a hold expire while viewing it: it must move to History without becoming booked. Open details from both featured/list cards, exercise the existing allowed reschedule flow and verify the updated list/limits after returning. Check exhausted quotas and active-conversation navigation gates still apply. Use fictional accounts and verify cross-account isolation; never save customer details in screenshots or notes.
