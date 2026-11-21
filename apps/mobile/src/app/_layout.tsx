import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { SessionProvider, useSession } from "../lib/session";
import {
  Body,
  Busy,
  Button,
  Card,
  Heading,
  Screen,
  ThemeProvider,
  useTheme,
} from "../components/ui";

function Navigator() {
  const session = useSession(),
    theme = useTheme();
  if (!session.ready)
    return (
      <Screen>
        <Busy />
      </Screen>
    );
  if (session.error)
    return (
      <Screen>
        <Heading eyebrow="HVACLINE" title="Let’s get connected." />
        <Card>
          <Body error>{session.error}</Body>
          {session.origin && (
            <>
              <Button title="Try again" onPress={session.retry} />
              <Button
                secondary
                title="Clear saved sign-in"
                onPress={() => {
                  void session.signOut().catch(() => undefined);
                }}
              />
            </>
          )}
        </Card>
      </Screen>
    );
  return (
    <>
      <StatusBar style="auto" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: theme.background },
          headerTintColor: theme.text,
          contentStyle: { backgroundColor: theme.background },
          headerShadowVisible: false,
        }}
      >
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Protected guard={!session.user}>
          <Stack.Screen name="sign-in" options={{ headerShown: false }} />
        </Stack.Protected>
        <Stack.Protected guard={!!session.user}>
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen
            name="appointments/[id]"
            options={{ title: "Your appointment" }}
          />
        </Stack.Protected>
      </Stack>
    </>
  );
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <SessionProvider>
          <Navigator />
        </SessionProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
