import { afterEach, expect, it, vi } from "vitest";
import { authorizeConversationSession, endConversationSession } from "./api";
import { lookupConversationApprovedFaq } from "../approved-faqs/api";

afterEach(() => vi.unstubAllGlobals());

it("preserves hosted authorization for browser session, FAQ and end requests", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      Response.json({
        session_id: "session-1",
        connection: { credential: "short-lived-token" },
        maximum_duration_seconds: 180,
        confirmation_expires_at: "2026-10-25T00:00:00Z",
      }),
    )
    .mockResolvedValueOnce(
      Response.json({
        matched: false,
        answer: null,
        source: null,
        fallback_message: "Ask the business to follow up.",
      }),
    )
    .mockResolvedValueOnce(Response.json({ review_available: true }));
  vi.stubGlobal("fetch", fetcher);
  const token = "fictional-admin-token";
  await authorizeConversationSession("https://api.example.com", token);
  await lookupConversationApprovedFaq(
    "https://api.example.com",
    "session-1",
    "Hours?",
    token,
  );
  await endConversationSession(
    "https://api.example.com",
    "session-1",
    "COMPLETED",
    token,
  );
  expect(fetcher).toHaveBeenCalledTimes(3);
  for (const [url, options] of fetcher.mock.calls) {
    expect(url).not.toContain(token);
    expect(options.headers["X-Demo-Admin-Token"]).toBe(token);
  }
});
