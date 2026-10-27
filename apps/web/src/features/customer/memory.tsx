"use client";

import { useEffect, useState } from "react";

type Fact = { key: string; value: string };
type SavedFact = Fact & {
  source_kind: string; updated_at: string; expires_at: string;
};
type Source = { intake_id: string; summary: string; suggestions: Fact[] };
type MemoryView = {
  available: boolean;
  enabled: boolean; revision: number; retention_days: number;
  options: Record<string, Record<string, string>>;
  facts: SavedFact[]; sources: Source[]; whatsapp_linked: boolean;
};

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function fact(value: unknown): value is Fact {
  return record(value) && typeof value.key === "string" && typeof value.value === "string";
}

export function parseMemory(value: unknown): MemoryView {
  if (!record(value) || typeof value.available !== "boolean" || typeof value.enabled !== "boolean" ||
      typeof value.revision !== "number" || !Number.isInteger(value.revision) || value.revision < 0 ||
      typeof value.retention_days !== "number" || !record(value.options) ||
      typeof value.whatsapp_linked !== "boolean" || !Array.isArray(value.facts) ||
      !Array.isArray(value.sources)) throw new Error("Memory could not be loaded.");
  const options: MemoryView["options"] = {};
  for (const [key, choices] of Object.entries(value.options)) {
    if (!record(choices)) throw new Error("Invalid memory options.");
    options[key] = {};
    for (const [choice, label] of Object.entries(choices)) {
      if (typeof label !== "string") throw new Error("Invalid memory label.");
      options[key][choice] = label;
    }
  }
  const facts: SavedFact[] = value.facts.map((entry: unknown) => {
    if (!record(entry) || typeof entry.key !== "string" || typeof entry.value !== "string" ||
        typeof entry.source_kind !== "string" ||
        typeof entry.updated_at !== "string" || typeof entry.expires_at !== "string") {
      throw new Error("Invalid saved memory.");
    }
    return { key: entry.key, value: entry.value, source_kind: entry.source_kind,
      updated_at: entry.updated_at, expires_at: entry.expires_at };
  });
  const sources: Source[] = value.sources.map((entry: unknown) => {
    if (!record(entry) || typeof entry.intake_id !== "string" ||
        typeof entry.summary !== "string" || !Array.isArray(entry.suggestions) ||
        !entry.suggestions.every(fact)) throw new Error("Invalid memory source.");
    return { intake_id: entry.intake_id, summary: entry.summary,
      suggestions: entry.suggestions };
  });
  return { available: value.available, enabled: value.enabled, revision: value.revision,
    retention_days: value.retention_days, options, facts, sources,
    whatsapp_linked: value.whatsapp_linked };
}

