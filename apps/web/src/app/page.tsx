import Link from "next/link";
import { Brand } from "@/components/brand";
import { ProductIcon, VoiceSymbol } from "@/components/product-icons";
import {
  HomepageChat,
  HomepageChatLink,
} from "@/features/homepage-chat/homepage-chat";
import "./product.css";

const services = [
  {
    icon: "snow",
    title: "AC repair",
    text: "Book visits for cooling problems.",
  },
  {
    icon: "heat",
    title: "Heating repair",
    text: "Schedule heating repair visits.",
  },
  {
    icon: "home",
    title: "Installation",
    text: "Book installation consultations.",
  },
  {
    icon: "shield",
    title: "Maintenance",
    text: "Schedule routine HVAC service.",
  },
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
              aria-label="Telnyx"
              width="20"
              height="20"
              viewBox="0 0 64 57"
              fill="currentColor"
            >
              <path d="M62.8955 52.5465C63.9678 50.6227 64.273 48.3736 63.7513 46.2396C63.6018 45.6498 63.3951 45.0755 63.134 44.5246C63.0515 44.3439 62.9578 44.1684 62.8534 43.9991L54.3508 28.1628H45.6519L54.5473 44.7598C54.8266 45.2421 54.9734 45.788 54.9734 46.3434C54.9734 46.8988 54.8266 47.4446 54.5473 47.927C54.2752 48.3777 53.8891 48.751 53.4267 49.0104C52.9643 49.2698 52.4415 49.4064 51.9095 49.4069H41.7654C41.6531 50.952 41.1664 52.448 40.3461 53.7692C39.5258 55.0905 38.3958 56.1984 37.0511 57H55.6978C56.9426 56.9184 58.1543 56.569 59.2475 55.9765C60.7904 55.2273 62.0635 54.0303 62.8955 52.5465Z" />
              <path d="M15.2053 17.8037H23.9042L28.2397 9.85101C28.6065 9.16466 29.1564 8.59008 29.8302 8.18926C30.504 7.78844 31.2761 7.5766 32.063 7.5766C32.85 7.5766 33.622 7.78844 34.2958 8.18926C34.9696 8.59008 35.5196 9.16466 35.8864 9.85101L40.0955 17.8037H48.7945L42.6211 6.2965C41.5975 4.39527 40.068 2.80466 38.1968 1.69537C36.3257 0.586089 34.1834 0 31.9999 0C29.8164 0 27.6741 0.586089 25.8029 1.69537C23.9318 2.80466 22.4023 4.39527 21.3787 6.2965L15.2053 17.8037Z" />
              <path d="M22.2207 26.7799C22.3119 25.2411 22.7794 23.7469 23.5832 22.4247C24.3869 21.1026 25.5032 19.9916 26.8368 19.1868H10.0001V26.7799H22.2207Z" />
              <path d="M23.6093 27.3331V48.0792H27.5659C28.3911 48.0701 29.1905 47.7947 29.8417 47.2951C30.493 46.7955 30.9602 46.0993 31.1718 45.3131C31.2569 45.0114 31.2994 44.6996 31.2981 44.3864V31.9387C31.3017 30.5874 31.846 29.292 32.8127 28.3339C33.7794 27.3758 35.0905 26.8323 36.4613 26.8213H54.0697V19.1868H31.8593C29.67 19.1904 27.5716 20.0503 26.0248 21.5777C24.478 23.105 23.6093 25.1749 23.6093 27.3331Z" />
              <path d="M0.865818 44.5248C0.604767 45.0756 0.398034 45.65 0.248471 46.2398C-0.272743 48.3783 0.0323602 50.6315 1.10434 52.5605C1.93859 54.0392 3.21144 55.2311 4.75229 55.9766C5.84555 56.5692 7.05718 56.9185 8.30203 57.0001H31.9997C34.2324 57.0001 36.3736 56.1258 37.9524 54.5696C39.5311 53.0133 40.4181 50.9026 40.4181 48.7017V28.1492H36.4053C35.4188 28.1743 34.4809 28.5764 33.7897 29.2707C33.0985 29.965 32.7082 30.8969 32.7012 31.8696V44.3173C32.6975 45.6685 32.1504 46.963 31.1799 47.9171C30.2094 48.8713 28.8946 49.407 27.524 49.407H12.1604C11.6284 49.4066 11.1057 49.27 10.6433 49.0105C10.1809 48.7511 9.79478 48.3778 9.5227 47.9271C9.24352 47.4422 9.09676 46.8942 9.09676 46.3366C9.09676 45.779 9.24352 45.231 9.5227 44.7461L18.4181 28.1492H9.64897L1.14643 43.9854C1.04822 44.179 0.950001 44.345 0.865818 44.5248Z" />
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
          <HomepageChatLink className="product-button button-small">
            Try Line <ProductIcon name="arrow" />
          </HomepageChatLink>
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
              <a className="product-text-link" href="#how-it-works">
                See how it works <span>↗</span>
              </a>
            </div>
          </div>
          <div className="hero-chat-composition">
            <HomepageChat />
          </div>
        </section>
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
      <footer className="product-footer product-container">
        <Brand />
        <p>AI voice receptionist. HVAC appointments booked in conversation.</p>
        <nav aria-label="Footer navigation">
          <Link href="/login">Sign in</Link>
          <Link href="/signup">Create an account</Link>
        </nav>
      </footer>
      <HomepageChatLink
        className="voice-launcher"
        label="Try Line’s voice AI on this page"
      >
        <span className="launcher-mark">
          <VoiceSymbol />
        </span>
        <span>
          Try Line<small>AI VOICE RECEPTIONIST FOR HVAC</small>
        </span>
        <ProductIcon name="arrow" />
      </HomepageChatLink>
    </div>
  );
}
