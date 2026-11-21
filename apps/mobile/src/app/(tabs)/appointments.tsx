import { useCallback, useEffect, useRef, useState } from "react";
import { AppState, Text, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import {
  appointmentLabel,
  filterAppointments,
  type AppointmentFilter,
} from "@insurance-operations/customer-core";
import {
  Body,
  Busy,
  Button,
  Card,
  Heading,
  Screen,
  styles,
  useTheme,
} from "../../components/ui";
import { appointments, formatTime } from "../../lib/models";
import { useSession } from "../../lib/session";

export default function AppointmentsScreen() {
  const { api } = useSession(),
    theme = useTheme();
  const [data, setData] = useState<ReturnType<typeof appointments>>(),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [filter, setFilter] = useState<AppointmentFilter>("upcoming"),
    [now, setNow] = useState(Date.now());
  const version = useRef(0);
  const load = useCallback(async () => {
    if (!api) return;
    const current = ++version.current;
    setLoading(true);
    setError("");
    try {
      const value = appointments(await api.request("appointments"));
      if (current === version.current) {
        setData(value);
        setNow(Date.now());
      }
    } catch (failure) {
      if (current === version.current)
        setError(
          failure instanceof Error
            ? failure.message
            : "Appointments could not be loaded.",
        );
    } finally {
      if (current === version.current) setLoading(false);
    }
  }, [api]);
  useFocusEffect(
    useCallback(() => {
      void load();
      const listener = AppState.addEventListener("change", (state) => {
        if (state === "active") void load();
      });
      return () => {
        version.current += 1;
        listener.remove();
      };
    }, [load]),
  );
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(timer);
  }, []);
  const visible = filterAppointments(data?.appointments ?? [], filter, now);
  return (
    <Screen>
      <Heading eyebrow="YOUR APPOINTMENTS" title="Know what’s next.">
        Your confirmed visits and past appointments, together.
      </Heading>
      <Button
        secondary
        title="Refresh appointments"
        busy={loading}
        onPress={() => {
          void load();
        }}
      />
      {loading ? (
        <Busy label="Loading your appointments…" />
      ) : error ? (
        <Card>
          <Body error>{error}</Body>
          <Button
            title="Try again"
            onPress={() => {
              void load();
            }}
          />
        </Card>
      ) : (
        <>
          <View style={styles.row}>
            {(["upcoming", "history", "all"] as const).map((value) => (
              <Button
                key={value}
                title={
                  value === "upcoming"
                    ? "Upcoming"
                    : value === "history"
                      ? "History"
                      : "All"
                }
                secondary={filter !== value}
                onPress={() => setFilter(value)}
              />
            ))}
          </View>
          <Body>
            All times in {data?.timezone ?? "UTC"}. Up to 50 latest
            appointments.
          </Body>
          {visible.length ? (
            visible.map((visit) => (
              <Card key={visit.id}>
                <Text
                  style={{
                    color:
                      visit.status === "CONFIRMED"
                        ? theme.success
                        : theme.muted,
                    fontSize: 12,
                    letterSpacing: 1,
                    fontWeight: "800",
                  }}
                >
                  {appointmentLabel(visit, now).toUpperCase()}
                </Text>
                <Text
                  style={{ color: theme.text, fontSize: 22, fontWeight: "700" }}
                >
                  {formatTime(visit.starts_at, data!.timezone)}
                </Text>
                <Body>
                  {visit.status === "HELD"
                    ? "A temporary hold is not a booked visit. Confirm it in the original conversation."
                    : "Open this visit for service details and available changes."}
                </Body>
                <Button
                  secondary
                  title="View appointment"
                  onPress={() =>
                    router.push({
                      pathname: "/appointments/[id]",
                      params: { id: visit.id },
                    })
                  }
                />
              </Card>
            ))
          ) : (
            <Card>
              <Text
                style={{ color: theme.text, fontSize: 22, fontWeight: "700" }}
              >
                {filter === "history"
                  ? "A clean slate."
                  : "Your next visit starts here."}
              </Text>
              <Body>
                {filter === "history"
                  ? "Past, cancelled, and expired appointments will appear here."
                  : "Once you confirm a visit with Line, it will appear here."}
              </Body>
              <Button
                title="Book with Line"
                onPress={() => router.navigate("/(tabs)")}
              />
            </Card>
          )}
        </>
      )}
    </Screen>
  );
}
