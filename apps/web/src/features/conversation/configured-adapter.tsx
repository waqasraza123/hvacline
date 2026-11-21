"use client";

import { useState } from "react";

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
  const selected = provider === "local" ? localClient : elevenLabsClient;
  return children({
    ...selected,
    start: async (authorization, backgroundContext) => {
      const next = authorization.provider ?? "elevenlabs";
      setProvider(next);
      await (next === "local" ? localClient : elevenLabsClient).start(
        authorization,
        backgroundContext,
      );
    },
    end: async () => {
      const results = await Promise.allSettled([
        localClient.end(),
        elevenLabsClient.end(),
      ]);
      const failure = results.find((result) => result.status === "rejected");
      if (failure?.status === "rejected") throw failure.reason;
    },
  });
}
