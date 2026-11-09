#!/usr/bin/env bash
# What survived? Run this first after a restart, or when you pick up someone's work.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "no git repository here: this work lives only on this computer"
  [ -f PROJECT.md ] && { echo "--- PROJECT.md"; cat PROJECT.md; }
  exit 0
fi
git fetch -q origin 2>/dev/null || echo "WARNING: git fetch failed; the remote view may be old"
branch=$(git branch --show-current)
echo "branch:          ${branch:-none (detached HEAD)}"
echo "last commit:     $(git log -1 --format='%h %ar %s' 2>/dev/null || echo none yet)"
if git rev-parse -q --verify "origin/$branch" >/dev/null; then
  echo "not pushed:      $(git rev-list --count "origin/$branch..HEAD") commit(s)"
  echo "remote is ahead: $(git rev-list --count "HEAD..origin/$branch") commit(s)"
else
  echo "not pushed:      this branch is not on the remote at all"
fi
echo "changed files:   $(git status --short | wc -l | tr -d ' ')"
git status --short | head -20
echo "--- ignored files, biggest first (git will never save these)"
git status --ignored --short | sed -n 's/^!! //p' | while IFS= read -r f; do du -sk "$f" 2>/dev/null; done | sort -rn | head -10
echo "--- other branches with recent work"
git branch -r --sort=-committerdate --format='%(committerdate:relative)  %(refname:short)' | head -8
echo "--- still running"
ps -A -o pid=,etime=,args= | grep -E '[r]emotion (render|still|bundle)|[f]fmpeg |[c]hrome-headless-shell.*--user-data-dir' | cut -c1-110 | head -10
for d in node_modules; do [ -d "$d" ] && echo "$d: there" || echo "$d: MISSING, run your setup again"; done
[ -f PROJECT.md ] && { echo "--- PROJECT.md"; cat PROJECT.md; }
exit 0
