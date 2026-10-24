# HVACLine AI Architecture

The web app, FastAPI API, and separate worker retain the established repository structure. PostgreSQL is the authority for business state. The agent invokes authenticated HTTP tools; it has no database credentials.

## Telephone and intake

Twilio signatures authenticate inbound calls and transfer callbacks. The called number determines the business. ElevenLabs tools use the existing server-only bearer secret, and the backend verifies the active call/session relationship and expiry. ElevenLabs post-call events retain existing HMAC timestamp verification and event replay checks.

Phone intake requires consent and verbal readback. A new `service-request` tool requires the existing confirmation receipt and matching caller name and callback number, plus explicit confirmation of structured HVAC details. It persists a service request without retaining transcript text. Transcript/customer/lead finalization remains in the existing signed post-call transaction. The HVAC customer address feeds that finalization; transcripts remain excluded from the operations projection.

## Booking

`business_schedules` stores versioned per-business configuration. `hvac_service_requests` stores confirmed HVAC intake. `hvac_appointments` stores HELD, CONFIRMED, CANCELLED, and EXPIRED appointment states. Expired holds stop blocking capacity even before any cleanup process runs.

Availability intersects business and team hours in the configured IANA timezone, applies ZIP-code coverage, notice, duration, horizon, and team time off, then removes overlapping confirmed appointments and active holds. Ambiguous and nonexistent daylight-saving boundary times are not offered.

All reservation, confirmation, cancellation, and rescheduling mutations lock the business schedule row. This serializes capacity changes within one business across API processes. The agency is also locked for settings creation and updates. Booking keys are unique within the tenant, with payload fingerprints preventing different requests from sharing a key. Appointments have a composite tenant/request foreign key. Rescheduling cancels the original and confirms its replacement in one transaction. Unsuccessful replacements roll back.

The current internal calendar requires explicit operator configuration and accurate maintenance of team availability. The provider-neutral `CalendarAdapter` and Google adapter implement free/busy, deterministic event creation with replay verification, and cancellation. They are not yet connected to the booking transaction. Runtime OAuth, durable synchronization, failure reconciliation, and live authorization are blockers before external calendars can be offered.

## Access and deployment boundaries

Every HVAC data query is scoped to the resolved business. Phone tools additionally bind requested resources to the current call. Development administration reuses the established actor resolver and optional hosted-sandbox token gate. All development operations stay hidden outside development. This is not finished production authentication or multi-tenant account onboarding.

No secrets are stored in business records, browser storage, or audit payloads. No raw audio is stored. New booking audit events contain record references and state only. Production retention automation, durable outbound notifications, usage/cost billing, tenant roles, and account lifecycle remain incomplete.

Existing table names, migration history, Python package and CLI names, and workspace namespace remain stable. The legacy receptionist categories column is mapped to `supported_service_categories` at the application boundary.
