import {
  customerMessage,
  type ConversationSpeaker,
  type VoiceLanguageSession,
  ProviderLanguageObserver,
  type ObservedLanguageResult,
} from "@insurance-operations/customer-core";
import { object, record, string } from "../lib/models";

type Options = {
  voiceLanguage?: VoiceLanguageSession;
  onLanguageResult?: (value?: ObservedLanguageResult) => void;
  onReadbackInterrupted?: () => void;
  credential: string;
  onConnect: () => void;
  onTurn: (speaker: ConversationSpeaker, text: string) => void;
  onTool: (
    name: string,
    parameters: Record<string, unknown>,
  ) => Promise<string>;
  onDisconnect: () => void;
  onError: (message: string) => void;
};

export class TextConnection {
  private socket?: WebSocket;
  private ready = false;
  private closed = false;
  private timer?: ReturnType<typeof setTimeout>;
  private queue = Promise.resolve();
  private results = new Map<string, { signature: string; result: string }>();
  private agentEvents = new Set<number>();
  private lastActivityAt = 0;
  private languageObserver = new ProviderLanguageObserver();
  constructor(private readonly options: Options) {
    this.languageObserver.start(options.voiceLanguage);
  }

  connect() {
    const socket = new WebSocket(this.options.credential);
    this.socket = socket;
    this.timer = setTimeout(
      () => this.fail("Chat could not connect in time. Please try again."),
      20_000,
    );
    socket.onopen = () => {
      if (this.closed) return;
      this.send({
        type: "conversation_initiation_client_data",
        conversation_config_override: { ...this.options.voiceLanguage?.overrides, conversation: { text_only: true } },
        dynamic_variables: { homepage_guest: false },
      });
    };
    socket.onmessage = (event) => {
      if (this.closed) return;
      if (typeof event.data !== "string" || event.data.length > 262144) {
        this.fail("Chat returned an unsupported event.");
        return;
      }
      this.queue = this.queue
        .then(async () => {
          if (!this.closed) await this.receive(object(JSON.parse(event.data)));
        })
        .catch(() => {
          this.fail(
            "Chat could not process a response. Your saved bookings are kept.",
          );
        });
    };
    socket.onerror = () =>
      this.fail(
        "Chat lost its connection. Your draft and saved bookings are kept.",
      );
    socket.onclose = () => {
      if (this.closed) return;
      this.closed = true;
      this.ready = false;
      clearTimeout(this.timer);
      this.options.onDisconnect();
    };
  }

  private send(data: unknown) {
    if (
      !this.socket ||
      this.socket.readyState !== WebSocket.OPEN ||
      this.closed
    )
      throw new Error("Connect to Line before sending a message.");
    this.socket.send(JSON.stringify(data));
  }

  private async receive(event: Record<string, unknown>) {
    if (event.type === "conversation_initiation_metadata") {
      if (!this.ready) {
        this.ready = true;
        clearTimeout(this.timer);
        this.options.onConnect();
      }
    } else if (event.type === "ping") {
      const ping = object(event.ping_event);
      if (typeof ping.event_id === "number")
        this.send({ type: "pong", event_id: ping.event_id });
    } else if (event.type === "agent_response") {
      const response = object(event.agent_response_event);
      const text = string(response.agent_response);
      const eventId = response.event_id;
      if (typeof eventId === "number") {
        if (this.agentEvents.has(eventId)) return;
        this.agentEvents.add(eventId);
      }
      this.options.onTurn("AGENT", text);
    } else if (event.type === "agent_tool_request") {
      const tool = event.agent_tool_request;
      if (record(tool) && tool.tool_name === "language_detection" && tool.tool_type === "system") this.options.onReadbackInterrupted?.();
    } else if (event.type === "interruption") {
      this.options.onReadbackInterrupted?.();
    } else if (event.type === "agent_tool_response_full_payload" || event.type === "agent_tool_response") {
      this.options.onLanguageResult?.(this.languageObserver.receive(event.agent_tool_response_full_payload ?? event.agent_tool_response));
    } else if (event.type === "client_tool_call") {
      const call = object(event.client_tool_call);
      const name = string(call.tool_name),
        callId = string(call.tool_call_id);
      const parameters = object(call.parameters ?? {});
      const signature = JSON.stringify({ name, parameters });
      const previous = this.results.get(callId);
      if (previous && previous.signature !== signature)
        throw new Error("Tool reference changed.");
      let result = previous?.result;
      let isError = false;
      if (result === undefined) {
        if (this.results.size >= 120) throw new Error("Too many tool calls.");
        try {
          result = await this.options.onTool(name, parameters);
        } catch {
          result = JSON.stringify({
            ok: false,
            message:
              "This tool could not finish. Do not claim success; retry the same step.",
          });
          isError = true;
        }
        this.results.set(callId, { signature, result });
      }
      if (!this.closed)
        this.send({
          type: "client_tool_result",
          tool_call_id: callId,
          result,
          is_error: isError,
        });
    } else if (event.type === "error" || (record(event.error) && event.error)) {
      this.fail(
        "The chat service could not continue. Your saved bookings are kept.",
      );
    }
  }

  sendText(value: string) {
    if (!this.ready) throw new Error("Wait for Line to connect.");
    const text = customerMessage(value);
    this.send({ type: "user_message", text });
    this.options.onTurn("USER", text);
  }

  notifyTyping() {
    if (
      this.ready &&
      !this.closed &&
      Date.now() - this.lastActivityAt >= 1000
    ) {
      this.lastActivityAt = Date.now();
      this.send({ type: "user_activity" });
    }
  }
  private fail(message: string) {
    if (this.closed) return;
    this.close();
    this.options.onError(message);
  }
  close() {
    this.closed = true;
    this.ready = false;
    clearTimeout(this.timer);
    this.socket?.close();
    this.socket = undefined;
    this.results.clear();
  }
}
