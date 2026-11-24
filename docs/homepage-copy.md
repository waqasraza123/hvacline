# HVACLine homepage copy

## Current positioning — November 21, 2026 — UNVERIFIED

The homepage speaks to business owners across industries. HVACLine remains the
brand; customization is the broader product proposition, and the working example
is explicitly HVAC. This supersedes the previous HVAC-only hero copy. It does
not add industry implementations, self-service setup, countries or languages.
Existing booking, safety, provider and production-access boundaries still apply.

## Hero

Eyebrow: **CUSTOMIZABLE AI VOICE AGENTS**

Headline: **AI voice agents, built around your business.**

Supporting paragraph: Shape your agent’s voice, knowledge, and workflows to answer
questions, capture enquiries, and support your business.

Primary hero/header/launcher action: **Try Voice Chat**, linking to `/book`.

Secondary hero action: **Explore the dashboard**, linking to `/operations`.

Action note: Try the HVAC example. Sign in, then connect when you’re ready.

The existing headline markup retains its break after “AI voice agents,” and
accented second line. The hero feature badges include **Multilingual** with a
language icon and **Language support · Preview** caption, using the existing
orange icon and responsive wrapping. All six tags form a full-width strip beneath
the hero copy/demo, with titles before captions. The standalone
multilingual demo card is removed from the homepage; the dedicated demo remains
accessible through Operations and the README.

## Examples and closing action

The conversation card reads **Meet Line** with the subtitle **HVAC example**.
Voice remains its initial mode; Text chat and the existing guest exchange/sign-in
continuation are preserved. The standalone **HVAC PHONE EXAMPLE** section is
removed from the homepage. The hero phone link and callback dialog remain available.

The **HOW THE HVAC EXAMPLE WORKS** section and **AI LEAD RECOVERY** teaser are
also removed. The hero and feature badges now lead directly into the closing
action. The dedicated lead recovery page remains available through navigation.

Closing eyebrow: **EXPLORE THE HVAC EXAMPLE**

Closing headline: **Experience AI voice in action.**

Closing button: **Try Voice Chat**, linking to `/book`.

Closing support: Meet Line. Ask a question. See where the conversation takes you.

The customer workspace retains its current Voice default, Text choice,
authentication/MFA, AI disclosure, microphone permission and explicit connection.
Navigation alone does not start a provider session or place a phone call.

## Footer and launcher

Footer: Customizable AI voice agents for business conversations.

Footer links remain Sign in / Create an account. The fixed launcher keeps
**Try Voice Chat** with subtitle **AI VOICE AGENTS FOR BUSINESS**.

## Search and sharing metadata

Default title and Open Graph title:
**HVACLine | Customizable AI Voice Agents for Business**

Description and Open Graph description: Customizable AI voice agents for customer
conversations, lead capture, and business workflows. Explore HVACLine’s HVAC voice
and appointment-booking example.

The existing page-title template, icons and route-specific metadata are preserved.
README, mobile branding and backend/provider prompts are outside this copy change.

## Owner checks — not executed

From the repository root:

```sh
npm run verify:web
```

Manually inspect `/` at narrow phone and desktop widths in both themes. Check
headline wrapping, card/phone example labels, closing action, footer and launcher
for overlap or horizontal overflow. Follow the header/hero/closing/launcher
`/book` links and the existing phone/callback actions; confirm sign-in, consent
and connection remain separate steps. Inspect the page title, description and
Open Graph text. Confirm the homepage identifies the HVAC example and makes no
instant self-service, worldwide availability or ready-made all-industry claim.

The latest pass changes homepage presentation, explanatory copy and component
styles. Exact scope and manual checks are in [homepage branding](homepage-branding.md).
No tests, builds, linters, type checks, services or browser acceptance ran.
Implementation and visual/runtime acceptance remain **UNVERIFIED**. Deployment
and publication are separate owner actions; this slice needs no migration,
backend deployment, environment variable or provider configuration change.
