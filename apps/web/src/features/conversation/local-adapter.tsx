"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { MutableRefObject } from "react";
import type { AdapterProperties } from "./elevenlabs-adapter";
import type { ConversationClient, ConversationMode } from "./contracts";

type LocalAdapterProperties = AdapterProperties &
  Readonly<{ apiBaseUrl: string }>;
const VOICE_THRESHOLD = 0.018;
const SILENCE_MILLISECONDS = 750;

export function LocalConversationAdapter({
  children,
  ...properties
}: LocalAdapterProperties) {
  return children(useLocalConversationClient(properties));
}

function useLocalConversationClient({
  apiBaseUrl,
  onDisconnect,
  onDraft,
  onError,
  onTranscript,
}: Omit<LocalAdapterProperties, "children">): ConversationClient {
  const [status, setStatus] =
    useState<ConversationClient["status"]>("disconnected");
  const [mode, setMode] = useState<ConversationMode>();
  const [isMuted, setMutedState] = useState(false);
  const socketRef = useRef<WebSocket | undefined>(undefined);
  const streamRef = useRef<MediaStream | undefined>(undefined);
  const audioContextRef = useRef<AudioContext | undefined>(undefined);
  const processorRef = useRef<ScriptProcessorNode | undefined>(undefined);
  const mutedRef = useRef(false);
  const playingRef = useRef(false);
  const generationRef = useRef(0);
  const callbacksRef = useRef({ onDisconnect, onDraft, onError, onTranscript });
  useEffect(() => {
    callbacksRef.current = { onDisconnect, onDraft, onError, onTranscript };
  }, [onDisconnect, onDraft, onError, onTranscript]);

  const cleanup = useCallback(async () => {
    generationRef.current += 1;
    const socket = socketRef.current;
    socketRef.current = undefined;
    socket?.close(1000);
    processorRef.current?.disconnect();
    processorRef.current = undefined;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = undefined;
    const audioContext = audioContextRef.current;
    audioContextRef.current = undefined;
    playingRef.current = false;
    mutedRef.current = false;
    setMutedState(false);
    setMode(undefined);
    setStatus("disconnected");
    if (audioContext) await audioContext.close().catch(() => undefined);
  }, []);

  useEffect(
    () => () => {
      void cleanup();
    },
    [cleanup],
  );

  const start: ConversationClient["start"] = useCallback(
    async (authorization) => {
      if (
        authorization.provider !== "local" ||
        authorization.transport !== "websocket" ||
        authorization.websocketPath !== "/api/v1/development/local-conversation"
      )
        throw new Error(
          "Local conversation received an unsupported connection",
        );
      const generation = generationRef.current + 1;
      await cleanup();
      const current = () => generationRef.current === generation;
      if (!current())
        throw new Error("Local conversation startup was cancelled");
      setStatus("connecting");
      let audioContext: AudioContext | undefined;
      let stream: MediaStream | undefined;
      try {
        if (authorization.inputMode === "VOICE") {
          stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          if (!current()) {
            stream.getTracks().forEach((track) => track.stop());
            throw new Error("Local conversation startup was cancelled");
          }
          streamRef.current = stream;
          audioContext = new AudioContext();
          audioContextRef.current = audioContext;
          await audioContext.resume();
        }
        if (!current())
          throw new Error("Local conversation startup was cancelled");
        const websocketUrl = new URL(authorization.websocketPath, apiBaseUrl);
        if (!["http:", "https:"].includes(websocketUrl.protocol))
          throw new Error("The local API URL must use HTTP or HTTPS");
        websocketUrl.protocol =
          websocketUrl.protocol === "https:" ? "wss:" : "ws:";
        const socket = new WebSocket(websocketUrl);
        socket.binaryType = "arraybuffer";
        socketRef.current = socket;
        let playback = Promise.resolve();
        await new Promise<void>((resolve, reject) => {
          let ready = false;
          const timeout = window.setTimeout(
            () => reject(new Error("Local conversation connection timed out")),
            15_000,
          );
          const fail = (message: string) => {
            window.clearTimeout(timeout);
            if (!current()) {
              reject(new Error("Local conversation startup was cancelled"));
              socket.close();
              return;
            }
            if (ready) callbacksRef.current.onError(message);
            else reject(new Error(message));
            socket.close();
          };
          socket.onopen = () => {
            if (!current()) {
              reject(new Error("Local conversation startup was cancelled"));
              socket.close();
              return;
            }
            socket.send(
              JSON.stringify({
                session_id: authorization.sessionId,
                credential: authorization.credential,
              }),
            );
          };
          socket.onerror = () => fail("Local conversation WebSocket failed");
          socket.onmessage = (event) => {
            if (!current()) return;
            if (typeof event.data !== "string") {
              if (audioContext) {
                const context = audioContext;
                playback = playback
                  .then(() =>
                    playAudio(
                      event.data,
                      context,
                      playingRef,
                      (nextMode) => {
                        if (current()) setMode(nextMode);
                      },
                      current,
                    ),
                  )
                  .catch(() => {
                    if (current()) fail("Local speech playback failed");
                  });
              }
              return;
            }
            let message: unknown;
            try {
              message = JSON.parse(event.data);
            } catch {
              fail("Local conversation returned an invalid message");
              return;
            }
            if (!isMessage(message)) return;
            if (message.type === "ready" && !ready) {
              try {
                if (stream && audioContext) {
                  processorRef.current = startCapture(
                    stream,
                    audioContext,
                    socket,
                    mutedRef,
                    playingRef,
                  );
                }
              } catch {
                fail("Local microphone capture failed");
                return;
              }
              ready = true;
              window.clearTimeout(timeout);
              setStatus("connected");
              setMode("listening");
              resolve();
            } else if (
              message.type === "transcript" &&
              (message.speaker === "USER" || message.speaker === "AGENT") &&
              typeof message.text === "string"
            ) {
              callbacksRef.current.onTranscript(message.speaker, message.text);
            } else if (message.type === "draft") {
              void callbacksRef.current
                .onDraft({
                  fullName: optionalString(message.full_name),
                  email: optionalString(message.email),
                  phone: optionalString(message.phone),
                  intakeIntent: optionalString(message.intake_intent),
                  addressLine1: optionalString(message.address_line1),
                  city: optionalString(message.city),
                  stateCode: optionalString(message.state_code),
                  postalCode: optionalString(message.postal_code),
                  serviceKind: optionalString(message.service_kind),
                  preferredWindow: optionalString(message.preferred_window),
                  hazardousCondition: message.hazardous_condition === true,
                  handoffRequested: message.handoff_requested === true,
                })
                .catch(() =>
                  fail("The local intake draft could not be updated"),
                );
            } else if (
              message.type === "state" &&
              (message.mode === "speaking" || message.mode === "listening")
            ) {
              playingRef.current = message.mode === "speaking";
              setMode(message.mode);
            } else if (message.type === "error") {
              fail(
                typeof message.message === "string"
                  ? message.message
                  : "Local conversation failed",
              );
            }
          };
          socket.onclose = () => {
            window.clearTimeout(timeout);
            if (!ready)
              reject(new Error("Local conversation closed before connecting"));
            if (current()) {
              void cleanup();
              callbacksRef.current.onDisconnect();
            }
          };
        });
      } catch (error: unknown) {
        if (current()) await cleanup();
        throw error;
      }
    },
    [apiBaseUrl, cleanup],
  );

  const sendText = useCallback((text: string) => {
    const socket = socketRef.current;
    if (!text.trim() || text.length > 2_000)
      throw new Error("Enter a message of up to 2000 characters");
    if (socket?.readyState !== WebSocket.OPEN)
      throw new Error("The conversation is disconnected");
    socket.send(JSON.stringify({ type: "user_message", text: text.trim() }));
  }, []);

  return {
    status,
    mode,
    isMuted,
    start,
    end: cleanup,
    sendText,
    notifyTyping: () => undefined,
    setMuted: (muted) => {
      mutedRef.current = muted;
      setMutedState(muted);
    },
  };
}

