"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { LoadingSpinner } from "@/components/loading-spinner";
import {
  billingRequest,
  checkoutRedirect,
  draftCatalog,
  hours,
  money,
} from "./contracts";
import type { Billing, Catalog, History, Plan, PlanKey } from "./contracts";
import { PlanCards } from "./pricing";
import styles from "./billing.module.css";

type PendingPurchase = {
  request_id: string;
  plan?: PlanKey;
  hours?: number;
  accepted_amount: number;
  explicit_confirmation: true;
};

export function BillingDashboard({ accountId }: { accountId: string }) {
  const [catalog, setCatalog] = useState<Catalog>(draftCatalog);
  const [billing, setBilling] = useState<Billing>();
  const [history, setHistory] = useState<History>({ topups: [], labor: [] });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [extraHours, setExtraHours] = useState(1);
  const [accepted, setAccepted] = useState(false);
  const [packageAccepted, setPackageAccepted] = useState(false);
  const [pending, setPending] = useState<PendingPurchase>();
  const busyRef = useRef(false);
  const redirecting = useRef(false);
  const storageKey = `hvacline-test-purchase:${accountId}`;
  const remember = (value: PendingPurchase | undefined) => {
    setPending(value);
    try {
      if (value) sessionStorage.setItem(storageKey, JSON.stringify(value));
      else sessionStorage.removeItem(storageKey);
    } catch {
      /* The backend also retains the checkout request. */
    }
  };
  const load = useCallback(async (refresh: boolean) => {
    const [plans, summary, records] = await Promise.all([
      billingRequest<Catalog>("plans"),
      billingRequest<Billing>(
        refresh ? "refresh" : "status",
        refresh ? "POST" : "GET",
        refresh ? {} : undefined,
      ),
      billingRequest<History>("history"),
    ]);

    const latestRecords = refresh
      ? await billingRequest<History>("history")
      : records;
    return { plans, summary, records: latestRecords };
  }, []);
  const refreshBilling = async () => {
    const data = await load(true);
    setCatalog(data.plans);
    setBilling(data.summary);
    setHistory(data.records);
  };
  useEffect(() => {
    const returned = new URLSearchParams(window.location.search);
    const success = ["checkout", "topup"].some(
      (key) => returned.get(key) === "success",
    );
    let active = true;
    void load(success)
      .then(({ plans, summary, records }) => {
        if (!active) return;
        setCatalog(plans);
        setBilling(summary);
        setHistory(records);
        if (success)
          setMessage(
            summary.sync_pending || summary.checkout_pending
              ? "Stripe is still confirming the package. Refresh billing shortly."
              : "Your confirmed package and extra hours are up to date.",
          );
        try {
          const raw = sessionStorage.getItem(storageKey);
          if (raw) {
            const saved: PendingPurchase = JSON.parse(raw);
            const record = records.topups.find(
              (item) => item.id === saved.request_id,
            );
            if (
              (saved.plan &&
                summary.plan !== "none" &&
                !summary.checkout_pending) ||
              (record && ["paid", "expired"].includes(record.status))
            ) {
              sessionStorage.removeItem(storageKey);
              setPending(undefined);
            } else if (
              typeof saved.request_id === "string" &&
              Number.isInteger(saved.accepted_amount) &&
              saved.accepted_amount > 0
            ) {
              setPending(saved);
              if (
                saved.hours &&
                Number.isInteger(saved.hours) &&
                saved.hours >= 1 &&
                saved.hours <= 40
              )
                setExtraHours(saved.hours);
            }
          }
        } catch {
          /* The server retains purchase status when storage is unavailable. */
        }
      })
      .catch((failure: unknown) => {
        if (active)
          setError(
            failure instanceof Error
              ? failure.message
              : "Your package could not be loaded.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [load, storageKey]);

  async function act(name: string, operation: () => Promise<void>) {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(name);
    setError("");
    setMessage("");
    try {
      await operation();
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "This action could not be completed. Retry the same request.",
      );
    } finally {
      if (!redirecting.current) {
        busyRef.current = false;
        setBusy("");
      }
    }
  }
  async function choose(plan: Plan) {
    await act(plan.key, async () => {
      if (!packageAccepted)
        throw new Error("Review and accept the monthly package payment below.");
      if (pending && pending.plan !== plan.key)
        throw new Error(
          "Resolve the previous purchase before choosing another package.",
        );
      const request = pending ?? {
        request_id: crypto.randomUUID(),
        plan: plan.key,
        accepted_amount: plan.amount,
        explicit_confirmation: true as const,
      };
      remember(request);
      const result = await billingRequest<{ url: string }>(
        "checkout",
        "POST",
        request,
      );
      checkoutRedirect(result.url, "checkout");
      redirecting.current = true;
    });
  }
  const plan = catalog.plans.find((item) => item.key === billing?.plan);
  const paid = !!plan;
  const canPurchase = !!billing?.checkout_enabled && !billing.review_required;
  const amount = extraHours * (billing?.hourly_amount ?? 0);
  const pendingTopup = history.topups.find((item) =>
    ["creating", "open"].includes(item.status),
  );
  const date = (value: string) =>
    new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(
      new Date(value),
    );
  return (
    <main className={`${styles.dashboard} product-container`}>
      <div className={styles.sectionTop}>
        <span className={styles.eyebrow}>YOUR HOME CARE ACCOUNT</span>
        <span className={styles.testBadge}>
          <span /> SANDBOX ONLY · NO REAL CHARGES
        </span>
      </div>
      <div className={styles.accountHeading}>
        <div>
          <h1>
            Your comfort.
            <br />
            <span>All accounted for.</span>
          </h1>
          <p>One package. A clear hour balance. More time when you need it.</p>
        </div>
        <button
          className={styles.secondary}
          disabled={loading || !!busy}
          onClick={() =>
            void act("refresh", async () => {
              await refreshBilling();
              setMessage("Your package and payment history are up to date.");
            })
          }
        >
          {busy === "refresh" ? (
            <LoadingSpinner label="Checking Stripe…" />
          ) : (
            "↻ Refresh billing"
          )}
        </button>
      </div>
      <div className={styles.sandboxNote}>
        <strong>This is the full Stripe test experience.</strong>
        <span>
          Use test card 4242 4242 4242 4242, a future expiry and any three-digit
          CVC. Test payments update your demo balances.
        </span>
      </div>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {message && (
        <p className={styles.notice} role="status">
          {message}
        </p>
      )}
      {loading ? (
        <div className={styles.loadingPanel} aria-busy="true">
          <LoadingSpinner label="Loading your package and payment history…" />
          <div className={styles.skeletonGrid}>
            <span />
            <span />
            <span />
          </div>
        </div>
      ) : (
        <>
          {billing && (
            <>
              {(billing.sync_pending || billing.checkout_pending) && (
                <p className={styles.notice}>
                  A package checkout or payment confirmation is pending. Refresh
                  billing or resume the same package checkout before starting
                  another purchase.
                </p>
              )}
              {billing.pending_checkout_id && (
                <button
                  className={styles.secondary}
                  disabled={!!busy}
                  onClick={() =>
                    void act("cancel-package", async () => {
                      await billingRequest(
                        `checkouts/${billing.pending_checkout_id}/cancel`,
                        "POST",
                        {},
                      );
                      if (pending?.plan) remember(undefined);
                      await refreshBilling();
                      setMessage(
                        "The unpaid package checkout was canceled. Choose a package when you are ready.",
                      );
                    })
                  }
                >
                  {busy === "cancel-package" ? (
                    <LoadingSpinner label="Canceling package checkout…" />
                  ) : (
                    "Cancel unpaid package checkout"
                  )}
                </button>
              )}
              {billing.review_required && (
                <p className={styles.error} role="alert">
                  Billing is paused for business review following a refund or
                  payment dispute. Your recorded balances are shown for
                  reference.
                </p>
              )}
              <section
                className={styles.balanceGrid}
                aria-label="Maintenance hours"
              >
                <article className={styles.packageBalance}>
                  <span>YOUR PACKAGE</span>
                  <h2>{plan?.name ?? "Choose your first package"}</h2>
                  <p>
                    {plan
                      ? `${money(plan.amount)} / month`
                      : "Start with 3, 5 or 10 hours of maintenance."}
                  </p>
                  <span className={styles.status}>
                    {billing.subscription_status.replaceAll("_", " ")}
                  </span>
                  {billing.period_end && (
                    <p>
                      {billing.cancel_at_period_end
                        ? "Package ends"
                        : "Next renewal"}
                      : {date(billing.period_end)}
                    </p>
                  )}
                  <button
                    className={styles.darkButton}
                    disabled={!billing.portal_enabled || !!busy}
                    onClick={() =>
                      void act("portal", async () => {
                        const result = await billingRequest<{ url: string }>(
                          "portal",
                          "POST",
                          {},
                        );
                        checkoutRedirect(result.url, "portal");
                        redirecting.current = true;
                      })
                    }
                  >
                    {busy === "portal" ? (
                      <LoadingSpinner label="Opening Stripe portal…" />
                    ) : (
                      "Manage payments & renewal ↗"
                    )}
                  </button>
                </article>
                <article className={styles.balance}>
                  <span>PACKAGE HOURS LEFT</span>
                  <strong>
                    {hours(billing.remaining_package_minutes)}
                    <small> hrs</small>
                  </strong>
                  <p>
                    {hours(billing.used_package_minutes)} used of{" "}
                    {hours(billing.included_minutes)} included this period
                  </p>
                  <progress
                    aria-label="Included maintenance hours used"
                    max={Math.max(1, billing.included_minutes)}
                    value={billing.used_package_minutes}
                  />
                  <small>Resets after each paid monthly renewal.</small>
                </article>
                <article className={styles.balance}>
                  <span>PURCHASED HOURS LEFT</span>
                  <strong>
                    {hours(billing.remaining_purchased_minutes)}
                    <small> hrs</small>
                  </strong>
                  <p>
                    {hours(billing.used_purchased_minutes)} used of{" "}
                    {hours(billing.purchased_minutes)} purchased
                  </p>
                  <div className={styles.creditNote}>
                    Yours until used <span aria-hidden="true">↗</span>
                  </div>
                  <small>
                    Extra hours stay available after the package period.
                  </small>
                </article>
              </section>
            </>
          )}
          {paid && billing && (
            <section
              className={styles.topupPanel}
              aria-labelledby="add-hours-heading"
            >
              <div>
                <span className={styles.eyebrow}>
                  A LITTLE MORE TIME FOR YOUR HOME
                </span>
                <h2 id="add-hours-heading">Add hours. Keep your package.</h2>
                <p>
                  Buy extra technician maintenance time at your {plan.name}{" "}
                  rate. Your monthly package stays the same.
                </p>
                <div className={styles.topupRate}>
                  {money(billing.hourly_amount ?? 0)}
                  <span> / extra hour</span>
                </div>
                <p className={styles.small}>
                  Hours are credited after Stripe confirms payment. Parts and
                  materials are excluded.
                </p>
              </div>
              <form
                className={styles.topupForm}
                onSubmit={(event) => {
                  event.preventDefault();
                  void act("topup", async () => {
                    if (!accepted)
                      throw new Error(
                        "Confirm the extra-hours total before continuing.",
                      );
                    const request = pending ?? {
                      request_id: crypto.randomUUID(),
                      hours: extraHours,
                      accepted_amount: amount,
                      explicit_confirmation: true as const,
                    };
                    if (
                      request.hours !== extraHours ||
                      request.accepted_amount !== amount
                    )
                      throw new Error(
                        "Resolve the pending checkout before changing the hours.",
                      );
                    remember(request);
                    const result = await billingRequest<{ url: string }>(
                      "topup",
                      "POST",
                      request,
                    );
                    checkoutRedirect(result.url, "checkout");
                    redirecting.current = true;
                  });
                }}
              >
                <label htmlFor="additional-hours">
                  Extra maintenance hours
                </label>
                <div className={styles.stepper}>
                  <button
                    type="button"
                    aria-label="Remove one hour"
                    disabled={extraHours <= 1 || !!busy || !!pending}
                    onClick={() => {
                      setExtraHours((value) => value - 1);
                      setAccepted(false);
                    }}
                  >
                    −
                  </button>
                  <input
                    id="additional-hours"
                    type="number"
                    min={1}
                    max={40}
                    step={1}
                    value={extraHours}
                    disabled={!!busy || !!pending}
                    onChange={(event) => {
                      const value = Number(event.target.value);
                      if (
                        Number.isInteger(value) &&
                        value >= 1 &&
                        value <= 40
                      ) {
                        setExtraHours(value);
                        setAccepted(false);
                      }
                    }}
                  />
                  <button
                    type="button"
                    aria-label="Add one hour"
                    disabled={extraHours >= 40 || !!busy || !!pending}
                    onClick={() => {
                      setExtraHours((value) => value + 1);
                      setAccepted(false);
                    }}
                  >
                    +
                  </button>
                </div>
                <div className={styles.totalLine}>
                  <span>Due in this checkout</span>
                  <strong>{money(amount)}</strong>
                </div>
                <label className={styles.consent}>
                  <input
                    type="checkbox"
                    checked={accepted}
                    disabled={!!busy}
                    onChange={(event) => setAccepted(event.target.checked)}
                  />
                  <span>
                    I agree to pay {money(amount)} for {extraHours} extra
                    maintenance {extraHours === 1 ? "hour" : "hours"} in a
                    separate test checkout.
                  </span>
                </label>
                <button
                  className={styles.primary}
                  disabled={!canPurchase || !accepted || !!busy}
                >
                  {busy === "topup" ? (
                    <LoadingSpinner label="Preparing extra-hours checkout…" />
                  ) : (
                    `Add ${extraHours} ${extraHours === 1 ? "hour" : "hours"} · ${money(amount)} →`
                  )}
                </button>
                <small>Hosted by Stripe · Test payment only</small>
              </form>
            </section>
          )}
          {pending && (
            <div className={styles.notice}>
              <p>
                A saved checkout request is ready to resume. Keep it while
                payment is uncertain.
              </p>
              <button
                className={styles.secondary}
                disabled={!!busy}
                onClick={() =>
                  void act("resolve", async () => {
                    await refreshBilling();
                    const latest = await billingRequest<History>("history");
                    const unresolved = latest.topups.some(
                      (item) =>
                        item.id === pending.request_id &&
                        ["creating", "open"].includes(item.status),
                    );
                    const state = await billingRequest<Billing>("status");
                    if (
                      unresolved ||
                      (!pending.hours && state.checkout_pending)
                    )
                      throw new Error(
                        "The checkout is still pending. Resume it or cancel an open extra-hours checkout below.",
                      );
                    remember(undefined);
                    setAccepted(false);
                    setPackageAccepted(false);
                    setMessage(
                      "The saved purchase is resolved. You can deliberately start a new checkout.",
                    );
                  })
                }
              >
                {busy === "resolve" ? (
                  <LoadingSpinner label="Resolving saved purchase…" />
                ) : (
                  "Check saved purchase"
                )}
              </button>
            </div>
          )}
          {!paid && (
            <section aria-labelledby="choose-package">
              <div className={styles.subheading}>
                <div>
                  <span className={styles.eyebrow}>
                    START WITH THE RIGHT AMOUNT OF CARE
                  </span>
                  <h2 id="choose-package">Choose your maintenance package.</h2>
                </div>
                <Link href="/pricing">Compare packages ↗</Link>
              </div>
              {catalog.draft && (
                <p className={styles.notice}>
                  These are editable demonstration rates. Test checkout becomes
                  available when sandbox billing is configured.
                </p>
              )}
              <label className={styles.consent}>
                <input
                  type="checkbox"
                  checked={packageAccepted}
                  disabled={!!busy}
                  onChange={(event) => setPackageAccepted(event.target.checked)}
                />
                <span>
                  I understand the selected package price is collected
                  immediately and renews monthly until canceled. Package hours
                  reset each paid period; extra hours require a separate
                  checkout.
                </span>
              </label>
              <PlanCards
                plans={catalog.plans}
                onChoose={(value) => void choose(value)}
                disabled={!canPurchase || !packageAccepted}
                busy={busy}
              />
            </section>
          )}
          <section className={styles.history} aria-labelledby="payment-history">
            <div className={styles.subheading}>
              <div>
                <span className={styles.eyebrow}>EVERY HOUR HAS A RECORD</span>
                <h2 id="payment-history">Extra-hours payments</h2>
              </div>
              <span>Latest 50 purchases</span>
            </div>
            {history.topups.length ? (
              <div className={styles.tableWrap}>
                <table>
                  <thead>
                    <tr>
                      <th>Purchase</th>
                      <th>Hours</th>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.topups.map((item) => (
                      <tr key={item.id}>
                        <td>
                          {date(item.created_at)}
                          <small>{item.plan} package</small>
                        </td>
                        <td>+{hours(item.minutes)} hrs</td>
                        <td>{money(item.amount)}</td>
                        <td>
                          <span
                            className={
                              item.status === "paid"
                                ? styles.paid
                                : styles.status
                            }
                          >
                            {item.status}
                          </span>
                        </td>
                        <td>
                          {["creating", "open"].includes(item.status) && (
                            <div className={styles.historyActions}>
                              <button
                                disabled={!!busy}
                                onClick={() =>
                                  void act(item.id, async () => {
                                    const request: PendingPurchase = {
                                      request_id: item.id,
                                      hours: item.minutes / 60,
                                      accepted_amount: item.amount,
                                      explicit_confirmation: true,
                                    };
                                    setExtraHours(item.minutes / 60);
                                    remember(request);
                                    const result = await billingRequest<{
                                      url: string;
                                    }>("topup", "POST", request);
                                    checkoutRedirect(result.url, "checkout");
                                    redirecting.current = true;
                                  })
                                }
                              >
                                {busy === item.id ? (
                                  <LoadingSpinner label="Resuming…" />
                                ) : (
                                  `Resume · ${money(item.amount)}`
                                )}
                              </button>
                              {item.status === "open" && (
                                <button
                                  disabled={!!busy}
                                  onClick={() =>
                                    void act(`cancel-${item.id}`, async () => {
                                      await billingRequest(
                                        `topups/${item.id}/cancel`,
                                        "POST",
                                        {},
                                      );
                                      if (pending?.request_id === item.id)
                                        remember(undefined);
                                      await refreshBilling();
                                      setMessage(
                                        "The unpaid extra-hours checkout was canceled.",
                                      );
                                    })
                                  }
                                >
                                  {busy === `cancel-${item.id}` ? (
                                    <LoadingSpinner label="Canceling…" />
                                  ) : (
                                    "Cancel checkout"
                                  )}
                                </button>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className={styles.empty}>
                <span aria-hidden="true">↗</span>
                <h3>More time, when you need it.</h3>
                <p>
                  Your extra-hours purchases will appear here after you start a
                  checkout.
                </p>
              </div>
            )}
          </section>
          <section className={styles.history}>
            <div className={styles.subheading}>
              <div>
                <span className={styles.eyebrow}>
                  TIME SPENT CARING FOR YOUR HOME
                </span>
                <h2>Completed maintenance labor</h2>
              </div>
              <span>Latest 50 visits</span>
            </div>
            {history.labor.length ? (
              <div className={styles.tableWrap}>
                <table>
                  <thead>
                    <tr>
                      <th>Recorded</th>
                      <th>Total time</th>
                      <th>Package used</th>
                      <th>Purchased used</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.labor.map((item) => (
                      <tr key={item.id}>
                        <td>{date(item.created_at)}</td>
                        <td>{hours(item.minutes)} hrs</td>
                        <td>{hours(item.package_minutes)} hrs</td>
                        <td>{hours(item.purchased_minutes)} hrs</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className={styles.empty}>
                Completed labor appears when the business records the
                maintenance visit. A booking alone never consumes hours.
              </p>
            )}
          </section>
          {pendingTopup && !paid && (
            <p className={styles.notice}>
              Your package is inactive, but you can resume or cancel the saved
              extra-hours checkout from its payment record.
            </p>
          )}
        </>
      )}
      <p className={styles.finePrint}>
        Monthly package hours do not roll over. Purchased extra hours remain
        until used and do not renew automatically. Available appointments and
        approved work scope still apply. Payment does not create or confirm an
        appointment. Refunds and disputes require business review. All checkouts
        use Stripe test mode.
      </p>
    </main>
  );
}
