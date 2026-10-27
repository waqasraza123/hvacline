"use client";

import { useEffect, useState } from "react";
import { requestApi } from "../operations/api";
import styles from "./booking-limits.module.css";

export type BookingLimits = {
  max_active_appointments: number;
  max_booking_changes: number;
  active_appointments: number;
  appointments_remaining: number;
  refresh_at: string | null;
};

export function BookingLimitSummary({ limits }: { limits: BookingLimits }) {
  return (
    <section className={styles.summary} aria-label="Your booking limits">
      <strong>Your booking limits</strong>
      <p>
        Up to{" "}
        <b>
          {limits.max_active_appointments} active{" "}
          {limits.max_active_appointments === 1
            ? "appointment"
            : "appointments"}
        </b>{" "}
        at a time ·{" "}
        <b>
          {limits.max_booking_changes} date/time{" "}
          {limits.max_booking_changes === 1 ? "change" : "changes"}
        </b>{" "}
        per booking.
      </p>
      <p>
        {limits.active_appointments} of {limits.max_active_appointments}{" "}
        appointment places used · {limits.appointments_remaining} available.
        Unexpired holds use a place.
      </p>
      {limits.appointments_remaining === 0 && (
        <p role="status">
          Your appointment limit is reached. Open your existing booking to view
          details or make an allowed change.
        </p>
      )}
    </section>
  );
}

export function BookingLimitsPanel({ revision }: { revision: number }) {
  const [limits, setLimits] = useState<BookingLimits>();
  const [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    let requestVersion = 0;
    async function refresh() {
      if (!active) return;
      const version = ++requestVersion;
      if (timer !== undefined) window.clearTimeout(timer);
      try {
        const result = await requestApi<BookingLimits>(
          "",
          "",
          "booking-limits",
        );
        if (!active || version !== requestVersion) return;
        if (
          ![
            result.max_active_appointments,
            result.max_booking_changes,
            result.active_appointments,
            result.appointments_remaining,
          ].every((value) => Number.isInteger(value) && value >= 0)
        )
          throw new Error("Invalid booking limits");
        setLimits(result);
        setError(false);
        if (
          result.refresh_at &&
          Number.isFinite(Date.parse(result.refresh_at))
        ) {
          timer = window.setTimeout(
            () => void refresh(),
            Math.min(
              2147483647,
              Math.max(1000, Date.parse(result.refresh_at) - Date.now() + 1000),
            ),
          );
        }
      } catch {
        if (active && version === requestVersion) setError(true);
      }
    }
    const focus = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    void refresh();
    window.addEventListener("focus", focus);
    document.addEventListener("visibilitychange", focus);
    return () => {
      active = false;
      if (timer !== undefined) window.clearTimeout(timer);
      window.removeEventListener("focus", focus);
      document.removeEventListener("visibilitychange", focus);
    };
  }, [revision]);
  return (
    <>
      {limits && <BookingLimitSummary limits={limits} />}
      {error ? (
        <p role="status">
          Your booking limits could not be refreshed. Reload to check your
          remaining allowance.
        </p>
      ) : !limits ? (
        <p role="status">Loading your booking limits…</p>
      ) : null}
    </>
  );
}
