---
name: transcribe-audio
description: Get a word-timed transcript of a recording with no paid API, using sherpa-onnx from PyPI and models from GitHub, and prove that no speech was lost. Use it before cutting a recording, making captions from real speech, or checking what a generated voice said.
---

# Transcribe audio

> **This is a floor, not a ceiling.** Most of this worked when it was written, and this guide says what was not tested. Tools, models and limits keep changing, and you may know something better. Use your own judgement, research and the user's context. Check versions and limits when they matter. If you find a better way, use it and tell the user. Suggestions here are starting points, never the only choices.

If a director skill sent you here, go back to it when you finish.

## What this skill does

You give it a recording. It gives you every word with a start and an end time. These words are invented, to show the shape:

```json
{"segments": [{"start": 0.226, "end": 4.946,
  "text": "So what did the crew find when they opened the door?",
  "words": [{"w": "So", "s": 0.226, "e": 0.466}, {"w": "what", "s": 0.466, "e": 0.626}]}]}
```

Times are in seconds. A **segment** is one stretch of speech between pauses.

It uses three free parts:

| Part | Job |
|---|---|
| [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) | The program that runs the models. It comes from PyPI |
| Silero VAD | Finds where speech is (VAD means voice activity detection) |
| Parakeet TDT 0.6B v2 | Writes the English words and their times. It comes from sherpa-onnx's GitHub releases |
| Whisper turbo, optional | A second reading, to catch what Parakeet got wrong |

It also has two checks for the worst failure in this kind of work: a word the recogniser never heard reads as silence, and a cut then removes it.

## When to use it (and when not to)

Use it when:

- you will cut a recording on its words, such as removing pauses or choosing clips
- you need captions from real speech
- you want to know what a generated voice really said
- there is no budget, or no key for a paid service

Consider something else when:

- the speech is not English. Parakeet TDT 0.6B v2 is English only. See "Other languages" near the end for what to try
- you need to know who is speaking. This gives no speaker labels
- the user already has a good paid service and a key, and wants to use it

Whisper tools that fetch models from Hugging Face, such as `@remotion/install-whisper-cpp`, can fail in a cloud session because Hugging Face is often refused. That is why the models here come from GitHub.

## What you need before you start

| You need | Check | Install |
|---|---|---|
| Python 3 with `venv` | `python3 -m venv --help` | Usually there already. Tested on Python 3.10 |
| ffmpeg | `ffmpeg -version` | `apt-get install -y ffmpeg` if the machine lets you. Otherwise see below |
| curl and tar | `curl --version` | Usually there already |
| Network to PyPI and GitHub, once | see below | The user can open hosts in the cloud environment menu: Edit, then Network access |
| Disk: 700 MB, or 1.7 GB with Whisper | `df -h ~` | See the sizes below |

Test the network. Hosts differ per environment and per date:

```bash
curl -sS -o /dev/null -m 15 -w '%{http_code}\n' https://pypi.org/simple/sherpa-onnx/
curl -sS -L -o /dev/null -r 0-10 -m 30 -w '%{http_code}\n' https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx
```

A refusal reads `CONNECT tunnel failed, response 403` or `Host not in allowlist`. Any other status means the host answered. `200` or `206` means it works. A `504` means GitHub answered but had a bad moment. It happened while this skill was being tested, so wait some minutes and try again.

**If there is no ffmpeg and `apt-get` is not allowed,** this gets one from PyPI (checked on a Mac, not on Linux):

```bash
python3 -m venv ~/ffmpeg-venv && ~/ffmpeg-venv/bin/pip install -q imageio-ffmpeg
export FFMPEG=$(~/ffmpeg-venv/bin/python -c "import imageio_ffmpeg as i; print(i.get_ffmpeg_exe())")
```

The scripts read `FFMPEG` if it is set. In the plain commands below, replace `ffmpeg` with `"$FFMPEG"`.

Sizes, measured on 2026-11-09:

| Item | Download | On disk |
|---|---|---|
| Parakeet, int8 | 482 MB | 633 MB |
| Whisper turbo, int8 | 564 MB | 1.0 GB |
| Silero VAD | under 1 MB | under 1 MB |

### About cloud sessions

These held when this was written:

