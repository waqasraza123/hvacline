import { describe, expect, it } from "vitest";
import {
  appointmentDate,
  appointmentLabel,
  appointmentState,
  appointmentTimeRange,
  filterAppointments,
  parseAppointments,
} from "./appointments-model";
import type { Appointment } from "../operations/api";

const now = Date.parse("2026-10-28T12:00:00Z");
const booking: Appointment = {
  id: "fictional-booking",
  service_request_id: "fictional-request",
  team_key: "test-team",
  starts_at: "2026-10-28T13:00:00Z",
  ends_at: "2026-10-28T14:00:00Z",
  hold_expires_at: "2026-10-28T12:05:00Z",
  status: "CONFIRMED",
};

describe("customer appointment presentation", () => {
  it("keeps temporary holds separate from confirmed bookings at expiry", () => {
    const held = { ...booking, status: "HELD" };
    expect(appointmentState(held, now)).toBe("held");
    expect(appointmentLabel(held, now)).toBe("Awaiting confirmation");
    const expiry = Date.parse(held.hold_expires_at);
    expect(appointmentState(held, expiry)).toBe("expired");
    expect(appointmentLabel(held, expiry)).toBe("Hold expired");
    expect(filterAppointments([held], "upcoming", expiry)).toEqual([]);
    expect(filterAppointments([held], "history", expiry)).toEqual([held]);
  });

  it("does not imply service completion for a past confirmed appointment", () => {
    expect(appointmentState(booking, Date.parse(booking.starts_at))).toBe(
      "in_progress",
    );
    expect(appointmentLabel(booking, Date.parse(booking.starts_at))).toBe(
      "Scheduled now",
    );
    expect(appointmentLabel(booking, Date.parse(booking.ends_at))).toBe(
      "Past appointment",
    );
    expect(appointmentState({ ...booking, status: "CANCELLED" }, now)).toBe(
      "cancelled",
    );
    expect(appointmentState({ ...booking, status: "UNRECOGNIZED" }, now)).toBe(
      "attention",
    );
  });

  it("sorts upcoming bookings first without treating cancellations as upcoming", () => {
    const later = {
      ...booking,
      id: "later",
      starts_at: "2026-10-28T15:00:00Z",
      ends_at: "2026-10-28T16:00:00Z",
    };
    const cancelled = { ...booking, id: "cancelled", status: "CANCELLED" };
    const input = [cancelled, later, booking];
    expect(
      filterAppointments(input, "upcoming", now).map((item) => item.id),
    ).toEqual([booking.id, "later"]);
    expect(filterAppointments(input, "history", now)).toEqual([cancelled]);
    expect(
      filterAppointments(input, "all", now).map((item) => item.id),
    ).toEqual([booking.id, "later", "cancelled"]);
    expect(input[0]).toBe(cancelled);
  });

  it("uses the business timezone and includes the end date for an overnight visit", () => {
    const overnight = {
      ...booking,
      starts_at: "2026-11-01T03:30:00Z",
      ends_at: "2026-11-01T05:30:00Z",
    };
    expect(appointmentDate(overnight.starts_at, "America/New_York").day).toBe(
      "31",
    );
    expect(appointmentDate(overnight.starts_at, "America/New_York").month).toBe(
      "Oct",
    );
    expect(appointmentTimeRange(overnight, "America/New_York")).toContain(
      "Nov 1",
    );
  });

  it("validates list responses before formatting dates and preserves the UTC fallback", () => {
    expect(
      parseAppointments({ appointments: [booking], timezone: null }).timezone,
    ).toBe("UTC");
    expect(
      parseAppointments({
        appointments: [booking],
        timezone: "America/New_York",
      }).appointments,
    ).toEqual([booking]);
    for (const value of [
      null,
      { appointments: null, timezone: "UTC" },
      { appointments: [booking], timezone: "invalid/timezone" },
      {
        appointments: [{ ...booking, starts_at: "not a date" }],
        timezone: "UTC",
      },
      {
        appointments: [{ ...booking, ends_at: booking.starts_at }],
        timezone: "UTC",
      },
    ]) {
      expect(() => parseAppointments(value)).toThrow(
        "Your appointments could not be loaded.",
      );
    }
  });
});
