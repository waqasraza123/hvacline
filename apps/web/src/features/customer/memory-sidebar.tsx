"use client";

import { useState } from "react";
import { ProductIcon } from "@/components/product-icons";
import type { MemoryView } from "./memory-model";
import type { MemoryAction } from "./memory-action-dialog";
import styles from "./memory.module.css";

export function MemorySidebar({
  view,
  busy,
  mutate,
  onAction,
}: {
  view: MemoryView;
  busy: boolean;
  mutate: (
    path: string,
    fields?: Record<string, unknown>,
    notice?: string,
  ) => Promise<void>;
  onAction: (action: MemoryAction) => void;
}) {
  const [code, setCode] = useState("");
  const [linkApproved, setLinkApproved] = useState(false);
  return (
    <aside
      className={styles.sidebar}
      aria-label="Memory connections and privacy"
    >
      <section
        className={styles.card}
        aria-labelledby="memory-whatsapp-heading"
      >
        <div className={styles.sectionHeading}>
          <span className={styles.icon}>
            <ProductIcon name="chat" />
          </span>
          <span className={styles.smallStatus}>
            {view.whatsapp_linked ? "Connected" : "Not connected"}
          </span>
        </div>
        <h3 id="memory-whatsapp-heading">Take the context with you.</h3>
        <p>
          Connect a WhatsApp caller you trust to use this account’s optional
          memory during voice calls.
        </p>
        {view.enabled ? (
          <>
            {!view.whatsapp_linked && (
              <ol className={styles.linkSteps}>
                <li>Start a consented WhatsApp voice call.</li>
                <li>Ask Line for an account-linking code.</li>
                <li>Enter it here and approve that caller.</li>
              </ol>
            )}
            <form
              className={styles.editor}
              onSubmit={(event) => {
                event.preventDefault();
                if (linkApproved && /^HVACMEM-[A-Za-z0-9_-]{32}$/.test(code))
                  void mutate(
                    "whatsapp/link",
                    { code, explicit_confirmation: true },
                    "The WhatsApp caller is now connected.",
                  );
              }}
            >
              <label>
                Call linking code
                <input
                  value={code}
                  autoComplete="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  maxLength={40}
                  placeholder="HVACMEM-…"
                  disabled={busy || !view.available}
                  onChange={(event) => {
                    setCode(event.target.value);
                    setLinkApproved(false);
                  }}
                />
              </label>
              <label className={styles.checkbox}>
                <input
                  type="checkbox"
                  checked={linkApproved}
                  disabled={busy || !view.available}
                  onChange={(event) => setLinkApproved(event.target.checked)}
                />
                <span>
                  I approve this WhatsApp caller accessing my optional memory
                  and historical references.
                </span>
              </label>
              <button
                type="submit"
                className={styles.secondary}
                disabled={
                  busy ||
                  !linkApproved ||
                  !view.available ||
                  !/^HVACMEM-[A-Za-z0-9_-]{32}$/.test(code)
                }
              >
                Approve & connect caller
              </button>
            </form>
          </>
        ) : (
          <p className={styles.help}>
            Enable optional memory first to connect a caller. Booking works
            without a connection.
          </p>
        )}
        {view.whatsapp_linked && (
          <button
            type="button"
            className={styles.textButton}
            disabled={busy}
            onClick={() =>
              onAction({
                title: "Disconnect WhatsApp?",
                description:
                  "The linked caller will no longer be able to retrieve this account’s optional memory. Your saved details stay here.",
                label: "Disconnect caller",
                path: "whatsapp/unlink",
              })
            }
          >
            Disconnect WhatsApp
          </button>
        )}
      </section>

      <section
        className={`${styles.card} ${styles.privacy}`}
        aria-labelledby="memory-privacy-heading"
      >
        <span className={styles.icon}>
          <ProductIcon name="shield" />
        </span>
        <h3 id="memory-privacy-heading">Always your choice.</h3>
        <p>Memory is optional. You stay in control of what Line remembers.</p>
        <ul>
          <li>
            <ProductIcon name="check" />
            Facts need your confirmation.
          </li>
          <li>
            <ProductIcon name="clock" />
            Optional details expire after {view.retention_days} days.
          </li>
          <li>
            <ProductIcon name="calendar" />
            Availability, prices, and booking status are checked live.
          </li>
        </ul>
        <p className={styles.help}>
          Deleting optional memory keeps confirmed service, appointment, and
          transcript records in your business history.
        </p>
        <div className={styles.privacyActions}>
          {view.enabled && (
            <button
              type="button"
              className={styles.textButton}
              disabled={busy}
              onClick={() =>
                onAction({
                  title: "Turn off optional memory?",
                  description:
                    "This deletes optional saved details, summaries, and WhatsApp links. Booking and confirmed business records stay available.",
                  label: "Turn off & delete memory",
                  path: "consent",
                  fields: {
                    enabled: false,
                    explicit_confirmation: true,
                  },
                })
              }
            >
              Turn off & delete memory
            </button>
          )}
          <button
            type="button"
            className={styles.dangerLink}
            disabled={busy}
            onClick={() =>
              onAction({
                title: "Clear your optional memory?",
                description: `This deletes saved details, optional summaries, and WhatsApp links. Memory will ${view.enabled ? "stay enabled for future confirmed conversations" : "stay off"}. Confirmed business records are kept.`,
                label: "Delete optional memory",
                path: "delete",
              })
            }
          >
            Delete all optional memory
          </button>
        </div>
      </section>
    </aside>
  );
}
