# Resend staff email alerts — Step 2

Local source implementation, November 26, 2026. **UNVERIFIED**. Owner selected
Resend email. No tests, builds, linters, type checks, formatters, migrations,
services, provider requests, sends, activation, commits, pushes or deployments ran.

## Behavior and boundaries

Migration `20261126_0029`, after0028, adds `staff_alert_policies`, `staff_alerts`
and transactional capture triggers. **UNAPPLIED**. New handoff requests and new
urgent service requests capture one immutable email per approved recipient while
that business's policy is enabled. An existing routine service request becoming
hazardous is also captured. Rollback removes the alert with the source change;
repeated eligible changes cannot duplicate the same source/recipient alert.
Enabling a policy does not backfill historical requests.

Operations → Follow-up includes protected recipient settings and the latest100
staff delivery records. The saved policy allows up to five distinct valid staff
email addresses. Editing/enabling requires the administrator token, an expected
saved version and explicit recipient review in the UI. Policy changes are audited
without addresses or message contents. No public/customer/mobile proxy exposes
the new settings or history.

Emails contain the business/request references and instructions to open the
protected workspace. They contain no customer names, contact details, raw
transcripts or credentials. Urgent service review has a separate subject. These
notifications are not a substitute for emergency services, successful human
contact or an acknowledged escalation. This step does not add SMS, push,
on-call rotations or repeated unacknowledged-alert reminders.

Existing booking jobs collect staff deliveries. The worker checks the source's
business and open status, policy/version and recorded recipient suppression
before each request. Editing/disabling a policy invalidates queued alerts from
the earlier policy version. Closed requests and bounced/complained/suppressed
recipient histories prevent new sends. Already accepted messages cannot be recalled.

First-attempt time is committed before provider access. Retries preserve the
original payload/key, back off and stop after eight persisted attempts or23hours
from the first attempt. Alerts older than24hours expire. A possible earlier send
becomes UNKNOWN rather than being treated as unsent. No fresh-key resend or
automatic reopening of terminal jobs is exposed. The payload and initial attempt
horizon are protected against update by database triggers.

ACCEPTED means Resend accepted a request. DELIVERED is separate signed webhook
evidence. The existing `/api/v1/providers/resend/booking-events` endpoint accepts
staff receipts when staff email is enabled, even if booking emails are disabled;
the existing signature, bounded body and event deduplication protections remain.
Delivery events update staff records through the existing job runner. This is an
email alert, not a guarantee that staff read or acted on it.

The retry boundary follows Resend's documented24-hour deduplication window with
a conservative margin: [Resend idempotency keys](https://resend.com/docs/dashboard/emails/idempotency-keys).

## Owner setup — not performed

1. Deliberately select the intended database. After reviewing the forward migration,
   apply0029 before deploying the combined API/job/web source. Do not rerun already
   completed earlier migrations independently or point tests at this target.
2. Configure the existing `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET` and verified
   `BOOKING_EMAIL_FROM` sender on both API and the existing job runner/worker.
   Credentials stay in the secret manager/environment, never notes or source.
3. Set `STAFF_ALERT_EMAIL_ENABLED=true` on API and job runner only after provider
   setup is reviewed. The flag defaults to false and retains development identity
   gates; startup rejects enabled delivery without valid Resend configuration.
   Booking emails have their own flag and need not be enabled for staff alerts.
4. Retain signed Resend webhook delivery to the existing booking-events endpoint.
   Ensure the existing authenticated scheduled booking job or persistent worker
   runs. This implementation creates no new background service.
5. Connect an approved administrator workspace, review the sender/recipient list,
   explicitly enable the business policy and save. No settings save sends a test
   email. The first accepted sample send needs deliberate owner authorization.

## Owner commands

Focused frontend/unit source:

```sh
npm run test:web -- src/features/operations/follow-up.test.tsx src/features/operations/staff-alerts.test.ts
APP_ENVIRONMENT=test python -m pytest tests/test_staff_alerts.py tests/test_settings.py tests/test_booking_jobs.py
npm run verify:web
python -m ruff check apps/backend/src tests migrations
python -m mypy apps/backend/src
```

Only with an explicitly selected isolated disposable `TEST_DATABASE_URL`:

```sh
APP_ENVIRONMENT=test python -m pytest tests/database/test_staff_alerts.py tests/database/test_conversation_api.py tests/database/test_migrations.py tests/database/test_table_ownership.py tests/database/test_booking_jobs.py
```

Those database fixtures downgrade/rebuild the selected test target, including
cleanup of disposable staff alert rows so history-protecting downgrades can run.
The cleanup is test-only; there is no equivalent production history deletion.

Forward migration for the separately reviewed intended development target:

```sh
APP_ENVIRONMENT=development python -m alembic upgrade 20261126_0029
```

No command above ran here. Formatting/type/runtime results are unverified.

## Owner manual checks

- Verify disabled defaults, missing/incorrect administrator token rejection,
  recipient validation/duplicates/limits, version conflicts and draft cancellation.
  No save or reload may send an email. Inspect both themes, mobile and keyboard use.
- On an isolated approved test business, confirm historical requests remain
  unenrolled. New callback/transfer requests and new/later-detected hazards should
  each create only one row per recipient. Rollback and duplicate events must not
  leave extra jobs. Routine service requests should not create staff alerts.
- With a deliberately approved sample recipient/provider send, verify sender,
  references-only content and separate ACCEPTED/DELIVERED states. Confirm receipts
  are signed and duplicate/out-of-order receipts cannot downgrade delivery state.
- Simulate rate limiting, timeout and a crash after provider acceptance. The
  retry must preserve payload/key and first-attempt time. Eight attempts/expiry
  must stop uncertain sends without creating another email reference.
- Close the source or disable/change the policy while work is pending. Confirm
  queued jobs are suppressed/unknown as appropriate. Test recorded bounce/complaint
  suppression, cross-business access and global API/job flag mismatch. Already
  accepted emails may still arrive; no recall is claimed.
- Check booking confirmations/reminders and existing job types still work with
  their own flags. Do not advertise staff alerts as live until these results are
  reported and the intended deployment/provider configuration is accepted.
