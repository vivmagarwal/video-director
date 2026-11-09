import React from 'react';
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {ACCENT, FONT, INK, MUTED, PAPER, Rise} from './kit';

// Where the line goes, in pixels on a 1920x1080 frame. Invented numbers.
const POINTS = [[220, 800], [520, 730], [820, 750], [1120, 560], [1420, 480], [1700, 300]];
const DRAW_FROM = 15; // frames: the line starts here
const DRAW_TO = 105; // and reaches its end here

// How far along the line each point sits, from 0 to 1. The dot needs this to stay on the line.
const parts = POINTS.slice(1).map(([x, y], i) => Math.hypot(x - POINTS[i][0], y - POINTS[i][1]));
const total = parts.reduce((a, b) => a + b, 0);
const stops = parts.reduce((list, part) => [...list, list[list.length - 1] + part / total], [0]);

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const LineDiagram: React.FC = () => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	// progress: 0 at the start of the line, 1 at its end.
	const p = interpolate(frame, [DRAW_FROM, DRAW_TO], [0, 1], {
		...clamp,
		easing: Easing.bezier(0.65, 0, 0.35, 1),
	});
	const dotX = interpolate(p, stops, POINTS.map((q) => q[0]), clamp);
	const dotY = interpolate(p, stops, POINTS.map((q) => q[1]), clamp);
	// spring() with a config, so it settles with no bounce. It starts when the line lands.
	const label = spring({frame: frame - DRAW_TO, fps, config: {damping: 200}});
	return (
		<AbsoluteFill style={{background: PAPER}}>
			<svg viewBox="0 0 1920 1080" style={{height: '100%', width: '100%'}}>
				<line x1={220} y1={860} x2={1700} y2={860} stroke={MUTED} strokeWidth={4} />
				{/* pathLength={1} lets the dash numbers run from 0 to 1, whatever the line's real length. */}
				<polyline
					points={POINTS.map((q) => q.join(',')).join(' ')}
					fill="none"
					stroke={ACCENT}
					strokeLinejoin="round"
					strokeWidth={12}
					pathLength={1}
					strokeDasharray={1}
					strokeDashoffset={1 - p}
				/>
				{p > 0 ? <circle cx={dotX} cy={dotY} r={22} fill={ACCENT} /> : null}
			</svg>
			<div style={{left: 220, position: 'absolute', top: 96}}>
				<Rise delay={-8}>
					<div style={{color: INK, fontFamily: FONT, fontSize: 92, fontWeight: 800, letterSpacing: '-0.03em'}}>
						Sign-ups climbed
					</div>
				</Rise>
			</div>
			<div
				style={{
					color: INK,
					fontFamily: FONT,
					fontSize: 62,
					fontWeight: 800,
					left: 1330,
					opacity: label,
					position: 'absolute',
					top: 160,
					transform: `translateY(${(1 - label) * 24}px)`,
				}}
			>
				Four times over
			</div>
		</AbsoluteFill>
	);
};
