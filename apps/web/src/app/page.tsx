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
import { DemoGallery } from "@/features/websites/demo-gallery";
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
              <a className="product-text-link" href="#how-it-works">
                See how it works <span>↗</span>
              </a>
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
              aria-label="Voice, memory, account and payment features"
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
        <DemoGallery />
        <section id="how-it-works" className="how-section product-container">
          <div className="section-heading">
            <div>
              <p className="product-eyebrow">HOW LINE BOOKS AN APPOINTMENT</p>
              <h2>
                Three steps.
                <br />
                <span>One confirmed appointment.</span>
              </h2>
            </div>
            <p>
              Homeowners describe the problem, choose an available time, and
              confirm. Your team skips the scheduling callbacks.
            </p>
          </div>
          <ol className="booking-journey">
            <li>
              <span className="journey-number">01</span>
              <div className="journey-graphic journey-words">
                <span>“The AC isn’t cooling.”</span>
                <VoiceSymbol />
              </div>
              <h3>Line hears the problem.</h3>
              <p>
                The homeowner explains what’s wrong. Line collects the service
                needed, address, and contact details in a natural conversation.
              </p>
            </li>
            <li>
              <span className="journey-number">02</span>
              <div className="journey-graphic journey-calendar">
                <ProductIcon name="calendar" />
                <span>Live appointment slots</span>
                <span className="calendar-option">
                  Caller chooses <ProductIcon name="check" />
                </span>
              </div>
              <h3>Line offers available times.</h3>
              <p>
                Line checks the business’s schedule and service area, then reads
                out available appointment slots. The homeowner picks a time.
              </p>
            </li>
            <li>
              <span className="journey-number">03</span>
              <div className="journey-graphic journey-confirm">
                <span>
                  <ProductIcon name="check" />
                </span>
                <strong>Details read back.</strong>
                <p>Caller confirms the booking.</p>
              </div>
              <h3>The caller confirms. Line books.</h3>
              <p>
                Line reads back the appointment details and asks for explicit
                confirmation before saving the booking.
              </p>
            </li>
          </ol>
        </section>
        <OutboundDemo />
        <section className="product-faq product-container">
          <div>
            <p className="product-eyebrow">FAQ</p>
            <h2>What HVAC owners need to know.</h2>
          </div>
          <div className="product-faq-list">
            <details>
              <summary>
                How can I try a demo call?<span>+</span>
              </summary>
              <p>
                Choose Request an AI demo call to enter your number, pick a
                scenario and check phone-demo availability. You can also try
                Line’s Voice AI in your browser.
              </p>
            </details>
            <details>
              <summary>
                Who is HVACLine for?<span>+</span>
              </summary>
              <p>
                HVAC businesses losing appointment opportunities to missed calls
                and phone tag. Line handles the booking conversation, from the
                homeowner’s first description to a confirmed appointment.
              </p>
            </details>
            <details>
              <summary>
                Can homeowners speak naturally?<span>+</span>
              </summary>
              <p>
                Yes. Homeowners explain the problem in their own words. Line
                asks for the details needed to schedule the visit and offers
                available appointment times during the conversation.
              </p>
            </details>
            <details>
              <summary>
                Are the appointment times real?<span>+</span>
              </summary>
              <p>
                Yes. Line checks live availability against the business’s
                configured schedule and service area before offering times.
              </p>
            </details>
            <details>
              <summary>
                When does an appointment become a booking?<span>+</span>
              </summary>
              <p>
                After Line reads back the appointment details and the caller
                explicitly confirms. A suggested time or temporary hold is not a
                confirmed booking.
              </p>
            </details>
            <details>
              <summary>
                Can I try the conversation?<span>+</span>
              </summary>
              <p>
                Yes. Ask Line one question here without an account. Sign in to
                continue the conversation, or choose Voice in the booking
                workspace to speak with Line.
              </p>
            </details>
          </div>
        </section>
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
