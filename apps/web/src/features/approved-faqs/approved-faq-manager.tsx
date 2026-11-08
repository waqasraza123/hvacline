"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Brand } from "@/components/brand";

import {
  ApprovedFaqApiError,
  createApprovedFaq,
  listApprovedFaqs,
  previewApprovedFaqLookup,
  setApprovedFaqStatus,
  updateApprovedFaq,
} from "./api";
import type {
  ApprovedFaq,
  ApprovedFaqDraft,
  ApprovedFaqLookup,
} from "./contracts";
import {
  cleanFaqDraft,
  faqDraftChanged,
  faqDraftProblem,
  matchesKnowledgeFilter,
} from "./knowledge";
import type { KnowledgeFilter } from "./knowledge";
import styles from "./knowledge.module.css";

const EMPTY_DRAFT: ApprovedFaqDraft = {
  question: "",
  approvedAnswer: "",
  questionVariations: [],
};

export function ApprovedFaqManager({
  apiBaseUrl,
  adminToken,
  embedded = false,
}: {
  apiBaseUrl: string;
  adminToken?: string;
  embedded?: boolean;
}) {
  const [faqs, setFaqs] = useState<ApprovedFaq[]>([]);
  const [draft, setDraft] = useState<ApprovedFaqDraft>(EMPTY_DRAFT);
  const [lookupQuery, setLookupQuery] = useState("");
  const [lookup, setLookup] = useState<ApprovedFaqLookup>();
  const [lookupError, setLookupError] = useState<string>();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<KnowledgeFilter>("ALL");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string>();
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string>();
  const processing = useRef(false);

  useEffect(() => {
    let active = true;
    void listApprovedFaqs(apiBaseUrl, adminToken)
      .then((result) => active && setFaqs(result))
      .catch((error: unknown) => active && setLoadError(faqErrorMessage(error)))
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, adminToken, loadAttempt]);

  function operationBusy(value: boolean) {
    processing.current = value;
    setBusy(value);
  }

  function clearLookup() {
    setLookup(undefined);
    setLookupError(undefined);
  }

  async function createFaq() {
    if (processing.current || loading || loadError) return;
    const problem = faqDraftProblem(draft);
    if (problem) {
      setMessage(problem);
      return;
    }
    operationBusy(true);
    setMessage(undefined);
    try {
      const created = await createApprovedFaq(apiBaseUrl, draft, adminToken);
      setFaqs((current) => [...current, created]);
      setDraft(EMPTY_DRAFT);
      clearLookup();
      setMessage("FAQ saved as inactive. Review it, then activate it.");
    } catch (error) {
      setMessage(faqErrorMessage(error));
    } finally {
      operationBusy(false);
    }
  }

  async function previewLookup() {
    if (processing.current || loading || loadError || !lookupQuery.trim())
      return;
    operationBusy(true);
    clearLookup();
    try {
      const result = await previewApprovedFaqLookup(
        apiBaseUrl,
        lookupQuery,
        adminToken,
      );
      setLookup(result);
    } catch (error) {
      setLookupError(faqErrorMessage(error));
    } finally {
      operationBusy(false);
    }
  }

  function replaceFaq(updated: ApprovedFaq) {
    clearLookup();
    setFaqs((current) =>
      current.map((faq) => (faq.id === updated.id ? updated : faq)),
    );
  }

  const Container = embedded ? "section" : "main";
  const activeCount = faqs.filter((faq) => faq.status === "ACTIVE").length;
  const visibleIds = new Set(
    faqs
      .filter((faq) => matchesKnowledgeFilter(faq, search, filter))
      .map((faq) => faq.id),
  );
  const unavailable = loading || !!loadError;
  return (
    <Container className="settings-shell">
      {!embedded && (
        <nav className="top-nav" aria-label="Primary navigation">
          <Brand />
          <div className="nav-links">
            <Link className="text-link" href="/receptionist-settings">
              Business profile
            </Link>
            <Link className="text-link" href="/voice-test">
              Open receptionist
            </Link>
          </div>
        </nav>
      )}
      <header className="page-header">
        <p className="eyebrow">Knowledge base</p>
        <h1>Control what the receptionist can answer</h1>
        <p className="summary">
          The receptionist answers from the business information you approve.
          Questions without a clear answer go to your team.
        </p>
      </header>

      {loading && <p role="status">Loading your knowledge base…</p>}
      {loadError && (
        <div role="alert">
          <p>{loadError}</p>
          <button
            className="secondary-button"
            type="button"
            onClick={() => {
              setLoading(true);
              setLoadError(undefined);
              setLoadAttempt((value) => value + 1);
            }}
          >
            Retry loading
          </button>
        </div>
      )}
      {!unavailable && (
        <p className={styles.summary} role="status">
          {activeCount} active for Line · {faqs.length - activeCount} inactive ·{" "}
          {faqs.length} total answers
        </p>
      )}

      <section className="settings-card">
        <p className="section-kicker">New FAQ</p>
        <h2>Add an approved answer</h2>
        <FaqFields
          draft={draft}
          onChange={setDraft}
          disabled={busy || unavailable}
        />
        <div className="settings-actions">
          <button
            className="primary-button"
            disabled={busy || unavailable}
            onClick={() => void createFaq()}
            type="button"
          >
            Save inactive FAQ
          </button>
          <p className="settings-note">
            Activation is a separate audited action.
          </p>
        </div>
        {message && <p role="status">{message}</p>}
      </section>

      <section className="settings-card">
        <div className="section-heading-row">
          <div>
            <p className="section-kicker">Knowledge base</p>
            <h2>{faqs.length} approved FAQ records</h2>
          </div>
        </div>
        <div className={styles.filters}>
          <label>
            Search questions, answers and alternate phrasings
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <label>
            Show
            <select
              value={filter}
              onChange={(event) => {
                const value = event.target.value;
                if (
                  value === "ALL" ||
                  value === "ACTIVE" ||
                  value === "INACTIVE"
                )
                  setFilter(value);
              }}
            >
              <option value="ALL">All answers</option>
              <option value="ACTIVE">Active for Line</option>
              <option value="INACTIVE">Inactive</option>
            </select>
          </label>
        </div>
        {!unavailable && (
          <p className={styles.help} role="status">
            Showing {visibleIds.size} of {faqs.length} answers.
          </p>
        )}
        <div className="faq-list">
          {!unavailable && faqs.length === 0 && (
            <p className="empty-state">No FAQs have been configured.</p>
          )}
          {!unavailable && faqs.length > 0 && visibleIds.size === 0 && (
            <p className="empty-state">No answers match these filters.</p>
          )}
          {faqs.map((faq) => (
            <div key={faq.id} hidden={!visibleIds.has(faq.id)}>
              <FaqEditor
                apiBaseUrl={apiBaseUrl}
                adminToken={adminToken}
                faq={faq}
                locked={busy || unavailable}
                onBusyChange={operationBusy}
                onReplace={replaceFaq}
              />
            </div>
          ))}
        </div>
      </section>

      <section className="settings-card">
        <p className="section-kicker">Safe retrieval preview</p>
        <h2>Test a customer question</h2>
        <p className={styles.help}>
          Uses the same active answers and retrieval rules as Line. This preview
          does not start a conversation or save a customer question.
        </p>
        <label>
          Customer question
          <input
            maxLength={500}
            disabled={busy || unavailable}
            onChange={(event) => {
              setLookupQuery(event.target.value);
              clearLookup();
            }}
            type="text"
            value={lookupQuery}
          />
        </label>
        <div className="settings-actions">
          <button
            className="secondary-button"
            disabled={busy || unavailable || !lookupQuery.trim()}
            onClick={() => void previewLookup()}
            type="button"
          >
            Test approved lookup
          </button>
        </div>
        {lookup && (
          <div className="lookup-result" role="status">
            <strong>
              {lookup.matched
                ? "Approved answer found"
                : "Staff assistance needed"}
            </strong>
            <p>{lookup.matched ? lookup.answer : lookup.fallbackMessage}</p>
            {lookup.source && (
              <p className={styles.help}>
                Source: {lookup.source.question} · version{" "}
                {lookup.source.rowVersion}
              </p>
            )}
            {!lookup.matched && (
              <p className={styles.help}>
                No clear active match. Review an existing answer or add an
                approved alternate question; Line must not invent an answer.
              </p>
            )}
          </div>
        )}
        {lookupError && <p role="alert">{lookupError}</p>}
      </section>
    </Container>
  );
}

