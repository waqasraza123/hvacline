"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Brand } from "@/components/brand";
import { ProductIcon, VoiceSymbol } from "@/components/product-icons";
import { BrowserVoicePanel } from "@/features/conversation/browser-voice-panel";
import { OperationsApiError, requestApi } from "@/features/operations/api";
import type { Appointment } from "@/features/operations/api";
import type { Customer } from "./server";

type MyAppointments = { appointments: Appointment[]; timezone: string | null };

export function CustomerBooking({
  user,
  voiceEnabled,
}: {
  user: Customer;
  voiceEnabled: boolean;
}) {
  const router = useRouter();
  const [tab, setTab] = useState<"book" | "appointments">("book");
  const [voiceActive, setVoiceActive] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState("");
  async function logout() {
    setSigningOut(true);
    setError("");
    try {
      const response = await fetch("/api/account/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
        signal: AbortSignal.timeout(20000),
      });
      if (!response.ok)
        throw new Error("We couldn’t sign you out. Please try again.");
      router.replace("/login");
      router.refresh();
    } catch {
      setError("We couldn’t sign you out. Please try again.");
      setSigningOut(false);
    }
  }
  return (
    <div className="customer-shell">
      <header className="product-header product-container">
        <Brand />
        <div className="customer-account">
          <span className="account-avatar" aria-hidden="true">
            {user.full_name.slice(0, 1).toUpperCase()}
          </span>
          <span>{user.full_name}</span>
          <button
            type="button"
            disabled={voiceActive || signingOut}
            onClick={() => void logout()}
            aria-label="Sign out"
          >
            <ProductIcon name="logout" />
          </button>
        </div>
      </header>
      <main className="customer-main product-container">
        <div className="customer-page-heading">
          <div>
            <p className="product-eyebrow">YOUR HOME. YOUR SCHEDULE.</p>
            <h1>
              A little closer
              <br />
              to comfortable.
            </h1>
            <p>Book your next service, or pick up where you left off.</p>
          </div>
          <span className="customer-voice-label">
            <VoiceSymbol /> Powered by Line <span>VOICE AI</span>
          </span>
        </div>
        <nav className="customer-tabs" aria-label="Your booking workspace">
          <button
            type="button"
            aria-current={tab === "book" ? "page" : undefined}
            onClick={() => setTab("book")}
          >
            <ProductIcon name="mic" /> Book with Line
          </button>
          <button
            type="button"
            aria-current={tab === "appointments" ? "page" : undefined}
            disabled={voiceActive}
            onClick={() => setTab("appointments")}
          >
            <ProductIcon name="calendar" /> My appointments
          </button>
          <span>
            {voiceActive
              ? "Finish your conversation before leaving this page."
              : "Your next step, made simple."}
          </span>
        </nav>
        {error && (
          <p role="alert" className="customer-error">
            {error}
          </p>
        )}
        {tab === "book" ? (
          voiceEnabled ? (
            <BrowserVoicePanel
              apiBaseUrl=""
              presentation="customer"
              onActivityChange={setVoiceActive}
            />
          ) : (
            <section className="customer-empty">
              <VoiceSymbol />
              <h2>Line is taking a short break.</h2>
              <p>
                Voice booking is not available right now. Please check back
                shortly.
              </p>
              <Link className="product-text-link" href="/">
                Return home <ProductIcon name="arrow" />
              </Link>
            </section>
          )
        ) : (
          <AppointmentList onBook={() => setTab("book")} />
        )}
      </main>
      <footer className="customer-footer product-container">
        <span>HVACLine. A better first conversation.</span>
        <Link href="/">Back to home ↗</Link>
      </footer>
    </div>
  );
}

function AppointmentList({ onBook }: { onBook: () => void }) {
  const [data, setData] = useState<MyAppointments>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function load() {
    setLoading(true);
    setError("");
    try {
      const result = await requestApi<MyAppointments>("", "", "appointments");
      if (!Array.isArray(result.appointments))
        throw new Error("Your appointments could not be loaded.");
      setData(result);
    } catch (failure) {
      setError(
        failure instanceof OperationsApiError && failure.status === 401
          ? "Your session has ended. Sign in again to see your appointments."
          : "We couldn’t load your appointments. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    let active = true;
    void requestApi<MyAppointments>("", "", "appointments")
      .then((value) => {
        if (!active) return;
        if (!Array.isArray(value.appointments))
          throw new Error("Invalid appointments");
        setData(value);
      })
      .catch((failure) => {
        if (active)
          setError(
            failure instanceof OperationsApiError && failure.status === 401
              ? "Your session has ended. Sign in again to see your appointments."
              : "We couldn’t load your appointments. Please try again.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  if (loading)
    return (
      <div className="customer-empty" role="status">
        <span className="customer-loading" />
        <p>Getting your appointments…</p>
      </div>
    );
  if (error)
    return (
      <div className="customer-empty">
        <p className="customer-error" role="alert">
          {error}
        </p>
        <button className="product-button" onClick={() => void load()}>
          Try again
        </button>
        <Link href="/login" className="product-text-link">
          Sign in again
        </Link>
      </div>
    );
  if (!data?.appointments.length)
    return (
      <section className="customer-empty">
        <span className="empty-calendar">
          <ProductIcon name="calendar" />
        </span>
        <h2>Your calendar is clear.</h2>
        <p>When you book a service, you’ll find the details right here.</p>
        <button className="product-button" onClick={onBook}>
          Book with Line <ProductIcon name="arrow" />
        </button>
      </section>
    );
  return (
    <section
      className="customer-appointment-list"
      aria-label="Your appointments"
    >
      <div className="customer-list-heading">
        <h2>Your appointments</h2>
        <button className="product-text-link" onClick={() => void load()}>
          Refresh ↻
        </button>
      </div>
      {data.appointments.map((appointment) => {
        const expired =
          appointment.status === "HELD" &&
          new Date(appointment.hold_expires_at).getTime() <= Date.now();
        const label = expired
          ? "Hold expired"
          : ({
              CONFIRMED: "Confirmed",
              HELD: "Waiting for confirmation",
              CANCELLED: "Cancelled",
              EXPIRED: "Expired",
            }[appointment.status] ?? "Needs attention");
        return (
          <article key={appointment.id} className="customer-appointment">
            <span className="appointment-icon">
              <ProductIcon name="calendar" />
            </span>
            <div>
              <h3>
                {new Intl.DateTimeFormat("en-US", {
                  dateStyle: "full",
                  timeZone: data.timezone ?? "UTC",
                }).format(new Date(appointment.starts_at))}
              </h3>
              <p>
                {new Intl.DateTimeFormat("en-US", {
                  timeStyle: "short",
                  timeZone: data.timezone ?? "UTC",
                }).format(new Date(appointment.starts_at))}{" "}
                · {data.timezone ?? "UTC"}
              </p>
              <small>HVAC service appointment</small>
            </div>
            <span
              className={`appointment-status status-${appointment.status.toLowerCase()}`}
            >
              {label}
            </span>
          </article>
        );
      })}
      <p className="customer-list-note">
        Only appointments you have confirmed are booked. Temporary holds expire
        automatically.
      </p>
    </section>
  );
}
