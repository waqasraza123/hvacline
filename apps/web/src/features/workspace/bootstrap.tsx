"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { identifier, isRecord, parseInvitationToken, workspaceRequest } from "./api";
import { InvitationLink } from "./invitation-link";
import styles from "./workspace.module.css";

type Business = { id: string; name: string; slug: string; owner_email: string; has_owner: boolean };

export function WorkspaceBootstrap() {
  const [key, setKey] = useState("");
  const [rows, setRows] = useState<Business[]>();
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const creationKey = useRef("");
  const inFlight = useRef(false);

  async function refresh() {
    const data = await workspaceRequest("bootstrap/list", "POST", { bootstrap_key: key });
    if (!isRecord(data) || !Array.isArray(data.items) || !data.items.every((item: unknown) => isRecord(item) && typeof item.id === "string" && typeof item.name === "string" && typeof item.slug === "string" && typeof item.owner_email === "string" && typeof item.has_owner === "boolean")) throw new Error("The saved business list could not be verified.");
    setRows((data.items as Business[]).map((item) => ({ ...item, id: identifier(item.id) })));
  }
  async function perform(task: () => Promise<void>) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError(""); setToken("");
    try { await task(); } catch (failure) { setError(failure instanceof Error ? failure.message : "Setup could not finish. Reload saved businesses before another change."); }
    finally { inFlight.current = false; setBusy(false); }
  }

  return <div className={`customer-shell ${styles.root}`}>
    <header className="product-header product-container"><Brand /><ThemeToggle /><Link href="/workspace">Staff sign in</Link></header>
    <main className={`product-container ${styles.main}`}>
      <h1>Set up a business</h1><p>Platform operators create the business and invite its first owner. Each business manages its own staff after the owner joins.</p>
      <form className="ops-card" onSubmit={(event) => { event.preventDefault(); void perform(async () => { await refresh(); creationKey.current = ""; }); }}>
        <label>Platform-owner access key<input type="password" value={key} required minLength={32} maxLength={256} autoComplete="off" onChange={(event) => { setKey(event.target.value); setRows(undefined); setToken(""); }} /></label>
        <button type="submit" disabled={busy}>{busy ? "Working…" : "Open business setup"}</button>
      </form>
      {error && <p role="alert" className="ops-error">{error}</p>}
      {rows && <>
        <form className="ops-card" onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          void perform(async () => {
            creationKey.current ||= crypto.randomUUID();
            const result = await workspaceRequest("bootstrap/create", "POST", { bootstrap_key: key, creation_key: creationKey.current,
              name: data.get("name"), slug: data.get("slug"), owner_email: data.get("email") });
            if (!isRecord(result) || typeof result.id !== "string" || typeof result.replayed !== "boolean") throw new Error("The creation outcome is uncertain. Reload saved businesses.");
            if (result.invitation) setToken(parseInvitationToken(result.invitation));
            await refresh(); creationKey.current = "";
          });
        }}>
          <h2>Create business and owner invitation</h2>
          <label>Business name<input name="name" required maxLength={160} disabled={busy} /></label>
          <label>Business identifier<input name="slug" required minLength={3} maxLength={63} pattern="[a-z0-9]+(-[a-z0-9]+)*" placeholder="your-business-name" disabled={busy} /></label>
          <label>Owner email<input name="email" type="email" required maxLength={254} disabled={busy} /></label>
          <button type="submit" disabled={busy}>Create business and invitation</button>
        </form>
        {token && <InvitationLink key={token} token={token} />}
        <section className="ops-card"><h2>Saved businesses</h2><p>A business remains unconfigured until its owner accepts and supplies its actual details. No phone number or voice agent is activated here.</p>
          <button type="button" disabled={busy} onClick={() => void perform(async () => { await refresh(); creationKey.current = ""; })}>Reload businesses</button>
          {!rows.length && <p>No businesses have been created through this setup flow.</p>}
          {rows.map((row) => <div key={row.id} className={styles.listRow}><div><strong>{row.name}</strong><p>{row.slug} · {row.owner_email}</p><span>{row.has_owner ? "Owner has joined" : "Awaiting initial owner"}</span></div>
            {!row.has_owner && <button type="button" disabled={busy} onClick={() => void perform(async () => {
              const result = await workspaceRequest(`bootstrap/businesses/${row.id}/owner-invitation`, "POST", { bootstrap_key: key });
              setToken(parseInvitationToken(result)); await refresh();
            })}>Replace initial invitation</button>}
          </div>)}
        </section>
      </>}
    </main>
  </div>;
}
