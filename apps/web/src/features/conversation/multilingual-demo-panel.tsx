"use client";

import Link from "next/link";
import { useReducer } from "react";
import { LANGUAGE_NAMES } from "@insurance-operations/customer-core";
import { DEMO_COPY, initialMultilingualDemo, multilingualDemoReducer, type DemoLanguage } from "./multilingual-demo";
import styles from "./multilingual.module.css";

export function MultilingualDemoPanel({ onSetup }: { onSetup: () => void }) {
  const [state, dispatch] = useReducer(multilingualDemoReducer, undefined, initialMultilingualDemo);
  const action = state.interrupted ? "Repeat complete readback" : { intake: "Read back request", readback: "Confirm fictional request", saved: "Select fictional appointment", held: "Confirm fictional appointment", booked: "Demo completed" }[state.stage];
  return <section className={styles.root} aria-labelledby="multilingual-demo-title">
    <span className={styles.badge}>DEMO DATA · text simulation</span>
    <h2 id="multilingual-demo-title" className={styles.demoTitle}>One conversation. More ways to be understood.</h2>
    <p>Explore multilingual HVAC intake without an account, microphone or provider connection. Every message, language switch and booking below is scripted fictional data. No speech is generated and nothing is sent or saved.</p>
    <div className={styles.controls}>
      <label>Example language<select disabled={state.stage === "booked"} value={state.language} onChange={(event) => dispatch({ type: "language", language: event.target.value as DemoLanguage })}>
        {(Object.keys(DEMO_COPY) as DemoLanguage[]).map((code) => <option key={code} value={code}>{LANGUAGE_NAMES[code]}</option>)}
      </select></label>
      <button type="button" onClick={() => dispatch({ type: "reset" })}>Reset demo</button>
      <button type="button" onClick={onSetup}>Languages &amp; Voice setup</button>
    </div>
    <div className={styles.split}>
      <div className={styles.panel}>
        <h3>Simulated conversation</h3><p className={styles.note}>Active demo language: {LANGUAGE_NAMES[state.language]} · {state.switches} simulated switches</p>
        <p className={styles.note}>Fictional business date: November 24, 2026 · America/New_York. All appointment times are fictional.</p>
        <ol className={styles.turns} aria-live="polite" aria-relevant="additions">
          {state.turns.map((turn, index) => <li key={index} className={styles.turn} data-speaker={turn.speaker}>
            <strong>{turn.speaker === "LINE" ? "Line · simulated" : "Fictional customer"}</strong>
            <p lang={turn.language} dir={turn.language === "ar" ? "rtl" : "auto"}>{turn.text}</p>
          </li>)}
        </ol>
        <button className={styles.primary} type="button" disabled={state.stage === "booked"} onClick={() => dispatch({ type: "advance" })}>{action}</button>
        <div className={styles.controls}>
          <button disabled={state.stage !== "held"} type="button" onClick={() => dispatch({ type: "interrupt" })}>Interrupt confirmation</button>
          <button disabled={!["readback", "held"].includes(state.stage)} type="button" onClick={() => dispatch({ type: "ambiguous" })}>Try ambiguous consent</button>
          <button disabled={state.stage !== "intake"} type="button" onClick={() => dispatch({ type: "mixed" })}>English / Hindi example</button>
          <button disabled={state.stage === "booked"} type="button" onClick={() => dispatch({ type: "background" })}>Background speech example</button>
          <button disabled={state.stage === "booked"} type="button" onClick={() => dispatch({ type: "unsupported" })}>Unsupported language</button>
        </div>
      </div>
      <aside className={styles.panel} aria-label="Preserved fictional booking details">
        <span className={styles.badge}>DEMO DATA</span><h3>Your details stay together.</h3>
        <dl className={styles.details}>
          <div><dt>Name</dt><dd>{state.details.name}</dd></div><div><dt>Address</dt><dd>{state.details.address}</dd></div>
          <div><dt>Service</dt><dd>Air conditioning repair</dd></div><div><dt>Preferred window</dt><dd>{state.details.preferred}</dd></div>
          <div><dt>Original request reference</dt><dd>{state.details.requestId}</dd></div>
          <div><dt>Request state</dt><dd>{["saved", "held", "booked"].includes(state.stage) ? "Saved · simulated" : "Unsaved · awaiting confirmation"}</dd></div>
          <div><dt>Appointment</dt><dd>{state.stage === "booked" ? `${state.details.appointmentId} · confirmed in simulation` : state.stage === "held" ? "Temporarily held · unconfirmed" : "Not reserved"}</dd></div>
        </dl><p className={styles.note}>Switching language preserves the draft and saved request. A new readback in the selected language precedes each relevant confirmation.</p>
        <details><summary>Live voice is configured separately</summary><p>Live languages depend on verified channel and ElevenLabs settings. Browser voice requires sign-in, an available language, disclosure and microphone consent.</p><Link href="/book" prefetch={false}>Open protected browser voice</Link></details>
        <p className={styles.note}>Language examples are illustrative, not evaluated translations. Urdu is excluded from examples of live target support pending complete stack verification.</p>
      </aside>
    </div>
  </section>;
}
