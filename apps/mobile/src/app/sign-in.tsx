import { useEffect, useRef, useState } from "react";
import { AppState, Linking, Text, View } from "react-native";
import { usePreventScreenCapture } from "expo-screen-capture";
import {
  Body,
  Button,
  Card,
  Field,
  Heading,
  Screen,
  useTheme,
} from "../components/ui";
import { MobileApi } from "../lib/api";
import {
  challenge,
  login,
  object,
  string,
  type Account,
  type Challenge,
  type StoredSession,
} from "../lib/models";
import { useSession } from "../lib/session";

type CompletedLogin = {
  user: Account;
  session: StoredSession;
  recoveryCodes: string[];
};

export default function SignIn() {
  usePreventScreenCapture("customer-sign-in");
  const session = useSession(),
    theme = useTheme();
  const [signup, setSignup] = useState(false),
    [name, setName] = useState(""),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState("");
  const [pending, setPending] = useState<Challenge>(),
    [setup, setSetup] = useState<{ secret: string; uri: string }>(),
    [code, setCode] = useState("");
  const [recover, setRecover] = useState(false),
    [completed, setCompleted] = useState<CompletedLogin>(),
    [savedCodes, setSavedCodes] = useState(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [visible, setVisible] = useState(AppState.currentState === "active");
  const mounted = useRef(true),
    running = useRef(false),
    temporary = useRef<CompletedLogin | undefined>(undefined);
  const api = session.api;
  useEffect(() => {
    mounted.current = true;
    const listener = AppState.addEventListener("change", (state) =>
      setVisible(state === "active"),
    );
    return () => {
      mounted.current = false;
      listener.remove();
      const value = temporary.current;
      if (value)
        void new MobileApi(value.session.origin, value.session.token)
          .request("auth/logout", "POST")
          .catch(() => undefined);
    };
  }, []);
  useEffect(() => {
    if (!pending) return;
    const timer = setTimeout(
      () => {
        setPending(undefined);
        setSetup(undefined);
        setCode("");
        setError("Your sign-in challenge expired. Sign in again.");
      },
      Math.max(0, pending.expiresAt - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [pending]);

  async function action(work: () => Promise<void>) {
    if (running.current) return;
    running.current = true;
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (failure) {
      if (mounted.current)
        setError(
          failure instanceof Error
            ? failure.message
            : "Sign-in could not be completed.",
        );
    } finally {
      running.current = false;
      if (mounted.current) setBusy(false);
    }
  }

  async function begin() {
    if (!api) return;
    if (
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()) ||
      !password ||
      (signup && (!name.trim() || password.length < 15))
    )
      throw new Error(
        signup
          ? "Enter your name, email, and a password of at least 15 characters."
          : "Enter your email and password.",
      );
    const result = challenge(
      await api.request(signup ? "auth/signup" : "auth/login", "POST", {
        email: email.trim(),
        password,
        ...(signup ? { full_name: name.trim() } : {}),
      }),
    );
    if (!mounted.current) return;
    setPassword("");
    setPending(result);
    setRecover(false);
    setSetup(undefined);
    setCode("");
  }

  function challengeApi() {
    if (!pending || !session.origin || pending.expiresAt <= Date.now())
      throw new Error("Your sign-in challenge expired. Sign in again.");
    return new MobileApi(session.origin, pending.token);
  }

  async function enroll() {
    const value = object(
      await challengeApi().request("auth/mfa/setup", "POST"),
    );
    const secret = string(value.secret),
      uri = string(value.otpauth_uri);
    const parsed = new URL(uri);
    if (
      !/^[A-Z2-7]{16,128}$/.test(secret) ||
      parsed.protocol !== "otpauth:" ||
      parsed.hostname !== "totp" ||
      parsed.searchParams.get("secret") !== secret
    )
      throw new Error("The authenticator setup could not be read. Try again.");
    if (mounted.current) setSetup({ secret, uri });
  }

  async function verify() {
    if (!session.origin) return;
    if (recover) {
      if (!/^[a-fA-F0-9]{8}(-[a-fA-F0-9]{8}){3}$/.test(code.trim()))
        throw new Error("Enter a complete recovery code.");
      const result = challenge(
        await challengeApi().request("auth/mfa/recover", "POST", {
          code: code.trim(),
        }),
      );
      if (mounted.current) {
        setPending(result);
        setRecover(false);
        setCode("");
        setSetup(undefined);
      }
      return;
    }
    if (!/^\d{6}$/.test(code.trim()))
      throw new Error("Enter the six-digit code from your authenticator.");
    const result = login(
      await challengeApi().request("auth/mfa/verify", "POST", {
        code: code.trim(),
      }),
      session.origin,
    );
    temporary.current = result;
    if (!mounted.current) {
      await new MobileApi(result.session.origin, result.session.token).request(
        "auth/logout",
        "POST",
      );
      temporary.current = undefined;
      return;
    }
    setCode("");
    setSetup(undefined);
    setPending(undefined);
    if (result.recoveryCodes.length) setCompleted(result);
    else {
      await session.establish(result.session, result.user);
      temporary.current = undefined;
    }
  }

  async function cancel() {
    try {
      if (pending) await challengeApi().request("auth/mfa/cancel", "POST");
    } finally {
      if (mounted.current) {
        setPending(undefined);
        setSetup(undefined);
        setCode("");
        setRecover(false);
      }
    }
  }

  if (!visible)
    return (
      <Screen>
        <Heading eyebrow="HVACLINE" title="Welcome back." />
      </Screen>
    );
  return (
    <Screen>
      <Heading
        eyebrow="HVACLINE · YOUR HOME, HANDLED"
        title={
          completed
            ? "Keep these somewhere safe."
            : pending
              ? "One more step."
              : signup
                ? "Make room for comfort."
                : "Welcome home."
        }
      >
        {completed
          ? "These recovery codes can restore access if you lose your authenticator. Each code works once."
          : pending
            ? "Protect your appointments with your authenticator app."
            : "Talk to Line, book a service visit, and keep track of what’s next."}
      </Heading>
      {!!error && <Body error>{error}</Body>}
      {completed ? (
        <Card>
          <Body selectable>{completed.recoveryCodes.join("\n")}</Body>
          <Button
            title={
              savedCodes
                ? "Continue to HVACLine"
                : "I have saved my recovery codes"
            }
            busy={busy}
            onPress={() => {
              if (!savedCodes) {
                setSavedCodes(true);
                return;
              }
              void action(async () => {
                await session.establish(completed.session, completed.user);
                temporary.current = undefined;
                setCompleted(undefined);
              });
            }}
          />
        </Card>
      ) : pending ? (
        <Card>
          <Text style={{ color: theme.text, fontSize: 22, fontWeight: "700" }}>
            {recover
              ? "Use a recovery code"
              : pending.nextAction === "enroll"
                ? "Set up your authenticator"
                : "Authenticator code"}
          </Text>
          {pending.nextAction === "enroll" &&
            !recover &&
            (setup ? (
              <>
                <Body>
                  Enter this setup key in your authenticator, or open a
                  compatible app.
                </Body>
                <Body selectable>{setup.secret}</Body>
                <Button
                  secondary
                  title="Open authenticator"
                  disabled={busy}
                  onPress={() => {
                    void Linking.openURL(setup.uri).catch(() =>
                      setError(
                        "Open your authenticator and enter the setup key manually.",
                      ),
                    );
                  }}
                />
              </>
            ) : (
              <Button
                title="Get authenticator setup key"
                busy={busy}
                onPress={() => {
                  void action(enroll);
                }}
              />
            ))}
          {(pending.nextAction === "verify" || setup || recover) && (
            <>
              <Field
                label={recover ? "Recovery code" : "Six-digit code"}
                value={code}
                onChangeText={setCode}
                keyboardType={recover ? "default" : "number-pad"}
                autoCapitalize="none"
                autoCorrect={false}
                maxLength={recover ? 35 : 6}
                textContentType="oneTimeCode"
                secureTextEntry={recover}
                editable={!busy}
              />
              <Button
                title={recover ? "Recover access" : "Verify and continue"}
                busy={busy}
                onPress={() => {
                  void action(verify);
                }}
              />
            </>
          )}
          {pending.nextAction === "verify" && (
            <Button
              secondary
              title={
                recover ? "Use authenticator instead" : "Use a recovery code"
              }
              disabled={busy}
              onPress={() => {
                setRecover(!recover);
                setCode("");
                setError("");
              }}
            />
          )}
          <Button
            secondary
            title="Back to sign in"
            disabled={busy}
            onPress={() => {
              void action(cancel);
            }}
          />
        </Card>
      ) : (
        <Card>
          {signup && (
            <Field
              label="Full name"
              value={name}
              onChangeText={setName}
              autoComplete="name"
              maxLength={160}
              editable={!busy}
            />
          )}
          <Field
            label="Email"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="email"
            maxLength={254}
            editable={!busy}
          />
          <Field
            label="Password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoComplete={signup ? "new-password" : "current-password"}
            maxLength={128}
            editable={!busy}
            onSubmitEditing={() => {
              void action(begin);
            }}
          />
          {signup && (
            <Body>
              Use at least 15 characters. An authenticator app is required.
            </Body>
          )}
          <Button
            title={signup ? "Create account" : "Sign in"}
            busy={busy}
            onPress={() => {
              void action(begin);
            }}
          />
          <Button
            secondary
            title={
              signup
                ? "Already have an account? Sign in"
                : "New here? Create an account"
            }
            disabled={busy}
            onPress={() => {
              setSignup(!signup);
              setPassword("");
              setError("");
            }}
          />
        </Card>
      )}
      <View style={{ paddingHorizontal: 6 }}>
        <Body>
          Line is an AI assistant. For immediate danger, contact local emergency
          services.
        </Body>
      </View>
    </Screen>
  );
}
