"use client";
import Link from "next/link";
import { useState } from "react";
import { Brand } from "@/components/brand";
import { ScheduleForm } from "./schedule-form";
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

export function OperationsWorkspace({ apiBaseUrl }: { apiBaseUrl: string }) {
  const [token, setToken] = useState("");
  const [data, setData] = useState<Operations | null>(null);
  const [schedule, setSchedule] = useState<ScheduleResponse | null>(null);
  const [tab, setTab] = useState("requests");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [selected, setSelected] = useState<ServiceRequest | null>(null);
  const [day, setDay] = useState("");
  const [availability, setAvailability] = useState<Availability | null>(null);
  const [reservation, setReservation] = useState<Appointment | null>(null);
  const api = <T,>(path: string, method = "GET", body?: unknown) =>
    requestApi<T>(apiBaseUrl, token, path, method, body);
  async function load() {
    const [operations, configuration] = await Promise.all([
      api<Operations>("hvac/operations"),
      api<ScheduleResponse>("hvac/schedule"),
    ]);
    setData(operations);
    setSchedule(configuration);
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
    <main className="ops-shell">
      <nav className="top-nav">
        <Brand />
        <div className="nav-links">
          <Link href="/phone-demo">Phone sandbox</Link>
          <Link href="/receptionist-settings">Receptionist</Link>
          <Link href="/approved-faqs">Knowledge</Link>
        </div>
      </nav>
      <div className="ops-heading">
        <div>
          <p className="eyebrow">YOUR SERVICE WORKSPACE</p>
          <h1>Keep the next job moving.</h1>
          <p className="section-help">
            Development access · fictional data only · production sign-in
            pending
          </p>
        </div>
        {data && (
          <button onClick={() => void act(load)} disabled={busy}>
            Refresh workspace ↻
          </button>
        )}
      </div>
      {!data && (
        <form
          className="ops-card access-form"
          onSubmit={(event) => {
            event.preventDefault();
            void act(load);
          }}
        >
          <h2>Connect to your development workspace</h2>
          <p className="section-help">
            Enter the configured demo admin token. It stays in this page’s
            memory and is sent only to your backend.
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
            {busy ? "Connecting…" : "Open workspace"}
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
          <p className="section-help">
            Showing the latest 100 records per queue. Times in{" "}
            {schedule?.configuration?.timezone ?? "America/New_York"}.
          </p>
          <section className="ops-metrics" aria-label="Current queues">
            {[
              ["Incoming calls", data.calls.length],
              ["Service requests", data.service_requests.length],
              [
                "Confirmed bookings",
                data.appointments.filter((row) => row.status === "CONFIRMED")
                  .length,
              ],
              [
                "Missed / failed calls",
                data.calls.filter((row) =>
                  ["FAILED", "REJECTED"].includes(row.status),
                ).length,
              ],
              [
                "Pending callbacks",
                data.handoffs.filter((row) => row.kind === "CALLBACK").length,
              ],
              [
                "Human handoffs",
                data.handoffs.filter((row) => row.kind === "LIVE_TRANSFER")
                  .length,
              ],
            ].map(([label, value]) => (
              <article key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </article>
            ))}
          </section>
          <div
            className="ops-tabs"
            role="tablist"
            aria-label="Workspace sections"
          >
            {["requests", "bookings", "calls", "handoffs", "scheduling"].map(
              (name) => (
                <button
                  role="tab"
                  aria-selected={tab === name}
                  key={name}
                  onClick={() => setTab(name)}
                >
                  {name}
                </button>
              ),
            )}
          </div>
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
                      <a href={"tel:" + row.customer.phone}>
                        {row.customer.phone}
                      </a>
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
                            disabled={busy}
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
                data.appointments.map((row) => (
                  <article className="request-row" key={row.id}>
                    <div>
                      <h3>{timestamp(row.starts_at)}</h3>
                      <p>
                        {schedule?.configuration?.teams.find(
                          (team) => team.key === row.team_key,
                        )?.name ?? row.team_key}
                      </p>
                      <p>
                        {data.service_requests.find(
                          (request) => request.id === row.service_request_id,
                        )?.customer.full_name ?? "Service request"}
                      </p>
                    </div>
                    <span className="sample-badge">
                      {row.status === "HELD" &&
                      new Date(row.hold_expires_at) < new Date()
                        ? "EXPIRED"
                        : row.status}
                    </span>
                    {row.status === "CONFIRMED" && (
                      <button
                        disabled={busy}
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
                  </article>
                ))
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
                data.calls.map((row) => (
                  <article className="request-row" key={row.id}>
                    <div>
                      <h3>
                        {row.caller_number ?? "Caller number unavailable"}
                      </h3>
                      <p>{timestamp(row.received_at)}</p>
                    </div>
                    <span className="sample-badge">
                      {row.status.replaceAll("_", " ")}
                    </span>
                  </article>
                ))
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
                data.handoffs.map((row) => (
                  <article className="request-row" key={row.id}>
                    <div>
                      <h3>{row.kind.replaceAll("_", " ")}</h3>
                      <p>{row.reason}</p>
                    </div>
                    <span className="sample-badge">{row.status}</span>
                  </article>
                ))
              )}
            </section>
          )}
          {tab === "scheduling" && schedule && (
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
          )}
        </>
      )}
    </main>
  );
}
