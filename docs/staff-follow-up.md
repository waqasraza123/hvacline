# Staff follow-up controls — Step 1

Implemented in local source on November 26, 2026. **UNVERIFIED**. No tests,
builds, linters, type checks, formatters, services, migrations or deployments ran.

Operations → Follow-up now offers Acknowledge, Mark complete and Cancel follow-up
for connected workspaces. Each action requires an explicit confirmation and the
loaded row version. Existing backend ownership, transition and audit checks stay
authoritative. The client does not send a transfer-attempt flag or contact a
customer when changing status.

The loaded open queue supports status/type filters, contact/reason search and
oldest-first ordering. Age is calculated at the last refresh. Contact context
comes from the same business's unarchived customer records, without transcript
data. Counts cover the latest 100 open records, not all historical follow-up.

Successful acknowledgment remains in the queue. Completion/cancellation removes
the row and updates the Overview count from the confirmed server response. Errors,
conflicts and uncertain responses require a refresh before another update; the
client never automatically repeats a status mutation. Old backend responses
without a valid version display records without enabling writes. Demo rows and
their controls remain read-only.

This step adds no schema migration. The accompanying Step 2 staff email feature
requires migration0029 before deploying the combined change; see
[Staff email alerts](staff-email-alerts.md).

## Owner commands

From `/Users/mc/development/hvacline`, only when ready:

```sh
npm run test:web -- src/features/operations/follow-up.test.tsx src/features/operations/dashboard.test.tsx
npm run verify:web
```

On an explicitly selected disposable `TEST_DATABASE_URL` only:

```sh
APP_ENVIRONMENT=test python -m pytest tests/database/test_conversation_api.py
```

Database fixtures downgrade/rebuild their target. Never use the shared development
or production target for database tests. No commands above ran here.

## Owner manual checks

1. In demo mode, inspect filters, age and contact-unavailable wording; mutation
   controls must remain disabled and send no requests.
2. In an approved connected workspace, compare contact context with the owned
   request. Check filters/search, empty results, narrow-table scrolling, both
   themes and keyboard focus. No transcript should appear in the projection.
3. Acknowledge a sample requested handoff, confirm once and verify its saved status
   and audit event. It must remain open; acknowledgment must not call/email anyone.
4. Complete another sample only after handling it. Cancel a separate sample.
   Check confirmation wording, removal from the open queue, Overview counts and
   persisted terminal timestamps/status. Repeated clicks must not repeat the write.
5. Open two operator tabs. Change the same row in one, then attempt the old version
   in the other. Confirm a conflict, no overwritten status and a required refresh.
   Simulate a lost response; refresh saved status before another action.
6. Confirm another business's IDs remain inaccessible and that an older backend
   projection cannot enable writes. Completed/cancelled records remain in backend
   history; this step does not add a historical follow-up browser.

Step 2 adds staff alerts separately. No automatic escalation ladder or repeat
reminder schedule is introduced by these status controls.
