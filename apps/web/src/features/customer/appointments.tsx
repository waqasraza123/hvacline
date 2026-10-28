"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ProductIcon } from "@/components/product-icons";
import { OperationsApiError, requestApi } from "../operations/api";
import { AppointmentCard } from "./appointment-card";
import { BookingLimitsPanel } from "./booking-limits";
import {
  appointmentState,
  filterAppointments,
  isHistory,
  isUpcoming,
  parseAppointments,
} from "./appointments-model";
import type { AppointmentFilter, MyAppointments } from "./appointments-model";
import styles from "./appointments.module.css";

export function CustomerAppointments({
  revision,
  onBook,
  onViewBooking,
}: {
  revision: number;
  onBook: () => void;
  onViewBooking: (appointmentId: string) => void;
}) {
  const [data, setData] = useState<MyAppointments>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expiredSession, setExpiredSession] = useState(false);
  const [filter, setFilter] = useState<AppointmentFilter>("upcoming");
  const [now, setNow] = useState(() => Date.now());
  const mounted = useRef(false);
  const requestVersion = useRef(0);

  const load = useCallback(async () => {
    const version = ++requestVersion.current;
    setLoading(true);
    setError("");
    setExpiredSession(false);
    setData(undefined);
    try {
      const result = parseAppointments(
        await requestApi<unknown>("", "", "appointments"),
      );
      if (mounted.current && version === requestVersion.current) {
        setData(result);
        setNow(Date.now());
      }
    } catch (failure) {
      if (mounted.current && version === requestVersion.current) {
        const expired =
          failure instanceof OperationsApiError && failure.status === 401;
        setExpiredSession(expired);
        setError(
          expired
            ? "Your session has ended. Sign in again to see your appointments."
            : "We couldn’t load your appointments. Please try again.",
        );
      }
    } finally {
      if (mounted.current && version === requestVersion.current)
        setLoading(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    const focus = () => {
      void load();
    };
    void load();
    window.addEventListener("focus", focus);
    return () => {
      mounted.current = false;
      ++requestVersion.current;
      window.removeEventListener("focus", focus);
    };
  }, [load]);

  useEffect(() => {
    const times = (data?.appointments ?? [])
      .flatMap((appointment) => [
        appointment.starts_at,
        appointment.ends_at,
        ...(appointment.status === "HELD" ? [appointment.hold_expires_at] : []),
      ])
      .map(Date.parse)
      .filter((time) => time > now);
    if (!times.length) return;
    const timer = window.setTimeout(
      () => setNow(Date.now()),
      Math.min(2147483647, Math.max(25, Math.min(...times) - now + 25)),
    );
    return () => window.clearTimeout(timer);
  }, [data, now]);

  const appointments = data?.appointments ?? [];
  const confirmed = appointments.filter((appointment) =>
    ["upcoming", "in_progress"].includes(appointmentState(appointment, now)),
  );
  const held = appointments.filter(
    (appointment) => appointmentState(appointment, now) === "held",
  );
  const history = appointments.filter((appointment) =>
    isHistory(appointment, now),
  );
  const next = filterAppointments(confirmed, "upcoming", now)[0];
  const visible = filterAppointments(appointments, filter, now);
  const counts: Record<AppointmentFilter, number> = {
    upcoming: appointments.filter((appointment) => isUpcoming(appointment, now))
      .length,
    history: history.length,
    all: appointments.length,
  };

  return (
    <section
      className={styles.screen}
      aria-labelledby="appointments-heading"
      aria-busy={loading}
    >
      <div className={styles.heading}>
        <div>
          <span className={styles.eyebrow}>A LITTLE MORE ORGANIZED</span>
          <h2 id="appointments-heading">A clearer view of what’s next.</h2>
          <p>
            See what’s coming up, look back at past bookings, and manage the
            details.
          </p>
        </div>
        <button
          type="button"
          className={styles.secondary}
          disabled={loading}
          onClick={() => void load()}
        >
          <ProductIcon name="clock" />
          {loading ? "Refreshing…" : "Refresh bookings"}
        </button>
      </div>
      {loading ? (
        <div className={styles.empty} role="status">
          <span className="customer-loading" />
          <h3>Getting your appointments…</h3>
          <p>We’re bringing your latest booking details together.</p>
        </div>
      ) : error ? (
        <div className={styles.empty}>
          <span className={styles.icon}>
            <ProductIcon name="calendar" />
          </span>
          <h3>Let’s try that again.</h3>
          <p className={styles.error} role="alert">
            {error}
          </p>
          {expiredSession ? (
            <Link className="product-button" href="/login">
              Sign in again
            </Link>
          ) : (
            <button
              type="button"
              className="product-button"
              onClick={() => void load()}
            >
              Try again
            </button>
          )}
        </div>
      ) : (
        data && (
          <>
            <div className={styles.columns}>
              <div className={styles.mainColumn}>
                {next ? (
                  <AppointmentCard
                    appointment={next}
                    timezone={data.timezone}
                    now={now}
                    featured
                    onView={onViewBooking}
                  />
                ) : (
                  <div className={styles.welcome}>
                    <span className={styles.icon}>
                      <ProductIcon name="calendar" />
                    </span>
                    <span className={styles.eyebrow}>
                      MAKE ROOM FOR COMFORT
                    </span>
                    <h3>
                      {held.length
                        ? "One more step to a booked visit."
                        : "Your next visit starts here."}
                    </h3>
                    <p>
                      {held.length
                        ? "You have a temporary hold below. A hold becomes a booking only after explicit confirmation in your booking conversation."
                        : "When you confirm an appointment with Line, your next visit will appear right here."}
                    </p>
                    {!held.length && (
                      <button
                        type="button"
                        className={`product-button ${styles.primary}`}
                        onClick={onBook}
                      >
                        Book with Line <ProductIcon name="arrow" />
                      </button>
                    )}
                  </div>
                )}
                <div className={styles.historyHeader}>
                  <div>
                    <h3>Your bookings</h3>
                    <p>
                      <ProductIcon name="clock" />
                      All times in {data.timezone}
                    </p>
                  </div>
                  <span className={styles.countLabel}>
                    {appointments.length} shown
                  </span>
                </div>
                <nav
                  className={styles.filters}
                  aria-label="Filter appointments"
                >
                  {(["upcoming", "history", "all"] as const).map((item) => (
                    <button
                      type="button"
                      key={item}
                      aria-pressed={filter === item}
                      onClick={() => setFilter(item)}
                    >
                      {item === "upcoming"
                        ? "Upcoming"
                        : item === "history"
                          ? "History"
                          : "All bookings"}
                      <span>{counts[item]}</span>
                    </button>
                  ))}
                </nav>
                <div className={styles.results}>
                  <p className={styles.resultCount} role="status">
                    {visible.length}{" "}
                    {visible.length === 1 ? "appointment" : "appointments"} in
                    this view
                  </p>
                  {visible.length ? (
                    <div className={styles.list}>
                      {visible.map((appointment) => (
                        <AppointmentCard
                          key={appointment.id}
                          appointment={appointment}
                          timezone={data.timezone}
                          now={now}
                          onView={onViewBooking}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className={styles.empty}>
                      <span className={styles.icon}>
                        <ProductIcon name="calendar" />
                      </span>
                      <h3>
                        {filter === "history"
                          ? "A clean slate."
                          : "Nothing coming up just yet."}
                      </h3>
                      <p>
                        {filter === "history"
                          ? "Past, cancelled, and expired bookings will appear here."
                          : "Confirmed visits and active temporary holds appear here. You can also check your other bookings."}
                      </p>
                      {filter !== "all" && appointments.length > 0 ? (
                        <button
                          type="button"
                          className={styles.secondary}
                          onClick={() => setFilter("all")}
                        >
                          See all bookings
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="product-button"
                          onClick={onBook}
                        >
                          Book with Line <ProductIcon name="arrow" />
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
              <aside
                className={styles.sidebar}
                aria-label="Booking summary and help"
              >
                <section
                  className={styles.summary}
                  aria-labelledby="appointment-overview-heading"
                >
                  <span className={styles.icon}>
                    <ProductIcon name="calendar" />
                  </span>
                  <h3 id="appointment-overview-heading">At a glance</h3>
                  <p>From the bookings shown here.</p>
                  <dl>
                    <div>
                      <dt>
                        <span className={styles.dot} />
                        Confirmed upcoming
                      </dt>
                      <dd>{confirmed.length}</dd>
                    </div>
                    <div>
                      <dt>
                        <span className={styles.dot} data-hold />
                        Awaiting confirmation
                      </dt>
                      <dd>{held.length}</dd>
                    </div>
                    <div>
                      <dt>
                        <span className={styles.dot} data-history />
                        In your history
                      </dt>
                      <dd>{history.length}</dd>
                    </div>
                  </dl>
                </section>
                <div className={styles.limits}>
                  <BookingLimitsPanel revision={revision} />
                </div>
                <section
                  className={styles.help}
                  aria-labelledby="appointment-help-heading"
                >
                  <span className={styles.icon}>
                    <ProductIcon name="shield" />
                  </span>
                  <h3 id="appointment-help-heading">
                    Plans change. We get it.
                  </h3>
                  <p>
                    Open a booking to see its details and available date/time
                    changes. Your current visit stays booked until a new time is
                    confirmed.
                  </p>
                  <p>
                    Only confirmed appointments are booked. Temporary holds
                    expire automatically.
                  </p>
                  <button
                    type="button"
                    className={styles.textButton}
                    onClick={onBook}
                  >
                    Back to Book with Line <ProductIcon name="arrow" />
                  </button>
                </section>
              </aside>
            </div>
          </>
        )
      )}
    </section>
  );
}
