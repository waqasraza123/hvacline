"use client";

import Link from "next/link";
import { useReducer } from "react";
import { ProductIcon } from "@/components/product-icons";
import { demoReducer, initialDemo } from "./demo";
import { RecoveryDemo } from "./demo-panel";
import styles from "./recovery.module.css";

export function RecoveryHomepage() {
  const [state, dispatch] = useReducer(demoReducer, undefined, initialDemo);
  return <section className={`${styles.root} ${styles.hero} product-container`} id="ai-lead-recovery">
    <div className={styles.heroCopy}>
      <p className={styles.eyebrow}>AI LEAD RECOVERY</p>
      <h2>Missed calls shouldn’t mean missed revenue.</h2>
      <p>HVACLine automatically follows up with missed callers, unfinished conversations, and abandoned bookings — turning lost opportunities into confirmed appointments.</p>
      <div className={styles.actions}><Link className={`${styles.link} ${styles.primary}`} href="/lead-recovery">Try Live Demo <ProductIcon name="arrow" /></Link><Link className={styles.link} href="/lead-recovery?setup=1">Set Up AI Recovery</Link></div>
      <p className={styles.muted} style={{ marginTop: "1rem" }}>Explore the interactive simulation below. Live automation requires explicit permissions and supported provider setup; it starts disabled.</p>
    </div>
    <RecoveryDemo state={state} dispatch={dispatch} compact />
  </section>;
}
