"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";

import {
  authorizeConversationSession,
  ConversationApiError,
  confirmConversationIntake,
  endConversationSession,
} from "./api";
import { lookupConversationApprovedFaq } from "../approved-faqs/api";
import { BrowserBooking } from "./browser-booking";
import { BookingProgressPanel } from "./booking-progress-panel";
import {
  INITIAL_BOOKING_PROGRESS,
  conversationActivity,
  bookingFailure,
} from "./booking-progress";
import type { BookingProgress } from "./booking-progress";
import { ChatComposer } from "./chat-composer";
import chatStyles from "./conversation-chat.module.css";
import { ConfiguredConversationAdapter } from "./configured-adapter";
import type {
  ConfirmedConversationIntake,
  ConversationClient,
  ConversationDraft,
  ConversationInputMode,
  ConversationSpeaker,
  ConversationTurn,
} from "./contracts";
import { classifyConfirmationFailure, startFailureMessage } from "./failures";
import {
  classifyConnectionFailure,
  isLiveConversationPhase,
} from "./lifecycle";
import type { ConnectionFailureSource, ConversationPhase } from "./lifecycle";
import { appendTranscript, validateConfirmation } from "./review";
import { VoiceBookingSession } from "./voice-booking";
import { SessionTimer, remainingSessionSeconds } from "./session-timer";
import type { VoiceAppointment, VoiceBookingTool } from "./voice-booking";
import type { ReceptionistSettings } from "../receptionist/contracts";
import { ProductIcon, VoiceSymbol } from "@/components/product-icons";

type VoiceTestProperties = Readonly<{
  apiBaseUrl: string;
  adminToken?: string;
  receptionistSettings: ReceptionistSettings;
  presentation?: "workspace" | "customer";
  onActivityChange?: (active: boolean) => void;
  onViewAppointments?: () => void;
  onViewBooking?: (appointmentId: string) => void;
  onBookingChanged?: () => void;
}>;

type IntakeForm = {
  fullName: string;
  email: string;
  phone: string;
  intakeIntent: string;
  addressLine1: string;
  city: string;
  stateCode: string;
  postalCode: string;
  serviceKind: string;
  preferredWindow: string;
  hazardousCondition: boolean;
};

const EMPTY_FORM: IntakeForm = {
  fullName: "",
  email: "",
  phone: "",
  intakeIntent: "",
  addressLine1: "",
  city: "",
  stateCode: "",
  postalCode: "",
  serviceKind: "AC_REPAIR",
  preferredWindow: "",
  hazardousCondition: false,
};

