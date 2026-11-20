"use client";

import { useState } from "react";
import type { AiConnection, RecoveryApi } from "./api";
import styles from "./recovery.module.css";

export function AiSettings({ connection, api, onChange }: { connection: AiConnection; api: RecoveryApi; onChange: (connection: AiConnection) => void }) {
  const [provider, setProvider] = useState<"OPENAI" | "OPENAI_COMPATIBLE" | "ELEVENLABS">(connection.provider ?? "OPENAI");
  const [model, setModel] = useState(connection.model);
  const [endpoint, setEndpoint] = useState(connection.endpoint);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function act(task: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await task(); } catch (error) { setError(error instanceof Error ? error.message : "Could not update AI settings."); } finally { setBusy(false); setKey(""); }
  }
  return <section className={styles.panel} id="recovery-ai-settings">
    <div className={styles.toolbar}><h2>Connect Your AI Model</h2><span className={styles.badge}>{connection.status.replaceAll("_", " ")}</span></div>
    <p className={styles.muted}>Use your preferred AI provider to power customer conversations and recovery workflows.</p>
    <p className={styles.notice}>This connection supports staff-reviewed text drafts through Chat Completions. It cannot place calls, send messages, query appointments or book visits. Custom models are unsupported for live ElevenLabs recovery calling.</p>
    {!connection.encryption_configured && <p className={styles.notice}>Backend credential encryption is not configured. An administrator must set RECOVERY_TOKEN_ENCRYPTION_KEY before saving a connection.</p>}
    <form className={styles.form} onSubmit={(event) => { event.preventDefault(); void act(async () => {
      const result = await api<AiConnection>("ai", "PUT", { provider, model, endpoint: provider === "OPENAI" ? "https://api.openai.com/v1" : endpoint, expected_row_version: connection.row_version, ...(key ? { api_key: key } : {}) });
      onChange(result); setMessage("Configuration saved, not yet tested. Automation remains disabled.");
    }); }}>
      <label>Provider<select value={provider} disabled={busy} onChange={(event) => setProvider(event.target.value as typeof provider)}><option value="OPENAI">OpenAI · text model</option><option value="OPENAI_COMPATIBLE">OpenAI-compatible · custom / self-hosted</option><option value="ELEVENLABS">ElevenLabs · existing voice integration</option></select></label>
      {provider === "ELEVENLABS" ? <p className={styles.notice}>{connection.voice_status} Configure the existing private agent and telephony integration using the current voice setup. These text-model settings do not change hosted agents or telephone configuration.</p> : <>
        <label>Model name<input value={model} required maxLength={128} onChange={(event) => setModel(event.target.value)} disabled={busy} placeholder="Enter a model available in your account" /></label>
        {provider === "OPENAI_COMPATIBLE" && <label>API endpoint<input type="url" required value={endpoint} onChange={(event) => setEndpoint(event.target.value)} disabled={busy} placeholder="https://your-approved-provider.example/v1" /><span className={styles.muted}>Only explicitly allowlisted public HTTPS origins on port 443 are supported. Localhost, private networks, metadata endpoints, redirects and proxy environment settings are unsupported.</span></label>}
        <label>{connection.has_credential ? "Replace API key (leave blank to keep the saved key)" : "API key"}<input type="password" value={key} required={!connection.has_credential || provider !== connection.provider} onChange={(event) => setKey(event.target.value)} autoComplete="off" spellCheck={false} disabled={busy} maxLength={4096} /></label>
        <p className={styles.muted}>Keys are sent only to your authenticated backend and stored encrypted. The saved key is never returned. Model requirements: text messages, non-streaming Chat Completions and max_tokens. Tool calling, reasoning-only responses, audio and automatic provider fallback are unsupported.</p>
        <div className={styles.actions}><button type="submit" className={styles.primary} disabled={busy || !connection.encryption_configured}>{busy ? "Working…" : "Save configuration"}</button>
          <button type="button" disabled={busy || !connection.has_credential} onClick={() => void act(async () => { const result = await api<{ connection: AiConnection }>("ai/test", "POST", { expected_row_version: connection.row_version }); onChange(result.connection); setMessage("Text connection succeeded. This does not verify live calling or messaging."); })}>Test saved connection · small API request</button>
          <button type="button" disabled={busy || !connection.has_credential} onClick={() => void act(async () => { onChange(await api<AiConnection>("ai/revoke", "POST", { expected_row_version: connection.row_version })); setMessage("Credential revoked. No further requests can use this connection."); })}>Revoke credential</button></div>
      </>}
    </form>
    {connection.last_tested_at && <p className={styles.muted}>Last model request: {connection.last_tested_at}. {connection.last_error ? `Status: ${connection.last_error}.` : ""}</p>}
    {message && <p role="status" className={styles.notice}>{message}</p>}{error && <p role="alert" className={styles.notice}>{error} Refresh connection status before retrying an uncertain request.</p>}
  </section>;
}
