"use client";

import { useEffect, useState } from "react";
import { OperationsApiError, requestApi } from "@/features/operations/api";
import { StatusBadge } from "@/features/operations/dashboard-table";
import { deliveryMessage } from "./contracts";
import styles from "./integration.module.css";

type VoiceConfiguration = {
  calendars: { team_key: string; calendar_id: string }[];
  contact_notes: boolean;
  note_user_id: string | null;
};
type VoiceSettings = {
  configuration: VoiceConfiguration;
  version: number;
  teams: { key: string; name: string }[];
};
type Booking = {
  appointment_id: string;
  calendar_id: string;
  status:
    | "RESERVED"
    | "CONTACT_PENDING"
    | "CREATING"
    | "UNKNOWN"
    | "CONFIRMED"
    | "NEEDS_REVIEW"
    | "RELEASED";
  contact_id: string | null;
  event_id: string | null;
  last_error: string | null;
  starts_at: string;
  ends_at: string;
  team_key: string;
};
type BookingPage = {
  items: Booking[];
  total: number;
  offset: number;
  limit: number;
};
const prefix = "integrations/ghl";
const unresolved = new Set<Booking["status"]>([
  "CONTACT_PENDING",
  "CREATING",
  "UNKNOWN",
  "NEEDS_REVIEW",
]);

export function GhlVoiceSettings({
  apiBaseUrl,
  token,
  active,
}: {
  apiBaseUrl: string;
  token: string;
  active: boolean;
}) {
  const [settings, setSettings] = useState<VoiceSettings | null>(null);
  const [page, setPage] = useState<BookingPage | null>(null);
  const [routes, setRoutes] = useState<Record<string, string>>({});
  const [contactNotes, setContactNotes] = useState(false);
  const [noteUser, setNoteUser] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const api = <T,>(path: string, method = "GET", body?: unknown) =>
    requestApi<T>(apiBaseUrl, token, prefix + path, method, body);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      requestApi<VoiceSettings>(apiBaseUrl, token, prefix + "/voice"),
      requestApi<BookingPage>(
        apiBaseUrl,
        token,
        prefix + "/bookings?limit=25&offset=0",
      ),
    ])
      .then(([loaded, bookings]) => {
        if (cancelled) return;
        setSettings(loaded);
        setRoutes(
          Object.fromEntries(
            loaded.configuration.calendars.map((route) => [
              route.team_key,
              route.calendar_id,
            ]),
          ),
        );
        setContactNotes(loaded.configuration.contact_notes);
        setNoteUser(loaded.configuration.note_user_id ?? "");
        setPage(bookings);
      })
      .catch((failure: unknown) => {
        if (!cancelled)
          setError(
            failure instanceof Error
              ? failure.message
              : "Voice settings could not be loaded.",
          );
      });
    return () => {
      cancelled = true;
    };
  }, [apiBaseUrl, token]);

  async function act(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await task();
    } catch (failure) {
      setError(
        failure instanceof OperationsApiError && failure.code
          ? deliveryMessage(failure.code)
          : failure instanceof Error
            ? failure.message
            : "The operation failed.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function refresh(offset = page?.offset ?? 0) {
    setPage(await api<BookingPage>(`/bookings?limit=25&offset=${offset}`));
  }

  return (
    <section className={styles.delivery} aria-labelledby="ghl-voice-heading">
      <h3 id="ghl-voice-heading">Voice booking and contact summaries</h3>
      <p className="section-help">
        Route routine appointments to a GHL calendar after caller confirmation.
        Teams without a GHL route keep their existing scheduling.
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
      {!settings && !error && <p role="status">Loading voice settings…</p>}
      {settings && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void act(async () => {
              const result = await api<VoiceSettings>("/voice", "PUT", {
                expected_version: settings.version,
                calendars: settings.teams.flatMap((team) =>
                  routes[team.key]?.trim()
                    ? [
                        {
                          team_key: team.key,
                          calendar_id: routes[team.key].trim(),
                        },
                      ]
                    : [],
                ),
                contact_notes: contactNotes,
                note_user_id: contactNotes ? noteUser.trim() : null,
              });
              setSettings(result);
              setMessage(
                "Voice settings saved. New reservations use the selected calendars; contact summaries apply to subsequent CRM deliveries.",
              );
            });
          }}
        >
          <fieldset className={styles.fields} disabled={busy || !active}>
            <legend>Calendar routing</legend>
            {!settings.teams.length && (
              <p>
                Configure teams in Scheduling before adding calendar routes.
              </p>
            )}
            <div className={styles.grid}>
              {settings.teams.map((team) => (
                <label key={team.key}>
                  {team.name} — GHL calendar ID
                  <input
                    value={routes[team.key] ?? ""}
                    maxLength={128}
                    pattern={"[a-zA-Z0-9_\\-]+"}
                    onChange={(event) =>
                      setRoutes({ ...routes, [team.key]: event.target.value })
                    }
                  />
                  <small>Leave blank to use existing scheduling.</small>
                </label>
              ))}
            </div>
            <p className="section-help">
              Use an active fixed-duration calendar matching the appointment
              length in Scheduling. A team can use Google Calendar or GHL. GHL
              rescheduling and cancellation currently require staff assistance.
            </p>
            <label className={styles.check}>
              <input
                type="checkbox"
                checked={contactNotes}
                onChange={(event) => setContactNotes(event.target.checked)}
              />
              <span>Add the confirmed request summary to the GHL contact</span>
            </label>
            {contactNotes && (
              <label>
                GHL note author user ID
                <input
                  required
                  value={noteUser}
                  maxLength={128}
                  pattern={"[a-zA-Z0-9_\\-]+"}
                  onChange={(event) => setNoteUser(event.target.value)}
                />
              </label>
            )}
            <p className="section-help">
              Each confirmed request gets its own contact note with the name,
              callback number and summary. Existing contact details and notes
              are preserved.
            </p>
            <button>Save voice settings</button>
          </fieldset>
        </form>
      )}
      {!active && (
        <p>
          Resume the GHL connection to change these settings or recover a
          booking.
        </p>
      )}
      <div className={styles.heading}>
        <h4>GHL booking history</h4>
        <button disabled={busy} onClick={() => void act(() => refresh())}>
          Refresh bookings
        </button>
      </div>
      {page?.items.length === 0 && <p>No GHL booking attempts yet.</p>}
      {page?.items.map((booking) => (
        <BookingRow
          key={booking.appointment_id}
          booking={booking}
          disabled={busy || !active}
          recover={(body) =>
            act(async () => {
              await api(
                `/bookings/${booking.appointment_id}/recover`,
                "POST",
                body,
              );
              await refresh();
              setMessage(
                body.remote_event_id
                  ? "The GHL appointment was verified and its local confirmation recovered."
                  : "The local reservation was released after your absence review.",
              );
            })
          }
        />
      ))}
      {page && page.total > 0 && (
        <nav className={styles.actions} aria-label="GHL booking pages">
          <button
            disabled={busy || page.offset === 0}
            onClick={() =>
              void act(() => refresh(Math.max(0, page.offset - 25)))
            }
          >
            Previous
          </button>
          <span>
            {page.offset + 1}–{Math.min(page.offset + page.limit, page.total)}{" "}
            of {page.total}
          </span>
          <button
            disabled={busy || page.offset + page.limit >= page.total}
            onClick={() => void act(() => refresh(page.offset + 25))}
          >
            Next
          </button>
        </nav>
      )}
    </section>
  );
}

