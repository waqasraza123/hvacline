import { useCallback, useEffect, useRef, useState } from "react";
import { AppState } from "react-native";
import { useFocusEffect } from "expo-router";
import { requestRecordingPermissionsAsync } from "expo-audio";
import { useConversation } from "@elevenlabs/react-native";
import {
  appendTranscript,
  customerMessage,
  PendingTextEchoes,
  sessionConnection,
  type BookingProgress,
  type ConversationInputMode,
  type ConversationSpeaker,
  type ConversationTurn,
  type CustomerBookingSession,
  type VoiceAppointment,
  type VoiceBookingTool,
  type VoiceLanguageRegistry,
  type LanguageCode,
  languageSessionOverrides,
  ProviderLanguageObserver,
  type ObservedLanguageResult,
  parseVoiceLanguageRegistry,
} from "@insurance-operations/customer-core";
import { MobileApiError } from "../lib/api";
import { authorization, object, record, string, UUID } from "../lib/models";
import { useSession } from "../lib/session";
import { createBookingSession, intakeDraft } from "./booking-session";
import { TextConnection } from "./text-connection";

const BOOKING_TOOLS: readonly VoiceBookingTool[] = [
  "prepare_intake_confirmation",
  "confirm_service_request",
  "check_appointment_availability",
  "reserve_appointment",
  "confirm_appointment",
  "release_appointment_hold",
];
const INITIAL_PROGRESS: BookingProgress = {
  requestSaved: false,
  awaitingIntakeConfirmation: false,
  hazardous: false,
};
type Phase = "idle" | "connecting" | "connected" | "ended";

