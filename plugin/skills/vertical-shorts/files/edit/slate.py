# The slate: one entry per short. Anchor on words, never on timestamps.
# This slate fits the practice take from tools/make-sample.py. Replace it for a real film.
# Run: python3 tools/build-short.py edit/slate.py
FPS = 30  # the source's own rate
SOURCE = "footage/main.mp4"  # under public/
RAW_WIDTH = 1280  # the original recording's width, for the upscale check
EDIT = None  # the long cut's edit.json if you have one (its corrected words). Otherwise:
TRANSCRIPT = "edit/transcript.json"  # words on the source's clock
CHAPTERS = []  # (time, title) if there is no edit.json: a segment may not cross one

SHORTS = [
    {
        "id": "s01", "title": "Never lose a word", "kind": "practical move",
        "profile": "organic",  # "ad" if it may be boosted, "organic" if not
        "hook": ["A CUT MUST", "KEEP THIS"],  # at most 6 words across two lines
        "hits": ["cut", "word", "trust", "remember"],  # marked in the captions
        "view": {"cx": 640, "cy": 360, "w": 620},  # the picture window, in source pixels
        "segments": [  # a start phrase, an end phrase, and a hint time for repeats
            {"hint": "0:24", "start": "A cut must never", "end": "lose a word."},
            {"hint": "0:15", "start": "Three things matter", "end": "sound you can trust."},
            {"hint": "0:32", "start": "That idea is", "end": "to remember."},
        ],
        "drops": [],  # {"hint": "0:36", "phrase": "a than"} removes a stumble inside a segment
        "plate": {"at": "A cut must never", "name": "The speaker", "role": "Exact wording from the user", "dur_s": 2.5},
        "slides": [
            {"at": "a steady picture", "kicker": "Three things", "title": "What matters", "lines": ["Clear words", "A steady picture"], "dur_s": 2.2},
        ],
        "pops": [
            {"at": "lose a word.", "text": "A WORD"},
            {"at": "Three things", "text": "THREE"},
            {"at": "to remember.", "text": "REMEMBER"},
        ],
        "sfx": [{"at": "Three things", "src": "sfx/pop.wav", "volume": 0.25}],
        "cta": {"line": "Watch the whole talk", "sub": "Link under this video"},  # never invent a link
    },
]