function startCapture(
  stream: MediaStream,
  audioContext: AudioContext,
  socket: WebSocket,
  mutedRef: MutableRefObject<boolean>,
  playingRef: MutableRefObject<boolean>,
): ScriptProcessorNode {
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);
  const silentOutput = audioContext.createGain();
  silentOutput.gain.value = 0;
  source.connect(processor);
  processor.connect(silentOutput);
  silentOutput.connect(audioContext.destination);

  let speaking = false;
  let silenceSamples = 0;
  let utterance: Int16Array[] = [];
  let preRoll: Int16Array[] = [];
  processor.onaudioprocess = (event) => {
    if (
      mutedRef.current ||
      playingRef.current ||
      socket.readyState !== WebSocket.OPEN
    ) {
      speaking = false;
      silenceSamples = 0;
      utterance = [];
      preRoll = [];
      return;
    }
    const input = event.inputBuffer.getChannelData(0);
    const frame = downsamplePcm(input, audioContext.sampleRate);
    const rms = rootMeanSquare(input);
    if (!speaking) {
      preRoll.push(frame);
      preRoll = preRoll.slice(-3);
      if (rms >= VOICE_THRESHOLD) {
        speaking = true;
        utterance = [...preRoll];
        preRoll = [];
      }
      return;
    }
    utterance.push(frame);
    silenceSamples = rms < VOICE_THRESHOLD ? silenceSamples + frame.length : 0;
    if (
      silenceSamples >= (SILENCE_MILLISECONDS * 16_000) / 1_000 ||
      utterance.reduce((total, chunk) => total + chunk.length, 0) >= 16_000 * 29
    ) {
      socket.send(JSON.stringify({ type: "utterance_start" }));
      socket.send(joinPcm(utterance));
      socket.send(JSON.stringify({ type: "utterance_end" }));
      speaking = false;
      silenceSamples = 0;
      utterance = [];
    }
  };
  return processor;
}

