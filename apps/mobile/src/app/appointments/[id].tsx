import { useCallback, useRef, useState } from "react";
import { Alert, Text } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import type { Availability, Slot } from "@insurance-operations/customer-core";
import {
  Body,
  Busy,
  Button,
  Card,
  Choice,
  Field,
  Heading,
  Screen,
  useTheme,
} from "../../components/ui";
import { RescheduleSession } from "../../features/reschedule";
import { requiresStaffReview } from "../../features/booking-session";
import {
  availability,
  bookingDetails,
  formatTime,
  UUID,
  type BookingDetails,
} from "../../lib/models";
import { useSession } from "../../lib/session";

export default function AppointmentDetails() {
  const params = useLocalSearchParams<{ id: string }>();
  const id =
    typeof params.id === "string" && UUID.test(params.id)
      ? params.id
      : undefined;
  const { api, user } = useSession(),
    theme = useTheme();
  const accountId = user?.id;
  const [details, setDetails] = useState<BookingDetails>(),
    [slots, setSlots] = useState<Availability>(),
    [selected, setSelected] = useState<Slot>(),
    [day, setDay] = useState("");
  const [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [pending, setPending] = useState(false),
    [staffReview, setStaffReview] = useState(false);
  const change = useRef<RescheduleSession | undefined>(undefined),
    version = useRef(0),
    running = useRef(false);
  const load = useCallback(async () => {
    const current = ++version.current;
    setLoading(true);
    setError("");
    setDetails(undefined);
    setSlots(undefined);
    setSelected(undefined);
    setPending(false);
    setStaffReview(false);
    change.current = undefined;
    try {
      if (!api || !accountId || !id)
        throw new Error("This appointment reference is invalid.");
      const session = new RescheduleSession(api, accountId, id);
      await session.restore();
      const result = bookingDetails(await api.request(`appointments/${id}`));
      if (current === version.current) {
        change.current = session;
        setDetails(result);
        setPending(session.hasPending);
        setSlots(undefined);
        setSelected(undefined);
      }
    } catch (failure) {
      if (current === version.current)
        setError(
          failure instanceof Error
            ? failure.message
            : "The appointment could not be loaded.",
        );
    } finally {
      if (current === version.current) setLoading(false);
    }
  }, [api, accountId, id]);
  useFocusEffect(
    useCallback(() => {
      void load();
      return () => {
        version.current += 1;
      };
    }, [load]),
  );

  async function findTimes() {
    if (!api || !id || running.current || pending) return;
    running.current = true;
    setBusy(true);
    setError("");
    setSlots(undefined);
    setSelected(undefined);
    const current = version.current;
    try {
      if (
        !/^\d{4}-\d{2}-\d{2}$/.test(day) ||
        !Number.isFinite(Date.parse(`${day}T12:00:00Z`)) ||
        new Date(`${day}T12:00:00Z`).toISOString().slice(0, 10) !== day
      )
        throw new Error("Enter an exact calendar date as YYYY-MM-DD.");
      const result = availability(
        await api.request(`appointments/${id}/availability`, "POST", { day }),
      );
      if (current === version.current) setSlots(result);
    } catch (failure) {
      if (current === version.current)
        setError(
          failure instanceof Error
            ? failure.message
            : "Available times could not be loaded.",
        );
    } finally {
      running.current = false;
      setBusy(false);
    }
  }

  async function submit() {
    if (!details || !change.current || running.current) return;
    running.current = true;
    setBusy(true);
    setError("");
    const current = version.current,
      session = change.current;
    try {
      const result = await session.confirm(
        details.appointment.service_request_id,
        selected,
      );
      if (current === version.current) {
        setPending(false);
        router.replace({
          pathname: "/appointments/[id]",
          params: { id: result.id },
        });
      }
    } catch (failure) {
      if (current === version.current) {
        setPending(session.hasPending);
        setStaffReview(requiresStaffReview(failure));
        setError(
          failure instanceof Error
            ? failure.message
            : "The change could not be completed. Retry the same change.",
        );
      }
    } finally {
      running.current = false;
      setBusy(false);
    }
  }

  return (
    <Screen>
      <Heading eyebrow="YOUR SERVICE VISIT" title="The details, all here." />
      {loading ? (
        <Busy label="Loading your visit…" />
      ) : (
        <>
          {!!error && <Body error>{error}</Body>}
          {!details ? (
            <Button
              title="Try again"
              onPress={() => {
                void load();
              }}
            />
          ) : (
            <>
              <Card>
                <Text
                  style={{
                    color: theme.accent,
                    fontSize: 12,
                    fontWeight: "800",
                    letterSpacing: 1,
                  }}
                >
                  {details.appointment.status}
                </Text>
                <Text
                  style={{ color: theme.text, fontSize: 24, fontWeight: "700" }}
                >
                  {formatTime(details.appointment.starts_at, details.timezone)}
                </Text>
                <Body>
                  Until{" "}
                  {formatTime(details.appointment.ends_at, details.timezone)} ·{" "}
                  {details.timezone}
                </Body>
                <Body>{details.customer.full_name}</Body>
                <Body>{details.service.equipment_issue}</Body>
                {details.customer.address && (
                  <Body>
                    {details.customer.address.line1},{" "}
                    {details.customer.address.city},{" "}
                    {details.customer.address.state_code}{" "}
                    {details.customer.address.postal_code}
                  </Body>
                )}
              </Card>
              {pending ? (
                <Card>
                  <Text
                    style={{
                      color: theme.text,
                      fontSize: 20,
                      fontWeight: "700",
                    }}
                  >
                    Resolve your previous change.
                  </Text>
                  <Body>
                    A date/time change was submitted. Retry the original request
                    to establish its result before selecting another time.
                  </Body>
                  {change.current?.pendingTime && (
                    <Body>
                      Requested time:{" "}
                      {formatTime(change.current.pendingTime, details.timezone)}
                    </Body>
                  )}
                  {staffReview ? (
                    <Body error>
                      This change needs staff review. Contact the business; do
                      not create a replacement booking.
                    </Body>
                  ) : (
                    <Button
                      title="Retry the same appointment change"
                      busy={busy}
                      onPress={() => {
                        void submit();
                      }}
                    />
                  )}
                </Card>
              ) : details.can_reschedule ? (
                <Card>
                  <Text
                    style={{
                      color: theme.text,
                      fontSize: 20,
                      fontWeight: "700",
                    }}
                  >
                    Need a different time?
                  </Text>
                  <Body>
                    Your current visit stays booked until the replacement is
                    confirmed.
                  </Body>
                  <Field
                    label={`Preferred date (${details.timezone})`}
                    placeholder="YYYY-MM-DD"
                    value={day}
                    onChangeText={(value) => {
                      setDay(value);
                      setSlots(undefined);
                      setSelected(undefined);
                    }}
                    keyboardType="numbers-and-punctuation"
                    maxLength={10}
                    editable={!busy}
                  />
                  <Button
                    secondary
                    title="Find available times"
                    busy={busy}
                    onPress={() => {
                      void findTimes();
                    }}
                  />
                  {slots && (
                    <>
                      {!!slots.message && <Body>{slots.message}</Body>}
                      {!slots.slots.length && (
                        <Body>
                          No times are available for this date. Choose another
                          date.
                        </Body>
                      )}
                      {slots.slots.map((slot) => (
                        <Choice
                          key={`${slot.team_key}:${slot.starts_at}`}
                          label={`${formatTime(slot.starts_at, slots.timezone ?? details.timezone)} – ${formatTime(slot.ends_at, slots.timezone ?? details.timezone)}`}
                          selected={selected === slot}
                          disabled={busy}
                          onPress={() => setSelected(slot)}
                        />
                      ))}
                      {selected && (
                        <Button
                          title="Review appointment change"
                          disabled={busy}
                          onPress={() =>
                            Alert.alert(
                              "Confirm your new time",
                              `Move your visit to ${formatTime(selected.starts_at, slots.timezone ?? details.timezone)} (${slots.timezone ?? details.timezone})? Your current visit will be replaced only after confirmation.`,
                              [
                                { text: "Keep current visit", style: "cancel" },
                                {
                                  text: "Confirm new time",
                                  onPress: () => {
                                    void submit();
                                  },
                                },
                              ],
                            )
                          }
                        />
                      )}
                    </>
                  )}
                </Card>
              ) : (
                <Card>
                  <Body>
                    {details.change_message ??
                      "Contact the business to change this appointment."}
                  </Body>
                </Card>
              )}
            </>
          )}
        </>
      )}
    </Screen>
  );
}
