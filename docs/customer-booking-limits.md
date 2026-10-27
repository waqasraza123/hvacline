# Customer booking limits

Implementation is **unverified**. Source formatting was applied; no tests, builds, linters, type checks, migrations, services, previews, live bookings or provider changes ran. No migration is added.

## Configuration and scope

Set these on the Render API, then restart/redeploy it:

```dotenv
CUSTOMER_MAX_ACTIVE_APPOINTMENTS=1
CUSTOMER_MAX_BOOKING_CHANGES=1
```

Both default to 1 when omitted. Active appointments accept 1–20; changes accept 0–20, with 0 disabling further self-service date/time changes. Values are validated at startup. The browser reads effective limits and usage from the authenticated API; changing the values does not require a frontend rebuild after this feature is deployed. The existing three-minute conversation limit is unchanged.

The limits apply per signed-in customer within the business, across that customer's browser sessions, requests, tabs and devices. The appointment limit means **active appointments at a time**, not lifetime bookings. An upcoming/in-progress confirmed appointment or unexpired hold uses a place. Cancelled/expired holds and appointments whose end time has passed free the place. An original appointment plus its in-progress replacement hold use one place because they belong to the same service request. Existing bookings above a newly lowered cap are preserved; new bookings are blocked until capacity is available.

The change allowance applies to the booking's entire service-request history. A successful reschedule consumes one change; the replacement appointment ID does not reset it. Existing immutable `HVAC_APPOINTMENT_RESCHEDULED` audit records determine usage, including changes before this feature. Failed/rejected attempts and retries of an already-completed change do not consume another change. Raising or lowering the environment limit preserves used counts. The current customer editor supports date/time changes; original confirmed contact/service snapshots remain reference data.

This is an account-scoped customer policy. Staff/demo actors and telephone callers without a verified customer-account linkage do not share one artificial quota. It does not establish verified telephone identity or prevent someone creating another development account. Retain the existing fictional-data and development gates.

## Enforcement and display

The scheduling service checks new reservation capacity under the existing business schedule lock, after recognizing an idempotent replay. Confirmation checks capacity again while excluding its own place. Rescheduling checks the change allowance in both phases of the existing transaction flow; a completed replay returns before the allowance check. This covers customer voice/chat tools, on-screen booking and direct customer API requests.

The authenticated `GET /api/v1/customer/booking-limits` response provides effective limits, active usage, available places and the next hold/appointment expiry. A banner appears on both booking/history tabs. It refreshes after booking mutations, on focus/tab return and at the next expiry. The details modal shows changes used/maximum/remaining and disables date/time editing when the allowance is exhausted. A concurrent rejection refreshes the modal's allowance. UI refresh failures are explicit; backend checks remain authoritative.

Conflicts use `CUSTOMER_APPOINTMENT_LIMIT_REACHED` or `CUSTOMER_BOOKING_CHANGE_LIMIT_REACHED`, with a clear message and sanitized counts. Existing booking/calendar/notification transactions and retry keys remain authoritative; no client counter or browser storage determines eligibility.

## Owner commands — not executed

With the project environments installed:

```sh
python -m pytest tests/test_settings.py
npm run test --workspace @insurance-operations/web -- src/features/customer/booking-limits.test.ts src/features/customer/booking-details.test.ts 'src/app/api/v1/development/[...path]/route.test.ts'
npm run verify:web
ruff format --check .
ruff check .
mypy apps/backend/src tests app.py
```

Only with an explicitly isolated, disposable `TEST_DATABASE_URL` and existing test database configuration:

```sh
APP_ENVIRONMENT=test python -m pytest tests/database/test_conversation_api.py tests/database/test_hvac_scheduling.py
```

The database fixture downgrades/rebuilds its target. Never use a shared or hosted development/production database.

Manual: deploy backend first, then frontend. Check defaults show 1 active appointment and 1 date/time change, and usage starts from stored data. Place a hold, attempt a second request through another tab and through a direct API request, then release/expire the hold. Confirm a booking, reschedule it once, retry the same write and attempt a second change on the replacement ID. Check one replacement/notification set, usage 1/1 and disabled editing. Another customer must have an independent allowance. Change API values to 2/2 and 1/0 and restart: banner, modal and backend decisions must follow the new values without resetting history. Check lower limits preserve existing appointments, completed appointments free a place, focus/expiry refresh, Voice/Chat/fallback errors and unchanged phone/staff behavior.
