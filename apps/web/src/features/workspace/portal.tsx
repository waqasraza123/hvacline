"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { AuthenticatorSetup } from "@/features/customer/authenticator-setup";
import { parseMfaSetup } from "@/features/customer/mfa-setup";
import type { MfaSetup } from "@/features/customer/mfa-setup";
import { BusinessWorkspace } from "./workspace";
import { parseStaffUser, workspaceRequest, WorkspaceError } from "./api";
import type { StaffUser } from "./api";
import styles from "./workspace.module.css";

export function WorkspacePortal() {
  const [user, setUser] = useState<StaffUser>();
  const [businessId, setBusinessId] = useState("");
  const [invite, setInvite] = useState("");
  const [setup, setSetup] = useState<MfaSetup>();
  const [enroll, setEnroll] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(false);

  async function reloadIdentity() {
    const value = parseStaffUser(await workspaceRequest("auth/me"));
    setUser(value);
    setBusinessId((current) => value.businesses.some((item) => item.id === current) ? current : value.businesses[0]?.id ?? "");
  }
  useEffect(() => {
    const parameters = new URLSearchParams(window.location.hash.slice(1));
    const token = parameters.get("invite");
    if (token && /^[A-Za-z0-9_-]{43}$/.test(token)) { setInvite(token); setEnroll(true); }
    if (parameters.has("invite")) window.history.replaceState(null, "", window.location.pathname + window.location.search);
    let active = true;
    void workspaceRequest("auth/me").then((raw) => { if (active) { const value = parseStaffUser(raw); setUser(value); setBusinessId(value.businesses[0]?.id ?? ""); } })
      .catch((failure: unknown) => { if (active && !(failure instanceof WorkspaceError && failure.status === 401)) setError(failure instanceof Error ? failure.message : "Staff sign-in is unavailable."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function perform(task: () => Promise<void>) {
    if (inFlight.current || busy) return;
    inFlight.current = true; setBusy(true); setError("");
    try { await task(); } catch (failure) { setError(failure instanceof Error ? failure.message : "This request could not finish. Review saved status before retrying."); }
    finally { inFlight.current = false; setBusy(false); }
  }
  const business = user?.businesses.find((item) => item.id === businessId);

  return <div className={`customer-shell ${styles.root}`}>
    <header className="product-header product-container"><Brand /><ThemeToggle />
      {user && <button type="button" disabled={busy} onClick={() => void perform(async () => { await workspaceRequest("auth/logout", "POST", {}); setUser(undefined); setBusinessId(""); setSetup(undefined); setInvite(""); })}>Sign out of staff workspace</button>}
    </header>
    <main className={`product-container ${styles.main}`}>
      <h1>{user ? "Your business workspace" : "Staff sign in"}</h1>
      {loading && <p role="status">Loading staff access…</p>}
      {error && <p role="alert" className="ops-error">{error}</p>}
      {!loading && !user && <section className="ops-card">
        <p>Business staff use a separate password and authenticator. Customer accounts do not grant business access.</p>
        {!setup && <form onSubmit={(event) => {
          event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
          void perform(async () => {
            if (enroll) {
              setSetup(parseMfaSetup(await workspaceRequest("auth/invitation/start", "POST", { token: invite, password: data.get("password"), display_name: data.get("name") })));
              form.reset();
            } else {
              await workspaceRequest("auth/login", "POST", { email: data.get("email"), password: data.get("password"), code: data.get("code") });
              form.reset(); await reloadIdentity();
            }
          });
        }}>
          {enroll ? <label>Your staff name<input name="name" required maxLength={160} autoComplete="name" disabled={busy} /></label> : <label>Staff email<input type="email" name="email" required maxLength={254} autoComplete="username" disabled={busy} /></label>}
          <label>{enroll ? "Create a password · at least 15 characters" : "Password"}<input name="password" type="password" required minLength={enroll ? 15 : 1} maxLength={128} autoComplete={enroll ? "new-password" : "current-password"} disabled={busy} /></label>
          {!enroll && <label>Authenticator code<input name="code" required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} autoComplete="one-time-code" disabled={busy} /></label>}
          <button type="submit" disabled={busy || enroll && !invite}>{busy ? "Working…" : enroll ? "Set up authenticator" : "Sign in"}</button>
        </form>}
        {setup && <><AuthenticatorSetup setup={setup} /><form onSubmit={(event) => {
          event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
          void perform(async () => { await workspaceRequest("auth/invitation/confirm", "POST", { token: invite, code: data.get("code") }); setSetup(undefined); setInvite(""); setEnroll(false); form.reset(); await reloadIdentity(); });
        }}><label>Current authenticator code<input name="code" required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} autoComplete="one-time-code" disabled={busy} /></label><button type="submit" disabled={busy}>Verify and join business</button></form></>}
        {invite && <button type="button" disabled={busy} onClick={() => { setEnroll(!enroll); setSetup(undefined); setError(""); }}>{enroll ? "Already have a staff account? Sign in" : "Create the invited staff account"}</button>}
        <button type="button" disabled={busy} onClick={() => void perform(reloadIdentity)}>Check saved sign-in</button>
        <p>An invitation from the business owner is required. <Link href="/workspace/setup">Platform business setup</Link></p>
      </section>}
      {user && <>
        <p>{user.display_name} · {user.email}</p>
        {invite && <section className="ops-card"><h2>Join the invited business</h2><p>The invitation must match your signed-in staff email. Joining adds only the role the owner granted.</p><button type="button" disabled={busy} onClick={() => void perform(async () => { await workspaceRequest("auth/invitation/accept", "POST", { token: invite }); setInvite(""); await reloadIdentity(); })}>Accept invitation</button><button type="button" disabled={busy} onClick={() => setInvite("")}>Keep current access</button></section>}
        <div className={styles.toolbar}><label>Business<select value={businessId} disabled={busy} onChange={(event) => setBusinessId(event.target.value)}>{user.businesses.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.role}</option>)}</select></label><button type="button" disabled={busy} onClick={() => void perform(reloadIdentity)}>Refresh access</button></div>
        {!business && <p>No active business membership is available. Accept an invitation or ask an owner to restore access.</p>}
        {business && <BusinessWorkspace key={`${business.id}:${business.role}`} business={business} busy={busy} onBusyChange={setBusy} onIdentityChange={reloadIdentity} />}
      </>}
    </main>
  </div>;
}
