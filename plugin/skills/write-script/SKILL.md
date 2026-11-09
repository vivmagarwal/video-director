---
name: write-script
description: Write or revise a video script with the user, for the ear, at the right length and pace, with no invented facts and with quotes kept word for word. Use it before any narration is voiced or recorded.
---

# Write a script

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

## What this skill does

It helps you and the user write words that will be spoken in a video. You end with:

- a script in plain text, split into short blocks, one file per block
- a word count and an estimated length
- a list of where every fact came from
- a check that no quote changed

The rules here came from past narrated lesson videos, each checked by the person who asked for them. The numbers say where they came from. Your user's taste beats all of them.

Here is the difference it makes. The first version reads fine and sounds dead. The second one a person would actually say. Both are invented for this example:

```text
Before:  In this video, we will explore the importance of task hygiene, which is
         a key component of effective team management.

After:   Last March, a new manager opened a spreadsheet and found forty-one open
         tasks. Nobody had touched them for six weeks.
```

## When to use it (and when not to)

Use it when:

- the user wants a narrated video and has a topic, notes, a lesson or an article
- someone has written a script and it needs to work when spoken
- an agent or a person has revised a script, and you need to check that nothing true got changed

Do not use it when:

- the video is an edit of a real recording. The words are already said, so you are choosing cuts, not writing
- the video has no speech at all

## What you need before you start

No tools are needed beyond Python 3, for the two check scripts. Check it with `python3 --version`. They use only the standard library, and no network or key.

**Tested how.** Both check scripts were run on an Apple Silicon Mac with Python 3.10 on 2026-11-09, on invented scripts. They were not run on Linux. Nobody has measured how much these writing rules help.

You do need these from the user. Ask for them one at a time (see "How to talk to the user"):

1. **The source material.** Their notes, lesson, article, data. Everything true in the script comes from here.
2. **Who it is for.** One sentence.
3. **What the viewer should do afterwards.** One action.
4. **How long.** Or how fast. See step 3.
5. **Their style, if they have one.** A guide, a video they like, a script they liked. Use that over these rules.

## Steps

### 0. Save the tools

Keep the script in one project folder. Every step below that runs a command starts with `cd /path/to/project`: put your real folder there, as a full path. A `cd` from an earlier command may not carry over.

Do not retype the long files. They are in this skill's `files` folder. This copies them all into your folder and keeps any file already there.

```bash
cd /path/to/project
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/write-script"
cp -rn "$S/files/." . 2>/dev/null; test -e "check-script.py" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

It keeps any file that already exists, so your work is safe.

### 1. Agree the approach before you write

Tell the user, in two or three lines, what you plan: the opening, the shape, the length. Wait for a yes. Rewriting a script is cheap. Voicing it, cutting picture to it, and then rewriting it is not.

### 2. Make a fact sheet

Read the source. List each fact you may use, with where it came from:

```text
forty-one open tasks      notes.md, line 3
six weeks untouched       notes.md, line 3
"Which project tools do you really use?"    notes.md, line 8, exact quote
```

**Never invent a fact, number, name, date, study or quote.** If the source does not say it, leave it out or ask. "Experts say" and "studies show" with no source named do not go in. Do not state an organisation's policy: name who owns it.

If you need an example and the source has none, you may write one. It must be plainly labelled as written to teach with, in the words and on screen. For example: "Here is a made-up example." Do not give made-up people realistic-sounding results and let them pass as real.

If something is missing, write `[NEED: how many users, from whom?]` in your draft and ask. A gap is better than a guess. That placeholder will fail the check in step 7 until it is filled, which is what you want.

### 3. Work out how many words

**Pace is a floor the user can change.** The defaults:

| Video | Pace of the voice |
|---|---|
| A normal video | about 144 words a minute |
| A short intro of 2 to 3 minutes | about 180 words a minute |
| What the user asks for | that |

Then: **words = minutes × words a minute.**

| Length | Words at 144 | Words at 180 |
|---|---|---|
| 1 minute | 144 | 180 |
| 2 minutes | 288 | 360 |
| 2.5 minutes | 360 | 450 |
| 3 minutes | 432 | 540 |
| 5 minutes | 720 | |
| 10 minutes | 1,440 | |

**A finished video carries fewer words than this**, because pictures need room: held diagrams, title cards, pauses. So for a video with a lot of held picture, plan on fewer. Examples from past narrated lessons, counted across the whole finished video:

| Finished length | Spoken words | Words a minute |
|---|---|---|
| About 5 minutes | about 750 | about 140 |
| 8.4 minutes | about 1,120 | about 133 |
| About 10 minutes | about 1,300 | about 130 |

Short intros of about 2 to 2.5 minutes came out at about 180 words a minute of narration, because people who saw slower versions asked for faster speech. Your user may want something else, so show them one early.

Estimate time as: **seconds = words ÷ words a minute × 60, plus the seconds of held picture you plan.** As a rough starting point, allow 1 second after each block, and more for a title card. Example: 300 words in five blocks at 144 is 125 seconds, plus 5 seconds, about 130 seconds.

A pace number depends on how it is measured. Measure a voice from its first word to its last word, not on the file's length, because a generated voice file can have up to a second of silence at each end.

### 4. Choose a shape

A shape is the order of the parts. These worked. They are starting points, so change them to suit the topic.

**For a lesson of about 10 minutes.** This shape was used on several lesson videos of about that length:

1. **The opening story.** One person, one moment. Something went wrong or surprised them.
2. **What it is.** Say it plainly. Show it on screen.
3. **What counts as proof.** How would someone know this is real?
4. **The trap.** The mistake people really make. Say it is normal, then correct it. One line acted out helps here, labelled as an example.
5. **The questions.** Usually three questions to ask, each with a one-line explanation of what it means.
6. **Worked examples.** Usually two. Walk each one through the questions, one question at a time.
7. **One step to do.** One thing, this week, with the exact words to say or the exact thing to do.
8. **Optional: a fill-in template** held on screen as the last card, so people can pause and copy it.

One piece of feedback changed that order: **share the questions before the examples.** People could not follow the examples until they knew what was being tested. So: questions first, then work the examples through them.

**For a short intro of 2 to 3 minutes.** Not measured as a shape, but a sensible start:

1. A person, a moment or a number.
2. What this course or product is, plainly.
3. One example of what you get from it.
4. One thing to do next.

**One idea per video.** If you have two, make two videos.

### 5. Write it for the ear

**Start with something real.** A person, a moment or a number. Never open with a definition or with "In this video we will explore". The first seconds decide whether people stay, so say what this is early too.

**Give the example first, then name the rule.** A good example has a name or a role, a date and a cost.

```text
Rule first:     Unused tasks create hidden costs for teams.
Example first:  She closed nineteen tasks in one afternoon, and nobody noticed.
                If nobody notices when a task dies, it was already dead.
