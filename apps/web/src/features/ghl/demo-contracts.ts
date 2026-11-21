export type GhlDemoSnapshot = {
  sampled_at: string;
  sample_limit: 100;
  has_more: boolean;
  counts: {
    loaded: number;
    open: number;
    won: number;
    lost: number;
    abandoned: number;
  };
  pipelines: { name: string; stages: { name: string; count: number }[] }[];
};

export type GhlDemoView = {
  state: "live" | "disabled" | "unavailable";
  snapshot: GhlDemoSnapshot | null;
};

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value))
    throw new Error("The GoHighLevel demo response could not be read.");
  return value as Record<string, unknown>;
}

function count(value: unknown): number {
  if (
    typeof value !== "number" ||
    !Number.isInteger(value) ||
    value < 0 ||
    value > 100
  )
    throw new Error("Invalid demo count.");
  return value;
}

function name(value: unknown): string {
  if (typeof value !== "string" || !value.trim() || value.length > 100)
    throw new Error("Invalid demo label.");
  return value;
}

export function parseGhlDemo(value: unknown): GhlDemoView {
  const data = record(value);
  if (
    data.state !== "live" &&
    data.state !== "disabled" &&
    data.state !== "unavailable"
  )
    throw new Error("Invalid demo status.");
  const state = data.state;
  if (data.snapshot === null && state !== "live")
    return { state, snapshot: null };
  if (state === "disabled") throw new Error("Invalid disabled demo response.");
  const snapshot = record(data.snapshot);
  if (
    typeof snapshot.sampled_at !== "string" ||
    !Number.isFinite(Date.parse(snapshot.sampled_at)) ||
    snapshot.sample_limit !== 100 ||
    typeof snapshot.has_more !== "boolean" ||
    !Array.isArray(snapshot.pipelines) ||
    snapshot.pipelines.length > 20
  )
    throw new Error("Invalid demo snapshot.");
  const rawCounts = record(snapshot.counts);
  const counts = {
    loaded: count(rawCounts.loaded),
    open: count(rawCounts.open),
    won: count(rawCounts.won),
    lost: count(rawCounts.lost),
    abandoned: count(rawCounts.abandoned),
  };
  const pipelines = snapshot.pipelines.map((value: unknown) => {
    const pipeline = record(value);
    if (!Array.isArray(pipeline.stages) || pipeline.stages.length > 50)
      throw new Error("Invalid demo stages.");
    return {
      name: name(pipeline.name),
      stages: pipeline.stages.map((value: unknown) => {
        const stage = record(value);
        return { name: name(stage.name), count: count(stage.count) };
      }),
    };
  });
  if (
    counts.open + counts.won + counts.lost + counts.abandoned !== counts.loaded ||
    pipelines.reduce(
      (total, pipeline) =>
        total + pipeline.stages.reduce((sum, stage) => sum + stage.count, 0),
      0,
    ) !== counts.loaded
  )
    throw new Error("The demo counts do not match the displayed stages.");
  return {
    state,
    snapshot: {
      sampled_at: snapshot.sampled_at,
      sample_limit: 100,
      has_more: snapshot.has_more,
      counts,
      pipelines,
    },
  };
}
