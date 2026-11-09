# Video director

A friendly guide that helps you make or edit a video in a [Claude Code](https://code.claude.com) cloud session. You talk in plain English, and it guides you one step at a time: your idea, the words, the voice, the look, the effects, the final file. You don't need to know anything about making video.

## Start

Open a new session at [claude.ai/code](https://claude.ai/code), in any repository of yours. Then do either of these:

**Attach one file.** Download [`director.md`](director.md), attach it to the chat, and type:

```text
start
```

**Or paste one line,** with no attachment:

```text
Run `curl -fsSL https://raw.githubusercontent.com/vivmagarwal/video-director/main/director.md`, follow what it says, and start.
```

The director greets you and asks what you need. If you have files, it opens a private page where you can drop them, big ones too. When the video is ready, a private page lets you watch it and save it.

## What it uses

It works with public tools such as [Remotion](https://www.remotion.dev), ffmpeg, the free Kokoro voice and free speech recognition, plus two public effect libraries: [remotion-effects-library](https://github.com/vivmagarwal/remotion-effects-library) and [remocn](https://github.com/vivmagarwal/remocn). It asks you before anything that costs money.

- **Remotion's licence:** free for individuals, non-profits and companies of up to 3 people. Other companies need a paid licence: https://www.remotion.dev/license
- **Media you add** has its own licence, and that remains your responsibility.

## Other ways to use it

**As a repository of its own.** Press **Use this template** on GitHub, open a cloud session on your new repository, and type `start`. Skills in a repository's `.claude/skills/` load by themselves in a cloud session.

**As a plugin, in the terminal or the desktop app.** Plugins do not load in cloud sessions, so this is only for Claude Code on your own machine:

```text
/plugin marketplace add vivmagarwal/video-director
/plugin install video-director@video-director
```

Then run `/video-director:director`.

## What's here

| Path | What it is |
|---|---|
| `director.md` | The small start file you attach |
| `plugin/skills/` | The 20 skills. Each folder has a `SKILL.md`, and a `files` folder if it needs scripts or pages. Only the `director` skill depends on the others |
| `dist/` | The same skills as one download, which `director.md` fetches |

## A floor, not a ceiling

Everything here is a starting point. Tools, models and limits keep changing, and each guide tells Claude to use its own judgement and research, and your taste.

## What was tested

Scripts were run on a Mac on Remotion 4.0.541 and 4.0.542, and most cloud numbers come from real jobs on a slightly older Remotion. In November 2026 a real cloud session on 4.0.542 ran the edit-a-recording path from start to finish, then an effects and colour pass, and the fixes it led to are included. Those fixes were tested on a Mac, with the network denied where it matters, and have not yet run in a cloud session themselves. Each skill says what was not tested. If something breaks, please open an issue with the exact error.

## Licence

MIT. See [LICENSE](LICENSE).
