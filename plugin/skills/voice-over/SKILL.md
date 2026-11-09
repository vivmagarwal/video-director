---
name: voice-over
description: Make narration for a video from a written script, free, on the machine you are on, with Kokoro. It writes an .mp3 and word-timed captions, and checks the speech by reading it back with offline Whisper. Use it when a video needs a voice and no recording exists.
---

# Voice over

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

## What this skill does

You give it a text file. It gives you two files beside it:

```text
n1.txt             the words, written by you
n1.mp3             the voice: mono, 44.1 kHz, levelled to -20 LUFS (a standard unit of loudness)
n1.captions.json   every word with its start and end time
```

The voice is **Kokoro**, an open text-to-speech model (Apache-2.0 licence). It needs no key and no account. After a one-time download it needs no network.

Here is one line of the captions file. This shape is the one Remotion's `@remotion/captions` package reads, so captions work with no conversion:

```json
{ "text": " March,", "startMs": 522, "endMs": 1022, "timestampMs": 772.0, "confidence": null }
```

Paid voices such as ElevenLabs are a public option. See "If the user wants a paid voice" near the end.

## When to use it (and when not to)

Use it when:

- a video needs narration and nobody has recorded any
- a video needs a few speakers with different voices
- the user has no budget, or has no key for a paid voice
- you are making a draft and may change the words many times, because a new take costs nothing

Do not use it when:

- the user has a real recording. Keep the person's voice: a transcript is what you need, not a new voice
- the user asks for a particular paid voice
- the language is not Spanish, French or English, unless you test it first. See "Other languages" near the end

Kokoro is not a person. Tell the user that plainly. It can misread names and it has no acting range. Many listeners will accept it for an explainer. Some will not, and only a person can judge that.

## What you need before you start

| You need | Check | Install |
|---|---|---|
| Python 3 with `venv` | `python3 -m venv --help` | Usually there already. Tested on Python 3.10 |
| ffmpeg | `ffmpeg -version` | `apt-get install -y ffmpeg`, if the machine lets you. Otherwise see below |
| curl and tar | `curl --version` | Usually there already |
| Network to PyPI and GitHub, once | see below | The user can open hosts in the cloud environment menu: Edit, then Network access |
| About 1.5 GB of free disk | `df -h ~` | See "How big it is" |

Test the network before you start. Hosts differ per environment and per date:

```bash
curl -sS -o /dev/null -m 15 -w '%{http_code}\n' https://pypi.org/simple/kokoro-onnx/
curl -sS -L -o /dev/null -r 0-10 -m 30 -w '%{http_code}\n' https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

A refusal reads `CONNECT tunnel failed, response 403` or `Host not in allowlist`. Any other status means the host answered. `200` or `206` means it works. A `504` means GitHub answered but had a bad moment. It happened while this skill was being tested, and it can last a long while on the big files, so wait some minutes and try again.

**The model comes from GitHub on purpose.** Most guides fetch Kokoro from Hugging Face. Cloud proxies often refuse Hugging Face, and GitHub releases have worked there.

**If there is no ffmpeg and `apt-get` is not allowed,** this gives you one from PyPI (checked on a Mac, not on Linux; it has every filter these scripts use):

```bash
python3 -m venv ~/ffmpeg-venv && ~/ffmpeg-venv/bin/pip install -q imageio-ffmpeg
export FFMPEG=$(~/ffmpeg-venv/bin/python -c "import imageio_ffmpeg as i; print(i.get_ffmpeg_exe())")
```

Both scripts below read `FFMPEG` if it is set.

### How big it is

Measured on a Mac on 2026-11-09:

| Item | Size |
|---|---|
| `kokoro-v1.0.onnx`, the model | 325 MB |
| `voices-v1.0.bin`, all voices | 28 MB |
| `kokoro-timed.onnx`, a copy `voice.py` writes on its first run | about 325 MB |
| Whisper `base.en`, for reading back | 209 MB download, about 150 MB once the unused parts are deleted |
| The Python environment | 280 MB |

### About cloud sessions

These held when this was written:

- A cloud session is a Linux x64 container with 4 cores, about 15 GB of memory, and no GPU. Kokoro runs on the CPU, so no GPU is needed.
- Everything outside git can vanish in a container rebuild. That includes `~/voice-tools`. If a script says `No model in`, run the setup again.
- Only what is pushed is sure to survive. Commit and push the `.txt`, `.mp3` and `.captions.json` files after each batch. They are small: 29 seconds of speech came to about 460 KB.
- The Bash tool times out at 10 minutes, and a background command stops after 30 minutes, or after up to 2 hours if you start it with `timeout: 7200000`. Run big batches in the background and wait on the log file, not with a bare `sleep`, which is blocked.

### Tested how

`voice.py`, `readback.py`, `readback-language.py` and the setup were tested on a Mac (macOS on Apple Silicon, Python 3.10, kokoro-onnx 0.6.1) on 2026-11-09. They were not run on Linux. An earlier version of the same method did run on a Linux cloud container, on an older kokoro-onnx. The paid voice section at the end was not run against the paid service.

## Steps

### 0. Save the tools

Work in one project folder. Every step below that uses a project file starts with `cd /path/to/project`: put your real folder there, as a full path. A `cd` from an earlier command may not carry over.

Do not retype the long files. They are in this skill's `files` folder. This copies them all into your folder and keeps any file already there.

```bash
cd /path/to/project
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/voice-over"
cp -rn "$S/files/." . 2>/dev/null; test -e "setup-voice.sh" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

