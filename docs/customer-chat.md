# Customer chat and voice

Implementation is unverified. The owner reported that voice works on October 25, 2026; appointment booking has not been tested. No tests, builds, linters, type checks, migrations or live conversations were run for this change.

## Behavior

Customer `/book` defaults to **Chat**. Chat accepts typed messages and returns text without microphone access or spoken replies. **Voice** retains live speech and also accepts typed messages; replies in Voice can still be spoken. Finish the current conversation and start a new one to switch modes. Enter sends a message; Shift + Enter adds a line. Messages are limited to 2,000 characters.

Both modes use the existing authenticated customer proxy, private browser agent, eight blocking client tools, approved database FAQs and internal calendar. Both retain AI disclosure, fictional-data acknowledgement, shared limits, hazard handling and backend confirmation gates. Only Voice asks for microphone consent. Each complete current readback must be followed by a clear affirmative response before saving or booking. A typed correction, refusal or ambiguous answer cannot confirm it. A temporary hold is never a confirmed appointment.

Typed messages enter the browser transcript immediately; matching provider echoes are suppressed to avoid recording the same confirmation twice. Drafts remain in browser memory until explicit confirmation. The existing API field `spoken_confirmation` and controller names remain for compatibility; their gate validates transcript text in both modes. Disconnect preserves saved requests and confirmed appointments.

## ElevenLabs configuration

The existing private browser agent `agent_0301m5r65kr7ey5amcdx08yxe5ht` now permits the conversation `text_only` override and includes channel guidance for typed confirmations and voice replies. The saved configuration was read back: default text-only is false, private authentication remains enabled, and all eight tools remain attached. The phone agent was not changed. No live session was started.

The pinned ElevenLabs SDK supports `textOnly` with the existing WebRTC token and skips microphone creation for this mode. See the official [chat-mode guide](https://elevenlabs.io/docs/eleven-agents/guides/chat-mode) and [React SDK documentation](https://elevenlabs.io/docs/eleven-agents/libraries/react). No new agent, environment variable or OpenAI API key is required.

## Owner deployment steps

1. Use updated `main` containing migration `20261025_0011_browser_text_sessions`. Review the intended development database target privately. From that updated checkout or its pre-deploy environment, apply:

   ```bash
   APP_ENVIRONMENT=development alembic upgrade head
   ```

   Render's checked-in pre-deploy command already includes the migration; confirm the effective service command. An older deployed Render Shell may not contain the new revision. Do not launch the updated backend against the older schema: all conversation queries now expect `input_mode`.

2. Deploy the updated backend on Render, then the updated frontend on Vercel. Keep existing environment values and the browser agent ID. Existing voice sessions default to `VOICE`; their microphone consent is preserved. New Chat sessions store `TEXT` with no microphone-consent timestamp. The migration refuses downgrade while text sessions exist because older schemas require that consent for every row.

3. Open `/book` in a signed-in fictional account. Choose Chat, accept the two acknowledgements and start chatting. Voice has a separate microphone checkbox. The development-only data and privacy gates remain required.

## Owner checks (not executed)

Use an updated checkout with its own installed dependencies; an editable Python install pointing to an older checkout will exercise older code. Run from the repository root:

```bash
APP_ENVIRONMENT=test pytest tests/test_browser_spoken_confirmation.py tests/test_conversation_provider.py
npm run test --workspace @insurance-operations/web -- src/features/conversation/text-messages.test.ts src/features/conversation/api.test.ts src/features/conversation/voice-booking.test.ts
npm run verify:web
ruff format --check .
ruff check .
mypy apps/backend/src tests
```

Only with a confirmed isolated disposable `TEST_DATABASE_URL`:

```bash
APP_ENVIRONMENT=test pytest tests/database/test_conversation_api.py tests/database/test_migrations.py tests/database/test_hvac_scheduling.py tests/database/test_telephony_api.py
APP_ENVIRONMENT=test alembic upgrade head
APP_ENVIRONMENT=test alembic check
```

The database fixture downgrades/rebuilds its target; never point these tests at the configured development or hosted database.

Manual acceptance, using fictional information:

1. Start Chat with browser microphone access blocked. Confirm there is no permission prompt, microphone indicator or audible greeting/reply. Confirm AI disclosure and fictional-data acknowledgement are still required.
2. Send with Enter, click Send, add a line with Shift + Enter, and try a blank or overlong message. Each sent message and each agent reply should appear once. Lost connections must disable sending and preserve saved outcomes.
3. Ask a known FAQ and an unknown pricing/policy question. Only successful approved FAQ results may supply business facts. Try instructions to bypass confirmation; the guards must remain enforced.
4. Provide complete fictional intake details. Type a correction or no after the readback and confirm nothing saves. After the corrected complete readback, type yes and confirm exactly one saved request. Repeat yes/retry after a lost response without duplicating it.
5. Choose a future configured weekday for ZIP 10001. Select only a returned slot, decline a hold, reserve another, then type yes after its full date/time/timezone readback. Confirm the final `CONFIRMED` receipt, account history and operations workspace agree. A hold alone must remain unbooked. Check unavailable dates, competing/expired holds and hazards fail safely.
6. Finish and start a new conversation in Voice. Confirm microphone consent/permission is required and speech works. Type during Voice and confirm replies can still be spoken; starting a fresh Chat must restore silence. Both modes must share existing concurrency and daily limits.
7. Check signed-out access, expired sessions and a second fictional account cannot access the first account's records. Disconnect before saving, after saving and after booking; only confirmed outcomes should persist.
