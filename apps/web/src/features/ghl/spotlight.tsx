"use client";

import { useEffect, useState } from "react";
import { ProductIcon } from "@/components/product-icons";
import { requestApi } from "@/features/operations/api";
import type { IntegrationStatus } from "./contracts";
import styles from "./spotlight.module.css";

type StatusResult =
  | { state: "loading" }
  | { state: "ready"; value: IntegrationStatus }
  | { state: "unavailable" };

function connectionSummary(result: StatusResult, demo: boolean) {
  if (demo)
    return {
      label: "Explore the integration",
      detail:
        "Explore CRM sync, calendar booking and contact summaries, or connect your workspace to set up your own GHL sub-account.",
      tone: "neutral",
      action: "Explore GoHighLevel",
    };
  if (result.state === "loading")
    return {
      label: "Loading connection…",
      detail: "Checking your saved workspace connection.",
      tone: "neutral",
      action: "Open GoHighLevel",
    };
  if (result.state === "unavailable")
    return {
      label: "Status unavailable",
      detail: "Open GoHighLevel to review your connection and try again.",
      tone: "warning",
      action: "Review connection",
    };
  if (!result.value.enabled)
    return {
      label: "Setup required",
      detail:
        "Enable GoHighLevel for this workspace before connecting a sub-account.",
      tone: "neutral",
      action: "View setup",
    };
  const connection = result.value.connection;
  if (!connection || connection.status === "DISCONNECTED")
    return {
      label: "Not connected",
      detail:
        "Connect your GHL sub-account, then choose your pipeline, calendars and contact summary settings.",
      tone: "neutral",
      action: "Connect GoHighLevel",
    };
  if (connection.status === "PAUSED")
    return {
      label: "Connection paused",
      detail:
        "Your connection is paused. Review settings before resuming CRM delivery and GHL booking.",
      tone: "warning",
      action: "Review GoHighLevel",
    };
  if (connection.status === "ERROR" || connection.last_error)
    return {
      label: "Needs attention",
      detail:
        "Review the connection and delivery history to resolve the reported issue.",
      tone: "warning",
      action: "Review GoHighLevel",
    };
  return {
    label: "Connection active",
    detail:
      "Manage your CRM delivery, calendar routing and contact summaries in one place.",
    tone: "success",
    action: "Manage GoHighLevel",
  };
}

export function GhlSetupPreview({
  onConnect,
  onBack,
}: {
  onConnect: () => void;
  onBack: () => void;
}) {
  return (
    <section className={styles.feature} aria-labelledby="ghl-preview-heading">
      <div className={styles.introduction}>
        <div className={styles.brand}>
          <span className={styles.mark} aria-hidden="true">
            GHL
          </span>
          <span>YOUR CONNECTED WORKFLOW</span>
          <span className={styles.preview}>Preview</span>
        </div>
        <h2 id="ghl-preview-heading">From confirmed request to GoHighLevel.</h2>
        <p className={styles.description}>
          Give your team the customer details, appointment and request summary
          in the CRM they already use.
        </p>
        <div className={styles.actions}>
          <button type="button" className={styles.primary} onClick={onConnect}>
            Connect your workspace
            <ProductIcon name="arrow" />
          </button>
          <button type="button" className={styles.secondary} onClick={onBack}>
            Back to overview
          </button>
        </div>
        <p className={styles.caption}>
          This is a feature preview. Connect an administrator workspace to
          configure your GHL sub-account, calendars and contact summaries.
        </p>
      </div>
      <ol className={styles.steps} aria-label="GoHighLevel request workflow">
        <li>
          <span className={styles.icon} aria-hidden="true">
            01
          </span>
          <div>
            <h3>Capture the confirmed request</h3>
            <p>
              Match the contact and create an opportunity with the confirmed
              service details.
            </p>
          </div>
        </li>
        <li>
          <span className={styles.icon} aria-hidden="true">
            02
          </span>
          <div>
            <h3>Book the available appointment</h3>
            <p>
              Use a configured GHL calendar and confirm the caller’s selected
              time.
            </p>
          </div>
        </li>
        <li>
          <span className={styles.icon} aria-hidden="true">
            03
          </span>
          <div>
            <h3>Keep the team informed</h3>
            <p>
              Add the confirmed summary to the contact and keep managed booking
              stages up to date.
            </p>
          </div>
        </li>
      </ol>
    </section>
  );
}

export function GhlSpotlight({
  apiBaseUrl,
  token,
  demo,
  refreshedAt,
  onOpen,
  onConnect,
}: {
  apiBaseUrl: string;
  token: string;
  demo: boolean;
  refreshedAt: number;
  onOpen: () => void;
  onConnect: () => void;
}) {
  const [result, setResult] = useState<StatusResult>({ state: "loading" });
  useEffect(() => {
    if (demo) return;
    let active = true;
    requestApi<IntegrationStatus>(apiBaseUrl, token, "integrations/ghl")
      .then((value) => {
        if (active) setResult({ state: "ready", value });
      })
      .catch(() => {
        if (active) setResult({ state: "unavailable" });
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, token, demo, refreshedAt]);
  const summary = connectionSummary(result, demo);

  return (
    <section className={styles.feature} aria-labelledby="ghl-feature-heading">
      <div className={styles.introduction}>
        <div className={styles.brand}>
          <span className={styles.mark} aria-hidden="true">
            GHL
          </span>
          <span>CRM · VOICE · BOOKING</span>
          <span className={styles.preview}>Preview</span>
        </div>
        <h2 id="ghl-feature-heading">GoHighLevel, from call to booking.</h2>
        <p className={styles.description}>
          Bring confirmed requests into your CRM, book routine appointments on
          GHL calendars, and keep the details with the contact.
        </p>
        <div className={styles.actions}>
          <button type="button" className={styles.primary} onClick={onOpen}>
            {summary.action}
            <ProductIcon name="arrow" />
          </button>
          {demo && (
            <button
              type="button"
              className={styles.secondary}
              onClick={onConnect}
            >
              Connect your workspace
            </button>
          )}
        </div>
        <div className={styles.connection} aria-live="polite">
          <span className={styles.status} data-tone={summary.tone}>
            {summary.label}
          </span>
          <p>{summary.detail}</p>
        </div>
      </div>
      <div className={styles.capabilities} aria-label="GoHighLevel features">
        <div className={styles.capability}>
          <span className={styles.icon}>
            <ProductIcon name="shield" />
          </span>
          <div>
            <h3>Contacts & opportunities</h3>
            <p>Send confirmed leads to the right contact and pipeline stage.</p>
          </div>
        </div>
        <div className={styles.capability}>
          <span className={styles.icon}>
            <ProductIcon name="calendar" />
          </span>
          <div>
            <h3>GHL calendar booking</h3>
            <p>
              Route teams to their calendars and confirm available appointments.
            </p>
          </div>
        </div>
        <div className={styles.capability}>
          <span className={styles.icon}>
            <ProductIcon name="chat" />
          </span>
          <div>
            <h3>Contact summaries</h3>
            <p>Keep confirmed request details on the contact for your team.</p>
          </div>
        </div>
        <p className={styles.caption}>
          {demo
            ? "Explore the demo without signing in. Workspace setup requires administrator access."
            : "Connection status reflects saved settings. Calendar routes and contact summaries are configured separately."}
        </p>
      </div>
    </section>
  );
}
