import { intakePayload } from "./contracts";
import type {
  ConfirmationInput,
  ConfirmedConversationIntake,
  ConversationDraft,
  ConversationSpeaker,
  ConversationTurn,
  Availability,
  Slot,
  VoiceAppointment,
  VoiceBookingTool,
  BookingProgress,
  BookingFailure,
} from "./contracts";
import { appendTranscript } from "./transcript";
import { isLanguageCode, type LanguageCode } from "./voice-languages";

export type BookingSessionOptions = Readonly<{
  initialLanguage?: LanguageCode;
  sessionId: string;
  isActive: () => boolean;
  onSaved: (intake: ConfirmedConversationIntake) => void;
  onAppointment: (value: VoiceAppointment | undefined) => void;
  onProgress?: (value: BookingProgress) => void;
  request: <T>(path: string, body: unknown) => Promise<T>;
  confirmIntake: (
    input: ConfirmationInput,
  ) => Promise<ConfirmedConversationIntake>;
  randomUUID: () => string;
  classifyFailure: (
    tool: VoiceBookingTool,
    error: unknown,
    requestStarted: boolean,
  ) => BookingFailure;
  requiresStaffReview: (error: unknown) => boolean;
  isValidationFailure: (error: unknown) => boolean;
  isRejectedReservation: (error: unknown) => boolean;
}>;

export class CustomerBookingSession {
  private draft: ConversationDraft = {};
  private turns: ConversationTurn[] = [];
  private prepared?: ConfirmationInput;
  private preparedReadback?: string;
  private confirmationAttempt?: ConfirmationInput;
  private intake?: ConfirmedConversationIntake;
  private availability?: Availability;
  private reservation?: { identity: string; key: string };
  private held?: VoiceAppointment;
  private bookingAttempt?: { transcript: readonly ConversationTurn[]; language: LanguageCode };
  private busy = false;
  private hazardReported = false;
  private draftVersion = 0;
  private pending?: VoiceBookingTool;
  private failure?: BookingFailure;
  private requestStarted = false;
  private readbackLanguage: LanguageCode;
  private appointmentReadbackRequired = false;
  private languageRevision = 0;

  constructor(private readonly options: BookingSessionOptions) {
    this.readbackLanguage = options.initialLanguage ?? "en";
  }

  private publishProgress() {
    this.options.onProgress?.({
      requestSaved: this.intake !== undefined,
      awaitingIntakeConfirmation: this.prepared !== undefined && !this.intake,
      hazardous: this.hazardReported,
      serviceKind: this.prepared?.serviceKind ?? this.draft.serviceKind,
      availability: this.availability,
      pending: this.pending,
      failure: this.failure,
    });
  }

  get savedIntake() {
    return this.intake;
  }

  observeLanguageChange(language: LanguageCode) {
    if (language === this.readbackLanguage) return;
    this.readbackLanguage = language;
    this.languageRevision += 1;
    this.invalidateReadbacks();
  }

  invalidateReadbacks() {
    if (!this.confirmationAttempt) {
      this.prepared = undefined;
      this.preparedReadback = undefined;
    }
    this.appointmentReadbackRequired = this.held?.appointment.status === "HELD";
    this.draftVersion += 1;
    this.publishProgress();
  }

  recordTurn(speaker: ConversationSpeaker, text: string) {
    this.turns = appendTranscript(this.turns, speaker, text);
  }