export function VoiceTest({
  apiBaseUrl,
  adminToken,
  receptionistSettings,
  presentation = "workspace",
  onActivityChange,
  onViewAppointments,
  onViewBooking,
  onBookingChanged,
}: VoiceTestProperties) {
  const [transcript, setTranscript] = useState<ConversationTurn[]>([]);
  const [form, setForm] = useState<IntakeForm>(EMPTY_FORM);
  const [phase, setPhaseState] = useState<ConversationPhase>("idle");
  const [errorMessage, setErrorMessage] = useState<string>();
  const [savedIntake, setSavedIntake] = useState<ConfirmedConversationIntake>();
  const [voiceAppointment, setVoiceAppointment] = useState<VoiceAppointment>();
  const [bookingProgress, setBookingProgress] = useState<BookingProgress>(
    INITIAL_BOOKING_PROGRESS,
  );
  const voiceBookingRef = useRef<VoiceBookingSession | undefined>(undefined);
  const phaseRef = useRef<ConversationPhase>("idle");
  const sessionIdRef = useRef<string | undefined>(undefined);
  const intentionalEndRef = useRef(false);

  useEffect(() => {
    onActivityChange?.(
      ["requesting", "connecting", "active", "stopping", "saving"].includes(
        phase,
      ),
    );
  }, [phase, onActivityChange]);

  useEffect(() => () => onActivityChange?.(false), [onActivityChange]);

  const setPhase = useCallback((nextPhase: ConversationPhase) => {
    phaseRef.current = nextPhase;
    setPhaseState(nextPhase);
  }, []);

  const handleTranscript = useCallback(
    (speaker: ConversationSpeaker, text: string) => {
      if (!isLiveConversationPhase(phaseRef.current)) {
        return;
      }
      setTranscript((current) => appendTranscript(current, speaker, text));
      voiceBookingRef.current?.recordTurn(speaker, text);
    },
    [],
  );

  const handleDraft = useCallback(async (draft: ConversationDraft) => {
    if (!isLiveConversationPhase(phaseRef.current)) {
      return "The conversation is no longer active.";
    }
    if (draft.hazardousCondition) {
      setForm((current) => ({ ...current, hazardousCondition: true }));
    }
    const booking = voiceBookingRef.current;
    const result = await booking?.updateDraft(draft);
    if (voiceBookingRef.current !== booking)
      return "The conversation is no longer current.";
    if (voiceBookingRef.current?.savedIntake) {
      if (draft.hazardousCondition)
        setForm((current) => ({ ...current, hazardousCondition: true }));
      return result ?? "The request is already saved.";
    }
    setForm((current) => ({
      fullName: draft.fullName ?? current.fullName,
      email: draft.email ?? current.email,
      phone: draft.phone ?? current.phone,
      intakeIntent: draft.intakeIntent ?? current.intakeIntent,
      addressLine1: draft.addressLine1 ?? current.addressLine1,
      city: draft.city ?? current.city,
      stateCode: draft.stateCode ?? current.stateCode,
      postalCode: draft.postalCode ?? current.postalCode,
      serviceKind: draft.serviceKind ?? current.serviceKind,
      preferredWindow: draft.preferredWindow ?? current.preferredWindow,
      hazardousCondition:
        current.hazardousCondition || draft.hazardousCondition === true,
    }));
    return result ?? "The draft is visible for review. Nothing has been saved.";
  }, []);

  const handleBookingTool = useCallback(
    async (tool: VoiceBookingTool, parameters: Record<string, unknown>) => {
      const booking = voiceBookingRef.current;
      if (!booking)
        return JSON.stringify({
          ok: false,
          message: "Start a conversation first.",
        });
      return JSON.stringify(await booking.execute(tool, parameters));
    },
    [],
  );

  const handleApprovedFaqLookup = useCallback(
    async (query: string) => {
      const conversationSessionId = sessionIdRef.current;
      if (conversationSessionId === undefined) {
        return {
          matched: false,
          answer: null,
          fallbackMessage: receptionistSettings.escalationMessage,
          source: null,
        };
      }
      try {
        return await lookupConversationApprovedFaq(
          apiBaseUrl,
          conversationSessionId,
          query,
          adminToken,
        );
      } catch {
        return {
          matched: false,
          answer: null,
          fallbackMessage: receptionistSettings.escalationMessage,
          source: null,
        };
      }
    },
    [apiBaseUrl, adminToken, receptionistSettings.escalationMessage],
  );

  const handleConnectionFailure = useCallback(
    (source: ConnectionFailureSource) => {
      const failure = classifyConnectionFailure({
        intentionalEnd: intentionalEndRef.current,
        phase: phaseRef.current,
        sessionId: sessionIdRef.current,
        source,
      });
      if (failure === undefined) {
        return;
      }

      setErrorMessage(
        voiceBookingRef.current?.savedIntake
          ? "The connection ended. Your saved request and any confirmed booking are kept."
          : "The live connection ended unexpectedly. Start a new session.",
      );
      setPhase("stopping");
      void endConversationSession(
        apiBaseUrl,
        failure.sessionId,
        failure.outcome,
        adminToken,
      )
        .catch(() => undefined)
        .finally(() => {
          if (phaseRef.current === "stopping") {
            setPhase(voiceBookingRef.current?.savedIntake ? "saved" : "error");
          }
        });
    },
    [apiBaseUrl, adminToken, setPhase],
  );

  const handleDisconnect = useCallback(() => {
    handleConnectionFailure("disconnect");
  }, [handleConnectionFailure]);

  const handleError = useCallback(() => {
    handleConnectionFailure("provider_error");
  }, [handleConnectionFailure]);

  const cleanupActiveSession = useCallback(() => {
    const failure = classifyConnectionFailure({
      intentionalEnd: intentionalEndRef.current,
      phase: phaseRef.current,
      sessionId: sessionIdRef.current,
      source: "disconnect",
    });
    if (failure === undefined) {
      return;
    }

    phaseRef.current = "stopping";
    void endConversationSession(
      apiBaseUrl,
      failure.sessionId,
      failure.outcome,
      adminToken,
    ).catch(() => undefined);
  }, [apiBaseUrl, adminToken]);

  useEffect(() => {
    return cleanupActiveSession;
  }, [cleanupActiveSession]);

  return (
    <ConfiguredConversationAdapter
      onApprovedFaqLookup={handleApprovedFaqLookup}
      onDisconnect={handleDisconnect}
      onDraft={handleDraft}
      onError={handleError}
      onTranscript={handleTranscript}
      onBookingTool={handleBookingTool}
    >
      {(client) => (
        <VoiceTestExperience
          apiBaseUrl={apiBaseUrl}
          adminToken={adminToken}
          client={client}
          errorMessage={errorMessage}
          form={form}
          intentionalEndRef={intentionalEndRef}
          phase={phase}
          phaseRef={phaseRef}
          receptionistSettings={receptionistSettings}
          sessionIdRef={sessionIdRef}
          setErrorMessage={setErrorMessage}
          setForm={setForm}
          setPhase={setPhase}
          setTranscript={setTranscript}
          transcript={transcript}
          savedIntake={savedIntake}
          setSavedIntake={setSavedIntake}
          voiceAppointment={voiceAppointment}
          setVoiceAppointment={setVoiceAppointment}
          voiceBookingRef={voiceBookingRef}
          presentation={presentation}
          bookingProgress={bookingProgress}
          setBookingProgress={setBookingProgress}
          onViewAppointments={onViewAppointments}
          onViewBooking={onViewBooking}
          onBookingChanged={onBookingChanged}
        />
      )}
    </ConfiguredConversationAdapter>
  );
}

