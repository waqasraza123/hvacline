export type PhoneAccessPreview = {
  id: string;
  business_name: string;
  caller_last_four: string | null;
  called_last_four: string | null;
  created_at: string;
  expires_at: string;
  share_memory: boolean;
  memory_available: boolean;
};

export type PhoneAccess = PhoneAccessPreview & {
  status: "ACTIVE" | "EXPIRED" | "REVOKED";
};

const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
const object = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
const timestamp = (value: unknown): value is string =>
  typeof value === "string" && Number.isFinite(Date.parse(value));
const lastFour = (value: unknown): value is string | null =>
  value === null || typeof value === "string" && /^\d{4}$/.test(value);

export function normalizeCallCode(value: string): string {
  const compact = value.toUpperCase().replace(/[\s-]/g, "");
  if (!/^CALL[A-F0-9]{12}$/.test(compact))
    throw new Error("Enter the CALL code from the phone receptionist.");
  return `CALL-${compact.slice(4, 8)}-${compact.slice(8, 12)}-${compact.slice(12)}`;
}

export function parsePhoneAccessPreview(value: unknown): PhoneAccessPreview {
  if (!object(value) || typeof value.id !== "string" || !uuid.test(value.id) ||
      typeof value.business_name !== "string" || !value.business_name.trim() ||
      !lastFour(value.caller_last_four) || !lastFour(value.called_last_four) ||
      !timestamp(value.created_at) || !timestamp(value.expires_at) ||
      Date.parse(value.expires_at) <= Date.parse(value.created_at) ||
      typeof value.share_memory !== "boolean" || typeof value.memory_available !== "boolean")
    throw new Error("The call details could not be confirmed. Refresh before approving.");
  return {
    id: value.id, business_name: value.business_name,
    caller_last_four: value.caller_last_four, called_last_four: value.called_last_four,
    created_at: value.created_at, expires_at: value.expires_at,
    share_memory: value.share_memory, memory_available: value.memory_available,
  };
}

export function parsePhoneAccessList(value: unknown): PhoneAccess[] {
  if (!object(value) || !Array.isArray(value.items) || value.items.length > 20)
    throw new Error("Call approvals could not be loaded. Please refresh.");
  const items = value.items.map((item: unknown): PhoneAccess => {
    const preview = parsePhoneAccessPreview(item);
    if (!object(item) || !["ACTIVE", "EXPIRED", "REVOKED"].includes(String(item.status)))
      throw new Error("A call approval status could not be confirmed.");
    return { ...preview, status: item.status as PhoneAccess["status"] };
  });
  if (new Set(items.map((item) => item.id)).size !== items.length)
    throw new Error("Call approvals could not be confirmed. Please refresh.");
  return items;
}

export function requireCallApproval(value: unknown, expectedId: string): void {
  if (!object(value) || value.approved !== true || value.id !== expectedId ||
      !timestamp(value.expires_at) || Date.parse(value.expires_at) <= Date.now())
    throw new Error("Call approval could not be confirmed. Refresh saved approvals before retrying.");
}