  async updateDraft(draft: ConversationDraft): Promise<string> {
    this.hazardReported ||= draft.hazardousCondition === true;
    this.publishProgress();
    if (this.intake && this.hazardReported) {
      await this.api("hazard", {});
      if (this.held?.appointment.status !== "CONFIRMED") {
        this.held = undefined;
        this.options.onAppointment(undefined);
      }
      this.publishProgress();
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
    this.preparedReadback = undefined;
    if (!this.failure?.uncertain) this.failure = undefined;
    this.publishProgress();
    return "Draft updated on this device. Nothing has been saved. Prepare a readback before asking for confirmation.";
  }

  async execute(tool: VoiceBookingTool, parameters: Record<string, unknown>) {
    if (!this.options.isActive()) {
      return { ok: false, message: "The conversation is no longer active." };
    }
    if (this.busy) {
      return {
        ok: false,
        message: "Wait for the previous booking tool to finish.",
      };
    }
    const previousFailure = this.failure;
    this.busy = true;
    this.pending = tool;
    if (!this.failure?.uncertain || this.failure.operation === tool)
      this.failure = undefined;
    this.requestStarted = false;
    this.publishProgress();
    try {
      switch (tool) {
        case "prepare_intake_confirmation":
          return await this.prepare(parameters);
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
      if (previousFailure?.uncertain && !this.requestStarted)
        this.failure = previousFailure;
      else if (!this.failure?.uncertain)
        this.failure = this.options.classifyFailure(
          tool,
          failure,
          this.requestStarted,
        );
      if (
        tool === "confirm_service_request" &&
        this.options.isValidationFailure(failure) &&
        this.preparedReadback
      ) {
        return {
          ok: false,
          request_saved: false,
          code: "INTAKE_CONFIRMATION_REQUIRED",
          readback: this.preparedReadback,
          message:
            "The request is unsaved. A complete current readback and explicit confirmation are required.",
          instruction:
            "Present readback exactly, without shortening it or adding another question. Wait for a clear yes or confirm, then retry confirm_service_request. Corrections require submit_intake_draft and prepare_intake_confirmation again. Describe this as a confirmation requirement; do not call it a technical outage or claim a save or booking.",
        };
      }
      return {
        ok: false,
        request_saved: this.intake !== undefined,
        appointment_status: this.held?.appointment.status ?? null,
        message:
          failure instanceof Error
            ? failure.message
            : "Booking could not be completed.",
        instruction: this.options.requiresStaffReview(failure)
          ? "Do not claim success or create a replacement appointment. Keep the original reservation reference and request staff review of its GHL booking history."
          : "Do not claim success. Correct missing details or retry the same tool. Never invent availability or a confirmation.",
      };
    } finally {
      this.busy = false;
      this.pending = undefined;
      this.publishProgress();
    }
  }

  private api<T>(path: string, body: unknown): Promise<T> {
    this.requestStarted = true;
    return this.options.request<T>(path, body);
  }

  private async prepare(parameters: Record<string, unknown> = {}) {
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
    this.selectReadbackLanguage(parameters);
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
      idempotencyKey: this.options.randomUUID(),
      transcript: [],
      spokenConfirmation: true,
      ...(this.readbackLanguage === "en" ? {} : { readbackLanguage: this.readbackLanguage }),
    };
    const payload = intakePayload(input);
    const version = this.draftVersion;
    const languageRevision = this.languageRevision;
    const result = await this.api<{
      readback: string;
      business_date: string | null;
      timezone: string | null;
    }>("intake-readback", {
      customer: payload.customer,
      service: payload.service,
      ...(this.readbackLanguage === "en" ? {} : { readback_language: this.readbackLanguage }),
    });
    if (this.draftVersion !== version || this.languageRevision !== languageRevision)
      throw new Error(
        "The details changed. Prepare and read a new confirmation.",
      );
    this.prepared = input;
    this.preparedReadback = result.readback;
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
    if (!this.confirmationAttempt && parameters.readback_language !== undefined && parameters.readback_language !== (this.prepared.readbackLanguage ?? "en"))
      throw new Error("Language changed. Prepare a fresh readback and wait for a new explicit confirmation.");
    this.confirmationAttempt ??= {
      ...this.prepared,
      transcript: [...this.turns],
    };
    try {
      this.requestStarted = true;
      this.intake = await this.options.confirmIntake(this.confirmationAttempt);
    } catch (failure) {
      // Rejected validation never writes; transport failures retain the exact retry payload.
      if (this.options.isValidationFailure(failure))
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
    this.availability = undefined;
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
    if (this.bookingAttempt)
      throw new Error("Resolve the original appointment confirmation before requesting another readback or reservation.");
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
      this.reservation = { identity, key: this.options.randomUUID() };
    if (!this.reservation)
      throw new Error("Check availability again before reserving.");
    let result: VoiceAppointment;
    const language = this.selectReadbackLanguage(parameters);
    const languageRevision = this.languageRevision;
    try {
      result = await this.api<VoiceAppointment>("reservations", {
        ...(language === "en" ? {} : { readback_language: language }),
        team_key: parameters.team_key,
        starts_at: parameters.starts_at,
        idempotency_key: this.reservation.key,
      });
    } catch (failure) {
      if (this.options.isRejectedReservation(failure))
        this.reservation = undefined;
      throw failure;
    }
    this.held = result;
    this.appointmentReadbackRequired = this.languageRevision !== languageRevision;
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
    if (this.appointmentReadbackRequired && !this.bookingAttempt)
      throw new Error("Language changed. Obtain a new readback for this same held slot and wait for explicit confirmation.");
    if (parameters.explicit_confirmation !== true)
      throw new Error("Wait for a clear yes after the appointment readback.");
    if (!this.bookingAttempt && parameters.readback_language !== undefined && parameters.readback_language !== this.readbackLanguage)
      throw new Error("Language changed. Repeat reserve_appointment for the held slot to obtain a fresh readback, then wait for explicit confirmation.");
    this.bookingAttempt ??= { transcript: [...this.turns], language: this.readbackLanguage };
    try {
      this.held = await this.api<VoiceAppointment>(
        `appointments/${this.held.appointment.id}/confirm`,
        { explicit_confirmation: true, transcript: this.bookingAttempt.transcript,
          ...(this.bookingAttempt.language === "en" ? {} : { readback_language: this.bookingAttempt.language }) },
      );
    } catch (failure) {
      // An unknown result retains the original transcript and language for retry.
      if (!this.options.classifyFailure("confirm_appointment", failure, true).uncertain)
        this.bookingAttempt = undefined;
      throw failure;
    }
    if (this.held.appointment.status !== "CONFIRMED")
      throw new Error(
        "The appointment was not confirmed. Do not claim it is booked.",
      );
    this.bookingAttempt = undefined;
    this.appointmentReadbackRequired = false;
    this.options.onAppointment(this.held);
    return {
      ok: true,
      ...this.held,
      booked: true,
      message:
        "The appointment is confirmed and saved. Tell the customer the confirmed date, time and timezone.",
    };
  }

  private selectReadbackLanguage(parameters: Record<string, unknown>): LanguageCode {
    const language = parameters.readback_language;
    if (language !== undefined) {
      if (!isLanguageCode(language)) throw new Error("Unsupported readback language. Ask the customer to choose a supported language.");
      this.readbackLanguage = language;
    }
    return this.readbackLanguage;
  }

  private async release() {
    this.requireBookable();
    if (this.bookingAttempt)
      throw new Error("Resolve the original appointment confirmation or ask staff before releasing this hold.");
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
