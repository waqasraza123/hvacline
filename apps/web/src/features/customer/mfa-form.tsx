"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Brand } from "@/components/brand";
import { ProductIcon } from "@/components/product-icons";
import { AuthenticatorSetup } from "./authenticator-setup";
import { parseMfaSetup } from "./mfa-setup";
import type { MfaSetup } from "./mfa-setup";
import styles from "./mfa-form.module.css";

type Stage = "loading" | "enroll" | "verify" | "recovery" | "codes";
type MfaState = { stage: "enroll"; setup: MfaSetup } | { stage: "verify" };

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function securityRequest(
  action: string,
  body?: object,
): Promise<unknown> {
  const response = await fetch(`/api/account/${action}`, {
    method: body === undefined ? "GET" : "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(20000),
  });
  const data: unknown = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    throw new Error(
      record(data) &&
        record(data.error) &&
        typeof data.error.message === "string"
        ? data.error.message
        : "Verification could not be completed. Sign in again and retry.",
    );
  }
  return data;
}

async function loadMfa(): Promise<MfaState> {
  const status = await securityRequest("mfa-status");
  if (
    !record(status) ||
    !["enroll", "verify"].includes(String(status.next_action))
  ) {
    throw new Error("Sign in again to continue verification.");
  }
  if (status.next_action === "verify") return { stage: "verify" };
  return {
    stage: "enroll",
    setup: parseMfaSetup(await securityRequest("mfa-setup", {})),
  };
}

