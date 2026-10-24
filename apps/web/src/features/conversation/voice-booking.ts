import {
  ConversationApiError,
  confirmConversationIntake,
  intakePayload,
} from "./api";
import type { ConfirmationInput } from "./api";
import type {
  ConfirmedConversationIntake,
  ConversationDraft,
  ConversationSpeaker,
  ConversationTurn,
} from "./contracts";
import { appendTranscript } from "./review";
import { OperationsApiError, requestApi } from "../operations/api";
import type { Appointment, Availability, Slot } from "../operations/api";

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

type SessionOptions = Readonly<{
  apiBaseUrl: string;
  adminToken?: string;
  sessionId: string;
  isActive: () => boolean;
  onSaved: (intake: ConfirmedConversationIntake) => void;
  onAppointment: (value: VoiceAppointment | undefined) => void;
}>;

export class VoiceBookingSession {
  private draft: ConversationDraft = {};
  private turns: ConversationTurn[] = [];
  private prepared?: ConfirmationInput;
  private confirmationAttempt?: ConfirmationInput;
  private intake?: ConfirmedConversationIntake;
  private availability?: Availability;
  private reservation?: { identity: string; key: string };
  private held?: VoiceAppointment;
  private bookingAttempt?: readonly ConversationTurn[];
  private busy = false;
  private hazardReported = false;
  private draftVersion = 0;

  constructor(private readonly options: SessionOptions) {}

  get savedIntake() {
    return this.intake;
  }

  recordTurn(speaker: ConversationSpeaker, text: string) {
    this.turns = appendTranscript(this.turns, speaker, text);
  }

  async updateDraft(draft: ConversationDraft): Promise<string> {
    this.hazardReported ||= draft.hazardousCondition === true;
    if (this.intake && this.hazardReported) {
      await this.api("hazard", {});
      if (this.held?.appointment.status !== "CONFIRMED") {
        this.held = undefined;
        this.options.onAppointment(undefined);
      }
      return "Hazard flagged for human attention. No new appointment can be booked. Leave immediate danger and contact emergency services. Do not promise a transfer or an alert delivery.";
    }
    if (this.intake || this.confirmationAttempt) {
      return "The confirmed details are locked. Do not change them or create another request.";
    }
    this.draft = {
      ...this.draft,
      ...Object.fromEntries(
        Object.entries(draft).filter(([, value]) => value !== undefined),
      ),
      hazardousCondition: this.hazardReported
        ? true
        : (draft.hazardousCondition ?? this.draft.hazardousCondition),
    };
    this.draftVersion += 1;
    this.prepared = undefined;
    return "Draft updated in this browser. Nothing has been saved. Prepare a readback before asking for confirmation.";
  }

  async execute(tool: VoiceBookingTool, parameters: Record<string, unknown>) {
    if (!this.options.isActive()) {
      return { ok: false, message: "The voice session is no longer active." };
    }
    if (this.busy) {
      return {
        ok: false,
        message: "Wait for the previous booking tool to finish.",
      };
    }
    this.busy = true;
    try {
      switch (tool) {
        case "prepare_intake_confirmation":
          return await this.prepare();
        case "confirm_service_request":
          return await this.save(parameters);
        case "check_appointment_availability":
          return await this.checkAvailability(parameters);
        case "reserve_appointment":
          return await this.reserve(parameters);
        case "confirm_appointment":
          return await this.confirm(parameters);
        case "release_appointment_hold":
          return await this.release();
      }
    } catch (failure) {
      return {
        ok: false,
        request_saved: this.intake !== undefined,
        appointment_status: this.held?.appointment.status ?? null,
        message:
          failure instanceof Error
            ? failure.message
            : "Booking could not be completed.",
        instruction:
          "Do not claim success. Correct missing details or retry the same tool. Never invent availability or a confirmation.",
      };
    } finally {
      this.busy = false;
    }
  }

