"use client";

import { useRef, useState } from "react";
import { requestApi } from "../operations/api";
import type { Appointment, Availability, Slot } from "../operations/api";

export function BrowserBooking({
  apiBaseUrl,
  adminToken,
  serviceRequestId,
  postalCode,
  hazardous,
}: {
  apiBaseUrl: string;
  adminToken?: string;
  serviceRequestId: string;
  postalCode: string;
  hazardous: boolean;
}) {
  const [day, setDay] = useState("");
  const [availability, setAvailability] = useState<Availability>();
  const [appointment, setAppointment] = useState<Appointment>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const reservationRef = useRef<{ slot: string; key: string } | undefined>(
    undefined,
  );
  const busyRef = useRef(false);
  const api = <T,>(path: string, body: unknown) =>
    requestApi<T>(apiBaseUrl, adminToken ?? "", "hvac/" + path, "POST", body);
  async function act(task: () => Promise<void>) {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
    try {
      await task();
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Booking could not be completed.",
      );
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }
  async function reserve(slot: Slot) {
    const identity = slot.team_key + slot.starts_at;
    if (reservationRef.current?.slot !== identity) {
      reservationRef.current = { slot: identity, key: crypto.randomUUID() };
    }
    const result = await api<Appointment>("reservations", {
      service_request_id: serviceRequestId,
      team_key: slot.team_key,
      starts_at: slot.starts_at,
      idempotency_key: reservationRef.current.key,
    });
    setAppointment(result);
    setAvailability((current) =>
      current ? { ...current, slots: [] } : current,
    );
  }
  if (hazardous)
    return (
      <p role="status">
        Your request needs human attention. No appointment was booked. For
        immediate danger, contact emergency services.
      </p>
    );
  const timezone = availability?.timezone;
  function time(value: string) {
    return new Intl.DateTimeFormat("en-US", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: timezone ?? "UTC",
    }).format(new Date(value));
  }
  return (
    <div className="ops-card">
      <h3>Choose a service appointment</h3>
      <p>
        Your request is saved. An appointment is separate and requires
        confirmation below.
      </p>
      {!appointment && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void act(async () => {
              setAvailability(undefined);
              setAvailability(
                await api<Availability>("availability", {
                  postal_code: postalCode,
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
              disabled={busy}
              onChange={(event) => {
                setDay(event.target.value);
                setAvailability(undefined);
              }}
            />
          </label>
          <button disabled={busy}>Check real availability</button>
        </form>
      )}
      {availability && (
        <div className="slot-grid">
          <p>
            Times in {timezone ?? "UTC"}. {availability.message}
          </p>
          {!appointment && availability.slots.length === 0 && (
            <p>
              No appointments available for this selection. Try another date or
              ask the business to follow up.
            </p>
          )}
          {availability.slots.map((slot) => (
            <button
              key={slot.team_key + slot.starts_at}
              disabled={busy}
              onClick={() => void act(() => reserve(slot))}
            >
              {time(slot.starts_at)} · {slot.team_key}
            </button>
          ))}
        </div>
      )}
      {appointment && (
        <div role="status">
          <p>
            {time(appointment.starts_at)} · {timezone ?? "UTC"} ·{" "}
            {appointment.status}
          </p>
          {appointment.status === "HELD" && (
            <>
              <p>
                This temporary hold expires at{" "}
                {time(appointment.hold_expires_at)}. Confirm only if you agree
                to this appointment.
              </p>
              <button
                disabled={busy}
                onClick={() =>
                  void act(async () => {
                    const result = await api<Appointment>(
                      "appointments/" + appointment.id + "/confirm",
                      { explicit_confirmation: true },
                    );
                    if (result.status !== "CONFIRMED")
                      throw new Error(
                        "The appointment has not been confirmed.",
                      );
                    setAppointment(result);
                  })
                }
              >
                I agree — confirm appointment
              </button>
              <button
                disabled={busy}
                onClick={() =>
                  void act(async () => {
                    await api("appointments/" + appointment.id + "/cancel", {
                      explicit_confirmation: true,
                    });
                    setAppointment(undefined);
                    setAvailability(undefined);
                    reservationRef.current = undefined;
                  })
                }
              >
                Release hold and choose again
              </button>
            </>
          )}
          {appointment.status === "CONFIRMED" && (
            <p>Appointment confirmed and saved.</p>
          )}
        </div>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
