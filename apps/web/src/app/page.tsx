import Link from "next/link";
import { Suspense } from "react";
import { AccountAvatarPlaceholder } from "@/components/account-avatar";
import { HeaderAccount } from "@/components/header-account";
import { Brand } from "@/components/brand";
import { ProviderLogos, GitHubLink } from "@/components/provider-logos";
import { HeaderNavigation } from "@/components/header-navigation";
import headerStyles from "@/components/header-navigation.module.css";
import { ThemeToggle } from "@/components/theme-toggle";
import { ProductIcon, VoiceSymbol } from "@/components/product-icons";
import { OutboundDemo } from "@/features/outbound-demo/outbound-demo";
import {
  OutboundDemoDialog,
  OutboundDemoTrigger,
} from "@/features/outbound-demo/outbound-demo-dialog";
import { HomepageChat } from "@/features/homepage-chat/homepage-chat";
import { RecoveryHomepage } from "@/features/recovery/homepage";
import "./product.css";
import "@/features/outbound-demo/outbound-demo.css";
import styles from "./homepage.module.css";

export default function Home() {
  return (
    <div className={styles.home}>
      <OutboundDemoDialog>
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <header
          className={`product-header product-container ${headerStyles.header} ${styles.header}`}
        >
          <Brand />
          <HeaderNavigation />
          <div className="product-header-actions">
            <ThemeToggle />
            <Suspense fallback={<AccountAvatarPlaceholder />}>
              <HeaderAccount />
            </Suspense>
            <Link className="product-button button-small" href="/book">
              Try Voice Chat <ProductIcon name="arrow" />
            </Link>
          </div>
        </header>
        <main id="main-content" className="product-main">
          <section className={`product-hero product-container ${styles.hero}`}>
            <div className="hero-copy">
              <p className="product-eyebrow">
                <span /> CUSTOMIZABLE AI VOICE AGENTS
              </p>
              <h1>
                AI voice agents,
                <br />
                <span>built around your business.</span>
              </h1>
              <p className="product-lead">
                Shape your agent’s voice, knowledge, and workflows to answer
                questions, capture enquiries, and support your business.
              </p>
              <div className="product-hero-actions">
                <Link className="product-button" href="/book">
                  <ProductIcon name="mic" /> Try Voice Chat
                </Link>
                <Link className={styles.secondaryAction} href="/operations">
                  Explore the dashboard
                </Link>
              </div>
              <p className="hero-voice-note">
                Try the HVAC example. Sign in, then connect when you’re ready.
              </p>
              <div className="hero-contact-options">
                <OutboundDemoTrigger className="product-text-link">
                  Request a demo call
                </OutboundDemoTrigger>
                <a className="hero-inbound-call" href="tel:+12014097805">
                  <ProductIcon name="phone" />
                  <span>Call Line:</span>
                  <strong>+1 201 409 7805</strong>
                </a>
              </div>
            </div>
            <div className={`hero-chat-composition ${styles.demo}`}>
              <div className={styles.demoFrame}>
                <HomepageChat />
              </div>
              <p className={styles.demoCaption}>
                <ProductIcon name="chat" />
                A conversation is the best introduction.
              </p>
            </div>
            <ul
              className={`hero-trust-badges ${styles.badges}`}
              aria-label="Voice, multilingual, memory, CRM, account and payment features"
            >
              <li className="hero-trust-badge">
                <ProductIcon name="mic" />
                <span>
                  <strong>WebRTC</strong>
                  <small>Real-time voice</small>
                </span>
              </li>
              <li className="hero-trust-badge">
                <ProductIcon name="languages" />
                <span>
                  <strong>Multilingual</strong>
                  <small>Language support · Preview</small>
                </span>
              </li>
              <li className="hero-trust-badge">
                <ProductIcon name="shield" />
                <span>
                  <strong>Google Authenticator</strong>
                  <small>Protected by</small>
                </span>
              </li>
              <li className="hero-trust-badge">
                <ProductIcon name="home" />
                <span>
                  <strong>Persistent Memory</strong>
                  <small>Customer-controlled · Preview</small>
                </span>
              </li>
              <li className="hero-trust-badge">
                <ProductIcon name="chat" />
                <span>
                  <strong>GoHighLevel</strong>
                  <small>CRM sync · Preview</small>
                </span>
              </li>
              <li className="hero-trust-badge">
                <ProductIcon name="lock" />
                <span>
                  <strong className="hero-stripe-wordmark">stripe</strong>
                  <small>Secure payments · Sandbox</small>
                </span>
              </li>
            </ul>
          </section>
          <section
            className={`product-container ${styles.workflow}`}
            aria-labelledby="homepage-workflow-title"
          >
            <div className={styles.workflowHeading}>
              <p className="product-eyebrow">HOW THE HVAC EXAMPLE WORKS</p>
              <h2 id="homepage-workflow-title">
                A conversation.
                <br />
                A clear next step.
              </h2>
            </div>
            <ol className={styles.workflowSteps}>
              <li>
                <span className={styles.workflowIcon}>
                  <ProductIcon name="chat" />
                </span>
                <h3>Start with what you need.</h3>
                <p>Ask a question or describe an HVAC issue in your own words.</p>
              </li>
              <li>
                <span className={styles.workflowIcon}>
                  <ProductIcon name="calendar" />
                </span>
                <h3>Find a time that fits.</h3>
                <p>Share the details and explore available appointment times.</p>
              </li>
              <li>
                <span className={styles.workflowIcon}>
                  <ProductIcon name="check" />
                </span>
                <h3>You make the final call.</h3>
                <p>Review your details and explicitly confirm before booking.</p>
              </li>
            </ol>
          </section>
          <RecoveryHomepage />
          <OutboundDemo />
          <section className={`product-container ${styles.closingSection}`}>
            <div className={`product-final-cta ${styles.closing}`}>
              <div>
                <p className="product-eyebrow">EXPLORE THE HVAC EXAMPLE</p>
                <h2>
                  Experience AI voice
                  <br />
                  <span>in action.</span>
                </h2>
                <p className={styles.closingCopy}>
                  Meet Line. Ask a question. See where the conversation takes you.
                </p>
              </div>
              <Link className="product-button button-light" href="/book">
                <ProductIcon name="mic" /> Try Voice Chat
              </Link>
            </div>
          </section>
        </main>
        <footer
          className={`product-footer product-container ${headerStyles.footer} ${styles.footer}`}
        >
          <div className={`${headerStyles.footerLogos} ${styles.integrations}`}>
            <p className={styles.integrationLabel}>
              Voice &amp; messaging integrations
            </p>
            <ProviderLogos descriptions />
            <GitHubLink description />
          </div>
          <div className={styles.footerBrand}>
            <Brand />
            <p>Customizable AI voice agents for business conversations.</p>
          </div>
          <nav aria-label="Footer navigation">
            <Link href="/login">Sign in</Link>
            <Link href="/signup">Create an account</Link>
          </nav>
        </footer>
        <Link
          href="/book"
          className="voice-launcher"
          aria-label="Try Voice Chat with Line"
        >
          <span className="launcher-mark">
            <VoiceSymbol />
          </span>
          <span>
            Try Voice Chat<small>AI VOICE AGENTS FOR BUSINESS</small>
          </span>
          <ProductIcon name="arrow" />
        </Link>
      </OutboundDemoDialog>
    </div>
  );
}
