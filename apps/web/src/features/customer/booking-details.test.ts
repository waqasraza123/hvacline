import { afterEach, expect, it, vi } from "vitest";
import { BookingChange, bookingDay } from "./booking-details";

afterEach(() => vi.unstubAllGlobals());

const slot = {
  team_key: "team-a",
  starts_at: "2026-11-03T15:00:00Z",
  ends_at: "2026-11-03T16:00:00Z",
};
const confirmed = {
  ...slot,
  id: "new-booking",
  service_request_id: "request-1",
  status: "CONFIRMED",
  hold_expires_at: "2026-11-02T12:05:00Z",
};

it("keeps the same rescheduling payload and key after an unknown response", async () => {
  const fetcher = vi
    .fn()
    .mockRejectedValueOnce(new TypeError("Connection lost"))
    .mockResolvedValueOnce(Response.json(confirmed));
  vi.stubGlobal("fetch", fetcher);
  const change = new BookingChange("old-booking");
  await expect(change.submit("request-1", slot)).rejects.toThrow(
    "Connection lost",
  );
  expect(change.pending).toBeDefined();
  await expect(
    change.submit("request-1", { ...slot, starts_at: "2026-11-03T16:00:00Z" }),
  ).rejects.toThrow("previous change");
  expect(fetcher).toHaveBeenCalledTimes(1);
  await expect(change.submit("request-1", slot)).resolves.toEqual(confirmed);
  expect(fetcher.mock.calls[0][1].body).toBe(fetcher.mock.calls[1][1].body);
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toMatchObject({
    explicit_confirmation: true,
    service_request_id: "request-1",
    starts_at: slot.starts_at,
  });
  expect(change.pending).toBeUndefined();
});

it("retains calendar outage recovery but clears a definitively rejected slot", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      Response.json(
        {
          error: {
            code: "CALENDAR_UNAVAILABLE",
            message: "Retry calendar check",
          },
        },
        { status: 409 },
      ),
    )
    .mockResolvedValueOnce(
      Response.json(
        { error: { code: "SLOT_UNAVAILABLE", message: "Choose another time" } },
        { status: 409 },
      ),
    );
  vi.stubGlobal("fetch", fetcher);
  const change = new BookingChange("old-booking");
  await expect(change.submit("request-1", slot)).rejects.toThrow();
  expect(change.pending).toBeDefined();
  await expect(change.submit("request-1", slot)).rejects.toThrow();
  expect(change.pending).toBeUndefined();
});

it("clears a rejected change when the server allowance is exhausted", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValueOnce(
      Response.json(
        {
          error: {
            code: "CUSTOMER_BOOKING_CHANGE_LIMIT_REACHED",
            message: "No changes remaining",
          },
        },
        { status: 409 },
      ),
    ),
  );
  const change = new BookingChange("old-booking");
  await expect(change.submit("request-1", slot)).rejects.toThrow(
    "No changes remaining",
  );
  expect(change.pending).toBeUndefined();
});

it("does not report an unconfirmed or mismatched response as a successful edit", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(Response.json({ ...confirmed, status: "HELD" })),
  );
  const change = new BookingChange("old-booking");
  await expect(change.submit("request-1", slot)).rejects.toThrow(
    "not been confirmed",
  );
  expect(change.pending).toBeDefined();
});

it("uses the business calendar date across a UTC date boundary", () => {
  expect(bookingDay("2026-11-03T01:00:00Z", "America/New_York")).toBe(
    "2026-11-02",
  );
});
