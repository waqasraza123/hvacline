"use client";

import { useRef, useState } from "react";
import { LoadingSpinner } from "@/components/loading-spinner";
import { requestApi } from "@/features/operations/api";
import type { Appointment } from "@/features/operations/api";
import { hours } from "./contracts";
import type { Labor } from "./contracts";

export function LaborRecorder({
  apiBaseUrl,
  token,
  appointments,
}: {
  apiBaseUrl: string;
  token: string;
  appointments: Appointment[];
}) {
  const [appointmentId, setAppointmentId] = useState("");
  const [minutes, setMinutes] = useState(60);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState<Labor>();
  const [pending, setPending] = useState<{
    request_id: string;
    appointment_id: string;
    minutes: number;
    work_completed: true;
  }>();
  const locked = useRef(false);
  return (
    <section className="ops-card">
      <h2>Record completed maintenance labor</h2>
      <p className="section-help">
        Sandbox billing uses actual technician labor. Package hours are used
        first, followed by paid extra hours. Booking length alone never consumes
        hours. The visit must belong to a signed-in homeowner.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (locked.current || !confirmed) return;
          locked.current = true;
          setBusy(true);
          setError("");
          setReceipt(undefined);
          const request = pending ?? {
            request_id: crypto.randomUUID(),
            appointment_id: appointmentId,
            minutes,
            work_completed: true as const,
          };
          setPending(request);
          void requestApi<Labor>(
            apiBaseUrl,
            token,
            "billing/labor",
            "POST",
            request,
          )
            .then((value) => {
              setReceipt(value);
              setPending(undefined);
              setConfirmed(false);
            })
            .catch((failure: unknown) => {
              if (
                failure instanceof Error &&
                "status" in failure &&
                typeof failure.status === "number" &&
                failure.status >= 400 &&
                failure.status < 500
              )
                setPending(undefined);
              setError(
                failure instanceof Error
                  ? failure.message
                  : "Labor could not be recorded. Retry the same entry.",
              );
            })
            .finally(() => {
              locked.current = false;
              setBusy(false);
            });
        }}
      >
        <label>
          Confirmed appointment
          <select
            required
            value={appointmentId}
            disabled={busy || !!pending}
            onChange={(event) => setAppointmentId(event.target.value)}
          >
            <option value="">Choose a visit</option>
            {appointments
              .filter((item) => item.status === "CONFIRMED")
              .map((item) => (
                <option value={item.id} key={item.id}>
                  {item.starts_at} · {item.team_key} · {item.id.slice(0, 8)}
                </option>
              ))}
          </select>
        </label>
        <label>
          Actual maintenance labor in minutes
          <input
            type="number"
            required
            min={1}
            max={1440}
            step={1}
            value={minutes}
            disabled={busy || !!pending}
            onChange={(event) => setMinutes(Number(event.target.value))}
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={confirmed}
            disabled={busy}
            onChange={(event) => setConfirmed(event.target.checked)}
          />{" "}
          I confirm this work has been completed and these are the actual labor
          minutes.
        </label>
        <button
          className="primary-link"
          disabled={busy || !confirmed || !appointmentId}
        >
          {busy ? (
            <LoadingSpinner label="Recording maintenance hours…" />
          ) : pending ? (
            "Retry the same labor entry"
          ) : (
            "Record completed labor"
          )}
        </button>
      </form>
      {error && (
        <p className="ops-error" role="alert">
          {error}
        </p>
      )}
      {receipt && (
        <p className="ops-message" role="status">
          Recorded {hours(receipt.minutes)} hours:{" "}
          {hours(receipt.package_minutes)} package hours and{" "}
          {hours(receipt.purchased_minutes)} purchased hours. This action does
          not charge a card.
        </p>
      )}
    </section>
  );
}
