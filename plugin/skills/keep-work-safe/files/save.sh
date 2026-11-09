#!/usr/bin/env bash
# Commit these paths, and only these, then push in the same command.
#
#   bash save.sh "what changed" path1 path2 ...
#
# It refuses files over 95 MB, retries a failed push at 2, 4, 8 and 16 seconds,
# rebases once if the remote moved, and restores any file a commit hook changed
# that was clean before the commit. It never touches a file that was already dirty.
set -euo pipefail

msg=${1:?usage: save.sh "message" path...}
shift
[ "$#" -gt 0 ] || { echo "name the paths to commit" >&2; exit 2; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "this folder is not a git repository, so nothing was saved. See 'If there is no repository' in the guide." >&2; exit 2; }

branch=$(git branch --show-current)
[ -n "$branch" ] || { echo "not on a branch (detached HEAD), so nothing can be pushed" >&2; exit 2; }

big=$(find "$@" -type f -size +95M 2>/dev/null || true)
if [ -n "$big" ]; then
  printf 'too big for git (GitHub refuses a file over 100 MB):\n%s\n' "$big" >&2
  exit 2
fi

# Files that are changed right now, before the commit. A hook must not cost us these.
dirty_before=$(mktemp)
git diff --name-only | sort > "$dirty_before"

git add -- "$@"
if git diff --cached --quiet -- "$@"; then
  echo "nothing new to commit in those paths"
else
  # `-- paths` commits only these paths, even if something else is staged.
  git commit -q -m "$msg" -- "$@"
fi

# Files the hook changed: dirty now and clean before. Not one of ours, so put it back.
git diff --name-only | sort | comm -13 "$dirty_before" - | while IFS= read -r f; do
  echo "a hook changed $f; restoring it"
  git checkout -- "$f" </dev/null
done
rm -f "$dirty_before"

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "saved locally as $(git rev-parse --short HEAD). This repository has no remote, so a rebuild could still lose it."
  exit 0
fi
for wait in 2 4 8 16 stop; do
  if git push -q -u origin "$branch"; then
    echo "pushed $(git rev-parse --short HEAD) to origin/$branch"
    exit 0
  fi
  [ "$wait" = stop ] && break
  git fetch -q origin "$branch" 2>/dev/null || true
  if git rev-parse -q --verify "origin/$branch" >/dev/null &&
     ! git merge-base --is-ancestor "origin/$branch" HEAD; then
    echo "the remote moved; rebasing"
    git pull -q --rebase --autostash origin "$branch"
  fi
  echo "push failed; trying again in $wait s"
  python3 -c "import time; time.sleep($wait)"
done
echo "PUSH FAILED after 5 tries. The commit is local only." >&2
exit 1