function FaqEditor({
  apiBaseUrl,
  adminToken,
  faq,
  locked,
  onBusyChange,
  onReplace,
}: {
  apiBaseUrl: string;
  adminToken?: string;
  faq: ApprovedFaq;
  locked: boolean;
  onBusyChange: (busy: boolean) => void;
  onReplace: (faq: ApprovedFaq) => void;
}) {
  const [draft, setDraft] = useState<ApprovedFaqDraft>({
    question: faq.question,
    approvedAnswer: faq.approvedAnswer,
    questionVariations: faq.questionVariations,
  });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string>();
  const [conflict, setConflict] = useState(false);
  const processing = useRef(false);
  const dirty = faqDraftChanged(faq, draft);

  async function save() {
    if (processing.current || locked) return;
    const problem = faqDraftProblem(draft);
    if (problem) {
      setMessage(problem);
      return;
    }
    processing.current = true;
    setBusy(true);
    onBusyChange(true);
    setMessage(undefined);
    try {
      const updated = await updateApprovedFaq(
        apiBaseUrl,
        faq,
        draft,
        adminToken,
      );
      onReplace(updated);
      setDraft(updated);
      setConflict(false);
      setMessage("Saved and audited.");
    } catch (error) {
      setConflict(
        error instanceof ApprovedFaqApiError &&
          error.code === "APPROVED_FAQ_VERSION_CONFLICT",
      );
      setMessage(faqErrorMessage(error));
    } finally {
      processing.current = false;
      setBusy(false);
      onBusyChange(false);
    }
  }

  async function toggleStatus() {
    if (processing.current || locked || dirty || conflict) return;
    processing.current = true;
    setBusy(true);
    onBusyChange(true);
    setMessage(undefined);
    try {
      const updated = await setApprovedFaqStatus(
        apiBaseUrl,
        faq,
        faq.status === "ACTIVE" ? "INACTIVE" : "ACTIVE",
        adminToken,
      );
      onReplace(updated);
      setMessage(
        `${updated.status === "ACTIVE" ? "Activated" : "Deactivated"} and audited.`,
      );
    } catch (error) {
      setConflict(
        error instanceof ApprovedFaqApiError &&
          error.code === "APPROVED_FAQ_VERSION_CONFLICT",
      );
      setMessage(faqErrorMessage(error));
    } finally {
      processing.current = false;
      setBusy(false);
      onBusyChange(false);
    }
  }

  async function reloadLatest() {
    if (processing.current || locked) return;
    processing.current = true;
    setBusy(true);
    onBusyChange(true);
    try {
      const latest = (await listApprovedFaqs(apiBaseUrl, adminToken)).find(
        (entry) => entry.id === faq.id,
      );
      if (!latest) throw new Error("Missing answer");
      onReplace(latest);
      setDraft(latest);
      setConflict(false);
      setMessage("Latest saved answer loaded. Local edits discarded.");
    } catch (error) {
      setMessage(faqErrorMessage(error));
    } finally {
      processing.current = false;
      setBusy(false);
      onBusyChange(false);
    }
  }

  return (
    <article className="faq-editor">
      <div className="section-heading-row">
        <span className={`faq-status faq-status-${faq.status.toLowerCase()}`}>
          {faq.status}
        </span>
        <span className="version-badge">Version {faq.rowVersion}</span>
      </div>
      <p className={styles.help}>
        {faq.status === "ACTIVE"
          ? "Saving approved changes updates what Line can use immediately."
          : "Inactive answers are excluded from live retrieval and preview."}
      </p>
      <FaqFields draft={draft} onChange={setDraft} disabled={busy || locked} />
      <div className="settings-actions">
        <button
          className="secondary-button"
          disabled={busy || locked || !dirty || conflict}
          onClick={() => void save()}
          type="button"
        >
          Save changes
        </button>
        <button
          className="secondary-button"
          disabled={busy || locked || dirty || conflict}
          onClick={() => void toggleStatus()}
          type="button"
        >
          {faq.status === "ACTIVE" ? "Deactivate" : "Activate"}
        </button>
        {dirty && !conflict && (
          <button
            className="secondary-button"
            disabled={busy || locked}
            type="button"
            onClick={() => {
              setDraft(faq);
              setMessage(undefined);
            }}
          >
            Discard edits
          </button>
        )}
        {conflict && (
          <button
            className="secondary-button"
            disabled={busy || locked}
            type="button"
            onClick={() => void reloadLatest()}
          >
            Discard edits and reload latest
          </button>
        )}
      </div>
      {dirty && (
        <p className={styles.help}>
          Save or discard edits before changing activation.
        </p>
      )}
      {message && <p role="status">{message}</p>}
    </article>
  );
}

