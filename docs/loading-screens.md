# Shared loading screens

Implementation is **unverified**. No tests, builds, linters, type checks,
services or browser checks were run for this change.

`LoadingScreen` centers the existing HVACLine brand, an animated orange signal
and a descriptive loading status across the viewport. It follows the saved or
system theme through the existing `data-theme` initialization and stops the
signal animation for reduced-motion preferences. It requires no client state,
timer, dependency or artificial delay.

The root route fallback, Pricing, Billing and published-site route fallbacks
reuse it. Buttons and loading panels within visible content keep their inline
spinners. Calling is removed from the shared desktop and mobile top navigation;
the homepage calling section remains available.

## Deferred owner checks

From the repository root, run:

```sh
npm run verify:web
```

Manually check the deployed app or an owner-managed local instance:

1. With browser network throttling and cache disabled, navigate from the homepage
   to Pricing. On a cold route load, confirm the branded loader and descriptive
   status are centered horizontally and vertically, then replaced by Pricing.
   Cached routes may render immediately without a loader.
2. Repeat for Billing, a published `/sites/[slug]` URL and a route using the root
   fallback such as `/book`. Confirm eventual content, redirects and errors
   remain reachable; no loader persists after the destination resolves.
3. Check desktop and narrow mobile portrait/landscape in both themes. Confirm
   the loader fits the viewport without horizontal scrolling or a color flash.
4. Enable reduced motion and confirm the signal stays still. With a screen
   reader, confirm a descriptive loading status is available. Confirm the brand
   link remains keyboard accessible and returns home.
5. Confirm desktop and mobile top navigation contain Dashboard and Pricing,
   with no Calling item. Check both destinations, menu dismissal, active dot
   and keyboard navigation. Confirm the homepage calling section still works.
6. Confirm checkout buttons, sign-in and in-content loading panels retain their
   existing inline feedback and surrounding content.
