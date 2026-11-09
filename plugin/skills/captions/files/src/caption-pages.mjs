// Turn word timings into pages (the groups of words shown together).
// The video and the .srt both use this file, so they always agree.
import {createTikTokStyleCaptions} from '@remotion/captions';

// True if this word is part of a phrase that must stay together, and not its first word.
const joinsPrevious = (captions, i, phrases) =>
	phrases.some((phrase) => {
		const words = phrase.split(' ');
		return words.some((_, k) => {
			const first = i - k;
			if (k === 0 || first < 0 || first + words.length > captions.length) {
				return false;
			}
			const seen = captions.slice(first, first + words.length).map((c) => c.text.trim().replace(/[.,?!;:]$/, ''));
			return seen.join(' ') === phrase;
		});
	});

// If the voice file spells a word for sound, put the real spelling back here,
// on what is shown and nowhere else. Add your own words.
export const show = (captions) =>
	captions.map((c) => ({...c, text: c.text.replace(/Tan-dor/g, 'Thandor')}));

const endsSentence = (c) => /[.?!]["”’]?$/.test(c.text.trim());

export const pagesFrom = (rawCaptions, {pageMs = 1800, pauseMs = 500, keepTogether = []} = {}) => {
	const captions = show(rawCaptions);
	const marked = captions.map((c, i) => {
		// The last word of a sentence stays with the word before it, so it is never alone.
		const lastWord = i > 0 && endsSentence(c) && !endsSentence(captions[i - 1]);
		return {
			...c,
			// A non-breaking space in front of a word means no line break and no page break there.
			text: lastWord || joinsPrevious(captions, i, keepTogether) ? `\u00A0${c.text.trimStart()}` : c.text,
			// End a page where a sentence ends, so pages break on meaning.
			pageBreakAfter: endsSentence(c),
		};
	});
	return createTikTokStyleCaptions({
		captions: marked,
		combineTokensWithinMilliseconds: pageMs,
		breakOnSilenceAfterMilliseconds: pauseMs,
	}).pages;
};