It keeps any file that already exists, so your work is safe.

### 1. Set up once

The script just below is already saved, if you ran the copy step.

Save this as `setup-voice.sh`

```bash
#!/usr/bin/env bash
# One-time setup for free local narration. Safe to run again: it skips what exists.
# Everything goes in $VOICE_HOME (default ~/voice-tools), outside your project.
set -euo pipefail

VOICE_HOME="${VOICE_HOME:-$HOME/voice-tools}"
KOKORO=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
SHERPA=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models

# Download to a temporary name first, so a broken download is never mistaken for a finished one.
get() { [ -f "$2" ] || { curl -sSfL --retry 4 --retry-delay 5 -o "$2.part" "$1" && mv "$2.part" "$2"; }; }

mkdir -p "$VOICE_HOME/kokoro" "$VOICE_HOME/whisper"
[ -x "$VOICE_HOME/venv/bin/python" ] || python3 -m venv "$VOICE_HOME/venv"
# voice.py calls two private functions of kokoro-onnx, so the version is pinned.
"$VOICE_HOME/venv/bin/pip" install -q kokoro-onnx==0.6.1 soundfile onnx numpy sherpa-onnx

cd "$VOICE_HOME/kokoro"
get "$KOKORO/kokoro-v1.0.onnx" kokoro-v1.0.onnx
get "$KOKORO/voices-v1.0.bin" voices-v1.0.bin

cd "$VOICE_HOME/whisper"
if [ ! -d sherpa-onnx-whisper-base.en ]; then
	get "$SHERPA/sherpa-onnx-whisper-base.en.tar.bz2" base.tar.bz2
	tar xjf base.tar.bz2
	rm base.tar.bz2
	# Keep the small int8 model. readback.py does not use the two big ones.
	rm -f sherpa-onnx-whisper-base.en/base.en-encoder.onnx sherpa-onnx-whisper-base.en/base.en-decoder.onnx
fi

echo "ready: $VOICE_HOME/venv/bin/python"
```

Run it:

```bash
cd /path/to/project
bash setup-voice.sh
```

The last line reads `ready:` and gives the path to Python. Every command below uses that Python. Put your scripts in your project, not in `~/voice-tools`.

### 2. The two main scripts

The copy step has already saved these. They are here so that you can read them.

`voice.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/voice.py (259 lines).
```

`readback.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/readback.py (74 lines).
```

Do not save them in a folder that also holds a file called `segments.py`. See the trouble table for why.

### 3. Choose a voice with the user

Kokoro has 54 voices. List them with this:

```bash
~/voice-tools/venv/bin/python -c "import numpy as np, os; print(' '.join(sorted(np.load(os.path.expanduser('~/voice-tools/kokoro/voices-v1.0.bin')).keys())))"
```

The first two letters mean language and sex: `af` is American female, `am` American male, `bf` British female, `bm` British male. Other first letters are other languages, not tested here.

These are **examples only**, as starting points. The user's taste decides:

| Voice | What it is | Graded by others as |
|---|---|---|
| `af_heart` | American female | The best-graded voice |
| `af_bella` | American female | Close behind |
| `bf_emma` | British female | Good |
| `am_michael` | American male | Fair |
| `am_fenrir` | American male | Fair, and loud before levelling |
| `bm_george` | British male | Fair |

