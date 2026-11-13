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
import "./product.css";
import "@/features/outbound-demo/outbound-demo.css";

export default function Home() {
  return (
    <OutboundDemoDialog>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header
        className={`product-header product-container ${headerStyles.header}`}
      >
        <Brand />
        <HeaderNavigation />
        <div className="product-header-actions">
          <ThemeToggle />
          <ProviderLogos />
          <GitHubLink />
          <Suspense fallback={<AccountAvatarPlaceholder />}>
            <HeaderAccount />
          </Suspense>
          <Link className="product-button button-small" href="/book">
            Try Voice Chat <ProductIcon name="arrow" />
          </Link>
        </div>
      </header>
      <main id="main-content" className="product-main">
        <section className="product-hero product-container">
          <div className="hero-copy">
            <p className="product-eyebrow">
              <span /> AI VOICE RECEPTIONIST FOR HVAC
            </p>
            <h1>
              Stop losing jobs
              <br />
              <span>to missed calls.</span>
            </h1>
            <p className="product-lead">
              Line answers questions, checks available times, and books HVAC
              appointments in one natural conversation.
            </p>
            <div className="product-hero-actions">
              <Link className="product-button" href="/book">
                <ProductIcon name="mic" /> Try Voice Chat
                <ProductIcon name="arrow" />
              </Link>
            </div>
            <p className="hero-voice-note">
              Talk to Line in your browser. Sign in, then connect when you’re
              ready.
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
            <ul
              className="hero-trust-badges"
              aria-label="Voice, memory, CRM, account and payment features"
            >
              <li className="hero-trust-badge">
                <ProductIcon name="mic" />
                <span>
                  <small>Real-time voice</small>
                  <strong>WebRTC</strong>
                </span>
              </li>
              <li className="hero-trust-badge">
                <ProductIcon name="shield" />
                <span>
                  <small>Protected by</small>
                  <strong>Google Authenticator</strong>
                </span>
              </li>
              <li className="hero-trust-badge">
                <ProductIcon name="home" />
                <span>
                  <small>Customer-controlled · Preview</small>
                  <strong>Persistent Memory</strong>
                </span>
              </li>
              <li className="hero-trust-badge">
                <ProductIcon name="chat" />
                <span>
                  <small>CRM sync · Preview</small>
                  <strong>GoHighLevel</strong>
                </span>
              </li>
              <li className="hero-trust-badge">
                <ProductIcon name="lock" />
                <span>
                  <small>Secure payments · Sandbox</small>
                  <strong className="hero-stripe-wordmark">stripe</strong>
                </span>
              </li>
            </ul>
          </div>
          <div className="hero-chat-composition">
            <HomepageChat />
          </div>
        </section>
        <OutboundDemo />
        <section className="product-final-cta product-container">
          <div>
            <p className="product-eyebrow">TRY THE BOOKING CONVERSATION</p>
            <h2>
              Hear Line book
              <br />
              <span>an HVAC appointment.</span>
            </h2>
          </div>
          <Link className="product-button button-light" href="/book">
            Book an appointment <ProductIcon name="arrow" />
          </Link>
        </section>
      </main>
      <footer
        className={`product-footer product-container ${headerStyles.footer}`}
      >
        <div className={headerStyles.footerLogos}>
          <ProviderLogos descriptions />
          <GitHubLink description />
        </div>
        <Brand />
        <p>AI voice receptionist. HVAC appointments booked in conversation.</p>
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
          Try Voice Chat<small>AI VOICE RECEPTIONIST FOR HVAC</small>
        </span>
        <ProductIcon name="arrow" />
      </Link>
    </OutboundDemoDialog>
  );
}
