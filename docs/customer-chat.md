# Customer chat and voice

Implementation is unverified. The owner reported that voice works on October 25, 2026; appointment booking has not been tested. The owner subsequently reported Chat disconnecting just after startup and preventing completion of typed messages. The repair below has not been reproduced or verified in a live session. No tests, builds, linters, type checks, migrations or live conversations were run for this change.

## Behavior

Customer `/book` defaults to **Chat**. Chat accepts typed messages and returns text without microphone access or spoken replies. **Voice** retains live speech and also accepts typed messages; replies in Voice can still be spoken. Finish the current conversation and start a new one to switch modes. Enter sends a message; Shift + Enter adds a line. Messages are limited to 2,000 characters. Typing sends activity signals without sending the draft text. The editor stays mounted and editable during disconnects/retries, and Send is enabled only during a connected active conversation. Retrying does not erase an unsent message; leaving the page or explicitly starting over can discard browser-only drafts.

Both modes use the existing authenticated customer proxy, private browser agent, eight blocking client tools, approved database FAQs and internal calendar. Both retain AI disclosure, fictional-data acknowledgement, shared limits, hazard handling and backend confirmation gates. Only Voice asks for microphone consent. Each complete current readback must be followed by a clear affirmative response before saving or booking. A typed correction, refusal or ambiguous answer cannot confirm it. A temporary hold is never a confirmed appointment.

Following an owner-reported save failure, the confirmation gate accepts standalone `confirm`, `confirmed`, `I confirm` and `yes I confirm` alongside the existing yes replies, only after the complete current readback. Intake validation rejection returns `INTAKE_CONFIRMATION_REQUIRED` with the exact prepared readback and instructions to repeat it and wait for a fresh reply. A shortened readback still fails. The browser agent's recovery guidance was updated and saved configuration was read back. No live booking or tests ran for this repair; it requires updated backend/frontend deployments, with no new migration or environment settings.

Typed messages enter the browser transcript immediately; matching provider echoes are suppressed to avoid recording the same confirmation twice. Drafts remain in browser memory until explicit confirmation. The existing API field `spoken_confirmation` and controller names remain for compatibility; their gate validates transcript text in both modes. Disconnect preserves saved requests and confirmed appointments.

## ElevenLabs configuration

The existing private browser agent `agent_0301m5r65kr7ey5amcdx08yxe5ht` now permits the conversation `text_only` override and includes channel guidance for typed confirmations and voice replies. The saved configuration was read back: default text-only is false, private authentication remains enabled, and all eight tools remain attached. The phone agent was not changed. No live session was started.

