import { ConversationApiError } from "./api";
import { OperationsApiError } from "../operations/api";
import type { Availability } from "../operations/api";
import type { ConversationClient, ConversationInputMode } from "./contracts";
import type { ConversationPhase } from "./lifecycle";
import type { VoiceAppointment, VoiceBookingTool } from "./voice-booking";

export type BookingFailure = Readonly<{
  operation: VoiceBookingTool;
  message: string;
  uncertain: boolean;
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

export const INITIAL_BOOKING_PROGRESS: BookingProgress = {
  requestSaved: false,
  awaitingIntakeConfirmation: false,
  hazardous: false,
};

export const BOOKING_STAGES = [
  "Your details",
  "Confirm details",
  "Choose a time",
  "Appointment confirmed",
] as const;

const OPERATIONS: Record<VoiceBookingTool, string> = {
  prepare_intake_confirmation: "Preparing your details…",
  confirm_service_request: "Saving your request…",
  check_appointment_availability: "Checking availability…",
  reserve_appointment: "Holding your selected time…",
  confirm_appointment: "Confirming your appointment…",
  release_appointment_hold: "Releasing your temporary hold…",
};

export function bookingFailure(
  operation: VoiceBookingTool,
  failure: unknown,
  requestStarted = true,
): BookingFailure {
  const status =
    failure instanceof ConversationApiError ||
    failure instanceof OperationsApiError
      ? failure.status
      : undefined;
  const uncertain =
    requestStarted &&
    [
      "confirm_service_request",
      "reserve_appointment",
      "confirm_appointment",
      "release_appointment_hold",
    ].includes(operation) &&
    (status === undefined || status >= 500 || status === 408);
  const message = uncertain
    ? "We couldn’t establish the result. Retry the same action with Line before choosing something else. Saved requests and confirmed appointments are kept."
    : operation === "confirm_service_request" && status === 422
      ? "Your details still need confirmation. Wait for Line’s complete readback, then confirm or correct the details."
      : operation === "confirm_appointment" && status === 422
        ? "The appointment still needs confirmation. Wait for the full date and time readback, then confirm."
        : "This step could not be completed. Ask Line to correct the details or retry. No new success has been established.";
  return { operation, message, uncertain };
}

export function holdRemainingSeconds(
  value: VoiceAppointment | undefined,
  now: number,
): number {
  if (value?.appointment.status !== "HELD") return 0;
  const expires = Date.parse(value.appointment.hold_expires_at);
  return Number.isFinite(expires)
    ? Math.max(0, Math.ceil((expires - now) / 1000))
    : 0;
}

export function bookingPresentation(
  progress: BookingProgress,
  value: VoiceAppointment | undefined,
  now: number,
) {
  const confirmed = value?.appointment.status === "CONFIRMED";
  const remaining = holdRemainingSeconds(value, now);
  const stage = confirmed
    ? 3
    : progress.requestSaved
      ? 2
      : progress.awaitingIntakeConfirmation
        ? 1
        : 0;
  const failedStage = progress.failure
    ? ["prepare_intake_confirmation", "confirm_service_request"].includes(
        progress.failure.operation,
      )
      ? 1
      : 2
    : undefined;
  let message = progress.requestSaved
    ? "Your request is saved. Choose an available time with Line; no appointment is booked yet."
    : progress.awaitingIntakeConfirmation
      ? "Waiting for your confirmation. Review Line’s complete readback, then confirm or correct your details."
      : "Tell Line what you need. Your details are a draft until you confirm them.";
  if (value?.appointment.status === "HELD") {
    message =
      remaining > 0
        ? "Temporarily held—confirmation required. Wait for Line’s full date and time readback, then confirm."
        : "Your temporary hold has expired. Ask Line to release it and check availability again.";
  } else if (value?.appointment.status === "EXPIRED") {
    message = "Your temporary hold has expired. Choose a new available time.";
  } else if (value?.appointment.status === "CANCELLED") {
    message =
      "This appointment is cancelled. No appointment is booked for this selection.";
  } else if (progress.availability && !confirmed) {
    message = !progress.availability.configured
      ? "Online scheduling is not configured for this business. No appointment has been booked."
      : !progress.availability.in_service_area
        ? "The service address is outside the configured booking area. No appointment has been booked."
        : progress.availability.slots.length === 0
          ? "No times are available for this date. Ask Line to check another date."
          : "Available times found. Choose one of the times Line offers.";
  }
  if (progress.pending) message = OPERATIONS[progress.pending];
  if (progress.failure?.uncertain)
    message =
      "The last action has an unresolved result. Retry that same action before continuing.";
  if (confirmed) message = "Your appointment is confirmed and saved.";
  if (progress.hazardous)
    message =
      "Your request needs human attention. Leave immediate danger and contact emergency services. Do not wait for an appointment. No new appointment can be booked here.";
  return { stage, failedStage, confirmed, remaining, message };
}

export function conversationActivity(
  phase: ConversationPhase,
  client: Pick<ConversationClient, "status" | "mode" | "isMuted">,
  inputMode: ConversationInputMode,
): string {
  if (phase === "idle")
    return inputMode === "TEXT"
      ? "Ready to chat · microphone off"
      : "Ready for voice";
  if (phase === "requesting")
    return inputMode === "TEXT"
      ? "Authorizing chat…"
      : "Requesting microphone access and authorization…";
  if (phase === "connecting") return "Connecting securely…";
  if (phase === "stopping") return "Ending the conversation…";
  if (phase === "active") {
    if (client.status !== "connected")
      return "Connection interrupted · sending paused";
    if (inputMode === "TEXT") return "Chat connected · microphone off";
    if (client.isMuted)
      return client.mode === "speaking"
        ? "Line is speaking · microphone muted"
        : "Microphone muted";
    if (client.mode === "speaking") return "Line is speaking";
    if (client.mode === "listening") return "Line is listening";
    return "Voice connected";
  }
  return phase === "error" || phase === "review_error"
    ? "Conversation unavailable"
    : "Conversation ended";
}
