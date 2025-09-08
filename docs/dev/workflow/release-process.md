# Release Process

## Release Overview

Releases follow structured branch workflow:
- Development work in feature branches
- Feature branches merged to `staging` via PRs
- `master` branch serves as release branch
- Releases merge accumulated changes from `staging` to `master`

## Prerequisites

- Direct repository access (core maintainers only)
- Local development environment configured
- All target changes merged into `staging` branch

## Pre-Release Verification

1. **Confirm CI Status**: Ensure GitHub Actions pass on `staging`
2. **Run Local Validation**: `make check`
3. **Review Recent Changes**: Check commits and merged PRs

## Release Steps

### 1. Prepare Staging Branch

```bash
git checkout staging
git pull origin staging
```

### 2. Update Version Number and CHANGELOG.ms

```bash
# Edit HI_VERSION file with new version
# Add line to CHANGELOG.md file with short description
git add HI_VERSION  CHANGELOG.md
git commit -m "Bump version number to vX.X.X"
git push origin staging
```

### 3. Merge to Master

```bash
git checkout master
git pull origin master
git merge staging
git push origin master
```

### 4. Create GitHub Release

Using GitHub CLI (preferred for automation):

```bash
gh release create vX.X.X --title "vX.X.X" --generate-notes --latest
```

Or via GitHub web interface:
1. Navigate to repository releases page
2. Click "Create a new release"
3. **Tag**: `vX.X.X` (create new)
4. **Target**: `master` branch
5. **Title**: Use tag name
6. **Description**: Use "Generate release notes"
7. **Settings**: Check "Set as latest release"
8. Click "Publish Release"

#### Check GitHub Actions

- Check that ZIP file was successfully built
- Check that Docker image was built.

### 5. Validate Install URL Works

Make sure that the published ZIP install link works and that it is at least 10MB in size and no more than 100MB in size.

Test the manual instalation ZIP file.
```bash
curl -L https://github.com/cassandra/home-information/releases/latest/download/home-information.zip -o home-information.zip
```

## 6. Cleanup

For safety, move back to staging branch and get latest tags.
```bash
git checkout staging
git fetch --tags
```

This is where the automated release process ends.

## Post-Release Tasks (Manual)

### Validate Install Script Works

Test the single-command installation script (this must be done manually):
```
curl -fsSL https://raw.githubusercontent.com/cassandra/home-information/master/install.sh | bash
```

### Post-Release Monitoring

**Critical**: Monitor the release for the first few hours after publication:
- Check GitHub Issues for user reports
- Monitor GitHub Discussions for problems

**If critical issues are discovered**, see [Rollback Process](rollback-process.md) for immediate response procedures.

### Docker Image Cleanup (Periodic)

**Every few releases**, clean up old Docker images to prevent clutter:
1. Go to: `https://github.com/cassandra/home-information/pkgs/container/home-information`
2. Review old versions and delete:
   - Versions older than 6 months (except major releases)
   - Keep at least 10 recent versions for rollback capability
   - Always keep `latest` and current stable version
3. This helps with storage management and reduces user confusion

## Version Bumping Criteria

**TBD** - Establish guidelines for:
- **Major version**: Breaking changes
- **Minor version**: New features (backward compatible)
- **Patch version**: Bug fixes (backward compatible)

## Rollback Procedures

**TBD** - Document rollback procedures:
- Revert problematic releases
- Communication protocols
- Post-rollback testing

## Notes

- **Changelog Management**: Generated from GitHub's automatic changelog
- **Deployment**: Releases distributed as downloadable packages
- **Quality Assurance**: Branch protection enforces tests and code quality

## Related Documentation
- Workflow guidelines: [Workflow Guidelines](workflow-guidelines.md)
- **[Rollback Process](rollback-process.md)** - Emergency rollback procedures for problematic releases
