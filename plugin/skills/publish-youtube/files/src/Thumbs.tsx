import '@fontsource/inter/900.css';
import React from 'react';
import {AbsoluteFill, Img, staticFile, Still} from 'remotion';

// Inter is an example, from local files. For another font: npm i @fontsource/<name>, and import its weight above.
const fontFamily = 'Inter';

type Props = {
	readonly words: string; // four bold words or fewer: the thesis, not the title again
	readonly face: string; // a frame under public/
	readonly focus: string; // which part of the frame stays in view, as CSS object-position
	readonly ground: string;
	readonly ink: string;
	readonly accent: string;
};

const Thumb: React.FC<Props> = ({words, face, focus, ground, ink, accent}) => {
	const parts = words.split(' ');
	return (
		<AbsoluteFill style={{backgroundColor: ground, fontFamily}}>
			<Img src={staticFile(face)} style={{position: 'absolute', top: 0, right: 0, width: 640, height: 720, objectFit: 'cover', objectPosition: focus}} />
			{/* Text top left, clear of the bottom-right corner, where YouTube prints the running time. */}
			<div style={{position: 'absolute', left: 48, top: 44, width: 570, color: ink, fontWeight: 900, fontSize: 104, lineHeight: 1.0}}>
				{parts.slice(0, -1).join(' ')} <span style={{color: accent}}>{parts[parts.length - 1]}</span>
			</div>
		</AbsoluteFill>
	);
};

// Colours and words are examples. Make three real options with the user's own.
const dark = {ground: '#111827', ink: '#ffffff', accent: '#fbbf24'};
export const ThumbStills: React.FC = () => (
	<>
		<Still id="thumb-a" component={Thumb} width={1280} height={720} defaultProps={{...dark, words: 'First is heavy', face: 'thumbs/face-a.jpg', focus: '58% 20%'}} />
		<Still id="thumb-b" component={Thumb} width={1280} height={720} defaultProps={{...dark, words: 'Who goes first?', face: 'thumbs/face-b.jpg', focus: '58% 20%'}} />
		<Still id="thumb-c" component={Thumb} width={1280} height={720} defaultProps={{ground: '#f8fafc', ink: '#111827', accent: '#b45309', words: 'The cost of first', face: 'thumbs/face-a.jpg', focus: '58% 20%'}} />
	</>
);
