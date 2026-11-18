#!/usr/bin/env bash
# Find what agent sessions left behind in the folder that holds your clones; remove it on --remove.
# Usage: stale-worktrees.sh [--remove] [<folder>]
#   <folder> defaults to the folder holding the current repo's main clone, such as ~/src.
# One tab-separated line per finding:
#   stale|removed <path> <why>  a worktree that holds no work: unlocked, no uncommitted or
#                               untracked file, no checkout or commit in a day, its commit has
#                               landed (it is in origin's default branch, or GitHub says a pull
#                               request merged that exact commit), and no process in it.
#                               Removal deletes its local branch too.
#   keep <path> <why>           a worktree that may hold work or be in use. Never removed.
#   empty|rmdir <path>          a folder directly in <folder>, empty for a day
#   orphan <pid> <command>      a process running from a folder under <folder> that is gone.
#                               Never stopped: stop it only if your session started it.
# The day covers a peer that made a worktree and has not yet changed a file in it.
# Every subprocess costs about 10 ms under macOS bash, so the work per worktree stays small,
# and the process snapshot runs while git does its part.
set -euo pipefail

usage() { printf 'usage: stale-worktrees.sh [--remove] [<folder>]\n' >&2; }

remove=0
if [ "${1:-}" = --remove ]; then
	remove=1
	shift
fi
if [ "$#" -gt 1 ]; then
	usage
	exit 2
fi
if [ "$#" -eq 1 ]; then
	folder=$1
else
	common=$(git rev-parse --git-common-dir 2>/dev/null) || {
		usage
		exit 2
	}
	folder=$(cd "$common/../.." && pwd -P)
fi
folder=$(cd "$folder" && pwd -P)
tab=$'\t'
day=1440 # minutes

# The process snapshot starts first and runs in the background: each process's command line,
# and its working folder from lsof. lsof reads only your own processes, the only ones it may
# read, which halves its time. It is the slowest step.
snap=$(mktemp -d)
trap 'rm -rf "$snap"' EXIT
ps -ww -A -o pid=,ppid=,command= >"$snap/ps" & # -ww: Linux ps cuts a piped line at 80 columns
ps_job=$!
lsof_job=
if command -v lsof >/dev/null; then
	lsof -nPlbw -a -u "$(id -u)" -d cwd -Fpn >"$snap/lsof" 2>/dev/null &
	lsof_job=$!
fi

# Succeeds when file or folder $1 changed within the last day.
recent() { [ -n "$(find "$1" -maxdepth 0 -mmin -"$day")" ]; }

