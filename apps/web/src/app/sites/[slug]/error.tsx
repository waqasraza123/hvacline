"use client";

import Link from "next/link";
import styles from "@/features/websites/website.module.css";

export default function SiteError({ reset }: { reset: () => void }) {
  return (
    <main className={styles.utility}>
      <h1>This website could not be opened.</h1>
      <p>Please try again, or return to HVACLine home.</p>
      <button type="button" onClick={reset}>
        Try again
      </button>
      <p>
        <Link href="/">Back to HVACLine home</Link>
      </p>
    </main>
  );
}