```

**Use plain, short sentences.**

- Use short common words: "use", not "utilize"; "help", not "facilitate".
- Keep sentences short and active. A person does the verb.
- Put one idea in each sentence. As a rough limit, split anything over about 25 words.
- Explain each new word in the sentence that first uses it.
- When the viewer should say or do something, write the exact words.
- Give every number a direction and an owner: not "20%", but "her costs fell by a fifth".
- Quote official wording exactly, then say it again in plain words.
- Keep one word for one thing. If the word is "task", keep saying "task". Do not rotate synonyms.

**Cut these:**

- Filler: "it's worth noting", "it's important to", "at its core", "in today's world", "let's dive in", "in order to".
- Inflated words: delve, leverage, robust, seamless, empower, elevate, transformative, pivotal, realm, tapestry, "a testament to".
- "It's not X, it's Y." Just say Y.
- Setups: "Here's the thing", "What nobody tells you", "The best part is".
- Tails that pretend to explain: ", highlighting...", ", underscoring...", ", showcasing...".
- Telling people something matters. Show why it matters instead.
- Stacked fragments: "That's it. That's the whole thing."
- Poetic lines, slogans, wordplay, clever closing lines. A real person's quoted words are fine.
- Dashes used for rhythm. Use a full stop or a comma.

**End on one thing to do.** No recap. Nothing that says "to wrap up". Make it small enough to do this week, and say exactly what it is.

**Write it the way it is said.** The script goes straight to a voice, and usually to the captions too.

- Numbers in words: "four hundred kilometres", not "400 km".
- No markdown, backticks, tags or headings in the voice files.
- Punctuation and block breaks are your only pause controls. A dash interrupts and three dots trail off, and both change the timing.
- Read it aloud, or have it voiced, and rewrite anything that trips.

**If there is text on screen,** make every line on screen a whole sentence a stranger gets on one read. A title is a label that says what is inside, not a teaser. Show the thing, then name it.

### 6. Split it into blocks

Put one beat of picture in each file: `n1.txt`, `n2.txt`, and so on. Keep each under about 70 words.

The reason is time. A block can be voiced again alone. One big file means voicing everything again for one changed word, and every cut in the video moves.

A blank line inside a file makes a paragraph, which most voice tools read with a longer pause.

### 7. Run the check

`check-script.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/check-script.py (94 lines).
```

```bash
cd /path/to/project
python3 check-script.py narration/
python3 check-script.py narration/ --wpm=180        # for a short intro
```

```text
n1.txt: 26 words, about 11 s
n2.txt: 21 words, about 9 s
TOTAL: 47 words in 2 blocks. At 144 words a minute, plus 1.0 s per block: about 0 min 21 s. 0 to fix, 0 to look at.
```

A `FIX` line breaks the voice or the captions. Fix it. A `LOOK` line is for you to judge: `delve` in a quote stays, for example. This check catches form. It cannot tell you that a script is good.

### 8. Protect the quotes after every revision

**An agent can change a quote and nobody notices.** Here is an invented example. Asked to tighten a script, an agent turns "Which project tools" into "What project tools", and swaps "IT" for "tech support". The script reads just as well. Only comparing it with the source catches it.

So after every revision, by you or by anyone else, compare the script with its source.

`protect-quotes.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/protect-quotes.py (59 lines).
```

```bash
cd /path/to/project
cat narration/*.txt > all-blocks.txt
python3 protect-quotes.py source.md all-blocks.txt
```

This is what it printed in a test, on that invented example:

```text
FAIL quote not in the source: "What project tools do you really use"
     nearest in the source:  "Which project tools do you really use"
LOOK quote from the source not in the script: "Which project tools do you really use"
LOOK number not in the source: 5
LOOK name or capitalised word not in the source: Maria

Every changed passage (source, then script):
  ...She asked: ["Which] -> ["What]
  ...really use?" She [paused.] -> [paused, and Maria looked up.]
  ...She paused. The [IT] -> [tech support]
  ...IT team had [3] -> [5]

1 changed quote(s).
```

Note the line with `[IT] -> [tech support]`. That change was not inside quote marks, so only the list of changed passages shows it. **Read every changed passage.** It takes a minute. The script only finds quotes marked with quote marks, and a number written as a word, such as "three", will show as changed from "3". That is expected.

### 9. Show the user, then hand it on

Show the script as text, with the word count and the length. Ask them to read the facts in particular. Keep the fact sheet beside the script in your project, and commit both.

Before your first push, check the repository is private (`gh api repos/OWNER/REPO --jq .visibility` if you have `gh`, taking OWNER/REPO from `git remote -v`. `gh repo view` fails in a cloud session, because the session's GitHub proxy refuses GraphQL). If it is public or you cannot tell, ask the user before you push anything of theirs. A script can hold words the user has not made public.

```bash
cd /path/to/project
git add narration facts.md && git commit -m "Script v1" && git push
```

In a cloud session, only what is pushed is sure to survive a restart. A commit hook may reformat files you did not touch, so run `git status` after a commit, and restore only the files that were clean before it.

When a script goes on to be voiced, a word the voice cannot say may need a spoken spelling, such as `project{prodject}` in a voice tool that supports it. Keep the written spelling in your source of truth. That respelling is why `check-script.py` and `protect-quotes.py` both ignore anything in braces straight after a word.

## How to talk to the user

- Plain words. One question at a time. Give a recommendation with each question. For example: "How long should it be? I suggest about 3 minutes, around 430 words, since this is one idea."
- Ask for the source before you write anything. If they have none, ask them to tell you the story in their own words, and use those.
- Before you write, give the plan in two or three lines and wait for their OK.
- Show the first block early, ideally voiced, before writing all of it. Pace and tone are easier to hear than to describe.
- Say where you added or guessed anything. Never let a guess pass as a fact.
- Ask before going slower than the default pace. Ask whether people in the video should be named, or stay unnamed.
- Pause for their OK at three points: the plan, the first block, the finished script.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `FAIL quote not in the source` | A quote changed, or the source spells it differently | Restore the source's exact words. If the voice cannot say a word, respell it for the voice only |
| `LOOK number not in the source` | A number was invented or changed, or you wrote a word as a digit | Check the fact sheet. Remove it if it has no source |
| `LOOK name or capitalised word not in the source` | A name was invented, or it is just a capitalised word | Check. Remove an invented name |
| `FIX ... a backtick would be read aloud or dropped` | Markdown in a voice file | Take it out. These files are speech |
| `does not end on . ? or !` | A cut-off block | Finish the sentence |
| The script is far over length | Too many ideas | Cut an idea, not words. Make a second video |
| The voiced video runs longer than planned | Long pauses, or held picture you did not count | Measure the voice file, cut a block, or ask for a faster pace |
| People cannot follow a worked example | They do not know what is being tested | Give the questions before the examples |
| The script reads well and sounds stiff | It was written for the eye | Read it aloud, then shorten sentences and use the words you said |
| An opening starts with a definition | It is the easy way to start | Find the person, moment or number in your source |
| A captioned number looks odd, such as "forty-one" | It was written for the voice | Usually fine. If it matters, show the digits with text on screen |

## How to check it worked

1. `python3 check-script.py narration/` exits 0, and the total is near the length you agreed.
2. `python3 protect-quotes.py source.md all-blocks.txt` exits 0, and you read every changed passage.
3. Every fact in the script is on the fact sheet, with its source. Pick three at random and open the source to check.
4. Read the first and last blocks with no context. The first starts with a person, a moment or a number. The last gives one thing to do.
5. Read the whole script aloud, or listen to it voiced. A machine can count words. It cannot tell whether a line sounds natural. **The user has to say yes.**
