import type { Appointment } from "../operations/api";

export type MyAppointments = { appointments: Appointment[]; timezone: string };
export type AppointmentFilter = "upcoming" | "history" | "all";
export type AppointmentState =
  | "upcoming"
  | "in_progress"
  | "held"
  | "expired"
  | "past"
  | "cancelled"
  | "attention";

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseAppointments(value: unknown): MyAppointments {
  const message =
    "Your appointments could not be loaded. Please refresh and try again.";
  if (
    !record(value) ||
    !Array.isArray(value.appointments) ||
    !(value.timezone === null || typeof value.timezone === "string")
  )
    throw new Error(message);
  const timezone = value.timezone ?? "UTC";
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: timezone });
  } catch {
    throw new Error(message);
  }
  const appointments = value.appointments.map((item: unknown): Appointment => {
    if (
      !record(item) ||
      typeof item.id !== "string" ||
      !item.id ||
      typeof item.service_request_id !== "string" ||
      typeof item.team_key !== "string" ||
      typeof item.status !== "string" ||
      typeof item.starts_at !== "string" ||
      typeof item.ends_at !== "string" ||
      typeof item.hold_expires_at !== "string" ||
      ![item.starts_at, item.ends_at, item.hold_expires_at].every((date) =>
        Number.isFinite(Date.parse(date)),
      ) ||
      Date.parse(item.ends_at) <= Date.parse(item.starts_at)
    )
      throw new Error(message);
    return {
      id: item.id,
      service_request_id: item.service_request_id,
      team_key: item.team_key,
      status: item.status,
      starts_at: item.starts_at,
      ends_at: item.ends_at,
      hold_expires_at: item.hold_expires_at,
    };
  });
  return { appointments, timezone };
}

export function appointmentState(
  appointment: Appointment,
  now: number,
): AppointmentState {
  if (appointment.status === "CONFIRMED") {
    if (Date.parse(appointment.ends_at) <= now) return "past";
    return Date.parse(appointment.starts_at) <= now
      ? "in_progress"
      : "upcoming";
  }
  if (appointment.status === "HELD") {
    return Date.parse(appointment.hold_expires_at) <= now ||
      Date.parse(appointment.ends_at) <= now
      ? "expired"
      : "held";
  }
  if (appointment.status === "CANCELLED") return "cancelled";
  if (appointment.status === "EXPIRED") return "expired";
  return "attention";
}

export function isUpcoming(appointment: Appointment, now: number): boolean {
  return ["upcoming", "in_progress", "held"].includes(
    appointmentState(appointment, now),
  );
}

export function isHistory(appointment: Appointment, now: number): boolean {
  return ["past", "cancelled", "expired"].includes(
    appointmentState(appointment, now),
  );
}

export function filterAppointments(
  appointments: Appointment[],
  filter: AppointmentFilter,
  now: number,
): Appointment[] {
  return appointments
    .filter(
      (appointment) =>
        filter === "all" ||
        (filter === "upcoming"
          ? isUpcoming(appointment, now)
          : isHistory(appointment, now)),
    )
    .sort((left, right) => {
      const leftUpcoming = isUpcoming(left, now);
      const rightUpcoming = isUpcoming(right, now);
      if (leftUpcoming !== rightUpcoming) return leftUpcoming ? -1 : 1;
      return leftUpcoming
        ? Date.parse(left.starts_at) - Date.parse(right.starts_at)
        : Date.parse(right.starts_at) - Date.parse(left.starts_at);
    });
}

export function appointmentLabel(
  appointment: Appointment,
  now: number,
): string {
  const state = appointmentState(appointment, now);
  if (state === "expired" && appointment.status === "HELD")
    return "Hold expired";
  return {
    upcoming: "Confirmed",
    in_progress: "Scheduled now",
    held: "Awaiting confirmation",
    expired: "Expired",
    past: "Past appointment",
    cancelled: "Cancelled",
    attention: "Needs attention",
  }[state];
}

export function appointmentDate(value: string, timezone: string) {
  const date = new Date(value);
  const format = (options: Intl.DateTimeFormatOptions) =>
    new Intl.DateTimeFormat("en-US", { ...options, timeZone: timezone }).format(
      date,
    );
  return {
    month: format({ month: "short" }),
    day: format({ day: "2-digit" }),
    weekday: format({ weekday: "long" }),
    full: format({ dateStyle: "full" }),
  };
}

export function appointmentTimeRange(
  appointment: Appointment,
  timezone: string,
): string {
  const day = (value: string) =>
    new Intl.DateTimeFormat("en-US", {
      dateStyle: "short",
      timeZone: timezone,
    }).format(new Date(value));
  const start = new Intl.DateTimeFormat("en-US", {
    timeStyle: "short",
    timeZone: timezone,
  }).format(new Date(appointment.starts_at));
  const end = new Intl.DateTimeFormat("en-US", {
    ...(day(appointment.starts_at) === day(appointment.ends_at)
      ? {}
      : { dateStyle: "medium" as const }),
    timeStyle: "short",
    timeZone: timezone,
  }).format(new Date(appointment.ends_at));
  return `${start} – ${end}`;
}
