// Write an .srt file and report any page that is hard to read.
//   node make-srt.mjs public/voice.captions.json out/voice.srt
import {readFileSync, writeFileSync} from 'node:fs';
import {serializeSrt} from '@remotion/captions';
import {pagesFrom} from './src/caption-pages.mjs';

const [input, output] = process.argv.slice(2);
const captions = JSON.parse(readFileSync(input, 'utf8'));
// A subtitle holds more words than a highlighted page: about 4 s, 2 lines.
const pages = pagesFrom(captions, {pageMs: 4000, pauseMs: 800});

const wrap = (text, max = 42) => {
	if (text.length <= max) {
		return text;
	}
	// Break at the space nearest the middle, so the two lines come out even.
	const spaces = [...text.matchAll(/ /g)].map((m) => m.index);
	const middle = spaces.reduce((a, b) => (Math.abs(b - text.length / 2) < Math.abs(a - text.length / 2) ? b : a));
	return `${text.slice(0, middle)}\n${text.slice(middle + 1)}`;
};

let problems = 0;
const lines = pages.map((p) => {
	const start = p.tokens[0].fromMs;
	const end = p.tokens[p.tokens.length - 1].toMs;
	const text = p.tokens.map((t) => t.text).join('').replace(/\u00A0/g, ' ').trim();
	const seconds = (end - start) / 1000;
	const report = (why) => {
		problems++;
		console.log(`${why}: ${seconds.toFixed(1)} s, ${text.length} characters: "${text}"`);
	};
	if (text.length > 84) report('too long (more than 2 lines of 42)');
	if (text.length / seconds > 17) report('too fast (more than 17 characters a second)');
	if (seconds < 0.833) report('too short (under 0.83 s)');
	if (seconds > 7) report('too long on screen (over 7 s)');
	return [{text: wrap(text), startMs: start, endMs: end, timestampMs: null, confidence: null}];
});
writeFileSync(output, serializeSrt({lines}) + '\n');
console.log(`${lines.length} subtitles written to ${output}. ${problems} to read again.`);
