import { useState } from "react";
import { router } from "expo-router";
import { ConversationProvider } from "@elevenlabs/react-native";
import { Text, View } from "react-native";
import type { ConversationInputMode } from "@insurance-operations/customer-core";
import { LANGUAGE_NAMES } from "@insurance-operations/customer-core";
import {
  Body,
  Button,
  Card,
  Choice,
  Field,
  Heading,
  Screen,
  styles,
  useTheme,
} from "../../components/ui";
import { useBooking } from "../../features/use-booking";

function BookingScreen() {
  const theme = useTheme(),
    booking = useBooking();
  const [mode, setMode] = useState<ConversationInputMode>("VOICE"),
    [consent, setConsent] = useState(false),
    [draft, setDraft] = useState(""),
    [messageError, setMessageError] = useState("");
  const active =
    booking.phase === "connected" || booking.phase === "connecting";
  const receipt = booking.appointment;
  const confirmed = receipt?.appointment.status === "CONFIRMED";
  const holdRemaining =
    receipt?.appointment.status === "HELD"
      ? Math.max(
          0,
          Math.ceil(
            (Date.parse(receipt.appointment.hold_expires_at) - Date.now()) /
              1000,
          ),
        )
      : 0;
  const stage = confirmed
    ? 3
    : booking.progress.requestSaved
      ? 2
      : booking.progress.awaitingIntakeConfirmation
        ? 1
        : 0;
  return (
    <Screen>
      <Heading
        eyebrow="BOOK WITH LINE"
        title="Comfort starts with a conversation."
      >
        Ask a question or arrange your next HVAC service visit.
      </Heading>
      <Card>
        <View style={styles.row}>
          <Text
            style={{ color: theme.accent, fontSize: 24, fontWeight: "800" }}
          >
            Line
          </Text>
          <Text accessibilityLiveRegion="polite" style={{ color: theme.muted }}>
            {booking.phase === "connecting"
              ? "Connecting…"
              : booking.phase === "connected"
                ? `${booking.speaking ? "Speaking" : booking.mode === "TEXT" ? "Chat connected" : booking.muted ? "Microphone muted" : "Listening"} · ${booking.remaining}s left`
                : "Your AI receptionist"}
          </Text>
        </View>
        {!active && (
          <>
            <Body>Conversation language</Body>
            <View style={{ gap: 8 }}>
              {booking.languageRegistry?.languages.filter((item) => item.channel === "mobile" && item.available).map((item) =>
                <Choice key={item.code} label={item.name} selected={booking.language === item.code} onPress={() => booking.setLanguage(item.code)} />)}
              {!booking.languageRegistry && <Body>{booking.languageError || "Loading language availability…"}</Body>}
              {booking.languageRegistry && !booking.languageRegistry.languages.some((item) => item.channel === "mobile" && item.available) && <Body>No verified voice language is available for mobile. Ask staff for help.</Body>}
            </View>
            <View style={{ gap: 10 }}>
              <Choice
                label="Voice — speak with Line"
                selected={mode === "VOICE"}
                onPress={() => {
                  setMode("VOICE");
                  setConsent(false);
                }}
              />
              <Choice
                label="Chat — type without microphone access"
                selected={mode === "TEXT"}
                onPress={() => {
                  setMode("TEXT");
                  setConsent(false);
                }}
              />
            </View>
            <Choice
              label={
                mode === "VOICE"
                  ? "I understand Line is AI and agree to use my microphone for this conversation."
                  : "I understand I’m chatting with an AI assistant."
              }
              selected={consent}
              onPress={() => setConsent(!consent)}
            />
            <Button
              title={mode === "VOICE" ? "Talk to Line" : "Start chat"}
              disabled={
                !consent ||
                !booking.languageRegistry?.languages.some((item) => item.channel === "mobile" && item.code === booking.language && item.available) || !!booking.languageError ||
                !!booking.cleanupId ||
                !!booking.progress.failure?.uncertain
              }
              onPress={() => {
                setMessageError("");
                void booking.start(mode);
              }}
            />
          </>
        )}
        {active && (
          <>
            <Body>{booking.observedLanguage ? `Active language: ${LANGUAGE_NAMES[booking.observedLanguage]} · provider result observed.` : `Initial language: ${LANGUAGE_NAMES[booking.language]}. Current language is not confirmed by a provider result.`}</Body>
            {booking.languageSwitchFailed && <Body error>The provider could not confirm a language switch. Continue in the current language or ask for staff assistance.</Body>}
            <Button
              secondary
              title={
                booking.phase === "connecting"
                  ? "Cancel connection"
                  : "Finish conversation"
              }
              onPress={() => {
                void booking.finish("COMPLETED");
              }}
            />
            {booking.phase === "connected" && booking.mode === "VOICE" && (
              <Button
                secondary
                title={booking.muted ? "Unmute microphone" : "Mute microphone"}
                onPress={() => booking.setMuted(!booking.muted)}
              />
            )}
          </>
        )}
        {!!booking.error && <Body error>{booking.error}</Body>}
        {booking.cleanupId && (
          <Button
            secondary
            title="Release previous session"
            busy={booking.working}
            onPress={() => {
              void booking.releasePrevious();
            }}
          />
        )}
      </Card>
      {(active || booking.turns.length > 0) && (
        <Card>
          <Text
            accessibilityRole="header"
            style={{ color: theme.text, fontSize: 20, fontWeight: "700" }}
          >
            Your conversation
          </Text>
          {booking.turns.length ? (
            booking.turns.map((turn, index) => (
              <View
                key={index}
                style={{
                  gap: 5,
                  alignSelf:
                    turn.speaker === "USER" ? "flex-end" : "flex-start",
                  maxWidth: "94%",
                  backgroundColor:
                    turn.speaker === "USER"
                      ? theme.accentSurface
                      : theme.background,
                  padding: 14,
                  borderRadius: 15,
                }}
              >
                <Text
                  style={{
                    color: theme.accent,
                    fontWeight: "700",
                    fontSize: 12,
                  }}
                >
                  {turn.speaker === "USER" ? "YOU" : "LINE"}
                </Text>
                <Text
                  selectable
                  style={{ color: theme.text, fontSize: 16, lineHeight: 24 }}
                >
                  {turn.text}
                </Text>
              </View>
            ))
          ) : (
            <Body>Line’s messages will appear here when connected.</Body>
          )}
          <Field
            label="Message Line"
            value={draft}
            onChangeText={(value) => {
              setDraft(value);
              booking.notifyTyping();
            }}
            multiline
            maxLength={2000}
            placeholder="Describe what you need…"
            style={{ minHeight: 84, textAlignVertical: "top" }}
          />
          <Button
            title="Send message"
            disabled={booking.phase !== "connected" || !draft.trim()}
            onPress={() => {
              try {
                booking.sendText(draft);
                setDraft("");
                setMessageError("");
              } catch (failure) {
                setMessageError(
                  failure instanceof Error
                    ? failure.message
                    : "Your message could not be sent.",
                );
              }
            }}
          />
          {!!messageError && <Body error>{messageError}</Body>}
        </Card>
      )}
      <Card>
        <Text
          accessibilityRole="header"
          style={{ color: theme.text, fontSize: 20, fontWeight: "700" }}
        >
          From request to booked.
        </Text>
        {[
          "Share your details",
          "Confirm Line’s full readback",
          "Choose and confirm a time",
          "Appointment booked",
        ].map((label, index) => (
          <View key={label} style={styles.row}>
            <Text
              style={{
                color: index <= stage ? theme.accent : theme.muted,
                fontSize: 18,
                fontWeight: "800",
              }}
            >
              {index < stage ? "✓" : `${index + 1}.`}
            </Text>
            <Text
              style={{
                color: index <= stage ? theme.text : theme.muted,
                flex: 1,
                fontSize: 15,
              }}
            >
              {label}
            </Text>
          </View>
        ))}
        {booking.progress.hazardous ? (
          <Body error>
            This request needs human attention. Leave immediate danger and
            contact emergency services. No new appointment can be booked.
          </Body>
        ) : (
          <Body>
            {confirmed
              ? "Your appointment is confirmed and saved."
              : receipt?.appointment.status === "HELD"
                ? holdRemaining
                  ? `This time is held for ${holdRemaining}s. Confirm only after Line reads the full appointment details.`
                  : "Your temporary hold has expired. Ask Line to check availability again."
                : booking.progress.requestSaved
                  ? "Your request is saved. No appointment is booked yet."
                  : "Your details stay a draft until you confirm them."}
          </Body>
        )}
        {receipt && <Body>{receipt.readback}</Body>}
        {booking.progress.pending && (
          <Body>Completing the current booking step…</Body>
        )}
        {booking.progress.failure && (
          <>
            <Body error>{booking.progress.failure.message}</Body>
            {booking.phase === "connected" &&
              !booking.progress.failure.staffReview && (
                <Button
                  secondary
                  title="Retry the same booking step"
                  disabled={!!booking.progress.pending}
                  onPress={() => {
                    void booking.retry();
                  }}
                />
              )}
          </>
        )}
        <Button
          secondary
          title="View my appointments"
          onPress={() => router.navigate("/(tabs)/appointments")}
        />
      </Card>
      <Body>
        Only a confirmed appointment is booked. Temporary holds expire. Finish
        the conversation before switching screens; leaving this screen ends the
        connection.
      </Body>
    </Screen>
  );
}

export default function BookWithLine() {
  return (
    <ConversationProvider>
      <BookingScreen />
    </ConversationProvider>
  );
}
