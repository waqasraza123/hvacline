"use client";

import Link from "next/link";
import styles from "@/features/websites/website.module.css";

export default function DemoError({ reset }: { reset: () => void }) {
  return <main className={styles.utility}><h1>This demo could not be opened.</h1><p>Please try again, or return to the demo collection.</p><button type="button" onClick={reset}>Try again</button><p><Link href="/#voice-demos">Back to demos</Link></p></main>;
}
