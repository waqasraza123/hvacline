"use client";

import { useEffect, useState } from "react";

export function InvitationLink({ token }: { token: string }) {
  const [message, setMessage] = useState("");
  const [href, setHref] = useState("");
  useEffect(() => { setHref(`${window.location.origin}/workspace#invite=${encodeURIComponent(token)}`); }, [token]);
  return <section aria-label="Private invitation link" className="ops-card">
    <h3>Share this private invitation</h3>
    <p>This link is shown once and expires in 48 hours. Share it securely with the intended recipient. It has not been emailed automatically.</p>
    <label>Invitation link<input type="password" readOnly value={href} autoComplete="off" /></label>
    <button type="button" disabled={!href} onClick={() => void navigator.clipboard.writeText(href).then(() => setMessage("Invitation copied.")).catch(() => setMessage("Copy is unavailable. Select the link field and copy it manually."))}>Copy invitation</button>
    {message && <p role="status">{message}</p>}
  </section>;
}
