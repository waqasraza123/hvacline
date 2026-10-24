import Link from "next/link";
import { Brand } from "@/components/brand";
export default function Home() {
  return (
    <main className="site-shell hvac-home">
      <nav className="top-nav" aria-label="Primary navigation">
        <Brand />
        <div className="nav-links">
          <Link href="/phone-demo">Phone sandbox</Link>
          <Link className="primary-link" href="/operations">
            Open workspace ↗
          </Link>
        </div>
      </nav>
      <section className="hvac-hero">
        <div>
          <p className="eyebrow">THE FRONT DESK FOR HEATING & AIR</p>
          <h1>
            The next job
            <br />
            starts with
            <br />
            <span>a call.</span>
          </h1>
          <p className="summary">
            Keep the conversation moving while your team keeps homes
            comfortable. An AI phone receptionist built around HVAC service
            requests, real scheduling, and human backup.
          </p>
          <div className="hero-actions">
            <Link className="primary-link" href="/operations">
              Your service workspace ↗
            </Link>
            <Link className="secondary-link" href="/phone-demo">
              Explore the phone sandbox
            </Link>
          </div>
          <p className="demo-notice">
            Development preview · fictional data only · live telephone
            validation pending
          </p>
        </div>
        <aside className="hvac-call-card" aria-label="Example HVAC workflow">
          <div className="call-card-top">
            <span>AN EVERYDAY HVAC CALL</span>
            <span className="sample-badge">Example</span>
          </div>
          <p className="call-number">01 / INCOMING</p>
          <h2>
            “The AC stopped.
            <br />
            Can someone come out?”
          </h2>
          <div className="call-wave" aria-hidden="true">
            {[
              14, 28, 42, 24, 56, 34, 64, 36, 50, 22, 44, 60, 30, 48, 18, 32,
              54, 26, 42, 16,
            ].map((height, index) => (
              <i key={index} style={{ height }} />
            ))}
          </div>
          <ol className="call-steps">
            <li>
              <span>01</span>
              <div>
                <strong>Understand the problem</strong>
                <p>Capture the issue, callback number, and service address.</p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <strong>Check the actual schedule</strong>
                <p>Use configured service areas and technician availability.</p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <strong>Give your team a clear next step</strong>
                <p>A confirmed booking or an actionable follow-up request.</p>
              </div>
            </li>
          </ol>
          <p className="call-card-foot">
            No booking is promised before it is saved.
          </p>
        </aside>
      </section>
      <section className="hvac-services" aria-label="HVAC services">
        <span>Air conditioning repair</span>
        <span>Heating repair</span>
        <span>New installations</span>
        <span>Maintenance visits</span>
      </section>
      <section className="workflow-section">
        <p className="eyebrow">A SMALLER GAP BETWEEN A CALL AND A JOB</p>
        <h2>
          Built for the calls
          <br />
          your team cannot get to.
        </h2>
        <div className="capability-grid">
          <article>
            <span>01 / RECEPTION</span>
            <h3>A useful first conversation.</h3>
            <p>
              The receptionist introduces itself as AI, collects service
              details, and answers from approved business information.
            </p>
          </article>
          <article>
            <span>02 / SCHEDULING</span>
            <h3>A slot your team can honor.</h3>
            <p>
              Business hours, ZIP codes, technician calendars, and existing
              reservations determine what can be booked.
            </p>
          </article>
          <article>
            <span>03 / HUMAN BACKUP</span>
            <h3>Urgency reaches a person.</h3>
            <p>
              Hazards and requests that need a technician move to human
              attention. The agent never provides equipment repair instructions.
            </p>
          </article>
        </div>
      </section>
      <footer className="hvac-footer">
        <Brand />
        <p>One front desk. One trade. Every call matters.</p>
        <Link href="/operations">Open workspace ↗</Link>
      </footer>
    </main>
  );
}
