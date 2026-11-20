import type {
  Appointment,
  Availability,
  ConversationSessionAuthorization,
  ConfirmedConversationIntake,
  VoiceAppointment,
} from "@insurance-operations/customer-core";

export const TOKEN = /^[A-Za-z0-9_-]{32,128}$/;
export const UUID =
  /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
export type Account = Readonly<{
  id: string;
  full_name: string;
  email: string;
}>;
export type StoredSession = Readonly<{
  token: string;
  expiresAt: number;
  origin: string;
}>;
export type Challenge = Readonly<{
  token: string;
  nextAction: "enroll" | "verify";
  expiresAt: number;
}>;
export type BookingDetails = Readonly<{
  appointment: Appointment;
  customer: {
    full_name: string;
    phone: string | null;
    address: {
      line1: string;
      city: string;
      state_code: string;
      postal_code: string;
    } | null;
  };
  service: { kind: string; equipment_issue: string };
  timezone: string;
  can_reschedule: boolean;
  change_message: string | null;
}>;

export function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function object(value: unknown): Record<string, unknown> {
  if (!record(value))
    throw new Error(
      "The service returned an invalid response. Please try again.",
    );
  return value;
}

export function string(value: unknown): string {
  if (typeof value !== "string" || !value.trim())
    throw new Error("The service returned incomplete data.");
  return value;
}

export function date(value: unknown): string {
  const result = string(value);
  if (!Number.isFinite(Date.parse(result)))
    throw new Error("The service returned an invalid date.");
  return result;
}

function id(value: unknown) {
  const result = string(value);
  if (!UUID.test(result))
    throw new Error("The service returned an invalid reference.");
  return result;
}

export function account(value: unknown): Account {
  const data = object(value);
  return {
    id: id(data.id),
    full_name: string(data.full_name),
    email: string(data.email),
  };
}

export function challenge(value: unknown): Challenge {
  const data = object(value);
  if (
    data.mfa_required !== true ||
    !TOKEN.test(string(data.challenge_token)) ||
    !["enroll", "verify"].includes(String(data.next_action)) ||
    !Number.isInteger(data.expires_in) ||
    Number(data.expires_in) < 1 ||
    Number(data.expires_in) > 600 ||
    "session_token" in data
  )
    throw new Error("Sign-in could not be started. Try again.");
  return {
    token: string(data.challenge_token),
    nextAction: data.next_action as Challenge["nextAction"],
    expiresAt: Date.now() + Number(data.expires_in) * 1000,
  };
}

export function login(value: unknown, origin: string) {
  const data = object(value);
  if (
    data.mfa_verified !== true ||
    !TOKEN.test(string(data.session_token)) ||
    !Number.isInteger(data.expires_in) ||
    Number(data.expires_in) < 1 ||
    Number(data.expires_in) > 28800
  )
    throw new Error("Sign-in could not be completed. Try again.");
  const codes = data.recovery_codes;
  if (
    codes != null &&
    (!Array.isArray(codes) ||
      codes.length !== 10 ||
      !codes.every(
        (code: unknown) =>
          typeof code === "string" &&
          /^[a-f0-9]{8}(-[a-f0-9]{8}){3}$/.test(code),
      ))
  )
    throw new Error("Your recovery codes could not be read. Sign in again.");
  return {
    user: account(data.user),
    session: {
      token: string(data.session_token),
      expiresAt: Date.now() + Number(data.expires_in) * 1000,
      origin,
    },
    recoveryCodes: (codes ?? []) as string[],
  };
}

export function storedSession(
  value: unknown,
  origin: string,
): StoredSession | undefined {
  if (
    !record(value) ||
    typeof value.token !== "string" ||
    !TOKEN.test(value.token) ||
    value.origin !== origin ||
    typeof value.expiresAt !== "number" ||
    !Number.isFinite(value.expiresAt) ||
    value.expiresAt <= Date.now() ||
    value.expiresAt > Date.now() + 28800_000
  )
    return undefined;
  return { token: value.token, expiresAt: value.expiresAt, origin };
}

export function appointment(value: unknown): Appointment {
  const data = object(value);
  const starts = date(data.starts_at),
    ends = date(data.ends_at);
  if (
    Date.parse(ends) <= Date.parse(starts) ||
    !["HELD", "CONFIRMED", "CANCELLED", "EXPIRED"].includes(String(data.status))
  )
    throw new Error("The appointment returned invalid details.");
  return {
    id: id(data.id),
    service_request_id: id(data.service_request_id),
    team_key: string(data.team_key),
    status: string(data.status),
    starts_at: starts,
    ends_at: ends,
    hold_expires_at: date(data.hold_expires_at),
  };
}

