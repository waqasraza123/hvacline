import Link from "next/link";
import { Brand } from "@/components/brand";
import { ProductIcon, VoiceSymbol } from "@/components/product-icons";
import "./product.css";

const services = [
  { icon: "snow", title: "AC repair", text: "Bring the cool back." },
  { icon: "heat", title: "Heating repair", text: "Get comfortable again." },
  { icon: "home", title: "Installation", text: "Make room for better." },
  { icon: "shield", title: "Maintenance", text: "Stay a step ahead." },
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
            Book an appointment <ProductIcon name="arrow" />
          </Link>
        </div>
      </header>
      <main id="main-content" className="product-main">
        <section className="product-hero product-container">
          <div className="hero-copy">
            <p className="product-eyebrow">
              <span /> HEATING. COOLING. HANDLED.
            </p>
            <h1>
              Less waiting.
              <br />
              <span>More comfort.</span>
            </h1>
            <p className="product-lead">
              Your home needs attention. Getting help shouldn’t be another job.
              Tell Line what you need and book your HVAC appointment in one
              conversation.
            </p>
            <div className="product-hero-actions">
              <Link className="product-button" href="/book">
                Book your appointment <ProductIcon name="arrow" />
              </Link>
              <a className="product-text-link" href="#how-it-works">
                See how it works <span>↗</span>
              </a>
            </div>
            <div className="hero-benefits">
              <span>
                <ProductIcon name="check" /> Skip the phone tag
              </span>
              <span>
                <ProductIcon name="check" /> Choose a time that fits
              </span>
            </div>
          </div>
          <div className="hero-voice-composition">
            <div className="composition-label">
              <span className="voice-spark">✳</span> A LITTLE LESS
              BACK-AND-FORTH.
            </div>
            <article
              className="line-introduction"
              aria-labelledby="line-introduction-title"
            >
              <div className="line-card-header">
                <span className="line-name">
                  Meet Line<span>YOUR AI BOOKING ASSISTANT</span>
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
                A familiar way
                <br />
                to get things sorted.
              </h2>
              <p>
                Just tell us what’s going on.
                <br />
                Line takes it from there.
              </p>
              <Link className="line-card-action" href="/book">
                <ProductIcon name="mic" /> Let’s talk about your home{" "}
                <ProductIcon name="arrow" />
              </Link>
              <p className="line-card-note">
                Sign in to start your conversation.
              </p>
            </article>
            <div className="booking-promise">
              <span className="promise-icon">
                <ProductIcon name="calendar" />
              </span>
              <div>
                <strong>Your time. Your say.</strong>
                <span>Nothing is booked until you confirm.</span>
              </div>
              <ProductIcon name="check" />
            </div>
            <span className="composition-caption">
              LESS HOLD MUSIC. MORE PEACE OF MIND.
            </span>
          </div>
        </section>
        <section
          id="services"
          className="service-strip product-container"
          aria-label="Find the right HVAC service"
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
        <section id="how-it-works" className="how-section product-container">
          <div className="section-heading">
            <div>
              <p className="product-eyebrow">
                FROM “SOMETHING’S WRONG” TO SORTED.
              </p>
              <h2>
                Say it. Pick a time.
                <br />
                <span>Get on with your day.</span>
              </h2>
            </div>
            <p>
              No long forms. No waiting for someone to call you back just to
              find a time.
            </p>
          </div>
          <ol className="booking-journey">
            <li>
              <span className="journey-number">01</span>
              <div className="journey-graphic journey-words">
                <span>“The AC isn’t cooling.”</span>
                <VoiceSymbol />
              </div>
              <h3>Tell Line what you need.</h3>
              <p>
                A quick conversation covers the problem, your address, and the
                best way to reach you.
              </p>
            </li>
            <li>
              <span className="journey-number">02</span>
              <div className="journey-graphic journey-calendar">
                <ProductIcon name="calendar" />
                <span>A time that works for you</span>
                <span className="calendar-option">
                  Your choice <ProductIcon name="check" />
                </span>
              </div>
              <h3>Find your time.</h3>
              <p>
                Hear the available appointments and choose the one that works
                for your schedule.
              </p>
            </li>
            <li>
              <span className="journey-number">03</span>
              <div className="journey-graphic journey-confirm">
                <span>
                  <ProductIcon name="check" />
                </span>
                <strong>You’re in control.</strong>
                <p>Confirm when you’re ready.</p>
              </div>
              <h3>Confirm. Consider it handled.</h3>
              <p>
                Review the details, give your go-ahead, and keep your
                appointment in one place.
              </p>
            </li>
          </ol>
        </section>
        <section className="voice-feature-section">
          <div className="product-container voice-feature-inner">
            <div className="voice-feature-art" aria-hidden="true">
              <span className="feature-ring ring-one" />
              <span className="feature-ring ring-two" />
              <div className="feature-orb">
                <VoiceSymbol />
              </div>
              <span className="feature-art-label">
                A CONVERSATION, NOT A CHORE.
              </span>
            </div>
            <div>
              <p className="product-eyebrow">MEET YOUR NEW FIRST CALL.</p>
              <h2>
                Real conversation.
                <br />
                <span>A clear next step.</span>
              </h2>
              <p>
                Line is your AI booking assistant. It listens, helps you choose
                your service, and finds a time—without the back-and-forth.
              </p>
              <Link className="product-button" href="/signup">
                Find your next appointment <ProductIcon name="arrow" />
              </Link>
            </div>
          </div>
        </section>
        <section className="product-faq product-container">
          <div>
            <p className="product-eyebrow">A FEW THINGS, CLEARED UP.</p>
            <h2>
              Good questions.
              <br />
              Simple answers.
            </h2>
          </div>
          <div className="product-faq-list">
            <details>
              <summary>
                Do I need to make a phone call?<span>+</span>
              </summary>
              <p>
                No. Sign in and talk to Line right here on the website using
                your microphone.
              </p>
            </details>
            <details>
              <summary>
                When is my appointment booked?<span>+</span>
              </summary>
              <p>
                After you choose an available time and explicitly confirm the
                appointment. A suggested time or temporary hold is not a
                booking.
              </p>
            </details>
            <details>
              <summary>
                What can Line help me book?<span>+</span>
              </summary>
              <p>
                Air conditioning repair, heating repair, installations, and
                maintenance. Available appointments depend on your service area
                and the business’s schedule.
              </p>
            </details>
          </div>
        </section>
        <section className="product-final-cta product-container">
          <div>
            <p className="product-eyebrow">
              LET’S GET YOUR HOME BACK TO COMFORTABLE.
            </p>
            <h2>
              Your next appointment.
              <br />
              <span>Just a conversation away.</span>
            </h2>
          </div>
          <Link className="product-button button-light" href="/book">
            Book your appointment <ProductIcon name="arrow" />
          </Link>
        </section>
      </main>
      <footer className="product-footer product-container">
        <Brand />
        <p>Good service starts with a better conversation.</p>
        <nav aria-label="Footer navigation">
          <Link href="/login">Sign in</Link>
          <Link href="/signup">Create an account</Link>
        </nav>
      </footer>
      <Link
        href="/book"
        className="voice-launcher"
        aria-label="Book an appointment with Line, your AI voice assistant"
      >
        <span className="launcher-mark">
          <VoiceSymbol />
        </span>
        <span>
          Book with Line<small>YOUR AI BOOKING ASSISTANT</small>
        </span>
        <ProductIcon name="arrow" />
      </Link>
    </div>
  );
}
