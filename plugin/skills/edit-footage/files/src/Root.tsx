import React from 'react';
import {Composition} from 'remotion';
import edit from './edit.json';
import {Film} from './Film';

export const Root: React.FC = () => (
	<Composition id="film" component={Film} width={edit.width} height={edit.height} fps={edit.fps} durationInFrames={edit.durationInFrames} />
);
