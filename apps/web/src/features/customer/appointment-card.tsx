"use client";

import { ProductIcon } from "@/components/product-icons";
import type { Appointment } from "../operations/api";
import {
  appointmentDate,
  appointmentLabel,
  appointmentState,
  appointmentTimeRange,
} from "./appointments-model";
import styles from "./appointments.module.css";

export function AppointmentCard({
  appointment,
  timezone,
  now,
  featured = false,
  onView,
}: {
  appointment: Appointment;
  timezone: string;
  now: number;
  featured?: boolean;
  onView: (id: string) => void;
}) {
  const date = appointmentDate(appointment.starts_at, timezone);
  const state = appointmentState(appointment, now);
  return (
    <article className={featured ? styles.featured : styles.appointment}>
      {featured && (
        <div className={styles.featureHeader}>
          <span className={styles.eyebrow}>NEXT ON YOUR CALENDAR</span>
          <ProductIcon name="calendar" />
        </div>
      )}
      <div className={styles.appointmentBody}>
        <div className={styles.dateTile} aria-hidden="true">
          <span>{date.month}</span>
          <strong>{date.day}</strong>
          <small>{date.weekday.slice(0, 3)}</small>
        </div>
        <div className={styles.appointmentContent}>
          <span className={styles.badge} data-state={state}>
            {appointmentLabel(appointment, now)}
          </span>
          <h3>
            {featured ? "Your next HVAC visit." : "HVAC service appointment"}
          </h3>
          <p className={styles.fullDate}>
            <time dateTime={appointment.starts_at}>{date.full}</time>
          </p>
          <p className={styles.time}>
            <ProductIcon name="clock" />
            {appointmentTimeRange(appointment, timezone)}
          </p>
          {state === "held" && (
            <p className={styles.holdNote}>
              Temporary hold — your booking is not confirmed. Hold expires{" "}
              {new Intl.DateTimeFormat("en-US", {
                timeStyle: "short",
                timeZone: timezone,
              }).format(new Date(appointment.hold_expires_at))}
              .
            </p>
          )}
          {state === "attention" && (
            <p className={styles.holdNote}>
              Open the details to review this booking’s status.
            </p>
          )}
        </div>
      </div>
      <div className={styles.appointmentFooter}>
        <span>
          {featured
            ? "Your confirmed booking, all in one place."
            : state === "held"
              ? "Only confirmed appointments are booked."
              : "View the saved booking details."}
        </span>
        <button
          type="button"
          className={
            featured ? `product-button ${styles.primary}` : styles.detailButton
          }
          onClick={() => onView(appointment.id)}
        >
          View booking <ProductIcon name="arrow" />
        </button>
      </div>
    </article>
  );
}