- A cloud session is a Linux x64 container with 4 cores, about 15 GB of memory, and no GPU. These models run on the CPU.
- `/opt` may or may not be writable. The setup below uses `/opt/asr` if it can, and your own `~/asr` if it cannot. It tells you which.
- A restart can wipe everything outside git. If a script says it cannot find a model, run the setup again.
- Commit the transcript JSON. It is small. It also holds what the person said, so see the privacy check in step 8. A recording is usually too big for git, which refuses files over 100 MB.
- The Bash tool times out at 10 minutes, and a background command stops after 30 minutes, or after up to 2 hours if you start it with `timeout: 7200000`. A worker restart kills running processes, `nohup` included. Long jobs go in the background, writing to a log.
- A lost transcript can be made again. In one real job, Parakeet run a second time over a recording of about 8,000 words gave the same result.

### Speed

| Job | Machine | Time |
|---|---|---|
| Parakeet on 24 minutes | 4-core cloud container, 2026 | 121 s, about 12 times real time |
| Whisper turbo on the same 24 minutes | Same, with another job sharing the CPU | 14 minutes |
| Parakeet on a 53-second clip | Apple Silicon Mac, 2026-11-09 | 6 s |
| Whisper turbo on the same clip | Same | 23 s |

### Tested how

Every script here was tested on a Mac (Apple Silicon, Python 3.10, sherpa-onnx 2.0.1) on 2026-11-09, on a real 53-second interview clip and on generated speech. They were not run on Linux in this form. The same method ran on a Linux cloud container earlier in 2026, on a 24-minute recording.

## Steps

### 0. Save the tools

Work in one project folder. Every step below that uses a project file starts with `cd /path/to/project`: put your real folder there, as a full path. A `cd` from an earlier command may not carry over.

Do not retype the long files. They are in this skill's `files` folder. This copies them all into your folder and keeps any file already there.

```bash
cd /path/to/project
S="$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/skills/transcribe-audio"
cp -rn "$S/files/." . 2>/dev/null; test -e "tools/setup-transcription.sh" && echo copied || echo "NOT COPIED: set S to the folder that holds this SKILL.md, and run this again"
```

It keeps any file that already exists, so your work is safe.

### 1. Set up once

The script just below is already saved, if you ran the copy step.

`tools/setup-transcription.sh`, which the copy step puts in your folder:

```bash
# In this skill's files folder: files/tools/setup-transcription.sh (41 lines).
```

```bash
cd /path/to/project
bash tools/setup-transcription.sh --whisper
```

The last line tells you what to run in each new shell, for example `export ASR_HOME=/opt/asr`. Do that. Every script below needs it. Leave out `--whisper` if you do not want the second reading.

### 2. Make a 16 kHz mono wav

The models want this exact format. From a video or any audio file:

```bash
cd /path/to/project
ffmpeg -nostdin -y -i raw.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le audio16k.wav
```

### 3. Transcribe

**Run these scripts with `$ASR_HOME/venv/bin/python`, not `python3`.** That Python has the speech tools. Plain `python3` fails on `import sherpa_onnx`. All the scripts in this guide live in `tools/`.

`tools/transcribe.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/transcribe.py (104 lines).
```

```bash
cd /path/to/project
$ASR_HOME/venv/bin/python tools/transcribe.py audio16k.wav transcript.json
```

```text
done: 9 segments, 137 words, 53 s of audio in 6 s
```

**Do not "simplify" how the words are split.** This speech tool shows a new word with a space. Leave that line of the script as it is, or every segment can come back as one long "word". The line has a comment on it.

### 4. Get a second reading with Whisper

`tools/whisper-check.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/whisper-check.py (63 lines).
```

```bash
cd /path/to/project
$ASR_HOME/venv/bin/python tools/whisper-check.py audio16k.wav transcript.json whisper.json
```

It prints each chunk where the two disagree. Here is the kind of thing it prints, with invented words. The speaker said "if we are on the boat by then":

```text
  49.9 s  Parakeet: If we are on Well I think it'll be
          Whisper:  if we are on the boat by then? Well, I think it'll be...
```

Parakeet can lose a few words like that. It did on a real clip in testing. If a cut had trusted its timings, those words would have been removed as silence.

### 5. Correct the words, and write the fixes down

**Accents trip both models, in different places.** One may hear "teacher" as "cheetah" (an invented example), and the other may get that right and invent something else. Neither is the truth. When they disagree, ask someone or check the context.

Never edit `transcript.json` by hand and then lose track of it. Keep a table of corrections, keyed to the segment, so anyone can see every change and run it again. The words keep the recogniser's timings.

`tools/apply-corrections.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/apply-corrections.py (44 lines).
```

Write `corrections.json`. These rows are invented, to show the shape:

