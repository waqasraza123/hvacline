"use client";

import { useEffect, useState } from "react";
import { requestApi, type ScheduleResponse } from "./api";

type IntegrationStatus = {
  google_enabled: boolean;
  email_enabled: boolean;
  connections: {
    id: string;
    team_key: string;
    calendar_id: string;
    status: string;
    last_error: string | null;
  }[];
  sync: { appointment_id: string; status: string; last_error: string | null }[];
  notifications: {
    id: string;
    appointment_id: string;
    kind: string;
    status: string;
    delivery_status: string | null;
    last_error: string | null;
  }[];
};

export function CalendarConnections({
  baseUrl,
  token,
  schedule,
}: {
  baseUrl: string;
  token: string;
  schedule: ScheduleResponse;
}) {
  const [data, setData] = useState<IntegrationStatus | null>(null);
  const [calendarIds, setCalendarIds] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    let active = true;
    requestApi<IntegrationStatus>(baseUrl, token, "hvac/integrations").then(
      (result) => {
        if (active) setData(result);
      },
      (failure: unknown) => {
        if (active)
          setError(
            failure instanceof Error
              ? failure.message
              : "Connections could not be loaded.",
          );
      },
    );
    return () => {
      active = false;
    };
  }, [baseUrl, token]);

  async function refresh() {
    setBusy(true);
    setError("");
    try {
      setData(
        await requestApi<IntegrationStatus>(
          baseUrl,
          token,
          "hvac/integrations",
        ),
      );
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Connections could not be loaded.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function connect(teamKey: string, existingCalendarId?: string) {
    const popup = window.open("about:blank", "_blank");
    if (!popup) {
      setError("Allow popups to authorize Google Calendar, then try again.");
      return;
    }
    popup.opener = null;
    setBusy(true);
    setError("");
    try {
      const grant = await requestApi<{
        launch_url: string;
        state: string;
        browser_secret: string;
      }>(baseUrl, token, "hvac/integrations/google/authorize", "POST", {
        team_key: teamKey,
        calendar_id:
          calendarIds[teamKey]?.trim() || existingCalendarId || "primary",
      });
      const launch = new URL(grant.launch_url);
      if (
        launch.origin !== new URL(baseUrl).origin ||
        launch.pathname !==
          "/api/v1/development/hvac/integrations/google/launch"
      )
        throw new Error(
          "The calendar callback does not match this backend. Ask the workspace owner to check its configuration.",
        );
      const form = popup.document.createElement("form");
      form.method = "POST";
      form.action = grant.launch_url;
      for (const [name, value] of Object.entries({
        state: grant.state,
        browser_secret: grant.browser_secret,
      })) {
        const input = popup.document.createElement("input");
        input.type = "hidden";
        input.name = name;
        input.value = value;
        form.appendChild(input);
      }
      popup.document.body.appendChild(form);
      form.submit();
      setMessage(
        "Complete authorization in the new tab, then refresh connections here.",
      );
    } catch (failure) {
      popup.close();
      setError(
        failure instanceof Error
          ? failure.message
          : "Google Calendar could not be connected.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function disconnect(id: string) {
    setBusy(true);
    setError("");
    try {
      await requestApi(
        baseUrl,
        token,
        `hvac/integrations/google/${id}/disconnect`,
        "POST",
      );
      setData(
        await requestApi<IntegrationStatus>(
          baseUrl,
          token,
          "hvac/integrations",
        ),
      );
      setMessage(
        "Calendar disconnected. This team's booking stays paused until it reconnects.",
      );
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Calendar could not be disconnected.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="ops-card"
      aria-label="Calendar connections and booking messages"
    >
      <div className="ops-section-title">
        <div>
          <p className="eyebrow">CONNECTIONS & MESSAGES</p>
          <h2>Google Calendar and booking emails</h2>
        </div>
        <button type="button" disabled={busy} onClick={() => void refresh()}>
          Refresh connections
        </button>
      </div>
      <p className="section-help">
        Connect one writable Google calendar per team. Teams without a
        connection use the internal schedule. A disconnected calendar pauses
        that team's booking. External changes require staff review.
      </p>
      {error && (
        <p className="ops-error" role="alert">
          {error}
        </p>
      )}
      {message && (
        <p className="ops-message" role="status">
          {message}
        </p>
      )}
      {data && (
        <>
          {!data.google_enabled && (
            <p>Google Calendar connection is awaiting workspace owner setup.</p>
          )}
          {(schedule.configuration?.teams ?? []).map((team) => {
            const connection = data.connections.find(
              (row) => row.team_key === team.key,
            );
            return (
              <article className="request-row" key={team.key}>
                <div>
                  <h3>{team.name}</h3>
                  <p>
                    {connection?.status.replaceAll("_", " ") ??
                      "Internal calendar"}
                  </p>
                  <label>
                    Google calendar ID
                    <input
                      value={
                        calendarIds[team.key] ??
                        connection?.calendar_id ??
                        "primary"
                      }
                      disabled={busy || !data.google_enabled}
                      onChange={(event) =>
                        setCalendarIds({
                          ...calendarIds,
                          [team.key]: event.target.value,
                        })
                      }
                    />
                  </label>
                  <p className="section-help">
                    Use primary for your main calendar, or copy a calendar ID
                    from Google Calendar settings. Each team needs a separate
                    calendar.
                  </p>
                  {connection?.last_error && (
                    <p role="status">
                      Calendar access needs attention. Reconnect to restore
                      access.
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  disabled={busy || !data.google_enabled}
                  onClick={() =>
                    void connect(team.key, connection?.calendar_id)
                  }
                >
                  {connection ? "Reconnect Google" : "Connect Google"}
                </button>
                {connection && connection.status !== "DISCONNECTED" && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void disconnect(connection.id)}
                  >
                    Disconnect and pause booking
                  </button>
                )}
              </article>
            );
          })}
          <h3>Calendar sync</h3>
          {data.sync.length === 0 ? (
            <p className="section-help">No external calendar bookings yet.</p>
          ) : (
            data.sync.map((row) => (
              <p key={row.appointment_id}>
                Booking {row.appointment_id.slice(0, 8)} ·{" "}
                {row.status.replaceAll("_", " ")}
                {row.last_error
                  ? " · Staff review required; messages paused"
                  : ""}
              </p>
            ))
          )}
          <h3>Booking confirmations and reminders</h3>
          <p className="section-help">
            {data.email_enabled
              ? "Email delivery is enabled for bookings with a confirmed email address."
              : "Email delivery is awaiting workspace owner setup."}{" "}
            Accepted means the email provider has received the message.
            Delivered means the recipient's mail server accepted it.
          </p>
          {data.notifications.length === 0 ? (
            <p className="section-help">No queued booking emails yet.</p>
          ) : (
            data.notifications.map((row) => (
              <p key={row.id}>
                Booking {row.appointment_id.slice(0, 8)} ·{" "}
                {row.kind.replaceAll("_", " ")} ·{" "}
                {row.delivery_status ?? row.status}
                {row.last_error && (
                  <> · {row.last_error.replaceAll("_", " ")}</>
                )}
              </p>
            ))
          )}
        </>
      )}
    </section>
  );
}
