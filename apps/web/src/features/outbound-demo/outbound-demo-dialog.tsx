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
import {
  type DemoCall,
  type DemoScenario,
  isDemoCall,
  scenarios,
  UUID_PATTERN,
} from "./contracts";

const STORAGE_KEY = "hvacline-outbound-request-v1";
const TriggerContext = createContext<RefObject<HTMLButtonElement | null> | null>(
  null,
);

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
  const [available, setAvailable] = useState(false);
  const [phone, setPhone] = useState("");
  const [scenario, setScenario] = useState<DemoScenario>("cooling");
  const [consent, setConsent] = useState(false);
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
    let cancelled = false;
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
    void fetch("/api/outbound-demo", {
      cache: "no-store",
      signal: AbortSignal.timeout(45_000),
    })
      .then((response) => response.json())
      .then((data: unknown) => {
        if (
          !cancelled &&
          typeof data === "object" &&
          data !== null &&
          "available" in data &&
          data.available === true
        ) {
          setAvailable(true);
          if (!requestId.current)
            setMessage(
              "Private preview · approved numbers only · one call, up to three minutes.",
            );
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [checkStatus]);

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

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current || locked || !available || !consent) return;
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
        }),
      });
      const data: unknown = await response.json();
      if (!response.ok) {
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
      <Dialog.Root>
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
                <Dialog.Title>Have Line call you.</Dialog.Title>
                <Dialog.Description>
                  Try our AI voice agent with an HVAC conversation. Enter your
                  number and choose what you’d like to talk about.
                </Dialog.Description>
              </header>
              <form
                className="outbound-demo-form"
                onSubmit={submit}
                aria-busy={busy}
              >
                <label htmlFor="outbound-phone">Your phone number</label>
                <input
                  ref={phoneInput}
                  id="outbound-phone"
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="+12025550123"
                  pattern="\+[1-9][0-9]{7,14}"
                  maxLength={16}
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  required
                  disabled={locked}
                  aria-describedby="outbound-phone-help"
                />
                <p id="outbound-phone-help" className="outbound-demo-help">
                  Include your country code, such as +1 for the US. When available,
                  the private preview supports owner-approved numbers.
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
                  disabled={!available || !consent || locked || busy}
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
                <Link className="outbound-demo-browser" href="/book">
                  Prefer your browser? Try Voice <span aria-hidden="true">↗</span>
                </Link>
              </form>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </TriggerContext.Provider>
  );
}
