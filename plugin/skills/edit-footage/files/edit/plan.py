# The plan for one film: every editorial decision, as data, with its reason.
# Times are on the clock of the file you transcribed. Run: python3 tools/build-edit.py edit/plan.py
# This plan fits the practice recording from tools/make-sample.py. Replace it for a real film.
FPS = 30  # the working copy's own rate, so that no frame repeats
SOURCES = {"main": "footage/main.mp4"}  # under public/
TRANSCRIPT = "edit/transcript.json"
OUT = "src/edit.json"

# The cold open: the strongest lines, in an order that climbs to the title.
TEASER = [
    {"ranges": [("0:24.10", "0:26.20")], "keyword": ["A cut must never", "lose a word"]},
    {"ranges": [("0:32.60", "0:35.00")], "keyword": ["The one idea", "to remember"], "side": "left"},
]
TITLE = {"kicker": "A practice film", "title": "What a cut must keep", "sub": "Made from a 40-second test take"}

# Stumbles and false starts only. Never an idea. Each one carries its reason.
CONTENT_CUTS = [
    ("0:09.30", "0:12.00", "a false start; the next sentence says it cleanly"),
]
CHAPTERS = [  # (time at a pause, number, title, subtitle). They double as YouTube chapters.
    ("0:15.35", "01", "Three things", "What matters here"),
    ("0:29.20", "02", "The last idea", "The one to remember"),
]
LISTS = [  # the picture steps aside and each item lands on the words that name it
    {"start": "0:15.50", "end": "0:21.30", "kicker": "What matters", "title": "Three things",
     "items": [("0:17.39", "Clear words"), ("0:18.52", "A steady picture"), ("0:19.97", "Sound you can trust")]},
]
QUOTES = [  # full frame, over the speaker's own voice
    {"start": "0:24.20", "end": "0:26.10", "lines": ["A cut must never", "lose a word."]},
]
HITS = ["cut", "word", "remember"]  # key nouns, marked in the captions
NAME_PLATES = [("0:00.70", "The speaker", "Ask for the exact wording. Never guess a title.")]
END = {"kicker": "One question", "title": "What will you keep?", "sub": "Send this to someone who edits."}

# Speech the recogniser never heard: (start, end, words). tools/check-edit.py dropped finds it.
MISSED_WORDS = []
# A segment's start as m:ss.ss -> its corrected words. Fix mishearings only, in the speaker's own words.
CORRECTIONS = {"0:32.65": "That idea is the one to remember."}
