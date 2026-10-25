# Development booking calendar defaults

Status: implemented, unverified. No migration, seed, test, build, service or live check ran for this change. Existing database settings change only when the updated development seed executes; source publication alone does not initialize the hosted calendar.

Scheduling already persists in `business_schedules`, keyed by `agency_id`, with a JSON `configuration` and optimistic-concurrency `version`. Saving the operations Scheduling form updates that row; browser and phone booking read the same persisted configuration.

The updated development seed creates one missing calendar for the deterministic fictional development business:

| Setting | Default |
| --- | --- |
| Booking enabled | Yes, for the fictional development business |
| Business timezone | `America/New_York` |
| Service ZIPs | `10001` |
| Business/team hours | Monday–Friday, 09:00–17:00 |
| Visit duration | 60 minutes |
| Booking notice | 120 minutes |
| Change notice | 120 minutes |
| Booking horizon | 30 days |
| Team | `test-team` / Test Team |

The seed locks the development business before checking the schedule, validates defaults with the existing backend schema, and inserts the schedule and its audit event in one transaction. Repeated seeds preserve existing configuration and version, including operator edits or disabled booking, and do not duplicate the audit. No appointments are created. Other businesses get no defaults. The seed refuses non-development application environments, and schedule initialization requires the seeded business to be active and marked DEVELOPMENT.

## Owner application

After the updated source is published/deployed, review the intended development database target. If Render already runs `alembic upgrade head && insurance-operations-seed-development` as its pre-deploy command, the updated seed runs there. Otherwise, the owner runs:

```bash
APP_ENVIRONMENT=development alembic upgrade head
APP_ENVIRONMENT=development insurance-operations-seed-development
```

No new migration is introduced; upgrade only applies migrations that are already pending. The existing development seed also performs its documented foundation and optional phone setup, so review any configured demo phone variables before running it.

## Owner verification

From the active implementation checkout, with its dependencies installed:

```bash
ruff format --check apps/backend/src/insurance_operations/database/seed.py tests/database/test_migrations.py
ruff check apps/backend/src/insurance_operations/database/seed.py tests/database/test_migrations.py
mypy apps/backend/src tests
```

Only with `TEST_DATABASE_URL` confirmed isolated and disposable:

```bash
APP_ENVIRONMENT=test pytest tests/database/test_migrations.py -k development_seed
APP_ENVIRONMENT=test alembic upgrade head
```

The database fixture downgrades and rebuilds its target, and downgrades it again during teardown. Never point it at the development or production database. The final command restores only the confirmed disposable test database to migration head.

Manual checks:

1. Seed a development business with no calendar, then open `/operations` → Scheduling. Confirm the persisted defaults above and refresh the page to check they remain.
2. Book with fictional details using ZIP 10001 and a future configured weekday. Confirm business timezone, the two-hour notice, available team slots and the final CONFIRMED receipt.
3. Edit the calendar through Scheduling, including disabling booking, save, and rerun the development seed. Confirm all edits and the version remain unchanged, and disabled booking returns no slots.
4. Confirm another business is unconfigured and no appointments were created by seeding.

These are development test defaults, not the real availability or service area of an HVAC company. Production onboarding must collect each business's own approved calendar.
