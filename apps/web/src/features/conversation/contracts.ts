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
  sessionId: string;
  inputMode: ConversationInputMode;
  transport: ConversationTransport;
  credential: string;
  maximumDurationSeconds: number;
  authorizationExpiresAt?: string;
  confirmationExpiresAt: string;
}>;

export type ConfirmedConversationIntake = Readonly<{
  serviceRequestId?: string;
  conversationIntakeId: string;
  customerId: string;
  customerName: string;
  confirmedAt: string;
}>;
