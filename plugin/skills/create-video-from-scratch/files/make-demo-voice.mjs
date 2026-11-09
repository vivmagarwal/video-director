// A stand-in voice: one soft tone per word, plus word timings.
// It is NOT speech. It lets you build and time a video before any voice exists.
// Usage: node make-demo-voice.mjs public/demo/n1.txt public/demo/n2.txt
// Writes n1.wav and n1.captions.json beside each .txt file.
import {readFileSync, writeFileSync} from 'node:fs';

const RATE = 44100;

for (const path of process.argv.slice(2)) {
	const words = readFileSync(path, 'utf8').trim().split(/\s+/);
	const captions = [];
	const samples = [];
	let ms = 0;
	const silence = (length) => {
		for (let i = 0; i < (length * RATE) / 1000; i++) samples.push(0);
		ms += length;
	};
	for (const text of words) {
		const length = 120 + 45 * text.length;
		const count = Math.round((length * RATE) / 1000);
		for (let i = 0; i < count; i++) {
			const fade = Math.min(1, i / 400, (count - i) / 400);
			samples.push(0.25 * fade * Math.sin((2 * Math.PI * 220 * i) / RATE));
		}
		// Every word after the first starts with a space, the shape @remotion/captions expects.
		captions.push({text: (captions.length ? ' ' : '') + text, startMs: ms, endMs: ms + length});
		ms += length;
		silence(/[.?!]$/.test(text) ? 420 : /[,:;]$/.test(text) ? 180 : 60);
	}
	const data = Buffer.alloc(samples.length * 2);
	samples.forEach((s, i) => data.writeInt16LE(Math.round(s * 32767), i * 2));
	const head = Buffer.alloc(44);
	head.write('RIFF', 0);
	head.writeUInt32LE(36 + data.length, 4);
	head.write('WAVEfmt ', 8);
	head.writeUInt32LE(16, 16);
	head.writeUInt16LE(1, 20);
	head.writeUInt16LE(1, 22);
	head.writeUInt32LE(RATE, 24);
	head.writeUInt32LE(RATE * 2, 28);
	head.writeUInt16LE(2, 32);
	head.writeUInt16LE(16, 34);
	head.write('data', 36);
	head.writeUInt32LE(data.length, 40);
	const base = path.replace(/\.txt$/, '');
	writeFileSync(`${base}.wav`, Buffer.concat([head, data]));
	writeFileSync(`${base}.captions.json`, JSON.stringify(captions, null, 1));
	console.log(`${base}.wav  ${(ms / 1000).toFixed(1)} s, ${words.length} words`);
}
