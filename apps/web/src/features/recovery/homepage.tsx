import Link from "next/link";
import styles from "./recovery.module.css";

export function RecoveryHomepage() {
  return (
    <section
      className={`${styles.root} ${styles.teaser} product-container`}
      id="ai-lead-recovery"
      aria-labelledby="recovery-teaser-heading"
    >
      <div className={styles.teaserCard}>
        <div className={styles.teaserCopy}>
          <p className={styles.eyebrow}>AI LEAD RECOVERY</p>
          <h2 id="recovery-teaser-heading">Give missed opportunities a next step.</h2>
          <p>
            Explore follow-up for missed calls and unfinished bookings in the
            interactive dashboard demo.
          </p>
        </div>
        <Link
          className={`${styles.link} ${styles.primary}`}
          href="/ai-lead-recovery"
        >
          Try Yourself
        </Link>
      </div>
    </section>
  );
}
