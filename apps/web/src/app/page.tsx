import Link from "next/link";
import { Brand } from "@/components/brand";
import { ProductIcon, VoiceSymbol } from "@/components/product-icons";
import "./product.css";

const services = [
  { icon: "snow", title: "AC repair", text: "Book visits for cooling problems." },
  {
    icon: "heat",
    title: "Heating repair",
    text: "Schedule heating repair visits.",
  },
  { icon: "home", title: "Installation", text: "Book installation consultations." },
  { icon: "shield", title: "Maintenance", text: "Schedule routine HVAC service." },
] as const;

export default function Home() {
  return (
    <div className="product-site">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="product-header product-container">
        <Brand />
        <nav className="product-nav" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#services">Services</a>
        </nav>
        <div className="product-header-actions">
          <div className="product-provider-logos">
            <svg
              role="img"
              aria-label="ElevenLabs"
              width="16"
              height="20"
              viewBox="0 0 16 20"
              fill="currentColor"
            >
              <path d="M2 0h4v20H2zM10 0h4v20h-4z" />
            </svg>
            <svg
              role="img"
              aria-label="Twilio"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <circle
                cx="12"
                cy="12"
                r="10.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
              />
              <circle cx="8.5" cy="8.5" r="2.5" />
              <circle cx="15.5" cy="8.5" r="2.5" />
              <circle cx="8.5" cy="15.5" r="2.5" />
              <circle cx="15.5" cy="15.5" r="2.5" />
            </svg>
            <svg
              role="img"
              aria-label="WhatsApp"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path
                d="M12 2a10 10 0 0 0-8.66 15L2 22l5.13-1.34A10 10 0 1 0 12 2Z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinejoin="round"
              />
              <path d="M8.5 6.8c-.3-.7-.6-.7-.9-.7h-.7c-.3 0-.6.1-.9.4-.3.4-1.2 1.2-1.2 2.8s1.2 3.2 1.4 3.4c.2.2 2.4 3.7 5.8 5 .8.3 1.4.5 1.9.6.8.2 1.5.2 2.1.1.6-.1 1.9-.8 2.2-1.6.3-.8.3-1.5.2-1.6-.1-.2-.3-.3-.7-.4l-2.2-1.1c-.3-.1-.6-.2-.8.2-.2.3-.9 1.1-1.1 1.3-.2.2-.4.3-.7.1-.4-.2-1.5-.5-2.8-1.7-1-.9-1.7-2-1.9-2.4-.2-.3 0-.5.1-.7l.5-.6.3-.6c.1-.2 0-.4 0-.6l-1-2.4Z" />
            </svg>
          </div>
          <a
            className="product-github-link"
            href="https://github.com/waqasraza123/hvacline"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="View HVACLine on GitHub (opens in a new tab)"
            title="GitHub"
          >
            <svg
              aria-hidden="true"
              focusable="false"
              width="20"
              height="20"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.65 7.65 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
            </svg>
          </a>
          <Link className="product-login" href="/login">
            Sign in
          </Link>
          <Link className="product-button button-small" href="/book">
            Try <ProductIcon name="arrow" />
          </Link>
        </div>
      </header>
      <main id="main-content" className="product-main">
        <section className="product-hero product-container">
          <div className="hero-copy">
            <p className="product-eyebrow">
              <span /> AI VOICE RECEPTIONIST FOR HVAC BUSINESSES
            </p>
            <h1>
              Stop losing jobs
              <br />
              <span>to missed calls.</span>
            </h1>
            <p className="product-lead">
              HVACLine is the AI voice receptionist for HVAC businesses. Line
              talks with homeowners, hears the problem, checks live appointment
              slots, and confirms the time they choose.
            </p>
            <div className="product-hero-actions">
              <Link className="product-button" href="/book">
                Try the booking demo <ProductIcon name="arrow" />
              </Link>
              <a className="product-text-link" href="#how-it-works">
                See how it works <span>↗</span>
              </a>
            </div>
            <div className="hero-benefits">
              <span>
                <ProductIcon name="check" /> Live appointment availability
              </span>
              <span>
                <ProductIcon name="check" /> Every booking confirmed by the caller
              </span>
            </div>
          </div>
          <div className="hero-voice-composition">
            <div className="composition-label">
              <ProductIcon name="mic" /> LIVE CONVERSATION. CONFIRMED BOOKING.
            </div>
            <article
              className="line-introduction"
              aria-labelledby="line-introduction-title"
            >
              <div className="line-card-header">
                <span className="line-name">
                  Meet Line<span>YOUR AI VOICE RECEPTIONIST</span>
                </span>
                <span className="voice-ai-badge">Voice AI</span>
              </div>
              <div className="voice-orbit">
                <div className="voice-orbit-inner">
                  <VoiceSymbol />
                </div>
                <span className="orbit-accent" />
              </div>
              <h2 id="line-introduction-title">
                From problem
                <br />
                to appointment.
              </h2>
              <p>
                Line collects the details, offers available times, and asks the
                caller to confirm.
              </p>
              <Link className="line-card-action" href="/book">
                <ProductIcon name="mic" /> Try a booking conversation{" "}
                <ProductIcon name="arrow" />
              </Link>
              <p className="line-card-note">
                Sign in, then choose Voice to try the demo.
              </p>
            </article>
            <div className="booking-promise">
              <span className="promise-icon">
                <ProductIcon name="calendar" />
              </span>
              <div>
                <strong>Caller-confirmed appointments.</strong>
                <span>Line asks for confirmation before booking.</span>
              </div>
              <ProductIcon name="check" />
            </div>
            <span className="composition-caption">
              PROBLEM. AVAILABLE TIME. CONFIRMATION.
            </span>
          </div>
        </section>
        <section id="how-it-works" className="how-section product-container">
          <div className="section-heading">
            <div>
              <p className="product-eyebrow">
                HOW LINE BOOKS AN APPOINTMENT
              </p>
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
        <section
          id="services"
          className="service-strip product-container"
          aria-label="HVAC appointments Line can book"
        >
          {services.map((service) => (
            <article key={service.title}>
              <span className="service-icon">
                <ProductIcon name={service.icon} />
              </span>
              <div>
                <h2>{service.title}</h2>
                <p>{service.text}</p>
              </div>
            </article>
          ))}
        </section>
        <section className="product-faq product-container">
          <div>
            <p className="product-eyebrow">FAQ</p>
            <h2>What HVAC owners need to know.</h2>
          </div>
          <div className="product-faq-list">
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
                Yes. Open the booking demo, sign in, and choose Voice to speak
                with Line through your browser’s microphone.
              </p>
            </details>
          </div>
        </section>
        <section className="product-final-cta product-container">
          <div>
            <p className="product-eyebrow">
              TRY THE BOOKING CONVERSATION
            </p>
            <h2>
              Hear Line book
              <br />
              <span>an HVAC appointment.</span>
            </h2>
          </div>
          <Link className="product-button button-light" href="/book">
            Try the booking demo <ProductIcon name="arrow" />
          </Link>
        </section>
      </main>
      <footer className="product-footer product-container">
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
        aria-label="Try the HVACLine AI voice receptionist booking demo"
      >
        <span className="launcher-mark">
          <VoiceSymbol />
        </span>
        <span>
          Try Line<small>AI VOICE RECEPTIONIST FOR HVAC</small>
        </span>
        <ProductIcon name="arrow" />
      </Link>
    </div>
  );
}
