import React, {useMemo} from 'react';
import {AbsoluteFill, continueRender, delayRender, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Caption} from '@remotion/captions';
// The font comes from an npm package, so a render needs no font host.
import '@fontsource/inter/700.css';
// @ts-expect-error a small plain JS file, shared with make-srt.mjs
import {pagesFrom} from './caption-pages.mjs';

const fontFamily = 'Inter';
// Hold the render until the font is ready, so no frame is drawn in a fallback font.
const fontWait = delayRender('Loading the caption font');
document.fonts.load(`700 56px ${fontFamily}`).finally(() => continueRender(fontWait));

type Token = {text: string; fromMs: number; toMs: number};
type Page = {text: string; startMs: number; tokens: Token[]; durationMs: number};

export const Captions: React.FC<{
	readonly captions: Caption[];
	/** The frame the voice starts on in this composition. */
	readonly voiceStartsAt?: number;
	/** Pixels from the bottom of the frame to the bottom of the text. */
	readonly bottomInset?: number;
	/** Pixels kept clear on the left and on the right. */
	readonly left?: number;
	readonly right?: number;
	readonly fontSize?: number;
	readonly color?: string;
	readonly activeColor?: string;
	/** Phrases that must not split across a line or a page, as written in the captions. */
	readonly keepTogether?: string[];
}> = ({
	captions,
	voiceStartsAt = 0,
	bottomInset = 108,
	left = 200,
	right = 200,
	fontSize = 56,
	color = '#ffffff',
	activeColor = '#ffd84d',
	keepTogether = [],
}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const joined = keepTogether.join('|');
	const pages = useMemo<Page[]>(
		() => pagesFrom(captions, {keepTogether: joined ? joined.split('|') : []}),
		[captions, joined],
	);
	// Convert once, at the edge: milliseconds to frames, with Math.round.
	const toFrame = (ms: number) => voiceStartsAt + Math.round((ms / 1000) * fps);

	const page = pages.find((p, i) => {
		const start = toFrame(p.startMs);
		// Stay 12 frames after the last word, then clear. Never run into the next page.
		const last = toFrame(p.tokens[p.tokens.length - 1].toMs) + 12;
		const next = i + 1 < pages.length ? toFrame(pages[i + 1].startMs) : Infinity;
		return frame >= start && frame < Math.min(last, next);
	});
	if (!page) {
		return null;
	}

	return (
		<AbsoluteFill
			style={{
				justifyContent: 'flex-end',
				alignItems: 'center',
				paddingBottom: bottomInset,
				paddingLeft: left,
				paddingRight: right,
			}}
		>
			<div
				style={{
					fontFamily,
					fontSize,
					fontWeight: 700,
					lineHeight: 1.25,
					textAlign: 'center',
					// pre-wrap keeps each word's leading space and still lets a long page wrap.
					whiteSpace: 'pre-wrap',
					textWrap: 'balance',
					// A black edge reads on any picture. A drop shadow alone does not.
					WebkitTextStroke: `${Math.round(fontSize * 0.15)}px #000`,
					paintOrder: 'stroke fill',
				}}
			>
				{page.tokens.map((t) => {
					// A half-open range, so two words never light up on one frame.
					const active = frame >= toFrame(t.fromMs) && frame < toFrame(t.toMs);
					return (
						<span key={t.fromMs} style={{color: active ? activeColor : color}}>
							{t.text}
						</span>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};
