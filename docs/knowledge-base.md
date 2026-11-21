# Approved knowledge base

On November 9, the owner-authorized database operation applied
`20261108_0020` → `20261109_0021` and confirmed the resulting revision, non-null
JSONB column/default and validated shape/count constraint. The configured
runtime/direct database targets and roles match. No existing approved content
was edited or reseeded. Source formatting only was performed; tests, builds,
linters, type checks, provider actions, publication and deployment were not run.
The application changes remain local/unpublished and runtime-unverified.

HVACLine already uses `agency_approved_faqs` in PostgreSQL as its business-owned
knowledge library. Open Operations → knowledge base, using the existing
administrator authentication. Browser Voice/Chat, homepage guest questions and
telephone tools reuse `ApprovedFaqService`; provider agents should use the
existing `lookup_approved_faq` tool rather than a second uploaded knowledge base.

## Improvements — application acceptance UNVERIFIED

- Each answer supports up to eight approved alternate questions, 300 characters
  each. Punctuation/case-normalized duplicates and empty questions are rejected.
  All phrasings share the exact approved answer, activation status and version.
- Existing conservative matching thresholds are unchanged. Multiple close matches
  across answers use the existing staff fallback. Inactive and other-business
  answers are excluded. Sources retain the canonical question, record and version.
- Operations provides question/answer/variation search, active/inactive filtering,
  counts, loading/retry feedback and a structured preview of the real lookup.
  Filtering hides editors without losing unsaved drafts. Preview does not save
  customer questions or start a conversation.
- New answers remain inactive. Unsaved edits must be saved or discarded before
  activation changes; active-answer edits explicitly warn that saving updates
  Line's available knowledge. Version conflicts retain edits and offer an
  explicit discard-and-reload action. Writes retain ownership, versions and audit.
- Older clients that omit variations on update preserve saved variations.
  Sending an explicit empty list clears them. The frontend accepts older read
  responses without the optional field, but new editing needs the updated backend.

Forward migration `20261109_0021` adds only the JSONB variations column/default
and its shape/count constraint. Existing question/answer/status rows are retained.
Apply it before deploying this updated backend:

```sh
APP_ENVIRONMENT=development .venv/bin/python -m alembic upgrade head
```

Starter content now reflects optional Google Calendar/email integration,
account-based rescheduling and Stripe sandbox billing. These source edits do not
overwrite existing approved records. Review any older answers through Operations;
no seed or provider knowledge upload is needed to enable the new editor.

## Owner checks — not executed

```sh
APP_ENVIRONMENT=test .venv/bin/python -m pytest tests/test_approved_faq_matching.py
npm run test:web -- src/features/approved-faqs/api.test.ts src/features/approved-faqs/knowledge.test.ts
npm run verify:web
.venv/bin/ruff check apps/backend/src/insurance_operations/approved_faqs apps/backend/src/insurance_operations/database/models/approved_faq.py apps/backend/src/insurance_operations/database/development_content.py migrations/versions/20261109_0021_faq_question_variations.py tests/test_approved_faq_matching.py tests/database/test_approved_faq_api.py
.venv/bin/python -m mypy apps/backend/src/insurance_operations
```

Only on an isolated disposable `TEST_DATABASE_URL` (fixtures rebuild its schema):

```sh
APP_ENVIRONMENT=test .venv/bin/python -m pytest tests/database/test_approved_faq_api.py tests/database/test_migrations.py
```

Manual acceptance: create an inactive answer with alternate questions, confirm no
preview match until activation, then confirm the exact answer and source/version.
Try unrelated and ambiguous questions, deactivate and confirm fallback. Check
search/status filters preserve drafts; activation is blocked with unsaved edits;
stale-version writes retain drafts and require review. Check separate-business
isolation, keyboard/mobile layout, source-backed live tools and existing audit
events. Do not promise deployment, payment, calendar sync or message delivery
based on knowledge text alone.
