"use client";

import { useEffect, useState } from "react";
import { ProductIcon } from "@/components/product-icons";
import { recoveryApi } from "./api";
import type { RecoverySummary } from "./api";
import type { DemoState } from "./demo";
import { DemoMetrics } from "./demo-panel";
import styles from "./recovery.module.css";

export function RecoverySpotlight({ demo, state, apiBaseUrl, token, refreshedAt, onOpen, onSetup }: { demo: boolean; state: DemoState; apiBaseUrl: string; token: string; refreshedAt: number; onOpen: () => void; onSetup: () => void }) {
  const [summary, setSummary] = useState<RecoverySummary | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (demo) return;
    let active = true;
    setSummary(null); setError("");
    recoveryApi(apiBaseUrl, token)<RecoverySummary>("summary").then((result) => { if (active) setSummary(result); }).catch((error: unknown) => { if (active) setError(error instanceof Error ? error.message : "Recovery summary is unavailable."); });
    return () => { active = false; };
  }, [apiBaseUrl, token, demo, refreshedAt]);
  return <section className={`${styles.root} ${styles.frame} ${styles.spotlight}`}>
    <div className={styles.toolbar}><div><p className={styles.eyebrow}>AI LEAD RECOVERY</p><h2>Give missed opportunities a next step.</h2></div><span className={styles.badge}>{demo ? "DEMO DATA" : "LIVE WORKSPACE"}</span></div>
    <p className={styles.muted}>Recover missed calls and unfinished bookings with permission-based follow-up.</p>
    {demo ? <><DemoMetrics state={state} /><p className={styles.muted}>Latest simulation: {state.activity[0]?.message}</p></> : error ? <p role="alert">{error}</p> : summary ? <><div className={styles.metrics}>{[{ label: "Recoverable leads", value: summary.recoverable }, { label: "Scheduled follow-ups", value: summary.scheduled }, { label: "Recovered bookings", value: summary.recovered }, { label: "Conversion rate", value: `${(summary.conversion_rate * 100).toFixed(1)}%` }].map((metric) => <div className={styles.metric} key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong></div>)}</div><p className={styles.muted}>{summary.recent.length ? `Recent activity: ${summary.recent.map((event) => event.status.toLowerCase().replaceAll("_", " ")).join(" · ")}` : "No recovery activity yet. Review the setup checklist."}</p></> : <p role="status">Loading actual recovery metrics…</p>}
    <div className={styles.actions}><button type="button" className={styles.primary} onClick={onOpen}>{demo ? "Try interactive recovery demo" : "Open AI Lead Recovery"}<ProductIcon name="arrow" /></button><button type="button" onClick={onSetup}>{demo ? "Set Up AI Recovery" : "Configure recovery"}</button></div>
  </section>;
}
