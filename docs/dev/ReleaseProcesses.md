<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Release Process

- Get your `staging` branch fuly in sync.
- Bump the version number in the file `HI_VERSION` as appropriate: major, minor or suffix.
- Commit the version number change directly to the `staging` branch with "Bump version number to vX.X.X".
- Create pull request from `staging` into `master`.
- Ensure checks pass and get an approver.
- Merge the pull request.
- Tag the `master` branch with next version number in the form `vX.X.X`.
- Create GitHub release using that same tag.
- Add release notes: look at PR and commit histories.
