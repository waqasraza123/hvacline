# Existing SMS verification flow review — 2026-11-07

Subsequent owner-authorized source change removes the carrier line-type gate and
permits SMS-capable US VoIP/landline numbers. This supersedes the mobile-only
requirements in this historical review; delivery/code acceptance remain unverified.
See [current implementation and owner checks](sms-capable-demo-numbers.md).

The existing frontend and backend are connected in source to the supported
Telnyx Verify send/verify operations. No replacement implementation or endpoint
switch is needed. This is a source review plus one authenticated profile GET,
not hosted website acceptance. No SMS, verification POST, call, profile change,
test suite, migration or deployment ran during this investigation.

The owner reports a successful six-digit SMS delivery and
response_code accepted using the existing profile in Telnyx Learn & Build.
That establishes owner-reported provider delivery/code acceptance for that test;
it did not create an HVACLine account-bound challenge or exercise the website's
carrier check and activation gates. No recipient, OTP or request body is retained.

## Provider contract

| Operation | Existing adapter | Assessment |
| --- | --- | --- |
| Send | POST /v2/verifications/sms with phone_number, verify_profile_id and timeout_secs | Same official send operation used in the owner's test. No custom_code is supplied; Telnyx generates the code. |
| Verify | POST /v2/verifications/{saved_verification_id}/actions/verify with code | Officially supported verification by ID, equivalent in purpose to verification by phone number/profile. |
| Accept | Require response_code accepted and a returned phone number matching the challenge's destination hash | Success is decided on the server; the client cannot assert accepted status. |

Source: [provider](../apps/backend/src/insurance_operations/telephony/outbound/sms_provider.py).
The provider saves the ID from the send response. It does not substitute a
frontend-supplied phone number for that ID at verification time. The existing
by-ID route therefore should be retained rather than replaced with the console's
by-phone-number example.

Official contracts:
[send SMS](https://developers.telnyx.com/api-reference/verify/trigger-sms-verification),
[verify by ID](https://developers.telnyx.com/api-reference/verify/verify-verification-code-by-id),
[verify by phone number](https://developers.telnyx.com/api-reference/verify/verify-verification-code-by-phone-number).

## Frontend/backend connection

1. The homepage mounts OutboundDemoDialog. Text me a code posts action send_code,
   the recipient and versioned SMS consent to the Next /api/outbound-demo route.
2. The Next bridge requires the current authenticated account, same origin, the
   recovery cookie and the server form flag. It derives a stable account owner
   token and forwards to /api/v1/outbound-demo/phone-verifications using the
   server-only shared outbound secret.
3. The backend checks availability, US eligibility, optional allowlist and SMS
   budgets. It reserves a challenge before provider operations, performs Number
   Lookup, sends the SMS and saves the provider verification ID. The browser
   receives only challenge_id, expires_at and verified.
4. Verify mobile number posts action verify_code, challenge_id and six digits.
   The bridge forwards to /phone-verifications/verify. The service checks
   ownership/expiry/attempts, commits an attempt, verifies using the saved provider
   ID and marks the proof verified only after provider acceptance and destination
   matching. UI and backend both enforce six numeric digits.
5. Verifying a code does not call the voice provider. A separate explicit call
   submission passes phone_verification_id; the call reservation consumes a
   verified, unexpired, account/number-bound proof once. SMS verification does not
   replace authenticator MFA.

Relevant source:
[dialog](../apps/web/src/features/outbound-demo/outbound-demo-dialog.tsx),
[Next bridge](../apps/web/src/app/api/outbound-demo/route.ts),
[routes](../apps/backend/src/insurance_operations/telephony/outbound/routes.py),
[proof service](../apps/backend/src/insurance_operations/telephony/outbound/verification.py),
[schemas](../apps/backend/src/insurance_operations/telephony/outbound/verification_schemas.py).

## Null code length and current readback

An authenticated GET during this review returns HTTP200. Both the configured
profile ID and the existing HVACLine Public Demo OTP name match; the current
SMS code_length is integer6. No PATCH was sent. This agrees with the earlier
owner-authorized PATCH and its verified GET; the earlier null read predates that
change in the recorded session. A different reported null response cannot be
matched without its profile identity and timing.

The provider SDK describes code_length as optional. An unset field in a profile
response is not evidence that code generation or verification is broken, and
the HVACLine code never retrieves or rejects a profile based on that field.
The owner's successful test establishes six-digit acceptance for that request.
It does not establish a universal six-digit default for every unset profile:
the saved Learn & Build send payload and exact provider fallback rule are not
available. In particular, a request containing custom_code would not establish
the service-generated default; the HVACLine adapter omits that parameter.

The previous advice that null itself required correction was too strong. No
further profile change is warranted from null alone. Preserve the existing
working profile and judge delivery/code acceptance separately from stored
configuration readback.

Reference: [official generated profile types](https://github.com/team-telnyx/telnyx-node/blob/master/src/resources/verify-profiles.ts).

## Remaining activation requirements

- **Mobile policy differs from raw SMS capability.** Before sending, the adapter
  requires a successful US Number Lookup with carrier.type mobile. VoIP,
  landline, missing/unknown carrier types and lookup errors fail before SMS. A
  Sonetel number that receives Verify SMS can still fail this independent
  mobile-only policy if lookup classifies it as VoIP. Its actual lookup result
  was not queried in this review. No policy change is authorized or implemented.
- **SMS shares the website calling gate.** Both send and verify require
  website_available: backend enabled, website enabled, live voice acceptance,
  Verify credentials, and conditional transfer acceptance. The Next form flag
  must also be true. There is no independent SMS-only public activation flag.
  Do not invent voice acceptance merely to unlock SMS. Under consented_us,
  transfer remains disabled; omitting the number-policy variable defaults to
  allowlist.
- **Hosted configuration is unverified.** Render must have the existing working
  Verify key/profile and Number Lookup access, compatible backend revision and
  working operator/customer MFA setup. Vercel must have the compatible frontend,
  correct HTTPS API origin and matching server-only OUTBOUND_DEMO_SECRET. Local
  settings are not proof of these hosted values. Local dotenv inspection shows
  public execution/form flags unset and no matching configured bridge-secret
  pair; it is not a fully activated local website configuration.
- **Database requirement is already satisfied for the owner-confirmed target.**
  Earlier authorized readback verified20261105_0019 and the SMS proof table.
  No migration is introduced by this review or by the endpoint equivalence.
- **Application acceptance remains unverified.** The Telnyx console test bypasses
  account/MFA, bridge, mobile lookup, challenge persistence, expiry/attempt rules
  and proof consumption. Existing provider, bridge and database regression
  specifications cover these paths but were not executed here. No new message
  is needed to establish the documented endpoint equivalence; a future hosted
  website acceptance run would require separate owner authorization.
- **Voice lifecycle remains a separate dependency.** The earlier voicemail
  result established SIP delivery, not a human two-way call or backend terminal
  reconciliation. Its known-call status GET is still unreported. An active or
  unknown voice record blocks new calls, although it is not directly consulted
  by the SMS start method. SMS/account/number cooldown and budgets also remain.

Broader public release requirements remain documented in
[the existing release guide](public-demo-production-readiness.md). This review
does not activate public requests or change provider/spending/retention settings.
