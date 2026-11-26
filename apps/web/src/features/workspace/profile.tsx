"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { parseReceptionistSettings } from "@/features/receptionist/api";
import { categoriesFromDraft, settingsDraft, validateSettingsDraft } from "@/features/receptionist/settings-form";
import type { ReceptionistSettingsDraft } from "@/features/receptionist/contracts";
import { workspaceRequest, WorkspaceError } from "./api";

const fields: { key: keyof ReceptionistSettingsDraft; label: string; max: number }[] = [
  { key: "publicName", label: "Public business name", max: 160 }, { key: "greeting", label: "Reviewed greeting", max: 600 },
  { key: "officeHours", label: "Public office hours", max: 1000 }, { key: "contactEmail", label: "Public contact email", max: 254 },
  { key: "contactPhone", label: "Public contact phone", max: 32 }, { key: "supportedServiceCategories", label: "Supported HVAC services · one per line", max: 1620 },
  { key: "escalationMessage", label: "Human escalation message", max: 600 },
];

export function BusinessProfile({ agencyId, name, busy, onBusyChange }: { agencyId: string; name: string; busy: boolean; onBusyChange: (value: boolean) => void }) {
  const empty = useMemo(() => ({ publicName: name, greeting: "", officeHours: "", contactEmail: "", contactPhone: "", supportedServiceCategories: "", escalationMessage: "" }), [name]);
  const [draft, setDraft] = useState<ReceptionistSettingsDraft>(empty);
  const [saved, setSaved] = useState<ReceptionistSettingsDraft>();
  const [version, setVersion] = useState(0);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [needsReload, setNeedsReload] = useState(false);
  const latch = useRef(false);
  useEffect(() => {
    let active = true; setLoading(true); setError("");
    void workspaceRequest(`businesses/${agencyId}/profile`).then((raw) => {
      const value = parseReceptionistSettings(raw);
      if (value.agencyId !== agencyId) throw new Error("The returned profile does not match this business.");
      if (active) { const next = settingsDraft(value); setDraft(next); setSaved(next); setVersion(value.rowVersion); setNeedsReload(false); }
    }).catch((failure: unknown) => {
      if (!active) return;
      if (failure instanceof WorkspaceError && failure.status === 404) { setDraft(empty); setSaved(undefined); setVersion(0); setNeedsReload(false); }
      else { setError(failure instanceof Error ? failure.message : "Profile could not be loaded."); setNeedsReload(true); }
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [agencyId, revision, empty]);
  async function save() {
    if (latch.current || busy || loading || needsReload) return;
    const invalid = validateSettingsDraft(draft); if (invalid) { setError(invalid); return; }
    latch.current = true; onBusyChange(true); setError(""); setMessage("");
    try {
      const value = parseReceptionistSettings(await workspaceRequest(`businesses/${agencyId}/profile`, "PUT", {
        public_name: draft.publicName.trim(), greeting: draft.greeting.trim(), office_hours: draft.officeHours.trim(),
        contact_email: draft.contactEmail.trim() || null, contact_phone: draft.contactPhone.trim() || null,
        supported_service_categories: categoriesFromDraft(draft.supportedServiceCategories), escalation_message: draft.escalationMessage.trim(), expected_row_version: version,
      }));
      if (value.agencyId !== agencyId) throw new Error("The saved profile could not be confirmed for this business.");
      const next = settingsDraft(value); setDraft(next); setSaved(next); setVersion(value.rowVersion); setMessage("Business profile saved. Hosted voice agents and phone routing have not been changed.");
    } catch (failure) { setNeedsReload(true); setError(failure instanceof Error ? failure.message : "The save could not be confirmed. Reload saved values before another change."); }
    finally { latch.current = false; onBusyChange(false); }
  }
  return <section className="ops-card"><h2>Business profile</h2><p>Review actual business information and safe handoff wording. Phone-agent setup is a separate step.</p>
    <button type="button" disabled={busy || loading} onClick={() => setRevision((value) => value + 1)}>Reload saved profile</button>
    {loading && <p role="status">Loading business profile…</p>}{error && <p role="alert" className="ops-error">{error}</p>}{message && <p role="status">{message}</p>}
    <form onSubmit={(event) => { event.preventDefault(); void save(); }}><fieldset disabled={busy || loading || needsReload}><legend>Business details</legend>
      {fields.map((field) => <label key={field.key}>{field.label}<textarea rows={field.key === "supportedServiceCategories" ? 4 : 2} maxLength={field.max} value={draft[field.key]} onChange={(event) => setDraft({ ...draft, [field.key]: event.target.value })} /></label>)}
      <button type="submit">Save business profile</button><button type="button" onClick={() => { setDraft(saved ?? empty); setMessage(""); }}>Cancel changes</button>
    </fieldset></form>
  </section>;
}
