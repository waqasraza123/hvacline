# Homepage branding handoff

The homepage now presents HVACLine with the Line AI booking-assistant identity, electric blue/navy colors, concise customer-focused copy, responsive layouts, a prominent booking entry, a matching favicon, and keyboard/reduced-motion support. It contains no demo language, technical setup copy, invented reviews, customer counts or live appointment claims.

All booking/sign-in links currently lead to the existing protected `/operations` route. Customer `/login`, `/signup` and `/book` routes remain in an unfinished LOCAL-ONLY commit and are deliberately absent from this publication. Do not give customers the administrator token. Replace these homepage destinations with real customer account routes only after that work is reviewed, verified and published.

No tests, builds, linters, type checks, services, browser previews or live checks were run. Source formatting only was applied. The owner should run:

```bash
npm ci
npm run verify:web
```

Manual checks: open `/` at desktop and mobile sizes; follow every navigation/booking link; confirm the protected entry remains gated; check keyboard focus, native FAQ expansion, reduced motion, text contrast, fixed-launcher placement and absence of horizontal overflow. Verify the new favicon and page/share titles. No runtime or deployment success is claimed.
