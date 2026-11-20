import * as SecureStore from "expo-secure-store";
import { randomUUID } from "expo-crypto";
import type { Slot } from "@insurance-operations/customer-core";
import { MobileApi, MobileApiError } from "../lib/api";
import { appointment, date, object, string, UUID } from "../lib/models";

type PendingChange = {
  service_request_id: string;
  team_key: string;
  starts_at: string;
  idempotency_key: string;
  explicit_confirmation: true;
};
const STORAGE_OPTIONS = {
  keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
};

export class RescheduleSession {
  private pending?: PendingChange;
  private busy = false;
  constructor(
    private readonly api: MobileApi,
    private readonly accountId: string,
    private readonly appointmentId: string,
  ) {}
  private get storageKey() {
    return `hvacline.reschedule.${this.accountId}.${this.appointmentId}`;
  }
  get hasPending() {
    return this.pending !== undefined;
  }
  get pendingTime() {
    return this.pending?.starts_at;
  }

  async restore() {
    const raw = await SecureStore.getItemAsync(
      this.storageKey,
      STORAGE_OPTIONS,
    );
    if (!raw) return;
    const stored = object(JSON.parse(raw));
    if (stored.origin !== this.api.origin)
      throw new Error(
        "This saved change belongs to another server. Restore the original app configuration to resolve it.",
      );
    const data = object(stored.request);
    if (
      !UUID.test(string(data.service_request_id)) ||
      !UUID.test(string(data.idempotency_key)) ||
      data.explicit_confirmation !== true ||
      !/^[a-z0-9-]{1,40}$/.test(string(data.team_key))
    )
      throw new Error(
        "A previous appointment change needs staff review. Contact the business before making another change.",
      );
    this.pending = {
      service_request_id: string(data.service_request_id),
      team_key: string(data.team_key),
      starts_at: date(data.starts_at),
      idempotency_key: string(data.idempotency_key),
      explicit_confirmation: true,
    };
  }

  async confirm(requestId: string, slot?: Slot) {
    if (this.busy)
      throw new Error("Wait for the current appointment change to finish.");
    this.busy = true;
    try {
      if (!this.pending) {
        if (!slot)
          throw new Error("Choose an available appointment time first.");
        const value: PendingChange = {
          service_request_id: requestId,
          team_key: slot.team_key,
          starts_at: slot.starts_at,
          idempotency_key: randomUUID(),
          explicit_confirmation: true,
        };
        await SecureStore.setItemAsync(
          this.storageKey,
          JSON.stringify({ origin: this.api.origin, request: value }),
          STORAGE_OPTIONS,
        );
        this.pending = value;
      }
      if (this.pending.service_request_id !== requestId)
        throw new Error(
          "The saved change does not match this service request. Contact the business before continuing.",
        );
      const result = appointment(
        await this.api.request(
          `appointments/${this.appointmentId}/reschedule`,
          "POST",
          this.pending,
        ),
      );
      if (
        result.status !== "CONFIRMED" ||
        result.service_request_id !== this.pending.service_request_id ||
        result.team_key !== this.pending.team_key ||
        Date.parse(result.starts_at) !== Date.parse(this.pending.starts_at)
      )
        throw new Error(
          "The new appointment is not confirmed. Retry this same change before selecting another time.",
        );
      await SecureStore.deleteItemAsync(this.storageKey, STORAGE_OPTIONS);
      this.pending = undefined;
      return result;
    } catch (error) {
      const rejectedWithoutWrite =
        error instanceof MobileApiError &&
        ([400, 404, 410, 422].includes(error.status) ||
          [
            "SLOT_UNAVAILABLE",
            "RESERVATION_EXPIRED",
            "CHANGE_NOTICE_REQUIRED",
            "HUMAN_ATTENTION_REQUIRED",
            "CALENDAR_CONFLICT",
            "CUSTOMER_BOOKING_CHANGE_LIMIT_REACHED",
            "CUSTOMER_APPOINTMENT_LIMIT_REACHED",
          ].includes(error.code ?? ""));
      if (rejectedWithoutWrite && this.pending) {
        await SecureStore.deleteItemAsync(this.storageKey, STORAGE_OPTIONS);
        this.pending = undefined;
      }
      throw error;
    } finally {
      this.busy = false;
    }
  }
}
