"use client";

import { useId, useState } from "react";
import type { Dispatch } from "react";
import { ProductIcon } from "@/components/product-icons";
import { availableDemoSlots, demoMetrics } from "./demo";
import type { DemoAction, DemoState, DemoStatus } from "./demo";
import styles from "./recovery.module.css";

const filters: { label: string; status?: DemoStatus }[] = [{ label: "All" }, { label: "Scheduled", status: "SCHEDULED" }, { label: "Awaiting response", status: "AWAITING_RESPONSE" }, { label: "Recovered", status: "RECOVERED" }, { label: "Needs review", status: "NEEDS_REVIEW" }, { label: "Closed", status: "CLOSED" }];
export const money = (value: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
export const statusLabel = (value: string) => value.replaceAll("_", " ").toLowerCase();

export function DemoMetrics({ state }: { state: DemoState }) {
  const metrics = demoMetrics(state);
  return <div className={styles.metrics} aria-label="Demo recovery metrics">
    {[{ label: "Recovery opportunities", value: metrics.total, help: "Fictional cohort · all outcomes" }, { label: "Recovered appointments", value: metrics.recovered, help: "Simulated bookings only" },
      { label: "Recovery conversion", value: `${(metrics.conversion * 100).toFixed(1)}%`, help: "Recovered / fictional cohort" }, { label: "Estimated recovered revenue", value: money(metrics.revenue), help: "Fictional estimate · not actual revenue" }].map((metric) => <div className={styles.metric} key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong><small>{metric.help}</small></div>)}
  </div>;
}

export function RecoveryDemo({ state, dispatch, compact = false, onLive }: { state: DemoState; dispatch: Dispatch<DemoAction>; compact?: boolean; onLive?: () => void }) {
  const [filter, setFilter] = useState<DemoStatus>();
  const [selectedSlot, setSelectedSlot] = useState("");
  const heading = useId();
  const selected = state.cases.find((row) => row.id === state.selectedId)!;
  const rows = state.cases.filter((row) => !filter || row.status === filter);
  const slots = availableDemoSlots(state);
  const metrics = demoMetrics(state);
  const canStart = ["SCHEDULED", "AWAITING_RESPONSE"].includes(selected.status) && selected.step === "IDLE";
  return <section className={`${styles.root} ${styles.frame}`} aria-labelledby={heading}>
    <div className={styles.toolbar}><div><p className={styles.eyebrow}>A second chance at the next job</p><h2 id={heading}>AI Lead Recovery</h2></div><div className={styles.actions}><span className={styles.badge}>DEMO MODE · DEMO DATA</span><button type="button" onClick={() => { dispatch({ type: "RESET" }); setFilter(undefined); setSelectedSlot(""); }}>Reset Demo</button>{onLive && <button type="button" onClick={onLive}>Switch to Live Mode <ProductIcon name="arrow" /></button>}</div></div>
    <p className={styles.muted}>Fictional customers and simulated conversations. This demo never contacts a provider or creates a real booking.</p>
    <DemoMetrics state={state} />
    <div className={styles.toolbar}><p className={styles.muted}>{metrics.scheduled} scheduled · {metrics.awaiting} awaiting responses · 24 fictional opportunities</p><label className={styles.revenue}>Fictional job value <input aria-label="Fictional average job value in USD" type="number" min="0" max="100000" step="50" value={state.jobValue} onChange={(event) => dispatch({ type: "VALUE", value: Number(event.target.value) })} /> USD</label></div>
    <div className={styles.split}>
      <div className={styles.panel}>
        <h3>Every opportunity has a next step</h3>
        {!compact && <div className={styles.filters} aria-label="Filter fictional cases">{filters.map((item) => <button type="button" key={item.label} aria-pressed={item.status === filter} onClick={() => setFilter(item.status)}>{item.label}</button>)}</div>}
        <div className={styles.tableWrap}><table className={styles.table}><caption className={styles.muted}>DEMO DATA · select a fictional customer to explore</caption><thead><tr><th>Customer / source</th><th>Contact / status</th>{!compact && <><th>Last activity / next attempt</th><th>Outcome</th></>}<th>Action</th></tr></thead><tbody>
          {(compact ? [selected, ...rows.filter((row) => row.id !== selected.id)].slice(0, 4) : rows).map((row) => <tr key={row.id} aria-selected={row.id === selected.id}><td><button type="button" className={styles.rowButton} onClick={() => { dispatch({ type: "SELECT", id: row.id }); setSelectedSlot(""); }}>{row.customer}</button><small>{row.source} · DEMO DATA</small></td><td>{row.channel === "VOICE" ? "AI call simulation" : "SMS simulation"}<br /><span className={styles.status} data-status={row.status}>{statusLabel(row.status)}</span></td>{!compact && <><td>{row.lastActivity}<small>{row.status === "SCHEDULED" ? "Next: Nov 20 · 4:00 PM ET (fictional)" : "No scheduled demo contact"}</small></td><td>{row.appointment?.label ?? (row.status === "CLOSED" ? "Closed in demo" : "No booking")}</td></>}<td><button type="button" aria-label={`Explore ${row.customer}, demo data`} onClick={() => { dispatch({ type: "SELECT", id: row.id }); setSelectedSlot(""); }}>Explore</button></td></tr>)}
          {!rows.length && <tr><td colSpan={compact ? 3 : 5}>No fictional cases match this filter.</td></tr>}
        </tbody></table></div>
      </div>
      <div className={styles.panel} aria-label="Selected fictional recovery case">
        <div className={styles.toolbar}><div><span className={styles.badge}>DEMO DATA</span><h3 style={{ marginTop: ".8rem" }}>{selected.customer}</h3></div><ProductIcon name={selected.channel === "VOICE" ? "phone" : "chat"} /></div>
        <p className={styles.muted}>{selected.reference} · {selected.source}<br />{selected.service}</p>
        <details open key={selected.id}><summary>Why this qualifies</summary><p className={styles.muted}>{selected.reason}</p><p className={styles.muted}>Consent, eligibility, contact times and slots in this panel are fictional. Live Mode checks persisted permission and scheduling separately.</p></details>
        {canStart && <button type="button" className={styles.primary} onClick={() => dispatch({ type: "START" })}><ProductIcon name="phone" /> Start simulated AI follow-up</button>}
        {selected.step !== "IDLE" && <div className={styles.chat} aria-live="polite">
          <div className={styles.bubble}><small>DEMO DATA · SIMULATED AI ASSISTANT</small>Hi, this is the AI assistant for Demo Comfort HVAC. You recently asked about {selected.service.split(" · ")[0].toLowerCase()} but didn’t finish booking. Would you like help scheduling? {selected.channel === "SMS" && "Reply YES for help or STOP to opt out."}</div>
          {["SLOTS", "BOOKED"].includes(selected.step) && <><div className={`${styles.bubble} ${styles.customer}`}><small>DEMO DATA · SIMULATED CUSTOMER</small>Yes, I’d like to continue.</div><div className={styles.bubble}><small>DEMO DATA · SIMULATED AI ASSISTANT</small>I have your confirmed service details. Here are the available fictional appointment times. Choose one, then confirm your simulated booking.</div></>}
          {selected.step === "DECLINED" && <div className={`${styles.bubble} ${styles.customer}`}><small>DEMO DATA · SIMULATED CUSTOMER</small>STOP. Please don’t follow up.</div>}
          {selected.appointment && <div className={styles.bubble}><small>DEMO DATA · SIMULATED BOOKING CONFIRMATION</small>{selected.appointment.label}<br />Fictional appointment confirmed. No real appointment, calendar event or provider action occurred.</div>}
        </div>}
        {selected.step === "ASKED" && <div className={styles.actions}><button type="button" className={styles.primary} onClick={() => dispatch({ type: "YES" })}>Simulate customer YES</button><button type="button" onClick={() => dispatch({ type: "STOP" })}>Simulate STOP</button></div>}
        {selected.step === "SLOTS" && <div className={styles.slots}>
          {slots.map((slot) => <button type="button" key={slot.id} aria-pressed={selectedSlot === slot.id} onClick={() => setSelectedSlot(slot.id)}>{slot.label}<span>DEMO</span></button>)}
          {!slots.length && <p className={styles.muted}>All fictional slots have been used. Reset Demo to explore again.</p>}
          <button type="button" className={styles.primary} disabled={!slots.some((slot) => slot.id === selectedSlot)} onClick={() => dispatch({ type: "BOOK", slotId: selectedSlot })}>Confirm simulated booking</button>
          <button type="button" onClick={() => dispatch({ type: "STOP" })}>Simulate STOP</button>
        </div>}
        {["NEEDS_REVIEW", "CLOSED"].includes(selected.status) && <p className={styles.notice}>This demo case cannot be contacted. Select a scheduled case to explore the simulation.</p>}
        {state.notice && <p className={styles.notice} role="status">DEMO DATA · {state.notice}</p>}
      </div>
    </div>
    {!compact && <section className={styles.panel} style={{ marginTop: "1rem" }} aria-label="Simulated follow-up activity"><h3>Recent SMS & AI call simulations</h3><ul className={styles.activity}>{state.activity.slice(0, 6).map((event) => <li key={event.id}><span className={styles.badge}>DEMO DATA</span> {event.message}<small>{state.cases.find((row) => row.id === event.caseId)?.customer} · {event.channel} simulation · {event.time}</small></li>)}</ul></section>}
  </section>;
}
