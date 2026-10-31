# Calling and browser acceptance — UNVERIFIED

This checklist accompanies the preserved local-browser draft and repeat-call
polling fix. It is an owner handoff, not evidence that checks have run. The
current product is HVACLine; use Node.js 24 and Python 3.13. Do not replace
current business settings with the historical insurance/demo defaults.

## Owner commands — not run

```bash
python -m pytest tests/test_settings.py tests/test_conversation_provider_selection.py tests/test_conversation_provider.py tests/test_local_conversation.py tests/test_phone_conversation_provider.py tests/test_telephony_provider.py
python -m ruff format --check apps/backend/src tests
python -m ruff check apps/backend/src tests
python -m mypy apps/backend/src tests
npm run test --workspace @insurance-operations/web -- src/features/conversation/api.test.ts src/features/conversation/connection.test.ts
npm run verify:web
```

Database tests rebuild their target. First confirm `TEST_DATABASE_URL` selects an
isolated disposable database. Follow the exact database commands in the active
provider guide; never run the fixture against retained business data.

## Configuration and manual acceptance

1. Review [environment handoff](environment-handoff.md) and current schema before
   any separately authorized deployment. Preserve business data and existing
   stable MFA/encryption keys. Do not apply Blueprint seed commands blindly.
2. Use [Telnyx setup](telnyx-sip-setup.md) or [Twilio
   setup](telephony-provider-setup.md), according to the configured provider.
   Leave telephone execution disabled until private agent/tools, signed
   finalization, active-number ownership, quotas, privacy and spending choices
   are ready. Do not buy numbers or activate paid services implicitly.
3. Complete the selected provider's live call-to-booking/Operations checklist:
   two-way audio, consent/refusal, exact intake and appointment confirmations,
   hazards, duplicate delivery, disconnect after confirmation and handoff.
   Telnyx uses callback fallback; live transfer is not enabled by this feature.
4. Without reloading `/phone-demo`, complete a call and then make another.
   Confirm the shared latest-call panel updates after the first terminal result.
   Repeat with two open windows; another caller can replace the result.
5. Measure result expiry from call receipt, then allow one polling interval for
   the page to update. Confirm the panel returns to READY. The public projection
   must contain no caller details, transcript or secrets.
6. For the separate local browser workspace, follow [local browser
   setup](local-browser-voice.md). Check local Chat/Voice, cleanup, on-screen
   review, callback save and booking. The customer/MFA flow stays on ElevenLabs.
7. Complete [homepage hero acceptance](homepage-hero.md). Confirm the public
   business number and dial links stay hidden, and check browser Voice AI and
   Text chat navigation. The former phone-CTA variables no longer enable a panel.

Record actual results before marking any path ready. Publication to main does
not establish live calling, model performance or production readiness.