export function useBooking() {
  const { api } = useSession();
  const [languageRegistry, setLanguageRegistry] = useState<VoiceLanguageRegistry>();
  const [language, setLanguage] = useState<LanguageCode>("en");
  const [languageError, setLanguageError] = useState("");
  const [observedLanguage, setObservedLanguage] = useState<LanguageCode>();
  const [languageSwitchFailed, setLanguageSwitchFailed] = useState(false);
  const [languageObserver] = useState(() => new ProviderLanguageObserver());
  useEffect(() => {
    if (!api) return;
    let current = true;
    void api.request("voice-languages").then((raw) => {
      const value = parseVoiceLanguageRegistry(raw);
      if (current) { setLanguageRegistry(value); setLanguage(value.effective_defaults.mobile ?? "en"); setLanguageError(""); }
    }).catch(() => { if (current) setLanguageError("Language settings could not be loaded. Reopen this screen before starting."); });
    return () => { current = false; };
  }, [api]);
  const [phase, setPhase] = useState<Phase>("idle"),
    [mode, setMode] = useState<ConversationInputMode>("VOICE");
  const [turns, setTurns] = useState<ConversationTurn[]>([]),
    [progress, setProgress] = useState<BookingProgress>(INITIAL_PROGRESS);
  const [appointment, setAppointment] = useState<VoiceAppointment>(),
    [error, setError] = useState(""),
    [remaining, setRemaining] = useState(0),
    [cleanupId, setCleanupId] = useState<string>();
  const [working, setWorking] = useState(false);
  const mounted = useRef(true),
    focused = useRef(false),
    generation = useRef(0),
    starting = useRef(false);
  const live = useRef<
    { id: string; mode: ConversationInputMode; deadline: number } | undefined
  >(undefined);
  const cleanup = useRef<string | undefined>(undefined);
  const controller = useRef<CustomerBookingSession | undefined>(undefined);
  const socket = useRef<TextConnection | undefined>(undefined);
  const voiceTimer = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );
  const finishRef = useRef<
    (outcome: "COMPLETED" | "INTERRUPTED" | "FAILED") => Promise<void>
  >(async () => undefined);
  const latestProgress = useRef(progress);
  latestProgress.current = progress;
  const echoes = useRef(new PendingTextEchoes());
  const retryTool = useRef<
    { name: VoiceBookingTool; parameters: Record<string, unknown> } | undefined
  >(undefined);
  const toolBusy = useRef(false);
  const requestingMicrophone = useRef(false);

  const recordTurn = (speaker: ConversationSpeaker, text: string) => {
    if (!live.current || !mounted.current) return;
    const normalized = text.trim();
    if (!normalized || normalized.length > 2000) return;
    controller.current?.recordTurn(speaker, normalized);
    setTurns((previous) =>
      appendTranscript(previous, speaker, normalized).slice(-60),
    );
  };

  const executeTool = async (
    name: string,
    parameters: Record<string, unknown>,
  ): Promise<string> => {
    const active = live.current;
    const booking = controller.current;
    if (
      !active ||
      !booking ||
      Date.now() >= active.deadline ||
      !focused.current
    )
      return JSON.stringify({
        ok: false,
        message: "The conversation has ended. Do not claim a save or booking.",
      });
    if (name === "submit_intake_draft")
      return booking.updateDraft(intakeDraft(parameters));
    if (name === "lookup_approved_faq") {
      const query = string(parameters.query);
      if (query.length > 500)
        return JSON.stringify({
          matched: false,
          approved_answer: null,
          fallback_message: "Ask a shorter question or contact the business.",
          source: null,
        });
      const result = object(
        await api!.request(
          `conversation-sessions/${active.id}/approved-faq-lookup`,
          "POST",
          { query },
        ),
      );
      if (
        typeof result.matched !== "boolean" ||
        (result.matched &&
          (typeof result.answer !== "string" || !record(result.source)))
      )
        throw new Error("The approved answer could not be read.");
      return JSON.stringify({
        matched: result.matched,
        approved_answer: result.matched ? result.answer : null,
        fallback_message: string(result.fallback_message),
        source: result.matched ? result.source : null,
      });
    }
    if (
      [
        "retrieve_customer_memory",
        "prepare_customer_memory",
        "remember_customer_memory",
      ].includes(name)
    )
      return JSON.stringify({
        available: false,
        saved: false,
        message:
          "Persistent memory is not enabled in the mobile app. Do not claim to remember or save personal preferences.",
      });
    if (!BOOKING_TOOLS.includes(name as VoiceBookingTool))
      return JSON.stringify({
        ok: false,
        message: "This tool is not available in the mobile app.",
      });
    if (toolBusy.current)
      return JSON.stringify({
        ok: false,
        message: "Wait for the current booking action to finish.",
      });
    toolBusy.current = true;
    const tool = name as VoiceBookingTool;
    retryTool.current = { name: tool, parameters };
    try {
      return JSON.stringify(await booking.execute(tool, parameters));
    } finally {
      toolBusy.current = false;
    }
  };

  function languageResult(result?: ObservedLanguageResult) {
    if (!live.current || !mounted.current) return;
    if (result?.kind === "switched") {
      setObservedLanguage(result.language); setLanguageSwitchFailed(false);
      controller.current?.observeLanguageChange(result.language);
    } else if (result) {
      setObservedLanguage(undefined);
      controller.current?.invalidateReadbacks();
      if (result.kind === "failed") setLanguageSwitchFailed(true);
    }
  }

  const conversation = useConversation({
    onInterruption: () => controller.current?.invalidateReadbacks(),
    onAgentToolRequest: (event) => {
      if (event.tool_name === "language_detection" && event.tool_type === "system") {
        setObservedLanguage(undefined);
        controller.current?.invalidateReadbacks();
      }
    },
    onAgentToolResponse: (event) => languageResult(languageObserver.receive(event)),
    clientTools: Object.fromEntries(
      [
        ...BOOKING_TOOLS,
        "submit_intake_draft",
        "lookup_approved_faq",
        "retrieve_customer_memory",
        "prepare_customer_memory",
        "remember_customer_memory",
      ].map((name) => [
        name,
        (parameters: Record<string, unknown>) => executeTool(name, parameters),
      ]),
    ),
    onMessage: (message) => {
      if (live.current?.mode !== "VOICE") return;
      const speaker = message.source === "user" ? "USER" : "AGENT";
      const text = message.message.trim();
      if (speaker === "USER" && echoes.current.consume(text)) return;
      recordTurn(speaker, text);
    },
    onDisconnect: () => {
      if (live.current?.mode === "VOICE") void finishRef.current("INTERRUPTED");
    },
    onError: () => {
      if (live.current?.mode === "VOICE") {
        if (mounted.current)
          setError(
            "Voice lost its connection. Your saved requests and appointments are kept.",
          );
        void finishRef.current("FAILED");
      }
    },
  });
  const nativeEnd = useRef(conversation.endSession);
  nativeEnd.current = conversation.endSession;

  const markCleanup = (id?: string) => {
    cleanup.current = id;
    if (mounted.current) setCleanupId(id);
  };
  const finish = useCallback(
    async (outcome: "COMPLETED" | "INTERRUPTED" | "FAILED") => {
      generation.current += 1;
      const current = live.current;
      live.current = undefined;
      clearTimeout(voiceTimer.current);
      socket.current?.close();
      socket.current = undefined;
      echoes.current.clear();
      try {
        nativeEnd.current();
      } catch {
        /* Server cleanup must still run after an audio failure. */
      }
      if (mounted.current) {
        setPhase("ended");
        setRemaining(0);
      }
      if (!current || !api) return;
      markCleanup(current.id);
      try {
        await api.request(`conversation-sessions/${current.id}/end`, "POST", {
          outcome,
        });
        if (cleanup.current === current.id) markCleanup();
      } catch {
        if (mounted.current)
          setError(
            "The connection ended, but the server session still needs cleanup. Release the previous session before starting again.",
          );
      }
    },
    [api],
  );
  finishRef.current = finish;

  useEffect(() => {
    mounted.current = true;
    const listener = AppState.addEventListener("change", (state) => {
      if (
        state === "background" ||
        (state !== "active" && !requestingMicrophone.current)
      )
        void finishRef.current("INTERRUPTED");
    });
    return () => {
      mounted.current = false;
      listener.remove();
      void finishRef.current("INTERRUPTED");
    };
  }, []);
  useFocusEffect(
    useCallback(() => {
      focused.current = true;
      return () => {
        focused.current = false;
        void finishRef.current("INTERRUPTED");
      };
    }, []),
  );
  useEffect(() => {
    if (phase !== "connected") return;
    const timer = setInterval(() => {
      const deadline = live.current?.deadline;
      if (!deadline) return;
      const seconds = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setRemaining(seconds);
      if (!seconds) void finishRef.current("INTERRUPTED");
    }, 500);
    return () => clearInterval(timer);
  }, [phase]);

  async function start(inputMode: ConversationInputMode) {
    if (!languageRegistry || languageError) { setError(languageError || "Wait for language settings to load."); return; }
    if (!languageRegistry.languages.some((item) => item.channel === "mobile" && item.code === language && item.available)) {
      setError("This language is not configured for mobile. Choose an available language or contact staff."); return;
    }
    if (
      !api ||
      starting.current ||
      live.current ||
      cleanup.current ||
      toolBusy.current ||
      !focused.current ||
      latestProgress.current.failure?.uncertain
    )
      return;
    starting.current = true;
    const current = ++generation.current;
    setError("");
    setPhase("connecting");
    setMode(inputMode);
    try {
      if (inputMode === "VOICE") {
        requestingMicrophone.current = true;
        try {
          const permission = await requestRecordingPermissionsAsync();
          if (!permission.granted)
            throw new Error(
              "Microphone access is needed for Voice. Enable it in device settings, or choose Chat.",
            );
        } finally {
          requestingMicrophone.current = false;
        }
      }
      if (current !== generation.current || !focused.current) return;
      const raw = await api.request("conversation-sessions", "POST", {
        language,
        voice_channel: "mobile",
        input_mode: inputMode,
        ai_disclosure_accepted: true,
        microphone_consent_granted: inputMode === "VOICE",
      });
      const rawId =
        record(raw) &&
        typeof raw.session_id === "string" &&
        UUID.test(raw.session_id)
          ? raw.session_id
          : undefined;
      if (rawId) markCleanup(rawId);
      if (current !== generation.current || !focused.current) {
        if (rawId) {
          await api.request(`conversation-sessions/${rawId}/end`, "POST", {
            outcome: "INTERRUPTED",
          });
          if (cleanup.current === rawId) markCleanup();
        }
        return;
      }
      const grant = authorization(raw, inputMode);
      languageObserver.start(grant.voiceLanguage);
      setObservedLanguage(undefined); setLanguageSwitchFailed(false);
      const active = {
        id: grant.sessionId,
        mode: inputMode,
        deadline: Math.min(
          Date.parse(grant.authorizationExpiresAt!),
          Date.now() + grant.maximumDurationSeconds * 1000,
        ),
      };
      live.current = active;
      markCleanup();
      setTurns([]);
      setAppointment(undefined);
      setProgress(INITIAL_PROGRESS);
      retryTool.current = undefined;
      controller.current = createBookingSession({
        initialLanguage: grant.voiceLanguage?.language,
        api,
        sessionId: grant.sessionId,
        isActive: () =>
          live.current === active &&
          focused.current &&
          Date.now() < active.deadline,
        onProgress: (value) => {
          if (mounted.current && controller.current) {
            latestProgress.current = value;
            setProgress(value);
          }
        },
        onAppointment: (value) => {
          if (mounted.current) setAppointment(value);
        },
        onSaved: () => undefined,
      });
      const connected = () => {
        if (
          current !== generation.current ||
          live.current !== active ||
          !focused.current
        ) {
          nativeEnd.current();
          return;
        }
        clearTimeout(voiceTimer.current);
        setPhase("connected");
        setRemaining(
          Math.max(0, Math.ceil((active.deadline - Date.now()) / 1000)),
        );
      };
      if (inputMode === "TEXT") {
        const connection = new TextConnection({
          credential: grant.credential,
          voiceLanguage: grant.voiceLanguage,
          onLanguageResult: languageResult,
          onReadbackInterrupted: () => { setObservedLanguage(undefined); controller.current?.invalidateReadbacks(); },
          onConnect: connected,
          onTurn: recordTurn,
          onTool: executeTool,
          onDisconnect: () => {
            if (live.current === active) void finishRef.current("INTERRUPTED");
          },
          onError: (message) => {
            if (live.current === active) {
              setError(message);
              void finishRef.current("FAILED");
            }
          },
        });
        socket.current = connection;
        connection.connect();
      } else {
        const connection = sessionConnection(grant);
        if (connection.connectionType !== "webrtc")
          throw new Error("Voice requires a native WebRTC connection.");
        voiceTimer.current = setTimeout(() => {
          if (live.current === active) {
            setError("Voice could not connect in time. Try again.");
            void finishRef.current("FAILED");
          }
        }, 20_000);
        conversation.startSession({
          ...connection,
          ...languageSessionOverrides(grant.voiceLanguage),
          dynamicVariables: { homepage_guest: false },
          onConnect: connected,
        });
      }
    } catch (failure) {
      if (current === generation.current && mounted.current) {
        setError(
          failure instanceof Error
            ? failure.message
            : "Line could not connect.",
        );
        setPhase("ended");
        if (
          failure instanceof MobileApiError &&
          failure.code === "CONVERSATION_ALREADY_ACTIVE" &&
          typeof failure.details?.previous_session_id === "string" &&
          UUID.test(failure.details.previous_session_id)
        )
          markCleanup(failure.details.previous_session_id);
        if (live.current) await finish("FAILED");
      }
    } finally {
      starting.current = false;
    }
  }

  async function releasePrevious() {
    const id = cleanup.current;
    if (!id || !api || working) return;
    setWorking(true);
    setError("");
    try {
      await api.request(`conversation-sessions/${id}/end`, "POST", {
        outcome: "INTERRUPTED",
      });
      if (cleanup.current === id) markCleanup();
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "The previous session could not be released.",
      );
    } finally {
      setWorking(false);
    }
  }

  const sendText = (value: string) => {
    if (
      phase !== "connected" ||
      !live.current ||
      Date.now() >= live.current.deadline
    )
      throw new Error("Wait for Line to connect before sending.");
    const text = customerMessage(value);
    if (live.current.mode === "TEXT") socket.current?.sendText(text);
    else {
      echoes.current.add(text);
      try {
        conversation.sendUserMessage(text);
      } catch (failure) {
        echoes.current.consume(text);
        throw failure;
      }
      recordTurn("USER", text);
    }
  };
  const notifyTyping = () => {
    if (phase !== "connected") return;
    try {
      if (live.current?.mode === "TEXT") socket.current?.notifyTyping();
      else conversation.sendUserActivity();
    } catch {
      /* A typing signal must not discard the draft. */
    }
  };
  const retry = async () => {
    if (!retryTool.current || phase !== "connected") return;
    const value = retryTool.current;
    await executeTool(value.name, value.parameters);
  };
  return {
    languageRegistry, language, setLanguage, languageError, observedLanguage, languageSwitchFailed,
    phase,
    mode,
    turns,
    progress,
    appointment,
    error,
    remaining,
    cleanupId,
    working,
    start,
    finish,
    releasePrevious,
    sendText,
    notifyTyping,
    retry,
    muted: conversation.isMuted,
    setMuted: conversation.setMuted,
    speaking:
      phase === "connected" && mode === "VOICE" && conversation.isSpeaking,
  };
}
