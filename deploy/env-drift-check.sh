#!/bin/bash
# Verify that install.sh, deploy/env-generate.py, and local.env.example all
# declare the same set of environment variable names. Drift in any direction
# indicates a missed update and is treated as a build failure.
#
# Compared as sets (sorted, unique) — values are ignored; only names matter.
set -euo pipefail

cd "$( dirname "${BASH_SOURCE[0]}" )/.."

extract_var_names_from_env_text() {
    # Read an env-file-shaped stream from stdin, emit just the variable names
    # (lines matching ^KEY=...). Comments and blank lines are dropped.
    grep -E '^[A-Z][A-Z0-9_]+=' | sed 's/=.*//' | sort -u
}

install_sh_names=$( bash install.sh --list-env-vars )
env_generate_names=$( python3 deploy/env-generate.py --example | extract_var_names_from_env_text )
example_file_names=$( extract_var_names_from_env_text < local.env.example )

show_diff_and_fail() {
    local label_a="$1" set_a="$2" label_b="$3" set_b="$4"
    echo
    echo "Env-var drift detected between ${label_a} and ${label_b}:"
    diff -u \
        <( printf '%s\n' "${set_a}" ) \
        <( printf '%s\n' "${set_b}" ) \
        | sed "s|^---.*|--- ${label_a}|; s|^+++.*|+++ ${label_b}|" || true
    echo
    echo "Fix: update whichever source is behind so all three declare the same set."
    exit 1
}

if [[ "${install_sh_names}" != "${env_generate_names}" ]]; then
    show_diff_and_fail \
        "install.sh --list-env-vars" "${install_sh_names}" \
        "deploy/env-generate.py --example" "${env_generate_names}"
fi

if [[ "${install_sh_names}" != "${example_file_names}" ]]; then
    show_diff_and_fail \
        "install.sh --list-env-vars" "${install_sh_names}" \
        "local.env.example" "${example_file_names}"
fi

count=$( printf '%s\n' "${install_sh_names}" | wc -l | tr -d '[:space:]' )
echo "env-drift-check: OK (${count} variables consistent across install.sh, env-generate.py, and local.env.example)"
