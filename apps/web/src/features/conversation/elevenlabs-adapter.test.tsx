import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it, vi } from "vitest";
import { ElevenLabsConversationAdapter } from "./elevenlabs-adapter";
import type { ConversationClient } from "./contracts";

const sdk = vi.hoisted(() => ({
  sendContextualUpdate: vi.fn(),
  startSession: vi.fn((options: { onConnect: () => void }) =>
    options.onConnect(),
  ),
  endSession: vi.fn(),
  configuration: {} as Record<string, unknown>,
}));

vi.mock("@elevenlabs/react", () => ({
  ConversationProvider: ({ children }: { children: ReactNode }) => children,
  useConversationControls: () => ({
    sendContextualUpdate: sdk.sendContextualUpdate,
    endSession: sdk.endSession,
  }),
  useConversation: (configuration: Record<string, unknown>) => {
    sdk.configuration = configuration;
    return {
      status: "connected",
      mode: "listening",
      isMuted: false,
      startSession: sdk.startSession,
      endSession: sdk.endSession,
      setMuted: vi.fn(),
    };
  },
}));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

it("never retrieves account memory for a website whose memory capability is disabled", async () => {
  vi.stubGlobal("window", { setTimeout, clearTimeout });
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  let client!: ConversationClient;
  renderToStaticMarkup(
    <ElevenLabsConversationAdapter
      memoryEnabled={false}
      onDisconnect={vi.fn()}
      onDraft={vi.fn()}
      onError={vi.fn()}
      onApprovedFaqLookup={vi.fn()}
      onTranscript={vi.fn()}
      onBookingTool={vi.fn()}
    >
      {(value) => {
        client = value;
        return null;
      }}
    </ElevenLabsConversationAdapter>,
  );
  await client.start({
    sessionId: "website-session",
    inputMode: "VOICE",
    transport: "webrtc",
    credential: "synthetic-token",
    maximumDurationSeconds: 180,
    confirmationExpiresAt: "2030-01-01T00:30:00Z",
  });
  const tools = sdk.configuration.clientTools as Record<
    string,
    (input?: Record<string, unknown>) => unknown
  >;
  expect(String(await tools.retrieve_customer_memory())).toContain(
    "not enabled",
  );
  expect(String(await tools.remember_customer_memory({}))).toContain(
    "not enabled",
  );
  expect(fetcher).not.toHaveBeenCalled();
  expect(sdk.sendContextualUpdate).not.toHaveBeenCalled();
});

it.each(["VOICE", "TEXT"] as const)(
  "retrieves the same authorized memory on %s connection through the actual adapter",
  async (mode) => {
    vi.stubGlobal("window", { setTimeout, clearTimeout });
    const fetcher = vi.fn().mockResolvedValue(
      Response.json({
        summary: "Optional customer-confirmed context: morning appointments.",
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    let client!: ConversationClient;
    renderToStaticMarkup(
      <ElevenLabsConversationAdapter
        onDisconnect={vi.fn()}
        onDraft={vi.fn()}
        onError={vi.fn()}
        onApprovedFaqLookup={vi.fn()}
        onTranscript={vi.fn()}
        onBookingTool={vi.fn()}
      >
        {(value) => {
          client = value;
          return null;
        }}
      </ElevenLabsConversationAdapter>,
    );
    await client.start({
      sessionId: "authorized-session",
      inputMode: mode,
      transport: mode === "VOICE" ? "webrtc" : "websocket",
      credential:
        mode === "VOICE"
          ? "test-token"
          : "wss://api.elevenlabs.io/v1/convai/conversation?conversation_signature=test",
      maximumDurationSeconds: 180,
      confirmationExpiresAt: "2026-11-09T00:00:00Z",
    });
    await vi.waitFor(() =>
      expect(sdk.sendContextualUpdate).toHaveBeenCalledWith(
        "Optional customer-confirmed context: morning appointments.",
      ),
    );
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][0]).toContain(
      "authorized-session/memory/context",
    );
    expect(sdk.configuration.clientTools).toEqual(
      expect.objectContaining({
        retrieve_customer_memory: expect.any(Function),
        prepare_customer_memory: expect.any(Function),
        remember_customer_memory: expect.any(Function),
        confirm_appointment: expect.any(Function),
      }),
    );
    expect(sdk.startSession.mock.calls[0][0]).toMatchObject({
      textOnly: mode === "TEXT",
      connectionType: mode === "TEXT" ? "websocket" : "webrtc",
    });
  },
);
