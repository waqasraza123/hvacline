"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  normalizeCallCode, parsePhoneAccessList, parsePhoneAccessPreview, requireCallApproval,
  PhoneAccess, PhoneAccessPreview,
} from "./phone-access-model";
import styles from "./phone-access.module.css";

class AccessError extends Error {
  constructor(readonly status: number, message: string) { super(message); }
}

async function accessRequest(path = "", body?: unknown): Promise<unknown> {
  const response = await fetch(`/api/v1/development/phone-access${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store", redirect: "error", signal: AbortSignal.timeout(15000),
  });
  const value = response.status === 204 ? undefined : await response.json();
  if (!response.ok) throw new AccessError(response.status, value?.error?.message ?? "The call approval could not be confirmed.");
  return value;
}

function time(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function PhoneAccessPanel() {
  const [items, setItems] = useState<PhoneAccess[]>();
  const [code, setCode] = useState("");
  const [preview, setPreview] = useState<PhoneAccessPreview>();
  const [confirmed, setConfirmed] = useState(false);
  const [shareMemory, setShareMemory] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [unavailable, setUnavailable] = useState(false);
  const [signIn, setSignIn] = useState(false);
  const [reloadRequired, setReloadRequired] = useState(false);
  const active = useRef(false);
  const inFlight = useRef(false);

  const load = useCallback(async () => {
    const data = parsePhoneAccessList(await accessRequest());
    if (active.current) { setItems(data); setUnavailable(false); setSignIn(false); }
  }, []);

  const failure = useCallback((value: unknown) => {
    if (value instanceof AccessError) {
      setUnavailable(value.status === 404);
      setSignIn(value.status === 401);
    }
    setError(value instanceof Error ? value.message : "Call access is unavailable. Refresh saved approvals before retrying.");
  }, []);

  useEffect(() => {
    active.current = true;
    void load().catch((value: unknown) => { if (active.current) failure(value); });
    return () => { active.current = false; };
  }, [load, failure]);

  async function run(action: () => Promise<void>, mutation = false) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError(""); setNotice("");
    try { await action(); }
    catch (value) {
      if (active.current) { failure(value); if (mutation) setReloadRequired(true); }
    } finally { inFlight.current = false; if (active.current) setBusy(false); }
  }

  async function refresh() {
    await load();
    if (active.current) {
      setPreview(undefined); setCode(""); setConfirmed(false); setShareMemory(false);
      setReloadRequired(false);
    }
  }

  function previewCall(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void run(async () => {
      const normalized = normalizeCallCode(code);
      const result = parsePhoneAccessPreview(await accessRequest("/preview", { code: normalized }));
      if (Date.parse(result.expires_at) <= Date.now()) throw new Error("That call approval expired. Start a new call to try again.");
      if (active.current) { setCode(normalized); setPreview(result); setConfirmed(false); setShareMemory(false); }
    });
  }

  async function approve() {
    if (!preview || !confirmed || reloadRequired) return;
    if (Date.parse(preview.expires_at) <= Date.now()) throw new Error("That call approval expired. Start a new call to try again.");
    const result = await accessRequest("/approve", { access_id: preview.id, code, explicit_confirmation: true, share_memory: shareMemory });
    requireCallApproval(result, preview.id);
    if (active.current) { setCode(""); setPreview(undefined); setConfirmed(false); setShareMemory(false); }
    await load();
    if (active.current) setNotice("This call is approved. The receptionist can now check the information you allowed.");
  }

  return <section className={styles.panel} aria-labelledby="phone-access-heading" aria-busy={busy}>
    <div className={styles.heading}><div>
      <p className="product-eyebrow">YOUR ACCOUNT. THIS CALL.</p>
      <h1 id="phone-access-heading">Telephone access</h1>
      <p>Approve the phone receptionist to read your upcoming appointments during the call you are on.</p>
    </div><button type="button" className={styles.secondary} disabled={busy} onClick={() => void run(refresh)}>Refresh saved approvals</button></div>
    <p className={styles.warning}>Only approve a call you started and are currently on. The receptionist gives you a CALL code to enter here. Never share your password, authenticator code or recovery codes over the phone.</p>
    {error && <p className="customer-error" role="alert">{error}</p>}
    {signIn && <Link className="product-button" href="/login?intent=phone-access">Sign in again</Link>}
    {notice && <p role="status">{notice}</p>}
    {reloadRequired && <p role="status">The result is uncertain. Refresh saved approvals before making another change.</p>}
    {!unavailable && !signIn && <>
      <form className={styles.card} onSubmit={previewCall}>
        <h2>Connect the current call</h2>
        <label htmlFor="call-code">Call code</label>
        <div className={styles.codeRow}><input id="call-code" value={code} autoComplete="off" autoCapitalize="characters" spellCheck={false} maxLength={40} placeholder="CALL-XXXX-XXXX-XXXX" disabled={busy || reloadRequired} onChange={(event) => { setCode(event.target.value); setPreview(undefined); setConfirmed(false); setShareMemory(false); }} />
          <button className="product-button" disabled={busy || reloadRequired || !code.trim()}>Review call</button></div>
        <p>No code is saved in your browser. Approval ends when this call or the approving sign-in session ends.</p>
      </form>
      {preview && <section className={styles.card} aria-labelledby="review-call-heading">
        <h2 id="review-call-heading">Review this call</h2>
        <dl><div><dt>Business</dt><dd>{preview.business_name}</dd></div>
          <div><dt>Business line</dt><dd>{preview.called_last_four ? `Ending ${preview.called_last_four}` : "Unavailable"}</dd></div>
          <div><dt>Caller ID</dt><dd>{preview.caller_last_four ? `Ending ${preview.caller_last_four}` : "Unavailable"} · not proof of identity</dd></div>
          <div><dt>Expires</dt><dd>{time(preview.expires_at)}</dd></div></dl>
        <p>The call can read up to five upcoming confirmed appointments. Booking changes, payments and account changes are not included.</p>
        <label className={styles.check}><input type="checkbox" checked={shareMemory} disabled={busy || reloadRequired || !preview.memory_available} onChange={(event) => setShareMemory(event.target.checked)} />Also allow my saved memory for this call</label>
        {!preview.memory_available && <p>Saved memory is unavailable for this call. You can review optional consent in your account’s Memory settings.</p>}
        <label className={styles.check}><input type="checkbox" checked={confirmed} disabled={busy || reloadRequired} onChange={(event) => setConfirmed(event.target.checked)} />I am on this call and approve access to my account.</label>
        <div className={styles.actions}><button className="product-button" disabled={busy || reloadRequired || !confirmed} onClick={() => void run(approve, true)}>Approve this call</button>
          <button className={styles.secondary} disabled={busy} onClick={() => { setPreview(undefined); setCode(""); setConfirmed(false); setShareMemory(false); }}>Cancel</button></div>
      </section>}
    </>}
    <section className={styles.card} aria-labelledby="saved-call-heading">
      <h2 id="saved-call-heading">Recent approvals</h2><p>Status at last refresh. An expired call cannot be reconnected using an old approval.</p>
      {items ? items.length ? <ul className={styles.list}>{items.map((item) => <li key={item.id}>
        <div><strong>{item.business_name}</strong><p>{time(item.created_at)} · {item.status === "ACTIVE" && Date.parse(item.expires_at) <= Date.now() ? "EXPIRED" : item.status}</p><p>Expires {time(item.expires_at)} · Appointments{item.share_memory ? " and saved memory" : " only"}</p></div>
        {item.status === "ACTIVE" && <button className={styles.secondary} disabled={busy || reloadRequired} onClick={() => void run(async () => { await accessRequest(`/${item.id}/revoke`, {}); await load(); if (active.current) setNotice("Call access revoked."); }, true)}>Revoke access</button>}
      </li>)}</ul> : <p>No call approvals yet.</p> : !error && <p role="status">Loading saved approvals…</p>}
    </section>
  </section>;
}
