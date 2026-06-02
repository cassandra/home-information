#!/bin/bash
# Launch Claude Code from the project root with the dev environment active.
# Activates the venv, loads dev env vars, ensures gh auth, then starts claude.

PROJ_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

export PATH="$HOME/.local/bin:$PATH"
cd "$PROJ_ROOT"
. "$PROJ_ROOT/dev/init-env-dev.sh"

# Check GitHub login status and re-auth if necessary.
if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  if [[ -n "${GH_TOKEN:-${GITHUB_TOKEN:-}}" ]]; then
    printf '%s' "${GH_TOKEN:-$GITHUB_TOKEN}" | gh auth login --hostname github.com --with-token
  else
    # interactive web login
    gh auth login --hostname github.com --web
  fi
else
  echo "✓ GitHub Authorization"
fi

claude
