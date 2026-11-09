import {loadFont} from '@remotion/fonts';
import React from 'react';
import {
	AbsoluteFill,
	Composition,
	Easing,
	interpolate,
	registerRoot,
	staticFile,
	useCurrentFrame,
} from 'remotion';

// Font files in public/fonts. Every weight you use needs its own file.
const fraunces = 'Fraunces';
const inter = 'Inter';
const space = 'Space Grotesk';
for (const [family, file, weight] of [
	[fraunces, 'fraunces-latin-700-normal.woff2', '700'],
	[inter, 'inter-latin-500-normal.woff2', '500'],
	[inter, 'inter-latin-800-normal.woff2', '800'],
	[space, 'space-grotesk-latin-500-normal.woff2', '500'],
	[space, 'space-grotesk-latin-700-normal.woff2', '700'],
]) {
	loadFont({family, url: staticFile(`fonts/${file}`), weight});
}

// Three looks for ONE frame of the real video. They are examples, not a menu:
// replace them with what the user's brand, samples or reference video suggest.
const DIRECTIONS = {
	'dir-paper': {ground: '#FBF7EF', ink: '#1F2430', muted: '#5B6270', accent: '#C2410C', display: fraunces, displayWeight: 700, text: inter},
	'dir-night': {ground: '#12151C', ink: '#F4F1EA', muted: '#9AA3B2', accent: '#F59E0B', display: inter, displayWeight: 800, text: inter},
	'dir-poster': {ground: '#FFD400', ink: '#111111', muted: '#111111', accent: '#111111', display: space, displayWeight: 700, text: space},
} as const;

type Look = (typeof DIRECTIONS)[keyof typeof DIRECTIONS];

const SETTLE = Easing.bezier(0.16, 1, 0.3, 1); // the default entrance: fast start, soft stop
const SAFE = 84; // pixels kept clear at 1920x1080

/** Draws the safe area. Turn it on for stills you review; never render it in the film. */
const SafeGuide: React.FC = () => (
	<AbsoluteFill style={{border: `${SAFE}px solid rgba(255,0,120,0.25)`, boxSizing: 'border-box'}} />
);

const Frame: React.FC<{readonly look: Look; readonly guide?: boolean}> = ({look, guide = false}) => {
	const frame = useCurrentFrame();
	const enter = (delay: number) =>
		interpolate(frame - delay, [0, 18], [0, 1], {
			easing: SETTLE,
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
		});
	const underline = enter(30);
	return (
		<AbsoluteFill style={{background: look.ground, padding: SAFE, justifyContent: 'center'}}>
			<div
				style={{
					color: look.muted,
					fontFamily: look.text,
					fontSize: 28,
					fontWeight: 500,
					letterSpacing: '0.24em',
					marginBottom: 28,
					opacity: enter(0),
					textTransform: 'uppercase',
				}}
			>
				Step one
			</div>
			<div
				style={{
					color: look.ink,
					fontFamily: look.display,
					fontSize: 140,
					fontWeight: look.displayWeight,
					letterSpacing: '-0.035em',
					lineHeight: 1.05,
					maxWidth: 1500,
					opacity: enter(6),
					transform: `translateY(${(1 - enter(6)) * 24}px)`,
				}}
			>
				Say one thing{' '}
				<span style={{whiteSpace: 'nowrap'}}>
					per{'\u00A0'}
					<span style={{position: 'relative', display: 'inline-block'}}>
						screen
						<span
							style={{
								background: look.accent,
								bottom: 6,
								height: 14,
								left: 0,
								position: 'absolute',
								transform: `scaleX(${underline})`,
								transformOrigin: 'left',
								width: '100%',
							}}
						/>
					</span>
				</span>
			</div>
			<div
				style={{
					color: look.muted,
					fontFamily: look.text,
					fontSize: 44,
					fontWeight: 500,
					marginTop: 40,
					maxWidth: 1200,
					opacity: enter(14),
				}}
			>
				The viewer reads this once, at a glance, while listening.
			</div>
			{guide ? <SafeGuide /> : null}
		</AbsoluteFill>
	);
};

registerRoot(() => (
	<>
		{Object.entries(DIRECTIONS).map(([id, look]) => (
			<Composition
				key={id}
				id={id}
				component={Frame}
				defaultProps={{look, guide: false}}
				durationInFrames={90}
				fps={30}
				height={1080}
				width={1920}
			/>
		))}
	</>
));
