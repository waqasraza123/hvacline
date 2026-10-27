"use client";

import { useEffect, useId, useRef, useState } from "react";
import { ProductIcon } from "@/components/product-icons";
import type { Appointment, Availability, Slot } from "../operations/api";
import {
  BookingChange,
  SERVICE_NAMES,
  bookingDay,
  bookingTime,
  getBookingAvailability,
  getBookingDetails,
} from "./booking-details";
import type { BookingDetails } from "./booking-details";
import styles from "./booking-details.module.css";

export function BookingDetailsModal({
  appointmentId,
  changes,
  editingDisabled,
  onClose,
  onChanged,
}: {
  appointmentId: string;
  changes: Map<string, BookingChange>;
  editingDisabled: boolean;
  onClose: () => void;
  onChanged: (appointment: Appointment) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const title = useId();
  const [details, setDetails] = useState<BookingDetails>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(
    () => !!changes.get(appointmentId)?.pending,
  );
  const [day, setDay] = useState("");
  const [availability, setAvailability] = useState<Availability>();
  const [selection, setSelection] = useState<Slot>();
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const change = changes.get(appointmentId) ?? new BookingChange(appointmentId);

  useEffect(() => {
    const element = dialog.current;
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    element?.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      element?.close();
      document.body.style.overflow = previousOverflow;
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected)
        previousFocus.focus();
    };
  }, []);

  useEffect(() => {
    let active = true;
    void getBookingDetails(appointmentId)
      .then((result) => {
        if (!active) return;
        setDetails(result);
        setDay(bookingDay(result.appointment.starts_at, result.timezone));
      })
      .catch(() => {
        if (active)
          setError(
            "We couldn’t load your booking. Close this window and try again.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [appointmentId]);

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
          : "Your booking could not be changed.",
      );
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  function close() {
    if (!busyRef.current) onClose();
  }

  const pending = change.pending;
  const timezone = details?.timezone ?? "UTC";
  const address = details?.customer.address;

  return (
    <dialog
      ref={dialog}
      className={styles.dialog}
      aria-labelledby={title}
      aria-busy={busy}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClick={(event) => {
        if (event.target !== event.currentTarget) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        if (
          event.clientX < bounds.left ||
          event.clientX > bounds.right ||
          event.clientY < bounds.top ||
          event.clientY > bounds.bottom
        )
          close();
      }}
    >
      <div className={styles.header}>
        <div>
          <p>Your appointment</p>
          <h2 id={title}>Booking details</h2>
        </div>
        <button
          type="button"
          className={styles.close}
          onClick={close}
          disabled={busy}
          aria-label="Close booking details"
        >
          <ProductIcon name="close" />
        </button>
      </div>
      {loading && <p role="status">Loading your booking…</p>}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {details && (
        <>
          <div
            className={styles.receipt}
            data-confirmed={details.appointment.status === "CONFIRMED"}
          >
            <span>
              {details.appointment.status === "CONFIRMED"
                ? "Confirmed"
                : details.appointment.status.toLowerCase()}
            </span>
            <h3>{bookingTime(details.appointment.starts_at, timezone)}</h3>
            <p>
              Until{" "}
              {new Intl.DateTimeFormat("en-US", {
                timeStyle: "short",
                timeZone: timezone,
              }).format(new Date(details.appointment.ends_at))}{" "}
              · {timezone}
            </p>
            <p>{SERVICE_NAMES[details.service.kind] ?? "HVAC service"}</p>
          </div>
          <dl className={styles.details}>
            <div>
              <dt>Name</dt>
              <dd>{details.customer.full_name}</dd>
            </div>
            <div>
              <dt>Callback number</dt>
              <dd>{details.customer.phone ?? "Not provided"}</dd>
            </div>
            <div>
              <dt>Booking email</dt>
              <dd>{details.customer.email ?? "Not provided"}</dd>
            </div>
            <div>
              <dt>Service address</dt>
              <dd>
                {address
                  ? [
                      address.line1,
                      address.line2,
                      address.city,
                      address.state_code,
                      address.postal_code,
                      address.country_code,
                    ]
                      .filter(Boolean)
                      .join(", ")
                  : "Not provided"}
              </dd>
            </div>
            <div>
              <dt>Service request</dt>
              <dd>{details.service.equipment_issue}</dd>
            </div>
            <div>
              <dt>Booking reference</dt>
              <dd>{details.appointment.id}</dd>
            </div>
          </dl>
          {details.service.hazardous_condition && (
            <p className={styles.error}>
              This request needs human attention. For immediate danger, contact
              emergency services.
            </p>
          )}
          {editingDisabled ? (
            <p>Finish your conversation before editing this appointment.</p>
          ) : !editing ? (
            <>
              {details.can_reschedule ? (
                <button
                  type="button"
                  className="product-button"
                  onClick={() => setEditing(true)}
                >
                  Edit appointment date and time
                </button>
              ) : (
                <p>{details.change_message}</p>
              )}
            </>
          ) : (
            <section className={styles.editor} aria-label="Edit appointment">
              <h3>Choose a new date and time</h3>
              <p>
                {pending
                  ? "The previous change’s result is unresolved. Check the same change before selecting another time."
                  : "Your current appointment stays booked until the new time is confirmed."}
              </p>
              {pending ? (
                <>
                  <p>{bookingTime(pending.starts_at, timezone)}</p>
                  <button
                    type="button"
                    className="product-button"
                    disabled={busy}
                    onClick={() =>
                      void act(async () => {
                        const next = await change.submit(
                          pending.service_request_id,
                          pending,
                        );
                        onChanged(next);
                      })
                    }
                  >
                    {busy ? "Checking change…" : "Check previous change"}
                  </button>
                </>
              ) : (
                <>
                  <form
                    onSubmit={(event) => {
                      event.preventDefault();
                      void act(async () => {
                        setSelection(undefined);
                        setAgreed(false);
                        setAvailability(undefined);
                        setAvailability(
                          await getBookingAvailability(appointmentId, day),
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
                          setSelection(undefined);
                          setAgreed(false);
                        }}
                      />
                    </label>
                    <button
                      type="submit"
                      className="product-button"
                      disabled={busy}
                    >
                      {busy ? "Checking…" : "Check available times"}
                    </button>
                  </form>
                  {availability && (
                    <>
                      <p>{availability.timezone}</p>
                      {availability.slots.length ? (
                        <label>
                          Available appointment
                          <select
                            required
                            value={
                              selection
                                ? `${selection.team_key}|${selection.starts_at}`
                                : ""
                            }
                            disabled={busy}
                            onChange={(event) => {
                              setSelection(
                                availability.slots.find(
                                  (slot) =>
                                    `${slot.team_key}|${slot.starts_at}` ===
                                    event.target.value,
                                ),
                              );
                              setAgreed(false);
                            }}
                          >
                            <option value="">Choose a time</option>
                            {availability.slots
                              .filter(
                                (slot) =>
                                  !(
                                    slot.team_key ===
                                      details.appointment.team_key &&
                                    slot.starts_at ===
                                      details.appointment.starts_at
                                  ),
                              )
                              .map((slot) => (
                                <option
                                  key={`${slot.team_key}|${slot.starts_at}`}
                                  value={`${slot.team_key}|${slot.starts_at}`}
                                >
                                  {bookingTime(
                                    slot.starts_at,
                                    availability.timezone ?? timezone,
                                  )}
                                </option>
                              ))}
                          </select>
                        </label>
                      ) : (
                        <p role="status">
                          {availability.message ??
                            "No available times. Try another date."}
                        </p>
                      )}
                    </>
                  )}
                  {selection && (
                    <div className={styles.confirm}>
                      <p>
                        Change your appointment to{" "}
                        <strong>
                          {bookingTime(
                            selection.starts_at,
                            availability?.timezone ?? timezone,
                          )}
                        </strong>{" "}
                        ({availability?.timezone ?? timezone})?
                      </p>
                      <label className={styles.checkbox}>
                        <input
                          type="checkbox"
                          checked={agreed}
                          disabled={busy}
                          onChange={(event) => setAgreed(event.target.checked)}
                        />
                        I confirm this new appointment time.
                      </label>
                      <button
                        type="button"
                        className="product-button"
                        disabled={busy || !agreed}
                        onClick={() =>
                          void act(async () => {
                            changes.set(appointmentId, change);
                            const next = await change.submit(
                              details.appointment.service_request_id,
                              selection,
                            );
                            onChanged(next);
                          })
                        }
                      >
                        {busy ? "Saving change…" : "Confirm appointment change"}
                      </button>
                    </div>
                  )}
                  <button
                    type="button"
                    className="product-text-link"
                    disabled={busy}
                    onClick={() => {
                      setEditing(false);
                      setSelection(undefined);
                      setAgreed(false);
                      setAvailability(undefined);
                      setError("");
                    }}
                  >
                    Keep current appointment
                  </button>
                </>
              )}
            </section>
          )}
        </>
      )}
    </dialog>
  );
}
