import '@fontsource/inter/600.css';
import '@fontsource/inter/800.css';
import '@fontsource/inter/900.css';
import React from 'react';
import {
	AbsoluteFill,
	Audio,
	Easing,
	interpolate,
	OffthreadVideo,
	Sequence,
	staticFile,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';

// This file only draws what src/shorts.json says. The look is an example:
// change the colours, type and layout to the user's own.
// Inter is an example, from local files. For another font: npm i @fontsource/<name>, and import its weights above.
const fontFamily = 'Inter';
const LOOK = {ground: '#111827', plate: '#111827', paper: '#ffffff', accent: '#fbbf24', soft: '#cbd5e1'};
const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const EASE = Easing.bezier(0.16, 1, 0.3, 1);

// The area text may use on 1080x1920. Starting points measured from each platform's
// ad template in September 2026. They change: check them before a batch.
export const PROFILES = {
	ad: {left: 120, right: 780, top: 288, bottom: 1248},
	organic: {left: 60, right: 888, top: 240, bottom: 1490},
} as const;

type View = {cx?: number; cy?: number; w?: number};
type Word = {text: string; from: number; hit: boolean};
export type ShortData = {
	id: string;
	profile: keyof typeof PROFILES;
	fps: number;
	durationInFrames: number;
	source: string;
	sourceSize: number[];
	view: View;
	voice?: string | null;
	hook: string[];
	clips: {from: number; dur: number; src: number; scale: number; seg: number}[];
	pages: {from: number; to: number; words: Word[]}[];
	slides: {from: number; dur: number; kicker?: string; title: string; lines?: string[]}[];
	pops: {from: number; dur: number; text: string; sub?: string}[];
	sfx: {from: number; src: string; volume?: number}[];
	plate?: {from: number; dur: number; name: string; role: string} | null;
	cta?: {line: string; sub?: string} | null;
};

// The layout rule that beat every other choice in testing: the picture sits in a
// full-width panel at the top, and every word sits on a band below it, so no word
// ever touches the face. The 4:5 export keeps the same band as a centre crop of the
// 9:16 would: y 285 to 1635.
const useBand = (profile: keyof typeof PROFILES) => {
	const {height} = useVideoConfig();
	const p = PROFILES[profile];
	const shift = (1920 - height) / 2;
	const bottomY = p.bottom - shift;
	const panel = bottomY - (profile === 'ad' ? 400 : 330);
	return {
		left: p.left,
		right: p.right,
		width: p.right - p.left,
		top: Math.max(0, p.top - shift),
		bottomInset: height - bottomY,
		panel,
		textTop: panel + 18,
	};
};

// Big type that still fits its band: about 0.66 of the size per character, in this font.
const fitted = (text: string, width: number, max: number) => Math.min(max, Math.floor(width / (0.66 * Math.max(1, text.length))));

const Picture: React.FC<{readonly d: ShortData}> = ({d}) => {
	const {panel} = useBand(d.profile);
	const [srcW, srcH] = d.sourceSize;
	const w = d.view.w ?? Math.min(srcW, (srcH * 1080) / panel);
	const fit = 1080 / w;
	const h = panel / fit;
	const left = Math.max(0, Math.min(srcW - w, (d.view.cx ?? srcW / 2) - w / 2));
	const top = Math.max(0, Math.min(srcH - h, (d.view.cy ?? srcH / 2) - h / 2));
	return (
		<div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: panel, overflow: 'hidden', backgroundColor: 'black'}}>
			{d.clips.map((c) => (
				<Sequence key={c.from} from={c.from} durationInFrames={c.dur + (c === d.clips[d.clips.length - 1] ? d.durationInFrames : 0)} premountFor={d.fps} layout="none">
					<div style={{position: 'absolute', inset: 0, transform: `scale(${c.scale})`, transformOrigin: '50% 35%'}}>
						<OffthreadVideo
							src={staticFile(d.source)}
							trimBefore={c.src}
							muted={Boolean(d.voice)}
							style={{position: 'absolute', left: -left * fit, top: -top * fit, width: srcW * fit, height: srcH * fit}}
						/>
					</div>
				</Sequence>
			))}
		</div>
	);
};