function BookingRow({
  booking,
  disabled,
  recover,
}: {
  booking: Booking;
  disabled: boolean;
  recover: (body: {
    remote_event_id?: string;
    confirm_remote_absent?: boolean;
  }) => Promise<void>;
}) {
  const [enteredEventId, setEventId] = useState("");
  const eventId = booking.event_id ?? enteredEventId;
  const [absent, setAbsent] = useState(false);
  return (
    <article className={styles.delivery}>
      <div className={styles.heading}>
        <strong className={styles.identity}>{booking.appointment_id}</strong>
        <StatusBadge status={booking.status} />
      </div>
      <p>
        {new Date(booking.starts_at).toLocaleString(undefined, {
          timeZoneName: "short",
        })}{" "}
        · {booking.team_key}
      </p>
      <dl>
        <dt>Calendar</dt>
        <dd>{booking.calendar_id}</dd>
        <dt>GHL appointment</dt>
        <dd>{booking.event_id ?? "Not linked"}</dd>
      </dl>
      {booking.last_error && <p>{deliveryMessage(booking.last_error)}</p>}
      {unresolved.has(booking.status) && (
        <details>
          <summary>Review unresolved booking</summary>
          <p className="section-help">
            Check the original calendar and contact before taking action.
            Linking requires the exact original appointment and confirmed
            status. Keep this reservation reference when a response is lost.
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void recover(
                eventId
                  ? { remote_event_id: eventId }
                  : { confirm_remote_absent: absent },
              );
            }}
          >
            <label>
              Existing GHL appointment ID
              <input
                value={eventId}
                maxLength={128}
                pattern={"[a-zA-Z0-9_\\-]+"}
                disabled={disabled || absent || Boolean(booking.event_id)}
                onChange={(event) => setEventId(event.target.value)}
              />
            </label>
            {!booking.event_id && (
              <label className={styles.check}>
                <input
                  type="checkbox"
                  checked={absent}
                  disabled={disabled || Boolean(eventId)}
                  onChange={(event) => setAbsent(event.target.checked)}
                />
                <span>
                  I checked GHL and confirmed no appointment was created.
                  Release this local reservation.
                </span>
              </label>
            )}
            <button disabled={disabled || (!eventId && !absent)}>
              {eventId
                ? "Verify and recover confirmation"
                : "Release reviewed reservation"}
            </button>
          </form>
        </details>
      )}
    </article>
  );
}
