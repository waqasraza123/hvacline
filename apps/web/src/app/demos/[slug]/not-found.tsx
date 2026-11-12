import Link from "next/link";
import styles from "@/features/websites/website.module.css";

export default function DemoNotFound() {
  return (
    <main className={styles.utility}>
      <h1>This demo is not in the collection.</h1>
      <p>Choose one of the available Voice AI website demos.</p>
      <Link href="/#voice-demos">Explore the demos</Link>
    </main>
  );
}
