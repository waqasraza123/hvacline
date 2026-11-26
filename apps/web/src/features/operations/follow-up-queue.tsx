"use client";

import { useRef, useState } from "react";
import type { FollowUp } from "./api";
import { DashboardTable, StatusBadge } from "./dashboard-table";
import { allowedFollowUpActions, filterFollowUps, followUpActions, followUpAge, updateFollowUp } from "./follow-up";
import type { FollowUpAction } from "./follow-up";
import styles from "./follow-up.module.css";

export function FollowUpQueue({ rows, demo, apiBaseUrl, token, loadedAt, busy, onBusyChange, onReload, onUpdated, timestamp, update }: {
  rows: FollowUp[];
  demo: boolean;
  apiBaseUrl: string;
  token: string;
  loadedAt: number;
  busy: boolean;
  onBusyChange: (busy: boolean) => void;
  onReload: () => Promise<void>;
  onUpdated: (row: FollowUp) => void;
  timestamp: (value: string) => string;
  update?: (row: FollowUp, status: FollowUpAction) => Promise<FollowUp>;
}) {
  const [status, setStatus] = useState("ALL");
  const [kind, setKind] = useState("ALL");
  const [query, setQuery] = useState("");
  const [pending, setPending] = useState<{ row: FollowUp; status: FollowUpAction }>();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const inFlight = useRef(false);
  const visible = filterFollowUps(rows, status, kind, query);

  async function perform(refresh: boolean) {
    if (inFlight.current || busy || demo) return;
    if (!refresh && (!pending || needsRefresh)) return;
    inFlight.current = true;
    onBusyChange(true);
    setError("");
    setMessage("");
    try {
      if (refresh) {
        await onReload();
        setNeedsRefresh(false);
        setPending(undefined);
        setMessage("Follow-up queue refreshed.");
      } else if (pending) {
        const current = rows.find((row) => row.id === pending.row.id);
        if (!current || current.row_version !== pending.row.row_version || current.status !== pending.row.status) {
          throw new Error("This follow-up changed. Refresh before choosing another action.");
        }
        const result = update ? await update(current, pending.status) : await updateFollowUp(apiBaseUrl, token, current, pending.status, demo);
        onUpdated(result);
        setPending(undefined);
        setMessage(`Follow-up ${result.status.toLowerCase()}. No call or message was sent.`);
      }
    } catch (failure) {
      setNeedsRefresh(true);
      setError(failure instanceof Error ? failure.message : "Follow-up could not be updated.");
    } finally {
      inFlight.current = false;
      onBusyChange(false);
    }
  }

  return <section className="ops-card" aria-labelledby="follow-up-title" aria-busy={busy}>
    <div className={styles.heading}><div><h2 id="follow-up-title">Human follow-up</h2><p className="section-help">Oldest first in the loaded open queue. Acknowledging a request does not contact the customer.</p></div>
      {!demo && <button type="button" disabled={busy} onClick={() => void perform(true)}>Refresh follow-up</button>}
    </div>
    {demo && <p className="section-help">Demo records are read-only. Connect a workspace to update follow-up.</p>}
    <div className={styles.filters}>
      <label>Status<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="ALL">All open</option><option value="REQUESTED">Requested</option><option value="ACKNOWLEDGED">Acknowledged</option></select></label>
      <label>Follow-up type<select value={kind} onChange={(event) => setKind(event.target.value)}><option value="ALL">All types</option><option value="CALLBACK">Callbacks</option><option value="LIVE_TRANSFER">Human transfers</option></select></label>
      <label>Search loaded follow-up<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} autoComplete="off" /></label>
    </div>
    {error && <p className="ops-error" role="alert">{error} Refresh follow-up before another update.</p>}
    {message && <p className="ops-message" role="status">{message}</p>}
    {pending && <section className={styles.confirmation} aria-labelledby="follow-up-confirm-title">
      <h3 id="follow-up-confirm-title">{followUpActions[pending.status]}?</h3>
      <p>{pending.row.customer?.full_name ?? "Selected follow-up"} · {pending.row.reason}</p>
      <p>{pending.status === "COMPLETED" ? "Confirm only after your team has handled this request. This removes it from the open queue." : pending.status === "CANCELLED" ? "This closes the request without marking it completed and removes it from the open queue." : "This records that your team has seen the request. It stays in the open queue."} This does not place a call, send an email or attempt a transfer.</p>
      <div className={styles.actions}><button type="button" className="primary-button" disabled={busy || needsRefresh} onClick={() => void perform(false)}>Confirm {followUpActions[pending.status].toLowerCase()}</button><button type="button" disabled={busy} onClick={() => setPending(undefined)}>Keep current status</button></div>
    </section>}
    <p className="section-help">{visible.length} of {rows.length} loaded open requests · ages at last refresh</p>
    {!visible.length ? <p className="empty-state">{rows.length ? "No follow-up matches these filters." : "No pending callbacks or human handoffs."}</p> :
      <DashboardTable caption="Open human follow-up" headings={["Customer", "Follow-up", "Waiting", "Status", "Actions"]}>
        {visible.map((row) => <tr key={row.id}>
          <td><strong>{row.customer?.full_name ?? "Contact unavailable"}</strong><span className={styles.detail}>{row.customer?.phone ?? "No phone recorded"}</span><span className={styles.detail}>{row.customer?.email ?? "No email recorded"}</span></td>
          <td><strong>{row.kind.replaceAll("_", " ")}</strong><p>{row.reason}</p>{row.preferred_contact_method && <span className={styles.detail}>Preferred: {row.preferred_contact_method.replaceAll("_", " ")}</span>}{row.availability && <span className={styles.detail}>Availability: {row.availability}</span>}</td>
          <td>{followUpAge(row.created_at, loadedAt)}{row.created_at && Number.isFinite(Date.parse(row.created_at)) && <span className={styles.detail}>{timestamp(row.created_at)}</span>}</td>
          <td><StatusBadge status={row.status} /></td>
          <td><div className={styles.actions}>{allowedFollowUpActions(row).map((action) => <button type="button" key={action} disabled={demo || busy || needsRefresh} onClick={() => { setPending({ row, status: action }); setMessage(""); }}>{followUpActions[action]}</button>)}</div>{!allowedFollowUpActions(row).length && <span className={styles.detail}>Refresh with the updated backend to enable actions.</span>}</td>
        </tr>)}
      </DashboardTable>}
  </section>;
}
