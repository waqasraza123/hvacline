# Customer color refresh

Implemented in `/private/tmp/hvacline-browser-demo`. Implementation and browser appearance remain owner-unverified.

## Design

The owner selected orange and charcoal across all customer pages, with light backgrounds and dark feature panels. Shared customer CSS variables provide heat orange (#F97316), charcoal (#18181B), warm white (#FAFAF9), darker orange for readable links and focus outlines, and warm neutral text and borders. Homepage voice artwork and final CTA use charcoal panels and orange accents. Customer branding and the favicon retain their existing shapes.

The palette covers homepage, login, signup, booking, chat/voice selection and composer, booking progress/history, allowance banners, countdown, and booking-details/reschedule dialogs. Green confirmation, amber warning, and red error states remain distinct. Shared components retain existing internal-screen colors through variable fallbacks; the favicon is site-wide. No API, schema, environment, provider, copy, or booking-behavior change is included.

## Owner commands

From the active checkout, install dependencies if absent, then run the existing web verification:

```sh
cd /private/tmp/hvacline-browser-demo
npm ci
npm run verify:web
```

No installs, tests, builds, linters, type checks, services, browser previews, migrations, or deployments were run for this change. Source formatting only was applied using the existing formatter from the original checkout. Hosting remains owner-managed; deploy the frontend through Vercel after accepting the change.

## Manual checks

- Review `/`, `/login`, `/signup`, and signed-in `/book` at desktop and mobile widths. Confirm readable text, warm light backgrounds, charcoal feature panels, and consistent orange accents without wrapping or overflow regressions.
- Check logo/favicon, hero artwork, service icons, FAQ expansion, final CTA, floating launcher, authentication errors, password visibility, loading and disabled buttons.
- Navigate by keyboard: focus must remain visible on light and dark surfaces, selected modes and tabs must be identifiable, and disabled buttons must not lift on hover.
- With synthetic data, inspect Chat/Voice controls, composer, progress stages, allowance banner, normal/urgent countdown, booking history, and details/reschedule dialog, including close, selection and confirmation controls.
- Confirm green saved outcomes, amber warnings and red errors retain their text/icons. Check text contrast against WCAG AA (4.5:1 normal text, 3:1 large text) and essential control boundaries/focus against 3:1. Contrast has not been measured by the agent.
- Inspect internal operations/settings/demo pages to confirm their existing colors remain intact, apart from the shared site favicon.
