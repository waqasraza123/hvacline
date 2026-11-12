import type { Operations, ScheduleResponse } from "./api";
import type { OperationsSection } from "./dashboard-shell";
import { DashboardTable, StatusBadge } from "./dashboard-table";
import styles from "./dashboard.module.css";

export const demoReferenceTime = Date.parse("2026-11-12T13:00:00Z");

export const demoOperations: Operations = {
  service_requests: [
    {
      id: "demo-request-1",
      status: "BOOKED",
      confirmed_at: "2026-11-12T12:30:00Z",
      customer: {
        full_name: "Sample homeowner A",
        phone: "",
        address: {
          line1: "Sample service address",
          city: "New York",
          state_code: "NY",
          postal_code: "10001",
        },
      },
      service: {
        kind: "AC_REPAIR",
        equipment_issue: "Cooling system is running but not cooling the home.",
        preferred_window: "Thursday morning",
        hazardous_condition: false,
      },
    },
    {
      id: "demo-request-2",
      status: "BOOKED",
      confirmed_at: "2026-11-12T12:40:00Z",
      customer: {
        full_name: "Sample homeowner B",
        phone: "",
        address: {
          line1: "Sample service address",
          city: "New York",
          state_code: "NY",
          postal_code: "10001",
        },
      },
      service: {
        kind: "MAINTENANCE",
        equipment_issue: "Seasonal heating maintenance visit.",
        preferred_window: "Thursday afternoon",
        hazardous_condition: false,
      },
    },
    {
      id: "demo-request-3",
      status: "OPEN",
      confirmed_at: "2026-11-12T12:45:00Z",
      customer: {
        full_name: "Sample homeowner C",
        phone: "",
        address: {
          line1: "Sample service address",
          city: "New York",
          state_code: "NY",
          postal_code: "10001",
        },
      },
      service: {
        kind: "INSTALLATION",
        equipment_issue: "Request for a replacement system consultation.",
        preferred_window: "Friday morning",
        hazardous_condition: false,
      },
    },
    {
      id: "demo-request-4",
      status: "HANDOFF_REQUESTED",
      confirmed_at: "2026-11-12T12:50:00Z",
      customer: {
        full_name: "Sample homeowner D",
        phone: "",
        address: {
          line1: "Sample service address",
          city: "New York",
          state_code: "NY",
          postal_code: "10001",
        },
      },
      service: {
        kind: "HEATING_REPAIR",
        equipment_issue:
          "Reported safety concern routed to human attention; automatic booking is blocked.",
        preferred_window: "Staff follow-up required",
        hazardous_condition: true,
      },
    },
  ],
  appointments: [
    {
      id: "demo-appointment-1",
      service_request_id: "demo-request-1",
      team_key: "demo-team-1",
      starts_at: "2026-11-12T15:00:00Z",
      ends_at: "2026-11-12T16:00:00Z",
      status: "CONFIRMED",
      hold_expires_at: "2026-11-12T12:35:00Z",
    },
    {
      id: "demo-appointment-2",
      service_request_id: "demo-request-2",
      team_key: "demo-team-2",
      starts_at: "2026-11-12T19:00:00Z",
      ends_at: "2026-11-12T20:00:00Z",
      status: "CONFIRMED",
      hold_expires_at: "2026-11-12T12:45:00Z",
    },
  ],
  calls: [
    {
      id: "demo-call-1",
      status: "COMPLETED",
      received_at: "2026-11-12T12:25:00Z",
      caller_number: null,
    },
    {
      id: "demo-call-2",
      status: "COMPLETED",
      received_at: "2026-11-12T12:35:00Z",
      caller_number: null,
    },
    {
      id: "demo-call-3",
      status: "FAILED",
      received_at: "2026-11-12T12:40:00Z",
      caller_number: null,
    },
  ],
  handoffs: [
    {
      id: "demo-handoff-1",
      kind: "CALLBACK",
      status: "REQUESTED",
      reason:
        "Sample installation consultation: homeowner asked to discuss equipment options with the team.",
      lead_id: "demo-lead-1",
    },
    {
      id: "demo-handoff-2",
      kind: "LIVE_TRANSFER",
      status: "ACKNOWLEDGED",
      reason:
        "Sample heating request: staff follow-up needed after a safety concern.",
      lead_id: "demo-lead-2",
    },
  ],
};

export const demoSchedule: ScheduleResponse = {
  version: 1,
  configuration: {
    expected_version: 1,
    enabled: true,
    timezone: "America/New_York",
    postal_codes: ["10001"],
    windows: [{ weekday: 3, start: "09:00", end: "17:00" }],
    teams: [
      {
        key: "demo-team-1",
        name: "Cooling team",
        windows: [],
        unavailable_dates: [],
      },
      {
        key: "demo-team-2",
        name: "Heating team",
        windows: [],
        unavailable_dates: [],
      },
    ],
    duration_minutes: 60,
    notice_minutes: 120,
    horizon_days: 30,
    cancellation_notice_minutes: 120,
  },
};

