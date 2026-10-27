# Homepage branding handoff

The homepage presents HVACLine with the Line AI voice-receptionist identity, electric blue/navy colors, responsive layouts, a matching favicon, and keyboard/reduced-motion support. The October 27 copy update targets HVAC business owners with missed-call/job loss, live appointment availability and caller-confirmed booking. Sections follow hero, three-step workflow, services, FAQ and final CTA. Demo entry points reuse the existing customer booking route. Full copy, three ranked hero options and current owner checks are in `docs/homepage-copy.md`. No performance metrics, reviews or customer counts are invented.

Booking/sign-in links target `/book`, `/login` and `/signup`. These customer routes and their draft authentication remain development-only and owner-unverified; they require the private portal configuration and customer-access migration before use. `/operations` remains a separate protected administrator workspace. Do not give customers the administrator token or treat the customer draft as production authentication.

No tests, builds, linters, type checks, services, browser previews or live checks were run. Source formatting only was applied. The owner should run:

```bash
npm ci
npm run verify:web
```

Manual checks: open `/` at desktop and mobile sizes; follow every navigation/booking link; confirm customer routes require authentication and `/operations` remains separately gated; check keyboard focus, native FAQ expansion, reduced motion, text contrast, fixed-launcher placement and absence of horizontal overflow. Verify the new favicon and page/share titles. No runtime or deployment success is claimed.
