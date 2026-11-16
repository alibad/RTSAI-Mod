#!/bin/bash

rtsai_source_status_allowed() {
	local status="$1"
	[ -z "${status}" ] && return 0
	[ -z "$(printf '%s\n' "${status}" | LC_ALL=C grep -vE '^ D \.github/workflows/[A-Za-z0-9._-]+\.ya?ml$' || true)" ]
}

rtsai_workflow_deletions_json() {
	git -C "$1" diff --name-only --diff-filter=D -- .github/workflows/ |
		awk 'BEGIN { printf "[" } { printf "%s\"%s\"", separator, $0; separator = ", " } END { printf "]" }'
}
