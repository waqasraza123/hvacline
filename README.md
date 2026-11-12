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

The codebase also includes a Phase 1 multi-product website collection: three
independent visual templates share typed configuration and routing. The existing
HVACLine product remains intact; a full website editor and per-business voice
provisioning are future phases.

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

## Explore Voice AI Demos

The homepage's **Explore Voice AI Demos** gallery opens three complete example
websites. Each uses its own layout, content, theme and metadata:

| Website | Route | Design | Conversation boundary |
| --- | --- | --- | --- |
| HVACLine AI | `/demos/hvac` | Charcoal/orange industrial, equipment illustration and service workflow | Written example; existing `/book` account entry, with Voice/Text checked in the existing flow |
| Alder & Stone | `/demos/real-estate` | Warm editorial luxury, serif headlines and asymmetric architectural collection | Fictional brand and illustrated properties; no agent or inquiries submitted |
| Morrow Studio | `/demos/appointments` | Soft sage, spacious appointment studio and friendly welcome | Fictional studio; no agent, customer data or bookings |

Gallery artwork reuses the original local illustrations from the actual demos.
There are no third-party website screenshots, active property listings or
simulated successful bookings. Other demo businesses never default to the HVAC
agent. Connection links preserve existing authentication, consent and backend
availability checks; the new pages themselves do not start sessions.

`WebsiteTemplate`, `WebsiteConfiguration` and server-only `AgentConfiguration`
remain separate. Validated static records feed a shared source interface and
component registry, with three distinct layout components. Section order, brand,
approved asset references, colors, allowlisted fonts, content, navigation, CTAs
and SEO live in structured configuration. CSS Modules isolate template styling.
There is no database migration, new dependency, editor, upload endpoint or
publishing service in Phase 1.

**Implementation is unverified.** Focused regression tests were added but no
checks were executed under the active owner policy. Exact commands, manual
acceptance and the Phase 2/3 implementation plan:
[Multi-product website foundation](docs/multi-product-websites.md).

## Dashboard demo

Choose **Dashboard demo** in the homepage navigation or open `/operations`.
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