export function CustomerMfaForm() {
  const router = useRouter();
  const leaving = useRef(false);
  const [stage, setStage] = useState<Stage>("loading");
  const [setup, setSetup] = useState<MfaSetup>();
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const [savedCodes, setSavedCodes] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void loadMfa()
      .then((result) => {
        if (active && !leaving.current) {
          setSetup(result.stage === "enroll" ? result.setup : undefined);
          setStage(result.stage);
        }
      })
      .catch((failure: unknown) => {
        if (active && !leaving.current)
          setError(
            failure instanceof Error ? failure.message : "Sign in again.",
          );
      });
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await securityRequest(
        stage === "recovery" ? "mfa-recover" : "mfa-verify",
        { code },
      );
      setCode("");
      if (stage === "recovery") {
        const next = await loadMfa();
        setSetup(next.stage === "enroll" ? next.setup : undefined);
        setStage(next.stage);
      } else if (
        record(result) &&
        Array.isArray(result.recovery_codes) &&
        result.recovery_codes.length === 10 &&
        result.recovery_codes.every((item: unknown) => typeof item === "string")
      ) {
        setSetup(undefined);
        setCodes(result.recovery_codes);
        setSavedCodes(false);
        setStage("codes");
      } else {
        setSetup(undefined);
        router.replace("/book");
        router.refresh();
      }
    } catch (failure) {
      setCode("");
      setError(
        failure instanceof Error
          ? failure.message
          : "Verification failed. Sign in again.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    leaving.current = true;
    setBusy(true);
    setSetup(undefined);
    setCode("");
    setCodes([]);
    await securityRequest("mfa-cancel", {}).catch(() => undefined);
    router.replace("/login");
    router.refresh();
  }

  function changeStage(next: "verify" | "recovery") {
    setCode("");
    setError("");
    setSetup(undefined);
    setStage(next);
  }

  const enrolling = stage === "enroll" || stage === "codes";
  const recovering = stage === "recovery";
  const steps = enrolling
    ? [
        "Add your authenticator",
        "Verify your first code",
        "Save recovery codes",
      ]
    : recovering
      ? [
          "Find a recovery code",
          "Set up a new authenticator",
          "Save new recovery codes",
        ]
      : [
          "Open your authenticator",
          "Enter your current code",
          "Continue to your account",
        ];
  const currentStep = stage === "codes" ? 2 : stage === "verify" ? 1 : 0;
  const title =
    stage === "enroll"
      ? "Set up your authenticator"
      : stage === "codes"
        ? "Your backup plan, ready."
        : recovering
          ? "Let’s get you back in."
          : stage === "loading"
            ? "Getting things ready…"
            : "Good to have you back.";
  const description =
    stage === "enroll"
      ? "Connect an authenticator app, then enter its code below to finish setup."
      : stage === "codes"
        ? "Save these recovery codes before you continue. They’re only shown once."
        : recovering
          ? "Use one of the recovery codes you saved when you set up your account."
          : "Enter the six-digit code from your authenticator app to finish signing in.";
  const validCode = recovering
    ? /^[A-Fa-f0-9]{8}(-[A-Fa-f0-9]{8}){3}$/.test(code)
    : /^[0-9]{6}$/.test(code);

  return (
    <div className={`customer-shell ${styles.page}`}>
      <header className="product-header product-container">
        <Brand />
        <Link className="product-text-link" href="/">
          Back to home <span aria-hidden="true">↗</span>
        </Link>
      </header>
      <main className={`product-container ${styles.layout}`}>
        <aside className={styles.story} aria-labelledby="security-heading">
          <span className={styles.storyIcon}>
            <ProductIcon name="shield" />
          </span>
          <p className={styles.eyebrow}>A LITTLE EXTRA PEACE OF MIND</p>
          <h2 id="security-heading">
            Your account.
            <br />
            <span>In safe hands.</span>
          </h2>
          <p>
            Your bookings and saved details deserve an extra layer of
            protection.
          </p>
          <ol className={styles.steps} aria-label="Verification steps">
            {steps.map((step, index) => (
              <li
                key={step}
                aria-current={index === currentStep ? "step" : undefined}
                data-complete={index < currentStep}
              >
                <span>
                  {index < currentStep ? (
                    <ProductIcon name="check" />
                  ) : (
                    `0${index + 1}`
                  )}
                </span>
                {step}
              </li>
            ))}
          </ol>
          <div className={styles.storyNote}>
            <ProductIcon name="shield" />
            <p>
              Only enter your verification codes here. HVACLine will never ask
              you to share them in a call or chat.
            </p>
          </div>
        </aside>
        <section className={styles.card} aria-labelledby="mfa-title">
          <div className={styles.cardHeading}>
            <span className={styles.cardIcon}>
              <ProductIcon name={stage === "codes" ? "check" : "shield"} />
            </span>
            <span className={styles.smallLabel}>ACCOUNT SECURITY</span>
            <span className={styles.required}>
              {stage === "codes" ? "Verified" : "Required"}
            </span>
          </div>
          <h1 id="mfa-title">{title}</h1>
          {stage !== "loading" && (
            <p className={styles.description}>{description}</p>
          )}
          {stage === "loading" && !error && (
            <div className={styles.loading} role="status">
              Preparing secure verification…
            </div>
          )}
          {stage === "enroll" && setup && <AuthenticatorSetup setup={setup} />}
          {stage === "codes" ? (
            <div className={styles.backup}>
              <ul
                className={styles.recoveryCodes}
                aria-label="One-time recovery codes"
              >
                {codes.map((item) => (
                  <li key={item}>
                    <code>{item}</code>
                  </li>
                ))}
              </ul>
              <p className={styles.help}>
                Store these somewhere private, separate from your password. Each
                code can be used once to replace a lost authenticator.
              </p>
              <label className={styles.savedCheckbox}>
                <input
                  type="checkbox"
                  checked={savedCodes}
                  onChange={(event) => setSavedCodes(event.target.checked)}
                />
                <span>I saved my recovery codes somewhere safe.</span>
              </label>
              <button
                type="button"
                className={`product-button ${styles.submit}`}
                disabled={!savedCodes}
                onClick={() => {
                  setCodes([]);
                  router.replace("/book");
                  router.refresh();
                }}
              >
                Continue to my account <ProductIcon name="arrow" />
              </button>
            </div>
          ) : (
            stage !== "loading" && (
              <form
                className={styles.form}
                onSubmit={(event) => void submit(event)}
                aria-busy={busy}
              >
                <label className={styles.inputLabel} htmlFor="mfa-code">
                  {recovering ? "Your recovery code" : "Verification code"}
                </label>
                <input
                  className={
                    recovering ? styles.recoveryInput : styles.codeInput
                  }
                  id="mfa-code"
                  name="code"
                  value={code}
                  onChange={(event) =>
                    setCode(
                      recovering
                        ? event.target.value
                        : event.target.value.replace(/\D/g, "").slice(0, 6),
                    )
                  }
                  autoComplete={recovering ? "off" : "one-time-code"}
                  inputMode={recovering ? "text" : "numeric"}
                  pattern={
                    recovering
                      ? "[A-Fa-f0-9]{8}(-[A-Fa-f0-9]{8}){3}"
                      : "[0-9]{6}"
                  }
                  minLength={recovering ? 35 : 6}
                  maxLength={recovering ? 35 : 6}
                  placeholder={
                    recovering
                      ? "xxxxxxxx-xxxxxxxx-xxxxxxxx-xxxxxxxx"
                      : "000000"
                  }
                  aria-describedby={`mfa-code-help${error ? " mfa-error" : ""}`}
                  aria-invalid={error ? true : undefined}
                  autoCapitalize="none"
                  spellCheck={false}
                  required
                  disabled={busy}
                />
                <p className={styles.help} id="mfa-code-help">
                  {recovering
                    ? "After this code is accepted, you’ll set up and verify a replacement authenticator."
                    : "Use the current code shown for HVACLine AI. It refreshes every 30 seconds."}
                </p>
                {error && (
                  <p id="mfa-error" className={styles.error} role="alert">
                    {error}
                  </p>
                )}
                <button
                  className={`product-button ${styles.submit}`}
                  type="submit"
                  disabled={busy || !validCode}
                >
                  {busy
                    ? "Verifying…"
                    : recovering
                      ? "Continue to replacement setup"
                      : "Verify & continue"}
                  {!busy && <ProductIcon name="arrow" />}
                </button>
                {stage === "verify" && (
                  <button
                    className={styles.textButton}
                    type="button"
                    disabled={busy}
                    onClick={() => changeStage("recovery")}
                  >
                    Lost access to your app? Use a recovery code
                  </button>
                )}
                {recovering && (
                  <button
                    className={styles.textButton}
                    type="button"
                    disabled={busy}
                    onClick={() => changeStage("verify")}
                  >
                    Use my authenticator instead
                  </button>
                )}
              </form>
            )
          )}
          {stage === "loading" && error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
          {stage !== "codes" && (
            <div className={styles.cancel}>
              <button
                className={styles.textButton}
                type="button"
                disabled={busy}
                onClick={() => void cancel()}
              >
                Cancel and sign in again
              </button>
            </div>
          )}
          <p className={styles.privacy}>
            <ProductIcon name="shield" />
            Protected with authenticator verification.
          </p>
        </section>
      </main>
      <footer className={`product-container ${styles.footer}`}>
        Your next appointment starts with a secure sign-in.
      </footer>
    </div>
  );
}
