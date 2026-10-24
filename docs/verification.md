# HVACLine AI Verification

Implementation source: `0cbbe8f318824f7a371ec9aba46443d58d6dcf70` on `feat/hvacline-ai`.

Evidence: [GitHub CI run 40116765713](https://github.com/waqasraza123/insurance-operations-ai/actions/runs/40116765713).

| Check | Result |
| --- | --- |
| `npm run verify:web` | Passed in CI, including the production build and 24 tests |
| `ruff format --check .` | Passed |
| `ruff check .` | Passed |
| `mypy apps/backend/src tests` | Passed |
| `APP_ENVIRONMENT=test pytest` | 83 passed |
| `alembic upgrade head` | Passed on CI's disposable PostgreSQL 17 service |
| `alembic current` | `20261024_0009 (head)` |
| `alembic check` | No new upgrade operations detected |
| `insurance-operations-worker --check` | Ready in CI |

Coverage includes signed provider boundaries, confirmed post-call materialization, authenticated HVAC phone tools, persistent booking, concurrent reservation conflicts, idempotent replay, tenant scoping, expired holds, hazardous-request refusal, atomic rescheduling, cancellation, and minimum-notice behavior throughout an active hold. Google Calendar tests use HTTP fixtures and do not prove live OAuth/calendar access.

The phone-to-booking database test uses synthetic provider requests. It is not a real telephone call. Live Twilio routing, ElevenLabs dashboard settings, interruptions/corrections, audio quality, transfer behavior, external calendars, notifications and production account access remain unverified or incomplete.

The local execution host fails Next build with `uv_resident_set_memory` ENOENT. GitHub independently compiled the same application and generated `/operations` successfully. No production/shared database was reset, migrated or seeded during this work.
