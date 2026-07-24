# Branch Protection Policy

This document outlines the branch protection rules for the Media Downloader repository.

## Protected Branches

### `main` Branch

The `main` branch contains production-ready code and is protected with the following rules:

- **No direct pushes**: All changes must come through pull requests
- **No force pushes**: History rewriting is not allowed
- **No deletions**: Branch cannot be deleted
- **Required pull request reviews**:
  - At least 1 approval from a maintainer
  - Dismiss stale reviews when new commits are pushed
  - Require review from code owners (if applicable)
- **Required status checks**:
  - All CI tests must pass
  - Linting (ruff) must pass
  - Type checking (basedpyright) must pass
  - Build verification for Windows and Linux
- **Required linear history**: Merge commits are not allowed
- **Restrict push access**: Only maintainers can push (after PR approval)

### `development` Branch

The `development` branch is the integration branch and has these protections:

- **No direct pushes**: All changes must come through pull requests
- **No force pushes**: History rewriting is not allowed
- **Required pull request reviews**:
  - At least 1 approval required
  - New commits dismiss stale reviews
- **Required status checks**:
  - All CI tests must pass
  - Linting and type checking must pass

## Branch Workflow

### Feature Development

```
feature/your-feature  →  development  →  main (via release PR)
```

1. Create feature branch from `development`
2. Develop and test locally
3. Create PR targeting `development`
4. After approval, merge into `development`
5. When ready for release, create PR from `development` to `main`

### Hotfix Process

```
hotfix/critical-fix  →  main  →  development (backmerge)
```

1. Create hotfix branch from `main`
2. Fix the critical issue
3. Create PR targeting `main`
4. After merge, backmerge to `development`

## Release Process

1. **Prepare release**:
   - Update CHANGELOG.md
   - Update version in relevant files
   - Update documentation

2. **Create release PR**:
   - From `development` to `main`
   - Title: "Release v1.x.x"
   - Include release notes summary

3. **After merge**:
   - CI/CD creates release artifacts
   - GitHub release is published
   - Backmerge to `development`

## Enforcement

These rules are enforced both by:
- GitHub's branch protection settings (automatic)
- Code review practices (manual)

Violations will be caught during the PR review process.

## Questions?

If you need an exception to these rules, please:
1. Open an issue explaining the situation
2. Discuss with maintainers
3. Get explicit approval before proceeding
