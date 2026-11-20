import type { ConfigContext, ExpoConfig } from "expo/config";

function identifier(value: string | undefined, name: string) {
  if (value && !/^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$/.test(value))
    throw new Error(
      `${name} must be a valid reverse-domain application identifier.`,
    );
  return value || undefined;
}

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "HVACLine",
  slug: "hvacline-mobile",
  version: "0.1.0",
  scheme: "hvacline",
  orientation: "portrait",
  userInterfaceStyle: "automatic",
  ios: {
    supportsTablet: true,
    bundleIdentifier: identifier(
      process.env.MOBILE_IOS_BUNDLE_IDENTIFIER,
      "MOBILE_IOS_BUNDLE_IDENTIFIER",
    ),
    infoPlist: {
      NSMicrophoneUsageDescription:
        "Talk to Line to ask HVAC questions and book a service visit.",
      ITSAppUsesNonExemptEncryption: false,
    },
  },
  android: {
    package: identifier(
      process.env.MOBILE_ANDROID_PACKAGE,
      "MOBILE_ANDROID_PACKAGE",
    ),
    permissions: [
      "android.permission.RECORD_AUDIO",
      "android.permission.MODIFY_AUDIO_SETTINGS",
    ],
    blockedPermissions: ["android.permission.CAMERA"],
  },
  plugins: [
    "expo-router",
    "expo-secure-store",
    [
      "expo-audio",
      {
        microphonePermission: "Talk to Line to book an HVAC service visit.",
        enableBackgroundRecording: false,
        enableBackgroundPlayback: false,
      },
    ],
    "@livekit/react-native-expo-plugin",
    [
      "@config-plugins/react-native-webrtc",
      {
        microphonePermission: "Talk to Line to book an HVAC service visit.",
        cameraPermission: false,
      },
    ],
  ],
});
