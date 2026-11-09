import '@fontsource/inter/400.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/800.css';
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
} from 'remotion';
import edit from './edit.json';

// This file only draws what edit.json says. Every decision is in edit/plan.py.
// Inter is an example, from local files. For another font: npm i @fontsource/<name>, and import its weights above.
const fontFamily = 'Inter';

// The look is an example. Change it to the user's own colours and type.
const LOOK = {ground: '#0f172a', card: '#f8fafc', ink: '#0f172a', paper: '#ffffff', accent: '#fbbf24', muted: '#94a3b8'};
const CAPTION_BOTTOM = 108; // keeps captions above YouTube's control bar
const CARD = {scale: 0.5, left: 84, top: 236}; // the card the picture shrinks into for a list
const EASE = Easing.bezier(0.16, 1, 0.3, 1);
const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

type Clip = {
	section: string;
	from: number;
	dur: number;
	src: number;
	scale: number;
	who?: string;
	view?: {source?: string; crop?: number[]};
};

const sources = edit.sources as Record<string, string>;
const sizes = edit.sizes as Record<string, number[]>;
const colors = edit.colors as Record<string, string>;

const ClipView: React.FC<{readonly clip: Clip}> = ({clip}) => {
	const key = clip.view?.source ?? 'main';
	const [srcW, srcH] = sizes[key];
	// A crop is [x, y, w, h] in source pixels: one speaker's tile, for example.
	const [x, y, w] = clip.view?.crop ?? [0, 0, srcW, srcH];
	const fit = edit.width / w;
	// A teaser shot steps left, but never so far that its right edge shows: with the
	// origin at 46 %, a zoom leaves 54 % of its extra width on that side.
	const shift = clip.section === 'teaser' ? Math.min(120, (clip.scale - 1) * edit.width * 0.54) : 0;
	return (
		<AbsoluteFill style={{overflow: 'hidden', backgroundColor: 'black'}}>
			<AbsoluteFill
				style={{
					transform: `translateX(${-shift}px) scale(${clip.scale})`,
					transformOrigin: '46% 38%',
				}}
			>
				<OffthreadVideo
					src={staticFile(sources[key])}
					trimBefore={clip.src}
					muted={Boolean(edit.voice)}
					style={{
						position: 'absolute',
						left: -x * fit,
						top: -y * fit,
						width: srcW * fit,
						height: srcH * fit,
					}}
				/>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

const listAmount = (frame: number): number => {
	for (const s of edit.lists) {
		if (frame >= s.from - 1 && frame < s.from + s.dur + 16) {
			const on = interpolate(frame, [s.from, s.from + 16], [0, 1], {...CLAMP, easing: EASE});
			const off = interpolate(frame, [s.from + s.dur, s.from + s.dur + 16], [1, 0], {...CLAMP, easing: EASE});
			return Math.min(on, off);
		}
	}

	return 0;
};

const Footage: React.FC = () => {
	const frame = useCurrentFrame();
	const p = listAmount(frame);
	return (
		<AbsoluteFill style={{backgroundColor: LOOK.ground}}>
			<AbsoluteFill
				style={{
					transformOrigin: '0 0',
					transform: `translate(${CARD.left * p}px, ${CARD.top * p}px) scale(${1 - (1 - CARD.scale) * p})`,
					borderRadius: 28 * p,
					overflow: 'hidden',
				}}
			>
				{(edit.clips as Clip[]).map((clip) => (
					<Sequence key={clip.from} from={clip.from} durationInFrames={clip.dur} premountFor={edit.fps}>
						<ClipView clip={clip} />
					</Sequence>
				))}
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

const rise = (frame: number, at = 0) => ({
	opacity: interpolate(frame, [at, at + 10], [0, 1], CLAMP),
	transform: `translateY(${interpolate(frame, [at, at + 14], [24, 0], {...CLAMP, easing: EASE})}px)`,
});

const Keyword: React.FC<{readonly item: (typeof edit.teaser)[number]}> = ({item}) => {
	const frame = useCurrentFrame();
	const side = item.side === 'left' ? {left: 90} : {right: 90};
	return (
		<div style={{position: 'absolute', top: 300, width: 760, ...side, ...rise(frame, 4), color: LOOK.paper, textShadow: '0 4px 40px rgba(0,0,0,.7)'}}>
			<div style={{fontSize: 56, fontWeight: 600}}>{item.keyword[0]}</div>
			<div style={{fontSize: 118, fontWeight: 800, lineHeight: 1.02, color: LOOK.accent}}>{item.keyword[1]}</div>
		</div>
	);
};

const Card: React.FC<{readonly kicker: string; readonly title: string; readonly sub?: string}> = ({kicker, title, sub}) => {
	const frame = useCurrentFrame();
	return (
		<AbsoluteFill style={{backgroundColor: LOOK.ground, color: LOOK.paper, justifyContent: 'center', padding: '0 160px'}}>
			<div style={{...rise(frame), fontSize: 34, fontWeight: 600, color: LOOK.accent, marginBottom: 20}}>{kicker}</div>
			<div style={{...rise(frame, 4), fontSize: 104, fontWeight: 800, lineHeight: 1.05, textWrap: 'balance'}}>{title}</div>
			{sub ? <div style={{...rise(frame, 10), fontSize: 42, marginTop: 28, color: LOOK.muted}}>{sub}</div> : null}
		</AbsoluteFill>
	);
};

const ListPanel: React.FC<{readonly list: (typeof edit.lists)[number]}> = ({list}) => {
	const frame = useCurrentFrame();
	return (
		<div style={{position: 'absolute', left: 1090, top: 180, width: 750, color: LOOK.paper}}>
			<div style={{...rise(frame, 6), fontSize: 30, fontWeight: 600, color: LOOK.accent}}>{list.kicker}</div>
			<div style={{...rise(frame, 8), fontSize: 60, fontWeight: 800, lineHeight: 1.08, marginBottom: 30, textWrap: 'balance'}}>{list.title}</div>
			{list.items.map((item) => (
				<div key={item.text} style={{...rise(frame, item.at), fontSize: 42, lineHeight: 1.25, marginBottom: 20}}>
					{item.text}
				</div>
			))}
		</div>
	);
};

const Quote: React.FC<{readonly quote: (typeof edit.quotes)[number]}> = ({quote}) => {
	const frame = useCurrentFrame();
	return (
		<AbsoluteFill style={{backgroundColor: LOOK.card, color: LOOK.ink, justifyContent: 'center', padding: '0 170px', opacity: interpolate(frame, [0, 8], [0, 1], CLAMP)}}>
			{quote.lines.map((line, i) => (
				<div key={line} style={{...rise(frame, i * 8), fontSize: 92, fontWeight: 800, lineHeight: 1.12}}>
					{line}
				</div>
			))}
		</AbsoluteFill>
	);
};

const Plate: React.FC<{readonly plate: (typeof edit.plates)[number]}> = ({plate}) => {
	const frame = useCurrentFrame();
	return (
		<div style={{position: 'absolute', left: 90, bottom: 240, ...rise(frame), backgroundColor: LOOK.ink, color: LOOK.paper, padding: '16px 30px', borderRadius: 10}}>
			<div style={{fontSize: 40, fontWeight: 800}}>{plate.name}</div>
			<div style={{fontSize: 28, color: LOOK.muted}}>{plate.role}</div>
		</div>
	);
};

const Chat: React.FC<{readonly chat: (typeof edit.chats)[number]}> = ({chat}) => {
	const frame = useCurrentFrame();
	return (
		<div style={{position: 'absolute', right: 90, top: 90, width: 720, ...rise(frame), backgroundColor: LOOK.card, color: LOOK.ink, padding: '24px 30px', borderRadius: 16}}>
			<div style={{fontSize: 28, fontWeight: 600, marginBottom: 8}}>{chat.name}</div>
			<div style={{fontSize: 38, lineHeight: 1.25}}>{chat.text}</div>
		</div>
	);
};

const Captions: React.FC = () => {
	const frame = useCurrentFrame();
	const page = edit.pages.find((p) => frame >= p.from && frame < p.to) as
		| {words: {t: string; from: number; hit: boolean}[]; who?: string}
		| undefined;
	if (!page) {
		return null;
	}

	const spoken = (page.who && colors[page.who]) || LOOK.accent; // one colour per person, in every chapter
	return (
		<div style={{position: 'absolute', left: 240, right: 240, bottom: CAPTION_BOTTOM, textAlign: 'center'}}>
			<span style={{backgroundColor: 'rgba(15,23,42,.82)', padding: '8px 18px', borderRadius: 10, fontSize: 46, fontWeight: 600, lineHeight: 1.45, boxDecorationBreak: 'clone', WebkitBoxDecorationBreak: 'clone'}}>
				{page.words.map((w, i) => (
					// eslint-disable-next-line react/no-array-index-key
					<span key={i} style={{color: frame >= w.from && (w.hit || i === page.words.findLastIndex((x) => frame >= x.from)) ? spoken : LOOK.paper}}>
						{i ? ' ' : ''}
						{w.t}
					</span>
				))}
			</span>
		</div>
	);
};

const Progress: React.FC = () => {
	const frame = useCurrentFrame();
	const {from, to} = edit.body;
	const p = interpolate(frame, [from, to], [0, 1], CLAMP);
	if (frame < from || frame >= to) {
		return null;
	}

	return (
		<div style={{position: 'absolute', left: 0, right: 0, top: 0, height: 6, backgroundColor: 'rgba(255,255,255,.18)'}}>
			<div style={{width: `${p * 100}%`, height: '100%', backgroundColor: LOOK.accent}} />
			{edit.chapters.map((c) => (
				<div key={c.from} style={{position: 'absolute', top: 0, height: 6, width: 3, backgroundColor: LOOK.paper, left: `${((c.from - from) / (to - from)) * 100}%`}} />
			))}
		</div>
	);
};

const At: React.FC<{readonly from: number; readonly dur: number; readonly children: React.ReactNode}> = ({from, dur, children}) =>
	dur > 0 ? (
		<Sequence from={from} durationInFrames={dur} layout="none">
			{children}
		</Sequence>
	) : null;

export const Film: React.FC = () => (
	<AbsoluteFill style={{fontFamily, backgroundColor: LOOK.ground}}>
		<Footage />
		{edit.voice ? <Audio src={staticFile(edit.voice)} /> : null}
		{edit.bed
			? [edit.title, ...edit.chapters, edit.end].map((c) => (
					<Sequence key={c.from} from={c.from} durationInFrames={c.dur}>
						<Audio src={staticFile(edit.bed as string)} volume={0.5} />
					</Sequence>
				))
			: null}
		{edit.teaser.map((item) => (
			<At key={item.from} from={item.from} dur={item.dur}>
				<Keyword item={item} />
			</At>
		))}
		{edit.lists.map((l) => (
			<At key={l.from} from={l.from} dur={l.dur}>
				<ListPanel list={l} />
			</At>
		))}
		{edit.quotes.map((q) => (
			<At key={q.from} from={q.from} dur={q.dur}>
				<Quote quote={q} />
			</At>
		))}
		<Progress />
		<Captions />
		{edit.plates.map((p) => (
			<At key={p.from} from={p.from} dur={p.dur}>
				<Plate plate={p} />
			</At>
		))}
		{edit.chats.map((c) => (
			<At key={c.from} from={c.from} dur={c.dur}>
				<Chat chat={c} />
			</At>
		))}
		<At from={edit.title.from} dur={edit.title.dur}>
			<Card kicker={edit.title.kicker} title={edit.title.title} sub={edit.title.sub} />
		</At>
		{edit.chapters.map((c) => (
			<At key={c.from} from={c.from} dur={c.dur}>
				<Card kicker={c.number} title={c.title} sub={c.subtitle} />
			</At>
		))}
		<At from={edit.end.from} dur={edit.end.dur}>
			<Card kicker={edit.end.kicker} title={edit.end.title} sub={edit.end.sub} />
		</At>
	</AbsoluteFill>
);
