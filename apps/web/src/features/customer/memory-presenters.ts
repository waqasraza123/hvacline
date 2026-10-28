const FIELD_LABELS: Record<string, string> = {
  appointment_time: "Preferred time",
  appointment_days: "Preferred days",
  contact_preference: "How to reach you",
  equipment_type: "Equipment type",
  equipment_brand: "Equipment brand",
  equipment_fuel: "Heating fuel",
  arrival_preference: "Before we arrive",
  site_access: "At your home",
};

export function memoryField(key: string): string {
  return FIELD_LABELS[key] ?? key.replaceAll("_", " ");
}

export function memoryDate(value: string): string {
  const date = new Date(value);
  return Number.isFinite(date.getTime())
    ? date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Date unavailable";
}
