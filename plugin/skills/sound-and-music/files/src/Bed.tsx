import React, {useMemo} from 'react';
import {Audio, interpolate, staticFile, useVideoConfig} from 'remotion';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Sets one music file under a whole film. speech is a sorted list of
// [firstFrame, lastFrame] for each spoken stretch, in composition frames.
// openDb and duckedDb are gains in dB on the file's own level.
export const Bed: React.FC<{
	readonly src: string;
	readonly speech: readonly (readonly [number, number])[];
	readonly openDb: number;
	readonly duckedDb: number;
}> = ({src, speech, openDb, duckedDb}) => {
	const {fps, durationInFrames} = useVideoConfig();
	// Speech less than 1.2 s apart is one stretch, so the music never lifts into a comma.
	const ranges = useMemo(() => {
		const out: [number, number][] = [];
		for (const [a, b] of speech) {
			const last = out[out.length - 1];
			if (last && a - last[1] < 1.2 * fps) {
				last[1] = Math.max(last[1], b);
			} else {
				out.push([a, b]);
			}
		}
		return out;
	}, [speech, fps]);
	const lead = Math.round(0.4 * fps);
	const release = Math.round(0.6 * fps);
	return (
		<Audio
			src={staticFile(src)}
			loop
			// Without this the curve restarts each time the file loops, and the fade-out never plays.
			loopVolumeCurveBehavior="extend"
			volume={(f) => {
				let depth = 0;
				for (const [a, b] of ranges) {
					const down = interpolate(f, [a - lead, a], [0, 1], clamp);
					const up = interpolate(f, [b, b + release], [1, 0], clamp);
					depth = Math.max(depth, Math.min(down, up));
				}
				const edges =
					interpolate(f, [0, 24], [0, 1], clamp) *
					interpolate(f, [durationInFrames - 24, durationInFrames - 1], [1, 0], clamp);
				// Work in decibels and convert once.
				return edges * 10 ** ((openDb + (duckedDb - openDb) * depth) / 20);
			}}
		/>
	);
};
