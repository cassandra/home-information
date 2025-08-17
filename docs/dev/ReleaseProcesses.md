<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Release Process

## Preamble 

- Releases are only done by the core maintainers with direct repo access and not done on a fork of the repo.
- All work is done in feature branches that get merged into the staging branch.
- The master branch is the release branch.
- The release process is mainly about merging the accumulated PRs in staging into master.

## Step by Step

- Change to `staging` branch locally.
- Get your local `staging` branch fuly in sync with remote/upstream.
- Bump the version number in the file `HI_VERSION` as appropriate: major, minor or suffix.
- Commit the version number change directly to the upstream `staging` branch with "Bump version number to vX.X.X".
- Change to local `master` branch.
- Get your `master` branch fully in sync with remote/upstream.
- Merge from `staging` into `master`
- Push `master` to remote/upstream.
- Create GitHub release.
- Add/create tag with next version number in the form `vX.X.X`.
- Set Target = `master`
- Use "Generate release notes" button anmd edit as needed.
- Use "Set as the latest release" (usually)
- "Publish Release" button.
