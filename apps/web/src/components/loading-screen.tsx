import { Brand } from "./brand";
import styles from "./loading-screen.module.css";

export function LoadingScreen({
  label = "Getting things ready…",
}: {
  label?: string;
}) {
  return (
    <main className={styles.screen} aria-busy="true">
      <div className={styles.content}>
        <Brand />
        <div className={styles.signal} aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
          <span />
        </div>
        <p className={styles.label} role="status">
          {label}
        </p>
      </div>
    </main>
  );
}
