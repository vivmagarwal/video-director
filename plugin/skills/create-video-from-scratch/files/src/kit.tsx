import {loadFont} from '@remotion/fonts';
import React from 'react';
import {
	AbsoluteFill,
	Audio,
	Easing,
	interpolate,
	Sequence,
	staticFile,
	useCurrentFrame,
} from 'remotion';

// ---- Fonts: files on disk, so a render needs no font server. ----
export const FONT = 'Inter';
for (const weight of ['500', '800']) {
	loadFont({
		family: FONT,
		url: staticFile(`fonts/inter-latin-${weight}-normal.woff2`),
		weight,
	});
}

// ---- The look, in one place. These are examples: ask the user for theirs. ----
export const INK = '#1F2430';
export const MUTED = '#5B6270';
export const PAPER = '#FBF7EF';
export const ACCENT = '#C2410C';
const SETTLE = Easing.bezier(0.16, 1, 0.3, 1); // a fast start and a soft stop

// ---- The clock. ----
export const FPS = 30;
export const AIR = 12; // frames before a block's voice starts
export const TAIL = 18; // frames after a block's voice ends
export const OUTRO = 75; // extra frames on the last block, so the end is not abrupt

export type Word = {
	readonly text: string;
	readonly startMs: number;
	readonly endMs: number;
};
export type Block =
	| {readonly kind: 'card'; readonly frames: number}
	| {readonly kind: 'voice'; readonly caps: readonly Word[]; readonly extra?: number};

const toFrames = (ms: number) => Math.round((ms * FPS) / 1000);

/** Turns a list of blocks into start frames and lengths. Timings come from the voice. */
export const layout = (blocks: readonly Block[]) => {
	const at: number[] = [];
	const len: number[] = [];
	let t = 0;
	blocks.forEach((block, i) => {
		const body =
			block.kind === 'card'
				? block.frames
				: AIR + toFrames(block.caps[block.caps.length - 1].endMs) + TAIL + (block.extra ?? 0);
		const length = body + (i === blocks.length - 1 ? OUTRO : 0);
		at.push(t);
		len.push(length);
		t += length;
	});
	return {at, len, duration: t};
};

const tokens = (s: string) =>
	s
		.toLowerCase()
		.replace(/[’‘]/g, "'")
		.split(/[^\p{L}\p{N}']+/u)
		.filter(Boolean);

/**
 * The frame, on its block's clock, where a phrase starts being said.
 * Returns the FIRST match and throws when the phrase is never said.
 * So choose a phrase that is said once.
 */
export const cue = (caps: readonly Word[], phrase: string, early = 0): number => {
	const want = tokens(phrase);
	const said = caps.flatMap((word, index) => tokens(word.text).map((t) => ({t, index})));
	for (let i = 0; i + want.length <= said.length; i++) {
		if (want.every((w, k) => said[i + k].t === w)) {
			return Math.max(0, AIR + toFrames(caps[said[i].index].startMs) - early);
		}
	}
	throw new Error(
		`cue: "${phrase}" is not in this voice block. It says: "${caps.map((w) => w.text.trim()).join(' ')}"`,
	);
};

/** Fades and lifts its children in, counted from its parent Sequence's frame 0. */
export const Rise: React.FC<{
	readonly delay?: number;
	readonly children: React.ReactNode;
}> = ({delay = 0, children}) => {
	const frame = useCurrentFrame();
	const p = interpolate(frame - delay, [0, 18], [0, 1], {
		easing: SETTLE,
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	return <div style={{opacity: p, transform: `translateY(${(1 - p) * 24}px)`}}>{children}</div>;
};

/** One whole sentence on screen. The deep bottom padding leaves room for captions. Pass `centre` when there are none. */
export const Statement: React.FC<{readonly text: string; readonly centre?: boolean}> = ({text, centre = false}) => (
	<AbsoluteFill style={{justifyContent: 'center', padding: centre ? '84px 160px' : '84px 160px 220px'}}>
		<Rise>
			<div
				style={{
					color: INK,
					fontFamily: FONT,
					fontSize: 92,
					fontWeight: 800,
					letterSpacing: '-0.03em',
					lineHeight: 1.12,
				}}
			>
				{text}
			</div>
		</Rise>
	</AbsoluteFill>
);

/** Word captions. A word lights on its own start and never earlier. */
const Captions: React.FC<{readonly caps: readonly Word[]}> = ({caps}) => {
	const frame = useCurrentFrame();
	const pages: Word[][] = [[]];
	for (const word of caps) {
		pages[pages.length - 1].push(word);
		const count = pages[pages.length - 1].length;
		if (/[.?!]$/.test(word.text) || (/[,:;]$/.test(word.text) && count >= 3) || count === 7) {
			pages.push([]);
		}
	}
	const at = (ms: number) => AIR + toFrames(ms);
	const page = pages.find((p, i) => {
		if (p.length === 0) return false;
		const next = pages[i + 1]?.[0];
		const end = Math.min(
			at(p[p.length - 1].endMs) + 12,
			next ? at(next.startMs) : Number.MAX_SAFE_INTEGER,
		);
		return frame >= at(p[0].startMs) && frame < end;
	});
	if (!page) return null;
	return (
		<AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 108}}>
			<div
				style={{
					background: INK,
					borderRadius: 14,
					color: '#FFFFFF',
					fontFamily: FONT,
					fontSize: 44,
					fontWeight: 500,
					maxWidth: 1500,
					padding: '10px 26px',
					textAlign: 'center',
				}}
			>
				{page.map((word, i) => {
					const on = frame >= at(word.startMs) && frame < at(word.endMs);
					return (
						<span key={i} style={{color: on ? '#FDBA74' : '#FFFFFF'}}>
							{word.text.trim()}{' '}
						</span>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};

/** One voice block: its pictures, its sound and its captions, on one clock. */
export const Narrated: React.FC<{
	readonly audio: string;
	readonly caps: readonly Word[];
	readonly at: number;
	readonly len: number;
	readonly children: React.ReactNode;
}> = ({audio, caps, at, len, children}) => (
	<Sequence from={at} durationInFrames={len}>
		{children}
		<Sequence from={AIR} layout="none">
			<Audio src={staticFile(audio)} />
		</Sequence>
		<Captions caps={caps} />
	</Sequence>
);
