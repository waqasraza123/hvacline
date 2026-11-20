# GitHub presentation and licensing

The repository uses a short product-focused README with an original SVG banner,
a feature list, website link, and proprietary license notice. Development,
deployment, architecture, setup, and project-status details are kept out of README.
README also links directly to Dashboard and **Try Yourself** at
`https://www.hvacline.online/ai-lead-recovery`, labels recovery as a preview and
mentions GHL calendar booking/contact summaries without claiming live acceptance.
Community files supply bug/feature forms, a PR template,
contribution guidance, a security-reporting process, and release-note categories.
README includes a React Native logo, React Native/Expo badges and an iOS/Android
customer-app Preview feature linked to apps/mobile. The SVG logo is copied from
https://reactnative.dev/img/header_logo.svg and linked to the official project;
third-party names and artwork retain their owners' rights.
The existing v0.1.0-beta.1 tag stays at its original commit. The owner requests
publication of the Expo mobile source and a new v0.1.0-beta.2 tag; this is not an
app-store binary release or a runtime acceptance claim.

## Owner licensing decision

The owner requires prior written permission for use, including free, personal,
educational, evaluation, internal, and commercial use. Root LICENSE expresses
that decision for original first-party work. README and development setup repeat
it; npm metadata uses UNLICENSED, and Python metadata uses LicenseRef-Proprietary
with LICENSE included. UNLICENSED means no package license is granted; it is not
the public-domain Unlicense.

Third-party works retain their licenses, including TailAdmin's MIT notice. No
copyright assignment, legal entity, payment agreement, or commercial fee is
invented. Existing valid grants and rights under applicable law remain intact.
Public GitHub viewing/forking rights remain under GitHub's terms. This is a
licensing notice, not an application paywall or access-control implementation.
The repository remains public.

[GitHub licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
explains the public-repository rights. Permissions should identify the authorized
work and scope in writing; a public inquiry does not itself grant permission.

## Owner acceptance — UNVERIFIED

No tests, builds, lint/type checks, formatters, migrations, seeds, browser renders,
live services, provider operations, or deployment are authorized by this task.
Application runtime, packaging, and GitHub rendering remain unverified.

Suggested read-only commands for the owner:

```bash
gh repo view waqasraza123/hvacline --json description,homepageUrl,repositoryTopics
gh api repos/waqasraza123/hvacline/private-vulnerability-reporting
```

Manual checks:

1. Open the repository on GitHub at desktop and phone widths. Check banner text,
   website/license links, Dashboard and Try Yourself destinations, and feature
   readability. Check the React Native logo/badge and Expo badge, the mobile
   source link, and the app's Preview label. Confirm recovery remains labeled Preview.
   Confirm the README contains
   no development, deployment, architecture, setup, or verification sections.
2. Check the About description, website URL, and topic chips. Confirm the
   proprietary permission requirement is visible near the top of README and in
   LICENSE. A custom license may be shown by GitHub as an unrecognized license;
   the explicit notice and LICENSE link provide the readable terms.
3. Open New issue and inspect both forms without submitting. Check required
   fields, documentation/license links, and the private security-report link.
4. Inspect the PR template and release-note categories. Publishing a PR/release
   is not required for this review. Do not submit an actual vulnerability report.
5. Confirm TailAdmin's MIT notice remains and first-party package metadata uses
   the proprietary indicators. Review written permission agreements separately.

If the owner specifically authorizes a packaging check, from the repository root:

```bash
.venv/bin/python -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/hvacline-license-wheel .
```

Inspect the produced wheel's METADATA and license files for LicenseRef-Proprietary
and the full LICENSE text. This build has not run. No dependency versions or
application behavior are changed by the licensing metadata.
