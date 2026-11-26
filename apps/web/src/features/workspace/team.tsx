"use client";

import { useEffect, useRef, useState } from "react";
import { parseInvitationToken, parseTeam, workspaceRequest } from "./api";
import type { Member, Role, Team } from "./api";
import { InvitationLink } from "./invitation-link";
import styles from "./workspace.module.css";

export function TeamPanel({ agencyId, busy, onBusyChange, onIdentityChange }: { agencyId: string; busy: boolean; onBusyChange: (value: boolean) => void; onIdentityChange: () => Promise<void> }) {
  const [data, setData] = useState<Team>();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [token, setToken] = useState("");
  const [needsReload, setNeedsReload] = useState(false);
  const inFlight = useRef(false);
  async function load() { setData(parseTeam(await workspaceRequest(`businesses/${agencyId}/team`))); setNeedsReload(false); }
  useEffect(() => {
    let active = true;
    void workspaceRequest(`businesses/${agencyId}/team`).then((raw) => { if (active) setData(parseTeam(raw)); }).catch((failure: unknown) => { if (active) setError(failure instanceof Error ? failure.message : "Team access could not be loaded."); });
    return () => { active = false; };
  }, [agencyId]);

  async function perform(task: () => Promise<void>, refresh = false) {
    if (inFlight.current || busy || needsReload && !refresh) return;
    inFlight.current = true; onBusyChange(true); setError(""); setMessage(""); setToken("");
    try { await task(); } catch (failure) { setNeedsReload(true); setError(failure instanceof Error ? failure.message : "The update could not be confirmed. Reload team status before another change."); }
    finally { inFlight.current = false; onBusyChange(false); }
  }
  const path = `businesses/${agencyId}`;
  return <section className="ops-card" aria-labelledby="team-heading">
    <h2 id="team-heading">Business team</h2><p>Owners manage all roles. Administrators can invite and manage staff. Staff cannot change business configuration or team access.</p>
    <button type="button" disabled={busy} onClick={() => void perform(async () => { await load(); await onIdentityChange(); }, true)}>Reload team and access</button>
    {error && <p className="ops-error" role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {data && <>
      <form onSubmit={(event) => { event.preventDefault(); const form = event.currentTarget; const fields = new FormData(form);
        void perform(async () => { setToken(parseInvitationToken(await workspaceRequest(`${path}/invitations`, "POST", { email: fields.get("email"), role: fields.get("role") }))); form.reset(); await load(); });
      }}><fieldset disabled={busy || needsReload}><legend>Invite a team member</legend>
        <label>Staff email<input name="email" type="email" required maxLength={254} autoComplete="off" /></label>
        <label>Business role<select name="role" defaultValue="STAFF"><option value="STAFF">Staff</option>{data.role === "OWNER" && <><option value="ADMIN">Administrator</option><option value="OWNER">Owner</option></>}</select></label>
        <button type="submit">Create private invitation</button></fieldset>
      </form>
      {token && <InvitationLink key={token} token={token} />}
      <h3>Members · up to 100 loaded</h3>
      {data.members.map((row) => <MemberEditor key={`${row.id}:${row.row_version}`} member={row} canEdit={data.role === "OWNER" || row.role === "STAFF"} owner={data.role === "OWNER"} disabled={busy || needsReload}
        save={(role, active) => perform(async () => { await workspaceRequest(`${path}/members/${row.id}`, "PUT", { role, active, expected_row_version: row.row_version }); await load(); await onIdentityChange(); setMessage("Membership updated. Access is checked on each new business request."); })} />)}
      <h3>Invitations · latest 100</h3>
      {!data.invitations.length && <p>No invitations recorded.</p>}
      {data.invitations.map((row) => <div key={row.id} className={styles.listRow}><div><strong>{row.email}</strong><p>{row.role} · {row.consumed ? "Accepted" : row.revoked ? "Revoked" : "Pending or expired"}</p><small>Expires {new Date(row.expires_at).toLocaleString()}</small></div>
        {!row.consumed && !row.revoked && (data.role === "OWNER" || row.role === "STAFF") && <button type="button" disabled={busy || needsReload} onClick={() => void perform(async () => { await workspaceRequest(`${path}/invitations/${row.id}/revoke`, "POST", { expected_row_version: row.row_version }); await load(); setMessage("Invitation revoked. Its link can no longer grant access."); })}>Revoke invitation</button>}
      </div>)}
    </>}
  </section>;
}

function MemberEditor({ member, canEdit, owner, disabled, save }: { member: Member; canEdit: boolean; owner: boolean; disabled: boolean; save: (role: Role, active: boolean) => Promise<void> }) {
  const [role, setRole] = useState<Role>(member.role);
  const [active, setActive] = useState(member.active);
  return <form className={styles.member} onSubmit={(event) => { event.preventDefault(); void save(role, active); }}>
    <div><strong>{member.display_name}</strong><p>{member.email ?? "Email unavailable"} · {member.active ? "Active" : "Inactive"}</p></div>
    <fieldset disabled={disabled || !canEdit}><legend>Access for {member.display_name}</legend>
      <label>Role<select value={role} onChange={(event) => setRole(event.target.value as Role)}><option value="STAFF">Staff</option>{owner && <><option value="ADMIN">Administrator</option><option value="OWNER">Owner</option></>}{!owner && member.role !== "STAFF" && <option value={member.role}>{member.role}</option>}</select></label>
      <label className={styles.checkbox}><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} />Active business access</label>
      <button type="submit" disabled={role === member.role && active === member.active}>Save membership</button>
    </fieldset>
  </form>;
}
