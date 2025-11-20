# Release Labels Quick Reference

This is a quick reference guide for maintainers on using release labels for automated versioning.

## ⚠️ IMPORTANT: Default Behavior

**If you merge a PR without a release label, NO RELEASE will be created.**

This is intentional and safe by default - you must explicitly label PRs to trigger a release.

## When Reviewing PRs

Before merging any PR to `master`, decide if it should trigger a release and add the appropriate label:

## Label Reference

| Label | Color | Effect | Current → New | Use Case |
|-------|-------|--------|---------------|----------|
| **release:patch** | 🟢 Green | Patch bump | 2.1.5 → 2.1.6 | Bug fixes, minor improvements |
| **release:minor** | 🟡 Yellow | Minor bump | 2.1.5 → 2.2.0 | New features, enhancements, new functionality |
| **release:major** | 🔴 Red | Major bump | 2.1.5 → 3.0.0 | Breaking changes, major API changes, removed features |
| **skip-release** (or no label) | ⚪ Gray | No release | 2.1.5 → 2.1.5 | Docs only, CI changes, tests, or changes not ready to release |

**Note:** `skip-release` label is optional - if you don't add any label, the PR will be skipped for release automatically.

## Decision Tree

```
Should this PR trigger a release?
│
├─ NO → Don't add a label (or use 'skip-release')
│   Examples:
│   - Docs only changes
│   - README updates
│   - CI/workflow changes
│   - Tests only
│   - Work in progress you want to merge but not release yet
│
└─ YES → Does it break existing code?
    │
    ├─ YES → Use 'release:major'
    │   Examples:
    │   - Breaking API changes
    │   - Removed features
    │   - Changed method signatures
    │
    └─ NO → Does it add new features?
        │
        ├─ YES → Use 'release:minor'
        │   Examples:
        │   - New methods
        │   - New functionality
        │   - New API endpoints
        │
        └─ NO → Use 'release:patch'
            Examples:
            - Bug fixes
            - Performance improvements
            - Minor enhancements
```

## Examples

### release:patch
- Fix bug in `CubeService.get_dimension()`
- Improve error message
- Update dependency version
- Performance optimization
- Fix typo in code

### release:minor
- Add new method to `ChoreService`
- Add support for new TM1 REST API endpoint
- Add optional parameter to existing method (backwards compatible)
- New utility function

### release:major
- Remove deprecated method
- Change method signature (breaking)
- Rename class or module
- Change default behavior that breaks existing code
- Update minimum Python version

### No label (or skip-release)
- Update README
- Fix documentation typo
- Update GitHub Actions workflow
- Add or update tests (no code changes)
- Add code comments
- Refactoring that you want to accumulate before releasing
- Any change you're not ready to release yet

## Default Behavior

If **NO label** is added → **NO RELEASE** (safe default)

To trigger a release, you **MUST** add one of: `release:patch`, `release:minor`, or `release:major`

## Priority

If multiple PRs are merged in one day with different labels, the **highest priority label wins**:

1. **release:major** (highest priority)
2. **release:minor**
3. **release:patch** (lowest priority)

Example:
```
Monday:
  - PR #101: Docs update (no label) → skip
  - PR #102: New feature (release:minor) → minor
  - PR #103: Bug fix (release:patch) → patch

  Result: Next release will be MINOR (2.1.5 → 2.2.0)
         (all 3 PRs included in changelog)

Tuesday:
  - PR #104: Test update (no label) → skip
  - PR #105: CI fix (no label) → skip

  Result: NO RELEASE (no release labels found)
```

## Common Mistakes

❌ **DON'T**:
- Forget to add a release label when you want a release (will be skipped!)
- Use `release:minor` for bug fixes
- Add a release label to docs-only changes
- Mix breaking changes with features in same PR

✅ **DO**:
- Add appropriate release label before merging (if you want a release)
- Leave without label for docs, tests, CI, or work-in-progress
- Split breaking changes into separate PRs when possible
- Review the entire set of changes since last release
- Remember: **no label = no release** (safe default)

## Workflow Timeline

### Scenario 1: Release Day (PRs with release labels)

```
┌─────────────────────────────────────────────────────────┐
│ Throughout the Day                                       │
│ ─────────────────────────────────────────────────────── │
│ 10:00 AM  Merge PR #123 (release:patch) ✅              │
│ 2:00 PM   Merge PR #124 (release:minor) ✅              │
│ 5:00 PM   Merge PR #125 (no label - docs only)         │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 4:00 AM CET (Next Day) - Automated Workflow             │
│ ─────────────────────────────────────────────────────── │
│ 1. Check for new commits → Found 3 PRs                  │
│ 2. Determine version → MINOR (highest label found)      │
│ 3. Run full tests → 2-3 hours                           │
│ 4. Tests PASS → Continue                                │
│ 5. Bump version → 2.1.5 → 2.2.0                         │
│ 6. Create release → GitHub Release + changelog          │
│ 7. Publish → PyPI                                        │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 7:00 AM CET                                              │
│ ─────────────────────────────────────────────────────── │
│ ✅ Version 2.2.0 available on PyPI                       │
│ Users can: pip install --upgrade TM1py                   │
└─────────────────────────────────────────────────────────┘
```

### Scenario 2: No Release (no release labels)

```
┌─────────────────────────────────────────────────────────┐
│ Throughout the Day                                       │
│ ─────────────────────────────────────────────────────── │
│ 10:00 AM  Merge PR #126 (no label - tests)             │
│ 2:00 PM   Merge PR #127 (no label - CI fix)            │
│ 5:00 PM   Merge PR #128 (skip-release - docs)          │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 4:00 AM CET (Next Day) - Automated Workflow             │
│ ─────────────────────────────────────────────────────── │
│ 1. Check for new commits → Found 3 PRs                  │
│ 2. Check for release labels → NONE found                │
│ 3. Skip release ⏭️                                       │
│ 4. Workflow completes (no version bump, no publish)     │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 7:00 AM CET                                              │
│ ─────────────────────────────────────────────────────── │
│ ℹ️  No release created (version remains 2.2.0)          │
│ Changes merged to master but not published to PyPI      │
└─────────────────────────────────────────────────────────┘
```

## Checking Labels via GitHub CLI

```bash
# View labels on a PR
gh pr view 123 --json labels

# Add label to PR
gh pr edit 123 --add-label "release:minor"

# Remove label from PR
gh pr edit 123 --remove-label "release:patch"
```

## Questions?

See the full documentation:
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
- [RELEASE_SETUP_GUIDE.md](../../RELEASE_SETUP_GUIDE.md)
- [RELEASE_AUTOMATION_PROPOSAL.md](../../RELEASE_AUTOMATION_PROPOSAL.md)