async function playAudio(
  data: ArrayBuffer | Blob,
  audioContext: AudioContext,
  playingRef: MutableRefObject<boolean>,
  setMode: (mode: ConversationMode) => void,
  current: () => boolean,
) {
  if (!current()) return;
  const encoded = data instanceof Blob ? await data.arrayBuffer() : data;
  const buffer = await audioContext.decodeAudioData(encoded.slice(0));
  if (!current()) return;
  const source = audioContext.createBufferSource();
  source.buffer = buffer;
  source.connect(audioContext.destination);
  playingRef.current = true;
  setMode("speaking");
  await new Promise<void>((resolve) => {
    source.onended = () => {
      if (current()) {
        playingRef.current = false;
        setMode("listening");
      }
      resolve();
    };
    source.start();
  });
}

function downsamplePcm(input: Float32Array, inputRate: number): Int16Array {
  const ratio = inputRate / 16_000;
  const output = new Int16Array(Math.floor(input.length / ratio));
  for (let index = 0; index < output.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, input[Math.floor(index * ratio)]));
    output[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return output;
}

function joinPcm(frames: readonly Int16Array[]): ArrayBuffer {
  const length = frames.reduce((total, frame) => total + frame.length, 0);
  const output = new Int16Array(length);
  let offset = 0;
  for (const frame of frames) {
    output.set(frame, offset);
    offset += frame.length;
  }
  return output.buffer;
}

function rootMeanSquare(input: Float32Array): number {
  const sum = input.reduce((total, sample) => total + sample * sample, 0);
  return Math.sqrt(sum / input.length);
}

function isMessage(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && "type" in value;
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}
