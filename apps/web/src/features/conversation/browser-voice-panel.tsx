"use client";

import { useEffect, useState } from "react";
import { getReceptionistSettings } from "../receptionist/api";
import type { ReceptionistSettings } from "../receptionist/contracts";
import { VoiceTest } from "./voice-test";

export function BrowserVoicePanel({
  apiBaseUrl,
  adminToken,
  presentation,
  onActivityChange,
  onViewAppointments,
  onViewBooking,
}: {
  apiBaseUrl: string;
  adminToken?: string;
  presentation?: "workspace" | "customer";
  onActivityChange?: (active: boolean) => void;
  onViewAppointments?: () => void;
  onViewBooking?: (appointmentId: string) => void;
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
  if (error)
    return (
      <div className="customer-empty">
        <h2>Line couldn’t connect.</h2>
        <p role="alert">Please refresh the page and try again.</p>
      </div>
    );
  if (!settings)
    return (
      <div className="customer-empty" role="status">
        <span className="customer-loading" />
        <p>Getting Line ready for you…</p>
      </div>
    );
  return (
    <VoiceTest
      apiBaseUrl={apiBaseUrl}
      adminToken={adminToken}
      receptionistSettings={settings}
      presentation={presentation}
      onActivityChange={onActivityChange}
      onViewAppointments={onViewAppointments}
      onViewBooking={onViewBooking}
    />
  );
}