The grades are from the model's own voice list, as read in one review: `https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md`. Whisper understood every English voice in that review, so a transcript cannot rank them. A person's ear has to.

**Make an audition.** Write about 40 words that sound like the real video. Voice it in two or three voices. Send the files to the user and ask which they like:

```bash
cd /path/to/project
mkdir -p audition
cp sample.txt audition/heart.txt; cp sample.txt audition/emma.txt; cp sample.txt audition/michael.txt
PY=~/voice-tools/venv/bin/python
$PY voice.py audition/heart.txt --voice=af_heart --target=144 </dev/null
$PY voice.py audition/emma.txt --voice=bf_emma --target=144 </dev/null
$PY voice.py audition/michael.txt --voice=am_michael --target=144 </dev/null
```

If the user has a reference, such as "like this video", ask for it and try to match it.

**Do not mix voices inside a series.** A listener hears a new voice as a new person. Pick one narrator for the whole series and write the voice and speed down. If a video has speakers too, give each a voice of their own, and never the narrator's. A blend of voices and a slight change of pitch are possible too, but they were not tested with this script.

### 4. Test every name and hard word first

Kokoro reads a word it does not know by English spelling rules. In one batch, about four in ten first names came out wrong. Fix them before you voice anything.

Say each name in a short line, then read it back:

```bash
cd /path/to/project
PY=~/voice-tools/venv/bin/python
echo 'This is Thandor. Thandor runs the night shift.' > name-test.txt
$PY voice.py name-test.txt --voice=af_heart --speed=0.85 </dev/null
$PY readback.py name-test.mp3 name-test.txt </dev/null
```

Here is what came back, with an invented name:

```text
HEARD: This is Tandoor. Tandoor runs the night shift.
MATCH: 75.0% of 8 script words
  script: thandor thandor                heard: tandoor tandoor
```

That may or may not be what the name's owner wants. Whisper can only offer the nearest word it knows.

You can also see the sounds without voicing anything. This prints them in IPA (a standard way to write speech sounds):

```bash
~/voice-tools/venv/bin/python -c "from kokoro_onnx.tokenizer import Tokenizer; print(Tokenizer().phonemize('Which project tools', 'en-us'))"
```

This prints `wˌɪtʃ pɹədʒˈɛkt tˈuːlz`, with the stress on the second part of "project", as in the verb "to project". That is wrong for this sentence, so the next step fixes it. In the same way, `Thandor` prints as `thˈændɔːɹ`, sounding the t and the h apart.

**Whisper is only a witness for a name.** It writes the nearest thing it knows, so an invented name comes back spelled in odd ways even when it sounds right. Read the IPA as well, and ask the person who owns the name. Never give Whisper the name as a hint: with the name in its prompt, it writes the name whatever was said. `readback.py` gives no prompt.

### 5. Write the text for the voice

Put one block of speech in each file: `n1.txt`, `n2.txt`, and so on. Keep a block under about 70 words, one beat of picture. A change to one block then means voicing only that block again.

A blank line starts a new paragraph, which gets a longer pause.

**Write it the way it is said:**

- Numbers as words. "1,250" gives one caption word for four spoken words, and the pace number goes wrong. "$24" came back from Whisper as "$1.24" in a test. Write "twenty-four dollars".
- No markdown, no backticks, no tags. They are not speech.
- Write "Doctor", not "Dr." The script starts a new sentence after a full stop followed by a capital, so "Dr. Smith" gets a pause.
- A sentence over roughly 80 words stops the script. Break it up. The listener needs that anyway.

**Respell a word when it must stay as written.** Put the respelling in braces straight after the word. The voice says the respelling. The captions show the word:

```text
Which project{prodject} tools do you really use?
The betting{bett-ing} is that it fits on one page.
This is Thandor{Tan-dor}.
```

Those three were tested. `project{prodject}` changed the sounds to `pɹˈɑːdʒɛkt`, the noun. `Thandor{Tan-dor}` gave `tˈændˈɔːɹ`, and Whisper still wrote "Tandoor", which is the closest word it has for that sound. There can be no spaces inside the braces.

A hyphen in a respelling gives each part its own stress. `Kweh-lah-nee` came out as `kwˈeɪlˈɑːnˈiː`, three stressed beats. If that sounds choppy, try one word: `Kwelahnee` gives `kwˈɛlɑːnˌiː`.