```json
[
  {"segment": 12, "heard": "cheetah", "said": "teacher", "why": "both readings differ; context"},
  {"segment": 30, "heard": "the parcel", "said": "the pastel", "why": "speaker's accent; Whisper agrees"}
]
```

```bash
cd /path/to/project
python3 tools/apply-corrections.py transcript.json corrections.json transcript.fixed.json
```

It stops with `No match for 'banana' in segment 0: ...` if a row matches nothing, so a table that has gone stale cannot pass unseen. When a fix changes the number of words, it shares the old time out across the new words. Keep the original `transcript.json`. Run the corrections again whenever you transcribe again.

### 6. If you cut the audio, prove no speech was lost

**A word the recogniser does not hear reads as silence** to anything that cuts on word timings. On a real job, a cut that tightened pauses removed a two-word phrase (about a second of speech) and a "But". Nothing warned about it. The transcript simply had no words there.

Two checks together catch this:

1. **Compare `silencedetect` against the kept ranges.** This finds speech that was never transcribed. Only this check found that phrase.
2. **Transcribe the cut audio again and diff the words.** This finds clipped words.

`tools/check-cut.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/check-cut.py (91 lines).
```

Write `keep.json`, the parts of the raw audio your cut keeps, in seconds:

```json
[[0.18, 5.00], [5.42, 26.05], [26.51, 33.19]]
```

```bash
cd /path/to/project
$ASR_HOME/venv/bin/python tools/check-cut.py audio16k.wav transcript.json keep.json
```

In a test we hid four words from the transcript and let the cut drop them. Here is part of what it printed:

```text
SOUND DROPPED     7.44 to     8.62 s (1.18 s). Transcript there: (nothing: the recogniser missed it, listen here)
WORDS DIFFER expected: um  |  heard in the cut: (nothing)
```

**Each `SOUND DROPPED` line is a place to check, not always a fault.** On our noisy 53-second clip, 8 lines appeared with a clean cut too. Most were breaths and room sound, and one was a real phrase that Parakeet missed. So look at the list: open the source, read the Whisper chunk for that moment, and if possible ask a person to listen. If `SOUND DROPPED` lists too much noise, raise `NOISE` near the top of the script, for example from `-35dB` to `-30dB`.

Also expect small word differences. A filler such as "um" often comes and goes, and a short word can read differently with less audio around it. Read each one anyway.

### 7. Make captions from it, if you need them

`tools/to-captions.py`, which the copy step puts in your folder:

```python
# In this skill's files folder: files/tools/to-captions.py (59 lines).
```

```bash
cd /path/to/project
python3 tools/to-captions.py transcript.fixed.json voice.captions.json
```

That JSON is what Remotion's `@remotion/captions` package reads. If you cut the audio, word times must go through the same keep list, once, before you make captions. A word's time is relative to the source file.

### 8. Commit the results

