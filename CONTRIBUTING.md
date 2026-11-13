# Working on HVACLine

HVACLine is proprietary software. Read [LICENSE](LICENSE) before using, running,
or modifying it. Public repository access does not grant a development or
noncommercial-use license.

## Propose a change

Use the [issue forms](https://github.com/waqasraza123/hvacline/issues/new/choose)
to describe a bug or proposed improvement. Include the affected workflow,
expected behavior, and a minimal example with fictional data. Discuss substantial
changes before implementation.

Before preparing code changes, obtain written permission from the applicable
copyright holders covering the proposed work. Agree any contribution licensing
terms in writing; this guide does not grant permission or transfer ownership.

## Authorized development

- Read [AGENTS.md](AGENTS.md), [project state](docs/project-state.md), and the
  [development setup guide](docs/development-setup.md).
- Follow existing naming, ownership constraints, API contracts, and migration
  history. Legacy package names remain for compatibility.
- Keep changes focused. Preserve unrelated work and third-party notices.
- Use fictional records. Do not commit secrets, personal data, customer content,
  transcripts, recordings, or provider credentials.
- Document configuration changes, migrations, and exact owner acceptance steps.

## Validation and pull requests

The owner must explicitly authorize each specific test, build, lint, type check,
migration, seed, readiness check, service startup, or other verification execution.
Do not start background terminals, watchers, or development servers on your own.

The [setup guide](docs/development-setup.md#verification) lists deferred commands;
feature guides supply focused commands and manual acceptance steps. Database
tests require a separate disposable database. Never substitute a shared database.

In a pull request, describe the problem, resulting behavior, and any setup needed.
List exactly what ran and what remains unverified. If execution was not
authorized, say so and provide the exact suggested commands and manual checks.
Do not claim provider or production success from fixtures or a build.

Keep commit messages under 140 characters. Follow the owner's publication and
deployment instructions; permission to edit source does not authorize live
provider actions, deployment, or customer calls/messages.

## Security reports

Follow [SECURITY.md](SECURITY.md) for private vulnerability reporting. Public
issues and pull requests must not contain sensitive reproduction details.
