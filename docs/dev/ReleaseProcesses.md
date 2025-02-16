<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Release Process

- Change to `staging` branch locally.
- Get your local `staging` branch fuly in sync with remote/upstream.
- Bump the version number in the file `HI_VERSION` as appropriate: major, minor or suffix.
- Commit the version number change directly to the upstream `staging` branch with "Bump version number to vX.X.X".
- Chnage to local `master` branch.
- Get your `master` branch fully in sync with remote/upstream.
- Merge from `staging` into `master`
- Push `master` to remote/upstream.
- Create GitHub release using that same tag.
- Add tag with next version number in the form `vX.X.X`.
- Add release notes: look at PR and commit histories.
