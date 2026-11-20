# Expo customer app

Implementation is **UNVERIFIED**. This is the customer app for iOS and Android:
account creation/sign-in, mandatory authenticator MFA and recovery, voice/chat
booking, appointment history/details, and explicit date/time changes. It does not
add an administrator dashboard or change the backend's production access gates.

## Stack and layout

- `apps/mobile`: Expo SDK 58.0.26, React Native 0.88.1, Expo's supported React
  19.3.0, Expo Router 58.0.32, TypeScript 6.0.3, native components, system
  light/dark appearance and accessible controls.
- `packages/customer-core`: shared booking controller, contracts, payloads,
  transcript handling, text echo handling and appointment presentation. Web
  compatibility modules retain the existing request adapters and error classes.
- Native voice uses `@elevenlabs/react-native@1.2.42`. Its published peer range
  requires LiveKit React Native 2.12.0 / WebRTC 144.1.2; the newer LiveKit 3.x
  packages are deliberately not forced into an incompatible peer graph.
- Silent Chat uses the documented ElevenLabs text-only WebSocket protocol.
  The native voice SDK rejects WebSocket connections, so Chat has its own
  transport and never requests microphone permission or sends audio frames.
- `apps/web/src/app/api/mobile/[...path]/route.ts` is an explicitly enabled,
  customer-only server gateway. It forwards the native bearer token and injects
  the existing portal key server-side. The app contains no portal/admin/provider
  secret. Existing web cookie routes remain separate.

