## User story

<!--
Reference to the story in telemed-ia-docs:
code-corhuila/telemed-ia-docs#NN
If this PR is infrastructure or tooling, write N/A and explain why.
-->

## What changes and why

<!--
3-5 lines: the problem this PR solves and the decision taken.
If the change is purely technical, say so.
-->

## How it was tested

<!--
- Which tests cover the change.
- Result of the `ci.yml` workflow (green/red).
- Local commands executed and their result.
- If the change affects the contract, whether the HTTP client still
  consumes it correctly.
-->

## Promotion trace

<!--
Only for PRs targeting `qa` or `main`.
List each re-applied commit with its traceability line:

- feat(api): some change
  - cherry picked from commit <sha-in-origin>

For PRs targeting `develop`, write: N/A — PR targeting develop.
-->

N/A — PR targeting `develop`.

## Checklist

- [ ] No secrets or real credentials committed.
- [ ] No schema changes outside the `-db` repo.
- [ ] The service still validates RS256 JWT in itself (norm 5.3.7).
- [ ] The common error envelope is preserved (norm 5.3.5).
- [ ] `X-Correlation-Id` is reused or generated and echoed (norm 5.3.9).
- [ ] Creation is idempotent (norm 5.3.8).
- [ ] Listings are paginated (norm 5.3.6).
- [ ] Domain has no framework or database dependency.
- [ ] The three permanent branches remain intact.
- [ ] Commit messages follow Conventional Commits.
- [ ] CI is green (`ruff check` and `pytest`).
- [ ] Affected documentation updated.
