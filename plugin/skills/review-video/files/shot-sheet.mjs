#!/usr/bin/env node
// Renders stills from a Remotion composition and tiles them into labelled
// contact sheets, so you can look at a whole video before rendering it.
//
//   node shot-sheet.mjs <entry> <composition> [options]
//
//   --every=3            one still every N seconds, starting half a step in (default 3)
//   --frames=40,150,310  these exact frames instead
//   --cols=5             tiles across (default 5)
//   --rows=4             tiles down, per sheet (default 4)
//   --scale=0.5          render scale of each still (default 0.5)
//   --tile=640           width of each tile in pixels (default 640)
//   --crop=w:h:x:y       crop each still before tiling, in scaled pixels
//   --gl=angle           Chrome's GL backend (default angle)
//   --timeout=120000     milliseconds a still may take
//   --browser=<path>     a Chrome Headless Shell to use instead of Remotion's own
//   --out=out/sheets     output folder (default out/sheets)
//
// Needs: @remotion/bundler and @remotion/renderer at the same version as remotion,
// and a full ffmpeg on PATH. The Node API does not read remotion.config.ts, which
// is why the GL backend is passed here.
import {execFileSync} from 'node:child_process';
import {mkdirSync, rmSync} from 'node:fs';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';

const option = (name, fallback) => {
	const hit = process.argv.find((a) => a.startsWith(`--${name}=`));
	return hit ? hit.slice(name.length + 3) : fallback;
};

const [entry, id] = process.argv.slice(2).filter((a) => !a.startsWith('--'));
if (!entry || !id) {
	console.error('Usage: node shot-sheet.mjs <entry> <composition> [--every=3] [--frames=40,150] [--cols=5] [--rows=4] [--scale=0.5] [--tile=640] [--crop=w:h:x:y] [--gl=angle] [--browser=<path>] [--out=out/sheets]');
	process.exit(1);
}

const cols = Number(option('cols', 5));
const rows = Number(option('rows', 4));
const scale = Number(option('scale', 0.5));
const tile = Number(option('tile', 640));
const crop = option('crop', null);
const outDir = option('out', 'out/sheets');
const browserExecutable = option('browser', null);
const chromiumOptions = {gl: option('gl', 'angle')};

const scratch = path.join(outDir, `.${id}-stills`);
rmSync(scratch, {recursive: true, force: true});
mkdirSync(scratch, {recursive: true});

const started = Date.now();
const serveUrl = await bundle({entryPoint: path.resolve(entry)});
const browser = await openBrowser('chrome', {browserExecutable, chromiumOptions});

const composition = await selectComposition({
	serveUrl,
	id,
	puppeteerInstance: browser,
	chromiumOptions,
	browserExecutable,
});

const asked = option('frames', null);
const stepFrames = Math.round(Number(option('every', 3)) * composition.fps);
const frames = asked
	? asked.split(',').map(Number)
	: Array.from(
			{length: Math.max(1, Math.floor(composition.durationInFrames / stepFrames))},
			(_, i) => Math.round(stepFrames / 2) + i * stepFrames,
		);

const bad = frames.filter((f) => !Number.isInteger(f) || f < 0 || f >= composition.durationInFrames);
if (bad.length > 0) {
	await browser.close({silent: true});
	console.error(`These frames are not in "${id}" (0 to ${composition.durationInFrames - 1}): ${bad.join(', ')}`);
	process.exit(1);
}

const renderStart = Date.now();
const stills = [];
for (const frame of frames) {
	const output = path.join(scratch, `${String(frame).padStart(6, '0')}.png`);
	await renderStill({
		composition,
		serveUrl,
		output,
		frame,
		scale,
		puppeteerInstance: browser,
		chromiumOptions,
		browserExecutable,
		timeoutInMilliseconds: Number(option('timeout', 120000)),
	});
	stills.push({frame, output});
	process.stdout.write('.');
}
process.stdout.write('\n');
await browser.close({silent: true});
const secondsEach = (Date.now() - renderStart) / 1000 / frames.length;

let hasDrawtext = execFileSync('ffmpeg', ['-hide_banner', '-filters'], {encoding: 'utf8'}).includes(' drawtext ');
const clock = (frame) => {
	const s = Math.floor(frame / composition.fps);
	return `${Math.floor(s / 60)}\\:${String(s % 60).padStart(2, '0')}`;
};

const perSheet = cols * rows;
const sheets = [];
for (let n = 0; n * perSheet < stills.length; n++) {
	const group = stills.slice(n * perSheet, (n + 1) * perSheet);
	const inputs = group.flatMap((s) => ['-i', s.output]);
	const file = path.join(outDir, `${id}-${String(n + 1).padStart(2, '0')}.png`);
	const makeSheet = (labelled) => {
		const label = (s) =>
			labelled
				? `,drawtext=text='f${s.frame} ${clock(s.frame)}':x=8:y=8:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=6`
				: '';
		const chains = group.map(
			(s, i) => `[${i}:v]${crop ? `crop=${crop},` : ''}scale=${tile}:-2${label(s)}[t${i}]`,
		);
		// Spare cells are mid grey, so nobody reads them as a black frame in the video.
		const graph = `${chains.join(';')};${group.map((_, i) => `[t${i}]`).join('')}concat=n=${group.length}:v=1:a=0,tile=${cols}x${rows}:padding=4:color=0x8A8A8A`;
		execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...inputs, '-filter_complex', graph, '-frames:v', '1', file], {
			stdio: ['ignore', 'ignore', 'pipe'],
		});
	};
	try {
		makeSheet(hasDrawtext);
	} catch (err) {
		if (!hasDrawtext) throw err;
		// drawtext exists but found no font on this machine. Make the sheet without labels.
		hasDrawtext = false;
		makeSheet(false);
	}
	sheets.push({file, frames: group.map((s) => s.frame)});
}
rmSync(scratch, {recursive: true, force: true});

for (const {file, frames: shown} of sheets) {
	console.log(`${file}, frames in reading order:`);
	for (let r = 0; r < rows && r * cols < shown.length; r++) {
		console.log(`  ${shown.slice(r * cols, (r + 1) * cols).join('  ')}`);
	}
}
if (!hasDrawtext) {
	console.log('This ffmpeg could not draw labels, so the tiles carry none. Read the frame order above.');
}
console.log(`${frames.length} stills, ${secondsEach.toFixed(2)} s each, ${((Date.now() - started) / 1000).toFixed(1)} s in all.`);
