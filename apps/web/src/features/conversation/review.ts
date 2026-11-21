import type { ConversationTurn } from "./contracts";

export type IntakeReviewValues = Readonly<{
  fullName: string;
  email: string;
  phone: string;
  intakeIntent: string;
}>;

export { appendTranscript } from "@insurance-operations/customer-core";

export function validateConfirmation(
  form: IntakeReviewValues,
  transcript: readonly ConversationTurn[],
): string | undefined {
  if (!form.fullName.trim()) {
    return "Full name is required.";
  }
  if (!form.email.trim() && !form.phone.trim()) {
    return "Email or phone is required.";
  }
  if (!form.intakeIntent.trim()) {
    return "HVAC service request is required.";
  }
  const speakers = new Set(transcript.map((turn) => turn.speaker));
  if (!speakers.has("USER") || !speakers.has("AGENT")) {
    return "The confirmed transcript needs customer and AI assistant turns.";
  }
  if (transcript.some((turn) => !turn.text.trim())) {
    return "Transcript turns cannot be empty.";
  }
  return undefined;
}