Version selection used the [Expo SDK 58 release](https://expo.dev/changelog/sdk-58),
[Expo's dependency matrix](https://unpkg.com/expo@58.0.26/bundledNativeModules.json),
published npm package peer metadata, [Expo monorepo guidance](https://docs.expo.dev/guides/monorepos/),
and the [ElevenLabs native SDK](https://elevenlabs.io/docs/eleven-agents/libraries/react-native)
and [WebSocket event reference](https://elevenlabs.io/docs/eleven-agents/api-reference/eleven-agents/websocket).
The dependency lockfile was resolved with package scripts disabled. Package
installation, native compatibility and runtime behavior have not been verified.

## Configuration

Use the repository's Node **24.x** requirement (at least 24.3 for this Expo/RN
release). The resolver available during implementation used Node 26 and emitted
engine warnings; the repository's declared Node requirement was preserved.

Copy `apps/mobile/.env.example` to `apps/mobile/.env` and set:

| Variable                       | Purpose                                                                                                                                 |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| `EXPO_PUBLIC_WEB_ORIGIN`       | Public HTTPS origin of the Next.js website hosting `/api/mobile`, without a path, query or credentials. This is not the FastAPI origin. |
| `MOBILE_IOS_BUNDLE_IDENTIFIER` | Owner-selected reverse-domain iOS application identifier.                                                                               |
| `MOBILE_ANDROID_PACKAGE`       | Owner-selected reverse-domain Android package identifier.                                                                               |

Public Expo variables are bundled into the app. Never put API keys or the
customer portal key in an `EXPO_PUBLIC_*` variable, application configuration,
EAS public environment, or application source.

On the **Next.js server**, configure the existing `NEXT_PUBLIC_API_BASE_URL` and
server-only `CUSTOMER_PORTAL_SECRET`, plus `MOBILE_API_ENABLED=true` when ready
for controlled acceptance. The new gateway defaults off in the web environment
example. The portal secret must match the FastAPI setting and is never entered
in the mobile app. Deployment of these changes/settings remains owner-managed.

The existing API still requires `APP_ENVIRONMENT=development`,
`DEMO_SANDBOX_ENABLED=true`, `CUSTOMER_PORTAL_ENABLED=true`, its configured
development business/actor and MFA encryption key. Booking requires the existing
ElevenLabs conversation configuration and `CONVERSATION_AI_ENABLED=true` with
`CONVERSATION_PROVIDER=elevenlabs`. No flag or credential was changed by this work.
The local conversation provider is rejected by the mobile client. Use the
existing setup guides rather than creating new provider agents or seeding data.

The gateway permits only listed customer authentication, appointment, FAQ and
conversation-booking actions; it does not forward admin headers, incoming
cookies, arbitrary paths, redirects or query strings. Browser-origin requests
are rejected, but missing Origin is not an authentication mechanism: scoped
backend bearer checks, MFA and existing rate/ownership gates provide access
control. Do not use a shared static key as a native client credential.

## Session and booking behavior

Password sign-in returns only a short-lived MFA challenge. Challenges, setup
secrets and recovery codes stay in memory; recovery codes require explicit
acknowledgement before entering the app. Sign-in screens suppress capture and
hide sensitive content while inactive. The full session is stored in SecureStore
with device-only unlocked keychain accessibility, bound to its server origin,
validated against `/auth/me` on restoration and subject to the backend's maximum
eight-hour expiry. Sign-out removes the local token and attempts server revocation;
offline revocation failure is reported. Session refresh is not implemented.

Voice requires disclosure/explicit microphone consent and device permission.
Chat requires AI disclosure acknowledgement and remains silent. Both feed the
shared booking controller and existing backend confirmation/ownership/hazard
rules. Only persisted `CONFIRMED` appointments are described as booked. Drafts,
holds, failures and staff-review outcomes have separate visible states. The
transcript is held in memory; normal backend confirmation persistence is reused.
Optional persistent customer memory is not enabled by this mobile version; its
agent tools return an explicit unavailable response.

Leaving the booking screen, backgrounding the app, expiry or disconnect ends the
provider connection and requests backend session cleanup. A failed cleanup keeps
its reference for an explicit retry; a backend-owned same-user active-session
reference can also be released. There is no automatic reconnection or new-key
replay. Active conversations and intake retry payloads are not restored after
process termination. After an uncertain write/disconnect, inspect appointments
and contact staff if necessary before starting another request; an unknown intake
or provider outcome is not established by an empty appointment list.

Rescheduling reads server-provided slots, asks for explicit confirmation and saves
the original request/key in SecureStore **before** the first POST. Only resource
references, selected slot and the request key are stored, scoped to the signed-in
account, original appointment and server. An uncertain change can be retried
after reopening the app with exactly that same payload. A matching confirmed
replacement clears the saved request. Known definitive rejections allow a new
choice; uncertain/provider-review outcomes preserve the reference. Existing
notice/change limits, GHL restrictions and transactional backend behavior remain
authoritative. There is no offline mutation queue or app-provided cancellation.

## Owner commands — none executed during implementation

From the repository root, under Node 24.x:

```sh
npm ci
npm exec --workspace @insurance-operations/mobile -- expo install --check
npm run typecheck:mobile
npm run test:mobile
npm run test:web -- src/features/customer/mobile-proxy.test.ts src/features/customer/appointments-model.test.ts src/features/conversation/voice-booking.test.ts src/features/conversation/api.test.ts src/features/conversation/connection.test.ts src/features/conversation/text-messages.test.ts src/features/conversation/review.test.ts src/features/conversation/booking-progress.test.ts
npm run verify:web
```

These checks are necessary because the web app now consumes the extracted shared
package. No Python/schema behavior changed, and no migration is required for this
mobile slice. The already-required backend migrations remain a deployment prerequisite.

After configuration, create and run the native development build on the desired
platform using the installed Xcode/Android toolchain:

```sh
npm run mobile:ios
npm run mobile:android
```

Run the command for the platform you are accepting. For an already-installed
development client, start Metro with `npm run dev:mobile`. These commands start
services/builds and are left to the owner. **Expo Go cannot run native voice.**
`apps/mobile/eas.json` also defines development, internal preview and production
profiles; an Expo account/project, owner identifiers and platform signing must be
configured before using EAS. No EAS project, signing credential, binary, store
listing, deployment or publication was created.

## Manual acceptance — iOS and Android

1. Confirm an unset/invalid origin produces a clear configuration screen, the
   gateway is unavailable when disabled, and no client bundle contains a portal,
   provider or administrator secret. Confirm existing web sign-in/booking works.
2. Create a controlled account, enroll using a compatible authenticator/manual
   key, reject incorrect/expired codes, acknowledge recovery codes, recover with
   one code and complete re-enrollment. Password-only access must never succeed.
3. Restart the app, restore only the correct account, expire/revoke a session,
   sign out online/offline and test locked-device storage failures. Reject another
   account's appointment/session references. Changing the web origin must not
   reuse a previous server's credentials.
4. Deny microphone permission and use Chat; verify no microphone indicator or
   audio. Test long typing, full readbacks, tool replies, no duplicate text echoes,
   dropped connections, unsent draft retention and explicit previous-session cleanup.
5. Accept Voice permission and verify actual audio, mute/unmute, typed replies,
   full intake and separate appointment readbacks, exactly one saved booking,
   hold expiry, unavailable slots and human handling of hazards. Do not claim a
   successful booking until it appears as confirmed in appointment history.
6. Switch tabs, background/lock the device, interrupt audio and reach the session
   limit: the provider/microphone must stop and late callbacks must not revive it.
   Lost writes must keep their original retry references; never blindly rebook.
7. Inspect upcoming/history/details and business timezone/DST displays. Decline
   a date/time change, then explicitly confirm a server-returned slot. Drop its
   response, terminate/reopen the app and retry the same saved change; verify one
   replacement and preservation of the original until transaction success. Check
   limits, provider-review, conflict, stale-slot and no-availability responses.
8. Check keyboard behavior, large text, screen readers, touch targets, small and
   tablet layouts, both color schemes, auth capture protection and background
   redaction on physical devices.

All implementation/runtime/security/provider/visual acceptance remains
**UNVERIFIED** until the owner reports these results. Production customer identity,
tenant onboarding, operational support and store requirements remain separate
launch work; the mobile app does not remove those existing project gates.