export function timezone(value: unknown): string {
  const zone = value == null ? "UTC" : string(value);
  new Intl.DateTimeFormat("en-US", { timeZone: zone });
  return zone;
}

export function appointments(value: unknown) {
  const data = object(value);
  if (!Array.isArray(data.appointments))
    throw new Error("Appointments could not be loaded.");
  return {
    appointments: data.appointments.map(appointment),
    timezone: timezone(data.timezone),
  };
}

export function availability(value: unknown): Availability {
  const data = object(value);
  if (
    typeof data.configured !== "boolean" ||
    typeof data.in_service_area !== "boolean" ||
    !Array.isArray(data.slots)
  )
    throw new Error("Available times could not be loaded.");
  return {
    configured: data.configured,
    in_service_area: data.in_service_area,
    timezone: timezone(data.timezone),
    message: typeof data.message === "string" ? data.message : null,
    slots: data.slots.map((item: unknown) => {
      const slot = object(item);
      const starts = date(slot.starts_at),
        ends = date(slot.ends_at);
      if (Date.parse(ends) <= Date.parse(starts))
        throw new Error("Invalid appointment time.");
      return {
        team_key: string(slot.team_key),
        starts_at: starts,
        ends_at: ends,
      };
    }),
  };
}

export function bookingDetails(value: unknown): BookingDetails {
  const data = object(value),
    customer = object(data.customer),
    service = object(data.service);
  if (typeof data.can_reschedule !== "boolean")
    throw new Error("Appointment details could not be loaded.");
  const address = customer.address == null ? null : object(customer.address);
  return {
    appointment: appointment(data.appointment),
    timezone: timezone(data.timezone),
    can_reschedule: data.can_reschedule,
    change_message:
      typeof data.change_message === "string" ? data.change_message : null,
    customer: {
      full_name: string(customer.full_name),
      phone: typeof customer.phone === "string" ? customer.phone : null,
      address: address
        ? {
            line1: string(address.line1),
            city: string(address.city),
            state_code: string(address.state_code),
            postal_code: string(address.postal_code),
          }
        : null,
    },
    service: {
      kind: string(service.kind),
      equipment_issue: string(service.equipment_issue),
    },
  };
}

export function voiceAppointment(value: unknown): VoiceAppointment {
  const data = object(value);
  return {
    appointment: appointment(data.appointment),
    readback: string(data.readback),
    timezone: timezone(data.timezone),
  };
}

export function confirmedIntake(value: unknown): ConfirmedConversationIntake {
  const data = object(value),
    customer = object(data.customer);
  return {
    conversationIntakeId: id(data.conversation_intake_id),
    customerId: id(customer.id),
    customerName: string(customer.full_name),
    confirmedAt: date(data.confirmed_at),
    serviceRequestId:
      data.service_request_id == null ? undefined : id(data.service_request_id),
    leadId: data.lead_id == null ? undefined : id(data.lead_id),
  };
}

export function authorization(
  value: unknown,
  mode: "VOICE" | "TEXT",
): ConversationSessionAuthorization {
  const data = object(value),
    connection = object(data.connection);
  if (
    connection.provider !== "elevenlabs" ||
    data.input_mode !== mode ||
    connection.transport !== (mode === "VOICE" ? "webrtc" : "websocket") ||
    !Number.isInteger(data.maximum_duration_seconds) ||
    Number(data.maximum_duration_seconds) < 1 ||
    Number(data.maximum_duration_seconds) > 180
  )
    throw new Error(
      "This conversation connection is not supported in the mobile app.",
    );
  const credential = string(connection.credential);
  if (mode === "TEXT") {
    const url = new URL(credential);
    if (
      url.protocol !== "wss:" ||
      url.hostname !== "api.elevenlabs.io" ||
      url.pathname !== "/v1/convai/conversation" ||
      !url.search ||
      url.username ||
      url.password ||
      url.port ||
      url.hash
    )
      throw new Error("The chat connection is invalid.");
  }
  const expires = date(data.authorization_expires_at);
  if (Date.parse(expires) <= Date.now())
    throw new Error("The conversation connection has expired.");
  return {
    sessionId: id(data.session_id),
    provider: "elevenlabs",
    inputMode: mode,
    transport: mode === "VOICE" ? "webrtc" : "websocket",
    credential,
    maximumDurationSeconds: Number(data.maximum_duration_seconds),
    authorizationExpiresAt: expires,
    confirmationExpiresAt: date(data.confirmation_expires_at),
  };
}

export function formatTime(value: string, zone: string) {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: zone,
  }).format(new Date(value));
}
