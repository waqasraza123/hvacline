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
          <Link className="product-login" href="/login">
            Sign in
          </Link>
          <Link className="product-button button-small" href="/book">
            Try the booking demo <ProductIcon name="arrow" />
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
