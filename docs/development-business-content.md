# Development business content

The development seed supplies 28 source-backed FAQs for the fictional Harborline Heating & Air business. Questions and answers are defined in `apps/backend/src/insurance_operations/database/development_content.py` and the three original entries in `database/seed.py`. This is development content, not approved facts about a real HVAC company.

On October 25, 2026 the owner-requested scoped application inserted 25 additional FAQs into the configured Neon development database, with 28 active seed FAQs reported afterward. It reused the existing receptionist profile, created and enabled the missing default calendar and skipped phone routing. Three newly inserted answers were subsequently clarified through the audited FAQ service to distinguish website bookings and browser memory from other channels. No migrations, tests or live voice conversations ran. This data-application result does not verify Render's effective database configuration or end-to-end booking.

Coverage includes the four supported service categories, installation estimates, equipment-brand limitations, service-area checks, required intake details, appointment availability, business timezone, five-minute holds, confirmation, unavailable slots, appointment changes, pricing/fee inquiries, warranty and financing inquiries, technician arrival information, staff assistance, booking receipts, external-calendar limitations, AI disclosure, equipment-advice limits, emergency-response limitations and confirmation/privacy behavior.

No prices, diagnostic fees, financing eligibility, warranty terms, brand support, emergency response times, notification delivery or staff callbacks are invented. Where these facts or capabilities are not configured, the approved answer directs the user to staff. Availability and service-area eligibility require the scheduling tools. The original fictional office-hours FAQ is a business fact and must be reviewed if the business changes its operating hours; editing a booking calendar does not automatically rewrite approved FAQs.

## Stored records

- `agency_approved_faqs`: missing development FAQ entries, initially ACTIVE, using deterministic IDs, canonical question normalization and the existing content validator.
- `agency_receptionist_settings`: a missing Line profile with the four HVAC categories and a conservative fallback. Existing custom profiles are preserved. Only exact known legacy fallback text promising follow-up is replaced with wording that does not promise a callback, transfer or delivered alert.
- `business_schedules`: the existing development calendar defaults are inserted only if the fictional business has no calendar. Existing calendars, including disabled ones, are preserved.
- `audit_events`: content-minimizing FAQ creation and known-default fallback update records; no transcript or customer content is included.

Seeding does not create customer accounts, service requests, appointments, conversations, provider agents or external calendar events. Conflicting FAQ IDs or normalized questions are skipped, so edited questions/answers and deactivated entries are not overwritten or reactivated. The target business must be active and marked DEVELOPMENT; the command also requires `APP_ENVIRONMENT=development`.

The browser agent uses `lookup_approved_faq` against the application database. Keep its provider Knowledge Base empty for this flow; no duplicate upload is needed. Lookup remains deliberately conservative, so unsupported or ambiguous questions use the staff-assistance fallback.

## Application

After deploying the updated source and reviewing the intended development Neon target:

```bash
APP_ENVIRONMENT=development insurance-operations-seed-development --skip-telephony
```

This applies the requested fictional business content, including a missing calendar, without changing phone routing. The seed updates no production business. It does not run migrations; any earlier required migrations must already be present. Ensure Render uses the intended development database branch.

## Owner verification

These checks have not been run by Codex:

```bash
ruff format --check apps/backend/src/insurance_operations/database/development_content.py apps/backend/src/insurance_operations/database/seed.py tests/database/test_migrations.py
ruff check apps/backend/src/insurance_operations/database/development_content.py apps/backend/src/insurance_operations/database/seed.py tests/database/test_migrations.py
mypy apps/backend/src tests
```

Only after confirming `TEST_DATABASE_URL` is isolated and disposable:

```bash
APP_ENVIRONMENT=test pytest tests/database/test_migrations.py -k development_seed
APP_ENVIRONMENT=test alembic upgrade head
```

The database fixture downgrades/rebuilds its target and downgrades it again at teardown. The final command restores only that disposable test target to migration head.

Manual acceptance:

1. Open `/operations` → knowledge and confirm the seeded questions and approved answers. Review office hours and all business-specific statements against the current fictional configuration.
2. Use knowledge lookup preview for a supported canonical question, then an unrelated request. Confirm a source-backed answer for the former and the staff-assistance fallback for the latter.
3. Edit and deactivate an FAQ, rerun the content command, and confirm the edit/status/version remain unchanged. Keep the business calendar and phone settings unchanged when reseeding.
4. In fictional browser voice, ask about maintenance, pricing, warranty and a topic outside the approved scope. Confirm the assistant follows returned answers and does not invent terms or promise delivery/dispatch.
5. Complete the two booking confirmations and inspect the persisted CONFIRMED receipt. This runtime acceptance is separate from database-content application.
