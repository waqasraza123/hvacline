"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import {
  type FormEvent,
  type ReactNode,
  type RefObject,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { ProductIcon, VoiceSymbol } from "@/components/product-icons";
import { authPageHref } from "@/features/customer/auth-continuation";
import {
  type DemoCall,
  type DemoScenario,
  type SmsChallenge,
  isDemoCall,
  isSmsChallenge,
  scenarios,
  UUID_PATTERN,
} from "./contracts";

const STORAGE_KEY = "hvacline-outbound-request-v1";
const TriggerContext = createContext<RefObject<HTMLButtonElement | null> | null>(
  null,
);

function signInRequired(value: unknown): boolean {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof value.error === "object" &&
    value.error !== null &&
    "code" in value.error &&
    value.error.code === "CALLBACK_SIGN_IN_REQUIRED"
  );
}

export function OutboundDemoTrigger({
  children = "Request an AI demo call",
  className = "product-button",
}: {
  children?: ReactNode;
  className?: string;
}) {
  const trigger = useContext(TriggerContext);
  if (!trigger) throw new Error("Demo call triggers require OutboundDemoDialog");
  return (
    <Dialog.Trigger
      className={`outbound-demo-trigger ${className}`}
      onClick={(event) => {
        trigger.current = event.currentTarget;
      }}
    >
      <ProductIcon name="phone" />
      {children}
      <ProductIcon name="arrow" />
    </Dialog.Trigger>
  );
}

