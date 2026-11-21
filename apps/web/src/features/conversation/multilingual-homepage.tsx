import Link from "next/link";
import styles from "./multilingual.module.css";

export function MultilingualHomepage() {
  return <section className={`${styles.root} ${styles.homepage} product-container`} aria-labelledby="multilingual-homepage-title">
    <div className={styles.teaser}><div><p className="product-eyebrow">MULTILINGUAL AI VOICE · PREVIEW</p>
      <h2 id="multilingual-homepage-title">Your customers speak different languages. Your AI can too.</h2>
      <p>Let customers speak naturally in their preferred language, while your AI receptionist handles enquiries, appointments, and follow-ups.</p>
      <p className={styles.note}>Explore a fictional simulation. Live language and channel availability require provider setup.</p>
    </div><Link className={styles.primary} href="/multilingual-ai-voice">Try Multilingual Demo</Link></div>
  </section>;
}
