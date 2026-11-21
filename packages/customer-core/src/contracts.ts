import type { LanguageCode, VoiceLanguageSession } from "./voice-languages";

export type ConversationSpeaker = "USER" | "AGENT";

export type ConversationTurn = Readonly<{
  speaker: ConversationSpeaker;
  text: string;
}>;

export type ConversationDraft = Readonly<{
  fullName?: string;
  email?: string;
  phone?: string;
  intakeIntent?: string;
  addressLine1?: string;
  city?: string;
  stateCode?: string;
  postalCode?: string;
  serviceKind?: string;
  preferredWindow?: string;
  hazardousCondition?: boolean;
  handoffRequested?: boolean;
}>;

export type ApprovedFaqToolResult = Readonly<{
  matched: boolean;
  answer: string | null;
  fallbackMessage: string;
  source: Readonly<{
    faqId: string;
    question: string;
    rowVersion: number;
  }> | null;
}>;

export type ApprovedFaqToolLookup = (
  query: string,
) => Promise<ApprovedFaqToolResult>;

export type ConversationConnectionStatus =
  "disconnected" | "connecting" | "connected";

export type ConversationMode = "speaking" | "listening" | undefined;
export type ConversationInputMode = "VOICE" | "TEXT";
export type ConversationTransport = "webrtc" | "websocket";

export type ConversationClient = Readonly<{
  observedLanguage?: LanguageCode;
  languageSwitchFailed?: boolean;
  status: ConversationConnectionStatus;
  mode: ConversationMode;
  isMuted: boolean;
  start: (
    authorization: ConversationSessionAuthorization,
    backgroundContext?: string,
  ) => Promise<void>;
  sendText: (text: string) => void;
  notifyTyping: () => void;
  end: () => Promise<void>;
  setMuted: (muted: boolean) => void;
}>;

export type ConversationSessionAuthorization = Readonly<{
  voiceLanguage?: VoiceLanguageSession;
  provider?: "elevenlabs" | "local";
  websocketPath?: string;
  sessionId: string;
  inputMode: ConversationInputMode;
  transport: ConversationTransport;
  credential: string;
  maximumDurationSeconds: number;
  authorizationExpiresAt?: string;
  confirmationExpiresAt: string;
}>;

export type ConfirmedConversationIntake = Readonly<{
  leadId?: string;
  serviceRequestId?: string;
  conversationIntakeId: string;
  customerId: string;
  customerName: string;
  confirmedAt: string;
}>;

export type Appointment = {
  id: string;
  service_request_id: string;
  team_key: string;
  starts_at: string;
  ends_at: string;
  status: string;
  hold_expires_at: string;
};
export type Slot = { team_key: string; starts_at: string; ends_at: string };
export type Availability = {
  configured: boolean;
  in_service_area: boolean;
  timezone: string | null;
  slots: Slot[];
  message: string | null;
};

export type ConfirmationInput = Readonly<{
  readbackLanguage?: LanguageCode;
  sessionId: string;
  fullName: string;
  email: string;
  phone: string;
  intakeIntent: string;
  transcript: readonly ConversationTurn[];
  idempotencyKey: string;
  addressLine1: string;
  city: string;
  stateCode: string;
  postalCode: string;
  serviceKind: string;
  preferredWindow: string;
  hazardousCondition: boolean;
  spokenConfirmation?: boolean;
}>;

export function intakePayload(input: ConfirmationInput) {
  return {
    ...(input.readbackLanguage ? { readback_language: input.readbackLanguage } : {}),
    conversation_session_id: input.sessionId,
    customer: {
      full_name: input.fullName,
      email: input.email || null,
      phone: input.phone || null,
      address: {
        line1: input.addressLine1,
        city: input.city,
        state_code: input.stateCode,
        postal_code: input.postalCode,
        country_code: "US",
      },
    },
    intake_intent: input.intakeIntent,
    service: {
      kind: input.serviceKind,
      equipment_issue: input.intakeIntent,
      preferred_window: input.preferredWindow,
      hazardous_condition: input.hazardousCondition,
    },
    spoken_confirmation: input.spokenConfirmation ?? false,
    transcript: input.transcript,
  };
}

export type VoiceBookingTool =
  | "prepare_intake_confirmation"
  | "confirm_service_request"
  | "check_appointment_availability"
  | "reserve_appointment"
  | "confirm_appointment"
  | "release_appointment_hold";

export type VoiceAppointment = Readonly<{
  appointment: Appointment;
  timezone: string;
  readback: string;
}>;

export type BookingFailure = Readonly<{
  operation: VoiceBookingTool;
  message: string;
  uncertain: boolean;
  staffReview?: boolean;
}>;

export type BookingProgress = Readonly<{
  requestSaved: boolean;
  awaitingIntakeConfirmation: boolean;
  hazardous: boolean;
  serviceKind?: string;
  pending?: VoiceBookingTool;
  failure?: BookingFailure;
  availability?: Availability;
}>;
