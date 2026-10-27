import type {
  ConfirmedConversationIntake,
  ConversationInputMode,
  ConversationSessionAuthorization,
  ConversationTurn,
} from "./contracts";

type ErrorBody = Readonly<{
  error?: Readonly<{
    message?: unknown;
    code?: unknown;
    details?: unknown;
  }>;
}>;

const REQUEST_TIMEOUT_MILLISECONDS = 15_000;

export class ConversationApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly previousSessionId?: string;
  readonly retryAfterSeconds?: number;

  constructor(
    status: number,
    message: string,
    recovery: {
      code?: string;
      previousSessionId?: string;
      retryAfterSeconds?: number;
    } = {},
  ) {
    super(message);
    this.name = "ConversationApiError";
    this.status = status;
    this.code = recovery.code;
    this.previousSessionId = recovery.previousSessionId;
    this.retryAfterSeconds = recovery.retryAfterSeconds;
  }
}

export async function authorizeConversationSession(
  apiBaseUrl: string,
  adminToken?: string,
  inputMode: ConversationInputMode = "VOICE",
): Promise<ConversationSessionAuthorization> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/development/conversation-sessions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(adminToken ? { "X-Demo-Admin-Token": adminToken } : {}),
      },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MILLISECONDS),
      body: JSON.stringify({
        input_mode: inputMode,
        ai_disclosure_accepted: true,
        microphone_consent_granted: inputMode === "VOICE",
        synthetic_data_acknowledged: true,
      }),
    },
  );
  const body: unknown = await readJson(response);
  if (!response.ok) {
    throw apiError(response, body);
  }
  if (!isRecord(body) || !isRecord(body.connection)) {
    throw new ConversationApiError(
      502,
      "The conversation service returned invalid data",
    );
  }
  const sessionId = requiredString(body.session_id);
  const authorizedInputMode = body.input_mode ?? "VOICE";
  const transport = body.connection.transport;
  const credential = requiredString(body.connection.credential);
  const maximumDurationSeconds = body.maximum_duration_seconds;
  const authorizationExpiresAt = requiredString(body.authorization_expires_at);
  const confirmationExpiresAt = requiredString(body.confirmation_expires_at);
  if (
    sessionId === undefined ||
    authorizedInputMode !== inputMode ||
    (transport !== "webrtc" && transport !== "websocket") ||
    transport !== (inputMode === "TEXT" ? "websocket" : "webrtc") ||
    credential === undefined ||
    confirmationExpiresAt === undefined ||
    typeof maximumDurationSeconds !== "number" ||
    !Number.isInteger(maximumDurationSeconds) ||
    maximumDurationSeconds < 1 ||
    maximumDurationSeconds > 180 ||
    (authorizationExpiresAt !== undefined &&
      !Number.isFinite(Date.parse(authorizationExpiresAt)))
  ) {
    if (sessionId !== undefined) {
      await endConversationSession(
        apiBaseUrl,
        sessionId,
        "FAILED",
        adminToken,
      ).catch(() => undefined);
    }
    throw new ConversationApiError(
      502,
      "The conversation service returned invalid data",
    );
  }
  return {
    sessionId,
    inputMode,
    transport,
    credential,
    maximumDurationSeconds,
    authorizationExpiresAt,
    confirmationExpiresAt,
  };
}

export async function endConversationSession(
  apiBaseUrl: string,
  sessionId: string,
  outcome: "COMPLETED" | "INTERRUPTED" | "FAILED",
  adminToken?: string,
): Promise<boolean> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/development/conversation-sessions/${sessionId}/end`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(adminToken ? { "X-Demo-Admin-Token": adminToken } : {}),
      },
      keepalive: true,
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MILLISECONDS),
      body: JSON.stringify({ outcome }),
    },
  );
  const body: unknown = await readJson(response);
  if (!response.ok) {
    throw apiError(response, body);
  }
  if (!isRecord(body) || typeof body.review_available !== "boolean") {
    throw new ConversationApiError(
      502,
      "The conversation service returned invalid data",
    );
  }
  return body.review_available;
}

export type ConfirmationInput = Readonly<{
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

export async function confirmConversationIntake(
  apiBaseUrl: string,
  input: ConfirmationInput,
  adminToken?: string,
): Promise<ConfirmedConversationIntake> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/development/conversation-intakes`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": input.idempotencyKey,
        ...(adminToken ? { "X-Demo-Admin-Token": adminToken } : {}),
      },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MILLISECONDS),
      body: JSON.stringify(intakePayload(input)),
    },
  );
  const body: unknown = await readJson(response);
  if (!response.ok) {
    throw apiError(response, body);
  }
  if (!isRecord(body) || !isRecord(body.customer)) {
    throw new ConversationApiError(
      502,
      "The intake service returned invalid data",
    );
  }
  const conversationIntakeId = requiredString(body.conversation_intake_id);
  const customerId = requiredString(body.customer.id);
  const customerName = requiredString(body.customer.full_name);
  const confirmedAt = requiredString(body.confirmed_at);
  if (
    conversationIntakeId === undefined ||
    customerId === undefined ||
    customerName === undefined ||
    confirmedAt === undefined
  ) {
    throw new ConversationApiError(
      502,
      "The intake service returned invalid data",
    );
  }
  return {
    conversationIntakeId,
    customerId,
    customerName,
    confirmedAt,
    serviceRequestId: requiredString(body.service_request_id),
  };
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

function apiError(response: Response, body: unknown): ConversationApiError {
  const errorBody = isRecord(body) ? (body as ErrorBody) : undefined;
  const message = errorBody?.error?.message;
  const code = requiredString(errorBody?.error?.code);
  const details = errorBody?.error?.details;
  const recovery =
    isRecord(details) && code === "CONVERSATION_ALREADY_ACTIVE" ? details : {};
  const previousSessionId = requiredString(recovery.previous_session_id);
  const seconds = recovery.retry_after_seconds;
  return new ConversationApiError(
    response.status,
    typeof message === "string" && message.trim()
      ? message
      : "The request could not be completed",
    {
      code,
      previousSessionId:
        previousSessionId !== undefined &&
        /^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(previousSessionId)
          ? previousSessionId
          : undefined,
      retryAfterSeconds:
        typeof seconds === "number" &&
        Number.isInteger(seconds) &&
        seconds > 0 &&
        seconds <= 86_400
          ? seconds
          : undefined,
    },
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function requiredString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}
