# HVACLine AI Delivery Status

The active product is exclusively an AI phone receptionist and booking workspace for U.S. HVAC service businesses. This plan supersedes the insurance roadmap and archived continuation notes.

## Current implementation

Reuse the existing signed Twilio/ElevenLabs phone path, consent and readback receipts, approved knowledge, lead creation, callbacks, and human transfers. Add HVAC service requests, internal technician scheduling, reservations, booking confirmation, cancellation/rescheduling APIs, and an operations workspace. Preserve Neon and existing deployment identifiers.

## Acceptance gate

A synthetic caller reaches a configured business number, speaks to the AI receptionist, confirms contact and service details, receives an actually persisted appointment if configured, and the operator sees the request and booking. A mocked provider test does not satisfy this gate.

## Remaining production work

- Complete live carrier routing, ElevenLabs tool configuration, interruption/correction QA, transfer QA, and post-call delivery validation with an owner-authorized number.
- Implement production identity, roles, membership selection, account onboarding, per-tenant provider credentials and agent configuration. Current actor resolution is development-only.
- Complete Google OAuth connection, token vault integration, refresh, calendar selection, durable sync, conflict reconciliation, and live tests. The current Google HTTP adapter is not a connected integration.
- Complete caller verification for existing-customer lookup and telephone cancellation/rescheduling. Current rescheduling/cancellation APIs are for authenticated development operators only.
- Add durable notification outbox and delivery for confirmations, reminders, callbacks, and urgent handoffs. Dashboard persistence does not prove notification delivery.
- Add tenant usage and cost metering, limits suitable for paid clients, billing, observability, retention/deletion automation, deployment recovery, and production acceptance testing.
- Extend the workspace with account onboarding, role administration, lead/callback completion actions, and rescheduling UI. Do not present these as shipped.

The product remains gated to synthetic development use until these launch blockers are resolved. No production-ready claim is authorized by unit tests alone.
