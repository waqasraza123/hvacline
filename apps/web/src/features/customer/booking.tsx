"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Brand } from "@/components/brand";
import { ProductIcon, VoiceSymbol } from "@/components/product-icons";
import { BrowserVoicePanel } from "@/features/conversation/browser-voice-panel";
import type { Customer } from "./server";
import { BookingDetailsModal } from "./booking-details-modal";
import { BookingChange } from "./booking-details";
import { BookingLimitsPanel } from "./booking-limits";
import { CustomerMemory } from "./memory";
import { CustomerAppointments } from "./appointments";

export function CustomerBooking({
  user,
  voiceEnabled,
}: {
  user: Customer;
  voiceEnabled: boolean;
}) {
  const router = useRouter();
  const [tab, setTab] = useState<"book" | "appointments" | "memory">("book");
  const [voiceActive, setVoiceActive] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState("");
  const [selectedBooking, setSelectedBooking] = useState<string>();
  const [appointmentsRevision, setAppointmentsRevision] = useState(0);
  const [bookingChanges] = useState(() => new Map<string, BookingChange>());
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
            <p className="product-eyebrow">
              {tab === "memory"
                ? "YOUR DETAILS. YOUR CHOICE."
                : tab === "appointments"
                  ? "YOUR VISITS. YOUR SCHEDULE."
                  : "YOUR HOME. YOUR SCHEDULE."}
            </p>
            <h1>
              {tab === "memory"
                ? "A little less repeating."
                : tab === "appointments"
                  ? "Your visits."
                  : "A little closer"}
              <br />
              {tab === "memory"
                ? "A little more you."
                : tab === "appointments"
                  ? "All in one place."
                  : "to comfortable."}
            </h1>
            <p>
              {tab === "memory"
                ? "Manage what Line remembers for your next conversation."
                : tab === "appointments"
                  ? "Keep track of your upcoming visits and saved booking details."
                  : "Book your next service, or pick up where you left off."}
            </p>
          </div>
          <span className="customer-voice-label">
            <VoiceSymbol /> Powered by Line <span>VOICE & CHAT</span>
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
          <button
            type="button"
            disabled={voiceActive}
            aria-current={tab === "memory" ? "page" : undefined}
            onClick={() => setTab("memory")}
          >
            <ProductIcon name="shield" />
            Memory
          </button>
          <span>
            {voiceActive
              ? "Finish your conversation before leaving this page."
              : "Your next step, made simple."}
          </span>
        </nav>
        {tab === "book" && (
          <BookingLimitsPanel revision={appointmentsRevision} />
        )}
        {error && (
          <p role="alert" className="customer-error">
            {error}
          </p>
        )}
        {tab === "memory" ? (
          <CustomerMemory key={user.id} />
        ) : tab === "book" ? (
          voiceEnabled ? (
            <BrowserVoicePanel
              apiBaseUrl=""
              presentation="customer"
              onActivityChange={setVoiceActive}
              onViewAppointments={() => setTab("appointments")}
              onViewBooking={setSelectedBooking}
              onBookingChanged={() =>
                setAppointmentsRevision((current) => current + 1)
              }
            />
          ) : (
            <section className="customer-empty">
              <VoiceSymbol />
              <h2>Line is taking a short break.</h2>
              <p>
                Chat and voice booking are not available right now. Please check
                back shortly.
              </p>
              <Link className="product-text-link" href="/">
                Return home <ProductIcon name="arrow" />
              </Link>
            </section>
          )
        ) : (
          <CustomerAppointments
            key={appointmentsRevision}
            revision={appointmentsRevision}
            onBook={() => setTab("book")}
            onViewBooking={setSelectedBooking}
          />
        )}
      </main>
      {selectedBooking && (
        <BookingDetailsModal
          key={selectedBooking}
          appointmentId={selectedBooking}
          changes={bookingChanges}
          editingDisabled={voiceActive}
          onClose={() => setSelectedBooking(undefined)}
          onChanged={(appointment) => {
            setAppointmentsRevision((current) => current + 1);
            setTab("appointments");
            setSelectedBooking(appointment.id);
          }}
        />
      )}
      <footer className="customer-footer product-container">
        <span>HVACLine. A better first conversation.</span>
        <Link href="/">Back to home ↗</Link>
      </footer>
    </div>
  );
}
