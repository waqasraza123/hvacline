"use client";
import { useState } from "react";
import { LaborRecorder } from "@/features/billing/labor-recorder";
import { LoadingSpinner } from "@/components/loading-spinner";
import { ApprovedFaqManager } from "@/features/approved-faqs/approved-faq-manager";
import { ReceptionistSettingsEditor } from "@/features/receptionist/receptionist-settings";
import { BrowserVoicePanel } from "@/features/conversation/browser-voice-panel";
import { ScheduleForm } from "./schedule-form";
import { CalendarConnections } from "./calendar-connections";
import { DashboardShell } from "./dashboard-shell";
import type { OperationsSection } from "./dashboard-shell";
import { DashboardOverview } from "./dashboard-overview";
import { DashboardTable, StatusBadge } from "./dashboard-table";
import { WebsiteManager } from "@/features/websites/website-manager";
import { GhlIntegration } from "@/features/ghl/integration";
import {
  demoOperations,
  demoSchedule,
  demoReferenceTime,
  DemoSection,
} from "./dashboard-demo";
import styles from "./dashboard.module.css";
import { requestApi } from "./api";
import type {
  Appointment,
  Availability,
  Operations,
  Schedule,
  ScheduleResponse,
  ServiceRequest,
  Slot,
} from "./api";

