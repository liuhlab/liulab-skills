#!/usr/bin/env bash
# Shared assertion semantics for tests/eval.sh and tests/lint.sh.

eval_grep() { # <case-sensitive> <regex> <file>
  local sensitive="$1" pattern="$2" file="$3"
  if [ "$sensitive" = true ]; then
    grep -qE "$pattern" "$file"
  else
    grep -qiE "$pattern" "$file"
  fi
}

eval_skill_assert() { # <skill|!skill> <transcript>; print the reason on failure
  local spec="$1" transcript="$2" skill_name forbidden=false
  skill_name="$spec"
  if [ "${skill_name#!}" != "$skill_name" ]; then
    forbidden=true
    skill_name="${skill_name#!}"
  fi

  if [ "$forbidden" = true ]; then
    if python3 tests/eval_stream.py skill "$transcript" "$skill_name"; then
      printf 'invoked forbidden Skill %s\n' "$skill_name"
      return 1
    fi
    return 0
  fi

  if ! python3 tests/eval_stream.py skill "$transcript" "$skill_name"; then
    printf 'no Skill invocation for %s\n' "$skill_name"
    return 1
  fi
  return 0
}