  private api<T>(path: string, body: unknown): Promise<T> {
    return requestApi<T>(
      this.options.apiBaseUrl,
      this.options.adminToken ?? "",
      `conversation-sessions/${this.options.sessionId}/booking/${path}`,
      "POST",
      body,
    );
  }

  private async prepare() {
    if (this.intake)
      return {
        ok: true,
        persisted: true,
        message: "The service request is already saved.",
      };
    if (this.confirmationAttempt)
      throw new Error(
        "Retry confirm_service_request to resolve the previous save before changing details.",
      );
    const required = (key: keyof ConversationDraft): string => {
      const value = this.draft[key];
      if (typeof value !== "string" || !value.trim())
        throw new Error(`Collect ${key} and call submit_intake_draft first.`);
      return value.trim();
    };
    if (typeof this.draft.hazardousCondition !== "boolean")
      throw new Error(
        "Ask about gas odor, smoke, carbon monoxide alarms or electrical danger and set hazardous_condition.",
      );
    const input: ConfirmationInput = {
      sessionId: this.options.sessionId,
      fullName: required("fullName"),
      email: this.draft.email?.trim() ?? "",
      phone: required("phone"),
      intakeIntent: required("intakeIntent"),
      addressLine1: required("addressLine1"),
      city: required("city"),
      stateCode: required("stateCode").toUpperCase(),
      postalCode: required("postalCode"),
      serviceKind: required("serviceKind"),
      preferredWindow: required("preferredWindow"),
      hazardousCondition: this.draft.hazardousCondition,
      idempotencyKey: crypto.randomUUID(),
      transcript: [],
      spokenConfirmation: true,
    };
    const payload = intakePayload(input);
    const version = this.draftVersion;
    const result = await this.api<{
      readback: string;
      business_date: string | null;
      timezone: string | null;
    }>("intake-readback", {
      customer: payload.customer,
      service: payload.service,
    });
    if (this.draftVersion !== version)
      throw new Error(
        "The details changed. Prepare and read a new confirmation.",
      );
    this.prepared = input;
    return {
      ok: true,
      persisted: false,
      ...result,
      instruction:
        "Read readback exactly, then wait for the customer's answer. If corrected, update the draft and prepare a new readback.",
    };
  }

  private async save(parameters: Record<string, unknown>) {
    if (this.intake)
      return {
        ok: true,
        persisted: true,
        service_request_id: this.intake.serviceRequestId,
      };
    if (parameters.explicit_confirmation !== true)
      throw new Error(
        "Wait for the customer to confirm the readback before saving.",
      );
    if (!this.prepared)
      throw new Error(
        "Call prepare_intake_confirmation and read the result first.",
      );
    this.confirmationAttempt ??= {
      ...this.prepared,
      transcript: [...this.turns],
    };
    try {
      this.intake = await confirmConversationIntake(
        this.options.apiBaseUrl,
        this.confirmationAttempt,
        this.options.adminToken,
      );
    } catch (failure) {
      // Rejected validation never writes; transport failures retain the exact retry payload.
      if (failure instanceof ConversationApiError && failure.status === 422)
        this.confirmationAttempt = undefined;
      throw failure;
    }
    this.options.onSaved(this.intake);
    if (this.hazardReported && !this.prepared.hazardousCondition)
      await this.api("hazard", {});
    return {
      ok: true,
      persisted: true,
      service_request_id: this.intake.serviceRequestId,
      human_attention_required:
        this.hazardReported || this.prepared.hazardousCondition,
      message:
        "The service request and confirmed transcript are saved. No appointment has been booked.",
    };
  }

  private requireBookable() {
    if (!this.intake?.serviceRequestId)
      throw new Error("Confirm and save the service request first.");
    if (this.hazardReported || this.prepared?.hazardousCondition)
      throw new Error(
        "This hazardous request needs human attention. Do not offer an appointment. Leave immediate danger and contact emergency services.",
      );
  }