function FaqFields({
  draft,
  onChange,
  disabled,
}: {
  draft: ApprovedFaqDraft;
  onChange: (draft: ApprovedFaqDraft) => void;
  disabled: boolean;
}) {
  return (
    <fieldset className={`faq-fields ${styles.fields}`} disabled={disabled}>
      <legend className={styles.legend}>Approved question and answer</legend>
      <label>
        Approved customer question
        <input
          maxLength={300}
          onChange={(event) =>
            onChange({ ...draft, question: event.target.value })
          }
          type="text"
          value={draft.question}
        />
      </label>
      <label>
        Exact approved answer
        <textarea
          maxLength={2_000}
          onChange={(event) =>
            onChange({ ...draft, approvedAnswer: event.target.value })
          }
          value={draft.approvedAnswer}
        />
      </label>
      <label>
        Other ways customers ask this
        <textarea
          rows={3}
          maxLength={2408}
          value={draft.questionVariations.join("\n")}
          onChange={(event) =>
            onChange({
              ...draft,
              questionVariations: event.target.value.split("\n"),
            })
          }
        />
        <small className={styles.help}>
          Up to eight distinct questions, one per line, 300 characters each. All
          must have the same approved answer.{" "}
          {cleanFaqDraft(draft).questionVariations.length}/8 added.
        </small>
      </label>
    </fieldset>
  );
}

function faqErrorMessage(error: unknown): string {
  if (error instanceof ApprovedFaqApiError) {
    if (error.status === 409) {
      return `${error.message}. Your edits are kept; review the saved answer before retrying.`;
    }
    return error.message;
  }
  return "The approved FAQ service is unavailable.";
}
