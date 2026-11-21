import type { ConversationSpeaker, ConversationTurn } from "./contracts";
import { appendTranscript } from "./review";

const unavailable = JSON.stringify({
  available: false,
  message: "Memory is unavailable. Continue booking without it.",
});

export function customerMemoryTools({
  sessionId,
  transcript,
}: {
  sessionId: () => string | undefined;
  transcript: () => readonly ConversationTurn[];
}) {
  let pendingSave:
    | { session: string; requestId: string; parameters: string; body: string }
    | undefined;
  async function request(
    action: "context" | "readback" | "remember",
    parameters: Record<string, unknown> = {},
  ): Promise<string> {
    const current = sessionId();
    if (!current) return unavailable;
    try {
      let body = JSON.stringify(parameters);
      if (action === "remember") {
        if (typeof parameters.request_id !== "string") return unavailable;
        if (
          pendingSave?.session === current &&
          pendingSave.requestId === parameters.request_id
        ) {
          if (pendingSave.parameters !== body) return unavailable;
          body = pendingSave.body;
        } else {
          pendingSave = {
            session: current,
            requestId: parameters.request_id,
            parameters: body,
            body: JSON.stringify({
              ...parameters,
              transcript: transcript().slice(-60),
            }),
          };
          body = pendingSave.body;
        }
      }
      const response = await fetch(
        `/api/v1/development/conversation-sessions/${encodeURIComponent(current)}/memory/${action}`,
        {
          method: "POST",
          cache: "no-store",
          headers: { "Content-Type": "application/json" },
          signal: AbortSignal.timeout(5000),
          body,
        },
      );
      if (!response.ok || sessionId() !== current) return unavailable;
      return response.status === 204
        ? JSON.stringify({ saved: true })
        : await response.text();
    } catch {
      return unavailable;
    }
  }

  return {
    reset: () => {
      pendingSave = undefined;
    },
    retrieve_customer_memory: () => request("context"),
    prepare_customer_memory: (parameters: Record<string, unknown>) =>
      request("readback", parameters),
    remember_customer_memory: (parameters: Record<string, unknown>) =>
      request("remember", parameters),
    async loadContext(sendContext: (context: string) => void): Promise<void> {
      const current = sessionId();
      if (!current) return;
      try {
        const result: unknown = JSON.parse(await request("context"));
        if (
          sessionId() === current &&
          typeof result === "object" &&
          result !== null &&
          "summary" in result &&
          typeof result.summary === "string" &&
          result.summary.trim() &&
          result.summary.length <= 2000
        ) {
          sendContext(result.summary);
        }
      } catch {
        // Optional memory must never interrupt the booking conversation.
      }
    },
  };
}

export function customerMemorySession() {
  let current: string | undefined;
  let turns: ConversationTurn[] = [];
  const tools = customerMemoryTools({
    sessionId: () => current,
    transcript: () => turns,
  });
  return {
    ...tools,
    start(sessionId: string) {
      current = sessionId;
      turns = [];
      tools.reset();
    },
    end() {
      current = undefined;
      turns = [];
      tools.reset();
    },
    record(speaker: ConversationSpeaker, text: string) {
      if (!current) return;
      turns = appendTranscript(turns, speaker, text).slice(-60);
    },
  };
}