export function OutboundDemoDialog({ children }: { children: ReactNode }) {
  const trigger = useRef<HTMLButtonElement | null>(null);
  const phoneInput = useRef<HTMLInputElement | null>(null);
  const signInLink = useRef<HTMLAnchorElement | null>(null);
  const availabilityVersion = useRef(0);
  const [open, setOpen] = useState(false);
  const [authentication, setAuthentication] = useState<
    "loading" | "authenticated" | "required" | "unavailable"
  >("loading");
  const [available, setAvailable] = useState(false);
  const [phone, setPhone] = useState("");
  const [scenario, setScenario] = useState<DemoScenario>("cooling");
  const [consent, setConsent] = useState(false);
  const [smsConsent, setSmsConsent] = useState(false);
  const [smsCode, setSmsCode] = useState("");
  const [verification, setVerification] = useState<SmsChallenge | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [smsMessage, setSmsMessage] = useState("");
  const smsPending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [locked, setLocked] = useState(false);
  const [call, setCall] = useState<DemoCall | null>(null);
  const [message, setMessage] = useState(
    "Phone demos aren’t available right now. You can explore the form or try Line in your browser.",
  );
  const requestId = useRef<string | null>(null);
  const submitting = useRef(false);
  const checking = useRef(false);
  const callId = call?.id;
  const callTerminal = call?.terminal;
  const callStatus = call?.status;

  const refreshAvailability = useCallback(async () => {
    const version = ++availabilityVersion.current;
    setAuthentication("loading");
    setAvailable(false);
    try {
      const response = await fetch("/api/outbound-demo", {
        cache: "no-store",
        signal: AbortSignal.timeout(45_000),
      });
      const data: unknown = await response.json();
      if (version !== availabilityVersion.current) return;
      if (signInRequired(data)) {
        setAuthentication("required");
        setConsent(false);
        return;
      }
      if (
        !response.ok ||
        typeof data !== "object" ||
        data === null ||
        !("available" in data) ||
        typeof data.available !== "boolean"
      )
        throw new Error("Unavailable");
      setAuthentication("authenticated");
      setAvailable(data.available);
      if (!requestId.current)
        setMessage(
          data.available
            ? "One-time AI demo · eligible numbers only · up to three minutes."
            : "Phone demos aren’t available right now. You can explore the form or try Line in your browser.",
        );
    } catch {
      if (version === availabilityVersion.current) setAuthentication("unavailable");
    }
  }, []);

  const checkStatus = useCallback(async () => {
    if (!requestId.current || submitting.current || checking.current) return;
    checking.current = true;
    setBusy(true);
    try {
      const response = await fetch(
        `/api/outbound-demo?request_id=${requestId.current}`,
        { cache: "no-store", signal: AbortSignal.timeout(45_000) },
      );
      const data: unknown = await response.json();
      if (signInRequired(data)) {
        setAuthentication("required");
        setAvailable(false);
        setConsent(false);
        setMessage("Sign in to check your saved callback request.");
        return;
      }
      if (!response.ok || !isDemoCall(data)) throw new Error("Unavailable");
      setCall(data);
      setMessage(data.message);
    } catch {
      setMessage(
        "The call outcome is unconfirmed. Contact the demo owner before requesting another call.",
      );
    } finally {
      checking.current = false;
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      if (saved && UUID_PATTERN.test(saved)) {
        requestId.current = saved;
        setLocked(true);
        void checkStatus();
      }
    } catch {
      /* A request still stays locked in memory when storage is unavailable. */
    }
    if (new URLSearchParams(window.location.search).get("demo_call") === "1")
      setOpen(true);
    void refreshAvailability();
    return () => {
      availabilityVersion.current += 1;
    };
  }, [checkStatus, refreshAvailability]);

  useEffect(() => {
    if (!open) return;
    if (authentication === "required") signInLink.current?.focus();
    else if (authentication === "authenticated" && !locked)
      phoneInput.current?.focus();
  }, [authentication, locked, open]);

  useEffect(() => {
    if (!callId || callTerminal || callStatus === "unknown") return;
    const started = Date.now();
    const timer = window.setInterval(() => {
      if (Date.now() - started > 4 * 60_000) {
        window.clearInterval(timer);
        setMessage(
          "Final call status is delayed. Check status or contact the demo owner before retrying.",
        );
        return;
      }
      void checkStatus();
    }, 10_000);
    return () => window.clearInterval(timer);
  }, [callId, callTerminal, callStatus, checkStatus]);

  useEffect(() => {
    if (!verification || locked) return;
    const timer = window.setTimeout(() => {
      setVerification(null);
      setSmsCode("");
      setConsent(false);
      setSmsMessage("Your code expired. Request a new verification text.");
    }, Math.max(0, Date.parse(verification.expires_at) - Date.now()));
    return () => window.clearTimeout(timer);
  }, [verification, locked]);

  async function verifyPhone(action: "send_code" | "verify_code") {
    if (
      smsPending.current || locked || busy || !available ||
      authentication !== "authenticated" ||
      (action === "send_code"
        ? !smsConsent || !/^\+1[0-9]{10}$/.test(phone.trim())
        : !verification || !/^[0-9]{6}$/.test(smsCode))
    ) return;
    smsPending.current = true;
    setVerifying(true);
    setSmsMessage(
      action === "send_code"
        ? "Requesting your verification text…"
        : "Checking your code…",
    );
    try {
      const response = await fetch("/api/outbound-demo", {
        method: "POST",
        signal: AbortSignal.timeout(45_000),
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          action === "send_code"
            ? {
                action,
                phone_number: phone.trim(),
                sms_consent: true,
                sms_consent_version: "outbound-sms-v1",
              }
            : { action, challenge_id: verification?.challenge_id, code: smsCode },
        ),
      });
      const value: unknown = await response.json();
      if (signInRequired(value)) {
        setAuthentication("required");
        setAvailable(false);
        setVerification(null);
        setConsent(false);
        setSmsConsent(false);
        setSmsCode("");
        return;
      }
      if (!response.ok || !isSmsChallenge(value)) {
        const error =
          typeof value === "object" && value !== null && "error" in value
            ? value.error : null;
        setSmsMessage(
          typeof error === "object" && error !== null && "message" in error &&
          typeof error.message === "string"
            ? error.message
            : "Text verification is unavailable. Please try later.",
        );
        if (response.status === 403) setVerification(null);
        return;
      }
      setVerification(value);
      setSmsCode("");
      setSmsMessage(
        value.verified
          ? "Mobile number verified. You can now request your demo call."
          : "Enter the six-digit code from your text before it expires.",
      );
    } catch {
      setSmsMessage("Text verification is unconfirmed. Wait a minute before requesting another code.");
    } finally {
      smsPending.current = false;
      setVerifying(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      submitting.current ||
      locked ||
      !available ||
      !consent ||
      verifying ||
      !verification?.verified ||
      Date.parse(verification.expires_at) <= Date.now() ||
      authentication !== "authenticated"
    )
      return;
    submitting.current = true;
    setBusy(true);
    setLocked(true);
    requestId.current = crypto.randomUUID();
    try {
      sessionStorage.setItem(STORAGE_KEY, requestId.current);
    } catch {
      /* Optional recovery across reloads. */
    }
    setMessage("Requesting your one-time call. Keep your phone nearby.");
    try {
      const response = await fetch("/api/outbound-demo", {
        method: "POST",
        signal: AbortSignal.timeout(45_000),
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: requestId.current,
          phone_number: phone.trim(),
          scenario,
          consent: true,
          consent_version: "outbound-demo-v1",
          phone_verification_id: verification.challenge_id,
        }),
      });
      const data: unknown = await response.json();
      if (!response.ok) {
        if (signInRequired(data)) {
          setAuthentication("required");
          setAvailable(false);
        }
        const error =
          typeof data === "object" && data !== null && "error" in data
            ? data.error
            : null;
        setMessage(
          typeof error === "object" &&
            error !== null &&
            "message" in error &&
            typeof error.message === "string"
            ? error.message
            : "The call outcome is unconfirmed. Please check its status.",
        );
        if (
          typeof error === "object" && error !== null && "code" in error &&
          error.code === "DEMO_PHONE_VERIFICATION_REQUIRED"
        ) {
          setVerification(null);
          setSmsCode("");
        }
        if (
          typeof data === "object" &&
          data !== null &&
          "request_not_created" in data &&
          data.request_not_created === true
        ) {
          requestId.current = null;
          setLocked(false);
          setConsent(false);
          try {
            sessionStorage.removeItem(STORAGE_KEY);
          } catch {
            // Recovery storage is optional.
          }
        }
        return;
      }
      if (!isDemoCall(data)) throw new Error("Invalid response");
      setCall(data);
      setMessage(data.message);
      setPhone("");
    } catch {
      setMessage(
        "The connection was interrupted. Check call status before requesting another call.",
      );
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return (
    <TriggerContext.Provider value={trigger}>
      <Dialog.Root
        open={open}
        onOpenChange={(nextOpen) => {
          setOpen(nextOpen);
          if (nextOpen) void refreshAvailability();
        }}
      >
        <div className="product-site">{children}</div>
        <Dialog.Portal>
          <Dialog.Overlay className="outbound-demo-overlay" />
          <Dialog.Content
            className="product-site outbound-demo-dialog"
            onOpenAutoFocus={(event) => {
              if (phoneInput.current && !phoneInput.current.disabled) {
                event.preventDefault();
                phoneInput.current.focus();
              }
            }}
            onCloseAutoFocus={(event) => {
              if (trigger.current?.isConnected) {
                event.preventDefault();
                trigger.current.focus();
              }
            }}
          >
            <Dialog.Close
              className="outbound-demo-close"
              aria-label="Close demo call form"
            >
              <ProductIcon name="close" />
            </Dialog.Close>
            <aside className="outbound-demo-agent">
              <div className="outbound-demo-agent-mark">
                <VoiceSymbol />
              </div>
              <p className="outbound-demo-agent-name">Meet Line.</p>
              <p className="outbound-demo-agent-copy">
                Your AI receptionist.
                <br />
                A real conversation, on your phone.
              </p>
              <ol className="outbound-demo-steps">
                <li>
                  <span>01</span> Pick an HVAC scenario
                </li>
                <li>
                  <span>02</span> Answer Line’s call
                </li>
                <li>
                  <span>03</span> Speak naturally. Try an interruption.
                </li>
              </ol>
              <div className="outbound-demo-duration">
                <ProductIcon name="clock" />
                <span>A short demo · up to 3 minutes</span>
              </div>
            </aside>
            <div className="outbound-demo-dialog-body">
              <header>
                <p className="product-eyebrow">HEAR LINE IN ACTION</p>
                <Dialog.Title>
                  {authentication === "authenticated"
                    ? "Have Line call you."
                    : authentication === "required"
                      ? "Sign in for your demo call."
                      : authentication === "loading"
                        ? "Just a moment…"
                        : "Let’s check your sign-in."}
                </Dialog.Title>
                <Dialog.Description>
                  {authentication === "authenticated"
                    ? "Try our AI voice agent with an HVAC conversation. Enter your number and choose what you’d like to talk about."
                    : "Sign in to your HVACLine account with your authenticator. Then return here to choose your phone number and agree to one demo call."}
                </Dialog.Description>
              </header>
              {authentication === "authenticated" ? (
                <form
                  className="outbound-demo-form"
                  onSubmit={submit}
                  aria-busy={busy}
                >
                  <label htmlFor="outbound-phone">Your US mobile number</label>
                  <input
                    ref={phoneInput}
                    id="outbound-phone"
                    type="tel"
                    inputMode="tel"
                    autoComplete="tel"
                    placeholder="+12025550123"
                    pattern="\+1[0-9]{10}"
                    maxLength={12}
                    value={phone}
                    onChange={(event) => {
                      setPhone(event.target.value);
                      setVerification(null);
                      setSmsCode("");
                      setSmsConsent(false);
                      setConsent(false);
                      setSmsMessage("");
                    }}
                    required
                    disabled={locked || verifying}
                    aria-describedby="outbound-phone-help"
                  />
                  <p id="outbound-phone-help" className="outbound-demo-help">
                    Include +1 and the area code. We’ll verify your mobile number
                    by text before calling. Landline and internet phone numbers
                    aren’t supported.
                  </p>
                  <label className="outbound-demo-consent">
                    <input
                      type="checkbox"
                      checked={smsConsent}
                      onChange={(event) => setSmsConsent(event.target.checked)}
                      disabled={locked || verifying || verification?.verified}
                    />
                    <span>
                      I agree to receive a verification text at this number.
                      Message and data rates may apply.
                    </span>
                  </label>
                  {!verification?.verified && (
                    <button
                      type="button"
                      className="outbound-demo-check"
                      disabled={
                        !available || !smsConsent || locked || verifying || busy ||
                        !/^\+1[0-9]{10}$/.test(phone.trim())
                      }
                      onClick={() => void verifyPhone("send_code")}
                    >
                      {verifying
                        ? "Please wait…"
                        : verification ? "Send a new code" : "Text me a code"}
                    </button>
                  )}
                  {verification && !verification.verified && (
                    <>
                      <label htmlFor="outbound-sms-code">Text verification code</label>
                      <input
                        id="outbound-sms-code"
                        type="text"
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        maxLength={6}
                        pattern="[0-9]{6}"
                        value={smsCode}
                        onChange={(event) => setSmsCode(event.target.value)}
                        disabled={locked || verifying}
                        aria-describedby="outbound-sms-status"
                      />
                      <button
                        type="button"
                        className="outbound-demo-check"
                        disabled={locked || verifying || !/^[0-9]{6}$/.test(smsCode)}
                        onClick={() => void verifyPhone("verify_code")}
                      >
                        Verify mobile number
                      </button>
                    </>
                  )}
                  <p
                    id="outbound-sms-status"
                    className="outbound-demo-help"
                    role="status"
                  >
                    {smsMessage}
                  </p>
                  <label htmlFor="outbound-scenario">Try a conversation</label>
                  <select
                    id="outbound-scenario"
                    value={scenario}
                    onChange={(event) =>
                      setScenario(event.target.value as DemoScenario)
                    }
                    disabled={locked}
                  >
                    {Object.entries(scenarios).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <label className="outbound-demo-consent">
                    <input
                      type="checkbox"
                      checked={consent}
                      onChange={(event) => setConsent(event.target.checked)}
                      required
                      disabled={locked}
                    />
                    <span>
                      I control this number and agree to one AI demo call from Line
                      via ElevenLabs and Telnyx. Call audio is processed to provide
                      the conversation. I can end it at any time; no marketing or
                      automatic redial.
                    </span>
                  </label>
                  <button
                    className="product-button"
                    type="submit"
                    disabled={
                      !available || !consent || !verification?.verified ||
                      locked || busy || verifying
                    }
                  >
                    {busy
                      ? "Please wait…"
                      : locked
                        ? "Call already requested"
                        : available
                          ? "Request my demo call"
                          : "Phone demos unavailable"}
                    <ProductIcon name="arrow" />
                  </button>
                  <p className="outbound-demo-status" role="status" aria-live="polite">
                    {message}
                  </p>
                  <p className="outbound-demo-fine">
                    A fictional business. A real telephone call. No real appointment,
                    service quote or follow-up marketing.
                  </p>
                  {locked && (
                    <>
                      <button
                        className="outbound-demo-check"
                        type="button"
                        onClick={() => void checkStatus()}
                        disabled={busy}
                      >
                        Check call status
                      </button>
                      <p className="outbound-demo-help">
                        Closing this window won’t cancel a requested call.
                      </p>
                    </>
                  )}
                </form>
              ) : (
                <div className="outbound-demo-signin">
                  {authentication === "loading" ? (
                    <p role="status">Checking your sign-in…</p>
                  ) : authentication === "required" ? (
                    <>
                      <p className="outbound-demo-help">
                        Your phone number and call consent come after sign-in.
                      </p>
                      <Link
                        ref={signInLink}
                        className="product-button"
                        href={authPageHref("/login", "demo-call")}
                      >
                        Sign in and continue <ProductIcon name="arrow" />
                      </Link>
                      <Link
                        className="outbound-demo-browser"
                        href={authPageHref("/signup", "demo-call")}
                      >
                        New here? Create an account
                      </Link>
                    </>
                  ) : (
                    <>
                      <p role="status">
                        We couldn’t check your sign-in. Please try again.
                      </p>
                      <button
                        type="button"
                        className="product-button"
                        onClick={() => void refreshAvailability()}
                      >
                        Try again <ProductIcon name="arrow" />
                      </button>
                    </>
                  )}
                </div>
              )}
              <Link className="outbound-demo-browser" href="/book">
                Prefer your browser? Try Voice <span aria-hidden="true">↗</span>
              </Link>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </TriggerContext.Provider>
  );
}