export function OperationsWorkspace({
  apiBaseUrl,
  conversationAiEnabled,
}: {
  apiBaseUrl: string;
  conversationAiEnabled: boolean;
}) {
  const [token, setToken] = useState("");
  const [demo, setDemo] = useState(true);
  const [data, setData] = useState<Operations | null>(demoOperations);
  const [schedule, setSchedule] = useState<ScheduleResponse | null>(
    demoSchedule,
  );
  const [tab, setTab] = useState<OperationsSection>("overview");
  const [loadedAt, setLoadedAt] = useState(demoReferenceTime);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [selected, setSelected] = useState<ServiceRequest | null>(null);
  const [day, setDay] = useState("");
  const [availability, setAvailability] = useState<Availability | null>(null);
  const [reservation, setReservation] = useState<Appointment | null>(null);
  const api = <T,>(path: string, method = "GET", body?: unknown) => {
    if (demo) throw new Error("Connect a workspace to use this action.");
    return requestApi<T>(apiBaseUrl, token, path, method, body);
  };
  async function load() {
    const [operations, configuration] = await Promise.all([
      api<Operations>("hvac/operations"),
      api<ScheduleResponse>("hvac/schedule"),
    ]);
    setData(operations);
    setSchedule(configuration);
    setLoadedAt(Date.now());
  }
  async function act(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await task();
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "The request could not be completed.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function reserve(slot: Slot) {
    if (!selected) return;
    const result = await api<Appointment>("hvac/reservations", "POST", {
      service_request_id: selected.id,
      team_key: slot.team_key,
      starts_at: slot.starts_at,
      idempotency_key: crypto.randomUUID(),
    });
    setReservation(result);
    setAvailability(null);
    setMessage("Reserved for five minutes. Confirm the appointment below.");
  }
  function timestamp(value: string) {
    return new Intl.DateTimeFormat("en-US", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: schedule?.configuration?.timezone ?? "America/New_York",
    }).format(new Date(value));
  }
  return (
    <DashboardShell
      section={tab}
      onSelect={setTab}
      connected={data !== null}
      busy={busy}
      conversationAiEnabled={conversationAiEnabled}
      onRefresh={() => {
        if (!demo) void act(load);
      }}
      demo={demo}
    >
      {demo && (
        <div className={styles.demoBanner}>
          <div>
            <strong>Demo workspace · sample data</strong>
            <p>
              Explore the design. Calls, visits and business details are
              fictional; actions do not change a live workspace.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setDemo(false);
              setData(null);
              setSchedule(null);
              setTab("overview");
              setMessage("");
              setError("");
            }}
          >
            Connect your workspace
          </button>
        </div>
      )}
      {!data && (
        <form
          className="ops-card access-form"
          onSubmit={(event) => {
            event.preventDefault();
            void act(load);
          }}
        >
          <h2>Connect to your workspace</h2>
          <p className="section-help">
            Enter the configured admin token. It stays in this page’s memory and
            is sent only to your backend.
          </p>
          <label>
            Admin token
            <input
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              autoComplete="off"
            />
          </label>
          <button className="primary-link" disabled={busy}>
            {busy ? <LoadingSpinner label="Connecting…" /> : "Open dashboard"}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              setDemo(true);
              setToken("");
              setData(demoOperations);
              setSchedule(demoSchedule);
              setLoadedAt(demoReferenceTime);
              setError("");
              setMessage("");
            }}
          >
            Explore demo instead
          </button>
        </form>
      )}
      {error && (
        <p className="ops-error" role="alert">
          {error}
        </p>
      )}
      {message && (
        <p className="ops-message" role="status">
          {message}
        </p>
      )}
      {data && (
        <>
          <p className={styles.queueNote}>
            {demo ? "Sample schedule for November 12, 2026. " : ""}
            Up to 100 latest records per queue. Counts reflect loaded records,
            not business totals. Times in{" "}
            {schedule?.configuration?.timezone ?? "America/New_York"}.
            {!demo && (
              <>
                {" "}
                Last refreshed {timestamp(new Date(loadedAt).toISOString())}.
              </>
            )}
          </p>
          {tab === "overview" && (
            <DashboardOverview
              data={data}
              schedule={schedule}
              loadedAt={loadedAt}
              timestamp={timestamp}
              onSelect={setTab}
            />
          )}
          {demo && <DemoSection section={tab} />}
          {!demo && tab === "integrations" && (
            <GhlIntegration apiBaseUrl={apiBaseUrl} token={token} />
          )}
          {!demo && tab === "websites" && (
            <WebsiteManager apiBaseUrl={apiBaseUrl} token={token} />
          )}
          {!demo && tab === "maintenance hours" && (
            <LaborRecorder
              apiBaseUrl={apiBaseUrl}
              token={token}
              appointments={data.appointments}
            />
          )}
          {tab === "requests" && (
            <section className="ops-card">
              <h2>Service requests</h2>
              {data.service_requests.length === 0 ? (
                <p className="empty-state">
                  No confirmed service requests yet. Incoming calls appear after
                  the caller confirms their details.
                </p>
              ) : (
                data.service_requests.map((row) => (
                  <article className="request-row" key={row.id}>
                    <div>
                      <span className="sample-badge">
                        {row.service.kind.replaceAll("_", " ")}
                      </span>
                      <h3>{row.customer.full_name}</h3>
                      <p>{row.service.equipment_issue}</p>
                      <p className="section-help">
                        {row.customer.address.line1},{" "}
                        {row.customer.address.city},{" "}
                        {row.customer.address.state_code}{" "}
                        {row.customer.address.postal_code}
                      </p>
                      {row.customer.phone && (
                        <a href={"tel:" + row.customer.phone}>
                          {row.customer.phone}
                        </a>
                      )}
                      <p className="section-help">
                        Preferred: {row.service.preferred_window}
                      </p>
                    </div>
                    <div>
                      <span
                        className={
                          row.service.hazardous_condition
                            ? "ops-urgent"
                            : "sample-badge"
                        }
                      >
                        {row.status.replaceAll("_", " ")}
                      </span>
                      {!row.service.hazardous_condition &&
                        row.status !== "BOOKED" && (
                          <button
                            disabled={busy || demo}
                            onClick={() => {
                              setSelected(row);
                              setAvailability(null);
                              setReservation(null);
                            }}
                          >
                            Find an appointment
                          </button>
                        )}
                    </div>
                  </article>
                ))
              )}
            </section>
          )}
          {selected && tab === "requests" && (
            <section className="ops-card">
              <h2>Book {selected.customer.full_name}</h2>
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void act(async () => {
                    setAvailability(
                      await api<Availability>("hvac/availability", "POST", {
                        postal_code: selected.customer.address.postal_code,
                        day,
                      }),
                    );
                  });
                }}
              >
                <label>
                  Service date
                  <input
                    type="date"
                    required
                    value={day}
                    onChange={(event) => setDay(event.target.value)}
                  />
                </label>
                <button disabled={busy}>Check availability</button>
                <button type="button" onClick={() => setSelected(null)}>
                  Close
                </button>
              </form>
              {availability && (
                <div className="slot-grid">
                  {availability.message && <p>{availability.message}</p>}
                  {availability.slots.map((slot) => (
                    <button
                      disabled={busy}
                      key={slot.team_key + slot.starts_at}
                      onClick={() => void act(() => reserve(slot))}
                    >
                      {timestamp(slot.starts_at)} · {slot.team_key}
                    </button>
                  ))}
                </div>
              )}
              {reservation && (
                <div className="ops-message">
                  <p>
                    {timestamp(reservation.starts_at)} · {reservation.status}
                  </p>
                  <button
                    disabled={busy || reservation.status !== "HELD"}
                    onClick={() =>
                      void act(async () => {
                        const result = await api<Appointment>(
                          "hvac/appointments/" + reservation.id + "/confirm",
                          "POST",
                          { explicit_confirmation: true },
                        );
                        if (result.status !== "CONFIRMED")
                          throw new Error("The appointment was not confirmed.");
                        setReservation(result);
                        await load();
                        setMessage("Appointment confirmed and saved.");
                      })
                    }
                  >
                    Confirm agreed appointment
                  </button>
                </div>
              )}
            </section>
          )}
          {tab === "bookings" && (
            <section className="ops-card">
              <h2>Appointment calendar</h2>
              {data.appointments.length === 0 ? (
                <p className="empty-state">
                  No appointments. Configure your scheduling rules before taking
                  bookings.
                </p>
              ) : (
                <DashboardTable
                  caption="Appointment calendar"
                  headings={[
                    "Appointment",
                    "Team",
                    "Customer",
                    "Status",
                    "Action",
                  ]}
                >
                  {data.appointments.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <strong>{timestamp(row.starts_at)}</strong>
                      </td>
                      <td>
                        {schedule?.configuration?.teams.find(
                          (team) => team.key === row.team_key,
                        )?.name ?? row.team_key}
                      </td>
                      <td>
                        {data.service_requests.find(
                          (request) => request.id === row.service_request_id,
                        )?.customer.full_name ?? "Service request"}
                      </td>
                      <td>
                        <StatusBadge
                          status={
                            row.status === "HELD" &&
                            new Date(row.hold_expires_at) < new Date()
                              ? "EXPIRED"
                              : row.status
                          }
                        />
                      </td>
                      <td>
                        {row.status === "CONFIRMED" && (
                          <button
                            disabled={busy || demo}
                            onClick={() =>
                              void act(async () => {
                                await api(
                                  "hvac/appointments/" + row.id + "/cancel",
                                  "POST",
                                  { explicit_confirmation: true },
                                );
                                await load();
                                setMessage("Appointment cancelled.");
                              })
                            }
                          >
                            Cancel appointment
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </DashboardTable>
              )}
            </section>
          )}
          {tab === "calls" && (
            <section className="ops-card">
              <h2>Incoming calls</h2>
              {data.calls.length === 0 ? (
                <p className="empty-state">
                  No incoming calls yet. Carrier routing and a configured number
                  are required.
                </p>
              ) : (
                <DashboardTable
                  caption="Incoming calls"
                  headings={["Caller", "Received", "Status"]}
                >
                  {data.calls.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <strong>
                          {row.caller_number ?? "Caller number unavailable"}
                        </strong>
                      </td>
                      <td>{timestamp(row.received_at)}</td>
                      <td>
                        <StatusBadge status={row.status} />
                      </td>
                    </tr>
                  ))}
                </DashboardTable>
              )}
            </section>
          )}
          {tab === "handoffs" && (
            <section className="ops-card">
              <h2>Human follow-up</h2>
              {data.handoffs.length === 0 ? (
                <p className="empty-state">
                  No pending callbacks or human handoffs.
                </p>
              ) : (
                <DashboardTable
                  caption="Pending human follow-up"
                  headings={["Follow-up", "Reason", "Status"]}
                >
                  {data.handoffs.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <strong>{row.kind.replaceAll("_", " ")}</strong>
                      </td>
                      <td>{row.reason}</td>
                      <td>
                        <StatusBadge status={row.status} />
                      </td>
                    </tr>
                  ))}
                </DashboardTable>
              )}
            </section>
          )}
          {!demo && tab === "receptionist" && (
            <ReceptionistSettingsEditor
              apiBaseUrl={apiBaseUrl}
              adminToken={token}
              embedded
            />
          )}
          {!demo && tab === "browser voice" && (
            <BrowserVoicePanel apiBaseUrl={apiBaseUrl} adminToken={token} />
          )}
          {!demo && tab === "knowledge" && (
            <ApprovedFaqManager
              apiBaseUrl={apiBaseUrl}
              adminToken={token}
              embedded
            />
          )}
          {!demo && tab === "scheduling" && schedule && (
            <>
              <CalendarConnections
                baseUrl={apiBaseUrl}
                token={token}
                schedule={schedule}
              />
              <ScheduleForm
                key={schedule.version}
                value={schedule}
                busy={busy}
                save={async (configuration: Schedule) => {
                  setBusy(true);
                  try {
                    await api("hvac/schedule", "PUT", configuration);
                    await load();
                    setMessage("Scheduling rules saved.");
                  } finally {
                    setBusy(false);
                  }
                }}
              />
            </>
          )}
        </>
      )}
    </DashboardShell>
  );
}
