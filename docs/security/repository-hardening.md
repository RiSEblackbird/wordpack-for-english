# Repository Hardening Checklist

Last reviewed: 2026-06-21

This checklist tracks GitHub repository settings that cannot be fully changed from the repository contents. Keep exact secret values, production identifiers, and private log details out of this document.

## GitHub Security Settings

- [ ] Secret scanning is enabled.
- [ ] Push protection is enabled.
- [ ] Dependabot alerts are enabled.
- [ ] Dependabot security updates are enabled.
- [ ] Code scanning alerts are visible after the CodeQL workflow runs.
- [ ] Dependency review is enabled on dependency and workflow changes.
- [ ] OpenSSF Scorecard advisory results are reviewed after the weekly run.

## GitHub Actions Settings

- [ ] Default workflow permissions are set to read-only.
- [ ] Fork pull request workflows require approval before secrets or privileged jobs can run.
- [ ] No workflow uses `pull_request_target` without a dedicated threat model.

## Branch / Ruleset

- [ ] `main` cannot be force-pushed.
- [ ] `main` cannot be deleted.
- [ ] Required checks are limited to stable, low-noise checks.
- [ ] CodeQL is not required until false positives and runtime are reviewed.
- [ ] Dependency review is required only after false positives are understood.
- [ ] OpenSSF Scorecard is not required while it is advisory-only.

## Production Environment

- [ ] `production` environment is protected.
- [ ] Deployment secrets are scoped to the production environment where possible.
- [ ] Long-lived `GCP_SA_KEY` migration to Workload Identity Federation is tracked separately.

## Manual Review Notes

- Date:
- Reviewer:
- Remaining gaps:
