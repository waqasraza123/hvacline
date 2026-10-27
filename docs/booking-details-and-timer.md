# Booking details, rescheduling and session timer

Implementation is **unverified**. Source formatting was applied; no tests, builds, linters, type checks, migrations, services, previews, live bookings or provider changes ran. The owner chose to retain the three-minute browser limit. The interrupted ten-minute source changes and migration were discarded; no database migration is added by this feature.

Customer booking and date/time-change quotas now apply; see [customer booking limits](customer-booking-limits.md) for environment settings, displayed usage and unexecuted acceptance checks.

## Customer behavior

- A confirmed receipt offers **View booking details**, including while the conversation is still active. **My appointments** offers **View details & edit** for saved appointments. Both open a native modal that loads the booking from the authenticated customer API.
- The modal shows booking status, date, end time, business timezone, service type, confirmed contact/address details, reported issue and reference. It exposes no transcript, provider credentials or other customers' details. Escape, close and backdrop dismissal restore focus; in-flight writes prevent accidental dismissal.
- **Edit appointment date and time** checks actual availability and requires a separate checkbox and confirmation action. Confirmed intake/contact snapshots are shown for reference. This slice implements date/time editing; contact/address/service amendments are not part of rescheduling. Editing is disabled during a live conversation to avoid competing with its booking tools.
- Replacement availability excludes this customer's old appointment from internal conflicts and verifies ownership/times before excluding its Google event. Other events and bookings remain busy. The scheduling service rechecks notice, hazards, capacity and external conflicts under its existing locks. It preserves the old appointment until replacement confirmation succeeds and reuses the existing calendar cleanup and email/reminder outbox.
- A lost or uncertain response retains the same reschedule payload and idempotency key in browser memory, including closing/reopening the modal. The customer must check that change before choosing another slot. A full page reload loses that browser-only retry context; inspect persisted appointments before trying another change. A confirmed reschedule opens the replacement's stored details and refreshes history. Server notice/status rules can require staff assistance instead of self-service.
- A prominent timer displays **3:00 → 0:00**. New grants include the server authorization expiry; older deployments fall back to the granted duration. The countdown uses the absolute deadline, so delayed background-tab ticks do not extend the session. There is a final-minute warning and an explanation when the browser's own timer ends the session. Manual or unexpected early disconnects preserve their remaining-time display and do not claim timer expiry. Start over resets the display. The existing 180-second API/database cap, separate provider limit and five-minute booking hold are unchanged.

## Deployment

Deploy the updated backend on Render, then the frontend on Vercel. Keep `CONVERSATION_MAX_DURATION_SECONDS=180` and the private browser agent maximum at 180 seconds. This feature does not require changes to the job project, Google/Resend settings, database revision or hosted agent. Retain all fictional-data and development-identity gates.

## Owner commands — not executed

From the active source with project dependencies installed:

```sh
npm run test --workspace @insurance-operations/web -- src/features/customer/booking-details.test.ts src/features/conversation/session-timer.test.ts src/features/conversation/api.test.ts src/features/conversation/booking-progress.test.ts 'src/app/api/v1/development/[...path]/route.test.ts'
npm run verify:web
python -m pytest tests/test_api.py
ruff format --check .
ruff check .
mypy apps/backend/src tests app.py
```

Only with an explicitly isolated, disposable `TEST_DATABASE_URL` and the existing test database configuration:

```sh
APP_ENVIRONMENT=test python -m pytest tests/database/test_conversation_api.py tests/database/test_hvac_scheduling.py
```

The database fixture downgrades/rebuilds its target; never use a shared or hosted development/production database.

Manual checks:

1. Confirm one fictional booking through Chat and Voice. Open details from the receipt before ending the session; verify the original timer continues and editing is disabled. Finish, then open it from history and check every field against stored data.
2. Pick a new date/time, decline confirmation and close: the booking must remain unchanged. Confirm a valid replacement: history and modal must show the new confirmed booking, with the previous booking cancelled. Check Google and delivery state through the existing integration acceptance steps.
3. Try another account's appointment identifier for details, availability and reschedule: each must return 404. Submit false confirmation, an unavailable slot, a near-term/past/cancelled booking and a hazardous request; none may bypass backend restrictions. Make an external calendar conflict and confirm safe rejection.
4. Lose a reschedule response, close/reopen the modal and check the previous change with the same key. Verify one replacement and one notification set. Test an expired replacement hold and a definitive slot rejection, then select another actual slot.
5. Confirm keyboard focus stays inside the modal, Escape/backdrop behavior, busy controls, focus return, narrow-screen scrolling, readable timezone and status. Check cancelled bookings do not look confirmed.
6. Watch 3:00 count down, switch tabs and return, then reach 0:00. Check the final-minute notice, normal expiry, retained unsent draft and saved booking. Start over and verify 3:00 resets. Interrupt the network early and check it is not labelled as time expiry.
