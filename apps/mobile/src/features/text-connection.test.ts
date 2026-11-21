import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { TextConnection } from "./text-connection";

class FakeSocket {
  static OPEN = 1;
  static latest: FakeSocket;
  readyState = 1;
  sent: Record<string, unknown>[] = [];
  onopen?: () => void;
  onmessage?: (event: { data: string }) => void;
  onclose?: () => void;
  onerror?: () => void;
  constructor(readonly url: string) {
    FakeSocket.latest = this;
  }
  send(data: string) {
    this.sent.push(JSON.parse(data));
  }
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
  receive(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

beforeEach(() => vi.stubGlobal("WebSocket", FakeSocket));
afterEach(() => {
  vi.unstubAllGlobals();
});

function connection(onTool = vi.fn().mockResolvedValue('{"ok":true}')) {
  const onConnect = vi.fn(),
    onTurn = vi.fn(),
    onDisconnect = vi.fn(),
    onError = vi.fn();
  const client = new TextConnection({
    credential:
      "wss://api.elevenlabs.io/v1/convai/conversation?signature=fictional",
    onConnect,
    onTurn,
    onTool,
    onDisconnect,
    onError,
  });
  client.connect();
  FakeSocket.latest.onopen?.();
  return {
    client,
    socket: FakeSocket.latest,
    onConnect,
    onTurn,
    onDisconnect,
    onError,
    onTool,
  };
}

it("applies the server language override while retaining silent Chat transport", () => {
  const client = new TextConnection({
    credential: "wss://api.elevenlabs.io/v1/convai/conversation?signature=fictional",
    voiceLanguage: { language: "es", allowed_languages: ["en", "es"], automatic_switching: true, overrides: { agent: { language: "es" } } },
    onConnect: vi.fn(), onTurn: vi.fn(), onTool: vi.fn(), onDisconnect: vi.fn(), onError: vi.fn(),
  });
  client.connect(); FakeSocket.latest.onopen?.();
  expect(FakeSocket.latest.sent[0]).toMatchObject({
    conversation_config_override: { agent: { language: "es" }, conversation: { text_only: true } },
  });
  client.close();
});

it("requests text-only transport and enables sending only after metadata", async () => {
  const value = connection();
  try {
    expect(value.socket.sent[0]).toMatchObject({
      type: "conversation_initiation_client_data",
      conversation_config_override: { conversation: { text_only: true } },
    });
    expect(() => value.client.sendText("Hello")).toThrow();
    value.socket.receive({
      type: "conversation_initiation_metadata",
      conversation_initiation_metadata_event: {
        conversation_id: "fictional-conversation",
      },
    });
    await vi.waitFor(() => expect(value.onConnect).toHaveBeenCalledOnce());
    value.client.sendText("  Hello Line  ");
    expect(value.socket.sent.at(-1)).toEqual({
      type: "user_message",
      text: "Hello Line",
    });
    expect(value.onTurn).toHaveBeenCalledWith("USER", "Hello Line");
    expect(value.socket.sent.some((event) => "user_audio_chunk" in event)).toBe(
      false,
    );
  } finally {
    value.client.close();
  }
});

it("records full readbacks before executing tools and deduplicates tool-call references", async () => {
  const events: string[] = [];
  const tool = vi.fn(async () => {
    events.push("tool");
    return '{"ok":true}';
  });
  const value = connection(tool);
  value.onTurn.mockImplementation(() => events.push("readback"));
  try {
    value.socket.receive({
      type: "agent_response",
      agent_response_event: {
        event_id: 1,
        agent_response: "Read the full details, then confirm.",
      },
    });
    const call = {
      type: "client_tool_call",
      client_tool_call: {
        tool_name: "confirm_service_request",
        tool_call_id: "fictional-call",
        parameters: { explicit_confirmation: true },
      },
    };
    value.socket.receive(call);
    value.socket.receive(call);
    await vi.waitFor(() =>
      expect(
        value.socket.sent.filter(
          (event) => event.type === "client_tool_result",
        ),
      ).toHaveLength(2),
    );
    expect(events).toEqual(["readback", "tool"]);
    expect(tool).toHaveBeenCalledOnce();
  } finally {
    value.client.close();
  }
});

it("does not execute delayed events after closing", async () => {
  const value = connection();
  value.socket.receive({
    type: "client_tool_call",
    client_tool_call: {
      tool_name: "reserve_appointment",
      tool_call_id: "fictional-call",
      parameters: {},
    },
  });
  value.client.close();
  await Promise.resolve();
  await Promise.resolve();
  expect(value.onTool).not.toHaveBeenCalled();
  expect(value.onDisconnect).not.toHaveBeenCalled();
});

it("closes on invalid protocol data without surfacing raw provider content", async () => {
  const value = connection();
  value.socket.onmessage?.({ data: "not-json-fictional" });
  await vi.waitFor(() => expect(value.onError).toHaveBeenCalledOnce());
  expect(value.socket.readyState).toBe(3);
  expect(value.onError.mock.calls[0][0]).not.toContain("not-json-fictional");
});
