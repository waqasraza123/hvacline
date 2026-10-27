import { OperationsApiError, requestApi } from "../operations/api";
import type { Appointment, Availability, Slot } from "../operations/api";

export type BookingDetails = {
  appointment: Appointment;
  timezone: string;
  can_reschedule: boolean;
  change_message: string | null;
  change_allowance: { maximum: number; used: number; remaining: number };
  customer: {
    full_name: string;
    phone: string | null;
    email: string | null;
    address: {
      line1: string | null;
      line2?: string | null;
      city: string | null;
      state_code: string | null;
      postal_code: string | null;
      country_code: string;
    } | null;
  };
  service: {
    kind: string;
    equipment_issue: string;
    preferred_window: string;
    hazardous_condition: boolean;
  };
};

export const SERVICE_NAMES: Record<string, string> = {
  AC_REPAIR: "AC repair",
  HEATING_REPAIR: "Heating repair",
  INSTALLATION: "Installation",
  MAINTENANCE: "Maintenance",
};

export function bookingTime(value: string, timezone: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "full",
    timeStyle: "short",
    timeZone: timezone,
  }).format(new Date(value));
}

export function bookingDay(value: string, timezone: string): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: timezone,
  }).formatToParts(new Date(value));
  const part = (type: string) =>
    parts.find((value) => value.type === type)?.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}

export async function getBookingDetails(id: string): Promise<BookingDetails> {
  const result = await requestApi<BookingDetails>(
    "",
    "",
    `appointments/${encodeURIComponent(id)}`,
  );
  if (
    !result.change_allowance ||
    ![
      result.change_allowance.maximum,
      result.change_allowance.used,
      result.change_allowance.remaining,
    ].every((value) => Number.isInteger(value) && value >= 0)
  )
    throw new Error(
      "Booking limits are unavailable. Please refresh and try again.",
    );
  return result;
}

export const getBookingAvailability = (id: string, day: string) =>
  requestApi<Availability>(
    "",
    "",
    `appointments/${encodeURIComponent(id)}/availability`,
    "POST",
    { day },
  );

type PendingChange = {
  service_request_id: string;
  team_key: string;
  starts_at: string;
  idempotency_key: string;
  explicit_confirmation: true;
};

export class BookingChange {
  pending: PendingChange | undefined;

  constructor(readonly appointmentId: string) {}

  async submit(
    requestId: string,
    slot: Pick<Slot, "team_key" | "starts_at">,
  ): Promise<Appointment> {
    if (
      this.pending &&
      (this.pending.service_request_id !== requestId ||
        this.pending.team_key !== slot.team_key ||
        this.pending.starts_at !== slot.starts_at)
    )
      throw new Error(
        "Check the previous change before choosing another time.",
      );
    this.pending ??= {
      service_request_id: requestId,
      team_key: slot.team_key,
      starts_at: slot.starts_at,
      idempotency_key: crypto.randomUUID(),
      explicit_confirmation: true,
    };
    try {
      const appointment = await requestApi<Appointment>(
        "",
        "",
        `appointments/${encodeURIComponent(this.appointmentId)}/reschedule`,
        "POST",
        this.pending,
      );
      if (
        appointment.status !== "CONFIRMED" ||
        appointment.service_request_id !== requestId ||
        appointment.team_key !== this.pending.team_key ||
        Date.parse(appointment.starts_at) !== Date.parse(this.pending.starts_at)
      ) {
        throw new Error(
          "The appointment change has not been confirmed. Retry to check its result.",
        );
      }
      this.pending = undefined;
      return appointment;
    } catch (error) {
      if (
        error instanceof OperationsApiError &&
        ([400, 404, 410, 422].includes(error.status) ||
          [
            "SLOT_UNAVAILABLE",
            "RESERVATION_EXPIRED",
            "CHANGE_NOTICE_REQUIRED",
            "HUMAN_ATTENTION_REQUIRED",
            "CALENDAR_CONFLICT",
            "CUSTOMER_BOOKING_CHANGE_LIMIT_REACHED",
            "CUSTOMER_APPOINTMENT_LIMIT_REACHED",
          ].includes(error.code ?? ""))
      )
        this.pending = undefined;
      throw error;
    }
  }
}
