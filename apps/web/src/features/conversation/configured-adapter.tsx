"use client";

import { useRef, useState } from "react";

import {
  ElevenLabsConversationAdapter,
  type AdapterProperties,
} from "./elevenlabs-adapter";
import { LocalConversationAdapter } from "./local-adapter";
import type { ConversationClient } from "./contracts";

type ConfiguredAdapterProperties = AdapterProperties &
  Readonly<{ apiBaseUrl: string }>;

export function ConfiguredConversationAdapter(
  properties: ConfiguredAdapterProperties,
) {
  return (
    <ElevenLabsConversationAdapter {...properties}>
      {(elevenLabsClient) => (
        <LocalConversationAdapter {...properties}>
          {(localClient) => (
            <AdapterSelector
              {...properties}
              elevenLabsClient={elevenLabsClient}
              localClient={localClient}
            />
          )}
        </LocalConversationAdapter>
      )}
    </ElevenLabsConversationAdapter>
  );
}

type SelectorProperties = ConfiguredAdapterProperties &
  Readonly<{
    elevenLabsClient: ConversationClient;
    localClient: ConversationClient;
  }>;

function AdapterSelector({
  children,
  elevenLabsClient,
  localClient,
}: SelectorProperties) {
  const [provider, setProvider] = useState<"elevenlabs" | "local">(
    "elevenlabs",
  );
  const providerRef = useRef(provider);
  const selected = provider === "local" ? localClient : elevenLabsClient;
  const activeClient = () =>
    providerRef.current === "local" ? localClient : elevenLabsClient;
  return children({
    ...selected,
    start: async (authorization, backgroundContext) => {
      providerRef.current = authorization.provider ?? "elevenlabs";
      setProvider(providerRef.current);
      await activeClient().start(authorization, backgroundContext);
    },
    end: () => activeClient().end(),
    sendText: (text) => activeClient().sendText(text),
    notifyTyping: () => activeClient().notifyTyping(),
    setMuted: (muted) => activeClient().setMuted(muted),
  });
}
