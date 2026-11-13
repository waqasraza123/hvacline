<p align="center">
  <img src="apps/web/public/icon.svg" alt="HVACLine AI logo" width="96" height="96">
</p>

<h1 align="center">HVACLine AI</h1>

<p align="center">
  <strong>Turn missed calls into HVAC bookings.</strong><br>
  An AI receptionist for U.S. heating and air businesses.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/HVAC-F97316?style=flat-square" alt="HVAC">
  <img src="https://img.shields.io/badge/AI_Receptionist-18181B?style=flat-square" alt="AI receptionist">
  <img src="https://img.shields.io/badge/Appointment_Booking-18181B?style=flat-square" alt="Appointment booking">
</p>

<p align="center">
  <a href="https://elevenlabs.io/"><img src="https://img.shields.io/badge/ElevenLabs-18181B?style=for-the-badge&amp;logo=elevenlabs&amp;logoColor=white" alt="ElevenLabs voice AI"></a>
  <a href="https://www.twilio.com/"><img src="https://img.shields.io/badge/Twilio-F22F46?style=for-the-badge&amp;logo=twilio&amp;logoColor=white" alt="Twilio telephone integration"></a>
  <a href="docs/whatsapp-inbound-calling.md"><img src="https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&amp;logo=whatsapp&amp;logoColor=white" alt="WhatsApp inbound voice integration"></a>
</p>

HVACLine collects service requests, answers business-approved questions, and guides customers toward an available appointment while your team is on the job.

Three independent website templates share typed configuration and routing.
Phase 2 adds persisted websites, a basic configuration editor and server-managed
agent routing. Live non-HVAC voice acceptance and production onboarding remain
pending; the existing HVACLine product remains intact.

## What it does

- **Meet customers where they are.** Browser chat and voice, with telephone and inbound WhatsApp voice integrations.
- **Capture the job details.** Contact information, service address, equipment issue, requested service and preferred time.
- **Book against real availability.** Service areas, business hours and technician schedules determine offered slots; customers explicitly confirm before booking.
- **Keep the team informed.** One operations workspace for requests, appointments, calls, callbacks and handoffs.
- **Explore the business dashboard.** Open `/operations` for an orange-and-charcoal TailAdmin dashboard demo with fictional HVAC requests, appointments and follow-up. Connect a workspace separately to use its existing tools.
- **Support returning customers.** Appointment history, rescheduling and optional customer-controlled memory. Google Calendar sync and booking emails/reminders are opt-in integrations.

## From request to appointment

1. A customer describes the issue and reviews their details with the receptionist.
2. HVACLine checks the configured service area and schedule, then holds an available time.
3. The customer confirms, and the saved appointment appears in the operations workspace.

Answers stay within approved business information. Hazards and unsupported requests go to staff; the receptionist does not diagnose equipment or invent prices. The application stores no raw audio.

## Configurable Voice AI websites

Connected Operations → Websites provides a restricted administrator editor:
create from three distinct templates, customize branding/content/colors/fonts/
sections/FAQs/actions, preview, save private drafts, publish immutable versions,
restore history and unpublish. Published sites use `/sites/[slug]`; ordinary
content changes require no rebuild. Drafts cannot change live agent/knowledge
bindings. Images are selected from approved artwork; uploads/custom domains are
not exposed. Voice/Text reuse signed ElevenLabs sessions and customer MFA.
Website inquiries use the existing lead workflow; booking and memory stay disabled
for those sessions. Existing HVAC account workflows remain separate.

The platform defaults off and remains development/test gated. Management requires
the existing business administrator token; customer sign-in does not grant owner
access. Migrations `20261112_0022` and `20261113_0023`, configured agents and owner
acceptance are required. Production self-service onboarding is not ready.

The owner stopped verification; final edits are **unverified**. Earlier web
verification and focused backend checks passed, while broader Python checks
reported unresolved failures. Exact results, changed source, deployment/setup
commands and one acceptance checklist: [Platform handoff](docs/website-platform-phase2.md).
No deployment, target migration or hosted agent change was performed.

The homepage retains the hero and calling entry. The public template showcase
and its navigation links are removed; `/demos/[slug]` returns not-found. Packages,
Services, booking walkthrough and HVAC-owner FAQ are removed; pricing lives on
`/pricing`. Header/footer integrations include short descriptions.

Showcase removal is **unverified**. Owner command: `npm run verify:web`. Manually
confirm that homepage, desktop/mobile navigation and published-site utility links
contain no demo collection links; `/demos/hvac`, `/demos/real-estate` and
`/demos/appointments` return 404; booking, calling, pricing and website editing
remain available.

## GoHighLevel integration

Connected Operations → Integrations adds an opt-in **GoHighLevel** connection:
confirmed leads match/create contacts and receive separate opportunities, with
booking/handoff stages, encrypted private tokens and durable delivery/recovery.
Existing scheduling remains authoritative. The integration defaults off, remains
development/test gated and is **unverified**; no migration or live GHL operation
has run. [Setup, exact deferred commands and acceptance](docs/gohighlevel.md).

The hero includes **GoHighLevel · CRM sync · Preview**. The next integration is
n8n event delivery after controlled GHL acceptance; the linked guide specifies
the follow-up slice and its limits.

## Dashboard demo

Choose **Dashboard** in the homepage navigation or open `/operations`.
The initial view uses clearly labeled fictional sample data and does not contact
the backend, request microphone access, or change bookings. Explore Overview,
Service requests, Appointments, Calls, Follow-up, Scheduling, Receptionist,
Knowledge base and Maintenance hours. Browser voice appears when that feature
is enabled. Sample appointments use November 12, 2026 as their example day.

The dashboard adapts TailAdmin's sidebar, header, metric cards and tables to
HVACLine's orange branding, existing light/dark theme and responsive navigation.
Selected components use scoped CSS Modules without adding dependencies.
[TailAdmin source](https://github.com/TailAdmin/free-nextjs-admin-dashboard) ·
[Retained MIT license](apps/web/src/features/operations/TAILADMIN-LICENSE.txt).

**Connect your workspace** opens the existing admin-token gate. Connected mode
uses stored records and preserves booking, scheduling, knowledge, receptionist
and maintenance-labor tools. Counts describe up to 100 loaded records per queue,
not business-wide totals. Follow-up remains a read-only queue; production
business login, roles and onboarding are separate work.

**Implementation is unverified.** No tests, builds, linting, type checks,
formatters, services or runtime checks were run for this dashboard change.
Owner checks, when explicitly authorized:

```bash
npm run verify:web
```

- At 320, 768 and 1440px, inspect light/dark colors, table scrolling, readable statuses and absence of page overflow.
- Use keyboard navigation to collapse/expand the desktop sidebar, open the mobile drawer, close it with Escape, and confirm focus returns to its trigger.
- Explore every demo section and confirm there are no API requests, microphone prompts or working booking/payment mutations.
- Connect an authorized workspace; check empty/loading/error states, refresh, counts/timezone and the existing booking/editor/calendar/labor flows with approved sample records.
- Confirm the homepage's Dashboard demo link works and customer booking, pricing and billing retain their layouts.

## Explore

[Setup guide](docs/development-setup.md) · [Browser chat & voice](docs/customer-chat.md) · [Telephone](docs/hvacline-live-validation.md) · [WhatsApp voice](docs/whatsapp-inbound-calling.md) · [Calendar & reminders](docs/calendar-and-booking-messages.md) · [Architecture](docs/hvacline-architecture.md)

Optional development-only [local browser conversations](docs/local-browser-voice.md) use whisper.cpp, Ollama and Piper; implementation and runtime acceptance remain unverified.
