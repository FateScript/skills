#!/usr/bin/env bash

# Link skill directories into a target agent's skills directory.
# Usage: ./link-skill.sh [kimi|claude|codex] [--dry-run]
#
# This repo is hierarchical. A directory is treated as a skill only when it
# contains SKILL.md, and the relative path is preserved in the target directory.
# Example: productivity/teach -> ~/.codex/skills/productivity/teach

set -euo pipefail

usage() {
    printf '%s\n' \
        'Usage: ./link-skill.sh [kimi|claude|codex] [--dry-run]' \
        '' \
        'Targets:' \
        '  kimi     ~/.kimi/skills (default)' \
        '  claude   ~/.claude/skills' \
        '  codex    ~/.codex/skills' \
        '' \
        'Options:' \
        '  -n, --dry-run   Print actions without changing files' \
        '  -h, --help      Show this help'
}

TARGET_TYPE="kimi"
DRY_RUN=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        kimi|claude|codex)
            TARGET_TYPE="$1"
            ;;
        -n|--dry-run)
            DRY_RUN=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Invalid argument: %s\n\n' "$1" >&2
            usage >&2
            exit 1
            ;;
    esac
    shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$TARGET_TYPE" in
    kimi)
        TARGET_DIR="$HOME/.kimi/skills"
        ;;
    claude)
        TARGET_DIR="$HOME/.claude/skills"
        ;;
    codex)
        TARGET_DIR="$HOME/.codex/skills"
        ;;
esac

if [ -n "${SKILLS_TARGET_DIR:-}" ]; then
    TARGET_DIR="$SKILLS_TARGET_DIR"
fi

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '[dry-run] %q' "$1"
        shift
        while [ "$#" -gt 0 ]; do
            printf ' %q' "$1"
            shift
        done
        printf '\n'
    else
        "$@"
    fi
}

ensure_parent_dir() {
    local parent_dir="$1"
    local rel_parent="${parent_dir#"$TARGET_DIR"/}"
    local current="$TARGET_DIR"
    local old_ifs="$IFS"
    local part

    [ "$parent_dir" != "$TARGET_DIR" ] || return 0

    IFS='/'
    for part in $rel_parent; do
        IFS="$old_ifs"
        current="$current/$part"

        if [ -L "$current" ]; then
            local link_target
            link_target="$(readlink "$current")"
            if [[ "$link_target" == "$SCRIPT_DIR"/* ]]; then
                run rm -f "$current"
            else
                printf 'Skip: parent path is a symlink not owned by this repo: %s -> %s\n' "$current" "$link_target" >&2
                return 1
            fi
        fi

        if [ -e "$current" ] && [ ! -d "$current" ]; then
            printf 'Skip: parent path exists but is not a directory: %s\n' "$current" >&2
            return 1
        fi

        if [ ! -d "$current" ]; then
            run mkdir -p "$current"
        fi

        IFS='/'
    done
    IFS="$old_ifs"
}

link_skill() {
    local skill_dir="$1"
    local rel_path="${skill_dir#"$SCRIPT_DIR"/}"
    local target_link="$TARGET_DIR/$rel_path"
    local parent_dir

    parent_dir="$(dirname "$target_link")"

    if ! ensure_parent_dir "$parent_dir"; then
        return 0
    fi

    if [ -L "$target_link" ]; then
        local current_target
        current_target="$(readlink "$target_link")"
        if [ "$current_target" = "$skill_dir" ]; then
            printf 'Unchanged: %s\n' "$rel_path"
            return 0
        fi
        run rm -f "$target_link"
        run ln -s "$skill_dir" "$target_link"
        printf 'Updated:   %s\n' "$rel_path"
        return 0
    fi

    if [ -e "$target_link" ]; then
        printf 'Skip: target already exists and is not a symlink: %s\n' "$target_link" >&2
        return 0
    fi

    run ln -s "$skill_dir" "$target_link"
    printf 'Created:   %s\n' "$rel_path"
}

printf 'Linking %s skills\n' "$TARGET_TYPE"
printf 'Source: %s\n' "$SCRIPT_DIR"
printf 'Target: %s\n' "$TARGET_DIR"
if [ "$DRY_RUN" -eq 1 ]; then
    printf 'Mode:   dry-run\n'
fi
printf '\n'

if [ ! -d "$TARGET_DIR" ]; then
    run mkdir -p "$TARGET_DIR"
fi

if [ -d "$TARGET_DIR" ]; then
    printf 'Cleaning broken links owned by this repo...\n'
    while IFS= read -r link; do
        link_target="$(readlink "$link")"
        if [ ! -e "$link" ] && [[ "$link_target" == "$SCRIPT_DIR"/* ]]; then
            run rm -f "$link"
            printf 'Removed:   %s\n' "${link#"$TARGET_DIR"/}"
        fi
    done < <(find "$TARGET_DIR" -type l -print)
    printf '\n'
else
    printf 'Cleaning skipped because target directory does not exist yet.\n\n'
fi

skill_count=0
while IFS= read -r skill_md; do
    skill_dir="$(dirname "$skill_md")"
    rel_path="${skill_dir#"$SCRIPT_DIR"/}"

    if [[ "$rel_path" == .* || "$rel_path" == */.* ]]; then
        continue
    fi

    skill_count=$((skill_count + 1))
    link_skill "$skill_dir"
done < <(
    find "$SCRIPT_DIR" \
        \( -path "$SCRIPT_DIR/.git" -o -path "$SCRIPT_DIR/.claude-plugin" \) -prune \
        -o -type f -name 'SKILL.md' -print | sort
)

if [ "$skill_count" -eq 0 ]; then
    printf 'No skills found under %s\n' "$SCRIPT_DIR"
    exit 1
fi

printf '\nDone. Linked %d skill(s).\n' "$skill_count"
