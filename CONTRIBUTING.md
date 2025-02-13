<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Contributing

We welcome contributions! Follow these guidelines to get started.

## Project and Goals

_TBD_

[Road Map](RoadMap.md)

## How to Contribute

users v. coder v. graphic designers

### User Contributions

### Graphic Design Contributions

### Code Contributions

See the [Development Page](docs/Development.md) for how to set up your development environment.

1. Open an issue describing your proposed change.
2. Fork the repository.
3. Create a feature branch.
4. Make your changes.
5. Submit a pull request to the `develop` branch.

Code should be tested before approval.
Squash and merge is preferred for a cleaner commit history.

 
#### Branching Strategy

- Main Branch (`master`): Stable, production-ready code.
- Development Branch (`develop`): Active development happens here.
- Feature Branches (feature/some-feature): Contributors should branch off `develop`.

Example:
``` shell
git checkout -b feature/new-feature develop
git commit -m "Add new feature"
git push origin feature/new-feature
```


#### Making Changes

: Guidelines on:

Code style (and how to check it)
Commit message format (use a clear and consistent format)
Testing (how to run tests and write new ones)
Documentation (how to update documentation)


#### Coding Style

We mostly adhere to PEP8 but we strongly disagree with its broadly accepted coding guidelines around spaces.  Spaces are great visual delimiters and greatly enhance readability. The deviations we make are shown in this Flake8 config file for what is ignored.

``` shell
[flake8]
max-line-length = 110

# Things I disable:
#
# E129 - visually indented line with same indent as next logical line
# D203 -
# E201 - whitespace after brackets
# E202 - whitespace before brackets
# E203 -
# E221 - multiple spaces before operator
# E231 - 
# E251 - unexpeced whitespace around keyword parameters
# W293 - blank line contains whitespace
# W291 - white space at end of line
# W391 - blank line at end of file
# W503 - line break before binary operator

ignore = E129,D203,E201,E202,E203,E221,E231,E251,W293,W291,W391,W503
```



#### Submitting a Pull Request: Explain the PR process:

- Open a PR against the `develop` branch.
- Write a clear and descriptive PR title and description.
- Include screenshots or GIFs if relevant.
- Address any feedback on the PR.

#### Code of Conduct

- be respectful
- be inclusive and welcoming
- be responsive
- provide feedback
- keep your ego in check
- keep PRs focused: one feature/fix per PR.


#### Licensing

See the [License Page](LICENSE.md).
