import { useState } from "react";
import { Alert } from "react-native";
import { Body, Button, Card, Heading, Screen } from "../../components/ui";
import { useSession } from "../../lib/session";

export default function AccountScreen() {
  const session = useSession();
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <Screen>
      <Heading eyebrow="YOUR ACCOUNT" title="A little peace of mind." />
      <Card>
        <Body>{session.user?.full_name}</Body>
        <Body>{session.user?.email}</Body>
        <Body>
          Authenticator verification protects your account. Your session is
          stored securely on this device and expires automatically.
        </Body>
      </Card>
      <Card>
        <Body>
          Sign out to remove this device’s saved session. Finish any booking
          conversation before signing out.
        </Body>
        {!!error && <Body error>{error}</Body>}
        <Button
          secondary
          title="Sign out"
          busy={busy}
          onPress={() => {
            setBusy(true);
            void session
              .signOut()
              .then((revoked) => {
                if (!revoked)
                  Alert.alert(
                    "Signed out on this device",
                    "The server could not be reached to revoke your session. It will expire automatically.",
                  );
              })
              .catch(() => {
                setError(
                  "Could not remove the saved session. Unlock this device and try again.",
                );
                setBusy(false);
              });
          }}
        />
      </Card>
      <Body>HVACLine · Version 0.1.0</Body>
    </Screen>
  );
}
