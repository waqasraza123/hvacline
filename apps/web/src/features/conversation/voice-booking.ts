import {
  CustomerBookingSession,
  type BookingSessionOptions,
} from "@insurance-operations/customer-core";
import { ConversationApiError, confirmConversationIntake } from "./api";
import { OperationsApiError, requestApi } from "../operations/api";
import { bookingFailure, bookingRequiresStaffReview } from "./booking-progress";
export type {
  VoiceAppointment,
  VoiceBookingTool,
} from "@insurance-operations/customer-core";

type SessionOptions = Pick<
  BookingSessionOptions,
  "sessionId" | "isActive" | "onSaved" | "onAppointment" | "onProgress"
> &
  Readonly<{ apiBaseUrl: string; adminToken?: string }>;

export class VoiceBookingSession extends CustomerBookingSession {
  constructor(options: SessionOptions) {
    super({
      ...options,
      request: <T>(path: string, body: unknown) =>
        requestApi<T>(
          options.apiBaseUrl,
          options.adminToken ?? "",
          `conversation-sessions/${options.sessionId}/booking/${path}`,
          "POST",
          body,
        ),
      confirmIntake: (input) =>
        confirmConversationIntake(
          options.apiBaseUrl,
          input,
          options.adminToken,
        ),
      randomUUID: () => crypto.randomUUID(),
      classifyFailure: bookingFailure,
      requiresStaffReview: bookingRequiresStaffReview,
      isValidationFailure: (error) =>
        error instanceof ConversationApiError && error.status === 422,
      isRejectedReservation: (error) =>
        error instanceof OperationsApiError &&
        [400, 404, 409, 410, 422].includes(error.status),
    });
  }
}
