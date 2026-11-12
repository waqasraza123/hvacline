"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  authorizeConversationSession,
  conversationApiPath,
  endConversationSession,
} from "@/features/conversation/api";
import { ElevenLabsConversationAdapter } from "@/features/conversation/elevenlabs-adapter";
import { ChatComposer } from "@/features/conversation/chat-composer";
import { SessionTimer } from "@/features/conversation/session-timer";
import { appendTranscript } from "@/features/conversation/review";
import type {
  ApprovedFaqToolResult,
  ConversationClient,
  ConversationDraft,
  ConversationInputMode,
  ConversationTurn,
} from "@/features/conversation/contracts";
import styles from "./website-voice.module.css";

type Properties = { slug: string; brandName: string; leadCapture: boolean };
const unavailable: ApprovedFaqToolResult = {
  matched: false,
  answer: null,
  fallbackMessage: "Please ask the business team to follow up.",
  source: null,
};

export function WebsiteVoice(properties: Properties) {
  const sessionIdRef = useRef<string | undefined>(undefined);
  const intentionalRef = useRef(false);
  const [transcript, setTranscript] = useState<ConversationTurn[]>([]);
  const [draft, setDraft] = useState<ConversationDraft>({});
  const [disconnected, setDisconnected] = useState(false);
  const [error, setError] = useState("");
  useEffect(
    () => () => {
      if (sessionIdRef.current)
        void endConversationSession(
          "",
          sessionIdRef.current,
          "INTERRUPTED",
          undefined,
          properties.slug,
        ).catch(() => undefined);
    },
    [properties.slug],
  );
  return (
    <ElevenLabsConversationAdapter
      memoryEnabled={false}
      onDisconnect={() => {
        if (!intentionalRef.current) {
          setDisconnected(true);
          setError(
            "The connection ended. Finish this session before starting again.",
          );
        }
      }}
      onError={setError}
      onTranscript={(speaker, text) =>
        setTranscript((current) => appendTranscript(current, speaker, text))
      }
      onDraft={async (next) => {
        setDraft(next);
        return JSON.stringify({
          ok: true,
          saved: false,
          message:
            "Draft only. The customer must finish the conversation and explicitly confirm the inquiry form. No appointment is booked.",
        });
      }}
      onApprovedFaqLookup={async (query) => {
        if (!sessionIdRef.current) return unavailable;
        try {
          const response = await fetch(
            conversationApiPath(
              "",
              `conversation-sessions/${sessionIdRef.current}/approved-faq-lookup`,
              properties.slug,
            ),
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ query }),
              signal: AbortSignal.timeout(10000),
            },
          );
          if (!response.ok) return unavailable;
          const result: unknown = await response.json();
          if (
            !result ||
            typeof result !== "object" ||
            !("matched" in result) ||
            typeof result.matched !== "boolean" ||
            !("answer" in result) ||
            (result.answer !== null && typeof result.answer !== "string") ||
            !("fallback_message" in result) ||
            typeof result.fallback_message !== "string"
          )
            return unavailable;
          return {
            matched: result.matched,
            answer: result.answer,
            fallbackMessage: result.fallback_message,
            source: null,
          };
        } catch {
          return unavailable;
        }
      }}
      onBookingTool={async () =>
        JSON.stringify({
          ok: false,
          code: "WEBSITE_CAPABILITY_DISABLED",
          message:
            "Booking and appointment holds are not enabled for this website. Offer an inquiry for human follow-up instead.",
        })
      }
    >
      {(client) => (
        <WebsiteVoiceControls
          {...properties}
          client={client}
          sessionIdRef={sessionIdRef}
          intentionalRef={intentionalRef}
          transcript={transcript}
          resetTranscript={() => {
            setTranscript([]);
            setDraft({});
            setError("");
            setDisconnected(false);
          }}
          draft={draft}
          disconnected={disconnected}
          error={error}
          setError={setError}
        />
      )}
    </ElevenLabsConversationAdapter>
  );
}

