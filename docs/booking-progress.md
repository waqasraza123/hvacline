# Browser booking progress

Implemented, owner verification pending. The owner reports the existing full booking flow works; this progress slice has not been run. No tests, builds, linters, type checks, migrations, services, browser previews or live conversations were executed.

The customer and operator browser experiences now show four booking stages alongside the conversation: Your details, Confirm details, Choose a time, and Appointment confirmed. Progress comes from the existing booking controller and API results. It does not interpret conversation text as proof of a save or booking.

Pending operations identify readback preparation, request saving, availability lookup, reservation, appointment confirmation, and hold release. Connection activity separately reflects speaking, listening, muted microphone, silent Chat, disconnection and conversation end. Countdown ticks are outside live announcements. The panel adds no animation; the existing layout places it above the transcript on small screens.

Only a returned CONFIRMED appointment produces the final receipt, including business date/time/timezone and service category. The receipt remains mounted after conversation end or disconnection. Customers can choose View my appointments after finishing the conversation. A hazard overrides ordinary booking guidance while retaining an already confirmed receipt; no notification or transfer delivery is promised.

The on-screen booking fallback updates the same panel. Elapsed holds disable new confirmation. If an earlier confirmation response was lost, Check previous confirmation retries that same appointment endpoint to establish its result, even after the displayed hold deadline. An unresolved reservation retains its selected time and retry key; unrelated actions are blocked until the previous action resolves. If a voice session ends with a reservation response still unknown, the fallback directs the owner/customer to inspect stored appointments rather than issuing a new reservation with a different key. Known validation/conflict rejections allow the normal correction flow. Server booking rules remain authoritative.

No backend API, schema, migration, environment variable, provider-agent or calendar-provider change is required. Deploy the updated frontend against the existing compatible backend. Hosting deployment was not performed for this slice.

## Owner commands — not executed

Run from the current HVAC implementation checkout with dependencies installed:

```bash
npm run test --workspace @insurance-operations/web -- src/features/conversation/voice-booking.test.ts src/features/conversation/booking-progress.test.ts
npm run verify:web
```

These commands require explicit owner authorization before Codex executes them. No database commands are needed for this frontend slice. Existing confirmation, ownership and booking acceptance requirements still apply.

## Manual acceptance — not executed

1. Complete a fictional booking in Voice and Chat. Observe pending messages during actual tools, confirm details separately from the appointment, and verify only the CONFIRMED response produces the final receipt. Compare date/time/timezone with My appointments and Operations.
2. Correct an address before saving. The prepared-details stage must return to Your details until a new readback is prepared. Refusal or an ambiguous answer must not save or advance to a confirmed appointment.
3. Check an unavailable date, an outside-area address and disabled/unconfigured scheduling. Show the relevant limitation without invented slots, a success receipt, or promised follow-up.
4. Select and release a hold, then choose another time. Finish the conversation with a hold still active and allow its deadline to pass. The countdown must stop at zero and ordinary on-screen confirmation must be disabled. Release the hold and check availability again.
5. Using development request interception, delay a response and lose a save/reservation/confirmation response. Pending state must appear during the request, uncertainty must remain visible, and retries must preserve existing payload/key or appointment identity. A lost confirmation followed by hold expiry must offer Check previous confirmation. No duplicate request or appointment should appear.
6. Disconnect before saving, after saving and after confirmation. Saved outcomes and the final receipt remain visible; the activity label must stop claiming to listen. Retry/start a new conversation and ensure late responses from the old session do not alter its progress. Check the preserved composer draft and existing session-release controls.
7. Report a hazard before booking and after a confirmed booking. Safety guidance takes priority, new self-booking stays blocked, and an existing confirmed appointment remains saved. Do not expect an alert or transfer to have been delivered.
8. Check narrow mobile and desktop layouts, keyboard controls and screen-reader announcements. Stage changes should be announced; countdown seconds should not. Muting must show microphone muted, Chat must remain silent, and View my appointments must stay disabled until the conversation ends.
