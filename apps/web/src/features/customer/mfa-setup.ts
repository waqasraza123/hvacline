export type MfaSetup = { secret: string; otpauthUri: string };

export function parseMfaSetup(value: unknown): MfaSetup {
  const message = "Authenticator setup could not be loaded. Sign in again.";
  if (
    typeof value !== "object" ||
    value === null ||
    !("secret" in value) ||
    typeof value.secret !== "string" ||
    !/^[A-Z2-7]{32}$/.test(value.secret) ||
    !("otpauth_uri" in value) ||
    typeof value.otpauth_uri !== "string" ||
    value.otpauth_uri.length > 2048
  )
    throw new Error(message);

  let uri: URL;
  try {
    uri = new URL(value.otpauth_uri);
  } catch {
    throw new Error(message);
  }
  if (
    uri.protocol !== "otpauth:" ||
    uri.hostname !== "totp" ||
    uri.username ||
    uri.password ||
    uri.port ||
    uri.hash ||
    uri.pathname.length < 2 ||
    ["secret", "issuer", "algorithm", "digits", "period"].some(
      (key) => uri.searchParams.getAll(key).length !== 1,
    ) ||
    uri.searchParams.get("secret") !== value.secret ||
    uri.searchParams.get("issuer") !== "HVACLine AI" ||
    uri.searchParams.get("algorithm") !== "SHA1" ||
    uri.searchParams.get("digits") !== "6" ||
    uri.searchParams.get("period") !== "30"
  )
    throw new Error(message);

  return { secret: value.secret, otpauthUri: value.otpauth_uri };
}
