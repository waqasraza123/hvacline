"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { ProductIcon, VoiceSymbol } from "@/components/product-icons";
import {
  clearHomepageHandoff,
  readHomepageHandoff,
  saveHomepageHandoff,
} from "./handoff";
import styles from "./homepage-chat.module.css";

type State =
  "loading" | "ready" | "used" | "busy" | "authenticated" | "unavailable";
const suggestions = [
  "Can you help with AC repair?",
  "How does booking work?",
  "What services do you offer?",
];

export function HomepageChatLink({
  children,
  className,
  label,
}: {
  children: ReactNode;
  className: string;
  label?: string;
}) {
  return (
    <a
      href="#try-line"
      className={className}
      aria-label={label}
      onClick={(event) => {
        const panel = document.getElementById("try-line");
        const action =
          document.getElementById("homepage-line-voice") ??
          document.getElementById("homepage-line-message");
        if (panel && action) {
          event.preventDefault();
          panel.scrollIntoView({
            behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
              .matches
              ? "instant"
              : "smooth",
            block: "center",
          });
          action.focus({ preventScroll: true });
        }
      }}
    >
      {children}
    </a>
  );
}

export function HomepageChat() {
  const router = useRouter();
  const [mode, setMode] = useState<"voice" | "text">("voice");
  const [state, setState] = useState<State>("loading");
  const [draft, setDraft] = useState("");
  const [exchange, setExchange] = useState({ message: "", reply: "" });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [storageAvailable, setStorageAvailable] = useState(true);
  const [restored, setRestored] = useState(false);
  const input = useRef<HTMLTextAreaElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const sending = useRef(false);
  const mounted = useRef(false);
  const attempt = useRef<{ id: string; message: string } | null>(null);
  const messages = useRef<HTMLDivElement>(null);
  const statusVersion = useRef(0);

  async function refreshStatus() {
    const version = ++statusVersion.current;
    try {
      const response = await fetch("/api/homepage-chat", {
        cache: "no-store",
        signal: AbortSignal.timeout(15_000),
      });
      const data: unknown = await response.json();
      if (!mounted.current || version !== statusVersion.current) return;
      if (
        typeof data !== "object" ||
        data === null ||
        !("state" in data) ||
        !["ready", "used", "busy", "authenticated", "unavailable"].includes(
          String(data.state),
        )
      )
        throw new Error("Unavailable");
      setState(data.state as State);
    } catch {
      if (mounted.current && version === statusVersion.current)
        setState("unavailable");
    }
  }

  useEffect(() => {
    mounted.current = true;
    const saved = readHomepageHandoff();
    if (saved) {
      setExchange({ message: saved.message, reply: saved.reply });
      setDraft(saved.pendingMessage);
    }
    setRestored(true);
    void refreshStatus();
    const refresh = () => {
      if (!sending.current) void refreshStatus();
    };
    window.addEventListener("focus", refresh);
    return () => {
      mounted.current = false;
      window.removeEventListener("focus", refresh);
    };
  }, []);

  useEffect(() => {
    if (restored) {
      if (draft || exchange.message)
        setStorageAvailable(
          saveHomepageHandoff(exchange.message, exchange.reply, draft),
        );
      else clearHomepageHandoff();
    }
  }, [draft, exchange, restored]);

  useEffect(() => {
    if (messages.current)
      messages.current.scrollTop = messages.current.scrollHeight;
  }, [exchange, pending]);

  function openGate() {
    setStorageAvailable(
      saveHomepageHandoff(exchange.message, exchange.reply, draft),
    );
    if (!dialog.current?.open) {
      dialog.current?.showModal();
      dialog.current?.querySelector<HTMLAnchorElement>("a")?.focus();
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current || !draft.trim()) return;
    if (state === "authenticated") {
      saveHomepageHandoff(exchange.message, exchange.reply, draft);
      router.push("/book");
      return;
    }
    if (state === "used") {
      openGate();
      return;
    }
    if (state !== "ready") return;
    sending.current = true;
    statusVersion.current += 1;
    setPending(true);
    setError("");
    const message = draft.trim();
    if (!attempt.current || attempt.current.message !== message)
      attempt.current = { id: crypto.randomUUID(), message };
    try {
      const response = await fetch("/api/homepage-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          request_id: attempt.current.id,
          ai_disclosure_accepted: true,
        }),
        signal: AbortSignal.timeout(35_000),
      });
      const data: unknown = await response.json();
      if (!mounted.current) return;
      if (
        typeof data === "object" &&
        data !== null &&
        "state" in data &&
        data.state === "authenticated"
      ) {
        saveHomepageHandoff(exchange.message, exchange.reply, draft);
        router.push("/book");
        return;
      }
      if (!response.ok) {
        const failure =
          typeof data === "object" &&
          data !== null &&
          "error" in data &&
          typeof data.error === "object" &&
          data.error !== null
            ? data.error
            : {};
        if ("code" in failure && failure.code === "HOMEPAGE_SIGN_IN_REQUIRED") {
          setState("used");
          openGate();
          return;
        }
        throw new Error(
          "message" in failure && typeof failure.message === "string"
            ? failure.message
            : "Line couldn’t reply. Please retry or sign in.",
        );
      }
      if (
        typeof data !== "object" ||
        data === null ||
        !("reply" in data) ||
        typeof data.reply !== "string" ||
        !data.reply.trim() ||
        data.reply.length > 4000
      )
        throw new Error(
          "Line’s reply could not be read. Please sign in to continue.",
        );
      const completed = { message, reply: data.reply };
      setExchange(completed);
      setDraft("");
      setState("used");
      setStorageAvailable(
        saveHomepageHandoff(completed.message, completed.reply, ""),
      );
    } catch (failure) {
      if (mounted.current) {
        setError(
          failure instanceof Error &&
            failure.name !== "TypeError" &&
            failure.name !== "TimeoutError"
            ? failure.message
            : "Line’s connection was interrupted. Your message is kept.",
        );
        await refreshStatus();
      }
    } finally {
      sending.current = false;
      if (mounted.current) setPending(false);
    }
  }

  const canSubmit =
    !pending && ["ready", "used", "authenticated"].includes(state);
  return (
    <section
      id="try-line"
      className={styles.panel}
      aria-labelledby="try-line-title"
    >
      <header className={styles.header}>
        <span className={styles.mark}>
          <VoiceSymbol />
        </span>
        <div>
          <h2 id="try-line-title">
            Meet Line<span>Your AI voice receptionist</span>
          </h2>
        </div>
        <span className={styles.badge}>
          <span /> Voice & chat
        </span>
      </header>
      <div
        className={styles.modes}
        role="group"
        aria-label="Try Line by voice or text"
      >
        <button
          type="button"
          aria-pressed={mode === "voice"}
          onClick={() => setMode("voice")}
        >
          <ProductIcon name="mic" /> Voice AI
        </button>
        <button
          type="button"
          aria-pressed={mode === "text"}
          onClick={() => setMode("text")}
        >
          <ProductIcon name="chat" /> Text chat
        </button>
      </div>
      {mode === "voice" ? (
        <div id="homepage-voice-preview" className={styles.voicePreview}>
          <div className={styles.voiceOrb} aria-hidden="true">
            <VoiceSymbol />
          </div>
          <p className={styles.eyebrow}>
            SPEAK NATURALLY. LINE TAKES IT FROM HERE.
          </p>
          <h3>
            Talk it through.
            <br />
            Book with Line.
          </h3>
          <p>Tell Line what you need. Find a time that works.</p>
          <Link
            id="homepage-line-voice"
            className={styles.voiceAction}
            href="/book"
          >
            <ProductIcon name="mic" /> Start voice chat{" "}
            <ProductIcon name="arrow" />
          </Link>
          <p className={styles.voiceHelp}>
            Sign in, then choose Voice to get started.
          </p>
        </div>
      ) : (
        <div id="homepage-text-preview">
          <div
            ref={messages}
            className={styles.messages}
            role="log"
            aria-label="Conversation with Line"
            aria-live="polite"
            aria-relevant="additions text"
          >
            <div className={styles.lineMessage}>
              <span>LINE</span>
              <p>Hi, I’m Line. What can I help you with today?</p>
            </div>
            {exchange.message && (
              <div className={styles.userMessage}>
                <span>YOU</span>
                <p>{exchange.message}</p>
              </div>
            )}
            {exchange.reply && (
              <div className={styles.lineMessage}>
                <span>LINE</span>
                <p>{exchange.reply}</p>
              </div>
            )}
            {pending && (
              <>
                <div className={styles.userMessage}>
                  <span>YOU</span>
                  <p>{draft}</p>
                </div>
                <div className={styles.thinking} role="status">
                  <i />
                  <i />
                  <i />
                  <span>Line is thinking…</span>
                </div>
              </>
            )}
          </div>
          {!exchange.reply && state === "ready" && !pending && (
            <div
              className={styles.suggestions}
              aria-label="Suggested questions"
            >
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => {
                    setDraft(suggestion);
                    input.current?.focus();
                  }}
                >
                  {suggestion}
                  <span>↗</span>
                </button>
              ))}
            </div>
          )}
          {state === "used" && (
            <div className={styles.continuation}>
              <span>
                <ProductIcon name="check" /> Your next step is a conversation
                away.
              </span>
              <button type="button" onClick={openGate}>
                Continue with Line <span>→</span>
              </button>
            </div>
          )}
          <form
            className={styles.form}
            onSubmit={(event) => void submit(event)}
            aria-busy={pending}
          >
            <label className={styles.label} htmlFor="homepage-line-message">
              Message Line
            </label>
            <div className={styles.composer}>
              <textarea
                ref={input}
                id="homepage-line-message"
                value={draft}
                maxLength={1000}
                rows={2}
                disabled={pending}
                aria-describedby="homepage-chat-help"
                placeholder={
                  state === "used"
                    ? "What would you like to ask next?"
                    : "How can Line help you?"
                }
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" &&
                    !event.shiftKey &&
                    !event.nativeEvent.isComposing
                  ) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
              />
              <button
                type="submit"
                disabled={!canSubmit || !draft.trim()}
                aria-label={
                  state === "ready"
                    ? "Send message and agree to AI processing"
                    : "Continue with Line"
                }
              >
                {state === "ready" ? "Send & agree" : "Continue"}
                <ProductIcon name="arrow" />
              </button>
            </div>
            <p id="homepage-chat-help" className={styles.help}>
              {pending
                ? "Getting your reply from Line…"
                : state === "loading"
                  ? "Getting Line ready…"
                  : state === "ready"
                    ? "Try one message. No account needed."
                    : state === "used"
                      ? "Sign in to keep the conversation going."
                      : state === "authenticated"
                        ? "Continue in your booking workspace."
                        : state === "busy"
                          ? "Line is busy. Check availability in a moment, or sign in."
                          : "Line is unavailable here right now. You can still sign in."}
            </p>
            {state === "ready" && (
              <p className={styles.help}>
                Choosing Send &amp; agree accepts AI processing by ElevenLabs.
                Read the details below.
              </p>
            )}
            {state === "ready" && (
              <details className={styles.disclosure}>
                <summary>Send & agree · AI processing details</summary>
                <p>
                  Choosing Send means you agree to AI processing by ElevenLabs
                  and its AI providers. This is text only; your microphone stays
                  off. Audio recording is disabled and zero-day scheduled
                  deletion is configured; provider Zero Retention Mode is not
                  enabled. No request or booking is saved here. This tab keeps
                  your exchange and draft for up to 30 minutes so you can
                  continue after signing in. A cookie remembers your free
                  allowance for 30 days.
                </p>
              </details>
            )}
            {error && (
              <p className={styles.error} role="alert">
                {error}
              </p>
            )}
            {["busy", "unavailable"].includes(state) && (
              <div className={styles.fallback}>
                <button type="button" onClick={() => void refreshStatus()}>
                  Check availability
                </button>
                <Link href="/login">Sign in to continue ↗</Link>
              </div>
            )}
            {!storageAvailable && (
              <p className={styles.help}>
                Browser storage is unavailable. Keep this page open to read your
                conversation.
              </p>
            )}
          </form>
        </div>
      )}
      <footer className={styles.footer}>
        <ProductIcon name="shield" />
        {mode === "voice"
          ? "Microphone access starts only with your permission."
          : "Your microphone stays off. Booking starts after sign-in."}
      </footer>
      <dialog
        ref={dialog}
        className={styles.dialog}
        aria-labelledby="homepage-signin-title"
        aria-describedby="homepage-signin-description"
        onClose={() => input.current?.focus()}
        onClick={(event) => {
          if (event.target === event.currentTarget) dialog.current?.close();
        }}
      >
        <div className={styles.dialogContent}>
          <button
            className={styles.close}
            type="button"
            aria-label="Close sign-in invitation"
            onClick={() => dialog.current?.close()}
          >
            ×
          </button>
          <span className={styles.dialogMark}>
            <VoiceSymbol />
          </span>
          <p className={styles.eyebrow}>LET’S PICK UP FROM HERE</p>
          <h2 id="homepage-signin-title">
            Keep the
            <br />
            conversation going.
          </h2>
          <p id="homepage-signin-description">
            Sign in to continue with Line and book your visit.
            {storageAvailable
              ? " Pick up where you left off."
              : " You can start a new conversation after signing in."}
          </p>
          <Link className={styles.primary} href="/login">
            Sign in to continue <span>→</span>
          </Link>
          <Link className={styles.secondary} href="/signup">
            Create an account <span>↗</span>
          </Link>
          <span className={styles.dialogNote}>
            <ProductIcon name="shield" /> Your bookings. Your details. In one
            place.
          </span>
        </div>
      </dialog>
    </section>
  );
}
