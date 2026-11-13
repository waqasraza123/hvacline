<p align="center">
  <img src="docs/assets/hvacline-banner.svg" alt="HVACLine AI — Turn missed calls into HVAC bookings." width="100%">
</p>

<p align="center">
  <strong>An AI receptionist for U.S. heating and air businesses.</strong><br>
  Answer the request. Find the right time. Keep the team in the loop.
</p>

<p align="center">
  <a href="https://github.com/waqasraza123/hvacline/releases/tag/v0.1.0-beta.1"><img src="https://img.shields.io/badge/release-v0.1.0--beta.1-F97316?style=flat-square" alt="Release v0.1.0-beta.1"></a>
  <a href="https://github.com/waqasraza123/hvacline/actions/workflows/ci.yml"><img src="https://github.com/waqasraza123/hvacline/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status on main"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Proprietary-18181B?style=flat-square" alt="Proprietary — written permission required"></a>
  <a href="https://github.com/waqasraza123/hvacline/stargazers"><img src="https://img.shields.io/github/stars/waqasraza123/hvacline?style=flat-square&amp;color=18181B" alt="GitHub stars"></a>
</p>

<p align="center">
  <a href="https://hvacline.online">Website</a> ·
  <a href="#capabilities">Capabilities</a> ·
  <a href="#getting-started">Getting started</a> ·
  <a href="#documentation">Documentation</a> ·
  <a href="https://github.com/waqasraza123/hvacline/releases">Releases</a> ·
  <a href="LICENSE">License</a>
</p>

HVACLine collects service requests, answers business-approved questions, and guides customers toward an available appointment while your team is on the job. Browser voice and text, telephone integrations, scheduling, and operations share the same confirmed request workflow.

> **Proprietary software.** Prior written permission from the applicable copyright holders is required to use, run, modify, redistribute, or commercialize this software, including for personal, educational, internal, or other noncommercial purposes. Public visibility does not grant a free-use license. See [LICENSE](LICENSE), including the limited rights required by GitHub's terms and applicable law.

> **Beta / development preview.** Use fictional data. Production identity, tenant onboarding, privacy review, and live provider acceptance remain incomplete. Final application changes are **unverified**; a release or CI badge does not establish production readiness. See [project state](docs/project-state.md) and the [platform handoff](docs/website-platform-phase2.md).

## Capabilities

| Area | What is implemented |
| --- | --- |
| **Voice & text** | Browser conversations with ElevenLabs, telephone integrations, and inbound WhatsApp voice. |
| **Service intake** | Contact details, service address, equipment issue, requested service, and explicit customer confirmation. |
| **Appointment booking** | Business hours, service areas, technician availability, expiring holds, and confirmed appointments. |
| **Operations** | Requests, appointments, calls, callbacks, handoffs, receptionist settings, and approved knowledge. |
| **Returning customers** | Account access with authenticator MFA, appointment management, and optional customer-controlled memory. |
| **Calendar & messages** | Opt-in Google Calendar synchronization and queued booking emails/reminders through Resend. |
| **Maintenance billing** | Stripe **sandbox-only** packages, purchased labor hours, checkout, and billing history. |
| **Voice AI websites** | Three templates, structured editing, private drafts, immutable publications, history, and rollback behind administrator gates. |
| **GoHighLevel CRM** | Opt-in confirmed-lead contact/opportunity delivery, booking stages, and delivery recovery; runtime acceptance pending. |

Optional integrations require their own configuration and acceptance. Answers stay within approved business information. Hazardous or unsupported requests go to staff. HVACLine does not diagnose equipment or invent prices, and the application stores no raw audio.

## From request to appointment

1. **Understand the request.** The customer describes the issue and confirms their details.
2. **Find a time.** HVACLine checks the configured service area and schedule, then holds an available slot.
3. **Confirm the booking.** The customer explicitly confirms; the saved appointment appears in Operations.

## Explore the dashboard

Open `/operations` on a configured instance for an orange-and-charcoal dashboard with light/dark themes, responsive navigation, requests, appointments, calls, and follow-up queues.

The initial dashboard uses clearly labeled **fictional sample data**. It makes no backend requests, requests no microphone access, and disables booking/payment mutations. **Connect your workspace** opens the separate administrator-token gate for stored records and management tools. Counts describe capped loaded queues, not business-wide analytics.