Before your first push, check the repository is private (`gh api repos/OWNER/REPO --jq .visibility` if you have `gh`, taking OWNER/REPO from `git remote -v`. `gh repo view` fails in a cloud session, because the session's GitHub proxy refuses GraphQL). If it is public or you cannot tell, ask the user before you push anything of theirs. A transcript holds a person's own words.

```bash
cd /path/to/project
git add transcript.json corrections.json transcript.fixed.json && git commit -m "Transcript and corrections" && git push
```

## Other languages

The main route here is English only, because Parakeet TDT 0.6B v2 knows only English. Tell the user this before you start, and ask which language the recording is in.

**For 25 European languages, try Parakeet v3.** Its maker lists Bulgarian, Croatian, Czech, Danish, Dutch, English, Estonian, Finnish, French, German, Greek, Hungarian, Italian, Latvian, Lithuanian, Maltese, Polish, Portuguese, Romanian, Russian, Slovak, Slovenian, Spanish, Swedish and Ukrainian (`https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3`). We tested only Spanish and French, on 13 seconds of generated speech each, on a Mac on 2026-11-09. Both came back with times for each word. The words matched the script, apart from numbers heard as digits and one lost accent. A real recording will be harder. The download is about 490 MB:

```bash
cd "$ASR_HOME/models"
curl -sSfL --retry 4 --retry-delay 5 -o v3.tar.bz2 https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8.tar.bz2
tar xjf v3.tar.bz2 && rm v3.tar.bz2
```

Make language copies of the scripts, under new names, so `tools/transcribe.py` stays as it is:

```bash
cd /path/to/project
sed 's/tdt-0.6b-v2-int8/tdt-0.6b-v3-int8/' tools/transcribe.py > tools/transcribe-v3.py
sed "s/language='en'/language='es'/" tools/whisper-check.py > tools/whisper-check-es.py
sed 's/transcribe\.py/transcribe-v3.py/' tools/check-cut.py > check-cut-v3.py
$ASR_HOME/venv/bin/python tools/transcribe-v3.py audio16k.wav transcript.json
$ASR_HOME/venv/bin/python tools/whisper-check-es.py audio16k.wav transcript.json whisper.json
```

Put the language's two-letter code in place of `es`. The Whisper check lists more places than it should in a language with accents, since it compares plain letters only. Read each one.

**For other languages,** Whisper turbo gives text with no word times in this setup. On a Hindi test it heard only the first of two sentences, so check its coverage. For word times you need another tool. sherpa-onnx's model list also has SenseVoice, for Chinese, Japanese, Korean and Cantonese, which we did not test. A paid service is the other choice, if the user wants one.

## How to talk to the user

- Plain words. Say "a word-by-word transcript with times". Do not make them learn "VAD" or "Parakeet".
- Say what you could not check. Say "Two programs read this and they agree on all but six places", not "the transcript is correct".
- **This machine cannot listen.** It reads with two recognisers and measures sound. For a name, a term or an accent, it may be wrong in a way it cannot detect.
- Ask one question at a time, with a suggestion. For example: "The two readings differ here: 'ship' or 'sheep'? I think 'ship' from the sentence. Can you check at 12 minutes 4 seconds?"
- Give exact timestamps when you ask them to listen, and list every place in one message, so they can do it in one sitting.
- Ask before removing anything from a real person's speech, and show them what you plan to remove.

## What goes wrong and how to fix it

| What you see | Why | Fix |
|---|---|---|
| `Set ASR_HOME first` | A new shell | Run the `export ASR_HOME=...` line that setup printed |
| A `Load model` error saying `File doesn't exist` | Setup was not run, or a rebuild wiped the disk | `bash tools/setup-transcription.sh --whisper` |
| `curl: (22) The requested URL returned error: 504` | GitHub is having a bad moment. It happened during testing | Wait some minutes and run the setup again. It skips what it already has |
| `CONNECT tunnel failed, response 403` or `Host not in allowlist` | The proxy refused the host | Ask the user to allow it in the cloud environment menu: Edit, then Network access |
| `Permission denied` on `/opt` | Not writable | The setup falls back to `~/asr` by itself, or set `ASR_HOME` to a path you own |
| `... is 44100 Hz. Make it 16 kHz mono first` | The wrong input format | Step 2 |
| Every segment is one long word | The line that splits words was changed | Use `tools/transcribe.py` as written |
| A hole in the transcript, with sound there | The recogniser missed it | Step 4 and step 6 |
| A word is wrong at one place, right at another | An accent, or too little audio around it | Add a row to the corrections table |
| Whisper writes `[BUZZER]` at the end of a short clip | Whisper invents text from silence. It happened in tests | Ignore it. Parakeet is the one that sets the timing |
| `Killed` or a process vanishes on a long job | A worker restart, or memory. Memory use was not measured here | Run it again: the result comes out the same |
| `No match for ... in segment ...` | A correction no longer fits, perhaps after new transcribing | Update the row |
| `open() got an unexpected keyword argument 'metadata_errors'` | faster-whisper 1.2.1 with PyAV 17, seen in a cloud session, if you try that tool rather than this one. It did not happen on a Mac on 2026-11-09 | Decode with ffmpeg and hand it the samples |

## How to check it worked

1. **Look at the words.** Read the start and end of `transcript.json`, and a few segments from the middle. Do they make sense? Do the words change at each space, rather than one long word per segment?
2. **The timing is close.** Cut out one word and check. This extracts a word from 0.946 to 1.906 s, for example. Send it to a person, or transcribe it:
   ```bash
   cd /path/to/project
   ffmpeg -nostdin -y -v error -ss 0.946 -to 1.906 -i audio16k.wav word.wav
   ```
3. **The coverage is complete.** Compare the speech time with `silencedetect`: any long stretch of sound with no words deserves a look. `tools/check-cut.py` does this when you pass a keep list covering the whole file.
4. **A second reading agrees,** or you have looked at every place it does not.
5. **Cuts lost nothing:** `tools/check-cut.py` gives no line you have not explained.
6. **A person has checked names and terms.** Nothing else can.
