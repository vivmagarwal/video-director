import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {Demo, DEMO_DURATION} from './Demo';
import {FPS} from './kit';

const Root: React.FC = () => (
	<Composition
		id="demo"
		component={Demo}
		durationInFrames={DEMO_DURATION}
		fps={FPS}
		height={1080}
		width={1920}
	/>
);

registerRoot(Root);
