import styles from "./loading-spinner.module.css";

export function LoadingSpinner({ label = "Loading…" }: { label?: string }) {
  return (
    <span className={styles.loading} role="status">
      <span className={styles.spinner} aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}
