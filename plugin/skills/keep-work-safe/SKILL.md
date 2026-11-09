---
name: keep-work-safe
description: Keep video work from being lost in a Claude Code cloud session, where the container can restart without warning and roll its disk back. Use from the first minute of any long cloud job, and again right after a restart.
---

# Keep your work safe in a cloud session

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

## What this skill does

It gives you the habits and small scripts that stop a restart, a hook, another session or a one-line mistake from costing you hours. The rule underneath all of them:

**Only what is pushed to the remote is sure to survive.**

For example, a container can restart in the middle of a render and come back as an older snapshot of its disk. That can take the render, the working video files, the transcripts, your scratch pages and a finished commit that was not pushed. In one such case the code came back from the file edits in the session's log, and everything else took an hour and a half to make again.

## When to use it (and when not to)

Use it in every cloud session that runs for more than a few minutes, or makes something that took real work.

You need less of this on your own computer, where nothing rolls back. The ideas still help.

## What you need before you start

- A git repository with a remote you can push to. Check: `git remote -v` and `git branch --show-current`. If you have none, see "If there is no repository" below.

- Git and bash. A cloud session has them.

- Python 3 for the wait in the save script. Check: `python3 --version`.

No key is needed, and nothing here costs money.

**What happens to a cloud container.** These facts held when this was written:

| Event | Running processes | Files | Unpushed commits |
|---|---|---|---|
| Worker restart | Killed, `nohup` included | Usually survive | Usually survive |
| Container rebuild or restart | Killed | Can roll back to an older snapshot. `node_modules`, the scratchpad and anything outside git can go. | Can go |
| A command passes the limit | A foreground command moves to the background at its timeout, and stops 30 minutes later. A background command gets 30 minutes, or up to 2 hours if you start it with `timeout: 7200000` | Survive | Survive |

Both things happen in practice. A restart can wipe the work, or drafts that were never committed can survive it. You cannot tell which you will get, so plan for the worse one.

## Steps

### First, save the files in this guide

`my-video` below stands for your project folder. A `cd` may not carry over from one Bash call to the next, so each command starts with its own.

Do not retype the long files. They are in this skill's `files` folder. This copies them all into your folder and keeps any file already there.

