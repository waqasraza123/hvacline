import Image from "next/image";
import Link from "next/link";
import { Fragment } from "react";
import type { CSSProperties, ReactNode } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { ProductIcon } from "@/components/product-icons";
import { websiteAsset } from "./assets";
import { WebsiteVoice } from "./website-voice";
import type {
  FontId,
  ResolvedWebsite,
  SectionId,
  VoicePresentation,
  WebsiteAction,
  WebsiteConfiguration,
} from "./contracts";
import styles from "./website.module.css";

const fonts: Record<FontId, string> = {
  system: "Arial, Helvetica, sans-serif",
  industrial: "Impact, 'Arial Narrow', 'Helvetica Neue', sans-serif",
  serif: "Georgia, 'Times New Roman', serif",
  humanist: "'Trebuchet MS', 'Segoe UI', sans-serif",
};

export function WebsiteFrame({
  site,
  children,
}: {
  site: ResolvedWebsite;
  children: ReactNode;
}) {
  const { appearance } = site.configuration;
  const variables: CSSProperties & Record<`--site-${string}`, string> = {
    "--site-light-bg": appearance.light.background,
    "--site-light-surface": appearance.light.surface,
    "--site-light-ink": appearance.light.foreground,
    "--site-light-muted": appearance.light.muted,
    "--site-light-accent": appearance.light.accent,
    "--site-light-accent-ink": appearance.light.accentInk,
    "--site-light-line": appearance.light.border,
    "--site-dark-bg": appearance.dark.background,
    "--site-dark-surface": appearance.dark.surface,
    "--site-dark-ink": appearance.dark.foreground,
    "--site-dark-muted": appearance.dark.muted,
    "--site-dark-accent": appearance.dark.accent,
    "--site-dark-accent-ink": appearance.dark.accentInk,
    "--site-dark-line": appearance.dark.border,
    "--site-heading-font": fonts[appearance.headingFont],
    "--site-body-font": fonts[appearance.bodyFont],
    "--site-space": { compact: "20px", balanced: "28px", airy: "40px" }[
      appearance.spacing
    ],
  };
  return (
    <div
      className={styles.site}
      style={variables}
      data-template={site.template.id}
      data-button={site.template.variants.button}
      data-imagery={site.template.variants.imagery}
    >
      <a className={styles.skipLink} href="#demo-content">
        Skip to website content
      </a>
      <div className={styles.demoBar}>
        <Link href="/">← HVACLine home</Link>
        <span>
          {site.configuration.designStyle}
          <span className={styles.demoTag}>
            {site.configuration.status === "published"
              ? "Voice AI website"
              : "Website preview"}
          </span>
        </span>
        <ThemeToggle />
      </div>
      {children}
    </div>
  );
}

export function SiteHeader({ site }: { site: ResolvedWebsite }) {
  const configuration = site.configuration;
  const logo = websiteAsset(configuration.brand.logo);
  return (
    <header className={styles.header} data-site-header>
      <a href="#hero" className={styles.brand}>
        <Image src={logo.src} width={36} height={36} alt="" />
        <span>{configuration.brand.name}</span>
      </a>
      <nav aria-label={`${configuration.brand.name} navigation`}>
        {configuration.header.navigation.map((link) => (
          <a key={link.section} href={`#${link.section}`}>
            {link.label}
          </a>
        ))}
      </nav>
      <SiteAction action={configuration.actions.primary} voice={site.voice} />
    </header>
  );
}

export function SiteAction({
  action,
  voice,
  secondary = false,
}: {
  action: WebsiteAction;
  voice: VoicePresentation;
  secondary?: boolean;
}) {
  const destination = action.destination;
  const href =
    destination.kind === "section"
      ? `#${destination.section}`
      : destination.kind === "url"
        ? destination.href
        : voice.kind === "existing-hvac-entry"
          ? voice.href
          : "#voice";
  return (
    <Link
      className={secondary ? styles.secondaryAction : styles.action}
      href={href}
    >
      {action.label}
      <ProductIcon name="arrow" />
    </Link>
  );
}

