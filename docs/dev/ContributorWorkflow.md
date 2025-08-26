<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Development Workflow

- See the [Contributing Page](../../CONTRIBUTING.md) for general information about contributing.
- See the [Development Setup Page](Setup.md) for how to set up your development environment.

## Branching Strategy

- **Main Branch** (`master`): Stable, production-ready code. Only updated by the project maintainers.
- **Development Branch** (`staging`): Active development happens here. Pull requests target this branch, with maintainers controlling merges.
- **Feature Branches**: Contributors will fork the repo and branch off `staging` branch for their work.  Anyone can fork the repository, create a feature branch and submit PRs against the `staging` branch.

## Making Changes - Overview

- Always work off the latest `staging` branch to avoid merge conflicts.
- Create an issue and a branch (issues highly encouraged for most PRs).
- Do your thing and add to and/or change the code: use clear commit messages.
- Create a PR: should be focused on a single feature or fix.

## Ensure Your Fork is in Sync

Switch to your local copy of staging branch:
``` shell
git checkout staging
```

Fetch the latest changes from upstream:
``` shell
git fetch upstream
```

Merge upstream changes into your fork's dev branch:
``` shell
git merge upstream/staging
```

Push the updated dev branch to your fork:
``` shell
git push origin staging
```

### Ensure New Dependencies in Sync

You should also ensure you are in sync with with any packages or database schema changes before beginning work.
``` shell
cd $PROJ_DIR
cd src
pip install -r hi/requirements/development.txt
./manage.py migrate
```

## Create an Issue and Branch

All PRs are encouraged to be associated with an issue and the branch should use the issue number in its name. For minor fixes, or test-only changes, skipping an issue is OK, but anything more substantial should have an issue for discussions and reference.

Issues (and hence branches) come in a few flavors with associated conventions.  In general, a branch will have both the issue number and a user-chosen, short mnemonic to be slightly more descriptive. Here are the conventions:

| Type    | Issue? | Branch                          | Notes |
|----------|-----|-----------------------------------|---------------|
| feature  | YES | feature/$(ISSUE_NUM}-${MNEMONIC}  | New Development |
| bugfix   | YES | bugfix/$(ISSUE_NUM}-${MNEMONIC}   | Bug Fixes |
| docs     | YES | docs/$(ISSUE_NUM}-${MNEMONIC}     | Documentation |
| ops      | YES | ops/$(ISSUE_NUM}-${MNEMONIC}      | Non-app, deployment, etc. |
| tests    | NO  | tests/${MNEMONIC}                 | For test-only changes |
| refactor | YES | refactor/$(ISSUE_NUM}-${MNEMONIC} | Only if no new behaviors |
| tweak    | NO  | tweak/${MNEMONIC}                 | For small, obvious PRs |

If you are contributing something new, without an existing issue, please create an issue first using the appropriate template: feature, bugfix, etc.. It is generally always better to think about what you are about to do before doing it. Creating an issue is a forcing function for thinking through and communicating your plans.

Once your code is up-to-date, an issue number exists and a mnemonic chosen, you can create your local branch off the current staging branch:
``` shell
git checkout -b feature/$(ISSUE_NUM}-${MNEMONIC} upstream/staging
```

## Do Your Thing

- Make your changes to the code.
- Test your changes locally (and add unit tests).
- Stage changes: `git add .`
- Commit changes: `git commit -m "Add feature: [brief description]"`
- Push branch to your fork: `git push origin feature/$(ISSUE_NUM}-${MNEMONIC}`

## Submit a Pull Request (PR)

- Go to your fork on GitHub: https://github.com/${YOURUSERNAME}/home-information
- Click the "Compare & pull request" button that appears after your push.
- Ensure the base repository is set to `cassandra/home-information -> staging`
- Ensure the compare branch is set to: `${YOURUSERNAME}/home-information -> feature/${YOUR_FEATURE_NAME}`
- Fill out the PR template (describe what your change does).
- If applicable, add a line that says which ticket it closes. i.e., "Closes #39"
- Submit the PR and wait for review!

## PR Reviews

During PR review, a decision will be made on whether to squash or rebase:
- **Squash and Merge (default)**: For most PRs
- **Rebase and Merge**: for well-structured PRs that need commit history

## Post-PR Cleanup

- After merging, you should consider deleting the branch to keep your forked repository clean.
- Get your local and forked `staging` branch up to date with the upstream changes (see above).