export function CustomerMemory() {
  const [view, setView] = useState<MemoryView>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [key, setKey] = useState("appointment_time");
  const [value, setValue] = useState("MORNING");
  const [confirmed, setConfirmed] = useState(false);
  const [code, setCode] = useState("");
  const [linkApproved, setLinkApproved] = useState(false);

  async function load() {
    const response = await fetch("/api/v1/development/memory", {
      cache: "no-store", signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new Error("Optional memory is unavailable. Booking still works.");
    setView(parseMemory(await response.json()));
  }
  useEffect(() => {
    const refresh = () => {
      void load().catch((failure: unknown) => {
        setError(failure instanceof Error ? failure.message : "Memory is unavailable.");
      });
    };
    const focus = () => { setView(undefined); setError(""); refresh(); };
    refresh();
    window.addEventListener("focus", focus);
    return () => window.removeEventListener("focus", focus);
  }, []);

  async function mutate(path: string, fields: Record<string, unknown> = {}) {
    if (!view || busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/v1/development/memory/${path}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        signal: AbortSignal.timeout(15000),
        body: JSON.stringify({ ...fields, expected_revision: view.revision,
          request_id: crypto.randomUUID() }),
      });
      if (!response.ok) throw new Error("Update was not confirmed. Refresh and review before retrying.");
      setConfirmed(false);
      setCode("");
      setLinkApproved(false);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Memory update failed.");
    } finally {
      try { await load(); } catch { setError("Refresh to check your saved memory before retrying."); }
      setBusy(false);
    }
  }

  return <section className="customer-empty" aria-labelledby="memory-heading">
    <h2 id="memory-heading">Your optional memory</h2>
    <p>Line can remember selected preferences and equipment facts across Chat,
      Voice and WhatsApp callers you securely link. Enabling memory allows summaries
      of existing and future confirmed conversations since your last memory erasure.
      Availability, prices and appointment
      status are always checked live.</p>
    {error && <p role="alert">{error}</p>}
    {!view && !error && <p role="status">Loading your memory…</p>}
    {view && <>
      {!view.available && <p>This business has disabled optional memory. You can still delete saved data.</p>}
      <p>Optional facts and summaries expire after {view.retention_days} days.
        Deleting optional memory leaves confirmed service, appointment and transcript records in your business history.</p>
      <button type="button" disabled={busy || (!view.available && !view.enabled)} onClick={() => void mutate("consent", {
        enabled: !view.enabled, explicit_confirmation: true,
      })}>{view.enabled ? "Disable memory and delete optional data" : "I consent to optional memory from confirmed conversations"}</button>
      <button type="button" disabled={busy} onClick={() => void mutate("delete")}>Delete all optional memory and unlink WhatsApp</button>
      {view.enabled && <>
        <h3>Saved facts</h3>
        {view.facts.length === 0 && <p>No facts saved. Suggestions become memory only after you confirm them.</p>}
        <ul>{view.facts.map((entry) => <li key={entry.key}>
          {entry.key.replaceAll("_", " ")}: {view.options[entry.key]?.[entry.value] ?? entry.value}
          {" "}<small>Source: {entry.source_kind.replaceAll("_", " ")};
            updated {new Date(entry.updated_at).toLocaleDateString()};
            expires {new Date(entry.expires_at).toLocaleDateString()}.</small>
          {" "}<button type="button" disabled={busy} onClick={() => {
            setKey(entry.key); setValue(entry.value); setConfirmed(false);
          }}>Correct</button>
          {" "}<button type="button" disabled={busy} onClick={() => void mutate(`facts/${entry.key}/delete`)}>Forget</button>
        </li>)}</ul>
        <h3>Add or correct a fact</h3>
        <label>Memory field <select value={key} disabled={busy} onChange={(event) => {
          const next = event.target.value;
          setKey(next); setValue(Object.keys(view.options[next] ?? {})[0] ?? "");
          setConfirmed(false);
        }}>{Object.keys(view.options).map((field) => <option key={field} value={field}>{field.replaceAll("_", " ")}</option>)}</select></label>
        <label>Value <select value={value} disabled={busy} onChange={(event) => {
          setValue(event.target.value); setConfirmed(false);
        }}>{Object.entries(view.options[key] ?? {}).map(([choice, label]) => <option key={choice} value={choice}>{label}</option>)}</select></label>
        <label><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
          I confirm the facts I choose to save are accurate and may be remembered.</label>
        <button type="button" disabled={busy || !confirmed || !view.available} onClick={() => void mutate("facts", {
          facts: [{ key, value }], explicit_confirmation: true,
        })}>Save confirmed fact</button>
        <h3>Authorized conversation summaries</h3>
        {view.sources.length === 0 && <p>No retained authorized conversations available for memory.</p>}
        <ul>{view.sources.map((source) => <li key={source.intake_id}>
          <p>{source.summary}</p>
          {source.suggestions.map((suggestion) => <button type="button"
            key={suggestion.key} disabled={busy || !confirmed || !view.available}
            onClick={() => void mutate("facts", {
              facts: [suggestion], source_intake_id: source.intake_id,
              explicit_confirmation: true,
            })}>Confirm and remember {view.options[suggestion.key]?.[suggestion.value]}</button>)}
        </li>)}</ul>
        <h3>WhatsApp identity</h3>
        <p>{view.whatsapp_linked ? "A WhatsApp caller is linked." : "No WhatsApp caller is linked."}
          Only a caller you approve can access this account&apos;s memory.</p>
        <p>During a consented WhatsApp voice call, ask Line to start account linking.
          Enter the code supplied by that call below. This grants that caller access
          to your optional memory and historical references.</p>
        <label>Call linking code <input value={code} autoComplete="off" spellCheck={false}
          maxLength={128} onChange={(event) => { setCode(event.target.value); setLinkApproved(false); }} /></label>
        <label><input type="checkbox" checked={linkApproved} onChange={(event) => setLinkApproved(event.target.checked)} />
          I approve linking the WhatsApp caller that supplied this code to my account.</label>
        <button type="button" disabled={busy || code.length < 24 || !linkApproved || !view.available}
          onClick={() => void mutate("whatsapp/link", { code, explicit_confirmation: true })}>Approve WhatsApp caller</button>
        <button type="button" disabled={busy || !view.whatsapp_linked}
          onClick={() => void mutate("whatsapp/unlink")}>Unlink WhatsApp</button>
      </>}
    </>}
  </section>;
}
