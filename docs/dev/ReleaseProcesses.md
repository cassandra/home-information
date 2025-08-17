<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Release Process

## Overview

Releases are managed through a structured branch workflow where:
- All development work occurs in feature branches
- Feature branches are merged into the `staging` branch via pull requests
- The `master` branch serves as the release branch
- Releases involve merging accumulated changes from `staging` into `master`

## Prerequisites

- Direct repository access (core maintainers only)
- Local development environment properly configured
- All target changes already merged into `staging` branch

## Pre-Release Verification

Before starting the release process, verify the staging branch is ready:

1. **Confirm CI Status**: Ensure all GitHub Actions checks are passing on `staging`
2. **Run Local Validation**: Execute tests and linting as a sanity check
   ```bash
   make check
   ```
3. **Review Recent Changes**: Check recent commits and merged PRs for any concerns

## Release Steps

### 1. Prepare Staging Branch
- Switch to `staging` branch locally
- Sync your local `staging` branch with remote/upstream:
  ```bash
  git checkout staging
  git pull github staging
  ```

### 2. Update Version Number
- Bump the version number in `HI_VERSION` file following semantic versioning
- Commit the version change directly to upstream `staging`:
  ```bash
  git add HI_VERSION
  git commit -m "Bump version number to vX.X.X"
  git push github staging
  ```

### 3. Merge to Master
- Switch to local `master` branch and sync with remote:
  ```bash
  git checkout master
  git pull github master
  ```
- Merge from `staging` into `master`:
  ```bash
  git merge staging
  git push github master
  ```

### 4. Create GitHub Release
1. Navigate to the GitHub repository releases page
2. Click "Create a new release"
3. **Tag**: Create new tag in format `vX.X.X`
4. **Target**: Set to `master` branch
5. **Title**: Use the tag name (e.g., `v1.2.3`)
6. **Description**: Use "Generate release notes" button and edit as needed
7. **Settings**: 
   - Check "Set as the latest release" (typically)
   - Leave "Set as a pre-release" unchecked (for stable releases)
8. Click "Publish Release"

## Future Considerations

### Version Bumping Criteria
**TBD** - Establish clear guidelines for when to increment:
- Major version (breaking changes)
- Minor version (new features, backward compatible)
- Patch version (bug fixes, backward compatible)

### Rollback Procedures
**TBD** - Document rollback procedures for failed releases:
- How to revert problematic releases
- Communication protocols for rollback situations
- Testing procedures post-rollback

## Notes

- **Changelog Management**: Release notes are generated from GitHub's automatic changelog feature rather than maintaining a separate changelog file
- **Deployment**: Current releases are distributed as downloadable packages for self-installation
- **Quality Assurance**: GitHub branch protection rules enforce passing tests and code quality checks before PRs can merge to `staging`
