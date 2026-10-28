"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ProductIcon } from "@/components/product-icons";
import { parseMemory } from "./memory-model";
import type { Fact, MemoryView } from "./memory-model";
import { memoryField } from "./memory-presenters";
import { MemoryStats, SavedMemoryFacts, MemorySources } from "./memory-cards";
import { MemorySidebar } from "./memory-sidebar";
import { MemoryActionDialog } from "./memory-action-dialog";
import type { MemoryAction } from "./memory-action-dialog";
import styles from "./memory.module.css";

export function CustomerMemory() {
  const [view, setView] = useState<MemoryView>();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [field, setField] = useState("");
  const [value, setValue] = useState("");
  const [source, setSource] = useState<string>();
  const [confirmed, setConfirmed] = useState(false);
  const [action, setAction] = useState<MemoryAction>();
  const editor = useRef<HTMLSelectElement>(null);
  const mounted = useRef(false);
  const busyRef = useRef(false);
  const version = useRef(0);

  const load = useCallback(async () => {
    const request = ++version.current;
    const response = await fetch("/api/v1/development/memory", {
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok)
      throw new Error(
        "Memory could not be loaded. Your booking is unaffected.",
      );
    const next = parseMemory(await response.json());
    if (mounted.current && request === version.current) setView(next);
  }, []);

  const refresh = useCallback(async () => {
    if (busyRef.current) return;
    setView(undefined);
    setError("");
    setMessage("");
    setConfirmed(false);
    setSource(undefined);
    setAction(undefined);
    try {
      await load();
    } catch (failure) {
      if (mounted.current)
        setError(
          failure instanceof Error ? failure.message : "Memory is unavailable.",
        );
    }
  }, [load]);

  useEffect(() => {
    mounted.current = true;
    const focus = () => {
      void refresh();
    };
    void refresh();
    window.addEventListener("focus", focus);
    return () => {
      mounted.current = false;
      ++version.current;
      window.removeEventListener("focus", focus);
    };
  }, [refresh]);

  async function mutate(
    path: string,
    fields: Record<string, unknown> = {},
    notice = "Your memory has been updated.",
  ) {
    if (!view || busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`/api/v1/development/memory/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: AbortSignal.timeout(15000),
        body: JSON.stringify({
          ...fields,
          expected_revision: view.revision,
          request_id: crypto.randomUUID(),
        }),
      });
      if (!response.ok)
        throw new Error(
          "The change was not confirmed. Refresh and review your memory before retrying.",
        );
      if (mounted.current) {
        setMessage(notice);
        setAction(undefined);
      }
    } catch (failure) {
      if (mounted.current)
        setError(
          failure instanceof Error ? failure.message : "Memory update failed.",
        );
    } finally {
      if (mounted.current) {
        setConfirmed(false);
        setSource(undefined);
        setAction(undefined);
        setView(undefined);
      }
      try {
        if (mounted.current) await load();
      } catch {
        if (mounted.current) {
          setMessage("");
          setError(
            "Refresh to check your saved memory before making another change.",
          );
        }
      }
      busyRef.current = false;
      if (mounted.current) setBusy(false);
    }
  }

  function review(fact: Fact, intakeId?: string) {
    if (!view?.options[fact.key]?.[fact.value]) {
      setError(
        "This detail is no longer available. Refresh your memory and review again.",
      );
      return;
    }
    setField(fact.key);
    setValue(fact.value);
    setSource(intakeId);
    setConfirmed(false);
    editor.current?.focus();
    editor.current?.scrollIntoView({ block: "center" });
  }

  const key =
    field && view?.options[field]
      ? field
      : (Object.keys(view?.options ?? {})[0] ?? "");
  const choices = view?.options[key] ?? {};
  const selectedValue = Object.hasOwn(choices, value)
    ? value
    : (Object.keys(choices)[0] ?? "");
  const canSave = Boolean(
    view?.enabled && view?.available && key && selectedValue,
  );
  const status = !view
    ? "Checking status"
    : !view.available
      ? "Paused by business"
      : view.enabled
        ? "Memory is on"
        : "Memory is off";

  return (
    <section
      className={styles.screen}
      aria-labelledby="memory-heading"
      aria-busy={busy}
    >
      <div className={styles.hero}>
        <div>
          <span className={styles.eyebrow}>A LITTLE MORE FAMILIAR</span>
          <h2 id="memory-heading">The details that make it yours.</h2>
          <p>
            Keep your preferences close, so your next conversation with Line
            feels a little more like picking up where you left off.
          </p>
          <div className={styles.channels}>
            <span>
              <ProductIcon name="chat" />
              Chat
            </span>
            <span>
              <ProductIcon name="mic" />
              Voice
            </span>
            <span>
              <ProductIcon name="shield" />
              WhatsApp you approve
            </span>
          </div>
        </div>
        <div className={styles.heroStatus}>
          <span
            className={styles.status}
            data-active={Boolean(view?.enabled && view?.available)}
          >
            {status}
          </span>
          <p>
            You choose what stays.
            <br />
            You can change your mind.
          </p>
        </div>
      </div>

      <div className={styles.feedback}>
        {error && (
          <div className={styles.error} role="alert">
            <p>{error}</p>
            <button
              type="button"
              disabled={busy}
              onClick={() => void refresh()}
            >
              Refresh memory
            </button>
          </div>
        )}
        {message && (
          <p className={styles.success} role="status">
            <ProductIcon name="check" />
            {message}
          </p>
        )}
      </div>
      {!view && !error && (
        <div className={styles.loading} role="status">
          <ProductIcon name="shield" />
          {busy ? "Updating your memory…" : "Loading your memory…"}
        </div>
      )}
      {view && (
        <>
          {!view.available && (
            <p className={styles.notice}>
              This business has paused optional memory. You can still remove
              saved details and disconnect WhatsApp.
            </p>
          )}
          <MemoryStats view={view} />
          <div className={styles.columns}>
            <div className={styles.mainColumn}>
              {!view.enabled ? (
                <section
                  className={styles.card}
                  aria-labelledby="memory-enable-heading"
                >
                  <span className={styles.icon}>
                    <ProductIcon name="home" />
                  </span>
                  <h3 id="memory-enable-heading">
                    Less repeating. More feeling understood.
                  </h3>
                  <p>
                    Let Line remember the home details and preferences you
                    choose, from your equipment type to a preferred appointment
                    time.
                  </p>
                  <div className={styles.examples}>
                    <span>Equipment details</span>
                    <span>Visit preferences</span>
                    <span>Contact preferences</span>
                  </div>
                  <p className={styles.help}>
                    Enabling memory allows summaries of existing and future
                    confirmed conversations since your last memory erasure.
                    Suggested facts are saved only when you approve them.
                  </p>
                  <button
                    type="button"
                    className={`product-button ${styles.primary}`}
                    disabled={busy || !view.available}
                    onClick={() =>
                      void mutate(
                        "consent",
                        { enabled: true, explicit_confirmation: true },
                        "Optional memory is now on.",
                      )
                    }
                  >
                    I consent — enable optional memory{" "}
                    <ProductIcon name="arrow" />
                  </button>
                </section>
              ) : (
                <>
                  <SavedMemoryFacts
                    view={view}
                    busy={busy}
                    onReview={review}
                    onAction={setAction}
                  />
                  <section
                    className={styles.card}
                    aria-labelledby="memory-editor-heading"
                  >
                    <div className={styles.sectionHeading}>
                      <div>
                        <span className={styles.eyebrow}>
                          {source ? "REVIEW A SUGGESTION" : "MAKE IT PERSONAL"}
                        </span>
                        <h3 id="memory-editor-heading">
                          Add or update a detail
                        </h3>
                      </div>
                      <span className={styles.icon}>
                        <ProductIcon name="check" />
                      </span>
                    </div>
                    <p>
                      {source
                        ? "This detail came from a confirmed conversation. Review it before saving."
                        : "Choose a detail and confirm it’s accurate. Saving replaces the previous value for that detail."}
                    </p>
                    <form
                      className={styles.editor}
                      onSubmit={(event) => {
                        event.preventDefault();
                        if (confirmed && canSave)
                          void mutate(
                            "facts",
                            {
                              facts: [{ key, value: selectedValue }],
                              ...(source ? { source_intake_id: source } : {}),
                              explicit_confirmation: true,
                            },
                            "Your confirmed detail has been saved.",
                          );
                      }}
                    >
                      <div className={styles.fieldRow}>
                        <label>
                          What should Line remember?
                          <select
                            ref={editor}
                            value={key}
                            disabled={busy || !view.available}
                            onChange={(event) => {
                              setField(event.target.value);
                              setValue("");
                              setConfirmed(false);
                              setSource(undefined);
                            }}
                          >
                            {Object.keys(view.options).map((fieldKey) => (
                              <option key={fieldKey} value={fieldKey}>
                                {memoryField(fieldKey)}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Your preference or detail
                          <select
                            value={selectedValue}
                            disabled={busy || !view.available}
                            onChange={(event) => {
                              setValue(event.target.value);
                              setConfirmed(false);
                              setSource(undefined);
                            }}
                          >
                            {Object.entries(choices).map(([option, label]) => (
                              <option key={option} value={option}>
                                {label}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                      {canSave && (
                        <div className={styles.readback}>
                          <span>LINE WILL REMEMBER</span>
                          <strong>
                            {memoryField(key)}: {choices[selectedValue]}
                          </strong>
                        </div>
                      )}
                      <label className={styles.checkbox}>
                        <input
                          type="checkbox"
                          checked={confirmed}
                          disabled={busy || !canSave}
                          onChange={(event) =>
                            setConfirmed(event.target.checked)
                          }
                        />
                        <span>
                          I confirm this detail is accurate and may be
                          remembered for future conversations.
                        </span>
                      </label>
                      <button
                        type="submit"
                        className={`product-button ${styles.primary}`}
                        disabled={busy || !confirmed || !canSave}
                      >
                        {busy ? "Saving…" : "Save confirmed detail"}
                        <ProductIcon name="check" />
                      </button>
                    </form>
                  </section>

                  <MemorySources view={view} busy={busy} onReview={review} />
                </>
              )}
            </div>
            <MemorySidebar
              view={view}
              busy={busy}
              mutate={mutate}
              onAction={setAction}
            />
          </div>
          {action && (
            <MemoryActionDialog
              action={action}
              busy={busy}
              onClose={() => setAction(undefined)}
              onConfirm={() => void mutate(action.path, action.fields)}
            />
          )}
        </>
      )}
    </section>
  );
}
