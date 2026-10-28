"use client";

import { ProductIcon } from "@/components/product-icons";
import type { Fact, MemoryView } from "./memory-model";
import type { MemoryAction } from "./memory-action-dialog";
import { memoryDate, memoryField } from "./memory-presenters";
import styles from "./memory.module.css";

export function MemoryStats({ view }: { view: MemoryView }) {
  return (
    <dl className={styles.stats}>
      <div>
        <dt>Saved details</dt>
        <dd>
          {view.facts.length}
          <span>confirmed by you</span>
        </dd>
      </div>
      <div>
        <dt>Conversation summaries</dt>
        <dd>
          {view.sources.length}
          <span>currently shown</span>
        </dd>
      </div>
      <div>
        <dt>Retention period</dt>
        <dd>
          {view.retention_days}
          <span>days before expiry</span>
        </dd>
      </div>
      <div>
        <dt>WhatsApp connection</dt>
        <dd className={styles.connectionStatus}>
          {view.whatsapp_linked ? "Connected" : "Not connected"}
          <span>only with your approval</span>
        </dd>
      </div>
    </dl>
  );
}

export function SavedMemoryFacts({
  view,
  busy,
  onReview,
  onAction,
}: {
  view: MemoryView;
  busy: boolean;
  onReview: (fact: Fact) => void;
  onAction: (action: MemoryAction) => void;
}) {
  return (
    <section className={styles.card} aria-labelledby="saved-memory-heading">
      <div className={styles.sectionHeading}>
        <div>
          <span className={styles.eyebrow}>CONFIRMED BY YOU</span>
          <h3 id="saved-memory-heading">Your saved details</h3>
        </div>
        <span className={styles.count}>{view.facts.length}</span>
      </div>
      <p>
        Small details for a more personal conversation. Edit or forget them
        whenever you like.
      </p>
      {view.facts.length === 0 ? (
        <div className={styles.empty}>
          <ProductIcon name="home" />
          <strong>A fresh start.</strong>
          <p>
            Add a preference below, or review a suggestion from a confirmed
            conversation.
          </p>
        </div>
      ) : (
        <ul className={styles.facts}>
          {view.facts.map((entry) => (
            <li key={entry.key}>
              <span className={styles.factLabel}>{memoryField(entry.key)}</span>
              <h4>{view.options[entry.key]?.[entry.value] ?? entry.value}</h4>
              <p className={styles.provenance}>
                {entry.source_kind === "CONVERSATION"
                  ? "From a confirmed conversation"
                  : entry.source_kind === "CUSTOMER_CONTROL"
                    ? "Added by you"
                    : entry.source_kind.replaceAll("_", " ")}
              </p>
              <dl className={styles.dates}>
                <div>
                  <dt>Updated</dt>
                  <dd>{memoryDate(entry.updated_at)}</dd>
                </div>
                <div>
                  <dt>Expires</dt>
                  <dd>{memoryDate(entry.expires_at)}</dd>
                </div>
              </dl>
              <div className={styles.factActions}>
                <button
                  type="button"
                  disabled={busy || !view.available}
                  onClick={() => onReview(entry)}
                  aria-label={`Edit ${memoryField(entry.key)}`}
                >
                  Edit detail <ProductIcon name="arrow" />
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    onAction({
                      title: `Forget ${memoryField(entry.key).toLowerCase()}?`,
                      description:
                        "This saved detail will be removed from optional memory.",
                      label: "Forget detail",
                      path: `facts/${encodeURIComponent(entry.key)}/delete`,
                    })
                  }
                  aria-label={`Forget ${memoryField(entry.key)}`}
                >
                  Forget
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function MemorySources({
  view,
  busy,
  onReview,
}: {
  view: MemoryView;
  busy: boolean;
  onReview: (fact: Fact, intakeId: string) => void;
}) {
  return (
    <section className={styles.card} aria-labelledby="memory-sources-heading">
      <div className={styles.sectionHeading}>
        <div>
          <span className={styles.eyebrow}>A LITTLE CONTEXT</span>
          <h3 id="memory-sources-heading">From your conversations</h3>
        </div>
        <span className={styles.icon}>
          <ProductIcon name="chat" />
        </span>
      </div>
      <p>
        Summaries from conversations you confirmed. Suggestions stay suggestions
        until you choose to save them.
      </p>
      {view.sources.length === 0 ? (
        <div className={styles.empty}>
          <ProductIcon name="chat" />
          <strong>No summaries just yet.</strong>
          <p>
            Confirmed conversations can appear here while memory is enabled and
            within its retention period.
          </p>
        </div>
      ) : (
        <ul className={styles.sources}>
          {view.sources.map((item) => (
            <li key={item.intake_id}>
              <div className={styles.sourceHeader}>
                <span>
                  <ProductIcon name="check" />
                  Confirmed conversation
                </span>
                {item.confirmed_at && (
                  <time dateTime={item.confirmed_at}>
                    {memoryDate(item.confirmed_at)}
                  </time>
                )}
              </div>
              <p>{item.summary}</p>
              {item.suggestions.length > 0 && (
                <div className={styles.suggestions}>
                  <span>DETAILS TO REVIEW</span>
                  {item.suggestions.map((suggestion) => (
                    <button
                      key={suggestion.key}
                      type="button"
                      disabled={busy || !view.available}
                      onClick={() => onReview(suggestion, item.intake_id)}
                    >
                      <span>
                        {memoryField(suggestion.key)}
                        <strong>
                          {view.options[suggestion.key]?.[suggestion.value] ??
                            suggestion.value}
                        </strong>
                      </span>
                      <span>
                        Review <ProductIcon name="arrow" />
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