```bash
cd my-video
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/keep-work-safe"
cp -rn "$S/files/." . 2>/dev/null; test -e "save.sh" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

It saves `save.sh`, `queue.sh` and `where-am-i.sh`.

### If there is no repository

Check first:

```bash
cd my-video
git rev-parse --is-inside-work-tree
```

`fatal: not a git repository` means nothing can be pushed, so the rest of this guide cannot protect the work. A real session began this way. Tell the user plainly, and early:

> Right now your work lives only on this computer, so a restart could lose it. The files you uploaded are safe on the upload page. To protect the work too, connect a GitHub repository when you start a session, and I'll save there. For now I'll keep going, and I'll put each finished version on a page, so you always have a copy.

Then do these three things:

- **Put each finished version on a delivery page,** because that survives a restart. It is the only copy that does.

- **Keep `PROJECT.md` up to date,** so that you can pick up the work if the files survive.

- **Start a local repository, if you want an undo history.** It does not protect against a rebuild, and `save.sh` will say so each time:

```bash
cd my-video
git init -q
git config user.name >/dev/null || git config user.name "Video project"
git config user.email >/dev/null || git config user.email "video@example.invalid"
```

### Step 1. Save with one command: commit by path and push together

A commit that is not pushed can vanish. So never do one without the other. Name each path: `git add -A` can sweep in another agent's half-written file or a huge video.

Before your first push, check the repository is private (`gh api repos/OWNER/REPO --jq .visibility` if you have `gh`, taking OWNER/REPO from `git remote -v`. `gh repo view` fails in a cloud session, because the session's GitHub proxy refuses GraphQL). If it is public or you cannot tell, ask the user before you push anything of theirs.

`save.sh`, which the copy step puts in your folder:

```bash
# In this skill's files folder: files/save.sh (64 lines).
```

```bash
cd my-video
bash save.sh "voice track for chapter 2, with its transcript" scripts/chapter2.py transcripts/chapter2.json
```

It does these things:

- **Commits only the paths you name**, even if something else is already staged. That is what `git commit -- paths` means.

- **Refuses a file over 95 MB**, because GitHub refuses a file over 100 MB, and a refused file can block every push after it.

- **Pushes in the same command.** On a failure it waits 2, 4, 8, then 16 seconds and tries again. If the remote has moved on, it rebases first (`--autostash` keeps your other changes).

- **Undoes hook damage**, in the safe way described in Step 7.

Commit the script itself first, so it comes back after a rollback.

Tested on a Mac against a local bare repository: a staged and a dirty stranger file stayed out of the commit; a hook's change to a clean file was restored, and a file that was already dirty was left alone; two planted push failures were retried and then succeeded; a push rejected because the remote had moved rebased and went through; a 96 MB file was refused; a path with a space worked. **Not run on Linux**, and not run against GitHub itself.

**Save often.** During a long run, commit and push about every 30 minutes, and whenever something took real work to make.

### Step 2. Decide what goes in git

| Keep in git | Why |
|---|---|
| Scripts, including one-off ones you may run again | They are the recipe. |
| Transcripts and word timings | They can take an hour to make. |
| Edit data: cuts, chapters, captions, shot lists | This is the real work of an edit. |
| Prompts, briefs and the words of the script | You cannot regenerate your own thinking. |
| Small images and audio that the video needs | Below 100 MB each. |
| A `README` for each big file: where it came from, its size and SHA-256 | So you can tell that a re-fetched file is the same. |
| Your notes, in `PROJECT.md` (Step 4) | So the next session can continue. |

| Do not keep in git | Why | So do this instead |
|---|---|---|
| Any file over 100 MB | GitHub refuses it. | Keep a recipe that rebuilds it, and a record of where it came from. |
| Finished videos in `out/` | Too big, and they can be rebuilt | **Deliver soon.** Until then a finished film exists only in this container. |
| `node_modules`, bundles, chunks, caches | They can be rebuilt | Keep the setup script in git. |
| Keys | Secret | Environment variables only. |

A batch of 58 finished films came to about 2.1 GB. Files like that sit only in a gitignored folder until they are delivered.

**Files you left in a gitignored folder are not saved, and git will not warn you.** A scratchpad is not saved either, and a container rebuild can wipe it. Check what git will never save:

```bash
git status --ignored --short | grep '^!!'
git check-ignore -v path/to/file
```

The second prints the rule that hides the file. It prints nothing if the file is not ignored. If something there took work to make, move it, then save it.

### Step 3. Make long work resumable

Every long job should be safe to run twice. Two habits make this so:

1. **Write to a `.part` file, then rename.** A half-written file must never look like a whole one.

2. **Write a `.done` marker only after the job has succeeded.** A rerun skips what has a marker.

Example jobs file. Each line is a name and a command, with `{out}` where the output goes:

```text
chapter1 ffmpeg -v error -y -i raw/chapter1.mov -c:v libx264 -g 25 -f mp4 {out}
chapter2 ffmpeg -v error -y -i raw/chapter2.mov -c:v libx264 -g 25 -f mp4 {out}
```

Save this as `queue.sh`
```bash
#!/usr/bin/env bash
# A queue that is safe to run again. Each line of the jobs file is one job:
#
#   <name> <the command, with {out} where the output file goes>
#
#   bash queue.sh jobs.txt work-folder
#
# A job counts as done only when its command exits 0. Its output is written to a
# .part file first and renamed, so a half-written file is never taken for a whole
# one. After a restart, run the same command again: finished jobs are skipped.
set -u
jobs_file=$1
work=$2
mkdir -p "$work"
failed=0
while read -r name cmd; do
  [ -n "$name" ] || continue
  if [ -f "$work/$name.done" ]; then
    echo "skip $name (done)"
    continue
  fi
  part="$work/$name.part.mp4"
  rm -f "$part"
  echo "run  $name"
  # </dev/null matters: ffmpeg reads stdin, and would eat the rest of the jobs file.
  if bash -c "${cmd//\{out\}/$part}" </dev/null >"$work/$name.log" 2>&1; then
    mv "$part" "$work/$name.mp4"
    date > "$work/$name.done"
    echo "done $name"
  else
    echo "FAIL $name, see $work/$name.log"
    failed=$((failed + 1))
  fi