# Every linked worktree of every clone in <folder>: repo, path, commit, branch.
list=
shopt -s nullglob
for repo in "$folder"/*/; do
	repo=${repo%/}
	[ -d "$repo/.git" ] || continue
	list+=$(git -C "$repo" worktree list --porcelain | awk -v r="$repo" '
		function emit() { if (n++ && p != "") print r "\t" p "\t" h "\t" b; p = h = b = "" }
		/^worktree / { p = substr($0, 10) }
		/^HEAD / { h = substr($0, 6) }
		/^branch refs\/heads\// { b = substr($0, 19) }
		/^$/ { emit() }
		END { if (p != "") emit() }')$'\n'
done

base_of() { # <repo>: origin's default branch, or nothing
	local base
	base=$(git -C "$1" symbolic-ref -q --short refs/remotes/origin/HEAD || true)
	if [ -z "$base" ] && git -C "$1" rev-parse -q --verify origin/main >/dev/null; then
		base=origin/main
	fi
	printf '%s' "$base"
}

# Sets $why and succeeds when commit $head of the worktree on $branch has landed in $repo.
landed() {
	local n
	if [ -n "$base" ] && git -C "$repo" merge-base --is-ancestor "$head" "$base"; then
		why="its commit is in $base"
		return 0
	fi
	if [ -n "$branch" ] && command -v gh >/dev/null; then
		n=$(cd "$repo" && gh pr list --head "$branch" --state merged --json headRefOid \
			--jq "[.[] | select(.headRefOid == \"$head\")] | length" 2>/dev/null || true)
		if [ "${n:-0}" -gt 0 ] 2>/dev/null; then
			why="a merged pull request holds its commit"
			return 0
		fi
	fi
	why="it has commits not in ${base:-a default branch}"
	return 1
}

# The git checks, for $repo $path $head $branch $base. A worktree that passes them all is a
# candidate: its "repo<tab>path<tab>why<tab>branch" line goes on $candidates. The branch, which
# a detached worktree lacks, comes last: read joins two tabs in a row into one.
candidates=
check() {
	local admin
	if [ ! -d "$path" ]; then
		if [ "$remove" = 1 ]; then
			git -C "$repo" worktree prune
			printf 'removed\t%s\tits folder was gone\n' "$path"
		else
			printf 'stale\t%s\tits folder is gone\n' "$path"
		fi
		return
	fi
	# The lock file, not `worktree list`: git before 2.31 lists no lock. A worktree's `.git`
	# file reads "gitdir: <its folder in the main clone>".
	admin=
	if [ -f "$path/.git" ]; then
		read -r _ admin <"$path/.git" || true
		case $admin in /*) ;; *) admin=$path/$admin ;; esac
	fi
	if [ -z "$admin" ]; then
		printf 'keep\t%s\tno .git file\n' "$path"
		return
	fi
	if [ -f "$admin/locked" ]; then
		printf 'keep\t%s\tlocked: %s\n' "$path" "$(tr '\n' ' ' <"$admin/locked" | sed 's/ *$//')"
		return
	fi
	if [ -n "$(git -C "$path" status --porcelain)" ]; then
		printf 'keep\t%s\tuncommitted or untracked files\n' "$path"
		return
	fi
	# Its reflog moves on every checkout and commit; HEAD alone, on a checkout.
	if recent "$admin/logs/HEAD" 2>/dev/null || recent "$admin/HEAD"; then
		printf 'keep\t%s\tchecked out or committed to within a day\n' "$path"
		return
	fi
	if ! landed; then
		printf 'keep\t%s\t%s\n' "$path" "$why"
		return
	fi
	candidates+="$repo$tab$path$tab$why$tab$branch"$'\n'
}

last=
while IFS=$tab read -r repo path head branch <&3; do
	[ -n "$path" ] || continue
	if [ "$repo" != "$last" ]; then
		base=$(base_of "$repo")
		last=$repo
	fi
	check
done 3<<<"$list"

# The snapshot, without this script and the processes it started. lsof exits 1 when it cannot
# read some process, so its status is not the snapshot's.
wait "$ps_job"
procs=$(awk -v me=$$ '$1 != me && $2 != me' "$snap/ps")
cwds=
if [ -n "$lsof_job" ]; then
	wait "$lsof_job" || true
	cwds=$(awk -v me=$$ '/^p/ { p = substr($0, 2) } /^n/ && p != me { print p "\t" substr($0, 2) }' \
		"$snap/lsof")
fi

# One pass for every candidate: "pid<tab>path" for each one a process works in or names on its
# command line.
busy=$(awk -F'\t' '
	FILENAME == ARGV[1] { if ($2 != "") paths[++n] = $2; next }
	FILENAME == ARGV[2] {
		for (i = 1; i <= n; i++)
			if (!(paths[i] in pid) && ($2 == paths[i] || index($2, paths[i] "/") == 1)) pid[paths[i]] = $1
		next
	}
	{
		split($0, f, " ")
		for (i = 1; i <= n; i++) if (!(paths[i] in pid) && index($0, paths[i] "/")) pid[paths[i]] = f[1]
	}
	END { for (p in pid) print pid[p] "\t" p }
' <(printf '%s' "$candidates") <(printf '%s\n' "$cwds") <(printf '%s\n' "$procs"))

while IFS=$tab read -r repo path why branch <&3; do
	[ -n "$path" ] || continue
	pid=
	while IFS=$tab read -r p w; do
		if [ "$w" = "$path" ]; then pid=$p; fi
	done <<<"$busy"
	if [ -n "$pid" ]; then
		printf 'keep\t%s\tprocess %s runs in it\n' "$path" "$pid"
	elif [ "$remove" = 0 ]; then
		printf 'stale\t%s\t%s\n' "$path" "$why"
	elif ! git -C "$repo" worktree remove "$path"; then
		printf 'keep\t%s\tgit worktree remove refused\n' "$path"
	else
		if [ -n "$branch" ]; then
			git -C "$repo" branch -q -D "$branch"
		fi
		printf 'removed\t%s\t%s\n' "$path" "$why"
	fi
done 3<<<"$candidates"

for dir in "$folder"/*/; do
	dir=${dir%/}
	[ -z "$(ls -A "$dir")" ] || continue
	! recent "$dir" || continue
	if [ "$remove" = 1 ]; then
		rmdir "$dir"
		printf 'rmdir\t%s\n' "$dir"
	else
		printf 'empty\t%s\n' "$dir"
	fi
done

while read -r pid _ cmd; do
	exe=${cmd%% *}
	case $exe in
	"$folder"/*) [ -e "$exe" ] || printf 'orphan\t%s\t%s\n' "$pid" "$cmd" ;;
	esac
done <<<"$procs"
while IFS=$tab read -r pid cwd; do
	case $cwd in
	"$folder"/*) [ -d "$cwd" ] || printf 'orphan\t%s\tworking folder %s is gone\n' "$pid" "$cwd" ;;
	esac
done <<<"$cwds"
