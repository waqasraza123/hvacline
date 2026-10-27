"use client";

import {
  ConversationProvider,
  useConversation,
  useConversationControls,
} from "@elevenlabs/react";
import { useRef } from "react";
import type { ReactNode } from "react";
import { sessionConnection } from "./connection";
import { customerMessage, PendingTextEchoes } from "./text-messages";
import { appendTranscript } from "./review";
import type { VoiceBookingTool } from "./voice-booking";

import type {
  ApprovedFaqToolLookup,
  ConversationClient,
  ConversationDraft,
  ConversationSpeaker,
  ConversationTurn,
} from "./contracts";

type AdapterProperties = Readonly<{
  children: (client: ConversationClient) => ReactNode;
  onDisconnect: () => void;
  onDraft: (draft: ConversationDraft) => Promise<string>;
  onError: (message: string) => void;
  onApprovedFaqLookup: ApprovedFaqToolLookup;
  onTranscript: (speaker: ConversationSpeaker, text: string) => void;
  onBookingTool: (
    tool: VoiceBookingTool,
    parameters: Record<string, unknown>,
  ) => Promise<string>;
}>;

type IntakeToolParameters = Readonly<{
  full_name?: unknown;
  email?: unknown;
  phone?: unknown;
  intake_intent?: unknown;
  address_line1?: unknown;
  city?: unknown;
  state_code?: unknown;
  postal_code?: unknown;
  service_kind?: unknown;
  preferred_window?: unknown;
  hazardous_condition?: unknown;
}>;

type ApprovedFaqToolParameters = Readonly<{
  query?: unknown;
}>;

export function ElevenLabsConversationAdapter(properties: AdapterProperties) {
  return (
    <ConversationProvider>
      <AdapterBridge {...properties} />
    </ConversationProvider>
  );
}

