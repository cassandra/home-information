#!/bin/bash
cd ~/proj/hi
. ./init-env-dev.sh

# Check GitHub login status and re-auth if necessary.
# gh auth login
if ! gh auth status --hostname "$host" >/dev/null 2>&1; then
  if [[ -n "${GH_TOKEN:-${GITHUB_TOKEN:-}}" ]]; then
    printf '%s' "${GH_TOKEN:-$GITHUB_TOKEN}" | gh auth login --hostname "$host" --with-token
  else
    # interactive web login
    gh auth login --hostname "$host" --web
  fi
else
    echo "✓ GitHub Authorization"
fi

claude
