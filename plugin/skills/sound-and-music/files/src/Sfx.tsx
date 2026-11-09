import React from 'react';
import {Audio, Sequence, staticFile, useVideoConfig} from 'remotion';

// Plays a short sound so that its loudest moment lands one frame before `at`.
// peak comes from peak-time.py. gainDb is relative to the file's own level.
export const Sfx: React.FC<{
	readonly src: string;
	readonly at: number;
	readonly peak: number;
	readonly gainDb: number;
}> = ({src, at, peak, gainDb}) => {
	const {fps} = useVideoConfig();
	return (
		<Sequence from={at - Math.round(peak * fps) - 1} layout="none">
			<Audio src={staticFile(src)} volume={10 ** (gainDb / 20)} />
		</Sequence>
	);
};
