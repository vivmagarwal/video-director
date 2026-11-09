import React from 'react';
import {AbsoluteFill, Composition, registerRoot, Sequence} from 'remotion';
import {FPS, layout, PAPER, Statement} from './kit';

const LINES = [
	'A video is a stack of still pictures.',
	'Thirty of them play every second.',
	'Change the plan, and every picture follows.',
];

// Reading time: at most 17 characters a second, plus a second to arrive.
const readFrames = (text: string) => Math.ceil((text.length / 17) * FPS) + FPS;

const L = layout(LINES.map((line) => ({kind: 'card' as const, frames: readFrames(line)})));

const Silent: React.FC = () => (
	<AbsoluteFill style={{background: PAPER}}>
		{LINES.map((line, i) => (
			<Sequence key={line} from={L.at[i]} durationInFrames={L.len[i]}>
				{/* centre: no captions sit below, so the text can use the middle of the frame. */}
				<Statement centre text={line} />
			</Sequence>
		))}
	</AbsoluteFill>
);

registerRoot(() => (
	<Composition id="silent" component={Silent} durationInFrames={L.duration} fps={FPS} height={1080} width={1920} />
));