Dashboard components adapt [TailAdmin](https://github.com/TailAdmin/free-nextjs-admin-dashboard); its [MIT notice](apps/web/src/features/operations/TAILADMIN-LICENSE.txt) is retained. [Dashboard guide and manual acceptance →](docs/operations-dashboard.md)

## Getting started

Development setup requires **Node.js 24**, **Python 3.13**, and a configured **Neon PostgreSQL** development branch. Running the software requires prior written permission under [LICENSE](LICENSE).

After receiving permission:

```bash
git clone https://github.com/waqasraza123/hvacline.git
cd hvacline
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local
npm ci
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Then follow the [development setup guide](docs/development-setup.md) for database configuration, migrations, fictional business content, and service startup. Keep test databases isolated and disposable. Provider credentials and opt-in integrations are configured separately; never commit secrets.

See the [environment handoff](docs/environment-handoff.md) for account, MFA, memory, and WhatsApp configuration. Existing `insurance_operations` package and CLI names are retained for deployment and schema compatibility.

## Architecture

| Layer | Technology |
| --- | --- |
| Web | Next.js, React, TypeScript |
| API | FastAPI, Python 3.13, Pydantic |
| Persistence | Neon PostgreSQL, SQLAlchemy 2, psycopg 3, Alembic |
| Voice & telephone | ElevenLabs, Twilio, Telnyx, WhatsApp voice |
| Optional integrations | Google Calendar, Resend, Stripe sandbox, GoHighLevel |
| Background work | Separate worker or bounded scheduled jobs |

```text
apps/web/          Customer experience, Operations, website editor
apps/backend/      API, scheduling, accounts, provider integrations, jobs
migrations/        Versioned database changes
tests/             Python unit, API, and database specifications
docs/              Setup, architecture, integrations, and acceptance guides
```

Ownership constraints, signed provider events, explicit confirmations, and persistent request keys protect shared workflows. Scheduling remains authoritative when integrations synchronize external records. [Architecture details →](docs/hvacline-architecture.md)

## Documentation

| Start here | Guides |
| --- | --- |
| **Setup & design** | [Development](docs/development-setup.md) · [Environment](docs/environment-handoff.md) · [Architecture](docs/hvacline-architecture.md) |
| **Customer experience** | [Chat & voice](docs/customer-chat.md) · [Authenticator MFA](docs/customer-mfa.md) · [Customer memory](docs/customer-memory.md) |
| **Receptionist & knowledge** | [Browser agent](docs/elevenlabs-agent-setup.md) · [Knowledge base](docs/knowledge-base.md) |
| **Telephone** | [Live validation](docs/hvacline-live-validation.md) · [Telnyx SIP](docs/telnyx-sip-setup.md) · [WhatsApp voice](docs/whatsapp-inbound-calling.md) · [Callbacks](docs/public-callbacks.md) |
| **Business tools** | [Dashboard](docs/operations-dashboard.md) · [Calendar & reminders](docs/calendar-and-booking-messages.md) · [Maintenance billing](docs/maintenance-billing.md) · [GoHighLevel](docs/gohighlevel.md) |
| **Website platform** | [Editor, publications & acceptance](docs/website-platform-phase2.md) · [Agent setup](docs/website-agent-instructions.md) |
| **Optional local voice** | [whisper.cpp, Ollama & Piper](docs/local-browser-voice.md) |
| **Project status** | [Current state](docs/project-state.md) · [Verification history](docs/verification.md) · [Launch requirements](docs/public-demo-production-readiness.md) |

## Status & releases

The existing [v0.1.0-beta.1 prerelease](https://github.com/waqasraza123/hvacline/releases/tag/v0.1.0-beta.1) records an earlier source snapshot. The default branch includes subsequent work; the tag remains pinned to its original commit.

- **Website platform:** administrator-only, off by default, and development/test gated. Published sites use `/sites/[slug]`; website sessions support inquiries, with booking and memory disabled. Production self-service onboarding is pending.
- **GoHighLevel:** source implemented and off by default. The configured development database reached migration `20261113_0024`; provider setup and runtime acceptance remain pending. [Setup and deferred checks](docs/gohighlevel.md).
- **Public template showcase:** removed; `/demos/[slug]` returns not-found. Templates remain available through the restricted editor. Pricing lives on `/pricing`.
- **Verification:** earlier checks cover earlier snapshots. Final source changes and live/visual acceptance remain unverified; exact results and deferred commands live in the linked feature guides.

n8n event delivery is a documented follow-up, not an implemented integration.

## Feedback, contributions & security

Use the [issue forms](https://github.com/waqasraza123/hvacline/issues/new/choose) for reproducible bugs, feature proposals, or permission inquiries. Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing code changes; written permission is required before running or modifying the software.

Report vulnerabilities privately through the process in [SECURITY.md](SECURITY.md). Keep credentials, customer information, recordings, and transcripts out of public reports.

## License

**Proprietary. All rights reserved.** No free, personal, educational, internal, or commercial use is licensed without prior written permission from the applicable copyright holders. Payment alone does not grant permission. Any authorization is limited to the scope and conditions agreed in writing.

For permission, open a [permission inquiry](https://github.com/waqasraza123/hvacline/issues/new?title=Licensing%20permission%20inquiry) describing the intended use without confidential information. An inquiry, acknowledgement, or public repository access is not authorization. See [LICENSE](LICENSE) for the full notice. Third-party components retain their own licenses.
