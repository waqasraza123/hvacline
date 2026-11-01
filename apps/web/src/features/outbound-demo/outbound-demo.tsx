"use client";

import Link from "next/link";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { ProductIcon, VoiceSymbol } from "@/components/product-icons";
import { CallingLaunchDate } from "./calling-launch";
import {
  type DemoCall,
  type DemoScenario,
  isDemoCall,
  scenarios,
  UUID_PATTERN,
} from "./contracts";

const STORAGE_KEY = "hvacline-outbound-request-v1";

export function OutboundDemo() {
  const [available, setAvailable] = useState(false);
  const [phone, setPhone] = useState("");
  const [scenario, setScenario] = useState<DemoScenario>("cooling");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [locked, setLocked] = useState(false);
  const [call, setCall] = useState<DemoCall | null>(null);
  const [message, setMessage] = useState(
    "Telephone demos are in private testing. Only numbers approved by the demo owner can receive a call.",
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
    <section
      id="call-me"
      className="outbound-demo product-container"
      aria-labelledby="outbound-title"
    >
      <div className="outbound-demo-intro">
        <p className="product-eyebrow">
          COMING <CallingLaunchDate />
        </p>
        <h2 id="outbound-title">
          Inbound &amp;
          <br />
          <span>outbound calling.</span>
        </h2>
        <p>
          Call Line from your phone, or have Line call you. Natural HVAC
          conversations, with the same AI receptionist.
        </p>
        <div className="outbound-demo-voice" aria-hidden="true">
          <VoiceSymbol />
          <span>Line · AI receptionist</span>
        </div>
      </div>
      {available || locked ? (
        <form className="outbound-demo-form" onSubmit={submit}>
          <div className="outbound-demo-heading">
            <ProductIcon name="phone" />
            <strong>Your one-time demo</strong>
            <span>3 min max</span>
          </div>
          <label htmlFor="outbound-phone">Your phone number</label>
          <input
            id="outbound-phone"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            placeholder="+ country code and number"
            pattern="\+[1-9][0-9]{7,14}"
            maxLength={16}
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            required
            disabled={!available || locked}
            aria-describedby="outbound-phone-help"
          />
          <p id="outbound-phone-help" className="outbound-demo-help">
            Use international format. Private preview is limited to
            owner-approved numbers.
          </p>
          <label htmlFor="outbound-scenario">Try a conversation</label>
          <select
            id="outbound-scenario"
            value={scenario}
            onChange={(event) =>
              setScenario(event.target.value as DemoScenario)
            }
            disabled={!available || locked}
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
              disabled={!available || locked}
            />
            <span>
              I control this number and agree to one AI demo call from Line via
              ElevenLabs and Telnyx. Call audio is processed to provide the
              conversation. I can end it at any time; no marketing or automatic
              redial.
            </span>
          </label>
          <button
            className="product-button"
            type="submit"
            disabled={!available || !consent || locked || busy}
          >
            {busy ? "Please wait…" : "Have Line Call Me"}
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
            <button
              className="outbound-demo-check"
              type="button"
              onClick={() => void checkStatus()}
              disabled={busy}
            >
              Check call status
            </button>
          )}
          <Link className="outbound-demo-browser" href="/book">
            Prefer your browser? Try Voice <span aria-hidden="true">↗</span>
          </Link>
        </form>
      ) : (
        <div className="calling-preview">
          <div className="calling-preview-date">
            <ProductIcon name="calendar" />
            <span>
              Coming <CallingLaunchDate />
            </span>
          </div>
          <article>
            <ProductIcon name="phone" />
            <div>
              <h3>Inbound calling</h3>
              <p>
                Pick up your phone and speak with Line about your HVAC needs.
              </p>
            </div>
          </article>
          <article>
            <ProductIcon name="phone" />
            <div>
              <h3>Outbound calling</h3>
              <p>
                Request a call from Line and try the conversation on your phone.
              </p>
            </div>
          </article>
          <Link className="product-button" href="/book">
            Try browser Voice today <ProductIcon name="arrow" />
          </Link>
        </div>
      )}
    </section>
  );
}
