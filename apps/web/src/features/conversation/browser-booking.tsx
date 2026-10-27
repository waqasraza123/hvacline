"use client";

import { useEffect, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { OperationsApiError, requestApi } from "../operations/api";
import type { Appointment, Availability, Slot } from "../operations/api";
import { bookingFailure, holdRemainingSeconds } from "./booking-progress";
import type { BookingFailure, BookingProgress } from "./booking-progress";
import type { VoiceAppointment, VoiceBookingTool } from "./voice-booking";

export function BrowserBooking({
  apiBaseUrl,
  adminToken,
  serviceRequestId,
  postalCode,
  hazardous,
  initialAppointment,
  initialTimezone,
  initialFailure,
  onProgress,
  onAppointment,
}: {
  apiBaseUrl: string;
  adminToken?: string;
  serviceRequestId: string;
  postalCode: string;
  hazardous: boolean;
  initialAppointment?: Appointment;
  initialTimezone?: string;
  initialFailure?: BookingFailure;
  onProgress?: Dispatch<SetStateAction<BookingProgress>>;
  onAppointment?: (value: VoiceAppointment | undefined) => void;
}) {
  const [day, setDay] = useState("");
  const [availability, setAvailability] = useState<Availability>();
  const [appointment, setAppointment] = useState<Appointment | undefined>(
    initialAppointment,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [failureState, setFailureState] = useState<BookingFailure | undefined>(
    initialFailure,
  );
  const [inheritedFailure] = useState(initialFailure);
  const reservationRef = useRef<{ slot: string; key: string } | undefined>(
    undefined,
  );
  const busyRef = useRef(false);
  const requestStartedRef = useRef(false);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (appointment?.status !== "HELD") return;
    const refresh = window.setTimeout(() => setNow(Date.now()), 0);
    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => {
      window.clearTimeout(refresh);
      window.clearInterval(interval);
    };
  }, [appointment]);
  const api = <T,>(path: string, body: unknown) => {
    requestStartedRef.current = true;
    return requestApi<T>(
      apiBaseUrl,
      adminToken ?? "",
      "hvac/" + path,
      "POST",
      body,
    );
  };
  async function act(operation: VoiceBookingTool, task: () => Promise<void>) {
    if (busyRef.current) return;
    if (failureState?.uncertain && failureState.operation !== operation) {
      setError("Retry the previous action before choosing another time.");
      return;
    }
    busyRef.current = true;
    requestStartedRef.current = false;
    setBusy(true);
    setError("");
    setFailureState(undefined);
    onProgress?.((current) => ({
      ...current,
      pending: operation,
      failure: undefined,
    }));
    try {
      await task();
    } catch (failure) {
      const nextFailure =
        failureState?.uncertain && !requestStartedRef.current
          ? failureState
          : bookingFailure(operation, failure, requestStartedRef.current);
      setFailureState(nextFailure);
      onProgress?.((current) => ({ ...current, failure: nextFailure }));
      setError(
        failure instanceof Error
          ? failure.message
          : "Booking could not be completed.",
      );
    } finally {
      busyRef.current = false;
      setBusy(false);
      onProgress?.((current) => ({ ...current, pending: undefined }));
    }
  }
  async function reserve(slot: Slot) {
    const identity = slot.team_key + slot.starts_at;
    if (reservationRef.current && reservationRef.current.slot !== identity)
      throw new Error(
        "The previous reservation is unresolved. Retry the same selected time.",
      );
    if (reservationRef.current?.slot !== identity) {
      reservationRef.current = { slot: identity, key: crypto.randomUUID() };
    }
    let result: Appointment;
    try {
      result = await api<Appointment>("reservations", {
        service_request_id: serviceRequestId,
        team_key: slot.team_key,
        starts_at: slot.starts_at,
        idempotency_key: reservationRef.current.key,
      });
    } catch (failure) {
      if (
        failure instanceof OperationsApiError &&
        [400, 404, 409, 410, 422].includes(failure.status)
      )
        reservationRef.current = undefined;
      throw failure;
    }
    setAppointment(result);
    if (timezone)
      onAppointment?.({ appointment: result, timezone, readback: "" });
    setAvailability((current) =>
      current ? { ...current, slots: [] } : current,
    );
  }
  if (hazardous)
    return (
      <p role="status">
        Your request needs human attention.{" "}
        {appointment?.status === "CONFIRMED"
          ? "Your existing appointment remains saved; no new appointment can be booked here."
          : "No appointment was booked."}{" "}
        For immediate danger, contact emergency services.
      </p>
    );
  if (
    inheritedFailure?.uncertain &&
    inheritedFailure.operation === "reserve_appointment" &&
    !initialAppointment
  )
    return (
      <p role="status">
        The previous reservation result is unresolved. Check My appointments or
        ask the business to review it before starting another booking.
      </p>
    );
  const timezone = availability?.timezone ?? initialTimezone;
  const holdExpired =
    appointment?.status === "HELD" &&
    holdRemainingSeconds(
      { appointment, timezone: timezone ?? "UTC", readback: "" },
      now,
    ) === 0;
  const confirmationUnresolved =
    failureState?.uncertain && failureState.operation === "confirm_appointment";
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
            void act("check_appointment_availability", async () => {
              setAvailability(undefined);
              onProgress?.((current) => ({
                ...current,
                availability: undefined,
              }));
              const result = await api<Availability>("availability", {
                postal_code: postalCode,
                day,
              });
              setAvailability(result);
              onProgress?.((current) => ({ ...current, availability: result }));
            });
          }}
        >
          <label>
            Service date
            <input
              type="date"
              required
              value={day}
              disabled={busy || failureState?.uncertain}
              onChange={(event) => {
                setDay(event.target.value);
                setAvailability(undefined);
                setError("");
                setFailureState(undefined);
                onProgress?.((current) => ({
                  ...current,
                  availability: undefined,
                  failure: undefined,
                }));
              }}
            />
          </label>
          <button disabled={busy || failureState?.uncertain}>
            Check real availability
          </button>
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
              disabled={
                busy ||
                (failureState?.uncertain &&
                  reservationRef.current?.slot !==
                    slot.team_key + slot.starts_at)
              }
              onClick={() =>
                void act("reserve_appointment", () => reserve(slot))
              }
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
            {confirmationUnresolved
              ? "Confirmation result unresolved"
              : holdExpired
                ? "Hold expired"
                : ({
                    HELD: "On hold — awaiting your confirmation",
                    CONFIRMED: "Confirmed",
                    CANCELLED: "Cancelled",
                    EXPIRED: "Hold expired",
                  }[appointment.status] ?? "Needs attention")}
          </p>
          {appointment.status === "HELD" && (
            <>
              <p>
                This temporary hold expires at{" "}
                {time(appointment.hold_expires_at)}. Confirm only if you agree
                to this appointment.
              </p>
              <button
                disabled={
                  busy ||
                  (failureState?.uncertain && !confirmationUnresolved) ||
                  (holdExpired && !confirmationUnresolved)
                }
                onClick={() =>
                  void act("confirm_appointment", async () => {
                    if (
                      !confirmationUnresolved &&
                      Date.parse(appointment.hold_expires_at) <= Date.now()
                    )
                      throw new Error(
                        "The temporary hold expired. Release it and choose another time.",
                      );
                    const result = await api<Appointment>(
                      "appointments/" + appointment.id + "/confirm",
                      { explicit_confirmation: true },
                    );
                    if (result.status !== "CONFIRMED")
                      throw new Error(
                        "The appointment has not been confirmed.",
                      );
                    setAppointment(result);
                    if (timezone)
                      onAppointment?.({
                        appointment: result,
                        timezone,
                        readback: "",
                      });
                  })
                }
              >
                {confirmationUnresolved
                  ? "Check previous confirmation"
                  : "I agree — confirm appointment"}
              </button>
              <button
                disabled={busy || confirmationUnresolved}
                onClick={() =>
                  void act("release_appointment_hold", async () => {
                    await api(
                      "appointments/" + appointment.id + "/release",
                      {},
                    );
                    setAppointment(undefined);
                    setAvailability(undefined);
                    reservationRef.current = undefined;
                    onAppointment?.(undefined);
                    onProgress?.((current) => ({
                      ...current,
                      availability: undefined,
                    }));
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
