export const stageLabels = {
  new: "New request",
  booked: "Booked",
  cancelled: "Cancelled",
  attention: "Needs attention",
} as const;

export const fieldLabels = {
  reference: "HVACLine request reference",
  summary: "Confirmed request summary",
  booking: "Booking details",
} as const;

export type StageKey = keyof typeof stageLabels;
export type FieldKey = keyof typeof fieldLabels;
export type StageMapping = Record<StageKey, string>;
export type FieldMapping = Record<FieldKey, string>;

export type Discovery = {
  pipelines: {
    id: string;
    name: string;
    stages: { id: string; name: string }[];
  }[];
  fields: { id: string; name: string; dataType: string }[];
};

export type Connection = {
  id: string;
  location_id: string;
  pipeline_id: string;
  stages: StageMapping;
  fields: FieldMapping;
  status: "ACTIVE" | "PAUSED" | "ERROR" | "DISCONNECTED";
  activated_at: string;
  last_checked_at: string | null;
  last_error: string | null;
  blocked_until: string | null;
};

export type IntegrationStatus = {
  enabled: boolean;
  connection: Connection | null;
};

export type Delivery = {
  id: string;
  connection_id: string;
  connection_status: Connection["status"];
  location_id: string;
  lead_id: string;
  reference: string;
  status: "PENDING" | "PROCESSING" | "SYNCED" | "RETRYING" | "NEEDS_REVIEW";
  attempts: number;
  desired_version: number;
  delivered_version: number;
  contact_id: string | null;
  opportunity_id: string | null;
  contact_unknown: boolean;
  opportunity_unknown: boolean;
  last_stage_id: string | null;
  pending_stage_id: string | null;
  created_at: string;
  next_attempt_at: string;
  last_synced_at: string | null;
  last_error: string | null;
};

export type DeliveryPage = {
  items: Delivery[];
  total: number;
  offset: number;
  limit: number;
};

export const emptyStages: StageMapping = {
  new: "",
  booked: "",
  cancelled: "",
  attention: "",
};
export const emptyFields: FieldMapping = {
  reference: "",
  summary: "",
  booking: "",
};

export function deliveryMessage(code: string | null): string {
  if (!code) return "";
  const messages: Record<string, string> = {
    GHL_AUTH_REQUIRED:
      "Replace the token or restore its permissions, then resume the connection.",
    GHL_CONTACT_MATCH_AMBIGUOUS:
      "Multiple contacts match. Resolve duplicates in GHL, then retry.",
    GHL_CONTACT_MATCH_CONFLICT:
      "The email and phone identify different contacts. Resolve the conflict in GHL, then retry.",
    GHL_CONTACT_IDENTIFIER_REQUIRED:
      "This confirmed lead needs an email address or phone number before it can sync.",
    GHL_PHONE_FORMAT_INVALID:
      "The saved phone number cannot be normalized. Correct it before retrying.",
    GHL_CONTACT_MAPPING_CHANGED:
      "The original contact no longer matches the confirmed identity. Review GHL contact changes.",
    GHL_CONTACT_CREATION_UNKNOWN:
      "Contact creation may have succeeded. Review GHL before allowing another creation.",
    GHL_OPPORTUNITY_CREATION_UNKNOWN:
      "Opportunity creation may have succeeded. Link the matching record or confirm its absence after reviewing GHL.",
    GHL_OPPORTUNITY_MANAGED_EXTERNALLY:
      "This opportunity is closed or outside managed stages. Restore it in GHL before retrying if HVACLine should manage it.",
    GHL_OPPORTUNITY_STAGE_CHANGED_EXTERNALLY:
      "The opportunity stage changed in GHL. Restore the last synchronized stage before retrying.",
    GHL_OPPORTUNITY_OWNERSHIP_INVALID:
      "The opportunity no longer matches this request. Review its location, pipeline, contact and reference.",
    GHL_OPPORTUNITY_MATCH_AMBIGUOUS:
      "More than one opportunity has this request reference. Resolve the duplicate references in GHL.",
    GHL_STAGE_MAPPING_INVALID:
      "A mapped stage is missing. Restore the configured stages or disconnect and configure a new connection.",
    GHL_FIELD_MAPPING_INVALID:
      "A mapped text field is missing. Restore it or configure a new connection.",
    GHL_FIELD_WRITE_UNCONFIRMED:
      "GHL did not retain the mapped field values. Check field configuration before resuming.",
    GHL_RATE_LIMITED:
      "GHL requested a delay. Delivery resumes after the displayed retry time.",
    GHL_RETRY_LIMIT:
      "Automatic attempts stopped. Resolve the cause, then retry deliberately.",
    GHL_CREDENTIALS_UNAVAILABLE:
      "The stored token could not be decrypted. Check the server encryption key or replace the token.",
    GHL_CONNECTION_INVALID:
      "The saved connection configuration is invalid. Disconnect and configure a new connection.",
    GHL_LOCAL_LEAD_UNAVAILABLE:
      "The local lead is unavailable or archived. It will not be exported.",
    GHL_REQUEST_REJECTED:
      "GHL rejected the request. Check token scopes, field mappings and whether multiple opportunities per contact are enabled.",
  };
  return (
    messages[code] ??
    "Delivery needs attention. Review the connection and retry when the cause is resolved."
  );
}
