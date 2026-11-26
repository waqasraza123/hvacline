"use client";

import { useEffect, useRef, useState } from "react";
import { DashboardTable, StatusBadge } from "./dashboard-table";
import { loadStaffAlerts, saveStaffAlertPolicy } from "./staff-alerts";
import type { StaffAlerts } from "./staff-alerts";
import styles from "./follow-up.module.css";

export function StaffAlertSettings({ apiBaseUrl, token, busy, onBusyChange, timestamp }: {
  apiBaseUrl: string; token: string; busy: boolean; onBusyChange: (value: boolean) => void; timestamp: (value: string) => string;
}) {
  const [data, setData] = useState<StaffAlerts>();
  const [enabled, setEnabled] = useState(false);
  const [recipients, setRecipients] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [needsReload, setNeedsReload] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const inFlight = useRef(false);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setData(undefined);
    setError("");
    void loadStaffAlerts(apiBaseUrl, token).then((value) => {
      if (!active) return;
      setData(value); setEnabled(value.policy.enabled); setRecipients(value.policy.recipients.join("\n"));
      setReviewed(false); setNeedsReload(false);
    }).catch((failure: unknown) => { if (active) setError(failure instanceof Error ? failure.message : "Staff alerts could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiBaseUrl, token, revision]);

  async function save() {
    if (!data || busy || inFlight.current || needsReload || enabled && !reviewed) return;
    inFlight.current = true;
    onBusyChange(true); setError(""); setMessage("");
    try {
      const addresses = recipients.split(/\r?\n/).map((value) => value.trim()).filter(Boolean);
      const policy = await saveStaffAlertPolicy(apiBaseUrl, token, data.policy, enabled, addresses);
      setData({ ...data, policy }); setEnabled(policy.enabled); setRecipients(policy.recipients.join("\n")); setReviewed(false);
      setMessage(policy.enabled ? "Staff alerts enabled for new requests. No test email was sent." : "Staff alerts disabled. Earlier accepted emails cannot be recalled.");
    } catch (failure) {
      setNeedsReload(true);
      setError(failure instanceof Error ? failure.message : "Settings could not be saved. Reload to review the saved outcome.");
    } finally { inFlight.current = false; onBusyChange(false); }
  }

  return <section className="ops-card" aria-labelledby="staff-alert-title" aria-busy={loading || busy}>
    <div className={styles.heading}><div><h2 id="staff-alert-title">Staff email alerts</h2><p className="section-help">Email your team about new callbacks, handoffs and urgent service requests. Historical requests are not enrolled.</p></div>
      <button type="button" disabled={busy || loading} onClick={() => { setMessage(""); setRevision((value) => value + 1); }}>Reload staff alerts</button>
    </div>
    {loading && <p role="status">Loading saved staff alerts…</p>}
    {error && <p role="alert" className="ops-error">{error} Reload saved settings before trying again.</p>}
    {message && <p role="status" className="ops-message">{message}</p>}
    {data && <>
      {!data.policy.runtime_enabled && <p className="section-help">Email delivery is not configured. Your administrator must finish Resend setup before enabling staff alerts.</p>}
      <p className="section-help">Sender: {data.policy.sender ?? "Not configured"}. Alerts contain request references, with customer details kept in the protected workspace.</p>
      <form onSubmit={(event) => { event.preventDefault(); void save(); }}>
        <label>Approved staff email addresses · one per line, maximum five<textarea value={recipients} disabled={busy} rows={5} maxLength={1600} autoComplete="off" onChange={(event) => { setRecipients(event.target.value); setReviewed(false); }} /></label>
        <label><input type="checkbox" checked={enabled} disabled={busy || !enabled && !data.policy.runtime_enabled} onChange={(event) => { setEnabled(event.target.checked); setReviewed(false); }} />Enable staff alerts for new requests</label>
        {enabled && <label><input type="checkbox" checked={reviewed} disabled={busy} onChange={(event) => setReviewed(event.target.checked)} />I reviewed the recipient list and authorize these staff notifications.</label>}
        <div className={styles.actions}><button type="submit" className="primary-button" disabled={busy || needsReload || enabled && !reviewed}>Save staff alerts</button><button type="button" disabled={busy} onClick={() => { setEnabled(data.policy.enabled); setRecipients(data.policy.recipients.join("\n")); setReviewed(false); setMessage(""); }}>Cancel changes</button></div>
      </form>
      <h3>Recent staff email delivery</h3>
      <p className="section-help">Accepted means Resend accepted the request. Delivery is confirmed separately. Unknown outcomes require review and are never automatically resent with a new reference.</p>
      {!data.recent.length ? <p className="empty-state">No staff email alerts recorded.</p> : <DashboardTable caption="Latest staff email alerts" headings={["Request", "Recipient", "Status", "Delivery", "Attempts"]}>
        {data.recent.map((row) => <tr key={row.id}><td>{row.event_type === "URGENT_SERVICE" ? "Urgent service review" : "Customer follow-up"}<span className={styles.detail}>{row.source_id}</span><span className={styles.detail}>{timestamp(row.created_at)}</span></td><td>{row.recipient}</td><td><StatusBadge status={row.status} />{row.last_error && <span className={styles.detail}>{row.last_error.replaceAll("_", " ")}</span>}</td><td>{row.delivery_status ?? "Not confirmed"}</td><td>{row.attempts}</td></tr>)}
      </DashboardTable>}
    </>}
  </section>;
}