// Frame 0 is the poster: a face and the hook. No fade from black.
const HookCard: React.FC<{readonly d: ShortData; readonly opacity: number}> = ({d, opacity}) => {
	const band = useBand(d.profile);
	return (
		<div style={{position: 'absolute', left: band.left, top: band.textTop, width: band.width, opacity}}>
			{d.hook.map((line, i) => (
				<div key={line} style={{display: 'table', backgroundColor: i ? LOOK.accent : LOOK.plate, color: i ? LOOK.plate : LOOK.paper, fontSize: fitted(line, band.width - 40, 88), fontWeight: 900, lineHeight: 1.08, padding: '4px 20px', marginBottom: 6}}>
					{line}
				</div>
			))}
		</div>
	);
};

const Captions: React.FC<{readonly d: ShortData}> = ({d}) => {
	const frame = useCurrentFrame();
	const band = useBand(d.profile);
	const page = d.pages.find((p) => frame >= p.from && frame < p.to);
	if (!page) {
		return null;
	}

	const lit = page.words.reduce((n, w, i) => (frame >= w.from ? i : n), 0);
	return (
		<div style={{position: 'absolute', left: band.left, width: band.width, bottom: band.bottomInset, textAlign: 'center'}}>
			<span style={{backgroundColor: LOOK.plate, padding: '10px 22px', borderRadius: 12, fontSize: 80, fontWeight: 800, lineHeight: 1.28, boxDecorationBreak: 'clone', WebkitBoxDecorationBreak: 'clone'}}>
				{page.words.map((w, i) => (
					// eslint-disable-next-line react/no-array-index-key
					<span key={i} style={{color: i === lit || (w.hit && frame >= w.from) ? LOOK.accent : LOOK.paper}}>
						{i ? ' ' : ''}
						{w.text}
					</span>
				))}
			</span>
		</div>
	);
};

const enter = (frame: number, n = 8) => ({
	opacity: interpolate(frame, [0, 4], [0, 1], CLAMP),
	transform: `scale(${interpolate(frame, [0, n], [0.92, 1], {...CLAMP, easing: EASE})})`,
});

// A pop: 1 to 3 words at 110 to 180 px, on screen 0.6 to 1.0 s, entering over 6 to 10 frames
// with at most 10 % overshoot. These are starting points from one test.
const Pop: React.FC<{readonly d: ShortData; readonly pop: ShortData['pops'][number]}> = ({d, pop}) => {
	const frame = useCurrentFrame();
	const band = useBand(d.profile);
	return (
		<div style={{position: 'absolute', left: band.left, width: band.width, top: band.textTop, textAlign: 'center', ...enter(frame)}}>
			<span style={{backgroundColor: LOOK.accent, color: LOOK.plate, fontSize: fitted(pop.text, band.width - 44, 120), fontWeight: 900, padding: '4px 22px', lineHeight: 1.1}}>{pop.text}</span>
			{pop.sub ? <div style={{color: LOOK.paper, fontSize: 56, fontWeight: 800, marginTop: 10}}>{pop.sub}</div> : null}
		</div>
	);
};

const Slide: React.FC<{readonly d: ShortData; readonly slide: ShortData['slides'][number]}> = ({d, slide}) => {
	const frame = useCurrentFrame();
	const band = useBand(d.profile);
	const {height} = useVideoConfig();
	const out = interpolate(frame, [slide.dur - 6, slide.dur], [1, 0], CLAMP);
	return (
		<AbsoluteFill style={{backgroundColor: LOOK.ground, opacity: Math.min(interpolate(frame, [0, 5], [0, 1], CLAMP), out)}}>
			<div style={{position: 'absolute', left: band.left, width: band.width, top: band.top + 40, maxHeight: height - band.bottomInset - band.top - 200, color: LOOK.paper}}>
				{slide.kicker ? <div style={{color: LOOK.accent, fontSize: 44, fontWeight: 800, marginBottom: 18}}>{slide.kicker}</div> : null}
				<div style={{fontSize: 84, fontWeight: 900, lineHeight: 1.06, marginBottom: 26}}>{slide.title}</div>
				{(slide.lines ?? []).map((line, i) => (
					<div key={line} style={{fontSize: 52, fontWeight: 600, lineHeight: 1.2, marginBottom: 16, opacity: interpolate(frame, [6 + i * 8, 12 + i * 8], [0, 1], CLAMP)}}>
						{line}
					</div>
				))}
			</div>
		</AbsoluteFill>
	);
};

