import styles from "@/features/websites/website.module.css";

export default function DemoLoading() {
  return <main className={styles.utility} aria-busy="true"><p role="status">Opening the demo website…</p><div className={styles.skeleton} aria-hidden="true" /></main>;
}
