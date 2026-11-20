import { createContext, useContext, useMemo, type ReactNode } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  useColorScheme,
  type TextInputProps,
  type ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

const light = {
  background: "#f6f5f2",
  surface: "#ffffff",
  text: "#202522",
  muted: "#67716b",
  line: "#e3e7e2",
  accent: "#a84416",
  accentSurface: "#fff1e8",
  success: "#246344",
  danger: "#b33232",
};
const dark = {
  background: "#141a17",
  surface: "#202923",
  text: "#f3f5ef",
  muted: "#a8b5ac",
  line: "#364239",
  accent: "#ffab7b",
  accentSurface: "#3a2a20",
  success: "#8bdbac",
  danger: "#ffaaaa",
};
type Palette = typeof light;
const ThemeContext = createContext<Palette>(light);
export function ThemeProvider({ children }: { children: ReactNode }) {
  const scheme = useColorScheme();
  return (
    <ThemeContext.Provider value={scheme === "dark" ? dark : light}>
      {children}
    </ThemeContext.Provider>
  );
}
export function useTheme() {
  return useContext(ThemeContext);
}

export function Screen({
  children,
  scroll = true,
}: {
  children: ReactNode;
  scroll?: boolean;
}) {
  const theme = useTheme();
  return (
    <SafeAreaView
      edges={["top", "left", "right"]}
      style={{ flex: 1, backgroundColor: theme.background }}
    >
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        {scroll ? (
          <ScrollView
            contentContainerStyle={styles.screen}
            keyboardShouldPersistTaps="handled"
          >
            {children}
          </ScrollView>
        ) : (
          <View style={[styles.screen, { flex: 1 }]}>{children}</View>
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

export function Heading({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
}) {
  const theme = useTheme();
  return (
    <View style={{ gap: 10, marginBottom: 10 }}>
      {eyebrow && (
        <Text style={[styles.eyebrow, { color: theme.accent }]}>{eyebrow}</Text>
      )}
      <Text
        accessibilityRole="header"
        style={[styles.title, { color: theme.text }]}
      >
        {title}
      </Text>
      {children && <Body>{children}</Body>}
    </View>
  );
}

export function Body({
  children,
  error = false,
  selectable = false,
}: {
  children: ReactNode;
  error?: boolean;
  selectable?: boolean;
}) {
  const theme = useTheme();
  return (
    <Text
      selectable={selectable}
      accessibilityRole={error ? "alert" : undefined}
      style={[styles.body, { color: error ? theme.danger : theme.muted }]}
    >
      {children}
    </Text>
  );
}

export function Card({
  children,
  style,
}: {
  children: ReactNode;
  style?: ViewStyle;
}) {
  const theme = useTheme();
  return (
    <View
      style={[
        styles.card,
        { backgroundColor: theme.surface, borderColor: theme.line },
        style,
      ]}
    >
      {children}
    </View>
  );
}

export function Button({
  title,
  onPress,
  disabled = false,
  busy = false,
  secondary = false,
  danger = false,
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  busy?: boolean;
  secondary?: boolean;
  danger?: boolean;
}) {
  const theme = useTheme();
  const color = secondary ? theme.text : theme.background;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: disabled || busy, busy }}
      disabled={disabled || busy}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        {
          backgroundColor: secondary
            ? theme.surface
            : danger
              ? theme.danger
              : theme.accent,
          borderColor: secondary ? theme.line : "transparent",
          opacity: disabled || busy ? 0.5 : pressed ? 0.75 : 1,
        },
      ]}
    >
      {busy && <ActivityIndicator color={color} />}
      <Text
        style={{ color, fontSize: 16, fontWeight: "700", textAlign: "center" }}
      >
        {title}
      </Text>
    </Pressable>
  );
}

export function Field({
  label,
  ...properties
}: TextInputProps & { label: string }) {
  const theme = useTheme();
  const style = useMemo(
    () => [
      styles.input,
      {
        backgroundColor: theme.surface,
        color: theme.text,
        borderColor: theme.line,
      },
    ],
    [theme],
  );
  return (
    <View style={{ gap: 8 }}>
      <Text style={{ color: theme.text, fontWeight: "600", fontSize: 14 }}>
        {label}
      </Text>
      <TextInput
        {...properties}
        accessibilityLabel={label}
        placeholderTextColor={theme.muted}
        style={[style, properties.style]}
      />
    </View>
  );
}

export function Busy({ label = "Getting things ready…" }: { label?: string }) {
  const theme = useTheme();
  return (
    <View
      style={{
        flex: 1,
        minHeight: 180,
        alignItems: "center",
        justifyContent: "center",
        gap: 16,
      }}
    >
      <ActivityIndicator size="large" color={theme.accent} />
      <Body>{label}</Body>
    </View>
  );
}

export function Choice({
  label,
  selected,
  onPress,
  disabled = false,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
  disabled?: boolean;
}) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityState={{ checked: selected, disabled }}
      onPress={onPress}
      disabled={disabled}
      style={[
        styles.choice,
        {
          borderColor: selected ? theme.accent : theme.line,
          backgroundColor: selected ? theme.accentSurface : theme.surface,
          opacity: disabled ? 0.6 : 1,
        },
      ]}
    >
      <Text
        style={{ color: selected ? theme.accent : theme.muted, fontSize: 20 }}
      >
        {selected ? "●" : "○"}
      </Text>
      <Text
        style={{ color: theme.text, flex: 1, fontSize: 15, lineHeight: 22 }}
      >
        {label}
      </Text>
    </Pressable>
  );
}

export const styles = StyleSheet.create({
  screen: {
    padding: 24,
    gap: 18,
    paddingBottom: 40,
    width: "100%",
    maxWidth: 720,
    alignSelf: "center",
    flexGrow: 1,
  },
  eyebrow: { fontSize: 12, letterSpacing: 2, fontWeight: "800" },
  title: { fontSize: 34, lineHeight: 40, fontWeight: "800", letterSpacing: -1 },
  body: { fontSize: 16, lineHeight: 24 },
  card: { borderWidth: 1, borderRadius: 22, padding: 22, gap: 16 },
  button: {
    borderRadius: 15,
    borderWidth: 1,
    minHeight: 52,
    paddingHorizontal: 18,
    paddingVertical: 14,
    flexDirection: "row",
    gap: 10,
    justifyContent: "center",
    alignItems: "center",
  },
  input: {
    minHeight: 54,
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 13,
    fontSize: 16,
  },
  choice: {
    minHeight: 56,
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    flexDirection: "row",
    gap: 12,
    alignItems: "center",
  },
  row: {
    flexDirection: "row",
    gap: 12,
    alignItems: "center",
    flexWrap: "wrap",
  },
});