Chat now uses a private signed WebSocket URL; Voice retains its existing WebRTC token. This replaces the initial implementation that forced Chat onto the voice transport. The backend requests the signed URL with `include_conversation_id=true`, validates its secure provider origin/path and returns it only as the short-lived connection credential. It never stores the URL/signature/API key in provider metadata; only a provider-supplied conversation reference is included when present. The frontend rejects mode/transport mismatches and never falls back to voice automatically. The pinned SDK receives `textOnly: true` for Chat. See the official [chat-mode guide](https://elevenlabs.io/docs/eleven-agents/guides/chat-mode), [React SDK documentation](https://elevenlabs.io/docs/eleven-agents/libraries/react) and [signed URL endpoint](https://elevenlabs.io/docs/eleven-agents/api-reference/conversations/get-signed-url). No new agent, environment variable or OpenAI API key is required.

## Owner deployment steps

The active-session recovery repair adds no migration. Deploy its updated backend on Render, then frontend on Vercel. A 409 `CONVERSATION_ALREADY_ACTIVE` means a previous session still occupies the configured slot; Send stays disabled until a new connection succeeds. For an already-stuck session on older code, close other booking tabs and wait the configured maximum duration (180 seconds in this setup) after the last start attempt before retrying.

With the repair deployed, an owned browser-session conflict offers **Release previous session**. Close other booking tabs, release it, then choose **Try a new conversation**. This ends backend intake access for that earlier session and preserves saved requests/appointments. It does not remotely close another browser's provider connection; closing the other tabs releases those connections. Other accounts' sessions and phone sessions cannot be released through this recovery action. Conflicts include a bounded retry delay. Daily and concurrency limits remain enforced.

Retries clean up the last known session before discarding its identifier. Repeated failed/interrupted cleanup is idempotent, and a late provider authorization cannot revive a session already released. Mode/transport-rejected grants also receive a best-effort cleanup request. If an authorization response is entirely lost, the owned-conflict recovery path handles the orphaned backend slot.

1. Use updated `main` containing migration `20261025_0011_browser_text_sessions`. Review the intended development database target privately. From that updated checkout or its pre-deploy environment, apply:

   ```bash
   APP_ENVIRONMENT=development alembic upgrade head
   ```

   Render's checked-in paid-plan Blueprint pre-deploy command already includes the migration; confirm the effective service command. On the owner's Free service, set **Settings → Build Command** to `pip install . && APP_ENVIRONMENT=development alembic upgrade head`, then deploy updated main. Free services do not offer shell or pre-deploy commands; Render documents [running migrations during the build on Free](https://render.com/docs/deploy-rails-6-7). An older deployed shell may not contain the new revision. Do not launch the updated backend against the older schema: all conversation queries expect `input_mode`. The connection/typing repair adds no migration beyond the existing `20261025_0011`.

2. Deploy the updated backend on Render, then the updated frontend on Vercel. Keep existing environment values and the browser agent ID. Existing voice sessions default to `VOICE`; their microphone consent is preserved. New Chat sessions store `TEXT` with no microphone-consent timestamp. The migration refuses downgrade while text sessions exist because older schemas require that consent for every row.

3. Open `/book` in a signed-in fictional account. Choose Chat, accept the two acknowledgements and start chatting. Voice has a separate microphone checkbox. The development-only data and privacy gates remain required.

## Owner checks (not executed)

Use an updated checkout with its own installed dependencies; an editable Python install pointing to an older checkout will exercise older code. Run from the repository root:

```bash
APP_ENVIRONMENT=test pytest tests/test_browser_spoken_confirmation.py tests/test_conversation_provider.py
npm run test --workspace @insurance-operations/web -- src/features/conversation/connection.test.ts src/features/conversation/text-messages.test.ts src/features/conversation/api.test.ts src/features/conversation/failures.test.ts src/features/conversation/voice-booking.test.ts src/features/conversation/lifecycle.test.ts
npm run verify:web
ruff format --check .
ruff check .
mypy apps/backend/src tests
```

Only with a confirmed isolated disposable `TEST_DATABASE_URL`:

```bash
APP_ENVIRONMENT=test pytest tests/database/test_conversation_api.py tests/database/test_approved_faq_api.py tests/database/test_migrations.py tests/database/test_hvac_scheduling.py tests/database/test_telephony_api.py
APP_ENVIRONMENT=test alembic upgrade head
APP_ENVIRONMENT=test alembic check
```

The database fixture downgrades/rebuilds its target; never point these tests at the configured development or hosted database.

Manual acceptance, using fictional information:

1. Start Chat with browser microphone access blocked. Confirm there is no permission prompt, microphone indicator or audible greeting/reply. Confirm AI disclosure and fictional-data acknowledgement are still required. Confirm Chat uses the signed WebSocket connection and Voice uses its WebRTC token.
2. Type continuously through the greeting/replies and several countdown ticks. Confirm focus, cursor position and draft remain stable, with no automatic mode changes or disconnect. Send with Enter, click Send, add a line with Shift + Enter, and try a blank or overlong message. Each sent message and each agent reply should appear once. Disconnect while an unsent draft exists: the editor must stay visible/editable, sending must stop, and the draft must survive a deliberate retry. Send it only after reconnection. Saved outcomes must survive disconnects too.
3. Ask a known FAQ and an unknown pricing/policy question. Only successful approved FAQ results may supply business facts. Try instructions to bypass confirmation; the guards must remain enforced.
4. Provide complete fictional intake details. Type a correction or no after the readback and confirm nothing saves. After the corrected complete readback, type yes and confirm exactly one saved request. Repeat yes/retry after a lost response without duplicating it.
5. Choose a future configured weekday for ZIP 10001. Select only a returned slot, decline a hold, reserve another, then type yes after its full date/time/timezone readback. Confirm the final `CONFIRMED` receipt, account history and operations workspace agree. A hold alone must remain unbooked. Check unavailable dates, competing/expired holds and hazards fail safely.
6. Finish and start a new conversation in Voice. Confirm microphone consent/permission is required and speech works. Type during Voice and confirm replies can still be spoken; starting a fresh Chat must restore silence. Both modes must share existing concurrency and daily limits.
7. Check signed-out access, expired sessions and a second fictional account cannot access the first account's records. Disconnect before saving, after saving and after booking; only confirmed outcomes should persist.
8. Leave an owned browser session active and try starting from a second tab. Confirm recovery offers only that account's earlier browser session. Close the first tab, release the earlier session, start again and verify Send enables only after connection. Repeat after a failed cleanup or reload. Another account must receive no recoverable session ID, and cannot end the first account's session. Saved bookings must survive recovery. Test a lost or incompatible authorization response and confirm no indefinite slot lock or automatic repeated starts.
9. Reply `confirm` after the exact intake readback and verify one request saves. Refusals and `confirm but change my address` must fail. After a deliberately shortened readback, validation must return the exact current readback to repeat; a fresh affirmative reply can then save without duplicates. Repeat the full appointment readback and separate confirmation before expecting `CONFIRMED`. Use a configured service ZIP; the seeded calendar serves 10001, and outside-area ZIPs must not return invented availability.
