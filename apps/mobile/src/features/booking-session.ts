import {
  CustomerBookingSession,
  intakePayload,
  type BookingFailure,
  type BookingProgress,
  type VoiceAppointment,
  type VoiceBookingTool,
  type ConversationDraft,
  type LanguageCode,
} from "@insurance-operations/customer-core";
import { randomUUID } from "expo-crypto";
import { MobileApi, MobileApiError } from "../lib/api";
import {
  availability,
  confirmedIntake,
  object,
  string,
  voiceAppointment,
} from "../lib/models";

const REVIEW_CODES = new Set([
  "GHL_APPOINTMENT_CREATION_UNKNOWN",
  "GHL_APPOINTMENT_OWNERSHIP_INVALID",
  "GHL_LOCAL_CONFIRMATION_REQUIRED",
  "GHL_BOOKING_REVIEW_REQUIRED",
  "GHL_CONTACT_CREATION_UNKNOWN",
]);
export function requiresStaffReview(error: unknown) {
  return error instanceof MobileApiError && REVIEW_CODES.has(error.code ?? "");
}
export function classifyFailure(
  operation: VoiceBookingTool,
  error: unknown,
  requestStarted = true,
): BookingFailure {
  const status = error instanceof MobileApiError ? error.status : 0;
  const staffReview = requiresStaffReview(error);
  const uncertain =
    requestStarted &&
    [
      "confirm_service_request",
      "reserve_appointment",
      "confirm_appointment",
      "release_appointment_hold",
    ].includes(operation) &&
    (!status || status >= 500 || status === 408 || staffReview);
  return {
    operation,
    uncertain,
    staffReview,
    message: staffReview
      ? "This booking needs staff review. Contact the business before selecting another appointment."
      : uncertain
        ? "The result is uncertain. Retry this same step while connected. Check your appointments before starting another booking."
        : error instanceof Error
          ? error.message
          : "This step could not be completed. Ask Line to correct the details or retry.",
  };
}

export function createBookingSession(options: {
  initialLanguage?: LanguageCode;
  api: MobileApi;
  sessionId: string;
  isActive: () => boolean;
  onProgress: (value: BookingProgress) => void;
  onAppointment: (value: VoiceAppointment | undefined) => void;
  onSaved: () => void;
}) {
  return new CustomerBookingSession({
    ...options,
    randomUUID,
    request: async <T>(path: string, body: unknown): Promise<T> => {
      const result = await options.api.request(
        `conversation-sessions/${options.sessionId}/booking/${path}`,
        "POST",
        body,
      );
      if (path === "availability") return availability(result) as T;
      if (path === "reservations" || path.endsWith("/confirm"))
        return voiceAppointment(result) as T;
      if (path === "intake-readback") {
        const data = object(result);
        string(data.readback);
      }
      return result as T;
    },
    confirmIntake: async (input) =>
      confirmedIntake(
        await options.api.request(
          "conversation-intakes",
          "POST",
          intakePayload(input),
          input.idempotencyKey,
        ),
      ),
    classifyFailure,
    requiresStaffReview,
    isValidationFailure: (error) =>
      error instanceof MobileApiError && error.status === 422,
    isRejectedReservation: (error) =>
      error instanceof MobileApiError &&
      [400, 404, 409, 410, 422].includes(error.status),
  });
}

export function intakeDraft(
  parameters: Record<string, unknown>,
): ConversationDraft {
  const optional = (key: string) =>
    typeof parameters[key] === "string" && parameters[key].trim()
      ? parameters[key].trim()
      : undefined;
  return {
    fullName: optional("full_name"),
    email:
      typeof parameters.email === "string"
        ? parameters.email.trim()
        : undefined,
    phone: optional("phone"),
    intakeIntent: optional("intake_intent"),
    addressLine1: optional("address_line1"),
    city: optional("city"),
    stateCode: optional("state_code"),
    postalCode: optional("postal_code"),
    serviceKind: optional("service_kind"),
    preferredWindow: optional("preferred_window"),
    hazardousCondition:
      typeof parameters.hazardous_condition === "boolean"
        ? parameters.hazardous_condition
        : undefined,
  };
}
