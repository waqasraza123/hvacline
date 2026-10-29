# Local browser conversations — UNVERIFIED

The previously uncommitted local voice draft is integrated with the current HVAC
application. ElevenLabs remains the default. Set `CONVERSATION_PROVIDER=local`
only in a separate development workspace. No provider flag, hosting setting,
installed dependency, model download or database was changed during integration.

## Scope

The backend selects the provider and returns a provider-tagged grant. Local mode
uses a single-use, hashed credential over an origin-checked WebSocket. Session,
operator, business, channel, expiry and ended-state checks are enforced on the
API. Authorization quotas and explicit review/save transactions remain shared.

Local Chat uses Ollama extraction and approved FAQs, without microphone access or
speech playback. Voice adds 16 kHz PCM, whisper.cpp recognition and Piper speech.
Models process on the **API host**, which is only the user's computer when the
API runs there. Ollama must use a loopback URL. Audio/transcript drafts remain in
memory except for per-operation temporary speech files, removed when each
operation exits. Unconfirmed transcripts are not persisted to the application
database; approved-FAQ source/audit behavior remains shared.

The local model only extracts HVAC fields and flags hazards/handoff. Substantive
answers come from approved business FAQs. It has no booking or confirmation
tools: finish the conversation, review all contact/service fields, and explicitly
save on screen. The existing booking panel then checks actual availability and
requires a separate appointment confirmation. The workspace callback checkbox
creates an idempotent callback request only after intake confirmation; failure
keeps the saved request and reports the callback issue. No callback delivery or
deadline is promised. Hazards remain staff-only and cannot self-book.

The local draft does not implement authenticated customer-account sessions.
Configuration rejects `CUSTOMER_PORTAL_ENABLED=true` with an enabled local
provider, preventing customer Chat/MFA from receiving a development-actor grant.
Keep the hosted customer experience on ElevenLabs. Telephone/WhatsApp provider
selection is independent. No migration is added.

## Owner setup — not executed

Use Node.js 24 and the repository's Python 3.13 environment. Review platform
support for [whisper.cpp](https://github.com/ggml-org/whisper.cpp) ([Homebrew formula](https://formulae.brew.sh/formula/whisper.cpp)),
[Ollama](https://github.com/ollama/ollama) and
[Piper](https://github.com/OHF-Voice/piper1-gpl) before installing. On the intended
Intel Mac, install/download the optional runtime and explicitly selected models:

```bash
brew install whisper.cpp
mkdir -p .local/models
curl -L https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin -o .local/models/ggml-base.en.bin
brew install --cask ollama
ollama pull llama3.2:3b
python -m pip install -e '.[dev,local-voice]'
mkdir -p .local/models/piper
python -m piper.download_voices --data-dir .local/models/piper en_US-lessac-medium
```

The Ollama app/service must already be running for the pull. Start it deliberately
with `open -a Ollama` or run `ollama serve` in a separate owner-managed terminal.
Do not launch both. Install/download failures must be resolved explicitly rather
than selecting another model silently. The default model paths are relative to
the API working directory. `.local/` is ignored by Git.

Piper is pinned in the optional `local-voice` extra. Synthesis uses its documented
[file output](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md), then
reads/deletes that temporary WAV; it does not assume `--output-file -` streams a
WAV to stdout. Actual installation and audio quality remain unverified.

For the local workspace only, retain existing database and operator values and
set these root `.env` values:

```dotenv
APP_ENVIRONMENT=development
WEB_ORIGIN=http://localhost:3000
CONVERSATION_AI_ENABLED=true
CONVERSATION_PROVIDER=local
CUSTOMER_PORTAL_ENABLED=false
HOMEPAGE_CHAT_ENABLED=false
LOCAL_WHISPER_COMMAND=whisper-cli
LOCAL_WHISPER_MODEL_PATH=.local/models/ggml-base.en.bin
LOCAL_OLLAMA_BASE_URL=http://127.0.0.1:11434
LOCAL_OLLAMA_MODEL=llama3.2:3b
LOCAL_PIPER_MODEL_PATH=.local/models/piper/en_US-lessac-medium.onnx
```

For an unhosted development workspace, set `NEXT_PUBLIC_API_BASE_URL` to
`http://localhost:8000`, `NEXT_PUBLIC_CONVERSATION_AI_ENABLED=true`, and
`NEXT_PUBLIC_DEMO_SANDBOX_ENABLED=false` in `apps/web/.env.local`. Start the API
and web app only when ready:

```bash
uvicorn insurance_operations.api:app --host 127.0.0.1 --port 8000
npm run dev:web
```

Open `/voice-test`. A protected local `/operations` workspace can instead retain
its existing sandbox/admin configuration. Never expose an unprotected development
API publicly. No new public provider variable or frontend credential is required.

To return to ElevenLabs, set backend `CONVERSATION_PROVIDER=elevenlabs`, retain its
existing private API key, agent and privacy configuration, and restart the API.
Re-enable customer features only with their existing protected configuration.

## Exact owner checks — not run

From the repository root with dependencies available:

```bash
python -m pytest tests/test_conversation_provider.py tests/test_conversation_provider_selection.py tests/test_local_conversation.py tests/test_settings.py tests/test_api.py
python -m ruff format --check apps/backend/src tests
python -m ruff check apps/backend/src tests
python -m mypy apps/backend/src tests
npm run test --workspace @insurance-operations/web -- src/features/conversation/api.test.ts src/features/conversation/connection.test.ts
npm run verify:web
```

Manual acceptance:

- In ElevenLabs mode, check customer login/MFA, silent Chat, Voice, existing
  booking tools and saved appointments. Confirm local selection does not change
  telephone routing or activate the public phone CTA.
- In local Chat, deny microphone permission, send messages and ask approved and
  unknown FAQs. Confirm no microphone or audio, correct HVAC fields, and no
  invented price/availability. In Voice, check recognition, spoken replies,
  mute/unmute and continuous speech up to the utterance cap.
- End, disconnect, deny microphone access, fail playback, navigate away during
  startup and retry deliberately. Confirm microphone tracks/sockets stop, stale
  callbacks cannot alter a new session, and connection failures release the
  application slot. Reused grants, cross-origin sockets and expired/ended
  sessions must fail.
- Finish a local session; inspect/correct all fields, save once, request a
  callback and use the on-screen booking flow. Check retries and saved records
  in Operations. Hazard handling must block ordinary booking. Nothing may be
  described as booked before the appointment confirmation succeeds.
- Complete the repeated-call and expiry checks in
  [the phone runbook](client-phone-demo-runbook.md). A terminal result must keep
  polling and the panel must clearly identify its shared latest-call behavior.

Implementation, installation, performance and runtime acceptance remain
**UNVERIFIED**. No tests, builds, linters, type checks, migrations, services or
live provider/model requests were run during this integration.