done < "$jobs_file"
echo "QUEUE-END failed=$failed"
[ "$failed" = 0 ]
```

```bash
cd my-video
mkdir -p out; bash queue.sh jobs.txt out/working > out/queue.log 2>&1
```

Run it with `run_in_background: true` and `timeout: 7200000`, because the Bash tool stops a foreground command at 10 minutes. After a restart, or at the 2-hour limit, run the same line again. Tested on a Mac: three jobs and one that failed on purpose. The failure was reported and did not stop the others, and on the second run the three were skipped, while the broken one was tried again and failed again.

The job commands are examples. A real job may write something other than an MP4: change the `.part.mp4` and `.mp4` names in the script to match.

**To wait for it**, wait on the files. Do not grep a process list, and do not grep a log for a word someone else will choose: a watcher waiting for one word misses a line worded another way. Bare `sleep` is blocked, so use a Monitor until-loop:

```bash
cd my-video
until grep -q '^QUEUE-END' out/queue.log; do sleep 30; done
```

### Step 4. Keep a project note

Keep one short file called `PROJECT.md` that a stranger could continue from, and save it with your work. After a restart, a new session reads this first. If the project already has one, add to it.

Here is an invented example. Change it to fit:

```markdown
# Bridge film

## The brief
A 12-minute film on how a bridge was built, for a local history group.

## What the user decided
- 2026-11-09: Calm look, teal and white.

## Where we are
Rendering the final film in chunks, 6 of 14 done. To resume, run the same `python3 render-chunks.py ...` command. The script changes are pushed. Next: master the sound, check the frames, send it to the user.
Updated 2026-11-09 14:20.

