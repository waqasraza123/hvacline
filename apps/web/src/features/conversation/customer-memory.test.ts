import { afterEach, expect, it, vi } from "vitest";
import { customerMemoryTools } from "./customer-memory";
import type { ConversationTurn } from "./contracts";

afterEach(() => vi.unstubAllGlobals());

it("loads only bounded authorized context and uses the session proxy", async () => {
  const fetcher = vi.fn().mockResolvedValue(
    Response.json({
      summary: "Optional customer-confirmed context: weekday mornings.",
    }),
  );
  vi.stubGlobal("fetch", fetcher);
  const tools = customerMemoryTools({
    sessionId: () => "owned-session",
    transcript: () => [],
  });
  const send = vi.fn();
  await tools.loadContext(send);
  expect(send).toHaveBeenCalledWith(
    "Optional customer-confirmed context: weekday mornings.",
  );
  expect(fetcher.mock.calls[0][0]).toBe(
    "/api/v1/development/conversation-sessions/owned-session/memory/context",
  );
  expect(fetcher.mock.calls[0][1]).toMatchObject({
    method: "POST",
    cache: "no-store",
    body: "{}",
  });
  expect(fetcher.mock.calls[0][1].headers).toEqual({
    "Content-Type": "application/json",
  });
});

it.each(["", "x".repeat(2001)])(
  "does not deliver empty or oversized context",
  async (summary) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(Response.json({ summary })),
    );
    const tools = customerMemoryTools({
      sessionId: () => "session",
      transcript: () => [],
    });
    const send = vi.fn();
    await tools.loadContext(send);
    expect(send).not.toHaveBeenCalled();
  },
);

it("never retrieves without an active session or delivers a late response to a new conversation", async () => {
  let current: string | undefined;
  let finish!: (response: Response) => void;
  const fetcher = vi.fn().mockImplementation(
    () =>
      new Promise<Response>((resolve) => {
        finish = resolve;
      }),
  );
  vi.stubGlobal("fetch", fetcher);
  const tools = customerMemoryTools({
    sessionId: () => current,
    transcript: () => [],
  });
  const send = vi.fn();
  await tools.loadContext(send);
  expect(fetcher).not.toHaveBeenCalled();
  current = "old-session";
  const pending = tools.loadContext(send);
  current = "new-session";
  finish(Response.json({ summary: "Private old context" }));
  await pending;
  expect(send).not.toHaveBeenCalled();
});

it("preserves the confirmed save payload across unknown responses and rejects a changed retry", async () => {
  let turns: ConversationTurn[] = [
    { speaker: "AGENT", text: "Memory readback" },
    { speaker: "USER", text: "yes" },
  ];
  const fetcher = vi
    .fn()
    .mockRejectedValueOnce(new TypeError("lost response"))
    .mockResolvedValue(new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetcher);
  const tools = customerMemoryTools({
    sessionId: () => "session",
    transcript: () => turns,
  });
  const parameters = {
    facts: [{ key: "appointment_time", value: "MORNING" }],
    request_id: "save-1",
    explicit_confirmation: true,
  };
  expect(
    JSON.parse(await tools.remember_customer_memory(parameters)),
  ).toMatchObject({ available: false });
  turns = [...turns, { speaker: "AGENT", text: "Retrying" }];
  expect(JSON.parse(await tools.remember_customer_memory(parameters))).toEqual({
    saved: true,
  });
  expect(fetcher.mock.calls[0][1].body).toBe(fetcher.mock.calls[1][1].body);
  expect(
    JSON.parse(
      await tools.remember_customer_memory({
        ...parameters,
        explicit_confirmation: false,
      }),
    ),
  ).toMatchObject({ available: false });
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it("handles service, transport, malformed response and context delivery failures without throwing", async () => {
  const tools = customerMemoryTools({
    sessionId: () => "session",
    transcript: () => [],
  });
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(new Response(null, { status: 503 }))
    .mockRejectedValueOnce(new TypeError("offline"))
    .mockResolvedValueOnce(new Response("invalid json"))
    .mockResolvedValueOnce(Response.json({ summary: "Confirmed preference" }));
  vi.stubGlobal("fetch", fetcher);
  const send = vi.fn(() => {
    throw new Error("disconnected");
  });
  for (let attempt = 0; attempt < 4; attempt++)
    await expect(tools.loadContext(send)).resolves.toBeUndefined();
  expect(send).toHaveBeenCalledTimes(1);
});
