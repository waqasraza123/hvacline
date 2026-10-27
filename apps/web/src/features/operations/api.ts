export type ServiceRequest = {
  id: string;
  status: string;
  confirmed_at: string;
  customer: {
    full_name: string;
    phone: string;
    address: {
      line1: string;
      city: string;
      state_code: string;
      postal_code: string;
    };
  };
  service: {
    kind: string;
    equipment_issue: string;
    preferred_window: string;
    hazardous_condition: boolean;
  };
};
export type Appointment = {
  id: string;
  service_request_id: string;
  team_key: string;
  starts_at: string;
  ends_at: string;
  status: string;
  hold_expires_at: string;
};
export type Operations = {
  service_requests: ServiceRequest[];
  appointments: Appointment[];
  calls: {
    id: string;
    status: string;
    received_at: string;
    caller_number: string | null;
  }[];
  handoffs: {
    id: string;
    kind: string;
    status: string;
    reason: string;
    lead_id: string;
  }[];
};
export type Window = { weekday: number; start: string; end: string };
export type Schedule = {
  expected_version: number;
  enabled: boolean;
  timezone: string;
  postal_codes: string[];
  windows: Window[];
  teams: {
    key: string;
    name: string;
    windows: Window[];
    unavailable_dates: string[];
  }[];
  duration_minutes: number;
  notice_minutes: number;
  horizon_days: number;
  cancellation_notice_minutes: number;
};
export type ScheduleResponse = {
  version: number;
  configuration: Schedule | null;
};
export type Slot = { team_key: string; starts_at: string; ends_at: string };
export type Availability = {
  configured: boolean;
  in_service_area: boolean;
  timezone: string | null;
  slots: Slot[];
  message: string | null;
};

export class OperationsApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly code?: string,
  ) {
    super(message);
    this.name = "OperationsApiError";
  }
}

export async function requestApi<T>(
  baseUrl: string,
  token: string,
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${baseUrl}/api/v1/development/${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-Demo-Admin-Token": token,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
    signal: AbortSignal.timeout(15000),
  });
  const data = await response.json();
  if (!response.ok)
    throw new OperationsApiError(
      response.status,
      data?.error?.message ?? "The request could not be completed.",
      data?.error?.code,
    );
  return data as T;
}
