import { ProductIcon } from "@/components/product-icons";
import type { ResolvedWebsite } from "../contracts";
import { ContactSection, FaqSection, RenderSections, SiteAction, SiteFooter, SiteHeader, SiteImage, VoiceSection } from "../primitives";
import shared from "../website.module.css";
import styles from "./calm.module.css";

export function CalmWebsite({ site }: { site: ResolvedWebsite }) {
  const configuration = site.configuration;
  const sections = {
    hero: (
      <section id="hero" className={styles.hero}>
        <div className={styles.heroCopy}><p className={shared.eyebrow}>{configuration.hero.eyebrow}</p><h1>{configuration.hero.title}</h1><p className={styles.lead}>{configuration.hero.description}</p><div className={styles.actions}><SiteAction action={configuration.actions.primary} voice={site.voice} /><SiteAction action={configuration.actions.secondary} voice={site.voice} secondary /></div><p className={styles.heroNote}><ProductIcon name="shield" />A gentle introduction. No microphone or account needed.</p></div>
        <figure className={styles.heroVisual}><SiteImage id={configuration.hero.image} priority /><figcaption>{configuration.hero.imageCaption}</figcaption><a className={styles.welcomeCard} href="#voice"><span className={styles.welcomeIcon}><ProductIcon name="chat" /></span><span><strong>A friendlier first hello.</strong><small>Explore a written welcome ↗</small></span></a></figure>
      </section>
    ),
    services: (
      <section id="services" className={styles.services}>
        <div className={styles.centeredHeading}><p className={shared.eyebrow}>FIND YOUR KIND OF SESSION</p><h2>A little time,<br />well spent.</h2><p>Illustrative ways to meet at our fictional studio.</p></div>
        <div className={styles.sessionCards}>{configuration.services.map((service, index) => <article key={service.title}><span className={styles.sessionIcon}><ProductIcon name={(["chat", "calendar", "sun"] as const)[index % 3]} /></span><h3>{service.title}</h3><p>{service.description}</p><a href="#voice">Explore the front desk<ProductIcon name="arrow" /></a></article>)}</div>
      </section>
    ),
    process: (
      <section id="process" className={styles.process}>
        <div className={styles.processIntro}><p className={shared.eyebrow}>SIMPLE BY DESIGN</p><h2>One small step<br />at a time.</h2><p>You do not need to have it all figured out. A useful first conversation starts with where you are.</p><span aria-hidden="true" className={styles.flower}>✳</span></div>
        <ol>{configuration.process.map((step, index) => <li key={step.title}><span>{index + 1}</span><div><h3>{step.title}</h3><p>{step.description}</p></div></li>)}</ol>
      </section>
    ),
    voice: <VoiceSection site={site} />,
    faq: <FaqSection configuration={configuration} />,
    contact: <ContactSection site={site} />,
  };
  return <div className={styles.calm}><SiteHeader site={site} /><main id="demo-content" className={shared.main}><RenderSections order={configuration.sections} sections={sections} /></main><SiteFooter site={site} /></div>;
}
