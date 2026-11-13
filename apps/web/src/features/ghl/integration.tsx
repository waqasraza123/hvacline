"use client";

import { useEffect, useState } from "react";
import { requestApi, OperationsApiError } from "@/features/operations/api";
import { StatusBadge } from "@/features/operations/dashboard-table";
import {
  deliveryMessage,
  emptyFields,
  emptyStages,
  fieldLabels,
  stageLabels,
} from "./contracts";
import type {
  Delivery,
  DeliveryPage,
  Discovery,
  FieldKey,
  FieldMapping,
  IntegrationStatus,
  StageKey,
  StageMapping,
} from "./contracts";
import styles from "./integration.module.css";

const prefix = "integrations/ghl";
const pageSize = 25;

function when(value: string | null) {
  return value ? new Date(value).toLocaleString() : "—";
}

export function GhlIntegration({
  apiBaseUrl,
  token,
}: {
  apiBaseUrl: string;
  token: string;
}) {
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [page, setPage] = useState<DeliveryPage | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [privateToken, setPrivateToken] = useState("");
  const [location, setLocation] = useState("");
  const [discovery, setDiscovery] = useState<Discovery | null>(null);
  const [pipeline, setPipeline] = useState("");
  const [stages, setStages] = useState<StageMapping>(emptyStages);
  const [fields, setFields] = useState<FieldMapping>(emptyFields);
  const [confirmed, setConfirmed] = useState(false);

  const api = <T,>(path = "", method = "GET", body?: unknown) =>
    requestApi<T>(apiBaseUrl, token, prefix + path, method, body);

  useEffect(() => {
    let active = true;
    requestApi<IntegrationStatus>(apiBaseUrl, token, prefix)
      .then(async (result) => {
        const deliveries = result.enabled
          ? await requestApi<DeliveryPage>(
              apiBaseUrl,
              token,
              `${prefix}/deliveries?limit=${pageSize}&offset=0`,
            )
          : null;
        if (active) {
          setStatus(result);
          setPage(deliveries);
        }
      })
      .catch((failure: unknown) => {
        if (active)
          setError(
            failure instanceof Error
              ? failure.message
              : "The GHL connection could not be loaded.",
          );
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, token]);

  async function refresh(offset = page?.offset ?? 0) {
    const result = await api<IntegrationStatus>();
    setStatus(result);
    if (result.enabled)
      setPage(
        await api<DeliveryPage>(
          `/deliveries?limit=${pageSize}&offset=${offset}`,
        ),
      );
  }

  async function act(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await task();
    } catch (failure) {
      const details =
        failure instanceof OperationsApiError && failure.code
          ? deliveryMessage(failure.code)
          : "";
      setError(
        [
          failure instanceof Error ? failure.message : "The operation failed.",
          details,
        ]
          .filter(Boolean)
          .join(" "),
      );
    } finally {
      setBusy(false);
    }
  }

  function clearDiscovery() {
    setDiscovery(null);
    setPipeline("");
    setStages(emptyStages);
    setFields(emptyFields);
    setConfirmed(false);
  }

  async function connectionAction(action: "pause" | "resume" | "disconnect") {
    await api("/connection/action", "POST", { action });
    setPrivateToken("");
    clearDiscovery();
    await refresh();
    setMessage(
      action === "disconnect"
        ? "Disconnected. Stored credentials were removed; delivery history is retained."
        : action === "pause"
          ? "Delivery paused. New confirmed requests remain queued."
          : "Connection resumed. Queued changes will be delivered on the next scheduled sync.",
    );
  }

  const connection = status?.connection;
  const connected = connection && connection.status !== "DISCONNECTED";
  const selectedPipeline = discovery?.pipelines.find(
    (item) => item.id === pipeline,
  );

  return (
    <section className="ops-card" aria-labelledby="ghl-heading">
      <div className={styles.heading}>
        <div>
          <h2 id="ghl-heading">GoHighLevel</h2>
          <p className="section-help">
            Send confirmed leads and booking outcomes to your GHL sub-account.
          </p>
        </div>
        <button disabled={busy} onClick={() => void act(() => refresh())}>
          Refresh status
        </button>
      </div>
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
      {!status && !error && <p role="status">Loading the connection…</p>}
      {status && !status.enabled && (
        <p>
          GoHighLevel is not enabled. Ask your workspace administrator to
          configure the integration.
        </p>
      )}
      {status?.enabled && (
        <>
          {connected ? (
            <div>
              <p>
                <StatusBadge status={connection.status} />
              </p>
              <p className={styles.identity}>
                Sub-account: {connection.location_id} · Pipeline:{" "}
                {connection.pipeline_id}
              </p>
              <p className="section-help">
                Last checked: {when(connection.last_checked_at)}
              </p>
              {connection.last_error && (
                <p role="status">{deliveryMessage(connection.last_error)}</p>
              )}
              {connection.blocked_until && (
                <p>
                  Rate-limit retry allowed after{" "}
                  {when(connection.blocked_until)}.
                </p>
              )}
              <div className={styles.actions}>
                <button
                  disabled={busy || connection.status === "PAUSED"}
                  onClick={() => void act(() => connectionAction("pause"))}
                >
                  Pause
                </button>
                <button
                  disabled={busy || connection.status === "ACTIVE"}
                  onClick={() => void act(() => connectionAction("resume"))}
                >
                  Validate and resume
                </button>
                <button
                  disabled={busy}
                  onClick={() => {
                    if (
                      window.confirm(
                        "Disconnect GoHighLevel and remove its stored token? Queued deliveries will stop. Existing GHL records and delivery history will remain.",
                      )
                    )
                      void act(() => connectionAction("disconnect"));
                  }}
                >
                  Disconnect
                </button>
              </div>
              <details>
                <summary>Replace private integration token</summary>
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void act(async () => {
                      await api("/connection/token", "POST", {
                        location_id: connection.location_id,
                        token: privateToken,
                      });
                      setPrivateToken("");
                      await refresh();
                      setMessage(
                        "Token replaced. Validate and resume when ready.",
                      );
                    });
                  }}
                >
                  <label>
                    New token
                    <input
                      type="password"
                      required
                      minLength={16}
                      maxLength={4096}
                      value={privateToken}
                      autoComplete="off"
                      onChange={(event) => setPrivateToken(event.target.value)}
                    />
                  </label>
                  <button disabled={busy}>Replace token and pause</button>
                </form>
              </details>
            </div>
          ) : (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void act(async () => {
                  if (!discovery) {
                    setDiscovery(
                      await api<Discovery>("/discover", "POST", {
                        token: privateToken,
                        location_id: location,
                      }),
                    );
                    return;
                  }
                  await api("/connection", "POST", {
                    token: privateToken,
                    location_id: location,
                    pipeline_id: pipeline,
                    stages,
                    fields,
                    multiple_opportunities_confirmed: confirmed,
                  });
                  setPrivateToken("");
                  clearDiscovery();
                  await refresh(0);
                  setMessage(
                    "Connected. New confirmed requests will sync; existing records are not backfilled.",
                  );
                });
              }}
            >
              <fieldset className={styles.fields} disabled={busy}>
                <legend>Connect a sub-account</legend>
                <div className={styles.grid}>
                  <label>
                    Location ID
                    <input
                      required
                      value={location}
                      maxLength={128}
                      pattern={"[a-zA-Z0-9_\\-]+"}
                      onChange={(event) => {
                        setLocation(event.target.value);
                        clearDiscovery();
                      }}
                    />
                  </label>
                  <label>
                    Private integration token
                    <input
                      type="password"
                      required
                      minLength={16}
                      maxLength={4096}
                      value={privateToken}
                      autoComplete="off"
                      onChange={(event) => {
                        setPrivateToken(event.target.value);
                        clearDiscovery();
                      }}
                    />
                  </label>
                </div>
                <p className="section-help">
                  The token is stored encrypted and never returned to this page.
                </p>
                {discovery && (
                  <>
                    <label>
                      Dedicated HVACLine pipeline
                      <select
                        required
                        value={pipeline}
                        onChange={(event) => {
                          setPipeline(event.target.value);
                          setStages(emptyStages);
                        }}
                      >
                        <option value="">Select a pipeline</option>
                        {discovery.pipelines.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <div className={styles.grid}>
                      {(Object.keys(stageLabels) as StageKey[]).map((key) => (
                        <label key={key}>
                          {stageLabels[key]} stage
                          <select
                            required
                            value={stages[key]}
                            onChange={(event) =>
                              setStages({
                                ...stages,
                                [key]: event.target.value,
                              })
                            }
                          >
                            <option value="">Select a stage</option>
                            {selectedPipeline?.stages.map((stage) => (
                              <option key={stage.id} value={stage.id}>
                                {stage.name}
                              </option>
                            ))}
                          </select>
                        </label>
                      ))}
                      {(Object.keys(fieldLabels) as FieldKey[]).map((key) => (
                        <label key={key}>
                          {fieldLabels[key]} field
                          <select
                            required
                            value={fields[key]}
                            onChange={(event) =>
                              setFields({
                                ...fields,
                                [key]: event.target.value,
                              })
                            }
                          >
                            <option value="">
                              Select an opportunity text field
                            </option>
                            {discovery.fields.map((field) => (
                              <option key={field.id} value={field.id}>
                                {field.name}
                              </option>
                            ))}
                          </select>
                        </label>
                      ))}
                    </div>
                    <label className={styles.check}>
                      <input
                        type="checkbox"
                        required
                        checked={confirmed}
                        onChange={(event) => setConfirmed(event.target.checked)}
                      />
                      <span>
                        I configured a dedicated pipeline and enabled multiple
                        opportunities per contact in this GHL sub-account.
                      </span>
                    </label>
                    <p className="section-help">
                      Use three dedicated text fields. Existing scheduling stays
                      in HVACLine. This connection does not enroll contacts in
                      messaging workflows.
                    </p>
                  </>
                )}
                <button>
                  {busy
                    ? "Working…"
                    : discovery
                      ? "Connect GoHighLevel"
                      : "Validate token and load options"}
                </button>
              </fieldset>
            </form>
          )}
          <h3>Delivery history</h3>
          <p className="section-help">
            Confirmations and CRM delivery are separate. Paused connections
            retain queued changes.
          </p>
          {page?.items.length === 0 && (
            <p>No requests have been queued for GHL.</p>
          )}
          {page?.items.map((delivery) => (
            <DeliveryRow
              key={delivery.id}
              delivery={delivery}
              busy={busy}
              retry={(body) =>
                act(async () => {
                  await api(`/deliveries/${delivery.id}/retry`, "POST", body);
                  await refresh();
                  setMessage("Delivery queued for reconciliation and retry.");
                })
              }
            />
          ))}
          {page && page.total > 0 && (
            <nav aria-label="GHL delivery pages" className={styles.actions}>
              <button
                disabled={busy || page.offset === 0}
                onClick={() =>
                  void act(() => refresh(Math.max(0, page.offset - pageSize)))
                }
              >
                Previous
              </button>
              <span>
                {page.offset + 1}–
                {Math.min(page.offset + page.limit, page.total)} of {page.total}
              </span>
              <button
                disabled={busy || page.offset + page.limit >= page.total}
                onClick={() => void act(() => refresh(page.offset + pageSize))}
              >
                Next
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}

function DeliveryRow({
  delivery,
  busy,
  retry,
}: {
  delivery: Delivery;
  busy: boolean;
  retry: (body: {
    remote_opportunity_id?: string;
    confirm_remote_absent?: boolean;
  }) => Promise<void>;
}) {
  const [remoteId, setRemoteId] = useState("");
  const [absent, setAbsent] = useState(false);
  const unresolved = delivery.contact_unknown || delivery.opportunity_unknown;
  return (
    <article className={styles.delivery}>
      <div className={styles.heading}>
        <strong className={styles.identity}>{delivery.reference}</strong>
        <StatusBadge status={delivery.status} />
      </div>
      <dl>
        <dt>Contact</dt>
        <dd>{delivery.contact_id ?? "Not linked"}</dd>
        <dt>Opportunity</dt>
        <dd>{delivery.opportunity_id ?? "Not linked"}</dd>
        <dt>Last synchronized</dt>
        <dd>{when(delivery.last_synced_at)}</dd>
        <dt>Attempts since last sync</dt>
        <dd>{delivery.attempts}</dd>
        {delivery.last_stage_id && (
          <>
            <dt>Last managed stage ID</dt>
            <dd>{delivery.last_stage_id}</dd>
          </>
        )}
        {delivery.pending_stage_id && (
          <>
            <dt>Pending stage ID</dt>
            <dd>{delivery.pending_stage_id}</dd>
          </>
        )}
        {delivery.status === "RETRYING" && (
          <>
            <dt>Next attempt</dt>
            <dd>{when(delivery.next_attempt_at)}</dd>
          </>
        )}
      </dl>
      {delivery.last_error && <p>{deliveryMessage(delivery.last_error)}</p>}
      {delivery.connection_status !== "ACTIVE" && (
        <p className="section-help">
          This delivery belongs to a {delivery.connection_status.toLowerCase()}{" "}
          connection.
        </p>
      )}
      {delivery.status !== "SYNCED" &&
        delivery.connection_status === "ACTIVE" && (
          <details>
            <summary>Review and retry</summary>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void retry({
                  ...(remoteId ? { remote_opportunity_id: remoteId } : {}),
                  confirm_remote_absent: absent,
                });
              }}
            >
              {delivery.opportunity_unknown && !delivery.opportunity_id && (
                <label>
                  Matching GHL opportunity ID (optional)
                  <input
                    value={remoteId}
                    pattern={"[a-zA-Z0-9_\\-]+"}
                    maxLength={128}
                    disabled={busy || absent}
                    onChange={(event) => setRemoteId(event.target.value)}
                  />
                </label>
              )}
              {unresolved && !delivery.opportunity_id && (
                <label className={styles.check}>
                  <input
                    type="checkbox"
                    checked={absent}
                    disabled={busy || Boolean(remoteId)}
                    onChange={(event) => setAbsent(event.target.checked)}
                  />
                  <span>
                    I checked this sub-account and confirmed that the unresolved
                    record does not exist. Allow a new creation only if
                    reconciliation finds no match.
                  </span>
                </label>
              )}
              <button disabled={busy}>Reconcile and retry</button>
            </form>
          </details>
        )}
    </article>
  );
}
