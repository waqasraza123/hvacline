"use client";
import { useState } from "react";
import type { ScheduleResponse, Schedule, Window } from "./api";

export function ScheduleForm({
  value,
  save,
  busy,
}: {
  value: ScheduleResponse;
  save: (configuration: Schedule) => Promise<void>;
  busy: boolean;
}) {
  const [enabled, setEnabled] = useState(value.configuration?.enabled ?? false);
  const [timezone, setTimezone] = useState(
    value.configuration?.timezone ?? "America/New_York",
  );
  const [postalCodes, setPostalCodes] = useState(
    value.configuration?.postal_codes.join(", ") ?? "",
  );
  const [duration, setDuration] = useState(
    value.configuration?.duration_minutes ?? 60,
  );
  const [notice, setNotice] = useState(
    value.configuration?.notice_minutes ?? 120,
  );
  const [cutoff, setCutoff] = useState(
    value.configuration?.cancellation_notice_minutes ?? 120,
  );
  const [windows, setWindows] = useState<Window[]>(
    value.configuration?.windows ?? [],
  );
  const [teams, setTeams] = useState<Schedule["teams"]>(
    value.configuration?.teams ?? [],
  );
  const [formError, setFormError] = useState("");
  return (
    <form
      className="ops-card schedule-form"
      onSubmit={async (event) => {
        event.preventDefault();
        setFormError("");
        try {
          await save({
            expected_version: value.version,
            enabled,
            timezone,
            postal_codes: postalCodes.split(/[\s,]+/).filter(Boolean),
            windows,
            teams,
            duration_minutes: duration,
            notice_minutes: notice,
            cancellation_notice_minutes: cutoff,
            horizon_days: value.configuration?.horizon_days ?? 30,
          });
        } catch (error) {
          setFormError(
            error instanceof Error
              ? error.message
              : "Settings could not be saved.",
          );
        }
      }}
    >
      <div className="ops-section-title">
        <div>
          <p className="eyebrow">DISPATCH RULES</p>
          <h2>Your booking calendar</h2>
        </div>
        <span className="sample-badge">Internal calendar</span>
      </div>
      <p className="section-help">
        Only enable booking when this workspace reflects your technicians’
        actual availability. External calendar sync is not active.
      </p>
      <label className="ops-checkbox">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(event) => setEnabled(event.target.checked)}
        />{" "}
        Enable appointment booking for these teams
      </label>
      <div className="ops-form-grid">
        <label>
          Business timezone
          <select
            value={timezone}
            onChange={(event) => setTimezone(event.target.value)}
          >
            {[
              "America/New_York",
              "America/Chicago",
              "America/Denver",
              "America/Phoenix",
              "America/Los_Angeles",
              "America/Anchorage",
              "Pacific/Honolulu",
            ].map((zone) => (
              <option key={zone}>{zone}</option>
            ))}
          </select>
        </label>
        <label>
          Service ZIP codes
          <input
            required
            placeholder="Enter your five-digit ZIP codes"
            value={postalCodes}
            onChange={(event) => setPostalCodes(event.target.value)}
          />
        </label>
        <label>
          Visit duration (minutes)
          <input
            type="number"
            min="15"
            max="480"
            step="15"
            value={duration}
            onChange={(event) => setDuration(Number(event.target.value))}
          />
        </label>
        <label>
          Booking notice (minutes)
          <input
            type="number"
            min="0"
            max="10080"
            value={notice}
            onChange={(event) => setNotice(Number(event.target.value))}
          />
        </label>
        <label>
          Change notice (minutes)
          <input
            type="number"
            min="0"
            max="10080"
            value={cutoff}
            onChange={(event) => setCutoff(Number(event.target.value))}
          />
        </label>
      </div>
      <fieldset>
        <legend>Business opening hours</legend>
        {windows.map((window, index) => (
          <div className="hours-row" key={index}>
            <select
              aria-label="Day"
              value={window.weekday}
              onChange={(event) =>
                setWindows(
                  windows.map((row, i) =>
                    i === index
                      ? { ...row, weekday: Number(event.target.value) }
                      : row,
                  ),
                )
              }
            >
              {[
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
              ].map((day, i) => (
                <option value={i} key={day}>
                  {day}
                </option>
              ))}
            </select>
            <input
              aria-label="Opening time"
              type="time"
              required
              value={window.start.slice(0, 5)}
              onChange={(event) =>
                setWindows(
                  windows.map((row, i) =>
                    i === index ? { ...row, start: event.target.value } : row,
                  ),
                )
              }
            />
            <input
              aria-label="Closing time"
              type="time"
              required
              value={window.end.slice(0, 5)}
              onChange={(event) =>
                setWindows(
                  windows.map((row, i) =>
                    i === index ? { ...row, end: event.target.value } : row,
                  ),
                )
              }
            />
            <button
              type="button"
              onClick={() => setWindows(windows.filter((_, i) => i !== index))}
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() =>
            setWindows([
              ...windows,
              { weekday: windows.length % 7, start: "08:00", end: "17:00" },
            ])
          }
        >
          Add opening hours
        </button>
      </fieldset>
      <fieldset>
        <legend>Technicians & service teams</legend>
        {teams.map((team, index) => (
          <div className="team-row" key={team.key}>
            <label>
              Team name
              <input
                required
                value={team.name}
                onChange={(event) =>
                  setTeams(
                    teams.map((row, i) =>
                      i === index ? { ...row, name: event.target.value } : row,
                    ),
                  )
                }
              />
            </label>
            <label>
              Days unavailable
              <input
                placeholder="YYYY-MM-DD, YYYY-MM-DD"
                value={team.unavailable_dates.join(", ")}
                onChange={(event) =>
                  setTeams(
                    teams.map((row, i) =>
                      i === index
                        ? {
                            ...row,
                            unavailable_dates: event.target.value
                              .split(/[, ]+/)
                              .filter(Boolean),
                          }
                        : row,
                    ),
                  )
                }
              />
            </label>
            <p className="section-help">
              {team.windows
                .map(
                  (window) =>
                    ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][
                      window.weekday
                    ] +
                    " " +
                    window.start.slice(0, 5) +
                    "–" +
                    window.end.slice(0, 5),
                )
                .join(" · ")}
            </p>
            <button
              type="button"
              onClick={() =>
                setTeams(
                  teams.map((row, i) =>
                    i === index
                      ? {
                          ...row,
                          windows: windows.map((window) => ({ ...window })),
                        }
                      : row,
                  ),
                )
              }
            >
              Use business hours for this team
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() =>
            setTeams([
              ...teams,
              {
                key: crypto.randomUUID().slice(0, 8),
                name: "",
                windows: windows.map((window) => ({ ...window })),
                unavailable_dates: [],
              },
            ])
          }
        >
          Add a team
        </button>
      </fieldset>
      {formError && (
        <p role="alert" className="ops-error">
          {formError}
        </p>
      )}
      <button className="primary-link" disabled={busy} type="submit">
        {busy ? "Saving…" : "Save scheduling rules"}
      </button>
    </form>
  );
}
