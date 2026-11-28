"use client";

import { providerFetch } from "@/lib/provider-fetch";

import { useEffect, useState } from "react";
import { LoadingSpinner } from "@/components/loading-spinner";
import { DashboardTable } from "@/features/operations/dashboard-table";
import { parseGhlDemo } from "./demo-contracts";
import type { GhlDemoView } from "./demo-contracts";
import styles from "./demo.module.css";

export function GhlDemo({ apiBaseUrl }: { apiBaseUrl: string }) {
  const [view, setView] = useState<GhlDemoView | null>(null);
  const [busy, setBusy] = useState(true);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const timeout = window.setTimeout(() => controller.abort(), 20_000);
    providerFetch(`${apiBaseUrl}/api/v1/public/ghl-demo`, {
      method: "GET",
      cache: "no-store",
      credentials: "omit",
      redirect: "error",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (response.status !== 200 && response.status !== 503)
          throw new Error("Unavailable");
        const data: unknown = await response.json();
        const result = parseGhlDemo(data);
        if ((response.status === 503) !== (result.state === "unavailable"))
          throw new Error("Invalid demo status");
        if (active) setView(result);
      })
      .catch(() => {
        if (active)
          setView((previous) => ({
            state: "unavailable",
            snapshot: previous?.snapshot ?? null,
          }));
      })
      .finally(() => {
        window.clearTimeout(timeout);
        if (active) setBusy(false);
      });
    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [apiBaseUrl, refresh]);

  const snapshot = view?.snapshot;
  const metrics = snapshot
    ? [
        { label: "Loaded opportunities", value: snapshot.counts.loaded },
        { label: "Open", value: snapshot.counts.open },
        { label: "Won", value: snapshot.counts.won },
        {
          label: "Lost or abandoned",
          value: snapshot.counts.lost + snapshot.counts.abandoned,
        },
      ]
    : [];

  return (
    <section className="ops-card" aria-busy={busy}>
      <div className={styles.heading}>
        <div>
          <span className="sample-badge">GoHighLevel · read-only demo</span>
          <h2>See the pipeline in GoHighLevel</h2>
          <p className="section-help">
            A live view of a fictional demo business. Explore its pipeline stages
            and opportunity counts; this view does not change any records.
          </p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            setBusy(true);
            setRefresh((value) => value + 1);
          }}
        >
          {busy ? (
            <LoadingSpinner label="Loading GoHighLevel…" />
          ) : (
            "Refresh GoHighLevel"
          )}
        </button>
      </div>
      <div aria-live="polite">
        {view?.state === "disabled" && (
          <p className="empty-state">
            The live GoHighLevel demo is not connected yet.
          </p>
        )}
        {view?.state === "unavailable" && (
          <p role="status" className="ops-error">
            GoHighLevel could not be refreshed. Please try again later.
            {snapshot ? " The last successful snapshot is shown below." : ""}
          </p>
        )}
      </div>
      {snapshot && (
        <>
          <p className="section-help">
            {view?.state === "live"
              ? "Last successful GHL read: "
              : "Previous successful GHL read: "}
            <time dateTime={snapshot.sampled_at}>
              {new Intl.DateTimeFormat("en-US", {
                dateStyle: "medium",
                timeStyle: "short",
              }).format(new Date(snapshot.sampled_at))}
            </time>
            . Refreshes are shared for up to one minute.
          </p>
          <dl className={styles.metrics}>
            {metrics.map((metric) => (
              <div key={metric.label}>
                <dt>{metric.label}</dt>
                <dd>{metric.value}</dd>
              </div>
            ))}
          </dl>
          <p className="section-help">
            Counts cover up to {snapshot.sample_limit} latest opportunities.
            {snapshot.has_more ? " More records may exist in GoHighLevel." : ""}
          </p>
          {snapshot.pipelines.length > 0 ? (
            <DashboardTable
              caption="GoHighLevel pipeline counts for the loaded opportunity sample"
              headings={["Pipeline", "Stage", "Loaded opportunities"]}
            >
              {snapshot.pipelines.flatMap((pipeline, pipelineIndex) =>
                pipeline.stages.length > 0
                  ? pipeline.stages.map((stage, stageIndex) => (
                      <tr key={`${pipelineIndex}-${stageIndex}`}>
                        <td>{pipeline.name}</td>
                        <th scope="row">{stage.name}</th>
                        <td>{stage.count}</td>
                      </tr>
                    ))
                  : [
                      <tr key={`${pipelineIndex}-empty`}>
                        <td>{pipeline.name}</td>
                        <td>No stages yet</td>
                        <td>0</td>
                      </tr>,
                    ],
              )}
            </DashboardTable>
          ) : (
            <p className="empty-state">
              No pipelines are configured in the demo business yet.
            </p>
          )}
          {snapshot.counts.loaded === 0 && snapshot.pipelines.length > 0 && (
            <p className="empty-state">
              No opportunities are saved in the demo business yet.
            </p>
          )}
        </>
      )}
    </section>
  );
}
