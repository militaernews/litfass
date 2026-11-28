# AGENTS.md

## Commit messages

Every commit must use this exact format:

```
type(scope): What was changed
```

- `type` is one of: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `build`, `ci`.
- `scope` is required and names the affected area (for example `site`, `server`, `bot`, `guide`, `stats`, `deps`, `monorepo`).
- The description starts with a capital letter, is one line, and says what changed in the past tense or imperative: `Add`, `Fix`, `Move`, `Remove`, `Update`.
- No merge-style or free-form messages such as `update`, `wip`, or `fix stuff`.

Examples:

```
feat(stats): Add 90-day range and CTR comparison
fix(nav): Correct bottom-tab icon sizes
docs(guide): Split setup steps into a three-card wizard
chore(deps): Bump dependencies and pin TypeScript 6.0.3
```