## Files that are not in git
- talk.mp4, 142 MB, sha256 abc123..., from the upload page
```

Update it before you start anything long, and whenever the plan changes. Write times from the `date` command, not from memory.

### Step 5. After a restart, look before you do anything

Do not assume anything survived, and do not assume anything is gone. This script reports what is there.

Save this as `where-am-i.sh`
```bash
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
```

```bash
cd my-video
bash where-am-i.sh
```

Tested on a Mac against a local bare repository: it printed the branch, the unpushed count, the ignored files and `PROJECT.md`. **Not run on Linux.**

Then recover in this order:

1. **Read `PROJECT.md`** and the output above. Check the last commit against what you remember.

2. **Stop any leftovers.** Check `ps`. Write patterns as `[r]emotion render`, because `pgrep -f` and `pkill -f` can match their own command line, so a wait loop waits on itself forever, and a `pkill` can kill your own shell (exit 144).

3. **Run your setup script again.** `node_modules` and tools may be gone.

4. **Rerun your resumable jobs.** They skip what is finished.

5. **Check what you are unsure of** against the source. A half-written file can look complete. A commit message can claim work that is not in it, for example when a checkout has already undone the change. Check with `git show --stat HEAD`.

6. **Re-make derived work, and compare it.** See the next step.

If source edits were lost and not committed, your session's log may still hold them, and you can replay the file edits it recorded. It is a last resort, because everything that was not a file edit stays lost.

### Step 6. Re-create derived work, and compare

Most work in a video job comes from something else: a transcript from a recording, an edit from a transcript. If you have the inputs and scripts, you can make it again. Then you can compare it, and that tells you the recipe is sound.

For example, after a restart you run a speech-to-text model again over a whole recording. If it gives the same number of words as the lost transcript, and the edit script then gives the same number of frames, the work lost was only time.

Keep a short record in git that lets you make that check:

```bash
cd my-video
wc -w transcripts/talk.txt > transcripts/talk.check
shasum -a 256 transcripts/talk.txt >> transcripts/talk.check
```

Some tools do not repeat exactly, so compare counts when the bytes differ, and look at what changed. If a result does not match, tell the user.

### Step 7. Handle commit hooks with care

A commit hook is a script that runs when you commit. It may reformat files you did not touch, across a whole folder, and it may do that on every commit.

**The trap in the fix.** The obvious fix is to restore every file outside your own paths. That silently undoes any real change that was sitting there uncommitted. So:

**Restore only what was clean before the commit.** A file that was already dirty may be another session's work.

```bash
cd my-video
git diff --name-only | sort > /tmp/before.txt
git add path/to/my-file && git commit -m "my change" -- path/to/my-file
git diff --name-only | sort | comm -13 /tmp/before.txt - | while IFS= read -r f; do git checkout -- "$f" </dev/null; done
git status --short
```

`save.sh` does this. Note what it cannot do: if the hook also changed a file that was already dirty, the hook's changes stay mixed in with the other work. Look at those with `git diff` and sort them out by hand.

Other hook traps:

- **A hook can refuse every commit for a reason unrelated to your work,** such as another file failing its check. Then nothing gets pushed. Report it to the user. Do not edit the unrelated file just to get past it.

- **With many agents in one checkout,** each commit's hook can reformat others' half-written files. There, `git commit --no-verify` with the checks run by hand is the safer way. Alone, let the hook run.

- **A formatter can change your own text.** It may read `___` in a Markdown script as emphasis and make it bold. Escaping it as `\_\_\_` keeps it.

- **Run `git status` after every commit.**

### Step 8. Never use the one-line rewrite

This one line empties the file:

```python
open(p, 'w').write(f(open(p).read()))
```

Python runs `open(p, 'w')` first, and that empties the file before the read happens. Tested: 6 bytes went in, and 0 bytes came out. In a shared file, this also wipes another agent's uncommitted work.

Do this. It also leaves the old file whole if the script dies midway:

```python
import os, pathlib
p = pathlib.Path('notes.txt')
text = p.read_text()
tmp = p.with_suffix('.tmp')
tmp.write_text(text.upper())
os.replace(tmp, p)
```

Never rewrite a shared file that holds another agent's uncommitted work. If you have already emptied a file, restore the committed copy with `git checkout -- <file>`. If a permission check refuses you, stop and tell the user what happened.

### Step 9. Stop `ffmpeg` eating your loops

ffmpeg reads stdin, so inside this loop it swallows the rest of the job list:

```bash
while read -r job; do
  ffmpeg -i "$job.mov" "$job.mp4"     # eats the next lines of jobs.txt
done < jobs.txt
```

The loop ends early, or runs with wrong names, and no error appears. Reproduced on a Mac: five jobs named `first` to `fifth` came out as `first`, `econd`, `hird`, `ourth`, `ifth`.

The fix is `</dev/null` on every command in the loop. With it, the same test ran all five with the right names:

```bash
while read -r job; do
  ffmpeg -i "$job.mov" "$job.mp4" </dev/null