function WebsiteVoiceControls({
  slug,
  brandName,
  leadCapture,
  client,
  sessionIdRef,
  intentionalRef,
  transcript,
  resetTranscript,
  draft,
  disconnected,
  error,
  setError,
}: Properties & {
  client: ConversationClient;
  sessionIdRef: React.MutableRefObject<string | undefined>;
  intentionalRef: React.MutableRefObject<boolean>;
  transcript: ConversationTurn[];
  resetTranscript: () => void;
  draft: ConversationDraft;
  disconnected: boolean;
  error: string;
  setError: (value: string) => void;
}) {
  const [mode, setMode] = useState<ConversationInputMode>("VOICE");
  const [disclosure, setDisclosure] = useState(false);
  const [microphone, setMicrophone] = useState(false);
  const [phase, setPhase] = useState<
    "idle" | "requesting" | "active" | "ending" | "ended" | "failed"
  >("idle");
  const [remaining, setRemaining] = useState(180);
  const [maximum, setMaximum] = useState(180);
  const [authorizedSession, setAuthorizedSession] = useState<string>();
  const [reviewAvailable, setReviewAvailable] = useState(false);
  const deadline = useRef(0);
  const locked = useRef(false);
  const mountedRef = useRef(true);
  const live = ["requesting", "active", "ending"].includes(phase);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const finish = useCallback(async () => {
    if (locked.current || !sessionIdRef.current) return;
    locked.current = true;
    intentionalRef.current = true;
    setPhase("ending");
    try {
      await client.end();
      const available = await endConversationSession(
        "",
        sessionIdRef.current,
        "COMPLETED",
        undefined,
        slug,
      );
      setReviewAvailable(available);
      setPhase("ended");
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "The session could not be finished. Retry finishing it.",
      );
      setPhase("failed");
    } finally {
      locked.current = false;
    }
  }, [client, sessionIdRef, intentionalRef, slug, setError]);

  useEffect(() => {
    if (phase !== "active") return;
    const timer = window.setInterval(() => {
      const left = Math.max(
        0,
        Math.ceil((deadline.current - Date.now()) / 1000),
      );
      setRemaining(left);
      if (left === 0) void finish();
    }, 1000);
    return () => window.clearInterval(timer);
  }, [phase, finish]);

  async function start() {
    if (locked.current || !disclosure || (mode === "VOICE" && !microphone))
      return;
    locked.current = true;
    setError("");
    setPhase("requesting");
    try {
      if (sessionIdRef.current) {
        await endConversationSession(
          "",
          sessionIdRef.current,
          "INTERRUPTED",
          undefined,
          slug,
        );
        sessionIdRef.current = undefined;
        setAuthorizedSession(undefined);
      }
      if (!mountedRef.current) return;
      resetTranscript();
      setReviewAvailable(false);
      intentionalRef.current = false;
      const grant = await authorizeConversationSession(
        "",
        undefined,
        mode,
        slug,
      );
      if (!mountedRef.current) {
        await endConversationSession(
          "",
          grant.sessionId,
          "INTERRUPTED",
          undefined,
          slug,
        );
        return;
      }
      sessionIdRef.current = grant.sessionId;
      setAuthorizedSession(grant.sessionId);
      setMaximum(grant.maximumDurationSeconds);
      deadline.current = grant.authorizationExpiresAt
        ? Date.parse(grant.authorizationExpiresAt)
        : Date.now() + grant.maximumDurationSeconds * 1000;
      setRemaining(
        Math.max(0, Math.ceil((deadline.current - Date.now()) / 1000)),
      );
      await client.start(grant);
      if (!mountedRef.current) {
        await client.end();
        return;
      }
      setPhase("active");
    } catch (failure) {
      intentionalRef.current = true;
      await client.end().catch(() => undefined);
      if (sessionIdRef.current)
        await endConversationSession(
          "",
          sessionIdRef.current,
          "FAILED",
          undefined,
          slug,
        ).catch(() => undefined);
      setError(
        failure instanceof Error
          ? failure.message
          : "The conversation could not start.",
      );
      setPhase("failed");
    } finally {
      locked.current = false;
    }
  }

  return (
    <div className={styles.panel}>
      <h3>Talk with {brandName}</h3>
      <p>
        Voice and Text connect to this website’s configured agent. No
        appointment is booked by this conversation.
      </p>
      <div className={styles.modes} role="group" aria-label="Conversation mode">
        {(["VOICE", "TEXT"] as const).map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={mode === value}
            disabled={live}
            onClick={() => setMode(value)}
          >
            {value === "VOICE" ? "Voice" : "Text Chat"}
          </button>
        ))}
      </div>
      {!live && phase !== "ended" && (
        <div className={styles.consents}>
          <label>
            <input
              type="checkbox"
              checked={disclosure}
              onChange={(event) => setDisclosure(event.target.checked)}
            />
            I understand I will be speaking with an AI assistant.
          </label>
          {mode === "VOICE" && (
            <label>
              <input
                type="checkbox"
                checked={microphone}
                onChange={(event) => setMicrophone(event.target.checked)}
              />
              I consent to microphone access for Voice.
            </label>
          )}
          <button
            type="button"
            disabled={!disclosure || (mode === "VOICE" && !microphone)}
            onClick={() => void start()}
          >
            Start {mode === "VOICE" ? "Voice" : "Text Chat"}
          </button>
        </div>
      )}
      {live && (
        <>
          <SessionTimer
            remaining={remaining}
            maximum={maximum}
            active={phase === "active"}
          />
          <p role="status">
            {phase === "active"
              ? disconnected
                ? "Disconnected — finish or retry."
                : client.status === "connected"
                  ? "Connected"
                  : "Connecting…"
              : phase === "requesting"
                ? "Authorizing this website’s session…"
                : "Finishing…"}
          </p>
          <div className={styles.modes}>
            {mode === "VOICE" && (
              <button
                type="button"
                disabled={phase !== "active"}
                aria-pressed={client.isMuted}
                onClick={() => client.setMuted(!client.isMuted)}
              >
                {client.isMuted ? "Unmute" : "Mute"}
              </button>
            )}
            <button
              type="button"
              disabled={phase === "requesting" || phase === "ending"}
              onClick={() => void finish()}
            >
              Finish conversation
            </button>
          </div>
        </>
      )}
      {phase === "failed" && authorizedSession && (
        <button type="button" onClick={() => void finish()}>
          Retry finishing session
        </button>
      )}
      {error && (
        <div role="alert">
          <p>{error}</p>
          <Link href={`/login?intent=website:${slug}`}>
            Sign in or verify your account
          </Link>
        </div>
      )}
      <ChatComposer
        assistantName={brandName}
        connected={
          phase === "active" && client.status === "connected" && !disconnected
        }
        send={client.sendText}
        onTyping={client.notifyTyping}
        textOnly={mode === "TEXT"}
      />
      {transcript.length > 0 && (
        <ol className={styles.transcript} aria-label="Your conversation">
          {transcript.map((turn, index) => (
            <li key={index}>
              <strong>{turn.speaker === "USER" ? "You" : "Assistant"}</strong>
              <p>{turn.text}</p>
            </li>
          ))}
        </ol>
      )}
      {phase === "ended" && (
        <>
          <p role="status">
            Conversation finished. No appointment was created.
          </p>
          {leadCapture && reviewAvailable && (
            <WebsiteInquiry
              slug={slug}
              sessionId={authorizedSession!}
              transcript={transcript}
              draft={draft}
            />
          )}
        </>
      )}
    </div>
  );
}

