import Link from "next/link";
import { ProductIcon } from "@/components/product-icons";
import type { ResolvedWebsite } from "../contracts";
import { ContactSection, FaqSection, RenderSections, SiteAction, SiteFooter, SiteHeader, SiteImage, VoiceSection } from "../primitives";
import shared from "../website.module.css";
import styles from "./industrial.module.css";

export function IndustrialWebsite({ site }: { site: ResolvedWebsite }) {
  const configuration = site.configuration;
  const sections = {
    hero: (
      <section id="hero" className={styles.hero}>
        <div className={styles.heroCopy}>
          <p className={shared.eyebrow}><span className={styles.signal} />{configuration.hero.eyebrow}</p>
          <h1>{configuration.hero.title}</h1>
          <p className={styles.lead}>{configuration.hero.description}</p>
          <div className={styles.actions}><SiteAction action={configuration.actions.primary} voice={site.voice} /><SiteAction action={configuration.actions.secondary} voice={site.voice} secondary /></div>
          <p className={styles.heroNote}>Website demo. Review the receptionist section for connection availability.</p>
        </div>
        <figure className={styles.heroVisual}>
          <SiteImage id={configuration.hero.image} priority />
          <figcaption>{configuration.hero.imageCaption}</figcaption>
          <span className={styles.stamp}>SERVICE<br />STARTS HERE ↗</span>
        </figure>
        <div className={styles.workflowStrip}>
          <span><ProductIcon name="chat" />Voice & Text entry</span>
          <span><ProductIcon name="check" />Confirm before booking</span>
          <span><ProductIcon name="shield" />Human attention for hazards</span>
        </div>
      </section>
    ),
    services: (
      <section id="services" className={styles.services}>
        <div className={styles.sectionIntro}><p className={shared.eyebrow}>THE WORK WE HELP START</p><h2>For the everyday.<br />And the unexpected.</h2><p>Example service categories for a heating and cooling business.</p></div>
        <div className={styles.serviceRows}>{configuration.services.map((service, index) => <article key={service.title}><span className={styles.number}>0{index + 1}</span><div><h3>{service.title}</h3><p>{service.description}</p></div><ProductIcon name={(["snow", "heat", "home", "shield"] as const)[index % 4]} /></article>)}</div>
      </section>
    ),
    process: (
      <section id="process" className={styles.process}>
        <div className={styles.processHeading}><p className={shared.eyebrow}>FROM FIRST QUESTION TO NEXT STEP</p><h2>A better start<br />to the service visit.</h2></div>
        <ol>{configuration.process.map((step, index) => <li key={step.title}><span>STEP / 0{index + 1}</span><h3>{step.title}</h3><p>{step.description}</p></li>)}</ol>
      </section>
    ),
    voice: <VoiceSection site={site} />,
    faq: <FaqSection configuration={configuration} />,
    contact: <><ContactSection site={site} /><div className={styles.bookingLink}><Link href="/book">Existing HVACLine booking workspace ↗</Link><span>Business resolution, authentication and availability remain in the existing flow.</span></div></>,
  };
  return <div className={styles.industrial}><SiteHeader site={site} /><main id="demo-content" className={shared.main}><RenderSections order={configuration.sections} sections={sections} /></main><SiteFooter site={site} /></div>;
}