export function SiteImage({
  id,
  className,
  priority = false,
  sizes = "(max-width: 767px) 100vw, 60vw",
}: {
  id: string;
  className?: string;
  priority?: boolean;
  sizes?: string;
}) {
  const asset = websiteAsset(id);
  return (
    <Image
      src={asset.src}
      alt={asset.alt}
      width={asset.width}
      height={asset.height}
      sizes={sizes}
      priority={priority}
      className={className}
    />
  );
}

export function VoiceSection({ site }: { site: ResolvedWebsite }) {
  const { voice, brand } = site.configuration;
  return (
    <section
      id="voice"
      className={styles.voiceSection}
      aria-labelledby="voice-heading"
      data-voice-section
    >
      <div className={styles.voiceCopy}>
        <p className={styles.eyebrow}>A FIRST CONVERSATION</p>
        <h2 id="voice-heading">{voice.title}</h2>
        <p>{voice.description}</p>
        <p
          className={styles.availability}
          data-voice-availability={site.voice.kind}
        >
          {site.voice.notice}
        </p>
        {site.voice.kind === "existing-hvac-entry" && (
          <Link href={site.voice.href} className={styles.action}>
            Open HVACLine workspace
            <ProductIcon name="arrow" />
          </Link>
        )}
      </div>
      {site.voice.kind === "website-session" ? (
        <WebsiteVoice
          slug={site.voice.slug}
          brandName={brand.name}
          leadCapture={site.voice.leadCapture}
        />
      ) : (
        <div className={styles.conversation}>
          <div className={styles.conversationHeader}>
            <ProductIcon name="chat" />
            <span>
              {brand.name}
              <small>Written example · no session is running</small>
            </span>
          </div>
          <ol aria-label="Illustrative conversation, not a live chat">
            {voice.examples.map((example, index) => (
              <li key={index} data-speaker={example.role}>
                <span>
                  {example.role === "visitor" ? "Visitor" : "Example assistant"}
                </span>
                <p>{example.text}</p>
              </li>
            ))}
          </ol>
          <p className={styles.conversationNote}>
            No microphone access. No call or booking is being made.
          </p>
        </div>
      )}
    </section>
  );
}

export function FaqSection({
  configuration,
}: {
  configuration: WebsiteConfiguration;
}) {
  return (
    <section
      id="faq"
      className={styles.faqSection}
      aria-labelledby="faq-heading"
      data-faq-section
    >
      <div>
        <p className={styles.eyebrow}>A FEW USEFUL ANSWERS</p>
        <h2 id="faq-heading">Before you begin.</h2>
      </div>
      <div>
        {configuration.faqs.map((faq) => (
          <details key={faq.question}>
            <summary>
              {faq.question}
              <span aria-hidden="true">+</span>
            </summary>
            <p>{faq.answer}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

export function ContactSection({ site }: { site: ResolvedWebsite }) {
  const { contact } = site.configuration;
  return (
    <section
      id="contact"
      className={styles.contactSection}
      data-contact-section
    >
      <p className={styles.eyebrow}>YOUR NEXT STEP</p>
      <h2>{contact.title}</h2>
      <p>{contact.description}</p>
      <SiteAction
        action={site.configuration.actions.primary}
        voice={site.voice}
      />
      <div className={styles.contactDetails}>
        <span>{contact.location}</span>
        <span>{contact.hours}</span>
        {contact.email && (
          <a href={`mailto:${contact.email}`}>{contact.email}</a>
        )}
        {contact.phone && <a href={`tel:${contact.phone}`}>{contact.phone}</a>}
      </div>
    </section>
  );
}

export function SiteFooter({ site }: { site: ResolvedWebsite }) {
  return (
    <footer className={styles.footer}>
      <strong>{site.configuration.brand.name}</strong>
      <span>
        {site.configuration.status === "published"
          ? "Built with HVACLine"
          : "Illustrative website · built with HVACLine"}
      </span>
      <Link href="/">HVACLine home ↗</Link>
    </footer>
  );
}

export function RenderSections({
  order,
  sections,
}: {
  order: readonly SectionId[];
  sections: Partial<Record<SectionId, ReactNode>>;
}) {
  return order.map((section) => {
    if (sections[section] === undefined)
      throw new Error(`Template cannot render section ${section}`);
    return <Fragment key={section}>{sections[section]}</Fragment>;
  });
}