const Plate: React.FC<{readonly d: ShortData; readonly plate: NonNullable<ShortData['plate']>}> = ({d, plate}) => {
	const frame = useCurrentFrame();
	const band = useBand(d.profile);
	return (
		<div style={{position: 'absolute', left: band.left, top: band.panel - 136, ...enter(frame), backgroundColor: LOOK.plate, color: LOOK.paper, padding: '12px 24px', borderLeft: `8px solid ${LOOK.accent}`}}>
			<div style={{fontSize: 46, fontWeight: 800}}>{plate.name}</div>
			<div style={{fontSize: 34, fontWeight: 600, color: LOOK.soft}}>{plate.role}</div>
		</div>
	);
};

const Closing: React.FC<{readonly d: ShortData}> = ({d}) => {
	const frame = useCurrentFrame();
	const band = useBand(d.profile);
	if (!d.cta) {
		return null;
	}

	return (
		<div style={{position: 'absolute', left: band.left, width: band.width, top: band.textTop, ...enter(frame), backgroundColor: LOOK.paper, color: LOOK.plate, padding: '14px 24px', borderRadius: 14}}>
			<div style={{fontSize: 52, fontWeight: 900, lineHeight: 1.08}}>{d.cta.line}</div>
			{d.cta.sub ? <div style={{fontSize: 34, fontWeight: 600, marginTop: 6}}>{d.cta.sub}</div> : null}
		</div>
	);
};

const Guides: React.FC<{readonly d: ShortData}> = ({d}) => {
	const band = useBand(d.profile);
	const {height} = useVideoConfig();
	return (
		<div
			style={{
				position: 'absolute',
				left: band.left,
				top: band.top,
				width: band.width,
				height: height - band.top - band.bottomInset,
				boxShadow: 'inset 0 0 0 4px #22d3ee, 0 0 0 4000px rgba(239,68,68,.22)',
			}}
		/>
	);
};

export const Short: React.FC<{readonly data: ShortData; readonly guides?: boolean}> = ({data: d, guides}) => {
	const frame = useCurrentFrame();
	const end = d.durationInFrames;
	// The hook holds to 4.5 s, then the short has the screen. Its last 3 frames fade
	// frame 0's hook back in, so the end hands straight back to the start when it loops.
	const hook = Math.max(
		interpolate(frame, [4.2 * d.fps, 4.5 * d.fps], [1, 0], CLAMP),
		interpolate(frame, [end - 3, end - 1], [0, 1], CLAMP),
	);
	return (
		<AbsoluteFill style={{fontFamily, backgroundColor: LOOK.ground}}>
			<Picture d={d} />
			{d.voice ? <Audio src={staticFile(d.voice)} /> : null}
			{d.sfx.map((x) => (
				<Sequence key={`${x.from}${x.src}`} from={x.from} layout="none">
					<Audio src={staticFile(x.src)} volume={x.volume ?? 0.3} />
				</Sequence>
			))}
			{d.pops.map((p) => (
				<Sequence key={p.from} from={p.from} durationInFrames={p.dur} layout="none">
					<Pop d={d} pop={p} />
				</Sequence>
			))}
			{d.plate ? (
				<Sequence from={d.plate.from} durationInFrames={d.plate.dur} layout="none">
					<Plate d={d} plate={d.plate} />
				</Sequence>
			) : null}
			{d.slides.map((s) => (
				<Sequence key={s.from} from={s.from} durationInFrames={s.dur} layout="none">
					<Slide d={d} slide={s} />
				</Sequence>
			))}
			<Captions d={d} />
			<Sequence from={Math.max(0, end - Math.round(5 * d.fps))} layout="none">
				<Closing d={d} />
			</Sequence>
			{hook > 0 ? <HookCard d={d} opacity={hook} /> : null}
			{guides ? <Guides d={d} /> : null}
		</AbsoluteFill>
	);
};
