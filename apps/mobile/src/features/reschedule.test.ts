import { beforeEach, expect, it, vi } from "vitest";
import { MobileApi } from "../lib/api";
import { RescheduleSession } from "./reschedule";

const storage = vi.hoisted(() => ({
  getItemAsync: vi.fn(),
  setItemAsync: vi.fn(),
  deleteItemAsync: vi.fn(),
  WHEN_UNLOCKED_THIS_DEVICE_ONLY: "device-only",
}));
vi.mock("expo-secure-store", () => storage);
vi.mock("expo-crypto", () => ({
  randomUUID: () => "00000000-0000-4000-8000-000000000004",
}));

const accountId = "00000000-0000-4000-8000-000000000001";
const appointmentId = "00000000-0000-4000-8000-000000000002";
const requestId = "00000000-0000-4000-8000-000000000003";
const slot = {
  team_key: "test-team",
  starts_at: "2026-12-01T14:00:00Z",
  ends_at: "2026-12-01T15:00:00Z",
};
const result = {
  id: "00000000-0000-4000-8000-000000000005",
  service_request_id: requestId,
  ...slot,
  status: "CONFIRMED",
  hold_expires_at: "2026-11-20T15:00:00Z",
};
const api = new MobileApi(
  "https://hvacline.example",
  "fictional-mobile-session-token-for-tests",
);

beforeEach(() => {
  vi.restoreAllMocks();
  Object.values(storage).forEach((value) => {
    if (typeof value === "function") value.mockReset();
  });
  storage.setItemAsync.mockResolvedValue(undefined);
  storage.deleteItemAsync.mockResolvedValue(undefined);
});

it("does not submit an appointment change unless its reference can be saved first", async () => {
  const request = vi.spyOn(api, "request");
  storage.setItemAsync.mockRejectedValueOnce(new Error("Device locked"));
  const session = new RescheduleSession(api, accountId, appointmentId);
  await expect(session.confirm(requestId, slot)).rejects.toThrow(
    "Device locked",
  );
  expect(request).not.toHaveBeenCalled();
});

it("replays exactly the original change after a lost response and app restart", async () => {
  const request = vi
    .spyOn(api, "request")
    .mockRejectedValueOnce(new Error("Lost response"));
  const session = new RescheduleSession(api, accountId, appointmentId);
  await expect(session.confirm(requestId, slot)).rejects.toThrow(
    "Lost response",
  );
  const original = request.mock.calls[0];
  storage.getItemAsync.mockResolvedValueOnce(
    storage.setItemAsync.mock.calls[0][1],
  );
  const resumed = new RescheduleSession(api, accountId, appointmentId);
  await resumed.restore();
  request.mockResolvedValueOnce(result);
  await expect(resumed.confirm(requestId)).resolves.toMatchObject({
    status: "CONFIRMED",
  });
  expect(request.mock.calls[1]).toEqual(original);
  expect(storage.deleteItemAsync).toHaveBeenCalledOnce();
});

it("retains the original request when a mismatched success response arrives", async () => {
  vi.spyOn(api, "request").mockResolvedValueOnce({
    ...result,
    team_key: "another-team",
  });
  const session = new RescheduleSession(api, accountId, appointmentId);
  await expect(session.confirm(requestId, slot)).rejects.toThrow(
    "not confirmed",
  );
  expect(session.hasPending).toBe(true);
  expect(storage.deleteItemAsync).not.toHaveBeenCalled();
});

it("does not replay another server's saved request", async () => {
  storage.getItemAsync.mockResolvedValueOnce(
    JSON.stringify({ origin: "https://other.example", request: {} }),
  );
  const request = vi.spyOn(api, "request");
  await expect(
    new RescheduleSession(api, accountId, appointmentId).restore(),
  ).rejects.toThrow("another server");
  expect(request).not.toHaveBeenCalled();
});
