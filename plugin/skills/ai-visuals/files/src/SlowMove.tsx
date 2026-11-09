import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

/**
 * A slow camera move on one still. Costs nothing per second and re-times with the voice.
 * `from` and `to` are scales. Keep both above 1 when you also pan, or the frame edge shows.
 * Linear on purpose: an eased camera move reads as a stumble.
 */
export const SlowMove: React.FC<{
	readonly src: string;
	readonly from?: number;
	readonly to?: number;
	readonly panX?: number; // pixels the picture travels sideways over the whole shot
	readonly originX?: string; // put this on the subject, not the frame centre
	readonly originY?: string;
	readonly blur?: number; // pixels of soft focus, so things on top stand out
}> = ({src, from = 1.04, to = 1.1, panX = 0, originX = '50%', originY = '50%', blur = 0}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const p = interpolate(frame, [0, durationInFrames - 1], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	return (
		<AbsoluteFill style={{overflow: 'hidden'}}>
			<Img
				src={staticFile(src)}
				style={{
					filter: blur ? `blur(${blur}px)` : undefined,
					height: '100%',
					objectFit: 'cover',
					transform: `translateX(${panX * (p - 0.5)}px) scale(${from + (to - from) * p})`,
					transformOrigin: `${originX} ${originY}`,
					width: '100%',
				}}
			/>
		</AbsoluteFill>
	);
};
