import Image from "next/image";
import Link from "next/link";
import { websiteAsset } from "./assets";
import { demoWebsites } from "./catalog";
import styles from "./gallery.module.css";

export function DemoGallery() {
  return (
    <section
      id="voice-demos"
      className={styles.gallery}
      aria-labelledby="voice-demos-heading"
    >
      <div className={styles.heading}>
        <div>
          <p className={styles.eyebrow}>ONE PLATFORM. MANY FRONT DOORS.</p>
          <h2 id="voice-demos-heading">Explore Voice AI Demos</h2>
        </div>
        <p>
          Different businesses. Different first impressions. Explore three ways
          a voice-first website can feel.
        </p>
      </div>
      <div className={styles.grid}>
        {demoWebsites.map((website, index) => {
          const image = websiteAsset(website.hero.image);
          const logo = websiteAsset(website.brand.logo);
          return (
            <Link
              href={`/demos/${website.slug}`}
              key={website.slug}
              className={styles.card}
              aria-labelledby={`demo-${website.slug}-title demo-${website.slug}-action`}
              aria-describedby={`demo-${website.slug}-description`}
            >
              <div
                className={styles.preview}
                data-template={website.templateId}
              >
                <div className={styles.previewHeader}>
                  <Image src={logo.src} width={20} height={20} alt="" />
                  <span>{website.brand.name}</span>
                  <span aria-hidden="true">☰</span>
                </div>
                <div className={styles.previewBody}>
                  <div>
                    <small>{website.hero.eyebrow}</small>
                    <p>{website.hero.title}</p>
                    <span className={styles.previewCta} aria-hidden="true">
                      {website.actions.primary.label} ↗
                    </span>
                  </div>
                  <Image
                    src={image.src}
                    alt={`${website.designStyle} template artwork: ${image.alt}`}
                    width={image.width}
                    height={image.height}
                    sizes="(max-width: 700px) 90vw, (max-width: 1050px) 45vw, 33vw"
                  />
                </div>
              </div>
              <div className={styles.cardContent}>
                <div className={styles.cardEyebrow}>
                  <span>{website.industry}</span>
                  <span>0{index + 1}</span>
                </div>
                <h3 id={`demo-${website.slug}-title`}>{website.brand.name}</h3>
                <p id={`demo-${website.slug}-description`}>{website.summary}</p>
                <div className={styles.cardFooter}>
                  <span>{website.designStyle}</span>
                  <strong id={`demo-${website.slug}-action`}>
                    Explore Demo <span aria-hidden="true">↗</span>
                  </strong>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
      <p className={styles.note}>
        Illustrated template previews. Fictional business content. Connection
        availability is explained within each demo.
      </p>
    </section>
  );
}
