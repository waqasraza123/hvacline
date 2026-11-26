"use client";

import { useEffect, useRef, useState } from "react";
import { MetricCard } from "@/components/ui/workspace-ui";
import { FollowUpQueue } from "@/features/operations/follow-up-queue";
import { updateFollowUp } from "@/features/operations/follow-up";
import { ScheduleForm } from "@/features/operations/schedule-form";
import { DashboardTable, StatusBadge } from "@/features/operations/dashboard-table";
import type { Operations, ScheduleResponse } from "@/features/operations/api";
import { isRecord, parseWorkspaceOperations, workspaceRequest } from "./api";
import type { Role } from "./api";
import { TeamPanel } from "./team";
import { BusinessProfile } from "./profile";
import styles from "./workspace.module.css";

function scheduleView(value: unknown): ScheduleResponse {
  if (!isRecord(value) || typeof value.version !== "number" || !Number.isSafeInteger(value.version) || value.version < 0 ||
    value.configuration !== null && (!isRecord(value.configuration) || typeof value.configuration.timezone !== "string" || !Array.isArray(value.configuration.postal_codes) || !Array.isArray(value.configuration.windows) || !Array.isArray(value.configuration.teams))) throw new Error("Business scheduling data could not be verified.");
  return value as ScheduleResponse;
}

export function BusinessWorkspace({ business, busy, onBusyChange, onIdentityChange }: { business: { id: string; name: string; role: Role }; busy: boolean; onBusyChange: (value: boolean) => void; onIdentityChange: () => Promise<void> }) {
  const [data, setData] = useState<Operations>();
  const [schedule, setSchedule] = useState<ScheduleResponse>();
  const [loadedAt, setLoadedAt] = useState(0);
  const [revision, setRevision] = useState(0);
  const [tab, setTab] = useState("overview");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const write = useRef(false);
  const canManage = business.role !== "STAFF";
  const path = `businesses/${business.id}`;
  async function load() {
    const [operations, configuration] = await Promise.all([workspaceRequest(`${path}/hvac/operations`), workspaceRequest(`${path}/hvac/schedule`)]);
    setData(parseWorkspaceOperations(operations)); setSchedule(scheduleView(configuration)); setLoadedAt(Date.now());
  }
  useEffect(() => {
    let active = true; setLoading(true); setError("");
    void Promise.all([workspaceRequest(`${path}/hvac/operations`), workspaceRequest(`${path}/hvac/schedule`)]).then(([operations, configuration]) => {
      if (active) { setData(parseWorkspaceOperations(operations)); setSchedule(scheduleView(configuration)); setLoadedAt(Date.now()); }
    }).catch((failure: unknown) => { if (active) { setData(undefined); setError(failure instanceof Error ? failure.message : "Business queues could not be loaded."); } }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [path, revision]);
  const stamp = (value: string) => new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: schedule?.configuration?.timezone ?? "UTC" }).format(new Date(value));
  return <section>
    <div className={styles.toolbar}><h2>{business.name}</h2><span>{business.role}</span><button type="button" disabled={busy || loading} onClick={() => setRevision((value) => value + 1)}>Reload business</button></div>
    <nav className={styles.tabs} aria-label="Business workspace sections">{["overview", "follow-up", ...(canManage ? ["team", "profile", "scheduling"] : [])].map((key) => <button type="button" key={key} aria-current={tab === key ? "page" : undefined} disabled={busy} onClick={() => setTab(key)}>{key === "follow-up" ? "Follow-up" : key[0].toUpperCase() + key.slice(1)}</button>)}</nav>
    {loading && <p role="status">Loading business queues…</p>}{error && <p role="alert" className="ops-error">{error}</p>}
    {tab === "team" && canManage && <TeamPanel agencyId={business.id} busy={busy} onBusyChange={onBusyChange} onIdentityChange={onIdentityChange} />}
    {tab === "profile" && canManage && <BusinessProfile agencyId={business.id} name={business.name} busy={busy} onBusyChange={onBusyChange} />}
    {tab === "scheduling" && canManage && schedule && <ScheduleForm key={`${business.id}:${schedule.version}`} value={schedule} busy={busy} save={async (configuration) => {
      if (write.current || busy) return; write.current = true; onBusyChange(true);
      try { await workspaceRequest(`${path}/hvac/schedule`, "PUT", configuration); await load(); }
      catch (failure) { setSchedule(undefined); setError((failure instanceof Error ? failure.message : "Scheduling could not be saved.") + " Reload the business before another change."); throw failure; }
      finally { write.current = false; onBusyChange(false); }
    }} />}
    {tab === "follow-up" && data && <FollowUpQueue rows={data.handoffs} demo={false} apiBaseUrl="" token="" busy={busy} loadedAt={loadedAt} onBusyChange={onBusyChange} onReload={load} timestamp={stamp}
      update={(row, status) => updateFollowUp("", "", row, status, false, (resource, body) => workspaceRequest(`${path}/${resource}`, "POST", body))}
      onUpdated={(row) => setData((value) => value ? { ...value, handoffs: value.handoffs.map((item) => item.id === row.id ? row : item).filter((item) => ["REQUESTED", "ACKNOWLEDGED"].includes(item.status)) } : value)} />}
    {tab === "overview" && data && <>
      <p>Counts reflect up to 100 loaded records per queue. Times in {schedule?.configuration?.timezone ?? "UTC"}. New businesses need a reviewed profile, real scheduling rules and separately provisioned phone/agent connections.</p>
      <div className={styles.metrics}><MetricCard label="Received calls" value={data.calls.length} help="Loaded business queue" /><MetricCard label="Service requests" value={data.service_requests.length} help="Confirmed service details" /><MetricCard label="Confirmed appointments" value={data.appointments.filter((row) => row.status === "CONFIRMED").length} help="Loaded bookings" /><MetricCard label="Open follow-up" value={data.handoffs.length} help="Staff attention required" /></div>
      <section className="ops-card"><h3>Service requests</h3>{!data.service_requests.length ? <p>No service requests recorded for this business.</p> : <DashboardTable caption="Business service requests" headings={["Customer", "Service", "Status"]}>{data.service_requests.map((row) => <tr key={row.id}><td>{row.customer.full_name}</td><td>{row.service.kind.replaceAll("_", " ")}</td><td><StatusBadge status={row.status} /></td></tr>)}</DashboardTable>}</section>
      <section className="ops-card"><h3>Appointments</h3>{!data.appointments.length ? <p>No appointments recorded for this business.</p> : <DashboardTable caption="Business appointments" headings={["Appointment", "Team", "Status"]}>{data.appointments.map((row) => <tr key={row.id}><td>{stamp(row.starts_at)}</td><td>{row.team_key}</td><td><StatusBadge status={row.status} /></td></tr>)}</DashboardTable>}</section>
    </>}
  </section>;
}