type ExperienceProperties = Readonly<{
  apiBaseUrl: string;
  adminToken?: string;
  client: ConversationClient;
  errorMessage: string | undefined;
  form: IntakeForm;
  intentionalEndRef: MutableRefObject<boolean>;
  phase: ConversationPhase;
  phaseRef: MutableRefObject<ConversationPhase>;
  receptionistSettings: ReceptionistSettings;
  sessionIdRef: MutableRefObject<string | undefined>;
  setErrorMessage: Dispatch<SetStateAction<string | undefined>>;
  setForm: Dispatch<SetStateAction<IntakeForm>>;
  setPhase: (phase: ConversationPhase) => void;
  setTranscript: Dispatch<SetStateAction<ConversationTurn[]>>;
  transcript: ConversationTurn[];
  savedIntake: ConfirmedConversationIntake | undefined;
  setSavedIntake: Dispatch<
    SetStateAction<ConfirmedConversationIntake | undefined>
  >;
  voiceAppointment: VoiceAppointment | undefined;
  setVoiceAppointment: Dispatch<SetStateAction<VoiceAppointment | undefined>>;
  voiceBookingRef: MutableRefObject<VoiceBookingSession | undefined>;
  presentation: "workspace" | "customer";
  bookingProgress: BookingProgress;
  setBookingProgress: Dispatch<SetStateAction<BookingProgress>>;
  onViewAppointments?: () => void;
  onViewBooking?: (appointmentId: string) => void;
  onBookingChanged?: () => void;
}>;

