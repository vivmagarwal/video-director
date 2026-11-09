import React from 'react';
import {
	AbsoluteFill,
	OffthreadVideo,
	random,
	Sequence,
	staticFile,
	useCurrentFrame,
} from 'remotion';
import n1 from '../public/demo/n1.captions.json';
import n2 from '../public/demo/n2.captions.json';
import {ACCENT, cue, FONT, INK, layout, MUTED, Narrated, PAPER, Rise, Statement} from './kit';

const L = layout([
	{kind: 'card', frames: 60},
	{kind: 'voice', caps: n1},
	{kind: 'voice', caps: n2},
]);

// Every cut is a phrase, never a typed frame number. A new voice re-times the video.
const EACH_SECOND = cue(n1, 'Each second');
const PLAN = cue(n2, 'the plan');
const PICTURES = cue(n2, 'the pictures');
const SOUND = cue(n2, 'the sound');
const CLIP = cue(n2, 'Here is a moving clip');
const CLIP_FRAMES = 120; // public/demo/clip.mp4 is 4 s long at 30 frames a second

const Thirty: React.FC = () => {
	const frame = useCurrentFrame();
	return (
		<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', paddingBottom: 200}}>
			<div
				style={{
					display: 'grid',
					gap: 14,
					gridTemplateColumns: 'repeat(10, 96px)',
					marginBottom: 44,
				}}
			>
				{Array.from({length: 30}, (_, i) => (
					<div
						key={i}
						style={{
							background: ACCENT,
							borderRadius: 8,
							height: 72,
							// random() with a seed gives the same value on every render. Math.random() does not.
							opacity: frame >= i ? 0.55 + 0.45 * random(`tile-${i}`) : 0,
						}}
					/>
				))}
			</div>
			<div style={{color: INK, fontFamily: FONT, fontSize: 62, fontWeight: 800}}>
				{'Thirty\u00A0pictures, every\u00A0second'}
			</div>
		</AbsoluteFill>
	);
};

/** A box that appears on the frame the narrator names it, and no earlier. */
const Part: React.FC<{readonly name: string; readonly from: number}> = ({name, from}) => (
	<div style={{height: 260, width: 460}}>
		<Sequence from={from} layout="none">
			<Rise>
				<div
					style={{
						alignItems: 'center',
						border: `6px solid ${ACCENT}`,
						borderRadius: 24,
						color: INK,
						display: 'flex',
						fontFamily: FONT,
						fontSize: 62,
						fontWeight: 800,
						height: 260,
						justifyContent: 'center',
					}}
				>
					{name}
				</div>
			</Rise>
		</Sequence>
	</div>
);

export const Demo: React.FC = () => (
	<AbsoluteFill style={{background: PAPER}}>
		<Sequence from={L.at[0]} durationInFrames={L.len[0]}>
			<Statement text={'How a video is\u00A0made'} />
		</Sequence>

		<Narrated audio="demo/n1.wav" caps={n1} at={L.at[1]} len={L.len[1]}>
			<Sequence durationInFrames={EACH_SECOND}>
				<Statement text={'A video is a stack of still\u00A0pictures.'} />
			</Sequence>
			<Sequence from={EACH_SECOND}>
				<Thirty />
			</Sequence>
		</Narrated>

		<Narrated audio="demo/n2.wav" caps={n2} at={L.at[2]} len={L.len[2]}>
			<Sequence durationInFrames={CLIP}>
				<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', paddingBottom: 200}}>
					<div style={{color: MUTED, fontFamily: FONT, fontSize: 62, fontWeight: 800, marginBottom: 56}}>
						Three parts
					</div>
					<div style={{display: 'flex', gap: 48}}>
						<Part name="The plan" from={PLAN} />
						<Part name="The pictures" from={PICTURES} />
						<Part name="The sound" from={SOUND} />
					</div>
				</AbsoluteFill>
			</Sequence>
			<Sequence from={CLIP} durationInFrames={CLIP_FRAMES}>
				<AbsoluteFill style={{alignItems: 'center', paddingTop: 84}}>
					<OffthreadVideo
						muted
						src={staticFile('demo/clip.mp4')}
						style={{borderRadius: 18, height: 720, width: 1280}}
					/>
				</AbsoluteFill>
			</Sequence>
			<Sequence from={CLIP + CLIP_FRAMES}>
				<Statement text={'Change the plan, and every\u00A0picture follows.'} />
			</Sequence>
		</Narrated>
	</AbsoluteFill>
);

export const DEMO_DURATION = L.duration;