**If you are free to change the words, rephrase instead.** One word is often easier to replace than to fix. If a rare word keeps coming back from Whisper as a different word, use a common word with the same meaning. A quote or a name cannot be rephrased, so respell those.

### 6. Choose the pace

The default is a floor the user can change:

| Video | Words a minute |
|---|---|
| A normal video | about 144 |
| A short intro of 2 to 3 minutes | about 180 |
| Whatever the user asks for | that |

Ask for a pace and the script searches for the speed:

```bash
cd /path/to/project
~/voice-tools/venv/bin/python voice.py n1.txt --voice=af_heart --target=144 </dev/null
```

```text
  take 1: speed 0.800 gives 146 words a minute
n1: af_heart speed 0.800 | 59 words | file 24.3 s | 146 words a minute over the speech span
```

Or set the speed yourself with `--speed=0.8`. Here is what the speed did on one 59-word passage, measured on a Mac with the default pauses:

| `--speed` | Words a minute |
|---|---|
| 0.7 | 127 |
| 0.8 | 146 |
| 0.9 | 168 |
| 1.0 | 177 |
| 1.1 | 185 |
| 1.25 | 200 |

The same passage at speed 1.0 in other voices: `af_bella` 172, `bf_emma` 176, `am_michael` 162, `bm_george` 147. So measure each voice on your own lines. One voice's numbers tell you little about another's.

**Three traps in the pace number:**

1. **Measure on the speech span, not on the file length.** Kokoro pads every take with silence. On a Mac we measured 0.24 to 0.48 s before the speech and 0.39 to 0.80 s after it. Other runs saw up to 0.9 s after. On a short line that wrecks the number: a 7-word line once read 112 words a minute by file length. A "correction" then sent it to top speed, where a name lost its first sound. `voice.py` cuts the padding and reports the span from the first word's start to the last word's end.
2. **Pauses do not shrink with speed.** The pauses between sentences are fixed seconds, so doubling the speed does not double the pace. Look at the table: from 1.0 to 1.25 the pace rose only 13%. If you cannot reach a fast pace, shorten the pauses: `--sentence-pause=0.25 --para-pause=0.5`.
3. **Inside one sentence, the model can drop a pause all at once.** One clip read 156 words a minute at speed 1.30, 164 at 1.33 and 193 at 1.36. So one proportional correction can overshoot. `--target` searches between the takes either side of the target to deal with this.

At speed 1.5, a name lost its first sound in one real job. So `--target` stays between 0.6 and 1.4, a cautious limit chosen for this script. If a take is still outside the band, the files are written, the script says `OUTSIDE the band`, and it exits 1. Then you decide.

**Pauses are your other dial.** `--sentence-pause=0.38` and `--para-pause=0.7` are the defaults. Past lesson videos used 0.42 and 0.75 at speed 0.8. A slow, deliberate block at the end of them used 0.6 at speed 0.72. Treat these as examples and listen.

### 7. Voice one block and read it back

```bash
cd /path/to/project
PY=~/voice-tools/venv/bin/python
$PY voice.py n1.txt --voice=af_heart --target=144 </dev/null
$PY readback.py n1.mp3 n1.txt </dev/null
```

**This machine has no ears.** A container cannot listen. It can only transcribe and measure. Reading back is the nearest thing to listening that it has. Here is a result from a test, on an invented script:

```text
HEARD: Last March, a new manager opened a spreadsheet and found 41 open tasks. Nobody had touched them for six weeks. She closed 19 in one afternoon and nobody noticed. Which project tools do you really use? ...
MATCH: 96.2% of 67 script words
  script: forty one                      heard: 41
  script: nineteen                       heard: 19
```

How to read the differences:

| What differs | What to do |
|---|---|
| A number written as digits (`41`) | Harmless |
| A homophone, or a spelling difference | Harmless |
| Two words heard as one (`3 pm`, `3pm`) | Harmless |
| A bracketed word at the very end, such as `[buzzer]` | Harmless. Whisper invented it from the silence after a short take. It happened on two test lines |
| A different real word (invented example: `vogue` for `vague`) | Rephrase, or respell if the words must stay |
| A word missing | Voice it again and read it back. If it stays missing, rephrase |

### 8. Stop and ask a person to listen

Before you voice a big batch, send the user one finished block and ask. For example:

> Here is the first part, 25 seconds, in the voice we chose. Could you listen? Is the voice right, is the speed right, and did it say the names properly?

