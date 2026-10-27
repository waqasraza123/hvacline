"use client";

import { useEffect, useId, useState } from "react";
import { BOOKING_STAGES, bookingPresentation } from "./booking-progress";
import type { BookingProgress } from "./booking-progress";
import type { VoiceAppointment } from "./voice-booking";
import styles from "./booking-progress.module.css";

const SERVICE_LABELS: Record<string, string> = {
  AC_REPAIR: "AC repair",
  HEATING_REPAIR: "Heating repair",
  INSTALLATION: "Installation",
  MAINTENANCE: "Maintenance",
};

export function BookingProgressPanel({
  progress,
  appointment,
  activity,
  conversationBusy,
  conversationEnded,
  onViewAppointments,
  onViewBooking,
}: {
  progress: BookingProgress;
  appointment?: VoiceAppointment;
  activity: string;
  conversationBusy: boolean;
  conversationEnded: boolean;
  onViewAppointments?: () => void;
  onViewBooking?: (appointmentId: string) => void;
}) {
  const [now, setNow] = useState(() => Date.now());
  const failureId = useId();
  useEffect(() => {
    if (appointment?.appointment.status !== "HELD") return;
    const tick = () => setNow(Date.now());
    const refresh = window.setTimeout(tick, 0);
    const interval = window.setInterval(tick, 1000);
    return () => {
      window.clearTimeout(refresh);
      window.clearInterval(interval);
    };
  }, [appointment]);
  const view = bookingPresentation(progress, appointment, now);
  const message =
    conversationEnded &&
    progress.failure?.uncertain &&
    !view.confirmed &&
    !progress.hazardous
      ? "The previous action’s result is unresolved. Check your appointments or ask the business to review it before starting another booking."
      : conversationEnded &&
          !progress.hazardous &&
          !view.confirmed &&
          !progress.pending &&
          !progress.failure
        ? progress.requestSaved
          ? appointment?.appointment.status === "HELD" && view.remaining > 0
            ? "Your time is temporarily held. Review the date and time below and confirm to book."
            : appointment
              ? view.message
              : "Your request is saved. Use the booking controls below to choose an available time."
          : "The conversation has ended. Review your details below before saving; no appointment is booked yet."
        : view.message;
  const date = appointment
    ? new Intl.DateTimeFormat("en-US", {
        dateStyle: "full",
        timeStyle: "short",
        timeZone: appointment.timezone,
      }).format(new Date(appointment.appointment.starts_at))
    : undefined;
  return (
    <section className={styles.panel} aria-label="Booking progress">
      <div className={styles.heading}>
        <h2>Your booking</h2>
        <span className={styles.activity}>{activity}</span>
      </div>
      <ol className={styles.steps} aria-label="Booking stages">
        {BOOKING_STAGES.map((label, index) => (
          <li
            key={label}
            aria-current={index === view.stage ? "step" : undefined}
            aria-describedby={
              index === view.failedStage ? failureId : undefined
            }
            className={index <= view.stage ? styles.reached : undefined}
          >
            <span aria-hidden="true">
              {index < view.stage || view.confirmed ? "✓" : index + 1}
            </span>
            {label}
            {index === view.failedStage && (
              <small className={styles.stageNote}>Needs attention</small>
            )}
          </li>
        ))}
      </ol>
      <p
        className={progress.hazardous ? styles.warning : styles.message}
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {message}
      </p>
      {progress.failure && (
        <p className={styles.warning} role="alert" id={failureId}>
          {progress.failure.message}
        </p>
      )}
      {conversationEnded &&
        progress.failure?.uncertain &&
        !view.confirmed &&
        onViewAppointments && (
          <button
            className={styles.historyButton}
            type="button"
            onClick={onViewAppointments}
          >
            Check my appointments
          </button>
        )}
      {appointment && (
        <div className={view.confirmed ? styles.receipt : styles.selection}>
          <h3>
            {view.confirmed ? "Appointment confirmed" : "Selected appointment"}
          </h3>
          <p>{date}</p>
          <p>{appointment.timezone}</p>
          {progress.serviceKind && (
            <p>{SERVICE_LABELS[progress.serviceKind] ?? "HVAC service"}</p>
          )}
          {appointment.appointment.status === "HELD" && (
            <>
              <p>
                {progress.failure?.uncertain
                  ? "Previous action unresolved · retry the same action"
                  : view.remaining > 0
                    ? "Temporarily held · confirmation required"
                    : "Hold expired · choose another time"}
              </p>
              {view.remaining > 0 && (
                <p aria-live="off">
                  Hold remaining: {Math.floor(view.remaining / 60)}:
                  {String(view.remaining % 60).padStart(2, "0")}
                </p>
              )}
            </>
          )}
          {view.confirmed && progress.hazardous && (
            <p>
              Your existing appointment remains saved. It does not replace
              urgent assistance.
            </p>
          )}
          {view.confirmed && onViewAppointments && (
            <>
              <button
                type="button"
                disabled={conversationBusy}
                onClick={onViewAppointments}
              >
                View my appointments
              </button>
              {conversationBusy && (
                <p>Finish your conversation to view your appointments.</p>
              )}
            </>
          )}
          {view.confirmed && onViewBooking && (
            <button
              type="button"
              onClick={() => onViewBooking(appointment.appointment.id)}
            >
              View booking details
            </button>
          )}
        </div>
      )}
    </section>
  );
}
