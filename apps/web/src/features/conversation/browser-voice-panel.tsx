"use client";

import { useEffect, useState } from "react";
import { getReceptionistSettings } from "../receptionist/api";
import type { ReceptionistSettings } from "../receptionist/contracts";
import { VoiceTest } from "./voice-test";

export function BrowserVoicePanel({
  apiBaseUrl,
  adminToken,
}: {
  apiBaseUrl: string;
  adminToken: string;
}) {
  const [settings, setSettings] = useState<ReceptionistSettings>();
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    void getReceptionistSettings(apiBaseUrl, adminToken).then(
      (value) => {
        if (active) setSettings(value);
      },
      () => {
        if (active)
          setError(
            "Unable to load the receptionist. Reopen this tab to retry.",
          );
      },
    );
    return () => {
      active = false;
    };
  }, [apiBaseUrl, adminToken]);
  if (error) return <p role="alert">{error}</p>;
  if (!settings) return <p role="status">Loading browser receptionist…</p>;
  return (
    <VoiceTest
      apiBaseUrl={apiBaseUrl}
      adminToken={adminToken}
      receptionistSettings={settings}
    />
  );
}