  private async checkAvailability(parameters: Record<string, unknown>) {
    this.requireBookable();
    const day = parameters.day;
    if (typeof day !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(day))
      throw new Error(
        "Ask for an exact calendar date and send day as YYYY-MM-DD.",
      );
    this.availability = await this.api<Availability>("availability", { day });
    return {
      ok: true,
      ...this.availability,
      instruction:
        "Offer only these returned slots, in the returned business timezone. Never invent a time. Ask the customer to choose one.",
    };
  }

  private async reserve(parameters: Record<string, unknown>) {
    this.requireBookable();
    const slot: Slot | undefined = this.availability?.slots.find(
      (item) =>
        item.team_key === parameters.team_key &&
        item.starts_at === parameters.starts_at,
    );
    const identity = `${parameters.team_key}:${parameters.starts_at}`;
    if (this.held?.appointment.status === "CONFIRMED")
      return { ok: true, ...this.held, booked: true };
    if (
      this.held &&
      this.held.appointment.status === "HELD" &&
      this.reservation?.identity !== identity
    )
      throw new Error(
        "Release the existing hold before choosing another time.",
      );
    if (!slot && this.reservation?.identity !== identity)
      throw new Error(
        "Choose a slot returned by check_appointment_availability first.",
      );
    if (
      !this.held &&
      this.reservation &&
      this.reservation.identity !== identity
    ) {
      throw new Error(
        "The previous reservation response is unresolved. Retry reserve_appointment with the previous slot before choosing another time.",
      );
    }
    if (this.reservation?.identity !== identity)
      this.reservation = { identity, key: crypto.randomUUID() };
    if (!this.reservation)
      throw new Error("Check availability again before reserving.");
    let result: VoiceAppointment;
    try {
      result = await this.api<VoiceAppointment>("reservations", {
        team_key: parameters.team_key,
        starts_at: parameters.starts_at,
        idempotency_key: this.reservation.key,
      });
    } catch (failure) {
      if (
        failure instanceof OperationsApiError &&
        [400, 404, 409, 410, 422].includes(failure.status)
      )
        this.reservation = undefined;
      throw failure;
    }
    this.held = result;
    this.options.onAppointment(result);
    return {
      ok: true,
      ...result,
      booked: result.appointment.status === "CONFIRMED",
      instruction:
        "A HELD appointment is not booked. Read readback exactly and wait for a clear yes before confirm_appointment.",
    };
  }

  private async confirm(parameters: Record<string, unknown>) {
    this.requireBookable();
    if (!this.held) throw new Error("Reserve an offered slot first.");
    if (this.held.appointment.status === "CONFIRMED")
      return { ok: true, ...this.held, booked: true };
    if (parameters.explicit_confirmation !== true)
      throw new Error("Wait for a clear yes after the appointment readback.");
    this.bookingAttempt ??= [...this.turns];
    try {
      this.held = await this.api<VoiceAppointment>(
        `appointments/${this.held.appointment.id}/confirm`,
        { explicit_confirmation: true, transcript: this.bookingAttempt },
      );
    } catch (failure) {
      // A failed readback can be corrected without changing the held appointment.
      this.bookingAttempt = undefined;
      throw failure;
    }
    if (this.held.appointment.status !== "CONFIRMED")
      throw new Error(
        "The appointment was not confirmed. Do not claim it is booked.",
      );
    this.options.onAppointment(this.held);
    return {
      ok: true,
      ...this.held,
      booked: true,
      message:
        "The appointment is confirmed and saved. Tell the customer the confirmed date, time and timezone.",
    };
  }

  private async release() {
    this.requireBookable();
    if (!this.held) return { ok: true, message: "No hold to release." };
    if (this.held.appointment.status === "CONFIRMED")
      throw new Error(
        "A confirmed appointment requires the existing appointment-change workflow.",
      );
    await this.api(`appointments/${this.held.appointment.id}/release`, {});
    this.held = undefined;
    this.reservation = undefined;
    this.bookingAttempt = undefined;
    this.availability = undefined;
    this.options.onAppointment(undefined);
    return {
      ok: true,
      booked: false,
      message: "The hold was released. Check availability again.",
    };
  }
}
