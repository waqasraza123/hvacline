export type Fact = { key: string; value: string };
export type SavedFact = Fact & {
  source_kind: string;
  updated_at: string;
  expires_at: string;
};
export type Source = {
  intake_id: string;
  summary: string;
  confirmed_at?: string;
  suggestions: Fact[];
};
export type MemoryView = {
  available: boolean;
  enabled: boolean;
  revision: number;
  retention_days: number;
  options: Record<string, Record<string, string>>;
  facts: SavedFact[];
  sources: Source[];
  whatsapp_linked: boolean;
};

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function fact(value: unknown): value is Fact {
  return (
    record(value) &&
    typeof value.key === "string" &&
    typeof value.value === "string"
  );
}

export function parseMemory(value: unknown): MemoryView {
  if (
    !record(value) ||
    typeof value.available !== "boolean" ||
    typeof value.enabled !== "boolean" ||
    typeof value.revision !== "number" ||
    !Number.isInteger(value.revision) ||
    value.revision < 0 ||
    typeof value.retention_days !== "number" ||
    !record(value.options) ||
    typeof value.whatsapp_linked !== "boolean" ||
    !Array.isArray(value.facts) ||
    !Array.isArray(value.sources)
  )
    throw new Error("Memory could not be loaded.");
  const options: MemoryView["options"] = {};
  for (const [key, choices] of Object.entries(value.options)) {
    if (!record(choices)) throw new Error("Invalid memory options.");
    options[key] = {};
    for (const [choice, label] of Object.entries(choices)) {
      if (typeof label !== "string") throw new Error("Invalid memory label.");
      options[key][choice] = label;
    }
  }
  const facts: SavedFact[] = value.facts.map((entry: unknown) => {
    if (
      !record(entry) ||
      typeof entry.key !== "string" ||
      typeof entry.value !== "string" ||
      typeof entry.source_kind !== "string" ||
      typeof entry.updated_at !== "string" ||
      typeof entry.expires_at !== "string"
    ) {
      throw new Error("Invalid saved memory.");
    }
    return {
      key: entry.key,
      value: entry.value,
      source_kind: entry.source_kind,
      updated_at: entry.updated_at,
      expires_at: entry.expires_at,
    };
  });
  const sources: Source[] = value.sources.map((entry: unknown) => {
    if (
      !record(entry) ||
      typeof entry.intake_id !== "string" ||
      typeof entry.summary !== "string" ||
      !Array.isArray(entry.suggestions) ||
      !entry.suggestions.every(fact)
    )
      throw new Error("Invalid memory source.");
    return {
      intake_id: entry.intake_id,
      summary: entry.summary,
      confirmed_at:
        typeof entry.confirmed_at === "string" ? entry.confirmed_at : undefined,
      suggestions: entry.suggestions,
    };
  });
  return {
    available: value.available,
    enabled: value.enabled,
    revision: value.revision,
    retention_days: value.retention_days,
    options,
    facts,
    sources,
    whatsapp_linked: value.whatsapp_linked,
  };
}