export function DemoSection({ section }: { section: OperationsSection }) {
  if (section === "websites")
    return (
      <section className="ops-card">
        <h2>Your Voice AI websites</h2>
        <p className="section-help">
          Connect your workspace to create, customize and save business-owned
          websites. These static designs remain safe previews.
        </p>
        <a href="/#voice-demos">Explore the three website templates ↗</a>
      </section>
    );
  if (section === "scheduling")
    return (
      <section className="ops-card">
        <h2>Scheduling & service teams</h2>
        <p className="section-help">
          Sample booking rules and technician calendars. Connect a workspace to
          manage availability.
        </p>
        <dl className={styles.demoFields}>
          <div>
            <dt>Service area</dt>
            <dd>New York · ZIP 10001</dd>
          </div>
          <div>
            <dt>Business timezone</dt>
            <dd>America/New_York</dd>
          </div>
          <div>
            <dt>Visit duration</dt>
            <dd>60 minutes</dd>
          </div>
          <div>
            <dt>Booking notice</dt>
            <dd>2 hours</dd>
          </div>
        </dl>
        <DashboardTable
          caption="Sample service teams"
          headings={["Team", "Hours", "Calendar"]}
        >
          <tr>
            <td>
              <strong>Cooling team</strong>
            </td>
            <td>Monday–Friday · 9am–5pm</td>
            <td>Internal calendar</td>
          </tr>
          <tr>
            <td>
              <strong>Heating team</strong>
            </td>
            <td>Monday–Friday · 9am–5pm</td>
            <td>Internal calendar</td>
          </tr>
        </DashboardTable>
        <p className="section-help">
          Google Calendar sync and booking emails require separate setup in a
          connected workspace.
        </p>
      </section>
    );
  if (section === "receptionist")
    return (
      <section className="ops-card">
        <h2>Your AI receptionist</h2>
        <p className="section-help">
          Sample business profile. These values do not configure a live agent.
        </p>
        <div className={styles.demoFields}>
          <label>
            Business name
            <input readOnly value="HVACLine sample business" />
          </label>
          <label>
            Services
            <input
              readOnly
              value="Cooling, heating, installation, maintenance"
            />
          </label>
        </div>
        <label>
          Greeting
          <textarea
            readOnly
            value="Thanks for calling our HVAC service team. I’m the AI receptionist. How can I help with your heating or cooling today?"
          />
        </label>
        <label>
          Human handoff guidance
          <textarea
            readOnly
            value="Route safety concerns and unsupported requests to staff. Only offer appointments from confirmed availability and ask the customer to confirm before booking."
          />
        </label>
      </section>
    );
  if (section === "knowledge")
    return (
      <section className="ops-card">
        <h2>Business knowledge base</h2>
        <p className="section-help">
          Sample approved answers for the receptionist. Connect a workspace to
          search and edit its knowledge base.
        </p>
        {[
          [
            "What services do you offer?",
            "We help with AC repair, heating repair, installation consultations and routine HVAC maintenance.",
          ],
          [
            "Can I book an appointment?",
            "Share your service address and the type of help you need. Available appointments depend on the service area and team calendar.",
          ],
          [
            "Can you tell me the repair price?",
            "The team must review the work before providing a repair quote. The AI receptionist does not invent prices or diagnose equipment.",
          ],
        ].map(([question, answer]) => (
          <article key={question} className="request-row">
            <div>
              <h3>{question}</h3>
              <p>{answer}</p>
            </div>
            <StatusBadge status="APPROVED" />
          </article>
        ))}
      </section>
    );
  if (section === "maintenance hours")
    return (
      <section className="ops-card">
        <h2>Maintenance hours</h2>
        <p className="section-help">
          Track completed technician labor against homeowner maintenance
          packages. This example does not represent purchased hours or a
          payment.
        </p>
        <DashboardTable
          caption="Example maintenance hour entry"
          headings={["Visit", "Team", "Completed labor", "Billing mode"]}
        >
          <tr>
            <td>Sample seasonal maintenance</td>
            <td>Heating team</td>
            <td>60 minutes · example only</td>
            <td>
              <StatusBadge status="SANDBOX" />
            </td>
          </tr>
        </DashboardTable>
        <p className="section-help">
          Connect a workspace to record actual completed labor. Booking duration
          alone does not consume package hours.
        </p>
      </section>
    );
  if (section === "browser voice")
    return (
      <section className="ops-card">
        <h2>Browser voice</h2>
        <p className="section-help">
          Your receptionist can collect service details, answer approved
          questions and guide appointment booking through browser voice.
        </p>
        <p>
          Connect a workspace to use the operator voice panel. This preview does
          not request microphone access or start a conversation.
        </p>
      </section>
    );
  return null;
}
