"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LoadingSpinner } from "@/components/loading-spinner";
import { billingRequest, draftCatalog, money } from "./contracts";
import type { Catalog, Plan } from "./contracts";
import styles from "./billing.module.css";

export function PlanCards({
  plans,
  onChoose,
  busy,
  disabled = false,
}: {
  plans: Plan[];
  onChoose?: (plan: Plan) => void;
  busy?: string;
  disabled?: boolean;
}) {
  return (
    <div className={styles.plans}>
      {plans.map((plan, index) => (
        <article
          className={`${styles.plan} ${index === 1 ? styles.featured : ""}`}
          key={plan.key}
        >
          {index === 1 && (
            <span className={styles.planBadge}>
              A little more peace of mind
            </span>
          )}
          <span className={styles.planNumber}>0{index + 1} / HOME CARE</span>
          <h2>{plan.name}</h2>
          <p className={styles.description}>{plan.description}</p>
          <p className={styles.price}>
            {money(plan.amount)}
            <span>/ month</span>
          </p>
          <p className={styles.hourLine}>
            <strong>{plan.included_hours} hours</strong> of technician
            maintenance
          </p>
          <div className={styles.extraRate}>
            <span>Need more time?</span>
            <strong>
              {money(plan.hourly_amount)}
              <small> / extra hour</small>
            </strong>
          </div>
          <ul className={styles.features}>
            <li>Package hours available after payment</li>
            <li>Add extra hours whenever you need them</li>
            <li>Separate checkout for each add-on</li>
            <li>Clear balance and service history</li>
          </ul>
          {onChoose ? (
            <button
              className={styles.primary}
              disabled={disabled || !!busy}
              onClick={() => onChoose(plan)}
            >
              {busy === plan.key ? (
                <LoadingSpinner label="Opening test checkout…" />
              ) : (
                `Choose ${plan.name} →`
              )}
            </button>
          ) : (
            <Link className={styles.primary} href="/billing">
              Explore {plan.name} <span aria-hidden="true">↗</span>
            </Link>
          )}
          <small className={styles.cardFoot}>
            Monthly package. Cancel future renewals in your portal.
          </small>
        </article>
      ))}
    </div>
  );
}

export function Pricing({ compact = false }: { compact?: boolean }) {
  const [catalog, setCatalog] = useState(draftCatalog);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);
  const [selected, setSelected] = useState("comfort");
  const [extra, setExtra] = useState(2);
  useEffect(() => {
    let active = true;
    void billingRequest<Catalog>("plans")
      .then((value) => {
        if (active) setCatalog(value);
      })
      .catch(() => {
        if (active) setUnavailable(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  const plan =
    catalog.plans.find((item) => item.key === selected) ?? catalog.plans[0];
  return (
    <section
      className={styles.pricing}
      id="maintenance-packages"
      aria-labelledby="pricing-title"
    >
      <div className={styles.sectionTop}>
        <span className={styles.eyebrow}>
          LESS GUESSWORK. MORE HOME COMFORT.
        </span>
        <span className={styles.testBadge}>
          <span /> STRIPE SANDBOX
        </span>
      </div>
      <div className={styles.pricingHeading}>
        <h1 id="pricing-title">
          Your home, cared for.
          <br />
          <span>Your hours, clear.</span>
        </h1>
        <p>
          Start with a maintenance package. Add technician hours when you need
          them. See the price before every payment.
        </p>
      </div>
      <div className={styles.notice}>
        {loading ? (
          <LoadingSpinner label="Loading package pricing…" />
        ) : unavailable ? (
          "Preview pricing — live package details are temporarily unavailable."
        ) : catalog.draft ? (
          "Draft demonstration rates — configure sandbox billing to try checkout."
        ) : (
          "Try the full payment experience with Stripe test cards. No real money is collected."
        )}
      </div>
      <PlanCards plans={catalog.plans} />
      {!compact && plan && (
        <div className={styles.calculator}>
          <div>
            <p className={styles.eyebrow}>DO THE MATH BEFORE YOU BOOK</p>
            <h2>
              A few more hours.
              <br />A clear extra price.
            </h2>
            <p>
              Keep your existing package. Purchase extra maintenance hours in a
              separate checkout at your package’s rate.
            </p>
            <label htmlFor="estimate-package">Your package</label>
            <select
              id="estimate-package"
              value={selected}
              onChange={(event) => setSelected(event.target.value)}
            >
              {catalog.plans.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.name} · {item.included_hours} hours / month
                </option>
              ))}
            </select>
            <label htmlFor="estimate-hours">
              Extra hours{" "}
              <strong>
                {extra} {extra === 1 ? "hour" : "hours"}
              </strong>
            </label>
            <input
              id="estimate-hours"
              type="range"
              min={1}
              max={20}
              value={extra}
              onChange={(event) => setExtra(Number(event.target.value))}
            />
          </div>
          <div className={styles.estimate} aria-live="polite">
            <span>YOUR PAYMENT BREAKDOWN</span>
            <div>
              <span>Initial {plan.name} package</span>
              <strong>{money(plan.amount)} / month</strong>
            </div>
            <div>
              <span>
                {extra} extra hours × {money(plan.hourly_amount)}
              </span>
              <strong>{money(extra * plan.hourly_amount)}</strong>
            </div>
            <div className={styles.estimateTotal}>
              <span>Separate add-hours payment</span>
              <strong>{money(extra * plan.hourly_amount)}</strong>
            </div>
            <p>
              The package is charged upfront. Extra hours are charged only when
              you choose to buy them. This calculator is illustrative.
            </p>
            <Link className={styles.primary} href="/billing">
              View my package <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      )}
      <div className={styles.promiseRow}>
        <div>
          <strong>01 / Choose your hours</strong>
          <p>A fixed package of maintenance labor each month.</p>
        </div>
        <div>
          <strong>02 / Pay with Stripe</strong>
          <p>Hosted checkout, payment methods and invoice history.</p>
        </div>
        <div>
          <strong>03 / Add time as needed</strong>
          <p>A separate payment. An updated balance. You stay in control.</p>
        </div>
      </div>
      <p className={styles.finePrint}>
        Packages cover technician maintenance labor. Parts, materials,
        installations and other work require a separate agreement. Appointments
        depend on service area and availability. Monthly package hours reset
        each paid billing period; unused package hours do not roll over.
        Purchased extra hours remain available until used. All website checkouts
        are sandbox/test only.
      </p>
    </section>
  );
}
