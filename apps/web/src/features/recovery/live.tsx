"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AiSettings } from "./ai-settings";
import { recoveryApi } from "./api";
import type { AiConnection, CasePage, RecoveryCase, RecoveryPolicy, RecoverySettings, RecoverySummary } from "./api";
import { statusLabel } from "./demo-panel";
import styles from "./recovery.module.css";

const filters = ["ALL", "PENDING", "SCHEDULED", "AWAITING_RESPONSE", "RECOVERED", "NEEDS_REVIEW", "CLOSED"];
type LiveData = { page: CasePage; summary: RecoverySummary; settings: RecoverySettings; ai: AiConnection; staff: string[] };
const stamp = (value: string | null, timezone: string) => value ? new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: timezone }).format(new Date(value)) : "—";

export function RecoveryLive({ apiBaseUrl, token, onDemo }: { apiBaseUrl: string; token: string; onDemo: () => void }) {
  const api = useMemo(() => recoveryApi(apiBaseUrl, token), [apiBaseUrl, token]);
  const [data, setData] = useState<LiveData | null>(null);
  const [policy, setPolicy] = useState<RecoveryPolicy | null>(null);
  const [filter, setFilter] = useState("ALL");
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [selectedId, setSelectedId] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [staff, setStaff] = useState("");
  const [draft, setDraft] = useState("");
  const [consentChannel, setConsentChannel] = useState<"SMS" | "VOICE" | "ALL">("SMS");
  const [consentGranted, setConsentGranted] = useState(false);
  const [evidence, setEvidence] = useState("");
  const [observedAt, setObservedAt] = useState("");
  const [consentSource, setConsentSource] = useState("SIGNED_FORM");
  const [attested, setAttested] = useState(false);
  const actionKeys = useRef(new Map<string, string>());
  const reload = useCallback(() => setRefresh((value) => value + 1), []);

  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    const query = `cases?limit=25&offset=${offset}${filter === "ALL" ? "" : `&status=${filter}`}`;
    Promise.all([api<CasePage>(query), api<RecoverySummary>("summary"), api<RecoverySettings>("settings"), api<AiConnection>("ai"), api<{ items: string[] }>("staff")])
      .then(([page, summary, settings, ai, team]) => { if (active) { setData({ page, summary, settings, ai, staff: team.items }); setPolicy(settings.policy); } })
      .catch((error: unknown) => { if (active) { setData(null); setError(error instanceof Error ? error.message : "Recovery data is unavailable."); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [api, filter, offset, refresh]);

  const selected = data?.page.items.find((row) => row.id === selectedId);
  const timezone = data?.settings.policy.timezone ?? "America/New_York";
  async function act(task: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await task(); } catch (error) { setError(error instanceof Error ? error.message : "This operation could not finish."); } finally { setBusy(false); }
  }
  async function action(row: RecoveryCase, action: string) {
    const body = { action, expected_row_version: row.row_version, ...(action === "ASSIGN" ? { assigned_to: staff } : {}) };
    const fingerprint = JSON.stringify({ id: row.id, ...body });
    const key = actionKeys.current.get(fingerprint) ?? crypto.randomUUID();
    actionKeys.current.set(fingerprint, key);
    await api(`cases/${row.id}/action`, "POST", body, key);
    setMessage(`Case action recorded: ${statusLabel(action)}.`); reload();
  }
  const onAiChange = (ai: AiConnection) => setData((previous) => previous ? { ...previous, ai } : previous);

  return <div className={styles.root}>
    <div className={styles.toolbar}><div><span className={styles.badge}>LIVE MODE · AUTHENTICATED WORKSPACE</span><p className={styles.muted} style={{ marginTop: ".7rem" }}>Actual agency records only. Outbound automation starts disabled.</p></div><div className={styles.actions}><button type="button" disabled={busy || loading} onClick={reload}>Refresh recovery</button><button type="button" onClick={onDemo}>Explore Demo Mode</button></div></div>
    {loading && <p role="status" className={styles.notice}>Loading protected recovery records…</p>}
    {error && <p role="alert" className={styles.notice}>{error} No demo data is substituted in Live Mode. Refresh saved status before retrying a write.</p>}
    {message && <p role="status" className={styles.notice}>{message}</p>}
    {data && policy && <>
      <ol className={styles.setup} aria-label="Recovery setup progress">
        <li>Explore the demo<small>Available without setup</small></li>
        <li>Connect your AI model<small>{data.ai.status === "CONNECTED" ? "Configured · text assistance" : "Missing or untested"}</small></li>
        <li>Configure SMS / voice<small>{data.settings.providers.SMS.available || data.settings.providers.VOICE.available ? "Provider available" : "Missing · recovery delivery unavailable"}</small></li>
        <li>Review rules & permissions<small>{policy.expected_row_version ? "Rules saved · permission required per contact" : "Defaults · review required"}</small></li>
        <li>Enable automation<small>{policy.enabled && data.settings.runtime_enabled ? "Enabled by administrator" : "Disabled"}</small></li>
      </ol>
      <div className={styles.notice}><strong>Finish setup before automated contact</strong><p>{data.settings.providers.SMS.reason} {data.settings.providers.VOICE.reason}</p><p className={styles.muted}>{data.settings.identity_gate}</p></div>
      <div className={styles.metrics} aria-label="Live recovery metrics">
        {[{ label: "Recoverable leads", value: data.summary.recoverable }, { label: "Scheduled follow-ups", value: data.summary.scheduled }, { label: "Follow-ups attempted", value: data.summary.attempted }, { label: "Recovered bookings", value: data.summary.recovered }, { label: "Recovery conversion", value: `${(data.summary.conversion_rate * 100).toFixed(1)}%` }].map((metric) => <div className={styles.metric} key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong></div>)}
      </div>
      <section className={styles.panel}>
        <div className={styles.toolbar}><h2>Recovery cases</h2><a className={styles.link} href="#recovery-ai-settings">AI Provider Settings</a></div>
        <div className={styles.filters} aria-label="Filter live recovery cases">{filters.map((status) => <button type="button" key={status} disabled={busy || loading} aria-pressed={filter === status} onClick={() => { setFilter(status); setOffset(0); setSelectedId(""); setDraft(""); }}>{statusLabel(status)}</button>)}</div>
        {data.page.total === 0 ? <p className={styles.notice}>No recovery cases match this view. Only new persisted activity with confirmed routine service details is eligible. Historical leads are never silently enrolled.</p> : <div className={styles.tableWrap}><table className={styles.table}><caption className={styles.muted}>{data.page.total} agency-owned cases · timestamps in {timezone}</caption><thead><tr>{["Customer", "Source", "Contact method", "Status", "Last activity", "Next attempt", "Outcome", "Actions"].map((heading) => <th key={heading}>{heading}</th>)}</tr></thead><tbody>{data.page.items.map((row) => <tr key={row.id}><td><strong>{row.customer}</strong></td><td>{statusLabel(row.source_type)}</td><td>{row.attempts.at(-1)?.channel ?? "Not scheduled"}</td><td><span className={styles.status} data-status={row.status}>{statusLabel(row.status)}{row.paused ? " · paused" : ""}</span></td><td>{stamp(row.last_activity_at, timezone)}</td><td>{stamp(row.next_attempt, timezone)}</td><td>{row.recovered_appointment_id ? "Attributed booking" : row.reason ? statusLabel(row.reason) : "No booking"}</td><td><button type="button" onClick={() => { setSelectedId(row.id); setDraft(""); setEvidence(""); setAttested(false); }}>Details</button></td></tr>)}</tbody></table></div>}
        <div className={styles.actions} style={{ marginTop: "1rem" }}><button type="button" disabled={offset === 0 || busy || loading} onClick={() => setOffset(Math.max(0, offset - 25))}>Previous</button><button type="button" disabled={offset + 25 >= data.page.total || busy || loading} onClick={() => setOffset(offset + 25)}>Next</button><span className={styles.muted}>{data.page.total ? `${offset + 1}–${Math.min(offset + 25, data.page.total)}` : "0"} of {data.page.total}</span></div>
      </section>
      {selected && <section className={styles.panel} style={{ marginTop: "1rem" }}>
        <div className={styles.toolbar}><h2>{selected.customer}</h2><span className={styles.status} data-status={selected.status}>{statusLabel(selected.status)}</span></div>
        <p>{selected.summary}</p><p className={styles.muted}>Original {statusLabel(selected.source_type)}: {selected.source_reference}<br />Service request: {selected.service_request_id}{selected.lead_id && <><br />Lead: {selected.lead_id}</>}<br />Eligible after: {stamp(selected.eligible_at, timezone)}<br />Outcome: {selected.reason ? statusLabel(selected.reason) : "Not contacted"}{selected.recovered_appointment_id && <><br />Confirmed recovered appointment: {selected.recovered_appointment_id}</>}</p>
        {selected.inbound_call_id && <p className={styles.muted}>Original call: {selected.inbound_call_id}</p>}
        {selected.conversation_session_id && <p className={styles.muted}>Original conversation: {selected.conversation_session_id}</p>}
        {selected.booking && <p className={styles.notice}>Saved appointment · {statusLabel(selected.booking.status)}<br />{stamp(selected.booking.starts_at, timezone)} – {stamp(selected.booking.ends_at, timezone)}<br />Team: {selected.booking.team_key}<br />{selected.recovered_appointment_id ? "Attributed recovery booking" : "Independent booking; no recovery credit"}</p>}
        <div className={styles.actions}>
          {!["RECOVERED", "CLOSED", "SUPPRESSED"].includes(selected.status) && <><button type="button" disabled={busy} onClick={() => void act(() => action(selected, selected.paused ? "RESUME" : "PAUSE"))}>{selected.paused ? "Resume with authorization checks" : "Pause case"}</button><button type="button" disabled={busy || !data.settings.providers.SMS.available && !data.settings.providers.VOICE.available || selected.attempts.some((attempt) => ["UNKNOWN", "STARTED", "QUEUED"].includes(attempt.status))} onClick={() => void act(() => action(selected, "RETRY"))}>Request authorized retry</button><button type="button" disabled={busy} onClick={() => void act(() => action(selected, "CLOSE"))}>Close case</button></>}
          <button type="button" disabled={busy || data.ai.status !== "CONNECTED"} onClick={() => void act(async () => { const result = await api<{ draft: string; connection: AiConnection }>(`cases/${selected.id}/draft`, "POST", { expected_row_version: data.ai.row_version }); setDraft(result.draft); onAiChange(result.connection); })}>Generate staff text draft · API request</button>
        </div>
        {draft && <p className={styles.notice}><strong>AI draft · staff review required · nothing sent</strong><br />{draft}</p>}
        {!["RECOVERED", "CLOSED", "SUPPRESSED"].includes(selected.status) && <div className={styles.form}><label>Assign to agency staff<select value={staff} onChange={(event) => setStaff(event.target.value)}><option value="">Choose staff member</option>{data.staff.map((identifier) => <option key={identifier} value={identifier}>{identifier}</option>)}</select></label><button type="button" disabled={!staff || busy} onClick={() => void act(() => action(selected, "ASSIGN"))}>Assign and pause automation</button></div>}
        <h3 style={{ marginTop: "1.5rem" }}>Contact permission & eligibility</h3>
        {selected.permissions.length === 0 && <p className={styles.muted}>No verified recovery permission is recorded. Saved phone numbers, sign-in, inbound calls and general booking consent never authorize automated contact.</p>}
        <ul className={styles.activity}>{selected.permissions.map((permission) => <li key={permission.channel}>{permission.channel} · {permission.revoked_at ? "REVOKED / SUPPRESSED" : "Explicit permission recorded"}<small>{permission.scope} · {permission.source} · evidence {permission.evidence_reference} · {permission.revoked_at ?? permission.granted_at}</small></li>)}</ul>
        <details><summary>Record explicit permission or revocation</summary><form className={styles.form} onSubmit={(event) => { event.preventDefault(); void act(async () => {
          const existing = selected.permissions.find((row) => row.channel === consentChannel);
          await api(`cases/${selected.id}/permission`, "PUT", { expected_row_version: existing?.row_version ?? 0, channel: consentChannel, granted: consentGranted,
            source: consentGranted ? consentSource : "CUSTOMER_REVOCATION", evidence_reference: evidence, observed_at: new Date(observedAt).toISOString() });
          setAttested(false); setEvidence(""); setMessage("Permission evidence recorded. No contact initiated."); reload();
        }); }}>
          <label>Channel<select value={consentChannel} onChange={(event) => { setConsentChannel(event.target.value as typeof consentChannel); setConsentGranted(false); }}><option value="SMS">SMS recovery</option><option value="VOICE">AI voice recovery</option><option value="ALL">All automated contact · revoke only</option></select></label>
          <label className={styles.check}><input type="checkbox" checked={consentGranted} disabled={consentChannel === "ALL"} onChange={(event) => setConsentGranted(event.target.checked)} />Record a new explicit grant (unchecked records revocation)</label>
          {consentGranted && <label>Evidence source<select value={consentSource} onChange={(event) => setConsentSource(event.target.value)}><option value="SIGNED_FORM">Signed customer form</option><option value="RECORDED_EXPLICIT_PERMISSION">Recorded explicit customer permission</option></select></label>}
          <label>Non-sensitive evidence reference<input value={evidence} pattern="[A-Za-z0-9_.:\-]{1,128}" required maxLength={128} onChange={(event) => setEvidence(event.target.value)} /></label>
          <label>When permission / revocation was observed<input type="datetime-local" required value={observedAt} onChange={(event) => setObservedAt(event.target.value)} /></label>
          <label className={styles.check}><input type="checkbox" required checked={attested} onChange={(event) => setAttested(event.target.checked)} />I reviewed actual channel-specific customer evidence. This is not inferred from a booking or inbound call.</label>
          <button type="submit" disabled={busy || !attested}>Record permission evidence</button>
        </form></details>
        <h3>Follow-up attempt history</h3>{!selected.attempts.length ? <p className={styles.muted}>No recovery contact has been attempted.</p> : <ul className={styles.activity}>{selected.attempts.map((attempt) => <li key={attempt.id}>Attempt {attempt.attempt_number} · {attempt.channel} · {statusLabel(attempt.status)}<small>Scheduled {stamp(attempt.scheduled_at, timezone)} · started {stamp(attempt.started_at, timezone)}{attempt.failure_code ? ` · ${attempt.failure_code}` : ""}</small></li>)}</ul>}
      </section>}
      <div style={{ marginTop: "1.5rem" }}><AiSettings key={data.ai.provider ?? "new"} connection={data.ai} api={api} onChange={onAiChange} /></div>
      <section className={styles.panel} style={{ marginTop: "1.5rem" }}><h2>Recovery rules & communication providers</h2><p className={styles.muted}>Permissions are checked again before every attempt. Maximum two contacts over seven days, at least 24 hours apart. Unknown provider outcomes block retries.</p>
        <form className={styles.form} onSubmit={(event) => { event.preventDefault(); void act(async () => { await api("settings", "PUT", policy); setMessage("Recovery rules saved. Automation remains subject to backend and provider gates."); reload(); }); }}>
          <div className={styles.formGrid}><label>Agency timezone<input value={policy.timezone} required onChange={(event) => setPolicy({ ...policy, timezone: event.target.value })} /></label><label>Maximum attempts<input type="number" min="1" max="2" required value={policy.max_attempts} onChange={(event) => setPolicy({ ...policy, max_attempts: Number(event.target.value) })} /></label><label>Contact window starts<input type="time" min="09:00" max="17:59" required value={policy.contact_start.slice(0, 5)} onChange={(event) => setPolicy({ ...policy, contact_start: event.target.value })} /></label><label>Contact window ends<input type="time" min="09:01" max="18:00" required value={policy.contact_end.slice(0, 5)} onChange={(event) => setPolicy({ ...policy, contact_end: event.target.value })} /></label><label>Minimum hours between attempts<input type="number" min="24" max="168" required value={policy.interval_hours} onChange={(event) => setPolicy({ ...policy, interval_hours: Number(event.target.value) })} /></label><label>Recovery expires after days<input type="number" min="1" max="7" required value={policy.expiry_days} onChange={(event) => setPolicy({ ...policy, expiry_days: Number(event.target.value) })} /></label></div>
          {(["SMS", "VOICE"] as const).map((channel) => <label key={channel} className={styles.check}><input type="checkbox" checked={policy.channels.includes(channel)} onChange={(event) => setPolicy({ ...policy, channels: event.target.checked ? [...policy.channels, channel] : policy.channels.filter((value) => value !== channel) })} />Allow {channel === "VOICE" ? "AI voice" : "SMS"} when a supported provider and explicit customer permission exist · {data.settings.providers[channel].available ? "available" : "provider unavailable"}</label>)}
          <label className={styles.check}><input type="checkbox" checked={policy.enabled} disabled={!policy.enabled && (!data.settings.runtime_enabled || data.ai.status !== "CONNECTED" || !data.settings.providers.SMS.available && !data.settings.providers.VOICE.available)} onChange={(event) => setPolicy({ ...policy, enabled: event.target.checked })} />Enable automated recovery (requires supported delivery setup)</label>
          <button type="submit" className={styles.primary} disabled={busy}>Save recovery rules</button>
        </form>
      </section>
    </>}
  </div>;
}