done < jobs.txt
```

From Python, use `stdin=subprocess.DEVNULL`. Any program that reads stdin can do this, so give it to voice tools and others too.

### Step 10. Know which branch your work is on

A cloud session is usually given one branch. Your work goes there.

- **Check it before you commit:** `git branch --show-current`.

- **Do not switch branches in a checkout other agents are using.** They all see the same files.

- **Push only to your branch.** A permission check may refuse a push or a merge. Do not work around it. Tell the user and ask.

- **Work on a branch does not reach `main` by itself.** A later session that starts from `main` will not see your work, your scripts or your notes. So when you finish, tell the user in plain words: "This is on branch X. It is not on main yet." Offer the exact merge step.

### Step 11. Check for other sessions before big work

Two sessions can end up doing the same work. A session can also decide that something cannot be done while a working recipe sits on another branch.

Before a big job, look:

```bash
cd my-video
git fetch -q origin
git branch -r --sort=-committerdate --format='%(committerdate:relative)  %(refname:short)' | head -10
git log --all --since='7 days ago' --format='%h %cr %D %s' | head -30
```

To read a file on another branch without switching:

```bash
cd my-video
git show origin/some-branch:path/to/file
```

If someone is working on the same thing, stop and ask the user. Before you decide that something cannot be done, search the other branches for it.

## How to talk to the user

- Say what is safe and what is not, in plain words: "The edit and the scripts are saved online. The finished film is only on this temporary computer until I send it to you."

- Tell them right away if a restart cost work, and how much: "The computer restarted. The scripts are safe. I need about 20 minutes to make the working copies again."

- Ask one question at a time, with a recommendation. For example: "A tool wants to change ten files I did not touch. I recommend leaving them out of this save. OK?"

- Ask before you delete anything you did not make, or anything that cannot be rebuilt.

- At the end, name the branch and what is not yet merged.

## What Anthropic's docs add

Checked November 2026. Look again if it matters.

- After a few minutes with no activity, a session's computer pauses with its files saved. A paused computer can later be reclaimed.
- When a session is reopened after that, the conversation comes back. Running commands and background helpers do not, so run them again.
- The session's GitHub proxy refuses tags and branch deletions. Save work on a branch.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `remote: error: File x is 150.00 MB; this exceeds GitHub's file size limit of 100.00 MB`, or similar | A big file is in a commit | Keep it out of git. If it is only in your newest local commit, undo that commit with `git reset --soft HEAD~1`, unstage the file, and commit again. |
| `Updates were rejected because the remote contains work that you do not have locally.` | Someone pushed first | `git pull --rebase --autostash origin <branch>`, then push. `save.sh` does this. |
| `CONNECT tunnel failed, response 403`, or a network error, on a push | The network, or the proxy | Retry at 2, 4, 8 and 16 s. If it stays refused, tell the user. |
| Files you did not touch show as modified after a commit | A hook reformatted them | Step 7. Restore only what was clean before. |
| A file is suddenly empty | The one-line rewrite | Step 8. `git checkout -- <file>`. |
| Your loop stopped early with no error | `ffmpeg` ate stdin | Step 9. |
| A wait loop never ends | `pgrep -f` matched itself, or you are grepping for a word nobody wrote | Use `[r]emotion render`, or wait on a file. |
| `pkill` killed your own shell (exit 144) | The pattern matched your own command line | Use a bracket pattern or a PID. |
| "worker was restarted", and jobs are gone | Restart | Step 5. |
| `node_modules` is gone, and commits you remember are gone | Disk rollback | Step 5. Whatever was pushed is on the remote. |
| A file that looks whole fails with `moov atom not found` | It was copied or read while still being written | Remake it, using a `.part` file and rename. |
| A commit message claims a change the diff does not hold | A checkout or restore undid it first | `git show --stat HEAD` after each commit. |
| `sleep` is refused | Bare `sleep` is blocked | A Monitor until-loop, or a bounded check loop. |

## How to check it worked

These should all be true at any moment you might lose the container:

```bash
cd my-video
branch=$(git branch --show-current)
git fetch -q origin
echo "not pushed: $(git rev-list --count origin/$branch..HEAD)"     # must be 0
git status --short                                                   # nothing you care about
git status --ignored --short | grep '^!!'                            # nothing here took real work
git log origin/$branch -1 --format='%h %ar %s'                       # your last save, on the remote
```

For the real test, read back from the remote and not from your disk:

```bash
cd my-video
git show "origin/$(git branch --show-current):PROJECT.md"
```

A stranger should be able to continue from that note, with the scripts in the branch, and with a fresh container. For a finished film, the check is that the user has it. Ask them to confirm it opens and plays. Nobody in a cloud session can hear it, so ask them to listen as well.