function WebsiteInquiry({
  slug,
  sessionId,
  transcript,
  draft,
}: {
  slug: string;
  sessionId: string;
  transcript: ConversationTurn[];
  draft: ConversationDraft;
}) {
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [hasPending, setHasPending] = useState(false);
  const pending = useRef<{ key: string; body: string } | undefined>(undefined);
  const locked = useRef(false);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked.current) return;
    locked.current = true;
    const form = new FormData(event.currentTarget);
    if (!pending.current)
      pending.current = {
        key: crypto.randomUUID(),
        body: JSON.stringify({
          conversation_session_id: sessionId,
          customer: {
            full_name: form.get("name"),
            email: form.get("email") || null,
            phone: form.get("phone") || null,
          },
          intake_intent: form.get("intent"),
          transcript,
          explicit_confirmation: true,
        }),
      };
    setHasPending(true);
    setBusy(true);
    setError("");
    try {
      const response = await fetch(
        conversationApiPath("", "conversation-intakes", slug),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": pending.current.key,
          },
          body: pending.current.body,
          signal: AbortSignal.timeout(20000),
        },
      );
      if (!response.ok) {
        if (response.status >= 400 && response.status < 500) {
          pending.current = undefined;
          setHasPending(false);
        }
        throw new Error(
          "The inquiry could not be saved. Review your details and retry. No booking was made.",
        );
      }
      setSaved(true);
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Unable to save the inquiry. Retry the same request.",
      );
    } finally {
      setBusy(false);
      locked.current = false;
    }
  }
  if (saved)
    return (
      <p role="status">
        Your inquiry was saved for human follow-up. This is not an appointment
        confirmation.
      </p>
    );
  return (
    <form onSubmit={(event) => void save(event)}>
      <h4>Review and confirm your inquiry</h4>
      <p>Only submit details you want this business to retain.</p>
      <fieldset disabled={busy || hasPending}>
        <label>
          Name
          <input
            name="name"
            required
            maxLength={200}
            defaultValue={draft.fullName}
          />
        </label>
        <label>
          Email
          <input
            type="email"
            name="email"
            defaultValue={draft.email}
            maxLength={254}
          />
        </label>
        <label>
          Phone
          <input name="phone" defaultValue={draft.phone} maxLength={40} />
        </label>
        <label>
          What should the team follow up on?
          <textarea
            name="intent"
            required
            maxLength={2000}
            defaultValue={draft.intakeIntent}
          />
        </label>
        <label>
          <input type="checkbox" required />I confirm these details and request
          human follow-up.
        </label>
      </fieldset>
      {error && <p role="alert">{error}</p>}
      <button disabled={busy || transcript.length < 2} type="submit">
        {busy
          ? "Saving…"
          : hasPending
            ? "Retry same inquiry"
            : "Confirm inquiry"}
      </button>
    </form>
  );
}