Transcripts cannot judge whether a voice is pleasant, whether a stress is off, or whether a name sounds right. In the review of voices mentioned above, Whisper understood every take, so that test could not rank them. A person's ear had to decide. Wait for an answer. A batch takes time: in one real job, one pass of nearly 1,000 short clips took about 1 hour 20 minutes on 3 threads, with a different Kokoro install.

### 9. Voice the rest

Save this as `voice-all.sh`

```bash
#!/usr/bin/env bash
# Voice every .txt in a folder, skipping any whose .mp3 is already newer.
#   bash voice-all.sh narration af_heart 144 2>&1 | tee voice.log
set -u
FOLDER="$1"; VOICE="$2"; PACE="$3"
PY="${VOICE_HOME:-$HOME/voice-tools}/venv/bin/python"
find "$FOLDER" -name '*.txt' | sort | while read -r f; do
	m="${f%.txt}.mp3"
	if [ -f "$m" ] && [ ! "$f" -nt "$m" ]; then echo "skip $f"; continue; fi
	# </dev/null matters: without it, ffmpeg eats the rest of this list and the loop stops early with no error.
	"$PY" voice.py "$f" --voice="$VOICE" --target="$PACE" </dev/null || echo "CHECK $f"
done
echo "finished $FOLDER"
```

Run it from the folder that holds `voice.py`. For a big batch, set the Bash tool to run it in the background, so a timeout cannot stop it:

```bash
cd /path/to/project
bash voice-all.sh narration af_heart 144 2>&1 | tee voice.log
```

It skips any block whose `.mp3` is newer than its `.txt`. So after you change one block, run the same command again and only that block is voiced.

Writing your own loop? **Every command inside a `while read` loop needs `</dev/null`.** ffmpeg reads standard input. Without this it swallows the rest of your list, and the loop ends early with no error.

The voice, speed and pace of each take are stored in the mp3. If you change the voice, delete the old mp3s, because a file date cannot tell you the voice changed. Read them like this:

```bash
cd /path/to/project
ffprobe -v error -show_entries format_tags=comment -of csv=p=0 n1.mp3
```

### 10. Read back everything, then commit