function AdapterBridge({
  children,
  onDisconnect,
  onDraft,
  onError,
  onApprovedFaqLookup,
  onTranscript,
  onBookingTool,
}: AdapterProperties) {
  const controls = useConversationControls();
  const pendingTextEchoes = useRef(new PendingTextEchoes());
  const memorySessionId = useRef<string | undefined>(undefined);
  const memoryTurns = useRef<ConversationTurn[]>([]);
  async function memoryTool(
    action: "context" | "readback" | "remember",
    parameters: Record<string, unknown> = {},
  ): Promise<string> {
    const sessionId = memorySessionId.current;
    if (!sessionId) return JSON.stringify({ available: false });
    try {
      const response = await fetch(
        `/api/v1/development/conversation-sessions/${encodeURIComponent(sessionId)}/memory/${action}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: AbortSignal.timeout(15000),
          body: JSON.stringify(action === "remember"
            ? { ...parameters, transcript: memoryTurns.current }
            : parameters),
        },
      );
      if (!response.ok) return JSON.stringify({
        available: false,
        message: "Memory was not saved or retrieved. Continue booking or use Memory settings.",
      });
      return response.status === 204
        ? JSON.stringify({ saved: true }) : await response.text();
    } catch {
      return JSON.stringify({ available: false });
    }
  }
  const conversation = useConversation({
    clientTools: {
      retrieve_customer_memory: () => memoryTool("context"),
      prepare_customer_memory: (parameters: Record<string, unknown>) =>
        memoryTool("readback", parameters),
      remember_customer_memory: (parameters: Record<string, unknown>) =>
        memoryTool("remember", parameters),
      lookup_approved_faq: async (parameters: ApprovedFaqToolParameters) => {
        const query = optionalString(parameters.query);
        if (query === undefined) {
          return JSON.stringify({
            matched: false,
            approved_answer: null,
            fallback_message: "Ask a human team member to follow up.",
            source: null,
          });
        }
        const result = await onApprovedFaqLookup(query);
        return JSON.stringify({
          matched: result.matched,
          approved_answer: result.answer,
          fallback_message: result.fallbackMessage,
          source:
            result.source === null
              ? null
              : {
                  faq_id: result.source.faqId,
                  question: result.source.question,
                  row_version: result.source.rowVersion,
                },
        });
      },
      submit_intake_draft: async (parameters: IntakeToolParameters) => {
        try {
          return await onDraft({
            fullName: optionalString(parameters.full_name),
            email:
              typeof parameters.email === "string"
                ? parameters.email.trim()
                : undefined,
            phone: optionalString(parameters.phone),
            intakeIntent: optionalString(parameters.intake_intent),
            addressLine1: optionalString(parameters.address_line1),
            city: optionalString(parameters.city),
            stateCode: optionalString(parameters.state_code),
            postalCode: optionalString(parameters.postal_code),
            serviceKind: optionalString(parameters.service_kind),
            preferredWindow: optionalString(parameters.preferred_window),
            hazardousCondition:
              typeof parameters.hazardous_condition === "boolean"
                ? parameters.hazardous_condition
                : undefined,
          });
        } catch {
          return JSON.stringify({
            ok: false,
            message:
              "The draft or hazard update failed. Do not book an appointment. Retry submit_intake_draft.",
          });
        }
      },
      prepare_intake_confirmation: (parameters: Record<string, unknown>) =>
        onBookingTool("prepare_intake_confirmation", parameters),
      confirm_service_request: (parameters: Record<string, unknown>) =>
        onBookingTool("confirm_service_request", parameters),
      check_appointment_availability: (parameters: Record<string, unknown>) =>
        onBookingTool("check_appointment_availability", parameters),
      reserve_appointment: (parameters: Record<string, unknown>) =>
        onBookingTool("reserve_appointment", parameters),
      confirm_appointment: (parameters: Record<string, unknown>) =>
        onBookingTool("confirm_appointment", parameters),
      release_appointment_hold: (parameters: Record<string, unknown>) =>
        onBookingTool("release_appointment_hold", parameters),
    },
    onDisconnect: () => {
      memorySessionId.current = undefined;
      memoryTurns.current = [];
      pendingTextEchoes.current.clear();
      onDisconnect();
    },
    onError: (message) => {
      memorySessionId.current = undefined;
      memoryTurns.current = [];
      onError(
        typeof message === "string"
          ? message
          : "Conversation connection failed",
      );
      controls.endSession();
    },
    onMessage: (message) => {
      const speaker = message.source === "user" ? "USER" : "AGENT";
      const text = message.message.trim();
      if (text) {
        if (speaker === "USER" && pendingTextEchoes.current.consume(text))
          return;
        memoryTurns.current = appendTranscript(memoryTurns.current, speaker, text).slice(-60);
        onTranscript(speaker, text);
      }
    },
  });

  const client: ConversationClient = {
    status:
      conversation.status === "error" ? "disconnected" : conversation.status,
    mode: conversation.mode,
    isMuted: conversation.isMuted,
    start: async (authorization) => {
      memorySessionId.current = authorization.sessionId;
      memoryTurns.current = [];
      pendingTextEchoes.current.clear();
      const connection = sessionConnection(authorization);
      await new Promise<void>((resolve, reject) => {
        const timer = window.setTimeout(() => {
          controls.endSession();
          reject(
            new Error("Conversation connection timed out. Try a new session."),
          );
        }, 20_000);
        const fail = () => {
          memorySessionId.current = undefined;
          memoryTurns.current = [];
          window.clearTimeout(timer);
          reject(
            new Error("Conversation connection could not be established."),
          );
        };
        try {
          conversation.startSession({
            ...connection,
            onConnect: () => {
              window.clearTimeout(timer);
              resolve();
            },
            onError: fail,
            onDisconnect: fail,
          });
        } catch (failure) {
          window.clearTimeout(timer);
          reject(failure);
        }
      });
    },
    end: async () => {
      memorySessionId.current = undefined;
      memoryTurns.current = [];
      pendingTextEchoes.current.clear();
      await conversation.endSession();
    },
    sendText: (value) => {
      if (conversation.status !== "connected")
        throw new Error("Connect to Line before sending a message.");
      const text = customerMessage(value);
      pendingTextEchoes.current.add(text);
      try {
        conversation.sendUserMessage(text);
      } catch (error) {
        pendingTextEchoes.current.consume(text);
        throw error;
      }
      memoryTurns.current = appendTranscript(memoryTurns.current, "USER", text).slice(-60);
      onTranscript("USER", text);
    },
    notifyTyping: () => {
      if (conversation.status === "connected") {
        try {
          controls.sendUserActivity();
        } catch {
          // A typing signal must not discard the customer's draft on disconnect.
        }
      }
    },
    setMuted: conversation.setMuted,
  };

  return children(client);
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}
