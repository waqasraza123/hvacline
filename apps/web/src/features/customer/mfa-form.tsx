"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Brand } from "@/components/brand";

type Stage = "loading" | "enroll" | "verify" | "recovery" | "codes";

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function securityRequest(action: string, body?: object): Promise<unknown> {
  const response = await fetch(`/api/account/${action}`, {
    method: body === undefined ? "GET" : "POST", cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(20000),
  });
  const data: unknown = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(record(data) && record(data.error) &&
    typeof data.error.message === "string" ? data.error.message :
    "Verification could not be completed. Sign in again and retry.");
  return data;
}

async function loadMfa(): Promise<{ stage: "enroll" | "verify"; secret?: string }> {
  const status = await securityRequest("mfa-status");
  if (!record(status) || !["enroll", "verify"].includes(String(status.next_action))) {
    throw new Error("Sign in again to continue verification.");
  }
  if (status.next_action === "verify") return { stage: "verify" };
  const setup = await securityRequest("mfa-setup", {});
  if (!record(setup) || typeof setup.secret !== "string" ||
      !/^[A-Z2-7]{32}$/.test(setup.secret)) {
    throw new Error("Authenticator setup could not be loaded. Sign in again.");
  }
  return { stage: "enroll", secret: setup.secret };
}

export function CustomerMfaForm() {
  const router = useRouter();
  const [stage, setStage] = useState<Stage>("loading");
  const [secret, setSecret] = useState<string>();
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const [savedCodes, setSavedCodes] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void loadMfa().then((result) => {
      if (active) { setStage(result.stage); setSecret(result.secret); }
    }).catch((failure: unknown) => {
      if (active) setError(failure instanceof Error ? failure.message : "Sign in again.");
    });
    return () => { active = false; };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError("");
    try {
      const result = await securityRequest(stage === "recovery" ? "mfa-recover" : "mfa-verify", { code });
      setCode("");
      if (stage === "recovery") {
        const next = await loadMfa();
        setSecret(next.secret); setStage(next.stage);
      } else if (record(result) && Array.isArray(result.recovery_codes) &&
          result.recovery_codes.length === 10 &&
          result.recovery_codes.every((item: unknown) => typeof item === "string")) {
        setSecret(undefined); setCodes(result.recovery_codes); setStage("codes");
      } else {
        setSecret(undefined); router.replace("/book"); router.refresh();
      }
    } catch (failure) {
      setCode("");
      setError(failure instanceof Error ? failure.message : "Verification failed. Sign in again.");
    } finally { setBusy(false); }
  }

  async function cancel() {
    setBusy(true); setSecret(undefined); setCodes([]);
    await securityRequest("mfa-cancel", {}).catch(() => undefined);
    router.replace("/login"); router.refresh();
  }

  return <div className="customer-shell auth-page">
    <header className="product-header product-container"><Brand /></header>
    <main className="product-container">
      <section className="auth-card" aria-labelledby="mfa-title">
        <h1 id="mfa-title">{stage === "enroll" ? "Set up your authenticator" :
          stage === "codes" ? "Save your recovery codes" : "Verify your authenticator"}</h1>
        <p>Authenticator verification is required for every customer account.
          Your account stays locked until setup and verification are complete.</p>
        {stage === "loading" && !error && <p role="status">Loading secure verification…</p>}
        {stage === "enroll" && <>
          <p>In Google Authenticator, Microsoft Authenticator, or another compatible
            app, add a setup key manually. Use “HVACLine AI” as the account label
            and choose a time-based, six-digit code.</p>
          <p>Your setup key:</p><code aria-label="Authenticator setup key" style={{ overflowWrap: "anywhere" }}>{secret}</code>
          <p>Keep this key private. Do not send it to support or paste it into a conversation.</p>
        </>}
        {stage === "codes" ? <>
          <p>These codes appear once. Store them somewhere private, separate from
            your password. Each can be used once to replace a lost authenticator.</p>
          <pre aria-label="One-time recovery codes" style={{ overflowX: "auto" }}>{codes.join("\n")}</pre>
          <label className="auth-checkbox"><input type="checkbox" checked={savedCodes}
            onChange={(event) => setSavedCodes(event.target.checked)} />I saved my recovery codes securely.</label>
          <button type="button" className="product-button" disabled={!savedCodes}
            onClick={() => { setCodes([]); router.replace("/book"); router.refresh(); }}>Continue to my account</button>
        </> : stage !== "loading" && <form onSubmit={(event) => void submit(event)} aria-busy={busy}>
          <label>{stage === "recovery" ? "Unused recovery code" : "Six-digit authenticator code"}
            <input value={code} onChange={(event) => setCode(event.target.value)}
              autoComplete={stage === "recovery" ? "off" : "one-time-code"}
              inputMode={stage === "recovery" ? "text" : "numeric"}
              pattern={stage === "recovery" ? "[A-Fa-f0-9]{8}(-[A-Fa-f0-9]{8}){3}" : "[0-9]{6}"}
              minLength={stage === "recovery" ? 35 : 6} maxLength={stage === "recovery" ? 35 : 6}
              spellCheck={false} required disabled={busy} />
          </label>
          {stage === "recovery" && <p>After validating this code, you must set up a
            new authenticator before your account can be unlocked.</p>}
          <button className="product-button" type="submit" disabled={busy}>
            {busy ? "Verifying…" : stage === "recovery" ? "Replace lost authenticator" : "Verify & continue"}
          </button>
          {stage === "verify" && <button type="button" disabled={busy}
            onClick={() => { setCode(""); setStage("recovery"); }}>Use a recovery code</button>}
          {stage === "recovery" && <button type="button" disabled={busy}
            onClick={() => { setCode(""); setStage("verify"); }}>Use my authenticator instead</button>}
        </form>}
        {error && <p className="customer-error" role="alert">{error}</p>}
        {stage !== "codes" && <button type="button" disabled={busy}
          onClick={() => void cancel()}>Cancel and sign in again</button>}
        <p><Link href="/">Return home</Link></p>
      </section>
    </main>
  </div>;
}