function VoiceTestExperience({
  apiBaseUrl,
  adminToken,
  client,
  errorMessage,
  form,
  intentionalEndRef,
  phase,
  phaseRef,
  receptionistSettings,
  sessionIdRef,
  setErrorMessage,
  setForm,
  setPhase,
  setTranscript,
  transcript,
  savedIntake,
  setSavedIntake,
  voiceAppointment,
  setVoiceAppointment,
  voiceBookingRef,
  presentation,
  bookingProgress,
  setBookingProgress,
  onViewAppointments,
  onViewBooking,
  onBookingChanged,
}: ExperienceProperties) {
  const [disclosureAccepted, setDisclosureAccepted] = useState(false);
  const [microphoneConsent, setMicrophoneConsent] = useState(false);
  const [syntheticDataAcknowledged, setSyntheticDataAcknowledged] =
    useState(false);
  const [remainingSeconds, setRemainingSeconds] = useState(180);
  const [maximumDuration, setMaximumDuration] = useState(180);
  const [timeLimitReached, setTimeLimitReached] = useState(false);
  const sessionDeadlineRef = useRef<number | undefined>(undefined);
  const [confirmationLocked, setConfirmationLocked] = useState(false);
  const [blockedSessionId, setBlockedSessionId] = useState<string>();
  const [inputMode, setInputMode] = useState<ConversationInputMode>(
    presentation === "customer" ? "TEXT" : "VOICE",
  );
  const textOnly = inputMode === "TEXT";
  const confirmationKeyRef = useRef<string | undefined>(undefined);
  const finishConversationRef = useRef<() => Promise<void>>(
    async () => undefined,
  );

  const finishConversation = useCallback(async () => {
    const sessionId = sessionIdRef.current;
    if (sessionId === undefined || intentionalEndRef.current) {
      return;
    }
    intentionalEndRef.current = true;
    setErrorMessage(undefined);
    setPhase("stopping");
    try {
      if (client.status !== "disconnected") {
        await client.end();
      }
      const reviewAvailable = await endConversationSession(
        apiBaseUrl,
        sessionId,
        "COMPLETED",
        adminToken,
      );
      if (!reviewAvailable) {
        setErrorMessage(
          "The session exceeded its limit and cannot be confirmed. " +
            "Start a new session.",
        );
        setPhase("error");
        return;
      }
      setPhase(voiceBookingRef.current?.savedIntake ? "saved" : "review");
    } catch {
      setErrorMessage(
        voiceBookingRef.current?.savedIntake
          ? "The conversation ended. Your saved request and any confirmed appointment are kept."
          : "The conversation ended, but the review could not be prepared. Start a new session.",
      );
      setPhase(voiceBookingRef.current?.savedIntake ? "saved" : "review_error");
    } finally {
      intentionalEndRef.current = false;
    }
  }, [
    apiBaseUrl,
    adminToken,
    client,
    intentionalEndRef,
    sessionIdRef,
    setErrorMessage,
    setPhase,
    voiceBookingRef,
  ]);

  useEffect(() => {
    finishConversationRef.current = finishConversation;
  }, [finishConversation]);

  useEffect(() => {
    if (phase !== "active") {
      return;
    }
    const deadline = sessionDeadlineRef.current;
    if (deadline === undefined) return;
    const tick = () => {
      const nextRemaining = Math.min(
        maximumDuration,
        remainingSessionSeconds(deadline, Date.now()),
      );
      setRemainingSeconds(nextRemaining);
      if (nextRemaining === 0) {
        window.clearInterval(interval);
        setTimeLimitReached(true);
        void finishConversationRef.current();
      }
    };
    const refresh = window.setTimeout(tick, 0);
    const interval = window.setInterval(tick, 1_000);
    return () => {
      window.clearTimeout(refresh);
      window.clearInterval(interval);
    };
  }, [maximumDuration, phase]);

  async function startConversation() {
    if (!["idle", "error"].includes(phaseRef.current)) return;
    if (blockedSessionId !== undefined) return;
    setTimeLimitReached(false);
    setRemainingSeconds(maximumDuration);
    sessionDeadlineRef.current = undefined;
    if (
      !disclosureAccepted ||
      (!textOnly && !microphoneConsent) ||
      !syntheticDataAcknowledged
    ) {
      setErrorMessage("Accept the required conversation permissions first.");
      return;
    }
    setPhase("requesting");
    const previousSessionId = sessionIdRef.current;
    if (previousSessionId !== undefined) {
      try {
        await client.end();
        await endConversationSession(
          apiBaseUrl,
          previousSessionId,
          "INTERRUPTED",
          adminToken,
        );
        sessionIdRef.current = undefined;
      } catch (error) {
        if (
          error instanceof ConversationApiError &&
          [404, 410].includes(error.status)
        ) {
          sessionIdRef.current = undefined;
        } else {
          setErrorMessage(
            "The previous session could not be released. Check your connection and retry; your unsent message is kept.",
          );
          setPhase("error");
          return;
        }
      }
    }
    setErrorMessage(undefined);
    setSavedIntake(undefined);
    setVoiceAppointment(undefined);
    setBookingProgress(INITIAL_BOOKING_PROGRESS);
    voiceBookingRef.current = undefined;
    setTranscript([]);
    setForm(EMPTY_FORM);
    confirmationKeyRef.current = undefined;
    setConfirmationLocked(false);
    sessionIdRef.current = undefined;
    try {
      if (!textOnly) {
        const permissionStream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        permissionStream.getTracks().forEach((track) => track.stop());
      }
      const authorization = await authorizeConversationSession(
        apiBaseUrl,
        adminToken,
        inputMode,
      );
      sessionIdRef.current = authorization.sessionId;
      voiceBookingRef.current = new VoiceBookingSession({
        apiBaseUrl,
        adminToken,
        sessionId: authorization.sessionId,
        isActive: () =>
          sessionIdRef.current === authorization.sessionId &&
          isLiveConversationPhase(phaseRef.current),
        onSaved: (intake) => {
          if (sessionIdRef.current !== authorization.sessionId) return;
          setSavedIntake(intake);
          setConfirmationLocked(true);
          if (!isLiveConversationPhase(phaseRef.current)) setPhase("saved");
        },
        onAppointment: (appointment) => {
          if (sessionIdRef.current === authorization.sessionId) {
            setVoiceAppointment(appointment);
            onBookingChanged?.();
          }
        },
        onProgress: (progress) => {
          if (sessionIdRef.current === authorization.sessionId)
            setBookingProgress(progress);
        },
      });
      setMaximumDuration(authorization.maximumDurationSeconds);
      setRemainingSeconds(authorization.maximumDurationSeconds);
      sessionDeadlineRef.current = authorization.authorizationExpiresAt
        ? Date.parse(authorization.authorizationExpiresAt)
        : Date.now() + authorization.maximumDurationSeconds * 1000;
      setPhase("connecting");
      await client.start(authorization);
      if (phaseRef.current === "stopping" || phaseRef.current === "error") {
        throw new Error("conversation connection failed during startup");
      }
      setPhase("active");
    } catch (error) {
      if (phaseRef.current === "stopping" || phaseRef.current === "error") {
        return;
      }
      const sessionId = sessionIdRef.current;
      if (sessionId !== undefined) {
        setPhase("stopping");
        await endConversationSession(
          apiBaseUrl,
          sessionId,
          "FAILED",
          adminToken,
        ).catch(() => undefined);
      }
      setErrorMessage(startFailureMessage(error, inputMode));
      if (error instanceof ConversationApiError)
        setBlockedSessionId(error.previousSessionId);
      setPhase("error");
    }
  }

  async function releaseBlockedSession() {
    if (phaseRef.current !== "error" || blockedSessionId === undefined) return;
    const previousSessionId = blockedSessionId;
    setPhase("stopping");
    intentionalEndRef.current = true;
    try {
      await client.end();
      await endConversationSession(
        apiBaseUrl,
        previousSessionId,
        "INTERRUPTED",
        adminToken,
      );
      setBlockedSessionId(undefined);
      if (sessionIdRef.current === previousSessionId)
        sessionIdRef.current = undefined;
      setErrorMessage(
        "Your previous session was released. Start a new conversation above.",
      );
    } catch (error) {
      if (
        error instanceof ConversationApiError &&
        [404, 410].includes(error.status)
      ) {
        setBlockedSessionId(undefined);
        setErrorMessage(
          "The earlier session is no longer active. Start a new conversation above.",
        );
      } else {
        setErrorMessage(
          "The previous session could not be released. Close other booking tabs and retry.",
        );
      }
    } finally {
      intentionalEndRef.current = false;
      setPhase("error");
    }
  }

  async function saveConfirmedIntake() {
    const sessionId = sessionIdRef.current;
    if (sessionId === undefined) {
      setErrorMessage("The conversation session is unavailable.");
      return;
    }
    const validationMessage = validateConfirmation(form, transcript);
    if (validationMessage !== undefined) {
      setErrorMessage(validationMessage);
      return;
    }
    if (
      !form.phone.trim() ||
      !form.addressLine1.trim() ||
      !form.city.trim() ||
      !/^[A-Za-z]{2}$/.test(form.stateCode) ||
      !/^[0-9]{5}$/.test(form.postalCode) ||
      !form.preferredWindow.trim()
    ) {
      setErrorMessage(
        "Complete the callback number, U.S. service address, and preferred window.",
      );
      return;
    }
    setErrorMessage(undefined);
    setPhase("saving");
    setBookingProgress((current) => ({
      ...current,
      pending: "confirm_service_request",
      failure: undefined,
    }));
    setConfirmationLocked(true);
    confirmationKeyRef.current ??= crypto.randomUUID();
    try {
      const result = await confirmConversationIntake(
        apiBaseUrl,
        {
          sessionId,
          fullName: form.fullName.trim(),
          email: form.email.trim(),
          phone: form.phone.trim(),
          intakeIntent: form.intakeIntent.trim(),
          transcript,
          idempotencyKey: confirmationKeyRef.current,
          addressLine1: form.addressLine1.trim(),
          city: form.city.trim(),
          stateCode: form.stateCode.toUpperCase(),
          postalCode: form.postalCode,
          serviceKind: form.serviceKind,
          preferredWindow: form.preferredWindow.trim(),
          hazardousCondition: form.hazardousCondition,
        },
        adminToken,
      );
      setSavedIntake(result);
      setBookingProgress({
        requestSaved: true,
        awaitingIntakeConfirmation: false,
        hazardous: form.hazardousCondition,
        serviceKind: form.serviceKind,
      });
      setPhase("saved");
    } catch (error) {
      const failure = classifyConfirmationFailure(error);
      if (failure.action === "correct_input") {
        confirmationKeyRef.current = undefined;
        setConfirmationLocked(false);
      }
      setErrorMessage(failure.message);
      setBookingProgress((current) => ({
        ...current,
        pending: undefined,
        failure: bookingFailure("confirm_service_request", error),
      }));
      setPhase(failure.action === "start_new_session" ? "error" : "review");
    }
  }

  function resetExperience() {
    sessionDeadlineRef.current = undefined;
    setRemainingSeconds(180);
    setMaximumDuration(180);
    setTimeLimitReached(false);
    sessionIdRef.current = undefined;
    confirmationKeyRef.current = undefined;
    setConfirmationLocked(false);
    setBlockedSessionId(undefined);
    setTranscript([]);
    setForm(EMPTY_FORM);
    setSavedIntake(undefined);
    setVoiceAppointment(undefined);
    setBookingProgress(INITIAL_BOOKING_PROGRESS);
    voiceBookingRef.current = undefined;
    setErrorMessage(undefined);
    setPhase("idle");
  }

  const isBusy = ["requesting", "connecting", "stopping", "saving"].includes(
    phase,
  );
  const canStart = phase === "idle" || phase === "error";
  const customerView = presentation === "customer";
  const experienceSessionId = sessionIdRef.current;

  return (
    <div className={`voice-grid ${customerView ? "line-experience" : ""}`}>
      <section
        className="voice-card voice-control-card"
        aria-labelledby="voice-controls-title"
      >
        {customerView && (
          <div className="line-session-identity">
            <span>LINE</span>
            <span className="voice-ai-badge">AI booking assistant</span>
          </div>
        )}
        <p className="eyebrow">
          {customerView
            ? `Booking with ${receptionistSettings.publicName}`
            : receptionistSettings.publicName}
        </p>
        <div
          className={chatStyles.modes}
          role="group"
          aria-label="Conversation mode"
        >
          <button
            aria-pressed={textOnly}
            disabled={!canStart || isBusy}
            onClick={() => setInputMode("TEXT")}
            type="button"
          >
            <ProductIcon name="chat" /> Chat
          </button>
          <button
            aria-pressed={!textOnly}
            disabled={!canStart || isBusy}
            onClick={() => setInputMode("VOICE")}
            type="button"
          >
            <ProductIcon name="mic" /> Voice
          </button>
        </div>
        <p className="section-help">
          {textOnly
            ? "Type to Line. No sound or microphone access."
            : "Speak with Line, or type while voice is connected."}
          {!canStart && " Start a new conversation to switch modes."}
        </p>
        {customerView ? (
          <>
            <div
              className={`customer-voice-orb ${phase === "active" ? "is-connected" : ""}`}
            >
              {textOnly ? (
                <ProductIcon name="chat" />
              ) : (
                <VoiceSymbol active={phase === "active" && !client.isMuted} />
              )}
            </div>
            <h2 id="voice-controls-title">
              {phase === "active"
                ? conversationActivity(phase, client, inputMode)
                : savedIntake
                  ? "One less thing on your list."
                  : "Let’s talk about your home."}
            </h2>
          </>
        ) : (
          <h1 id="voice-controls-title">Chat or talk to our AI receptionist</h1>
        )}
        <p className="summary">
          {customerView ? (
            "Tell Line what you need. Find a time that works. Nothing is booked until you confirm."
          ) : (
            <>
              {receptionistSettings.greeting} It can collect contact details and
              HVAC service needs, but cannot diagnose faults, give repair
              instructions, or promise a technician before a booking is
              confirmed.
            </>
          )}
        </p>
        {!customerView && (
          <div className="receptionist-context">
            <p>
              <strong>Supported interests:</strong>{" "}
              {receptionistSettings.supportedServiceCategories.join(", ")}
            </p>
            <p>
              <strong>Human follow-up:</strong>{" "}
              {receptionistSettings.escalationMessage}
            </p>
          </div>
        )}
        <div
          className={`voice-permissions ${customerView && !canStart ? "permissions-complete" : ""}`}
        >
          {customerView && <h3>Before we begin</h3>}
          <div className="disclosure" role="note">
            You are interacting with an AI, not a human. Your messages
            {textOnly ? "" : " and microphone audio"} are processed by
            ElevenLabs and its AI/LLM providers. Chat mode does not access your
            microphone or play audio. The configured agent has audio recording
            disabled and zero-day scheduled deletion; provider Zero Retention
            Mode is not enabled. Use fictional details only. This app keeps live
            drafts in this browser and does not store raw audio. Intake details
            and transcript text are saved only after you confirm the full
            readback or the on-screen review. Booking requires a separate
            confirmation of the appointment date and time.
          </div>
          <label className="consent-row">
            <input
              checked={disclosureAccepted}
              disabled={!canStart}
              onChange={(event) => setDisclosureAccepted(event.target.checked)}
              type="checkbox"
            />
            I agree to the AI and provider-processing disclosure above.
          </label>
          {!textOnly && (
            <label className="consent-row">
              <input
                checked={microphoneConsent}
                disabled={!canStart}
                onChange={(event) => setMicrophoneConsent(event.target.checked)}
                type="checkbox"
              />
              I consent to live microphone access for this conversation.
            </label>
          )}
          <label className="consent-row">
            <input
              checked={syntheticDataAcknowledged}
              disabled={!canStart}
              onChange={(event) =>
                setSyntheticDataAcknowledged(event.target.checked)
              }
              type="checkbox"
            />
            I will use fictional test details only, never real customer or
            sensitive data.
          </label>
        </div>
        {customerView && !canStart && (
          <p className="line-permissions-status">
            <ProductIcon name="shield" /> Your permissions are confirmed.
          </p>
        )}
        <div className="voice-actions">
          {canStart && (
            <button
              className={customerView ? "product-button" : "primary-button"}
              disabled={
                !disclosureAccepted ||
                (!textOnly && !microphoneConsent) ||
                !syntheticDataAcknowledged ||
                blockedSessionId !== undefined ||
                isBusy
              }
              onClick={() => void startConversation()}
              type="button"
            >
              {customerView && <ProductIcon name={textOnly ? "chat" : "mic"} />}
              {phase === "error"
                ? "Try a new conversation"
                : customerView
                  ? textOnly
                    ? "Start chatting with Line"
                    : "Start talking to Line"
                  : "Start conversation"}
            </button>
          )}
          {blockedSessionId !== undefined && phase === "error" && (
            <div>
              <p className="section-help">
                Close other booking tabs first. Release your earlier session to
                start again. Saved requests and appointments are kept.
              </p>
              <button
                className="secondary-button"
                onClick={() => void releaseBlockedSession()}
                type="button"
              >
                Release previous session
              </button>
            </div>
          )}
          {phase === "active" && (
            <>
              {!textOnly && (
                <button
                  className="secondary-button"
                  onClick={() => client.setMuted(!client.isMuted)}
                  type="button"
                >
                  {client.isMuted ? "Unmute" : "Mute"}
                </button>
              )}
              <button
                className="secondary-button"
                onClick={() => void finishConversation()}
                type="button"
              >
                {savedIntake ? "Finish conversation" : "Finish and review"}
              </button>
            </>
          )}
          {phase === "review_error" && (
            <button
              className="secondary-button"
              onClick={() => void finishConversation()}
              type="button"
            >
              Retry preparing review
            </button>
          )}
          {(phase === "saved" || phase === "review") && (
            <button
              className="secondary-button"
              onClick={resetExperience}
              type="button"
            >
              Start over
            </button>
          )}
        </div>
        <p className="voice-status">
          {conversationActivity(phase, client, inputMode)}
        </p>
        <SessionTimer
          remaining={remainingSeconds}
          maximum={maximumDuration}
          active={phase === "active"}
        />
        {phase === "active" &&
          remainingSeconds > 0 &&
          remainingSeconds <= 60 && (
            <p className="voice-status" role="status">
              Less than a minute remains. Finish confirming your appointment, or
              continue with the booking controls after the conversation ends.
            </p>
          )}
        {timeLimitReached && (
          <p className="voice-status" role="status">
            The conversation reached its time limit. Your saved request and any
            confirmed appointment are kept. If your request is saved, you can
            finish choosing and confirming a time with the booking controls
            below.
          </p>
        )}
        {errorMessage && (
          <p className="error-message" role="alert">
            {errorMessage}
          </p>
        )}
        <BookingProgressPanel
          progress={{
            ...bookingProgress,
            hazardous: bookingProgress.hazardous || form.hazardousCondition,
          }}
          appointment={voiceAppointment}
          activity={conversationActivity(phase, client, inputMode)}
          conversationBusy={isBusy || phase === "active"}
          conversationEnded={[
            "review",
            "review_error",
            "saved",
            "error",
          ].includes(phase)}
          onViewAppointments={onViewAppointments}
          onViewBooking={onViewBooking}
        />
      </section>

      <section
        className="voice-card voice-conversation-card"
        aria-labelledby="transcript-title"
      >
        <div className="line-conversation-heading">
          <h2 id="transcript-title">
            {customerView ? "Your conversation" : "Conversation transcript"}
          </h2>
          {customerView && <span>JUST YOU & LINE</span>}
        </div>
        <p className="section-help">
          Live text remains in this browser until you explicitly confirm it.
        </p>
        {transcript.length === 0 ? (
          <div className="empty-state">
            {customerView ? (
              <div className="conversation-empty">
                <span>
                  <ProductIcon name="mic" />
                </span>
                <h3>A conversation beats a long form.</h3>
                <p>
                  Start with what’s going on. Line will ask for the details and
                  help you find your next appointment.
                </p>
                <div className="conversation-example">
                  <span>You could start with…</span>
                  <p>
                    “My AC isn’t cooling, and I’d like someone to take a look.”
                  </p>
                </div>
                <ol>
                  <li>
                    <span>1</span> Tell us what you need
                  </li>
                  <li>
                    <span>2</span> Choose an available time
                  </li>
                  <li>
                    <span>3</span> Confirm your appointment
                  </li>
                </ol>
              </div>
            ) : (
              "No transcript yet."
            )}
          </div>
        ) : (
          <ol
            className="transcript-list"
            aria-live="polite"
            aria-relevant="additions text"
          >
            {transcript.map((turn, index) => (
              <li key={`${turn.speaker}-${index}`}>
                <div
                  className={`transcript-turn ${turn.speaker === "USER" ? "turn-user" : "turn-line"}`}
                >
                  <span>
                    {turn.speaker === "USER"
                      ? customerView
                        ? "You"
                        : "Customer"
                      : customerView
                        ? "Line · AI"
                        : "AI assistant"}
                  </span>
                  {customerView && phase !== "review" ? (
                    <p className="conversation-bubble">{turn.text}</p>
                  ) : (
                    <textarea
                      aria-label={`Transcript turn ${index + 1}`}
                      disabled={
                        phase === "connecting" ||
                        phase === "active" ||
                        phase === "stopping" ||
                        phase === "saving" ||
                        phase === "saved" ||
                        confirmationLocked
                      }
                      maxLength={2_000}
                      onChange={(event) => {
                        const text = event.target.value;
                        setTranscript((current) =>
                          current.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, text } : item,
                          ),
                        );
                      }}
                      value={turn.text}
                    />
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
        {phase !== "idle" && (
          <ChatComposer
            connected={phase === "active" && client.status === "connected"}
            onTyping={client.notifyTyping}
            send={client.sendText}
            textOnly={textOnly}
          />
        )}
      </section>

      {(phase === "review" || phase === "saving" || phase === "saved") && (
        <section
          className="voice-card review-card"
          aria-labelledby="review-title"
        >
          <h2 id="review-title">
            {customerView ? "Make sure we got it right." : "Review and confirm"}
          </h2>
          <p className="section-help">
            {customerView
              ? "Check your contact and service details before you continue. We’ll save them only when you confirm."
              : "Correct every field before saving. Confirmation creates one customer and an immutable intake record, plus an HVAC service request."}
          </p>
          <div className="form-grid">
            <FormField
              disabled={phase !== "review" || confirmationLocked}
              label="Full name"
              name="fullName"
              onChange={(value) => setForm({ ...form, fullName: value })}
              required
              value={form.fullName}
            />
            <FormField
              disabled={phase !== "review" || confirmationLocked}
              label="Email for booking updates (optional)"
              name="email"
              onChange={(value) => setForm({ ...form, email: value })}
              type="email"
              value={form.email}
            />
            <FormField
              disabled={phase !== "review" || confirmationLocked}
              label="Phone"
              name="phone"
              onChange={(value) => setForm({ ...form, phone: value })}
              type="tel"
              value={form.phone}
            />
            {(
              [
                ["addressLine1", "Street address"],
                ["city", "City"],
                ["stateCode", "State (two letters)"],
                ["postalCode", "ZIP code"],
                ["preferredWindow", "Preferred date or window"],
              ] as const
            ).map(([name, label]) => (
              <FormField
                key={name}
                name={name}
                label={label}
                disabled={phase !== "review" || confirmationLocked}
                value={form[name]}
                required
                onChange={(value) => setForm({ ...form, [name]: value })}
              />
            ))}
            <label>
              Service type
              <select
                value={form.serviceKind}
                disabled={phase !== "review" || confirmationLocked}
                onChange={(event) =>
                  setForm({ ...form, serviceKind: event.target.value })
                }
              >
                <option value="AC_REPAIR">AC repair</option>
                <option value="HEATING_REPAIR">Heating repair</option>
                <option value="INSTALLATION">Installation</option>
                <option value="MAINTENANCE">Maintenance</option>
              </select>
            </label>
            <label className="consent-row">
              <input
                type="checkbox"
                checked={form.hazardousCondition}
                disabled={phase !== "review" || confirmationLocked}
                onChange={(event) =>
                  setForm({ ...form, hazardousCondition: event.target.checked })
                }
              />
              Gas odor, smoke, carbon monoxide alarm, or electrical danger
              reported. Leave immediate danger and contact emergency services.
              Do not wait for an appointment.
            </label>
            <label className="wide-field">
              HVAC service request
              <textarea
                disabled={phase !== "review" || confirmationLocked}
                maxLength={2_000}
                onChange={(event) =>
                  setForm({ ...form, intakeIntent: event.target.value })
                }
                required
                value={form.intakeIntent}
              />
            </label>
          </div>
          {phase === "review" && (
            <button
              className="primary-button"
              onClick={() => void saveConfirmedIntake()}
              type="button"
            >
              {confirmationLocked
                ? "Retry confirmation"
                : "Confirm and save service request"}
            </button>
          )}
          {phase === "saving" && <p aria-live="polite">Saving confirmation…</p>}
          {savedIntake?.serviceRequestId && (
            <BrowserBooking
              key={savedIntake.serviceRequestId}
              apiBaseUrl={apiBaseUrl}
              adminToken={adminToken}
              serviceRequestId={savedIntake.serviceRequestId}
              postalCode={form.postalCode}
              hazardous={bookingProgress.hazardous || form.hazardousCondition}
              initialAppointment={voiceAppointment?.appointment}
              initialTimezone={voiceAppointment?.timezone}
              initialFailure={bookingProgress.failure}
              onProgress={(update) => {
                if (sessionIdRef.current === experienceSessionId)
                  setBookingProgress(update);
              }}
              onAppointment={(appointment) => {
                if (sessionIdRef.current === experienceSessionId) {
                  setVoiceAppointment(appointment);
                  onBookingChanged?.();
                }
              }}
            />
          )}
          {savedIntake && (
            <p className="success-message" aria-live="polite">
              {customerView ? (
                `Your service details are saved, ${savedIntake.customerName}. Only a confirmed appointment is booked.`
              ) : (
                <>
                  Saved customer {savedIntake.customerName}. Intake ID:{" "}
                  <code>{savedIntake.conversationIntakeId}</code>
                </>
              )}
            </p>
          )}
        </section>
      )}
    </div>
  );
}

type FormFieldProperties = Readonly<{
  disabled: boolean;
  label: string;
  name: string;
  onChange: (value: string) => void;
  required?: boolean;
  type?: "email" | "tel" | "text";
  value: string;
}>;

function FormField({
  disabled,
  label,
  name,
  onChange,
  required = false,
  type = "text",
  value,
}: FormFieldProperties) {
  return (
    <label>
      {label}
      <input
        disabled={disabled}
        name={name}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        type={type}
        value={value}
      />
    </label>
  );
}