Before your first push, check the repository is private (`gh api repos/OWNER/REPO --jq .visibility` if you have `gh`, taking OWNER/REPO from `git remote -v`. `gh repo view` fails in a cloud session, because the session's GitHub proxy refuses GraphQL). If it is public or you cannot tell, ask the user before you push anything of theirs.

```bash
cd /path/to/project
PY=~/voice-tools/venv/bin/python
for f in narration/*.txt; do echo "== $f"; $PY readback.py "${f%.txt}.mp3" "$f" </dev/null; done
git add narration && git commit -m "Voice the narration" && git push
```

Look at each difference, using the table in step 7. Then read back the finished mix of the video too, since that is what the viewer hears.

A change to one block's words moves everything after it in the video, because later cuts usually depend on the timings. Tell whoever is cutting the picture.

## Word timing: how good it is

The first run makes a second copy of the voice model, `kokoro-timed.onnx`, that also reports when each word is said. The script voices one sentence per model call, so each sentence's timing is exact and the pauses are chosen by you.

We compared it with the sound on one 29-second take, on a Mac:

- After a pause, the next word starts 0.06 to 0.14 s after the sound returns.
- Against another recogniser (Parakeet), a word's start is a median of 0.06 s later.

So a word highlight lights up about 2 frames late at 30 frames a second. That is good enough, and a highlight must never come early. To check your own take, use this script.

`check-drift.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/check-drift.py (59 lines).
```

```bash
cd /path/to/project
python3 check-drift.py n1.captions.json n1.mp3
```

```text
6 pauses compared. Word starts +0.113 s from the sound (middle value); range +0.056 to +0.138 s.
```

It exits 1 if any pause is more than 0.25 s off. When we told it the voice was 0.5 s later than it was, it reported `+0.602` and exited 1.

## Other languages

This skill was written for English. Its pace numbers, voice grades and `readback.py` are all English. Tell the user this before you start, and ask which language they want.

We tried others once each, on one or two short sentences, on a Mac on 2026-11-09. Nobody who speaks these languages listened, so a good result here only means the words came through:

| Language | Try this | What happened |
|---|---|---|
| Spanish | `--voice=ef_dora --lang=es` | Worked. A speech recogniser read back the words, with times for each word |
| French | `--voice=ff_siwis --lang=fr-fr` | Worked, the same way |
| Hindi | `--voice=hf_alpha --lang=hi` | Ran with no error. The recogniser read back only the first of two sentences, so we cannot say it works |
| Japanese | Do not use `voice.py` | The sounds came out wrong: the tool spelled each character as the English words "Chinese letter" |
| Chinese | Do not use `voice.py` for captions | It ran, but the whole text became one caption word, because it has no spaces between words |

Italian (`if_sara`, `--lang=it`) and Brazilian Portuguese (`pf_dora`, `--lang=pt-br`) have voices too. We did not test them.

```bash
cd /path/to/project
~/voice-tools/venv/bin/python voice.py es.txt --voice=ef_dora --lang=es --speed=1.0 </dev/null
```

**Three traps:**

- Always pass `--lang`. Without it the script uses English rules.
- The script starts a new sentence only before a plain capital A to Z or a quote mark. A sentence that starts with `¿` or `É` stays joined to the one before. If you see `This sentence is too long`, put a blank line between the sentences.
- Write the numbers as words, as in English. Do not rely on the speech rate table in step 6. Measure the voice you chose.

**To read it back,** use this script, not `readback.py`, whose model knows only English. It needs Whisper turbo, a 564 MB download that takes about 1 GB of disk:

```bash
cd ~/voice-tools/whisper
curl -sSfL --retry 4 --retry-delay 5 -o turbo.tar.bz2 https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-turbo.tar.bz2
tar xjf turbo.tar.bz2 && rm turbo.tar.bz2
```

`readback-language.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/readback-language.py (60 lines).
```

```bash
cd /path/to/project
~/voice-tools/venv/bin/python readback-language.py es.mp3 es.txt --lang=es </dev/null
```

Here is what the Spanish test printed, after the line of heard words. Numbers come back as digits, as in English, so that difference is harmless:

```text
MATCH: 97.1% of 35 script words
  script: cuarenta                       heard: 40
```

**If Kokoro will not do,** the better choices are a person recording it, or a paid voice service. The ElevenLabs model named below is sold as multilingual. We did not test it in other languages.

## If the user wants a paid voice

ElevenLabs is one public option, with more natural voices. **It costs money, and every call bills.** There is no cache: a repeat costs again. Ask before each batch and say roughly how many characters it is. Prices are at `https://elevenlabs.io/pricing`.

**It was refused in one cloud session in September 2026, and hosts differ, so test it.** This call costs nothing:

```bash
curl -sS -o /dev/null -m 15 -w '%{http_code}\n' https://api.elevenlabs.io/v1/voices
```

A refusal reads `CONNECT tunnel failed, response 403` or `Host not in allowlist`. Any other status, such as `200` or `401`, means the host answered. The user can then add `api.elevenlabs.io` in the cloud environment menu: Edit, then Network access.

**Adding the key.** The user creates a key on elevenlabs.io and adds `ELEVENLABS_API_KEY` as an environment variable in that same cloud environment menu. Then start a new session. Tell the user not to paste it into the chat, and never print it or commit it.

**One call.** This is the public API as documented at `https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps`. We did not make a paid call while writing this skill, so this request is untested. Only the converter was tested, on a hand-made sample.

```bash
cd /path/to/project
python3 -c "import json; print(json.dumps({'text': open('n1.txt').read().strip(), 'model_id': 'eleven_multilingual_v2', 'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75, 'speed': 1.0}}))" > request.json
curl -sS -X POST "https://api.elevenlabs.io/v1/text-to-speech/$VOICE_ID/with-timestamps?output_format=mp3_44100_128" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" -H 'content-type: application/json' -d @request.json -o n1.response.json
```

`eleven-to-captions.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/eleven-to-captions.py (47 lines).
```

```bash
cd /path/to/project
python3 eleven-to-captions.py n1.response.json n1
```

Choices that were measured on one voice, some months before this was written:

- `eleven_multilingual_v2` obeyed `speed`: 0.9 gave 116 words a minute, 1.0 gave 132, 1.1 gave 145, 1.2 gave 168.
- `eleven_v3` ignored it: 0.85, 1.0 and 1.15 gave 105, 109 and 107. Check again, as this may have changed.
- The braces in `word{respelling}` are a feature of `voice.py` only. With ElevenLabs, send the spoken spelling and change the word back in what you display.

This also applies to any other voice service. You need the audio, plus word or character timings. If a service gives no timings, make them with a word-timed transcription of its audio.

## How to talk to the user

- Use plain words. Say "the voice" and "how fast it talks", not "TTS" and "wpm", unless they use those words first.
- Ask one question at a time, with your suggestion. For example: "Which voice do you like? I suggest the first one, because it sounds the most natural to most people. Here are three samples."
- Pause for their OK at two points: after the audition, and after the first finished block.
- Tell them plainly that you cannot hear. Say "A speech tool read it back and got every word", never "it sounds good".
- Ask how to say any name you are unsure of. Ask for a recording or a spelling that shows the sound.
- Before any paid call, say that it costs money and wait for a yes.
- Send samples as chat files, each under 30 MiB. A block of voice is far smaller than that.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `curl: (22) The requested URL returned error: 504` during setup | GitHub is having a bad moment. It happened during testing | Wait some minutes and run the setup again. It skips what it already has |
| `CONNECT tunnel failed, response 403` or `Host not in allowlist` | The proxy refused the host | Ask the user to allow it in the cloud environment menu: Edit, then Network access |
| Hugging Face refused while following another guide | Common in cloud proxies | Use the GitHub URLs in `setup-voice.sh` |
| `No model in ...` | Setup has not run, or a rebuild wiped the disk | `bash setup-voice.sh` |
| `ModuleNotFoundError: No module named 'kokoro_onnx'` | You ran the system Python | Use `~/voice-tools/venv/bin/python` |
| `AttributeError` naming `_infer` or `_style_for` | A different kokoro-onnx version. The script uses these private functions | `~/voice-tools/venv/bin/pip install kokoro-onnx==0.6.1` |
| `module 'segments' has no attribute 'Profile'` | A file called `segments.py` sits beside your script, and the speech library imported it by mistake | Rename that file, or move your script to another folder |
| `NumPy Cython headers require Cython 3.0.0` | You installed `kokoro`, the PyTorch package, on Python 3.13. This skill uses `kokoro-onnx` | Follow the setup here. If you do want `kokoro`, use Python 3.12 |
| `open() got an unexpected keyword argument 'metadata_errors'` | faster-whisper 1.2.1 with PyAV 17, seen in a cloud session. You only meet this if you use faster-whisper rather than `readback.py`. It did not happen with PyAV 17.1.0 on a Mac on 2026-11-09 | Decode with ffmpeg and pass the samples to Whisper, as `readback.py` does |
| `No voice called ...` | A wrong voice name | The message lists all the names |
| `This sentence is too long for one model call` | Over 510 phonemes, roughly 80 words | Break the sentence |
| `A respelling needs a word before it and no spaces inside` | For example `word{two parts}` | Use a hyphen or one word |
| `WARNING rough timings, check this line` | Written words and spoken sounds could not be matched, often from numbers or symbols | Write the numbers as words |
| Your loop stops early with no error | ffmpeg read the loop's input | Add `</dev/null` |
| Pace is far too low on a short line | You measured file length, or digits were read as many words | Read the script's span number. Write numbers as words |
| Whisper hears a different word for a name each time | It only guesses at names it does not know | Read the IPA, and ask a person |
| `FileNotFoundError` naming `ffmpeg` | No ffmpeg on the path | See "What you need" |
| Voice mp3s vanished after a restart | They were never pushed | Commit and push after each batch. Run the voicing again if you must: the same words, voice and speed gave the same result in earlier runs |

## How to check it worked

Do these on the first block, and on the whole batch at the end:

1. **Files exist.** `ls -la n1.*` shows `.mp3` and `.captions.json`.
2. **The shape is right.** `ffprobe -v error -show_entries stream=codec_name,sample_rate,channels:format=duration -of compact n1.mp3` shows `mp3`, `44100`, one channel. A file check cannot tell you the video is good.
3. **The loudness is right.** On a real take this gave about -20.5 LUFS. Five voices measured between -20.4 and -20.9:
   ```bash
   ffmpeg -nostdin -hide_banner -i n1.mp3 -af ebur128=peak=true -f null - 2>&1 | grep -A12 Summary | grep -E 'I:|Peak:'
   ```
4. **The words are right.** `readback.py` shows no real differences.
5. **The timing is right.** `check-drift.py` exits 0.
6. **The pace is right.** The last line of `voice.py` is near your target.
7. **A person has listened** and said yes. Nothing else can stand in for this.
