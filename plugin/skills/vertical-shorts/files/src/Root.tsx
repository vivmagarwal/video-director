import React from 'react';
import {Composition} from 'remotion';
import {Short, type ShortData} from './Short';
import shorts from './shorts.json';

export const Root: React.FC = () => (
	<>
		{(shorts as unknown as ShortData[]).map((d) => (
			<React.Fragment key={d.id}>
				<Composition id={`${d.id}-9x16`} component={Short} width={1080} height={1920} fps={d.fps} durationInFrames={d.durationInFrames} defaultProps={{data: d, guides: false}} />
				<Composition id={`${d.id}-4x5`} component={Short} width={1080} height={1350} fps={d.fps} durationInFrames={d.durationInFrames} defaultProps={{data: d, guides: false}} />
			</React.Fragment>
		))}
	</>
);
