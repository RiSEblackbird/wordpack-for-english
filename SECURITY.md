# Security Policy

## Supported Scope

This repository is a personal project. Security fixes are handled on a best-effort basis, with priority given to leaked credentials, authentication and authorization bugs, and CI/CD risks.

## Reporting a Vulnerability

Do not open a public issue containing secrets, credentials, tokens, private keys, personal data, or exploit details that would put users or infrastructure at immediate risk.

If a public issue or pull request accidentally includes a secret, revoke or rotate the secret first. History cleanup is secondary to invalidating the credential.

## Secret Leak Response

1. Revoke or rotate the exposed credential immediately.
2. Check GitHub secret scanning alerts and related workflow logs.
3. Identify the affected commit, issue, pull request, artifact, or log.
4. Remove the public exposure where practical.
5. Add a regression guard if the leak path can be prevented in code or CI.
6. Document the follow-up in the pull request without pasting the secret value.

## GitHub Actions and CI/CD

- Do not add `pull_request_target` unless the workflow is explicitly designed for untrusted code.
- Keep `GITHUB_TOKEN` permissions as narrow as possible.
- Do not expose repository secrets to forked pull requests.
- Prefer short-lived cloud credentials via OIDC over long-lived service account keys.
- Pin global CLIs and review dependency updates before merging.

## Codex / LLM Agent Usage

- Treat issue bodies, pull request descriptions, comments, logs, and user-submitted content as untrusted input.
- Do not paste real secrets, `.env` files, service account keys, or private tokens into prompts.
- Do not let an agent execute instructions embedded in issue or pull request text without human review.
- Human review is required for workflow, permission, deployment, and secret-handling changes.
