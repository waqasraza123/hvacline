import { requestApi } from "@/features/operations/api";

export type RecoveryCase = {
  id: string; row_version: number; service_request_id: string; lead_id: string | null;
  inbound_call_id: string | null; conversation_session_id: string | null;
  customer: string; summary: string; source_type: string; source_reference: string; status: string;
  eligible_at: string; last_activity_at: string; recovered_appointment_id: string | null;
  paused: boolean; assigned_to: string | null; reason: string | null; next_attempt: string | null;
  booking: { id: string; starts_at: string; ends_at: string; team_key: string; status: string } | null;
  attempts: { id: string; channel: string; attempt_number: number; status: string; scheduled_at: string; started_at: string | null; completed_at: string | null; failure_code: string | null }[];
  permissions: { channel: string; scope: string; source: string; evidence_reference: string; granted_at: string | null; revoked_at: string | null; row_version: number }[];
};
export type CasePage = { items: RecoveryCase[]; total: number; limit: number; offset: number };
export type RecoverySummary = { total: number; recoverable: number; scheduled: number; attempted: number; recovered: number; conversion_rate: number; recent: { id: string; status: string; at: string }[] };
export type RecoveryPolicy = { expected_row_version: number; enabled: boolean; channels: ("SMS" | "VOICE")[]; timezone: string; contact_start: string; contact_end: string; max_attempts: number; interval_hours: number; expiry_days: number; abandoned_delay_minutes: number; booking_delay_minutes: number };
export type RecoverySettings = { policy: RecoveryPolicy; runtime_enabled: boolean; identity_gate: string; providers: Record<"SMS" | "VOICE", { available: boolean; reason: string }> };
export type AiConnection = { provider: "OPENAI" | "OPENAI_COMPATIBLE" | null; model: string; endpoint: string; status: string; row_version: number; has_credential: boolean; last_tested_at: string | null; last_error: string | null; capabilities: string[]; live_recovery_voice_supported: boolean; voice_status: string; encryption_configured: boolean };
export type RecoveryApi = <T>(path: string, method?: string, body?: unknown, key?: string) => Promise<T>;
export function recoveryApi(baseUrl: string, token: string): RecoveryApi {
  return <T,>(path: string, method = "GET", body?: unknown, key?: string) => requestApi<T>(baseUrl, token, `lead-recovery/${path}`, method, body, key);
}
