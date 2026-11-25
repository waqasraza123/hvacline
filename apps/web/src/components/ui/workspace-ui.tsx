import type { ReactNode } from "react";
import styles from "./workspace-ui.module.css";

export function PageHeader({ title, description, actions }: {
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return <div className={styles.pageHeader}>
    <div><h1>{title}</h1><p className={styles.description}>{description}</p></div>
    {actions && <div className={styles.actions}>{actions}</div>}
  </div>;
}

export function ContentPanel({ title, description, actions, children }: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return <section className={styles.panel} aria-label={title}>
    <div className={styles.panelHeader}><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{actions}</div>
    {children}
  </section>;
}

export function MetricCard({ label, value, help, icon, onClick }: {
  label: string;
  value: ReactNode;
  help: string;
  icon?: ReactNode;
  onClick?: () => void;
}) {
  const content = <><span className={styles.metricTop}><span>{label}</span>{icon}</span><strong className={styles.value}>{value}</strong><span className={styles.help}>{help}</span></>;
  return onClick
    ? <button type="button" className={styles.metric} onClick={onClick}>{content}</button>
    : <div className={styles.metric}>{content}</div>;
}

export function Badge({ children, tone = "neutral" }: {
  children: ReactNode;
  tone?: "neutral" | "accent" | "success" | "warning" | "error";
}) {
  return <span className={styles.badge} data-tone={tone}>{children}</span>;
}

export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return <div className={styles.empty}><h3>{title}</h3><p>{children}</p></div>;
}

export function LoadingSkeleton({ label }: { label: string }) {
  return <div className={styles.skeleton} role="status" aria-label={label}>
    <span aria-hidden="true" /><span aria-hidden="true" /><span aria-hidden="true" />
  </div>;
}
