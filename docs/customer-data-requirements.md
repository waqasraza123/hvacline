# Customer wording and data requirements — UNVERIFIED

On October 29, 2026, the owner requested removing demo/early-access language and explicitly approved removing fictional-data requirements. The source removes the login/signup notice, signup acknowledgement, browser Chat/Voice acknowledgement, and browser/telephone/WhatsApp API requirements. Homepage actions, phone-page metadata/status, Operations copy, README, intake readbacks, seed greetings/FAQs and documented agent instructions use neutral product wording.

AI/provider disclosure, Voice microphone consent, customer authentication/MFA, account isolation, exact intake/booking readbacks, quotas and provider privacy configuration remain enforced. Runtime environment and development-actor configuration are unchanged. The legacy signup field remains optional and deprecated so older signup clients can still submit it; it is never checked or recorded as consent.

Migration `20261029_0016` makes the historical `synthetic_data_acknowledged_at` column nullable. Old evidence is preserved; new sessions across all three channels leave it empty. Downgrade refuses while any row lacks the old acknowledgement, avoiding fabricated evidence. The disposable database fixture now clears conversations and dependent test rows before downgrade at setup/teardown, since the new migration and existing text-session migration reject consent fabrication. Never use that fixture against retained data.

No tests, builds, linters, type checks, migrations, seeds, services, provider updates or deployments were run. Implementation and runtime remain **UNVERIFIED**. The owner authorized publication to `main`; publication does not establish runtime acceptance.

## Owner commands

Run from `/private/tmp/hvacline-browser-demo` using dependencies installed for that checkout:

```sh
npm run verify:web
ruff format --check apps/backend/src migrations tests
ruff check apps/backend/src migrations tests
mypy apps/backend/src tests
python -m pytest tests/test_browser_spoken_confirmation.py tests/test_api.py
```

Only with `TEST_DATABASE_URL` confirmed isolated, disposable and distinct from runtime/direct database URLs; this fixture truncates test conversations/dependencies and downgrades/rebuilds the database:

```sh
APP_ENVIRONMENT=test python -m pytest tests/database/test_conversation_api.py tests/database/test_customer_mfa.py tests/database/test_phone_receptionist_flow.py tests/database/test_whatsapp_calling.py tests/database/test_migrations.py
APP_ENVIRONMENT=test alembic upgrade head
APP_ENVIRONMENT=test alembic check
```

## Deployment and manual acceptance

1. Finish existing conversations before deploying. Apply the new schema before starting the new backend, using the intended deployment database:

   ```sh
   APP_ENVIRONMENT=development alembic upgrade head
   ```

2. Deploy the backend, then frontend. Keep existing runtime environment, identity, privacy settings and secrets. No new environment variable or dependency is required.
3. Update the hosted browser agent's greeting, system prompt and client-tool descriptions from [browser setup](elevenlabs-agent-setup.md) and its linked JSON. Update the phone agent's disclosure and consent-tool fields from [phone setup](elevenlabs-phone-agent-setup.md). For WhatsApp, apply the **exact** new first message and consent-tool fields from [WhatsApp setup](whatsapp-inbound-calling.md) together with the backend: its transcript validation requires that exact disclosure. Hosted agents were not changed by this task.
4. In Operations, review the stored receptionist greeting and approved service, required-details, AI-disclosure and confirmation/privacy FAQs. Remove old fictional-data/demo instructions through the existing editors, using the revised seed text as a reference. Existing database content is intentionally preserved by the seed; redeploying or reseeding alone does not overwrite it. Preserve real business facts, pricing limitations and unrelated edits.
5. Inspect `/`, `/login`, `/signup`, `/book`, `/operations` and `/phone-demo` at desktop/mobile widths. Confirm the quoted notice, early-access labels and demo status text are absent. Confirm signup proceeds to mandatory MFA without a fictional-data checkbox.
6. Use controlled test details for acceptance. Chat must start after AI disclosure alone, with no microphone request. Voice must additionally require microphone consent. Refusing either applicable consent must prevent starting. After authorization, the historical synthetic-acknowledgement timestamp must remain empty.
7. Verify exact readbacks, corrections/refusals, one saved request and one confirmed booking, history/account isolation and retry behavior. Test phone/WhatsApp consent, callback and booking paths after provider configuration updates; declined consent must save no intake/booking. The agent must not ask callers to invent their details.
8. Preview the README and inspect page titles, accessible booking-link labels and phone status/error messages. Confirm existing service limitations and privacy disclosures still render.
