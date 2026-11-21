import type { ResolvedWebsite } from "../contracts";
import {
  ContactSection,
  FaqSection,
  RenderSections,
  SiteAction,
  SiteFooter,
  SiteHeader,
  SiteImage,
  VoiceSection,
} from "../primitives";
import shared from "../website.module.css";
import styles from "./editorial.module.css";

export function EditorialWebsite({ site }: { site: ResolvedWebsite }) {
  const configuration = site.configuration;
  const sections = {
    hero: (
      <section id="hero" className={styles.hero}>
        <div className={styles.heroHeading}>
          <p className={shared.eyebrow}>{configuration.hero.eyebrow}</p>
          <h1>{configuration.hero.title}</h1>
        </div>
        <div className={styles.heroComposition}>
          <figure>
            <SiteImage id={configuration.hero.image} priority />
            <figcaption>{configuration.hero.imageCaption}</figcaption>
          </figure>
          <aside>
            <span className={styles.flourish} aria-hidden="true">
              a&s
            </span>
            <p>{configuration.hero.description}</p>
            <SiteAction
              action={configuration.actions.secondary}
              voice={site.voice}
              secondary
            />
            <span className={styles.marginNote}>
              A fictional advisory.
              <br />A considered first impression.
            </span>
          </aside>
        </div>
      </section>
    ),
    showcase: (
      <section id="showcase" className={styles.collection}>
        <div className={styles.collectionHeading}>
          <p className={shared.eyebrow}>THE ILLUSTRATED COLLECTION</p>
          <h2>
            Distinct spaces.
            <br />
            <em>Individual stories.</em>
          </h2>
          <p>
            Architectural concepts to explore.
            <br />
            No active property listings.
          </p>
        </div>
        <div className={styles.propertyGrid}>
          {configuration.showcase.map((property, index) => (
            <article key={property.title}>
              <div className={styles.propertyImage}>
                <SiteImage
                  id={property.image}
                  sizes="(max-width: 700px) 100vw, 50vw"
                />
                <span>0{index + 1}</span>
              </div>
              <p className={styles.propertyLabel}>{property.label}</p>
              <h3>{property.title}</h3>
              <p>{property.description}</p>
              <a href="#voice">
                Explore an inquiry <span aria-hidden="true">↗</span>
              </a>
            </article>
          ))}
        </div>
      </section>
    ),
    story: (
      <section id="story" className={styles.story}>
        <div className={styles.storyImage}>
          <SiteImage
            id={configuration.story.image}
            sizes="(max-width: 700px) 100vw, 35vw"
          />
        </div>
        <div className={styles.storyCopy}>
          <p className={shared.eyebrow}>{configuration.story.eyebrow}</p>
          <h2>{configuration.story.title}</h2>
          <p>{configuration.story.description}</p>
          <SiteAction
            action={configuration.actions.primary}
            voice={site.voice}
          />
        </div>
      </section>
    ),
    voice: <VoiceSection site={site} />,
    services: (
      <section id="services" className={styles.services}>
        <div>
          <p className={shared.eyebrow}>HERE FOR THE NEXT CHAPTER</p>
          <h2>
            A personal approach,
            <br />
            <em>from the beginning.</em>
          </h2>
        </div>
        <div>
          {configuration.services.map((service, index) => (
            <article key={service.title}>
              <span>0{index + 1}</span>
              <div>
                <h3>{service.title}</h3>
                <p>{service.description}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    ),
    faq: <FaqSection configuration={configuration} />,
    contact: <ContactSection site={site} />,
  };
  return (
    <div className={styles.editorial}>
      <SiteHeader site={site} />
      <main id="demo-content" className={shared.main}>
        <RenderSections order={configuration.sections} sections={sections} />
      </main>
      <SiteFooter site={site} />
    </div>
  );
}
