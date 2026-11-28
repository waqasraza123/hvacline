"use client";

import { providerFetch } from "@/lib/provider-fetch";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import type { Appointment, Availability, Slot } from "@/features/operations/api";
import styles from "./recovery.module.css";

type Session = {
  status: string; row_version: number; expires_at: string; timezone: string; confirmed: boolean;
  service: { kind: string; equipment_issue: string };
  customer: { full_name: string; address: { line1: string; city: string; state_code: string; postal_code: string } };
  appointment: Appointment | null;
  approved_confirmation: { nonce: string; row_version: number } | null;
};
type Readback = { readback: string; nonce: string; row_version: number };

async function api<T>(path = "", body?: unknown): Promise<T> {
  const response = await providerFetch(`/api/recovery${path ? `/${path}` : ""}`, {
    method: body === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store", signal: AbortSignal.timeout(25000),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result?.error?.message ?? "The booking request could not finish. Refresh its saved status before retrying.");
  return result as T;
}

export function CustomerRecoveryBooking() {
  const [session, setSession] = useState<Session | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [day, setDay] = useState("");
  const [availability, setAvailability] = useState<Availability | null>(null);
  const [readback, setReadback] = useState<Readback | null>(null);
  const [approved, setApproved] = useState(false);
  const initialRequest = useRef<Promise<Session> | null>(null);

  useEffect(() => {
    let active = true;
    if (!initialRequest.current) {
      const parameters = new URLSearchParams(window.location.hash.slice(1));
      const token = parameters.get("token");
      // Fragments never enter server logs; remove the capability before further navigation.
      window.history.replaceState(null, "", window.location.pathname);
      initialRequest.current = token ? api<Session>("exchange", { token }) : api<Session>();
    }
    const load = initialRequest.current;
    load.then((value) => { if (active) setSession(value); })
      .catch((error: unknown) => { if (active) setError(error instanceof Error ? error.message : "This booking link could not be opened."); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, []);

  async function act(task: () => Promise<void>) {
    setBusy(true); setError("");
    try { await task(); } catch (error) { setError(error instanceof Error ? error.message : "The booking request could not finish."); } finally { setBusy(false); }
  }
  const time = (value: string) => new Intl.DateTimeFormat("en-US", { dateStyle: "full", timeStyle: "short", timeZone: session?.timezone ?? "America/New_York" }).format(new Date(value));
  async function select(slot: Slot) {
    if (!session) return;
    await api("reserve", { expected_row_version: session.row_version, team_key: slot.team_key, starts_at: slot.starts_at });
    setSession(await api<Session>());
    setAvailability(null); setReadback(null); setApproved(false);
  }
  return <div className={`${styles.root} customer-shell`} style={{ minHeight: "100vh", padding: "1.5rem" }}>
    <header className={styles.toolbar}><Brand /><ThemeToggle /></header>
    <main className={styles.frame} style={{ maxWidth: 760, margin: "2rem auto" }}>
      <p className={styles.eyebrow}>Continue your requested HVAC booking</p>
      <h1>{session?.confirmed ? "Your appointment is confirmed" : "Choose the next step for your service visit"}</h1>
      <p className={styles.muted}>This secure session is limited to the service request you asked us to continue. Availability comes from the business’s scheduling system.</p>
      {busy && <p role="status">Working on your booking…</p>}
      {error && <p className={styles.notice} role="alert">{error} If a confirmation timed out, use Check saved booking status before selecting another appointment.</p>}
      <button type="button" disabled={busy} onClick={() => void act(async () => { setSession(await api<Session>()); setReadback(null); setApproved(false); })}>Check saved booking status</button>
      {session && <>
        <p style={{ marginTop: "1.5rem" }}><strong>{session.customer.full_name}</strong><br />{session.service.kind.replaceAll("_", " ")} · {session.service.equipment_issue}</p>
        <p className={styles.muted}>{session.customer.address.line1}, {session.customer.address.city}, {session.customer.address.state_code} {session.customer.address.postal_code}<br />Times in {session.timezone}. Session expires {time(session.expires_at)}.</p>
        {session.confirmed && session.appointment ? <div className={styles.notice}><strong>Confirmed appointment</strong><p>{time(session.appointment.starts_at)}<br />Team: {session.appointment.team_key}<br />Booking reference: {session.appointment.id}</p><p>Existing booking confirmations and calendar updates follow the business’s configured notification settings.</p></div> : <>
          {session.appointment ? <section className={styles.panel}>
            <h2>Review your reservation</h2><p>{time(session.appointment.starts_at)} · {session.appointment.status.toLowerCase()}<br />Hold expires {time(session.appointment.hold_expires_at)}.</p>
            {session.approved_confirmation ? <div className={styles.notice}><p>Your approval is saved. Keep this selection while its confirmation is checked.</p><button type="button" disabled={busy} onClick={() => void act(async () => { await api("confirm", { expected_row_version: session.approved_confirmation!.row_version, nonce: session.approved_confirmation!.nonce, explicit_confirmation: true }); setSession(await api<Session>()); })}>Check / finish the approved booking</button></div> : <div className={styles.actions}><button type="button" disabled={busy} onClick={() => void act(async () => { setReadback(await api<Readback>("readback", {})); setApproved(false); })}>Review exact booking details</button><button type="button" disabled={busy} onClick={() => void act(async () => { setSession(await api<Session>("release", {})); setReadback(null); setApproved(false); })}>Release unconfirmed reservation</button></div>}
            {readback && <form className={styles.form} onSubmit={(event) => { event.preventDefault(); void act(async () => {
              await api<Appointment>("confirm", { expected_row_version: readback.row_version, nonce: readback.nonce, explicit_confirmation: approved });
              setSession(await api<Session>()); setReadback(null); setApproved(false);
            }); }}><p>{readback.readback}</p><label className={styles.check}><input type="checkbox" checked={approved} required onChange={(event) => setApproved(event.target.checked)} />I confirm this exact appointment and service address.</label><button className={styles.primary} disabled={busy || !approved}>Confirm appointment</button></form>}
          </section> : <section className={styles.panel}>
            <form className={styles.form} onSubmit={(event) => { event.preventDefault(); void act(async () => { setAvailability(await api<Availability>("availability", { day })); setSession(await api<Session>()); }); }}>
              <label>Preferred service date<input type="date" required value={day} onChange={(event) => setDay(event.target.value)} /></label><button type="submit" disabled={busy}>Find available appointments</button>
            </form>
            {availability && <div className={styles.slots}>{availability.slots.length ? availability.slots.map((slot) => <button type="button" key={`${slot.team_key}:${slot.starts_at}`} disabled={busy} onClick={() => void act(() => select(slot))}>{time(slot.starts_at)} · {slot.team_key}</button>) : <p>{availability.message ?? "No available appointments on this date. Try another date or contact the business."}</p>}</div>}
          </section>}
        </>}
      </>}
      <p className={styles.muted} style={{ marginTop: "1.5rem" }}>If your details are wrong or your link has expired, contact the business for staff assistance. This page cannot change the original service request or access other account records.</p>
      <Link className={styles.link} href="/">Return to HVACLine</Link>
    </main>
  </div>;
}
