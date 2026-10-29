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

## What it does

- **Meet customers where they are.** Browser chat and voice, with telephone and inbound WhatsApp voice integrations.
- **Capture the job details.** Contact information, service address, equipment issue, requested service and preferred time.
- **Book against real availability.** Service areas, business hours and technician schedules determine offered slots; customers explicitly confirm before booking.
- **Keep the team informed.** One operations workspace for requests, appointments, calls, callbacks and handoffs.
- **Support returning customers.** Appointment history, rescheduling and optional customer-controlled memory. Google Calendar sync and booking emails/reminders are opt-in integrations.

## From request to appointment

1. A customer describes the issue and reviews their details with the receptionist.
2. HVACLine checks the configured service area and schedule, then holds an available time.
3. The customer confirms, and the saved appointment appears in the operations workspace.

Answers stay within approved business information. Hazards and unsupported requests go to staff; the receptionist does not diagnose equipment or invent prices. The application stores no raw audio.

## Explore

[Setup guide](docs/development-setup.md) · [Browser chat & voice](docs/customer-chat.md) · [Telephone](docs/hvacline-live-validation.md) · [WhatsApp voice](docs/whatsapp-inbound-calling.md) · [Calendar & reminders](docs/calendar-and-booking-messages.md) · [Architecture](docs/hvacline-architecture.md)
