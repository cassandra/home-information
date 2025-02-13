<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Development Guidelines

## Coding Style

The project triued to adhere to PEP8 but we strongly disagree with the broadly accepted coding guidelines around spaces.  Spaces are great visual delimiters and greatly enhance readability. The whitespace deviations we make to PEP8 are shown in this Flake8 config file (`ignore`).

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

## Code Organization

_TBD_

## Testing Conventions

_TBD_

## Commit Messages

_TBD_

## PR Descriptions

_TBD_

## Documentation

_TBD_
