import React from 'react';
import {AbsoluteFill, Composition, registerRoot} from 'remotion';
import {SlowMove} from './SlowMove';

/** A background with something composited on top, and a soft contact shadow under it. */
const Shot: React.FC = () => (
	<AbsoluteFill>
		<SlowMove src="bg/room.png" from={1.04} to={1.1} originX="60%" originY="55%" blur={2} />
		<AbsoluteFill style={{alignItems: 'flex-end', justifyContent: 'flex-end', padding: '0 220px 150px'}}>
			<div
				style={{
					background: 'radial-gradient(closest-side, rgba(0,0,0,0.35), transparent)',
					bottom: 130,
					height: 50,
					position: 'absolute',
					right: 190,
					width: 400,
				}}
			/>
			<div style={{background: '#C2410C', borderRadius: 24, height: 420, width: 340}} />
		</AbsoluteFill>
	</AbsoluteFill>
);

registerRoot(() => (
	<Composition id="bg" component={Shot} durationInFrames={150} fps={30} height={1080} width={1920} />
));
